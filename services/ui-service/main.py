"""
Main FastAPI application for OpsBuddy UI Service.
Provides a web interface to interact with all OpsBuddy services.
"""

import time
import json
import aiohttp
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Global variables for startup/shutdown
startup_time = None

# Service URLs
SERVICE_URLS = {
    "gateway": "http://api-gateway:8000",
    "file-service": "http://file-service:8001",
    "utility-service": "http://utility-service:8002"
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global startup_time

    # Startup
    startup_time = time.time()
    print("Starting OpsBuddy UI Service...")

    try:
        print("UI Service started successfully")
    except Exception as e:
        print(f"Failed to start UI Service: {str(e)}")
        raise

    yield

    # Shutdown
    print("Shutting down UI Service...")
    print("UI Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="OpsBuddy UI",
    description="Web interface for OpsBuddy services",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Gzip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")


async def make_request(url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
    """Make HTTP request to services."""
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {"status": response.status, "text": await response.text()}
    except asyncio.TimeoutError:
        return {"error": "Request timeout", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with welcome message and service cards."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "OpsBuddy - AI Driven Oncall Support",
        "welcome_message": "Welcome to OpsBuddy - AI driven oncall support"
    })


@app.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "service": "ui-service",
        "uptime": time.time() - startup_time if startup_time else 0,
        "timestamp": time.time()
    }


# File Service endpoints
@app.get("/api/files")
async def list_files():
    """List files from file service."""
    url = f"{SERVICE_URLS['file-service']}/files"
    return await make_request(url)


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...), tags: str = Form(""), metadata: str = Form("")):
    """Upload file to file service."""
    try:
        # Prepare form data
        data = aiohttp.FormData()
        data.add_field('file', file.file, filename=file.filename, content_type=file.content_type)

        if tags:
            data.add_field('tags', tags)
        if metadata:
            data.add_field('metadata', metadata)

        url = f"{SERVICE_URLS['file-service']}/files/upload"
        return await make_request(url, "POST", data=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/{file_id}")
async def get_file(file_id: str):
    """Get file metadata from file service."""
    url = f"{SERVICE_URLS['file-service']}/files/{file_id}/metadata"
    return await make_request(url)


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete file from file service."""
    url = f"{SERVICE_URLS['file-service']}/files/{file_id}"
    return await make_request(url, "DELETE")


# Utility Service endpoints
@app.get("/api/configs")
async def list_configs():
    """List configurations from utility service."""
    url = f"{SERVICE_URLS['utility-service']}/configs"
    return await make_request(url)


@app.post("/api/configs")
async def create_config(
    name: str = Form(...),
    category: str = Form(...),
    value: str = Form(...),
    description: str = Form("")
):
    """Create configuration in utility service."""
    config_data = {
        "name": name,
        "category": category,
        "value": value,
        "description": description
    }

    url = f"{SERVICE_URLS['utility-service']}/configs"
    return await make_request(url, "POST", json=config_data)


@app.get("/api/system/info")
async def get_system_info():
    """Get system information from utility service."""
    url = f"{SERVICE_URLS['utility-service']}/system/info"
    return await make_request(url)


@app.post("/api/system/execute")
async def execute_command(command: str = Form(...), timeout: int = Form(30)):
    """Execute system command via utility service."""
    command_data = {
        "command": command,
        "timeout": timeout
    }

    url = f"{SERVICE_URLS['utility-service']}/system/execute"
    return await make_request(url, "POST", json=command_data)


# Service status endpoints
@app.get("/api/services/status")
async def get_services_status():
    """Get status of all services."""
    services = {}

    for service_name, service_url in SERVICE_URLS.items():
        try:
            if service_name == "gateway":
                url = f"{service_url}/health"
            elif service_name == "file-service":
                url = f"{service_url}/health"
            elif service_name == "utility-service":
                url = f"{service_url}/health"

            result = await make_request(url)
            services[service_name] = {
                "status": "healthy" if "status" in result and result.get("status") in ["healthy", "running"] else "unhealthy",
                "response": result
            }
        except Exception as e:
            services[service_name] = {
                "status": "error",
                "error": str(e)
            }

    return services


# UI Routes
@app.get("/files", response_class=HTMLResponse)
async def files_page(request: Request):
    """File service UI page."""
    return templates.TemplateResponse("files.html", {"request": request})


@app.get("/utility", response_class=HTMLResponse)
async def utility_page(request: Request):
    """Utility service UI page."""
    return templates.TemplateResponse("utility.html", {"request": request})


@app.get("/system", response_class=HTMLResponse)
async def system_page(request: Request):
    """System operations UI page."""
    return templates.TemplateResponse("system.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3000,
        reload=True,
        log_level="info"
    )