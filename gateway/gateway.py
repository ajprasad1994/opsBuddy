"""
OpsBuddy API Gateway - Main Application
Routes requests to appropriate microservices and provides centralized API access.
"""

import time
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import settings
from utils import (
    logger, CircuitBreaker, ServiceHealthChecker, log_request, 
    log_response, log_error, forward_request, determine_target_service,
    build_target_url
)

# Global variables for startup/shutdown
startup_time = None
circuit_breakers: Dict[str, CircuitBreaker] = {}
health_checker: Optional[ServiceHealthChecker] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global startup_time, circuit_breakers, health_checker
    
    # Startup
    startup_time = time.time()
    logger.info("Starting OpsBuddy API Gateway...")
    
    try:
        # Initialize circuit breakers for each service
        for service_name, service_config in settings.services.items():
            circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=service_config.circuit_breaker_threshold,
                timeout=settings.circuit_breaker_timeout
            )
        
        # Initialize health checker
        health_checker = ServiceHealthChecker(settings.services)
        
        # Perform initial health check
        await health_checker.check_all_services()
        
        logger.info("OpsBuddy API Gateway started successfully")
        logger.info(f"Routing rules: {settings.routing_rules}")
        logger.info(f"Service endpoints: {settings.service_urls}")
        
    except Exception as e:
        logger.error(f"Failed to start API Gateway: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down OpsBuddy API Gateway...")
    logger.info("API Gateway shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.gateway_name,
    description="Centralized API Gateway for OpsBuddy microservices",
    version=settings.gateway_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Add Gzip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "timestamp": time.time()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"General exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Gateway health check endpoint."""
    global health_checker
    
    if not health_checker:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "Health checker not initialized",
                "timestamp": time.time()
            }
        )
    
    try:
        # Check all services health
        service_health = await health_checker.check_all_services()
        
        # Determine overall gateway health
        overall_status = "healthy"
        unhealthy_services = []
        
        for service_name, health in service_health.items():
            if health.get("status") != "healthy":
                overall_status = "degraded"
                unhealthy_services.append(service_name)
        
        if not service_health:
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "gateway": {
                "name": settings.gateway_name,
                "version": settings.gateway_version,
                "uptime": time.time() - startup_time if startup_time else 0,
                "timestamp": time.time()
            },
            "services": service_health,
            "unhealthy_services": unhealthy_services
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# Service status endpoint
@app.get("/status")
async def service_status():
    """Get detailed status of all services."""
    global health_checker
    
    if not health_checker:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Health checker not initialized",
                "timestamp": time.time()
            }
        )
    
    try:
        service_health = await health_checker.check_all_services()
        
        return {
            "gateway": {
                "name": settings.gateway_name,
                "version": settings.gateway_version,
                "uptime": time.time() - startup_time if startup_time else 0,
                "timestamp": time.time()
            },
            "services": service_health,
            "circuit_breakers": {
                service_name: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure_time": cb.last_failure_time
                }
                for service_name, cb in circuit_breakers.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Dynamic routing middleware
@app.middleware("http")
async def route_requests(request: Request, call_next):
    """Route requests to appropriate microservices."""
    path = request.url.path
    method = request.method
    
    # Skip routing for gateway-specific endpoints
    if path in ["/", "/health", "/status", "/api", "/api/services", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Determine target service
    target_service = determine_target_service(path, settings.routing_rules)
    
    if not target_service:
        # No matching route found
        logger.warning(f"No route found for path: {path}")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "detail": f"No route found for path: {path}",
                "timestamp": time.time()
            }
        )
    
    # Check circuit breaker
    circuit_breaker = circuit_breakers.get(target_service)
    if circuit_breaker and not circuit_breaker.can_execute():
        logger.warning(f"Circuit breaker OPEN for service: {target_service}")
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service Unavailable",
                "detail": f"Service {target_service} is temporarily unavailable",
                "timestamp": time.time()
            }
        )
    
    try:
        # Log the request
        log_request(request, target_service, method, path)
        
        # Build target URL
        target_url = build_target_url(target_service, settings.service_urls, path)
        
        # Forward the request
        response, response_time = await forward_request(
            request, 
            target_url, 
            timeout=settings.services[target_service].timeout
        )
        
        # Log the response
        log_response(response, target_service, method, path, response.status_code)
        
        # Update circuit breaker on success
        if circuit_breaker:
            circuit_breaker.on_success()
        
        return response
        
    except Exception as e:
        # Log the error
        log_error(e, target_service, method, path)
        
        # Update circuit breaker on failure
        if circuit_breaker:
            circuit_breaker.on_failure()
        
        # Return appropriate error response
        if "timeout" in str(e).lower():
            return JSONResponse(
                status_code=504,
                content={
                    "error": "Gateway Timeout",
                    "detail": f"Service {target_service} did not respond in time",
                    "timestamp": time.time()
                }
            )
        else:
            return JSONResponse(
                status_code=502,
                content={
                    "error": "Bad Gateway",
                    "detail": f"Failed to forward request to {target_service}: {str(e)}",
                    "timestamp": time.time()
                }
            )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with gateway information."""
    return {
        "message": "Welcome to OpsBuddy API Gateway",
        "gateway": {
            "name": settings.gateway_name,
            "version": settings.gateway_version,
            "status": "running"
        },
        "services": list(settings.services.keys()),
        "documentation": "/docs" if settings.debug else "Not available in production",
        "health_check": "/health",
        "status": "/status"
    }


# API information endpoint
@app.get("/api")
async def api_info():
    """API information and available endpoints."""
    return {
        "gateway": {
            "name": settings.gateway_name,
            "version": settings.gateway_version
        },
        "available_services": {
            service_name: {
                "base_path": f"/api/{service_name}",
                "endpoints": [
                    "GET /api/{service_name}/*",
                    "POST /api/{service_name}/*",
                    "PUT /api/{service_name}/*",
                    "DELETE /api/{service_name}/*"
                ]
            }
            for service_name in settings.services.keys()
        },
        "routing_rules": settings.routing_rules
    }


# Services information endpoint (for frontend compatibility)
@app.get("/api/services")
async def get_services():
    """Get services information for frontend compatibility."""
    global health_checker

    if not health_checker:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Health checker not initialized",
                "timestamp": time.time()
            }
        )

    try:
        service_health = await health_checker.check_all_services()

        # Format services data for frontend
        services = []
        for service_name, health in service_health.items():
            services.append({
                "name": service_name.title(),
                "port": settings.services.get(service_name, {}).port or 8000,
                "status": health.get("status", "unknown"),
                "response_time": health.get("response_time", 0),
                "uptime": health.get("uptime", 0),
                "description": f"{service_name.title()} service"
            })

        return services

    except Exception as e:
        logger.error(f"Failed to get services: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to get services",
                "detail": str(e),
                "timestamp": time.time()
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "gateway:app",
        host=settings.gateway_host,
        port=settings.gateway_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
