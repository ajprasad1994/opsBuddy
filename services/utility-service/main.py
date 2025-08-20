"""
Main FastAPI application for OpsBuddy Utility Service.
Provides utility configuration management and system operations.
"""

import time
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel

from config import settings
from database import db_manager
from utility_service import utility_service
from utils import get_logger, log_operation

logger = get_logger("utility_service_main")

# Global variables for startup/shutdown
startup_time = None


# Request/Response Models
class CreateConfigRequest(BaseModel):
    name: str
    category: str
    value: Any
    description: Optional[str] = None


class UpdateConfigRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    value: Optional[Any] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ExecuteCommandRequest(BaseModel):
    command: str
    timeout: Optional[int] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global startup_time
    
    # Startup
    startup_time = time.time()
    logger.info("Starting OpsBuddy Utility Service...")
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        db_connected = await db_manager.connect()
        
        if db_connected:
            logger.info("Successfully connected to database")
            log_operation("startup", "utility_service", {"status": "success", "database": "connected"})
        else:
            logger.warning("Failed to connect to database, continuing without database")
            log_operation("startup", "utility_service", {"status": "warning", "database": "failed"})
        
        logger.info("Utility Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Utility Service: {str(e)}")
        log_operation("startup", "utility_service", {"status": "failed", "error": str(e)}, "ERROR")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Utility Service...")
    
    try:
        # Disconnect from database
        await db_manager.disconnect()
        logger.info("Successfully disconnected from database")
        log_operation("shutdown", "utility_service", {"status": "success"})
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        log_operation("shutdown", "utility_service", {"status": "failed", "error": str(e)}, "ERROR")
    
    logger.info("Utility Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.service_name,
    description="Utility configuration and system operations service for OpsBuddy platform",
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
        health_data = await utility_service.health_check()
        return health_data
        
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
            "configs": "/configs",
            "system": "/system/info",
            "execute": "/system/execute"
        },
        "documentation": "/docs" if settings.debug else "Not available in production"
    }


# Configuration endpoints
@app.post("/configs")
async def create_config(request: CreateConfigRequest):
    """Create a new utility configuration."""
    try:
        config = await utility_service.create_config(
            name=request.name,
            category=request.category,
            value=request.value,
            description=request.description
        )
        
        return {
            "message": "Configuration created successfully",
            "config": config
        }
        
    except Exception as e:
        logger.error(f"Failed to create config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/configs/{config_id}")
async def get_config(config_id: str):
    """Get a utility configuration by ID."""
    try:
        config = await utility_service.read_config(config_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/configs/{config_id}")
async def update_config(config_id: str, request: UpdateConfigRequest):
    """Update a utility configuration."""
    try:
        config = await utility_service.update_config(
            config_id=config_id,
            name=request.name,
            category=request.category,
            value=request.value,
            description=request.description,
            is_active=request.is_active
        )
        
        return {
            "message": "Configuration updated successfully",
            "config": config
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/configs/{config_id}")
async def delete_config(config_id: str):
    """Delete a utility configuration."""
    try:
        success = await utility_service.delete_config(config_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete configuration")
        
        return {
            "message": "Configuration deleted successfully",
            "config_id": config_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/configs")
async def list_configs(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of configs to return"),
    offset: int = Query(0, ge=0, description="Number of configs to skip")
):
    """List utility configurations with optional filtering."""
    try:
        configs = await utility_service.list_configs(
            category=category,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        
        return {
            "configs": configs,
            "count": len(configs),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to list configs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# System endpoints
@app.get("/system/info")
async def get_system_info():
    """Get system information and statistics."""
    try:
        system_info = await utility_service.get_system_info()
        return system_info
        
    except Exception as e:
        logger.error(f"Failed to get system info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/system/execute")
async def execute_command(request: ExecuteCommandRequest):
    """Execute a system command safely."""
    try:
        result = await utility_service.execute_command(
            command=request.command,
            timeout=request.timeout
        )
        
        return {
            "message": "Command executed successfully",
            "result": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute command: {str(e)}")
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
            "command_timeout": settings.command_timeout,
            "max_command_output": settings.max_command_output,
            "allowed_commands": settings.allowed_commands_list
        },
        "database": {
            "host": settings.influxdb_host,
            "port": settings.influxdb_port,
            "database": settings.influxdb_database
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
