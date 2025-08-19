"""
Database models for OpsBuddy application.
Defines data structures for different service operations.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class TimeSeriesData(BaseModel):
    """Base model for time-series data."""
    
    measurement: str = Field(..., description="Measurement name")
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags for the data point")
    fields: Dict[str, Any] = Field(..., description="Fields/values for the data point")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the data point")


class FileMetadata(BaseModel):
    """Model for file metadata."""
    
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File extension/type")
    upload_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Upload timestamp")
    tags: Dict[str, str] = Field(default_factory=dict, description="File tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class UtilityConfig(BaseModel):
    """Model for utility configuration."""
    
    config_id: str = Field(..., description="Unique configuration identifier")
    name: str = Field(..., description="Configuration name")
    category: str = Field(..., description="Configuration category")
    value: Any = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Configuration description")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    is_active: bool = Field(default=True, description="Whether configuration is active")


class AnalyticsMetric(BaseModel):
    """Model for analytics metrics."""
    
    metric_id: str = Field(..., description="Unique metric identifier")
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit")
    category: str = Field(..., description="Metric category")
    tags: Dict[str, str] = Field(default_factory=dict, description="Metric tags")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Metric timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DatabaseQuery(BaseModel):
    """Model for database queries."""
    
    query: str = Field(..., description="Database query string")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    timeout: Optional[int] = Field(30, description="Query timeout in seconds")


class DatabaseResponse(BaseModel):
    """Model for database operation responses."""
    
    success: bool = Field(..., description="Operation success status")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Query results")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class HealthCheck(BaseModel):
    """Model for health check responses."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Health check timestamp")
    version: str = Field(..., description="Service version")
    database_status: str = Field(..., description="Database connection status")
    uptime: float = Field(..., description="Service uptime in seconds")
