"""
Utility Service API routes for OpsBuddy application.
Provides REST endpoints for utility operations and system management.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any

from app.services.utility_service import utility_service
from app.api.models.utility_models import (
    UtilityConfigCreateRequest,
    UtilityConfigUpdateRequest,
    UtilityConfigResponse,
    UtilityConfigListRequest,
    UtilityConfigListResponse,
    SystemInfoResponse,
    HealthCheckResponse,
    CommandExecuteRequest,
    CommandExecuteResponse,
    UtilityOperationResponse,
    UtilityErrorResponse
)
from app.utils.logger import get_logger

logger = get_logger("utility_routes")

router = APIRouter(prefix="/utilities", tags=["Utility Service"])


@router.post("/configs", response_model=UtilityConfigResponse, summary="Create utility configuration")
async def create_config(request: UtilityConfigCreateRequest):
    """
    Create a new utility configuration.
    
    - **name**: Configuration name
    - **category**: Configuration category
    - **value**: Configuration value
    - **description**: Optional description
    """
    try:
        config = await utility_service.create_config(
            name=request.name,
            category=request.category,
            value=request.value,
            description=request.description
        )
        
        if not config:
            raise HTTPException(status_code=500, detail="Failed to create configuration")
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration creation failed: {str(e)}")


@router.get("/configs/{config_id}", response_model=UtilityConfigResponse, summary="Get utility configuration")
async def get_config(config_id: str):
    """
    Get a utility configuration by ID.
    
    - **config_id**: Unique identifier of the configuration
    """
    try:
        config = await utility_service.read_config(config_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration retrieval failed: {str(e)}")


@router.put("/configs/{config_id}", response_model=UtilityConfigResponse, summary="Update utility configuration")
async def update_config(config_id: str, request: UtilityConfigUpdateRequest):
    """
    Update an existing utility configuration.
    
    - **config_id**: Unique identifier of the configuration
    - **request**: Updated configuration data
    """
    try:
        config = await utility_service.update_config(
            config_id=config_id,
            name=request.name,
            category=request.category,
            value=request.value,
            description=request.description,
            is_active=request.is_active
        )
        
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")


@router.delete("/configs/{config_id}", response_model=UtilityOperationResponse, summary="Delete utility configuration")
async def delete_config(config_id: str):
    """
    Delete a utility configuration.
    
    - **config_id**: Unique identifier of the configuration
    """
    try:
        success = await utility_service.delete_config(config_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return UtilityOperationResponse(
            success=True,
            message="Configuration deleted successfully",
            config_id=config_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration deletion failed: {str(e)}")


@router.get("/configs", response_model=UtilityConfigListResponse, summary="List utility configurations")
async def list_configs(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of configurations to return")
):
    """
    List utility configurations with optional filtering.
    
    - **category**: Optional category filter
    - **is_active**: Optional active status filter
    - **limit**: Maximum number of configurations to return (1-1000)
    """
    try:
        configs = await utility_service.list_configs(
            category=category,
            is_active=is_active,
            limit=limit
        )
        
        return UtilityConfigListResponse(
            configurations=configs,
            total_count=len(configs),
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Configuration listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration listing failed: {str(e)}")


@router.get("/system/info", response_model=SystemInfoResponse, summary="Get system information")
async def get_system_info():
    """
    Get comprehensive system information and statistics.
    """
    try:
        system_info = await utility_service.get_system_info()
        
        if "error" in system_info:
            raise HTTPException(status_code=500, detail=system_info["error"])
        
        return system_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"System info retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"System info retrieval failed: {str(e)}")


@router.get("/health", response_model=HealthCheckResponse, summary="Health check")
async def health_check():
    """
    Perform a comprehensive health check of the system.
    """
    try:
        health_status = await utility_service.health_check()
        
        if "error" in health_status:
            raise HTTPException(status_code=500, detail=health_status["error"])
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/execute", response_model=CommandExecuteResponse, summary="Execute system command")
async def execute_command(request: CommandExecuteRequest):
    """
    Execute a system command (with safety restrictions).
    
    - **command**: Command to execute
    - **timeout**: Command timeout in seconds (1-300)
    """
    try:
        result = await utility_service.execute_command(
            command=request.command,
            timeout=request.timeout
        )
        
        return CommandExecuteResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Command execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")


@router.get("/ping", summary="Simple ping endpoint")
async def ping():
    """
    Simple ping endpoint to check if the service is running.
    """
    return {"message": "pong", "status": "healthy", "service": "utility"}


@router.get("/version", summary="Get service version")
async def get_version():
    """
    Get the current version of the utility service.
    """
    return {
        "service": "utility",
        "version": "1.0.0",
        "status": "active"
    }


@router.get("/configs/categories", summary="Get configuration categories")
async def get_config_categories():
    """
    Get a list of all available configuration categories.
    """
    try:
        configs = await utility_service.list_configs(limit=1000)
        
        # Extract unique categories
        categories = list(set(config.category for config in configs))
        categories.sort()
        
        return {
            "categories": categories,
            "total_count": len(categories)
        }
        
    except Exception as e:
        logger.error(f"Category listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Category listing failed: {str(e)}")


@router.get("/configs/{config_id}/history", summary="Get configuration history")
async def get_config_history(config_id: str):
    """
    Get the history of changes for a specific configuration.
    
    - **config_id**: Unique identifier of the configuration
    """
    try:
        # This would typically query a history/audit log
        # For now, we'll return basic information
        config = await utility_service.read_config(config_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return {
            "config_id": config_id,
            "current_value": config.value,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
            "message": "History tracking not yet implemented"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration history retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration history retrieval failed: {str(e)}")
