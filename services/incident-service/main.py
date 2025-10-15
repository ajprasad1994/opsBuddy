"""
Main FastAPI application for OpsBuddy Incident Service.
Monitors logs for incidents and publishes events to Redis.
"""

import time
import json
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import redis.asyncio as redis

from config import settings
from database import db_manager
from utils import get_logger, log_incident, create_incident_event, create_analytics_update, create_health_response

logger = get_logger("incident_service_main")

# Global variables for startup/shutdown
startup_time = None
redis_client = None
monitoring_task = None
last_error_check = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global startup_time, redis_client, monitoring_task, last_error_check

    # Startup
    startup_time = time.time()
    last_error_check = datetime.utcnow()
    logger.info("Starting OpsBuddy Incident Service...")

    try:
        # Connect to database
        logger.info("Connecting to InfluxDB...")
        db_connected = await db_manager.connect()

        if db_connected:
            logger.info("Successfully connected to InfluxDB")
        else:
            logger.warning("Failed to connect to InfluxDB, continuing without database")

        # Connect to Redis
        logger.info("Connecting to Redis...")
        redis_client = redis.Redis(**settings.redis_client_config)

        try:
            # Test Redis connection
            await redis_client.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            redis_client = None

        # Start monitoring with background thread approach
        if db_connected and redis_client:
            logger.info("Starting incident monitoring...")
            # Use background thread for monitoring (similar to UI service Redis subscriber)
            import threading
            monitor_thread = threading.Thread(target=start_monitoring_thread, daemon=True)
            monitor_thread.start()
            logger.info("Incident monitoring started successfully")
        else:
            logger.warning("Monitoring not started due to missing connections")

        logger.info("Incident Service started successfully")

    except Exception as e:
        logger.error(f"Failed to start Incident Service: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Incident Service...")

    try:
        # Stop monitoring task
        if monitoring_task:
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass

        # Close Redis connection
        if redis_client:
            await redis_client.close()
            logger.info("Redis connection closed")

        # Disconnect from database
        await db_manager.disconnect()
        logger.info("Database connection closed")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

    logger.info("Incident Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title=settings.service_name,
    description="Incident detection and monitoring service for OpsBuddy platform",
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
        # Check database connection
        db_status = "healthy" if db_manager._connected else "unhealthy"

        # Check Redis connection
        redis_status = "healthy"
        if redis_client:
            try:
                await redis_client.ping()
            except Exception:
                redis_status = "unhealthy"
        else:
            redis_status = "unhealthy"

        # Check monitoring status
        monitoring_status = "healthy" if monitoring_task and not monitoring_task.done() else "unhealthy"

        overall_status = "healthy"
        if db_status != "healthy" or redis_status != "healthy" or monitoring_status != "healthy":
            overall_status = "degraded"
        if db_status != "healthy" and redis_status != "healthy":
            overall_status = "unhealthy"

        return create_health_response(
            settings.service_name,
            overall_status,
            database=db_status,
            redis=redis_status,
            monitoring=monitoring_status,
            uptime=time.time() - startup_time if startup_time else 0
        )

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
            "incidents": "/incidents",
            "errors": "/errors"
        },
        "documentation": "/docs" if settings.debug else "Not available in production"
    }

# Get recent incidents endpoint
@app.get("/incidents")
async def get_incidents(hours: int = 1):
    """Get recent incidents and errors."""
    try:
        # Get incident summary from database
        summary = await db_manager.get_incident_summary(hours=hours)

        return {
            "incidents": summary,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to get incidents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get errors for specific service endpoint
@app.get("/errors/{service}")
async def get_service_errors(service: str, hours: int = 1):
    """Get errors for a specific service."""
    try:
        # Query errors for the service
        errors = await db_manager.query_service_errors(service, hours=hours)

        return {
            "service": service,
            "errors": errors,
            "count": len(errors),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to get service errors: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Force error check endpoint
@app.post("/check")
async def force_error_check(background_tasks: BackgroundTasks):
    """Force an immediate error check and publish incidents."""
    try:
        # Run error check in background
        background_tasks.add_task(run_error_check)

        return {
            "message": "Error check initiated",
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to initiate error check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
            "monitoring_interval": settings.monitoring_interval,
            "query_batch_size": settings.query_batch_size,
            "error_retention_hours": settings.error_retention_hours
        },
        "connections": {
            "database": "connected" if db_manager._connected else "disconnected",
            "redis": "connected" if redis_client else "disconnected"
        },
        "monitoring": {
            "is_running": monitoring_task is not None and not monitoring_task.done(),
            "last_check": last_error_check.isoformat() if last_error_check else None
        }
    }

# Background monitoring function
async def monitoring_loop():
    """Start the continuous monitoring loop in the main event loop."""
    global last_error_check

    logger.info(f"Starting monitoring loop with {settings.monitoring_interval}s interval")

    while True:
        try:
            logger.debug("Running error check cycle...")
            # Run error check
            await run_error_check()
            logger.debug("Error check cycle completed")

            # Wait for next interval
            await asyncio.sleep(settings.monitoring_interval)

        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {str(e)}")
            # Continue monitoring even if there's an error
            await asyncio.sleep(settings.monitoring_interval)

# Thread-based monitoring starter
def start_monitoring_thread():
    """Start monitoring in a background thread with its own event loop."""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the monitoring loop
        loop.run_until_complete(monitoring_loop())

    except Exception as e:
        logger.error(f"Error in monitoring thread: {str(e)}")

# Error checking and Redis publishing function
async def run_error_check():
    """Check for new errors and publish to Redis."""
    global last_error_check

    if not db_manager._connected or not redis_client:
        logger.warning("Cannot run error check: missing database or Redis connection")
        return

    try:
        # Update last check time
        current_check = datetime.utcnow()
        last_error_check = current_check

        # Query recent logs since last check
        if last_error_check:
            # Query errors since last check
            recent_errors = await db_manager.query_errors_since(
                last_error_check.replace(microsecond=0).isoformat() + "Z"
            )

            if recent_errors:
                logger.info(f"Found {len(recent_errors)} new errors")

                # Process each error
                for error_log in recent_errors:
                    # Create incident event
                    incident_event = create_incident_event(error_log, "error_detected")

                    # Publish to Redis channels
                    await publish_incident(incident_event)

                    # Publish individual error log for real-time UI updates
                    await publish_error_log(error_log)

                    # Log the incident
                    log_incident(
                        error_log.get("service", "unknown"),
                        "error_detected",
                        {
                            "error_message": error_log.get("message"),
                            "level": error_log.get("level"),
                            "operation": error_log.get("operation")
                        },
                        "ERROR"
                    )

                # Create analytics update
                service_error_counts = {}
                for error in recent_errors:
                    service = error.get("service", "unknown")
                    service_error_counts[service] = service_error_counts.get(service, 0) + 1

                # Publish analytics updates for each service
                for service, count in service_error_counts.items():
                    analytics_event = create_analytics_update(
                        service,
                        count,
                        {
                            "start": last_error_check.replace(microsecond=0).isoformat() + "Z",
                            "end": current_check.replace(microsecond=0).isoformat() + "Z"
                        }
                    )
                    await publish_analytics_update(analytics_event)

            else:
                logger.debug("No new errors found")

        # Update last_error_check for next iteration
        last_error_check = current_check

    except Exception as e:
        logger.error(f"Error during error check: {str(e)}")

# Redis publishing functions
async def publish_incident(incident_event: Dict[str, Any]):
    """Publish incident event to Redis."""
    if not redis_client:
        logger.warning("Cannot publish incident: no Redis connection")
        return

    try:
        # Publish to incidents channel
        await redis_client.publish(
            settings.redis_channel_incidents,
            json.dumps(incident_event, default=str)
        )

        # Also publish to errors channel for backward compatibility
        await redis_client.publish(
            settings.redis_channel_errors,
            json.dumps(incident_event, default=str)
        )

        logger.debug(f"Published incident event: {incident_event['data']['incident_id']}")

    except Exception as e:
        logger.error(f"Failed to publish incident to Redis: {str(e)}")

async def publish_analytics_update(analytics_event: Dict[str, Any]):
    """Publish analytics update to Redis."""
    if not redis_client:
        logger.warning("Cannot publish analytics update: no Redis connection")
        return

    try:
        # Publish to analytics channel
        await redis_client.publish(
            settings.redis_channel_analytics,
            json.dumps(analytics_event, default=str)
        )

        logger.debug(f"Published analytics update for service: {analytics_event['data']['service']}")

    except Exception as e:
        logger.error(f"Failed to publish analytics update to Redis: {str(e)}")


async def publish_error_log(error_log: Dict[str, Any]):
    """Publish individual error log to Redis for real-time UI updates."""
    if not redis_client:
        logger.warning("Cannot publish error log: no Redis connection")
        return

    try:
        # Create error log event for UI
        error_event = {
            "type": "error_log",
            "error": {
                "service": error_log.get("service", "unknown"),
                "level": error_log.get("level", "ERROR"),
                "logger": error_log.get("logger", "unknown"),
                "message": error_log.get("message", "No message"),
                "timestamp": error_log.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                "operation": error_log.get("operation"),
                "host": error_log.get("host")
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Publish to error logs channel
        await redis_client.publish(
            settings.redis_channel_errors,
            json.dumps(error_event, default=str)
        )

        logger.debug(f"Published error log for service: {error_log.get('service', 'unknown')}")

    except Exception as e:
        logger.error(f"Failed to publish error log to Redis: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )