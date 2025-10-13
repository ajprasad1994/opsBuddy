"""
Main FastAPI application for OpsBuddy Analytics Service.
Collects, validates, and stores logs from all microservices in InfluxDB.
"""

import time
import json
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field, validator
import aiohttp

from config import settings
from database import db_manager
from log_collector import log_collector
from log_transformer import log_transformer
from utils import get_logger, log_operation

logger = get_logger("analytics_service_main")

# Global variables for startup/shutdown
startup_time = None

# Request/Response Models
class LogEntry(BaseModel):
    """Log entry model for incoming logs."""
    timestamp: str = Field(..., description="ISO format timestamp")
    level: str = Field(..., description="Log level (INFO, ERROR, WARNING, DEBUG)")
    logger: str = Field(..., description="Logger name")
    message: str = Field(..., description="Log message")
    service: str = Field(..., description="Service name")
    operation: Optional[str] = Field(None, description="Operation being performed")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional log data")
    host: Optional[str] = Field(None, description="Host information")
    user_id: Optional[str] = Field(None, description="User ID if applicable")

    @validator('level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()

    @validator('timestamp')
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('Timestamp must be in ISO format')

class LogQuery(BaseModel):
    """Query model for log analytics."""
    service: Optional[str] = Field(None, description="Filter by service name")
    level: Optional[str] = Field(None, description="Filter by log level")
    start_time: Optional[str] = Field(None, description="Start time for query")
    end_time: Optional[str] = Field(None, description="End time for query")
    operation: Optional[str] = Field(None, description="Filter by operation")
    limit: int = Field(100, ge=1, le=10000, description="Maximum results to return")
    aggregation: Optional[str] = Field(None, description="Aggregation type (count, avg, etc.)")

class MetricsQuery(BaseModel):
    """Query model for metrics."""
    metric: str = Field(..., description="Metric name to query")
    service: Optional[str] = Field(None, description="Filter by service")
    start_time: Optional[str] = Field(None, description="Start time for query")
    end_time: Optional[str] = Field(None, description="End time for query")
    aggregation: str = Field("mean", description="Aggregation function")
    group_by: Optional[str] = Field(None, description="Group by field")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global startup_time

    # Startup
    startup_time = time.time()
    logger.info("Starting OpsBuddy Analytics Service...")

    try:
        # Connect to database
        logger.info("Connecting to InfluxDB...")
        db_connected = await db_manager.connect()

        if db_connected:
            logger.info("Successfully connected to InfluxDB")
            log_operation("startup", "analytics_service", {"status": "success", "database": "connected"})
        else:
            logger.warning("Failed to connect to InfluxDB, continuing without database")
            log_operation("startup", "analytics_service", {"status": "warning", "database": "failed"})

        # Start log collection in background
        logger.info("Starting log collection service...")
        await log_collector.start_collection()

        logger.info("Analytics Service started successfully")

    except Exception as e:
        logger.error(f"Failed to start Analytics Service: {str(e)}")
        log_operation("startup", "analytics_service", {"status": "failed", "error": str(e)}, "ERROR")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Analytics Service...")

    try:
        # Stop log collection
        await log_collector.stop_collection()

        # Disconnect from database
        await db_manager.disconnect()
        logger.info("Successfully disconnected from InfluxDB")
        log_operation("shutdown", "analytics_service", {"status": "success"})

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        log_operation("shutdown", "analytics_service", {"status": "failed", "error": str(e)}, "ERROR")

    logger.info("Analytics Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.service_name,
    description="Analytics and log collection service for OpsBuddy platform",
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

        # Check log collector status
        collector_status = "healthy" if log_collector.is_running() else "unhealthy"

        return {
            "status": "healthy" if db_status == "healthy" and collector_status == "healthy" else "degraded",
            "service": {
                "name": settings.service_name,
                "version": settings.service_version,
                "uptime": time.time() - startup_time if startup_time else 0
            },
            "database": db_status,
            "log_collector": collector_status,
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
            "logs": "/logs",
            "metrics": "/metrics",
            "analytics": "/analytics/query"
        },
        "documentation": "/docs" if settings.debug else "Not available in production"
    }


# Log ingestion endpoint
@app.post("/logs")
async def ingest_logs(logs: List[LogEntry], background_tasks: BackgroundTasks):
    """Ingest logs from microservices."""
    try:
        # Validate and transform logs
        validated_logs = []
        for log_entry in logs:
            try:
                # Transform log to standardized format
                transformed_log = await log_transformer.transform_log(log_entry.dict())
                validated_logs.append(transformed_log)
            except Exception as e:
                logger.warning(f"Failed to transform log entry: {str(e)}")
                continue

        if not validated_logs:
            raise HTTPException(status_code=400, detail="No valid logs to process")

        # Store logs in background
        background_tasks.add_task(store_logs_background, validated_logs)

        return {
            "message": "Logs received successfully",
            "logs_processed": len(validated_logs),
            "logs_received": len(logs),
            "timestamp": time.time()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Log ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Single log ingestion endpoint
@app.post("/logs/single")
async def ingest_single_log(log: LogEntry, background_tasks: BackgroundTasks):
    """Ingest a single log entry."""
    try:
        # Transform log to standardized format
        transformed_log = await log_transformer.transform_log(log.dict())

        # Store log in background
        background_tasks.add_task(store_single_log_background, transformed_log)

        return {
            "message": "Log received successfully",
            "log_id": transformed_log.get("log_id"),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Single log ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Query logs endpoint
@app.post("/logs/query")
async def query_logs(query: LogQuery):
    """Query logs with filters and aggregation."""
    try:
        # Build query filters
        filters = {}
        if query.service:
            filters["service"] = query.service
        if query.level:
            filters["level"] = query.level
        if query.operation:
            filters["operation"] = query.operation

        # Parse time range
        start_time = None
        end_time = None
        if query.start_time:
            start_time = query.start_time
        if query.end_time:
            end_time = query.end_time

        # Query logs from database
        logs = await db_manager.query_logs(
            filters=filters,
            start_time=start_time,
            end_time=end_time,
            limit=query.limit
        )

        return {
            "logs": logs,
            "count": len(logs),
            "query": query.dict(),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Log query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get service metrics and statistics."""
    try:
        # Get metrics from database
        metrics = await db_manager.get_service_metrics()

        return {
            "metrics": metrics,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Metrics retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics query endpoint
@app.post("/analytics/query")
async def analytics_query(query: MetricsQuery):
    """Advanced analytics query for metrics."""
    try:
        # Parse time range
        start_time = None
        end_time = None
        if query.start_time:
            start_time = query.start_time
        if query.end_time:
            end_time = query.end_time

        # Query metrics from database
        results = await db_manager.query_metrics(
            metric=query.metric,
            service=query.service,
            start_time=start_time,
            end_time=end_time,
            aggregation=query.aggregation,
            group_by=query.group_by
        )

        return {
            "results": results,
            "query": query.dict(),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Analytics query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Service statistics endpoint
@app.get("/stats")
async def get_service_statistics():
    """Get comprehensive service statistics."""
    try:
        # Get statistics from database
        stats = await db_manager.get_service_statistics()

        return {
            "statistics": stats,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Statistics retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Log collection status endpoint
@app.get("/collector/status")
async def get_collector_status():
    """Get log collector status and configuration."""
    try:
        status = {
            "is_running": log_collector.is_running(),
            "collection_interval": log_collector.collection_interval,
            "services_monitored": list(log_collector.services.keys()),
            "last_collection": log_collector.last_collection,
            "logs_collected": log_collector.logs_collected,
            "errors": log_collector.errors
        }

        return {
            "collector_status": status,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Collector status retrieval failed: {str(e)}")
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
            "log_collection_interval": settings.log_collection_interval,
            "batch_size": settings.batch_size,
            "retention_days": settings.retention_days
        },
        "database": {
            "host": settings.influxdb_host,
            "port": settings.influxdb_port,
            "database": settings.influxdb_database,
            "connected": db_manager._connected
        }
    }


# Background task functions
async def store_logs_background(logs: List[Dict[str, Any]]):
    """Store logs in database (background task)."""
    try:
        await db_manager.store_logs(logs)
        logger.info(f"Successfully stored {len(logs)} logs in database")
    except Exception as e:
        logger.error(f"Failed to store logs in background: {str(e)}")

async def store_single_log_background(log: Dict[str, Any]):
    """Store single log in database (background task)."""
    try:
        await db_manager.store_logs([log])
        logger.debug(f"Successfully stored single log in database: {log.get('log_id')}")
    except Exception as e:
        logger.error(f"Failed to store single log in background: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )