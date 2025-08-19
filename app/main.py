"""
Main FastAPI application for OpsBuddy.
Entry point for the operations management platform.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import db_manager
from app.api.routes import file_router, utility_router, analytics_router
from app.utils.logger import get_logger, log_operation

logger = get_logger("main")

# Global variables for startup/shutdown
startup_time = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global startup_time
    
    # Startup
    startup_time = time.time()
    logger.info("Starting OpsBuddy application...")
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        db_connected = await db_manager.connect()
        
        if db_connected:
            logger.info("Successfully connected to database")
            log_operation("startup", "main", {"status": "success", "database": "connected"})
        else:
            logger.warning("Failed to connect to database, continuing without database")
            log_operation("startup", "main", {"status": "warning", "database": "failed"})
        
        logger.info("OpsBuddy application started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        log_operation("startup", "main", {"status": "failed", "error": str(e)}, "ERROR")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down OpsBuddy application...")
    
    try:
        # Disconnect from database
        await db_manager.disconnect()
        logger.info("Successfully disconnected from database")
        log_operation("shutdown", "main", {"status": "success"})
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        log_operation("shutdown", "main", {"status": "failed", "error": str(e)}, "ERROR")
    
    logger.info("OpsBuddy application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="A comprehensive operations management platform with microservices architecture and time-series database integration",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            "message": "Request data validation failed",
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
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(f"Response: {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Root endpoint
@app.get("/", summary="Root endpoint")
async def root():
    """Root endpoint providing basic application information."""
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "description": "Operations Management Platform",
        "status": "running",
        "uptime": time.time() - startup_time if startup_time else 0,
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else None
    }


# Health check endpoint
@app.get("/health", summary="Health check")
async def health_check():
    """Application health check endpoint."""
    try:
        # Check database connection
        db_status = "healthy" if await db_manager.is_connected() else "unhealthy"
        
        # Calculate uptime
        uptime = time.time() - startup_time if startup_time else 0
        
        health_status = {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": time.time(),
            "application": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "database": db_status,
            "uptime": uptime
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }


# API versioning
@app.get("/api", summary="API information")
async def api_info():
    """API information and versioning details."""
    return {
        "api_version": "v1",
        "base_url": "/api/v1",
        "services": [
            {
                "name": "File Service",
                "endpoints": "/api/v1/files/*",
                "description": "File operations and management"
            },
            {
                "name": "Utility Service",
                "endpoints": "/api/v1/utilities/*",
                "description": "Utility configurations and system operations"
            },
            {
                "name": "Analytics Service",
                "endpoints": "/api/v1/analytics/*",
                "description": "Analytics metrics and reporting"
            }
        ],
        "documentation": "/docs" if settings.debug else None
    }


# Include API routers with versioning
app.include_router(file_router, prefix="/api/v1")
app.include_router(utility_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


# Additional utility endpoints
@app.get("/ping", summary="Simple ping")
async def ping():
    """Simple ping endpoint."""
    return {"message": "pong", "service": settings.app_name}


@app.get("/info", summary="Application information")
async def app_info():
    """Detailed application information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Operations Management Platform",
        "environment": settings.environment,
        "debug": settings.debug,
        "database": {
            "host": settings.influxdb_host,
            "port": settings.influxdb_port,
            "database": settings.influxdb_database,
            "version": "2.x" if settings.influxdb_token else "1.x"
        },
        "features": {
            "file_service": True,
            "utility_service": True,
            "analytics_service": True,
            "time_series_db": True,
            "async_operations": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
