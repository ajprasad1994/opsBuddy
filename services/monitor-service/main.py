"""
Main FastAPI application for OpsBuddy Monitor Service.
Coordinates health monitoring, Redis pub/sub, and WebSocket communication.
"""

import time
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import settings
from redis_client import redis_client
from health_monitor import health_monitor, ServiceHealth, ServiceStatus
from websocket_server import websocket_server


async def handle_error_log_message(message_data: str):
    """Handle incoming error log message and broadcast via WebSocket."""
    try:
        message = json.loads(message_data)

        if message.get("type") == "error_log" and message.get("error"):
            # Broadcast error log to all WebSocket clients
            await websocket_server._broadcast_to_clients({
                "type": "error_log",
                "error": message["error"],
                "timestamp": message.get("timestamp", datetime.utcnow().isoformat())
            })

            logger.debug(f"Broadcast error log for service: {message['error'].get('service', 'unknown')}")

    except Exception as e:
        logger.error(f"Error handling error log message: {str(e)}")

logger = None  # Will be set after logging is configured

# Global variables for startup/shutdown
startup_time = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global startup_time, logger

    # Configure logging
    import logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("monitor_service_main")

    startup_time = time.time()
    logger.info("Starting OpsBuddy Monitor Service...")

    try:
        # Connect to Redis
        logger.info("Connecting to Redis...")
        redis_connected = await redis_client.connect()

        if redis_connected:
            logger.info("Successfully connected to Redis")

            # Subscribe to error logs for real-time broadcasting
            await redis_client.subscribe_to_error_logs(handle_error_log_message)
        else:
            logger.warning("Failed to connect to Redis, continuing without Redis pub/sub")

        # Start health monitoring
        logger.info("Starting health monitoring...")
        await health_monitor.start_monitoring()
        logger.info("Health monitoring started successfully")

        # Create a simple monitoring loop that runs in the main event loop
        async def monitoring_loop():
            while True:
                try:
                    logger.info("Running health check cycle...")
                    await health_monitor._check_all_services()
                    logger.info("Health check cycle completed")
                    await asyncio.sleep(settings.health_check_interval)
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {str(e)}")
                    await asyncio.sleep(settings.retry_delay)

        # Start the monitoring loop in the main event loop
        asyncio.create_task(monitoring_loop())
        logger.info("Monitoring loop started in main event loop")

        # Verify monitoring is running
        if health_monitor.is_monitoring():
            logger.info("Health monitoring is active and running")
        else:
            logger.error("Health monitoring failed to start!")

        # Start WebSocket server
        logger.info("Starting WebSocket server...")
        websocket_task = asyncio.create_task(
            websocket_server.start_server(settings.service_host, 8006)
        )

        logger.info("Monitor Service started successfully")

    except Exception as e:
        logger.error(f"Failed to start Monitor Service: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Monitor Service...")

    try:
        # Stop health monitoring
        await health_monitor.stop_monitoring()

        # Stop WebSocket server
        await websocket_server.stop_server()

        # Disconnect from Redis
        await redis_client.disconnect()
        logger.info("Successfully disconnected from Redis")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

    logger.info("Monitor Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.service_name,
    description="Service health monitoring for OpsBuddy platform",
    version=settings.service_version,
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
async def validation_exception_handler(request, exc: RequestValidationError):
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
async def http_exception_handler(request, exc: StarletteHTTPException):
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
async def general_exception_handler(request, exc: Exception):
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
    """Service health check endpoint."""
    try:
        # Check Redis connection
        redis_status = "healthy" if redis_client.is_connected() else "unhealthy"

        # Check health monitor status
        monitor_status = "healthy" if health_monitor.is_monitoring() else "unhealthy"

        # Check WebSocket server status
        websocket_status = "healthy" if websocket_server.is_running() else "unhealthy"

        return {
            "status": "healthy" if all(status == "healthy" for status in [redis_status, monitor_status, websocket_status]) else "degraded",
            "service": {
                "name": settings.service_name,
                "version": settings.service_version,
                "uptime": time.time() - startup_time if startup_time else 0
            },
            "redis": redis_status,
            "health_monitor": monitor_status,
            "websocket_server": websocket_status,
            "websocket_connections": websocket_server.get_connection_count(),
            "timestamp": time.time()
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


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "message": f"Welcome to {settings.service_name}",
        "service": {
            "name": settings.service_name,
            "version": settings.service_version,
            "status": "running"
        },
        "endpoints": {
            "health": "/health",
            "services": "/services",
            "services/{name}": "/services/{name}",
            "system": "/system/health",
            "websocket": "ws://localhost:8006"
        },
        "documentation": "/docs" if settings.debug else "Not available in production"
    }


# Get all service statuses
@app.get("/services")
async def get_all_services():
    """Get status of all monitored services."""
    try:
        services = health_monitor.get_all_service_statuses()

        # Convert to JSON-serializable format
        service_data = {}
        for name, health in services.items():
            service_data[name] = {
                "name": health.name,
                "url": health.url,
                "status": health.status.value,
                "response_time": health.response_time,
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "consecutive_failures": health.consecutive_failures,
                "error_message": health.error_message,
                "details": health.details
            }

        return {
            "services": service_data,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to get service statuses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get specific service status
@app.get("/services/{service_name}")
async def get_service_status(service_name: str):
    """Get status of a specific service."""
    try:
        service_health = health_monitor.get_service_status(service_name)

        if not service_health:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

        return {
            "service": {
                "name": service_health.name,
                "url": service_health.url,
                "status": service_health.status.value,
                "response_time": service_health.response_time,
                "last_check": service_health.last_check.isoformat() if service_health.last_check else None,
                "consecutive_failures": service_health.consecutive_failures,
                "error_message": service_health.error_message,
                "details": service_health.details
            },
            "timestamp": time.time()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get service group status
@app.get("/services/groups/{group_name}")
async def get_service_group_status(group_name: str):
    """Get status of services in a specific group."""
    try:
        services = health_monitor.get_service_group_status(group_name)

        if not services:
            raise HTTPException(status_code=404, detail=f"Service group '{group_name}' not found")

        # Convert to JSON-serializable format
        service_data = {}
        for name, health in services.items():
            service_data[name] = {
                "name": health.name,
                "url": health.url,
                "status": health.status.value,
                "response_time": health.response_time,
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "consecutive_failures": health.consecutive_failures,
                "error_message": health.error_message,
                "details": health.details
            }

        return {
            "group": group_name,
            "services": service_data,
            "timestamp": time.time()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get service group status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get overall system health
@app.get("/system/health")
async def get_system_health():
    """Get overall system health summary."""
    try:
        system_health = health_monitor.get_overall_health()

        return {
            "system_health": system_health,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to get system health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time service health updates."""
    await websocket.accept()

    client_id = id(websocket)
    logger.info(f"WebSocket client connected: {client_id}")

    try:
        # Send initial system status
        system_health = health_monitor.get_overall_health()
        await websocket.send_json({
            "type": "initial_status",
            "data": system_health,
            "timestamp": time.time()
        })

        # Listen for client messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                message_type = data.get("type")

                if message_type == "subscribe":
                    subscriptions = data.get("subscriptions", ["health_updates"])
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "subscriptions": subscriptions,
                        "timestamp": time.time()
                    })

                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": time.time()
                    })

            except Exception as e:
                logger.error(f"Error handling WebSocket message: {str(e)}")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        try:
            await websocket.close()
        except:
            pass


# Service information endpoint
@app.get("/info")
async def service_info():
    """Get service information and configuration."""
    return {
        "service": {
            "name": settings.service_name,
            "version": settings.service_version,
            "host": settings.service_host,
            "port": settings.service_port,
            "environment": settings.environment
        },
        "configuration": {
            "health_check_interval": settings.health_check_interval,
            "service_timeout": settings.service_timeout,
            "max_consecutive_failures": settings.max_consecutive_failures,
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "websocket_ping_interval": settings.websocket_ping_interval
        },
        "monitoring": {
            "services_count": len(settings.service_urls),
            "is_monitoring": health_monitor.is_monitoring(),
            "websocket_connections": websocket_server.get_connection_count(),
            "websocket_running": websocket_server.is_running(),
            "redis_connected": redis_client.is_connected()
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )