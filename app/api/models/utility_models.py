"""
Pydantic models for Utility Service API.
Defines request/response schemas for utility operations.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator


class UtilityConfigCreateRequest(BaseModel):
    """Request model for creating utility configuration."""
    
    name: str = Field(..., description="Configuration name")
    category: str = Field(..., description="Configuration category")
    value: Any = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Configuration description")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Configuration name cannot be empty')
        if len(v) > 100:
            raise ValueError('Configuration name too long (max 100 characters)')
        return v.strip()
    
    @validator('category')
    def validate_category(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Configuration category cannot be empty')
        if len(v) > 50:
            raise ValueError('Configuration category too long (max 50 characters)')
        return v.strip()


class UtilityConfigUpdateRequest(BaseModel):
    """Request model for updating utility configuration."""
    
    name: Optional[str] = Field(None, description="New configuration name")
    category: Optional[str] = Field(None, description="New configuration category")
    value: Optional[Any] = Field(None, description="New configuration value")
    description: Optional[str] = Field(None, description="New configuration description")
    is_active: Optional[bool] = Field(None, description="Whether configuration is active")
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Configuration name cannot be empty')
            if len(v) > 100:
                raise ValueError('Configuration name too long (max 100 characters)')
            return v.strip()
        return v
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Configuration category cannot be empty')
            if len(v) > 50:
                raise ValueError('Configuration category too long (max 50 characters)')
            return v.strip()
        return v


class UtilityConfigResponse(BaseModel):
    """Response model for utility configuration."""
    
    config_id: str = Field(..., description="Unique configuration identifier")
    name: str = Field(..., description="Configuration name")
    category: str = Field(..., description="Configuration category")
    value: Any = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Configuration description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(..., description="Whether configuration is active")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UtilityConfigListRequest(BaseModel):
    """Request model for listing utility configurations."""
    
    category: Optional[str] = Field(None, description="Filter by category")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of configurations to return")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1:
            raise ValueError('Limit must be at least 1')
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v


class UtilityConfigListResponse(BaseModel):
    """Response model for utility configuration listing."""
    
    configurations: List[UtilityConfigResponse] = Field(..., description="List of configurations")
    total_count: int = Field(..., description="Total number of configurations")
    limit: int = Field(..., description="Limit used for the query")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemInfoResponse(BaseModel):
    """Response model for system information."""
    
    platform: str = Field(..., description="Operating system platform")
    platform_version: str = Field(..., description="Platform version")
    architecture: str = Field(..., description="System architecture")
    processor: str = Field(..., description="Processor information")
    hostname: str = Field(..., description="System hostname")
    python_version: str = Field(..., description="Python version")
    cpu_count: int = Field(..., description="Number of CPU cores")
    memory_total: int = Field(..., description="Total memory in bytes")
    memory_available: int = Field(..., description="Available memory in bytes")
    disk_usage: float = Field(..., description="Disk usage percentage")
    uptime: float = Field(..., description="Service uptime in seconds")


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    database: str = Field(..., description="Database connection status")
    system: SystemInfoResponse = Field(..., description="System information")
    uptime: float = Field(..., description="Service uptime in seconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CommandExecuteRequest(BaseModel):
    """Request model for command execution."""
    
    command: str = Field(..., description="Command to execute")
    timeout: int = Field(30, ge=1, le=300, description="Command timeout in seconds")
    
    @validator('command')
    def validate_command(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Command cannot be empty')
        if len(v) > 1000:
            raise ValueError('Command too long (max 1000 characters)')
        return v.strip()
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v < 1:
            raise ValueError('Timeout must be at least 1 second')
        if v > 300:
            raise ValueError('Timeout cannot exceed 300 seconds')
        return v


class CommandExecuteResponse(BaseModel):
    """Response model for command execution."""
    
    command: str = Field(..., description="Executed command")
    return_code: int = Field(..., description="Command return code")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    success: bool = Field(..., description="Whether command executed successfully")
    execution_time: Optional[float] = Field(None, description="Command execution time in seconds")


class UtilityOperationResponse(BaseModel):
    """Generic response model for utility operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    config_id: Optional[str] = Field(None, description="Configuration ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UtilityErrorResponse(BaseModel):
    """Error response model for utility operations."""
    
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
