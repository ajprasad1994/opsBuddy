"""
Pydantic models for Analytics Service API.
Defines request/response schemas for analytics operations.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator


class AnalyticsMetricCreateRequest(BaseModel):
    """Request model for creating analytics metric."""
    
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit")
    category: str = Field(..., description="Metric category")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Metric tags")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Metric name cannot be empty')
        if len(v) > 100:
            raise ValueError('Metric name too long (max 100 characters)')
        return v.strip()
    
    @validator('category')
    def validate_category(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Metric category cannot be empty')
        if len(v) > 50:
            raise ValueError('Metric category too long (max 50 characters)')
        return v.strip()
    
    @validator('unit')
    def validate_unit(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Metric unit cannot be empty')
        if len(v) > 20:
            raise ValueError('Metric unit too long (max 20 characters)')
        return v.strip()
    
    @validator('value')
    def validate_value(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError('Metric value must be a number')
        return float(v)


class AnalyticsMetricUpdateRequest(BaseModel):
    """Request model for updating analytics metric."""
    
    name: Optional[str] = Field(None, description="New metric name")
    value: Optional[float] = Field(None, description="New metric value")
    unit: Optional[str] = Field(None, description="New metric unit")
    category: Optional[str] = Field(None, description="New metric category")
    tags: Optional[Dict[str, str]] = Field(None, description="New metric tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="New metadata")
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Metric name cannot be empty')
            if len(v) > 100:
                raise ValueError('Metric name too long (max 100 characters)')
            return v.strip()
        return v
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Metric category cannot be empty')
            if len(v) > 50:
                raise ValueError('Metric category too long (max 50 characters)')
            return v.strip()
        return v
    
    @validator('unit')
    def validate_unit(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Metric unit cannot be empty')
            if len(v) > 20:
                raise ValueError('Metric unit too long (max 20 characters)')
            return v.strip()
        return v
    
    @validator('value')
    def validate_value(cls, v):
        if v is not None:
            if not isinstance(v, (int, float)):
                raise ValueError('Metric value must be a number')
            return float(v)
        return v


class AnalyticsMetricResponse(BaseModel):
    """Response model for analytics metric."""
    
    metric_id: str = Field(..., description="Unique metric identifier")
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit")
    category: str = Field(..., description="Metric category")
    tags: Dict[str, str] = Field(default_factory=dict, description="Metric tags")
    timestamp: datetime = Field(..., description="Metric timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnalyticsMetricListRequest(BaseModel):
    """Request model for listing analytics metrics."""
    
    category: Optional[str] = Field(None, description="Filter by category")
    tags: Optional[Dict[str, str]] = Field(None, description="Filter by tags")
    start_time: Optional[datetime] = Field(None, description="Start time for filtering")
    end_time: Optional[datetime] = Field(None, description="End time for filtering")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of metrics to return")
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1:
            raise ValueError('Limit must be at least 1')
        if v > 1000:
            raise ValueError('Limit cannot exceed 1000')
        return v


class AnalyticsMetricListResponse(BaseModel):
    """Response model for analytics metric listing."""
    
    metrics: List[AnalyticsMetricResponse] = Field(..., description="List of metrics")
    total_count: int = Field(..., description="Total number of metrics")
    limit: int = Field(..., description="Limit used for the query")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetricStatisticsRequest(BaseModel):
    """Request model for metric statistics."""
    
    name: str = Field(..., description="Metric name")
    category: Optional[str] = Field(None, description="Metric category")
    tags: Optional[Dict[str, str]] = Field(None, description="Metric tags")
    time_range: str = Field("24h", description="Time range for statistics")
    
    @validator('time_range')
    def validate_time_range(cls, v):
        allowed_ranges = ["1h", "6h", "24h", "7d", "30d"]
        if v not in allowed_ranges:
            raise ValueError(f'Time range must be one of: {", ".join(allowed_ranges)}')
        return v


class MetricStatisticsResponse(BaseModel):
    """Response model for metric statistics."""
    
    metric_name: str = Field(..., description="Metric name")
    time_range: str = Field(..., description="Time range used")
    start_time: str = Field(..., description="Start time of range")
    end_time: str = Field(..., description="End time of range")
    count: int = Field(..., description="Number of data points")
    statistics: Dict[str, float] = Field(..., description="Statistical values")


class MetricAggregationRequest(BaseModel):
    """Request model for metric aggregation."""
    
    category: str = Field(..., description="Metric category")
    aggregation: str = Field("sum", description="Aggregation function")
    time_interval: str = Field("1h", description="Time interval for aggregation")
    tags: Optional[Dict[str, str]] = Field(None, description="Metric tags")
    start_time: Optional[datetime] = Field(None, description="Start time for aggregation")
    end_time: Optional[datetime] = Field(None, description="End time for aggregation")
    
    @validator('aggregation')
    def validate_aggregation(cls, v):
        allowed_aggregations = ["sum", "avg", "min", "max", "count"]
        if v not in allowed_aggregations:
            raise ValueError(f'Aggregation must be one of: {", ".join(allowed_aggregations)}')
        return v
    
    @validator('time_interval')
    def validate_time_interval(cls, v):
        allowed_intervals = ["1m", "5m", "15m", "1h", "6h", "1d"]
        if v not in allowed_intervals:
            raise ValueError(f'Time interval must be one of: {", ".join(allowed_intervals)}')
        return v


class MetricAggregationResponse(BaseModel):
    """Response model for metric aggregation."""
    
    category: str = Field(..., description="Metric category")
    aggregation: str = Field(..., description="Aggregation function used")
    time_interval: str = Field(..., description="Time interval used")
    data: List[Dict[str, Any]] = Field(..., description="Aggregated data points")
    total_intervals: int = Field(..., description="Total number of intervals")


class MetricTrendsRequest(BaseModel):
    """Request model for metric trends."""
    
    name: str = Field(..., description="Metric name")
    category: Optional[str] = Field(None, description="Metric category")
    tags: Optional[Dict[str, str]] = Field(None, description="Metric tags")
    time_range: str = Field("7d", description="Time range for trend analysis")
    
    @validator('time_range')
    def validate_time_range(cls, v):
        allowed_ranges = ["1h", "6h", "24h", "7d", "30d"]
        if v not in allowed_ranges:
            raise ValueError(f'Time range must be one of: {", ".join(allowed_ranges)}')
        return v


class MetricTrendsResponse(BaseModel):
    """Response model for metric trends."""
    
    metric_name: str = Field(..., description="Metric name")
    time_range: str = Field(..., description="Time range used")
    trend_direction: str = Field(..., description="Trend direction")
    trend_strength: str = Field(..., description="Trend strength")
    slope: float = Field(..., description="Trend slope")
    change_percentage: float = Field(..., description="Percentage change")
    start_value: float = Field(..., description="Starting value")
    end_value: float = Field(..., description="Ending value")
    data_points: int = Field(..., description="Number of data points")
    aggregated_data: List[Dict[str, Any]] = Field(..., description="Aggregated data for trend")


class AnalyticsOperationResponse(BaseModel):
    """Generic response model for analytics operations."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    metric_id: Optional[str] = Field(None, description="Metric ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnalyticsErrorResponse(BaseModel):
    """Error response model for analytics operations."""
    
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
