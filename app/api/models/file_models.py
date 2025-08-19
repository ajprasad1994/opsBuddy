"""
Pydantic models for File Service API.
Defines request/response schemas for file operations.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator


class FileUploadRequest(BaseModel):
    """Request model for file upload."""
    
    filename: str = Field(..., description="Name of the file to upload")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="File tags")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Filename cannot be empty')
        if len(v) > 255:
            raise ValueError('Filename too long (max 255 characters)')
        return v.strip()


class FileUpdateRequest(BaseModel):
    """Request model for file update."""
    
    new_content: Optional[bytes] = Field(None, description="New file content")
    new_tags: Optional[Dict[str, str]] = Field(None, description="New file tags")
    new_metadata: Optional[Dict[str, Any]] = Field(None, description="New metadata")
    
    @validator('new_tags')
    def validate_tags(cls, v):
        if v is not None:
            for key, value in v.items():
                if not key or len(key.strip()) == 0:
                    raise ValueError('Tag key cannot be empty')
                if len(key) > 50:
                    raise ValueError('Tag key too long (max 50 characters)')
                if len(value) > 100:
                    raise ValueError('Tag value too long (max 100 characters)')
        return v


class FileListRequest(BaseModel):
    """Request model for listing files."""
    
    tags: Optional[Dict[str, str]] = Field(None, description="Filter by tags")
    file_type: Optional[str] = Field(None, description="Filter by file type")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of files to return")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1:
            raise ValueError('Limit must be at least 1')
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v


class FileMetadataResponse(BaseModel):
    """Response model for file metadata."""
    
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File extension/type")
    upload_time: datetime = Field(..., description="Upload timestamp")
    tags: Dict[str, str] = Field(default_factory=dict, description="File tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileContentResponse(BaseModel):
    """Response model for file content."""
    
    metadata: FileMetadataResponse = Field(..., description="File metadata")
    content: bytes = Field(..., description="File content")
    file_path: str = Field(..., description="File path on disk")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            bytes: lambda v: v.decode('utf-8', errors='ignore') if isinstance(v, bytes) else str(v)
        }


class FileListResponse(BaseModel):
    """Response model for file listing."""
    
    files: List[FileMetadataResponse] = Field(..., description="List of files")
    total_count: int = Field(..., description="Total number of files")
    limit: int = Field(..., description="Limit used for the query")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileOperationResponse(BaseModel):
    """Generic response model for file operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    file_id: Optional[str] = Field(None, description="File ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileErrorResponse(BaseModel):
    """Error response model for file operations."""
    
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
