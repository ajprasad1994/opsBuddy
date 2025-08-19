"""
API models package for OpsBuddy application.
Contains Pydantic models for request/response validation.
"""

# File Service Models
from .file_models import (
    FileUploadRequest,
    FileUpdateRequest,
    FileListRequest,
    FileMetadataResponse,
    FileContentResponse,
    FileListResponse,
    FileOperationResponse,
    FileErrorResponse
)

# Utility Service Models
from .utility_models import (
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

# Analytics Service Models
from .analytics_models import (
    AnalyticsMetricCreateRequest,
    AnalyticsMetricUpdateRequest,
    AnalyticsMetricResponse,
    AnalyticsMetricListRequest,
    AnalyticsMetricListResponse,
    MetricStatisticsRequest,
    MetricStatisticsResponse,
    MetricAggregationRequest,
    MetricAggregationResponse,
    MetricTrendsRequest,
    MetricTrendsResponse,
    AnalyticsOperationResponse,
    AnalyticsErrorResponse
)

__all__ = [
    # File Service Models
    "FileUploadRequest",
    "FileUpdateRequest",
    "FileListRequest",
    "FileMetadataResponse",
    "FileContentResponse",
    "FileListResponse",
    "FileOperationResponse",
    "FileErrorResponse",
    
    # Utility Service Models
    "UtilityConfigCreateRequest",
    "UtilityConfigUpdateRequest",
    "UtilityConfigResponse",
    "UtilityConfigListRequest",
    "UtilityConfigListResponse",
    "SystemInfoResponse",
    "HealthCheckResponse",
    "CommandExecuteRequest",
    "CommandExecuteResponse",
    "UtilityOperationResponse",
    "UtilityErrorResponse",
    
    # Analytics Service Models
    "AnalyticsMetricCreateRequest",
    "AnalyticsMetricUpdateRequest",
    "AnalyticsMetricResponse",
    "AnalyticsMetricListRequest",
    "AnalyticsMetricListResponse",
    "MetricStatisticsRequest",
    "MetricStatisticsResponse",
    "MetricAggregationRequest",
    "MetricAggregationResponse",
    "MetricTrendsRequest",
    "MetricTrendsResponse",
    "AnalyticsOperationResponse",
    "AnalyticsErrorResponse"
]
