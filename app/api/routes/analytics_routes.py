"""
Analytics Service API routes for OpsBuddy application.
Provides REST endpoints for analytics operations and metrics.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.analytics_service import analytics_service
from app.api.models.analytics_models import (
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
from app.utils.logger import get_logger

logger = get_logger("analytics_routes")

router = APIRouter(prefix="/analytics", tags=["Analytics Service"])


@router.post("/metrics", response_model=AnalyticsMetricResponse, summary="Create analytics metric")
async def create_metric(request: AnalyticsMetricCreateRequest):
    """
    Create a new analytics metric.
    
    - **name**: Metric name
    - **value**: Metric value
    - **unit**: Metric unit
    - **category**: Metric category
    - **tags**: Optional metric tags
    - **metadata**: Optional additional metadata
    """
    try:
        metric = await analytics_service.create_metric(
            name=request.name,
            value=request.value,
            unit=request.unit,
            category=request.category,
            tags=request.tags,
            metadata=request.metadata
        )
        
        if not metric:
            raise HTTPException(status_code=500, detail="Failed to create metric")
        
        return metric
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric creation failed: {str(e)}")


@router.get("/metrics/{metric_id}", response_model=AnalyticsMetricResponse, summary="Get analytics metric")
async def get_metric(metric_id: str):
    """
    Get an analytics metric by ID.
    
    - **metric_id**: Unique identifier of the metric
    """
    try:
        metric = await analytics_service.read_metric(metric_id)
        
        if not metric:
            raise HTTPException(status_code=404, detail="Metric not found")
        
        return metric
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric retrieval failed: {str(e)}")


@router.put("/metrics/{metric_id}", response_model=AnalyticsMetricResponse, summary="Update analytics metric")
async def update_metric(metric_id: str, request: AnalyticsMetricUpdateRequest):
    """
    Update an existing analytics metric.
    
    - **metric_id**: Unique identifier of the metric
    - **request**: Updated metric data
    """
    try:
        metric = await analytics_service.update_metric(
            metric_id=metric_id,
            name=request.name,
            value=request.value,
            unit=request.unit,
            category=request.category,
            tags=request.tags,
            metadata=request.metadata
        )
        
        if not metric:
            raise HTTPException(status_code=404, detail="Metric not found")
        
        return metric
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric update failed: {str(e)}")


@router.delete("/metrics/{metric_id}", response_model=AnalyticsOperationResponse, summary="Delete analytics metric")
async def delete_metric(metric_id: str):
    """
    Delete an analytics metric.
    
    - **metric_id**: Unique identifier of the metric
    """
    try:
        success = await analytics_service.delete_metric(metric_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Metric not found")
        
        return AnalyticsOperationResponse(
            success=True,
            message="Metric deleted successfully",
            metric_id=metric_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric deletion failed: {str(e)}")


@router.get("/metrics", response_model=AnalyticsMetricListResponse, summary="List analytics metrics")
async def list_metrics(
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Filter by tags (JSON string)"),
    start_time: Optional[str] = Query(None, description="Start time filter (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time filter (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of metrics to return")
):
    """
    List analytics metrics with optional filtering.
    
    - **category**: Optional category filter
    - **tags**: Optional JSON string of tags to filter by
    - **start_time**: Optional start time filter in ISO format
    - **end_time**: Optional end time filter in ISO format
    - **limit**: Maximum number of metrics to return (1-1000)
    """
    try:
        # Parse tags if provided
        metric_tags = None
        if tags:
            import json
            try:
                metric_tags = json.loads(tags)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid tags JSON format")
        
        # Parse time filters if provided
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format.")
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format.")
        
        metrics = await analytics_service.list_metrics(
            category=category,
            tags=metric_tags,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit
        )
        
        return AnalyticsMetricListResponse(
            metrics=metrics,
            total_count=len(metrics),
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric listing failed: {str(e)}")


@router.post("/metrics/statistics", response_model=MetricStatisticsResponse, summary="Get metric statistics")
async def get_metric_statistics(request: MetricStatisticsRequest):
    """
    Get statistical information for a specific metric.
    
    - **name**: Metric name
    - **category**: Optional metric category
    - **tags**: Optional metric tags
    - **time_range**: Time range for statistics (1h, 6h, 24h, 7d, 30d)
    """
    try:
        stats = await analytics_service.get_metric_statistics(
            name=request.name,
            category=request.category,
            tags=request.tags,
            time_range=request.time_range
        )
        
        if "error" in stats:
            raise HTTPException(status_code=400, detail=stats["error"])
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric statistics failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric statistics failed: {str(e)}")


@router.post("/metrics/aggregate", response_model=MetricAggregationResponse, summary="Aggregate metrics")
async def aggregate_metrics(request: MetricAggregationRequest):
    """
    Aggregate metrics over time intervals.
    
    - **category**: Metric category
    - **aggregation**: Aggregation function (sum, avg, min, max, count)
    - **time_interval**: Time interval for aggregation (1m, 5m, 15m, 1h, 6h, 1d)
    - **tags**: Optional metric tags
    - **start_time**: Optional start time for aggregation
    - **end_time**: Optional end time for aggregation
    """
    try:
        aggregated_data = await analytics_service.aggregate_metrics(
            category=request.category,
            aggregation=request.aggregation,
            time_interval=request.time_interval,
            tags=request.tags,
            start_time=request.start_time,
            end_time=request.end_time
        )
        
        return MetricAggregationResponse(
            category=request.category,
            aggregation=request.aggregation,
            time_interval=request.time_interval,
            data=aggregated_data,
            total_intervals=len(aggregated_data)
        )
        
    except Exception as e:
        logger.error(f"Metric aggregation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric aggregation failed: {str(e)}")


@router.post("/metrics/trends", response_model=MetricTrendsResponse, summary="Get metric trends")
async def get_metric_trends(request: MetricTrendsRequest):
    """
    Get trend analysis for a specific metric.
    
    - **name**: Metric name
    - **category**: Optional metric category
    - **tags**: Optional metric tags
    - **time_range**: Time range for trend analysis (1h, 6h, 24h, 7d, 30d)
    """
    try:
        trends = await analytics_service.get_metric_trends(
            name=request.name,
            category=request.category,
            tags=request.tags,
            time_range=request.time_range
        )
        
        if "error" in trends:
            raise HTTPException(status_code=400, detail=trends["error"])
        
        return trends
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric trends failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric trends failed: {str(e)}")


@router.get("/metrics/categories", summary="Get metric categories")
async def get_metric_categories():
    """
    Get a list of all available metric categories.
    """
    try:
        metrics = await analytics_service.list_metrics(limit=1000)
        
        # Extract unique categories
        categories = list(set(metric.category for metric in metrics))
        categories.sort()
        
        return {
            "categories": categories,
            "total_count": len(categories)
        }
        
    except Exception as e:
        logger.error(f"Category listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Category listing failed: {str(e)}")


@router.get("/metrics/names", summary="Get metric names")
async def get_metric_names(category: Optional[str] = Query(None, description="Filter by category")):
    """
    Get a list of all available metric names, optionally filtered by category.
    
    - **category**: Optional category filter
    """
    try:
        metrics = await analytics_service.list_metrics(category=category, limit=1000)
        
        # Extract unique names
        names = list(set(metric.name for metric in metrics))
        names.sort()
        
        return {
            "names": names,
            "total_count": len(names),
            "category": category
        }
        
    except Exception as e:
        logger.error(f"Metric names listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric names listing failed: {str(e)}")


@router.get("/metrics/{metric_id}/history", summary="Get metric history")
async def get_metric_history(
    metric_id: str,
    start_time: Optional[str] = Query(None, description="Start time filter (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time filter (ISO format)")
):
    """
    Get the history of a specific metric over time.
    
    - **metric_id**: Unique identifier of the metric
    - **start_time**: Optional start time filter in ISO format
    - **end_time**: Optional end time filter in ISO format
    """
    try:
        # Get the metric first
        metric = await analytics_service.read_metric(metric_id)
        
        if not metric:
            raise HTTPException(status_code=404, detail="Metric not found")
        
        # Parse time filters if provided
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format.")
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format.")
        
        # Get historical data
        history = await analytics_service.list_metrics(
            category=metric.category,
            tags={"metric_id": metric_id},
            start_time=start_dt,
            end_time=end_dt,
            limit=1000
        )
        
        return {
            "metric_id": metric_id,
            "metric_name": metric.name,
            "category": metric.category,
            "history": history,
            "total_points": len(history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric history retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metric history retrieval failed: {str(e)}")


@router.get("/ping", summary="Simple ping endpoint")
async def ping():
    """
    Simple ping endpoint to check if the service is running.
    """
    return {"message": "pong", "status": "healthy", "service": "analytics"}


@router.get("/version", summary="Get service version")
async def get_version():
    """
    Get the current version of the analytics service.
    """
    return {
        "service": "analytics",
        "version": "1.0.0",
        "status": "active"
    }
