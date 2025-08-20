"""
Main FastAPI application for OpsBuddy File Service.
Provides file upload, download, and management endpoints.
"""

import time
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import settings
from database import db_manager
from file_service import file_service
from utils import get_logger, log_operation

logger = get_logger("file_service_main")

# Global variables for startup/shutdown
startup_time = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global startup_time
    
    # Startup
    startup_time = time.time()
    logger.info("Starting OpsBuddy File Service...")
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        db_connected = await db_manager.connect()
        
        if db_connected:
            logger.info("Successfully connected to database")
            log_operation("startup", "file_service", {"status": "success", "database": "connected"})
        else:
            logger.warning("Failed to connect to database, continuing without database")
            log_operation("startup", "file_service", {"status": "warning", "database": "failed"})
        
        logger.info("File Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start File Service: {str(e)}")
        log_operation("startup", "file_service", {"status": "failed", "error": str(e)}, "ERROR")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down File Service...")
    
    try:
        # Disconnect from database
        await db_manager.disconnect()
        logger.info("Successfully disconnected from database")
        log_operation("shutdown", "file_service", {"status": "success"})
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        log_operation("shutdown", "file_service", {"status": "failed", "error": str(e)}, "ERROR")
    
    logger.info("File Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.service_name,
    description="File management service for OpsBuddy platform",
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
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "service": {
                "name": settings.service_name,
                "version": settings.service_version,
                "uptime": time.time() - startup_time if startup_time else 0
            },
            "database": db_status,
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
            "upload": "/files/upload",
            "download": "/files/{file_id}",
            "list": "/files",
            "metadata": "/files/{file_id}/metadata"
        },
        "documentation": "/docs" if settings.debug else "Not available in production"
    }


# File upload endpoint
@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None)
):
    """Upload a new file."""
    try:
        # Parse tags and metadata
        parsed_tags = {}
        if tags:
            try:
                import json
                parsed_tags = json.loads(tags)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid tags format")
        
        parsed_metadata = {}
        if metadata:
            try:
                import json
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata format")
        
        # Read file content
        content = await file.read()
        
        # Create file
        file_metadata = await file_service.create_file(
            file_content=content,
            filename=file.filename,
            tags=parsed_tags,
            metadata=parsed_metadata
        )
        
        return {
            "message": "File uploaded successfully",
            "file_id": file_metadata.file_id,
            "metadata": file_metadata
        }
        
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# File download endpoint
@app.get("/files/{file_id}")
async def download_file(file_id: str):
    """Download a file by ID."""
    try:
        file_data = await file_service.read_file(file_id)
        
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Return file as response
        from pathlib import Path
        file_path = Path(file_data["file_path"])
        
        return FileResponse(
            path=file_path,
            filename=file_data["metadata"].filename,
            media_type="application/octet-stream"
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"File download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get file metadata endpoint
@app.get("/files/{file_id}/metadata")
async def get_file_metadata(file_id: str):
    """Get file metadata by ID."""
    try:
        metadata = await file_service.get_file_metadata(file_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        return metadata
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Get metadata failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# List files endpoint
@app.get("/files")
async def list_files(
    tags: Optional[str] = Query(None, description="Comma-separated key=value pairs"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of files to return"),
    offset: int = Query(0, ge=0, description="Number of files to skip")
):
    """List files with optional filtering."""
    try:
        # Parse tags
        parsed_tags = {}
        if tags:
            for tag_pair in tags.split(','):
                if '=' in tag_pair:
                    key, value = tag_pair.split('=', 1)
                    parsed_tags[key.strip()] = value.strip()
        
        files = await file_service.list_files(
            tags=parsed_tags,
            file_type=file_type,
            limit=limit,
            offset=offset
        )
        
        return {
            "files": files,
            "count": len(files),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"List files failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Update file endpoint
@app.put("/files/{file_id}")
async def update_file(
    file_id: str,
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None)
):
    """Update an existing file."""
    try:
        # Parse tags and metadata
        parsed_tags = {}
        if tags:
            try:
                import json
                parsed_tags = json.loads(tags)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid tags format")
        
        parsed_metadata = {}
        if metadata:
            try:
                import json
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata format")
        
        # Read file content
        content = await file.read()
        
        # Update file
        updated_metadata = await file_service.update_file(
            file_id=file_id,
            new_content=content,
            new_tags=parsed_tags,
            new_metadata=parsed_metadata
        )
        
        return {
            "message": "File updated successfully",
            "file_id": updated_metadata.file_id,
            "metadata": updated_metadata
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"File update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Delete file endpoint
@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file by ID."""
    try:
        success = await file_service.delete_file(file_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete file")
        
        return {
            "message": "File deleted successfully",
            "file_id": file_id
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"File deletion failed: {str(e)}")
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
            "max_file_size": settings.max_file_size,
            "allowed_file_types": settings.allowed_file_types,
            "upload_directory": settings.upload_directory
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
