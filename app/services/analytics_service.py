"""
Analytics Service for OpsBuddy application.
Handles analytics metrics, data aggregation, and reporting.
"""

import uuid
import statistics
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from app.database import db_manager, AnalyticsMetric
from app.utils.logger import get_logger, log_operation


logger = get_logger("analytics_service")


class AnalyticsService:
    """Service for managing analytics operations and metrics."""
    
    def __init__(self):
        self.metric_cache = {}
    
    async def create_metric(self, name: str, value: float, unit: str, category: str, tags: Dict[str, str] = None, metadata: Dict[str, Any] = None) -> Optional[AnalyticsMetric]:
        """Create a new analytics metric."""
        try:
            metric_id = str(uuid.uuid4())
            
            metric = AnalyticsMetric(
                metric_id=metric_id,
                name=name,
                value=value,
                unit=unit,
                category=category,
                tags=tags or {},
                metadata=metadata or {}
            )
            
            # Store metric in database
            success = await self._store_metric(metric)
            if not success:
                raise Exception("Failed to store metric in database")
            
            # Update cache
            self._update_cache(metric)
            
            log_operation("create", "analytics_service", {
                "metric_id": metric_id,
                "name": name,
                "value": value,
                "category": category
            })
            
            return metric
            
        except Exception as e:
            logger.error(f"Failed to create analytics metric {name}: {str(e)}")
            log_operation("create", "analytics_service", {
                "status": "failed",
                "error": str(e),
                "name": name
            }, "ERROR")
            raise
    
    async def read_metric(self, metric_id: str) -> Optional[AnalyticsMetric]:
        """Read an analytics metric by ID."""
        try:
            metric = await self._get_metric(metric_id)
            if metric:
                log_operation("read", "analytics_service", {"metric_id": metric_id})
            return metric
            
        except Exception as e:
            logger.error(f"Failed to read analytics metric {metric_id}: {str(e)}")
            log_operation("read", "analytics_service", {
                "status": "failed",
                "error": str(e),
                "metric_id": metric_id
            }, "ERROR")
            return None
    
    async def update_metric(self, metric_id: str, name: str = None, value: float = None, unit: str = None, category: str = None, tags: Dict[str, str] = None, metadata: Dict[str, Any] = None) -> Optional[AnalyticsMetric]:
        """Update an analytics metric."""
        try:
            metric = await self._get_metric(metric_id)
            if not metric:
                raise ValueError(f"Metric with ID {metric_id} not found")
            
            # Update fields if provided
            if name is not None:
                metric.name = name
            if value is not None:
                metric.value = value
            if unit is not None:
                metric.unit = unit
            if category is not None:
                metric.category = category
            if tags is not None:
                metric.tags.update(tags)
            if metadata is not None:
                metric.metadata.update(metadata)
            
            metric.timestamp = datetime.now(timezone.utc)
            
            # Update in database
            success = await self._update_metric(metric)
            if not success:
                raise Exception("Failed to update metric in database")
            
            # Update cache
            self._update_cache(metric)
            
            log_operation("update", "analytics_service", {
                "metric_id": metric_id,
                "fields_updated": {
                    "name": name is not None,
                    "value": value is not None,
                    "unit": unit is not None,
                    "category": category is not None,
                    "tags": tags is not None,
                    "metadata": metadata is not None
                }
            })
            
            return metric
            
        except Exception as e:
            logger.error(f"Failed to update analytics metric {metric_id}: {str(e)}")
            log_operation("update", "analytics_service", {
                "status": "failed",
                "error": str(e),
                "metric_id": metric_id
            }, "ERROR")
            raise
    
    async def delete_metric(self, metric_id: str) -> bool:
        """Delete an analytics metric."""
        try:
            metric = await self._get_metric(metric_id)
            if not metric:
                raise ValueError(f"Metric with ID {metric_id} not found")
            
            # Delete from database
            success = await self._delete_metric(metric_id)
            if not success:
                raise Exception("Failed to delete metric from database")
            
            # Remove from cache
            self._remove_from_cache(metric_id)
            
            log_operation("delete", "analytics_service", {"metric_id": metric_id})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete analytics metric {metric_id}: {str(e)}")
            log_operation("delete", "analytics_service", {
                "status": "failed",
                "error": str(e),
                "metric_id": metric_id
            }, "ERROR")
            raise
    
    async def list_metrics(self, category: str = None, tags: Dict[str, str] = None, start_time: datetime = None, end_time: datetime = None, limit: int = 100) -> List[AnalyticsMetric]:
        """List analytics metrics with optional filtering."""
        try:
            # Query database for metrics
            query = "SELECT * FROM analytics_metric"
            conditions = []
            
            if category:
                conditions.append(f"category = '{category}'")
            
            if tags:
                for key, value in tags.items():
                    conditions.append(f"tags['{key}'] = '{value}'")
            
            if start_time:
                start_timestamp = int(start_time.timestamp() * 1e9)
                conditions.append(f"time >= {start_timestamp}")
            
            if end_time:
                end_timestamp = int(end_time.timestamp() * 1e9)
                conditions.append(f"time <= {end_timestamp}")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += f" ORDER BY time DESC LIMIT {limit}"
            
            results = await db_manager.query_data(query)
            
            # Convert results to AnalyticsMetric objects
            metrics = []
            for result in results:
                try:
                    metric = AnalyticsMetric(**result)
                    metrics.append(metric)
                except Exception as e:
                    logger.warning(f"Failed to parse analytics metric: {str(e)}")
            
            log_operation("list", "analytics_service", {
                "count": len(metrics),
                "filters": {"category": category, "tags": tags, "start_time": start_time, "end_time": end_time, "limit": limit}
            })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to list analytics metrics: {str(e)}")
            log_operation("list", "analytics_service", {
                "status": "failed",
                "error": str(e)
            }, "ERROR")
            return []
    
    async def get_metric_statistics(self, name: str, category: str = None, tags: Dict[str, str] = None, time_range: str = "24h") -> Dict[str, Any]:
        """Get statistical information for a specific metric."""
        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            if time_range == "1h":
                start_time = end_time - timedelta(hours=1)
            elif time_range == "6h":
                start_time = end_time - timedelta(hours=6)
            elif time_range == "24h":
                start_time = end_time - timedelta(days=1)
            elif time_range == "7d":
                start_time = end_time - timedelta(days=7)
            elif time_range == "30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=1)
            
            # Get metrics for the time range
            metrics = await self.list_metrics(
                category=category,
                tags=tags,
                start_time=start_time,
                end_time=end_time,
                limit=1000
            )
            
            # Filter by name if specified
            if name:
                metrics = [m for m in metrics if m.name == name]
            
            if not metrics:
                return {
                    "metric_name": name,
                    "time_range": time_range,
                    "count": 0,
                    "statistics": {}
                }
            
            # Calculate statistics
            values = [m.value for m in metrics]
            stats = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "sum": sum(values)
            }
            
            # Add percentiles
            if len(values) > 1:
                sorted_values = sorted(values)
                stats["p25"] = sorted_values[int(len(sorted_values) * 0.25)]
                stats["p75"] = sorted_values[int(len(sorted_values) * 0.75)]
                stats["p90"] = sorted_values[int(len(sorted_values) * 0.90)]
                stats["p95"] = sorted_values[int(len(sorted_values) * 0.95)]
                stats["p99"] = sorted_values[int(len(sorted_values) * 0.99)]
            
            result = {
                "metric_name": name,
                "time_range": time_range,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "count": len(values),
                "statistics": stats
            }
            
            log_operation("statistics", "analytics_service", {
                "metric_name": name,
                "time_range": time_range,
                "count": len(values)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get metric statistics: {str(e)}")
            log_operation("statistics", "analytics_service", {
                "status": "failed",
                "error": str(e),
                "metric_name": name
            }, "ERROR")
            return {"error": str(e)}
    
    async def aggregate_metrics(self, category: str, aggregation: str = "sum", time_interval: str = "1h", tags: Dict[str, str] = None, start_time: datetime = None, end_time: datetime = None) -> List[Dict[str, Any]]:
        """Aggregate metrics over time intervals."""
        try:
            # Set default time range if not specified
            if not end_time:
                end_time = datetime.now(timezone.utc)
            if not start_time:
                start_time = end_time - timedelta(days=1)
            
            # Get metrics for the time range
            metrics = await self.list_metrics(
                category=category,
                tags=tags,
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            
            if not metrics:
                return []
            
            # Group metrics by time interval
            grouped_metrics = {}
            for metric in metrics:
                # Round timestamp to interval
                if time_interval == "1m":
                    interval_time = metric.timestamp.replace(second=0, microsecond=0)
                elif time_interval == "5m":
                    interval_time = metric.timestamp.replace(minute=metric.timestamp.minute - metric.timestamp.minute % 5, second=0, microsecond=0)
                elif time_interval == "15m":
                    interval_time = metric.timestamp.replace(minute=metric.timestamp.minute - metric.timestamp.minute % 15, second=0, microsecond=0)
                elif time_interval == "1h":
                    interval_time = metric.timestamp.replace(minute=0, second=0, microsecond=0)
                elif time_interval == "6h":
                    interval_time = metric.timestamp.replace(hour=metric.timestamp.hour - metric.timestamp.hour % 6, minute=0, second=0, microsecond=0)
                elif time_interval == "1d":
                    interval_time = metric.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    interval_time = metric.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                
                if interval_time not in grouped_metrics:
                    grouped_metrics[interval_time] = []
                grouped_metrics[interval_time].append(metric.value)
            
            # Calculate aggregation for each interval
            aggregated_data = []
            for interval_time, values in grouped_metrics.items():
                if aggregation == "sum":
                    aggregated_value = sum(values)
                elif aggregation == "avg":
                    aggregated_value = statistics.mean(values)
                elif aggregation == "min":
                    aggregated_value = min(values)
                elif aggregation == "max":
                    aggregated_value = max(values)
                elif aggregation == "count":
                    aggregated_value = len(values)
                else:
                    aggregated_value = sum(values)
                
                aggregated_data.append({
                    "timestamp": interval_time.isoformat(),
                    "value": aggregated_value,
                    "count": len(values)
                })
            
            # Sort by timestamp
            aggregated_data.sort(key=lambda x: x["timestamp"])
            
            log_operation("aggregate", "analytics_service", {
                "category": category,
                "aggregation": aggregation,
                "time_interval": time_interval,
                "intervals": len(aggregated_data)
            })
            
            return aggregated_data
            
        except Exception as e:
            logger.error(f"Failed to aggregate metrics: {str(e)}")
            log_operation("aggregate", "analytics_service", {
                "status": "failed",
                "error": str(e),
                "category": category
            }, "ERROR")
            return []
    
    async def get_metric_trends(self, name: str, category: str = None, tags: Dict[str, str] = None, time_range: str = "7d") -> Dict[str, Any]:
        """Get trend analysis for a specific metric."""
        try:
            # Get aggregated data
            aggregated_data = await self.aggregate_metrics(
                category=category or "general",
                aggregation="avg",
                time_interval="1h",
                tags=tags,
                start_time=datetime.now(timezone.utc) - timedelta(days=7 if time_range == "7d" else 1),
                end_time=datetime.now(timezone.utc)
            )
            
            if not aggregated_data:
                return {"error": "No data available for trend analysis"}
            
            # Calculate trend
            values = [point["value"] for point in aggregated_data]
            if len(values) < 2:
                return {"error": "Insufficient data for trend analysis"}
            
            # Simple linear trend calculation
            x_values = list(range(len(values)))
            n = len(values)
            
            sum_x = sum(x_values)
            sum_y = sum(values)
            sum_xy = sum(x * y for x, y in zip(x_values, values))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
            
            # Calculate trend direction and strength
            if slope > 0.01:
                trend_direction = "increasing"
                trend_strength = "strong" if abs(slope) > 0.1 else "moderate"
            elif slope < -0.01:
                trend_direction = "decreasing"
                trend_strength = "strong" if abs(slope) > 0.1 else "moderate"
            else:
                trend_direction = "stable"
                trend_strength = "weak"
            
            # Calculate change percentage
            if values[0] != 0:
                change_percentage = ((values[-1] - values[0]) / values[0]) * 100
            else:
                change_percentage = 0
            
            result = {
                "metric_name": name,
                "time_range": time_range,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "slope": slope,
                "change_percentage": change_percentage,
                "start_value": values[0],
                "end_value": values[-1],
                "data_points": len(values),
                "aggregated_data": aggregated_data
            }
            
            log_operation("trends", "analytics_service", {
                "metric_name": name,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get metric trends: {str(e)}")
            log_operation("trends", "analytics_service", {
                "status": "failed",
                "error": str(e),
                "metric_name": name
            }, "ERROR")
            return {"error": str(e)}
    
    def _update_cache(self, metric: AnalyticsMetric):
        """Update the metric cache."""
        cache_key = f"{metric.category}:{metric.name}"
        if cache_key not in self.metric_cache:
            self.metric_cache[cache_key] = []
        self.metric_cache[cache_key].append(metric)
        
        # Keep only last 100 metrics per cache key
        if len(self.metric_cache[cache_key]) > 100:
            self.metric_cache[cache_key] = self.metric_cache[cache_key][-100:]
    
    def _remove_from_cache(self, metric_id: str):
        """Remove a metric from the cache."""
        for cache_key in list(self.metric_cache.keys()):
            self.metric_cache[cache_key] = [
                m for m in self.metric_cache[cache_key] 
                if m.metric_id != metric_id
            ]
            if not self.metric_cache[cache_key]:
                del self.metric_cache[cache_key]
    
    async def _store_metric(self, metric: AnalyticsMetric) -> bool:
        """Store analytics metric in the database."""
        try:
            tags = {
                "metric_id": metric.metric_id,
                "name": metric.name,
                "category": metric.category
            }
            tags.update(metric.tags)
            
            fields = {
                "value": metric.value,
                "unit": metric.unit,
                "metadata": str(metric.metadata)
            }
            
            return await db_manager.write_point(
                measurement="analytics_metric",
                tags=tags,
                fields=fields,
                timestamp=int(metric.timestamp.timestamp() * 1e9)
            )
            
        except Exception as e:
            logger.error(f"Failed to store analytics metric: {str(e)}")
            return False
    
    async def _get_metric(self, metric_id: str) -> Optional[AnalyticsMetric]:
        """Retrieve analytics metric from the database."""
        try:
            query = f'SELECT * FROM analytics_metric WHERE tags["metric_id"] = "{metric_id}" ORDER BY time DESC LIMIT 1'
            results = await db_manager.query_data(query)
            
            if results:
                result = results[0]
                return AnalyticsMetric(
                    metric_id=result.get("tags", {}).get("metric_id", metric_id),
                    name=result.get("tags", {}).get("name", ""),
                    value=result.get("fields", {}).get("value", 0.0),
                    unit=result.get("tags", {}).get("unit", ""),
                    category=result.get("tags", {}).get("category", ""),
                    tags={k: v for k, v in result.get("tags", {}).items() if k not in ["metric_id", "name", "category"]},
                    timestamp=datetime.fromisoformat(result.get("time", datetime.now(timezone.utc).isoformat())),
                    metadata=eval(result.get("fields", {}).get("metadata", "{}"))
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get analytics metric: {str(e)}")
            return None
    
    async def _update_metric(self, metric: AnalyticsMetric) -> bool:
        """Update analytics metric in the database."""
        try:
            # For time-series databases, we typically write a new point
            return await self._store_metric(metric)
            
        except Exception as e:
            logger.error(f"Failed to update analytics metric: {str(e)}")
            return False
    
    async def _delete_metric(self, metric_id: str) -> bool:
        """Delete analytics metric from the database."""
        try:
            return await db_manager.delete_data(
                measurement="analytics_metric",
                tags={"metric_id": metric_id}
            )
            
        except Exception as e:
            logger.error(f"Failed to delete analytics metric: {str(e)}")
            return False


# Global analytics service instance
analytics_service = AnalyticsService()
