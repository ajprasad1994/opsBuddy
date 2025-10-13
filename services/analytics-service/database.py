"""
InfluxDB integration for OpsBuddy Analytics Service.
Handles time-series data storage and querying.
"""

import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio

from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.query_api import QueryApi

from config import settings
from utils import get_logger

logger = get_logger("analytics_database")

class DatabaseManager:
    """Manages InfluxDB connections and operations."""

    def __init__(self):
        self._client: Optional[InfluxDBClient] = None
        self._connected: bool = False
        self._write_api = None
        self._query_api: Optional[QueryApi] = None

    async def connect(self) -> bool:
        """Connect to InfluxDB."""
        try:
            # Create InfluxDB client
            self._client = InfluxDBClient(**settings.influxdb_client_config)

            # Test connection
            health = self._client.health()
            if health.status != "pass":
                logger.error(f"InfluxDB health check failed: {health}")
                return False

            # Initialize APIs
            self._write_api = self._client.write_api(
                write_options=WriteOptions(
                    batch_size=settings.batch_size,
                    flush_interval=10_000,  # 10 seconds
                    retry_interval=5_000,   # 5 seconds
                )
            )
            self._query_api = self._client.query_api()

            self._connected = True
            logger.info("Successfully connected to InfluxDB")

            # Initialize database and buckets if needed
            await self._initialize_database()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {str(e)}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from InfluxDB."""
        try:
            if self._write_api:
                self._write_api.close()
            if self._client:
                self._client.close()
            self._connected = False
            logger.info("Disconnected from InfluxDB")
        except Exception as e:
            logger.error(f"Error disconnecting from InfluxDB: {str(e)}")

    async def _initialize_database(self):
        """Initialize database schema and buckets."""
        try:
            # Create buckets if they don't exist
            buckets_api = self._client.buckets_api()

            # Logs bucket
            logs_bucket = "opsbuddy-logs"
            if not buckets_api.find_bucket_by_name(logs_bucket):
                buckets_api.create_bucket(bucket_name=logs_bucket, org=settings.influxdb_org)
                logger.info(f"Created bucket: {logs_bucket}")

            # Metrics bucket
            metrics_bucket = "opsbuddy-metrics"
            if not buckets_api.find_bucket_by_name(metrics_bucket):
                buckets_api.create_bucket(bucket_name=metrics_bucket, org=settings.influxdb_org)
                logger.info(f"Created bucket: {metrics_bucket}")

        except Exception as e:
            logger.warning(f"Database initialization warning: {str(e)}")

    async def store_logs(self, logs: List[Dict[str, Any]]):
        """Store logs in InfluxDB."""
        if not self._connected or not self._write_api:
            logger.error("Cannot store logs: not connected to database")
            return

        try:
            points = []

            for log_entry in logs:
                # Create InfluxDB point for log entry
                point = Point("logs") \
                    .tag("service", log_entry.get("service", "unknown")) \
                    .tag("level", log_entry.get("level", "INFO")) \
                    .tag("logger", log_entry.get("logger", "unknown")) \
                    .tag("operation", log_entry.get("operation", "unknown")) \
                    .tag("host", log_entry.get("host", "unknown")) \
                    .field("message", log_entry.get("message", "")) \
                    .field("data_size", len(str(log_entry.get("data", {})))) \
                    .time(log_entry.get("timestamp"))

                # Add additional fields if present
                if log_entry.get("data"):
                    for key, value in log_entry["data"].items():
                        if isinstance(value, (int, float)):
                            point = point.field(f"data_{key}", float(value))
                        elif isinstance(value, str):
                            point = point.field(f"data_{key}", value)

                points.append(point)

            # Write points to database
            self._write_api.write(
                bucket="opsbuddy-logs",
                org=settings.influxdb_org,
                record=points
            )

            logger.debug(f"Stored {len(points)} log entries in InfluxDB")

        except Exception as e:
            logger.error(f"Failed to store logs in InfluxDB: {str(e)}")
            raise

    async def query_logs(self, filters: Dict[str, str] = None, start_time: str = None,
                        end_time: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query logs from InfluxDB."""
        if not self._connected or not self._query_api:
            logger.error("Cannot query logs: not connected to database")
            return []

        try:
            # Build Flux query
            query_parts = ['from(bucket: "opsbuddy-logs")']

            # Add time range
            if start_time:
                query_parts.append(f'start: {start_time}')
            else:
                # Default to last 24 hours
                start_time = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
                query_parts.append(f'start: {start_time}')

            if end_time:
                query_parts.append(f'stop: {end_time}')

            # Add filters
            if filters:
                for key, value in filters.items():
                    query_parts.append(f'filter(fn: (r) => r.{key} == "{value}")')

            # Add range and limit
            query_parts.append(f'range(start: -24h)')
            query_parts.append(f'limit(n: {min(limit, settings.max_query_limit)})')

            # Sort by time descending
            query_parts.append('sort(columns: ["_time"], desc: true)')

            flux_query = " |> ".join(query_parts)

            logger.debug(f"Executing Flux query: {flux_query}")

            # Execute query
            result = self._query_api.query(flux_query, org=settings.influxdb_org)

            # Process results
            logs = []
            for table in result:
                for record in table.records:
                    log_entry = {
                        "timestamp": record.get_time().isoformat(),
                        "service": record.values.get("service"),
                        "level": record.values.get("level"),
                        "logger": record.values.get("logger"),
                        "operation": record.values.get("operation"),
                        "host": record.values.get("host"),
                        "message": record.values.get("message"),
                        "_measurement": record.get_measurement(),
                        "_field": record.get_field()
                    }

                    # Add data fields
                    data_fields = {}
                    for key, value in record.values.items():
                        if key.startswith("data_"):
                            data_fields[key[5:]] = value  # Remove "data_" prefix

                    if data_fields:
                        log_entry["data"] = data_fields

                    logs.append(log_entry)

            logger.debug(f"Retrieved {len(logs)} log entries from InfluxDB")
            return logs

        except Exception as e:
            logger.error(f"Failed to query logs from InfluxDB: {str(e)}")
            raise

    async def query_metrics(self, metric: str, service: str = None, start_time: str = None,
                          end_time: str = None, aggregation: str = "mean",
                          group_by: str = None) -> List[Dict[str, Any]]:
        """Query metrics from InfluxDB."""
        if not self._connected or not self._query_api:
            logger.error("Cannot query metrics: not connected to database")
            return []

        try:
            # Build Flux query for metrics
            query_parts = [f'from(bucket: "opsbuddy-metrics")']

            # Add time range
            if start_time:
                query_parts.append(f'start: {start_time}')
            else:
                start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
                query_parts.append(f'start: {start_time}')

            if end_time:
                query_parts.append(f'stop: {end_time}')

            # Add service filter if specified
            if service:
                query_parts.append(f'filter(fn: (r) => r.service == "{service}")')

            # Add metric filter
            query_parts.append(f'filter(fn: (r) => r._field == "{metric}")')

            # Add aggregation
            if aggregation == "count":
                query_parts.append("aggregateWindow(every: 1m, fn: count)")
            elif aggregation == "sum":
                query_parts.append("aggregateWindow(every: 1m, fn: sum)")
            elif aggregation == "min":
                query_parts.append("aggregateWindow(every: 1m, fn: min)")
            elif aggregation == "max":
                query_parts.append("aggregateWindow(every: 1m, fn: max)")
            else:  # mean
                query_parts.append("aggregateWindow(every: 1m, fn: mean)")

            # Group by if specified
            if group_by:
                query_parts.append(f'group(columns: ["{group_by}"])')

            flux_query = " |> ".join(query_parts)

            logger.debug(f"Executing metrics query: {flux_query}")

            # Execute query
            result = self._query_api.query(flux_query, org=settings.influxdb_org)

            # Process results
            metrics = []
            for table in result:
                for record in table.records:
                    metric_entry = {
                        "timestamp": record.get_time().isoformat(),
                        "metric": metric,
                        "value": record.get_value(),
                        "service": record.values.get("service"),
                        "aggregation": aggregation
                    }

                    if group_by:
                        metric_entry[group_by] = record.values.get(group_by)

                    metrics.append(metric_entry)

            logger.debug(f"Retrieved {len(metrics)} metric entries from InfluxDB")
            return metrics

        except Exception as e:
            logger.error(f"Failed to query metrics from InfluxDB: {str(e)}")
            raise

    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics."""
        if not self._connected or not self._query_api:
            return {}

        try:
            # Query for service statistics over last hour
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)

            query = f'''
            from(bucket: "opsbuddy-logs")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> group(columns: ["service", "level"])
            |> count()
            |> group(columns: ["service"])
            '''

            result = self._query_api.query(query, org=settings.influxdb_org)

            # Process results
            service_metrics = {}
            for table in result:
                for record in table.records:
                    service = record.values.get("service")
                    level = record.values.get("level")
                    count = record.get_value()

                    if service not in service_metrics:
                        service_metrics[service] = {
                            "total_logs": 0,
                            "error_count": 0,
                            "warning_count": 0,
                            "info_count": 0,
                            "debug_count": 0
                        }

                    service_metrics[service]["total_logs"] += count
                    if level == "ERROR":
                        service_metrics[service]["error_count"] += count
                    elif level == "WARNING":
                        service_metrics[service]["warning_count"] += count
                    elif level == "INFO":
                        service_metrics[service]["info_count"] += count
                    elif level == "DEBUG":
                        service_metrics[service]["debug_count"] += count

            return service_metrics

        except Exception as e:
            logger.error(f"Failed to get service metrics: {str(e)}")
            return {}

    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        if not self._connected or not self._query_api:
            return {}

        try:
            # Get statistics for last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)

            # Query for overall statistics
            query = f'''
            from(bucket: "opsbuddy-logs")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> group(columns: ["service"])
            |> count()
            |> sum()
            '''

            result = self._query_api.query(query, org=settings.influxdb_org)

            # Process results
            total_logs = 0
            service_breakdown = {}

            for table in result:
                for record in table.records:
                    service = record.values.get("service")
                    count = record.get_value()

                    service_breakdown[service] = count
                    total_logs += count

            # Get error rate
            error_query = f'''
            from(bucket: "opsbuddy-logs")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r.level == "ERROR")
            |> count()
            '''

            error_result = self._query_api.query(error_query, org=settings.influxdb_org)
            error_count = 0

            for table in error_result:
                for record in table.records:
                    error_count += record.get_value()

            return {
                "total_logs_24h": total_logs,
                "error_count_24h": error_count,
                "error_rate_24h": (error_count / total_logs * 100) if total_logs > 0 else 0,
                "service_breakdown": service_breakdown,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Failed to get service statistics: {str(e)}")
            return {}

    async def store_metrics(self, metrics: List[Dict[str, Any]]):
        """Store custom metrics in InfluxDB."""
        if not self._connected or not self._write_api:
            logger.error("Cannot store metrics: not connected to database")
            return

        try:
            points = []

            for metric_entry in metrics:
                # Create InfluxDB point for metric
                point = Point("service_metrics") \
                    .tag("service", metric_entry.get("service", "unknown")) \
                    .tag("metric_type", metric_entry.get("metric_type", "gauge")) \
                    .field("value", float(metric_entry.get("value", 0))) \
                    .time(metric_entry.get("timestamp", datetime.utcnow()))

                # Add additional tags if present
                if metric_entry.get("tags"):
                    for key, value in metric_entry["tags"].items():
                        point = point.tag(key, str(value))

                points.append(point)

            # Write points to database
            self._write_api.write(
                bucket="opsbuddy-metrics",
                org=settings.influxdb_org,
                record=points
            )

            logger.debug(f"Stored {len(points)} metric entries in InfluxDB")

        except Exception as e:
            logger.error(f"Failed to store metrics in InfluxDB: {str(e)}")
            raise

# Global database manager instance
db_manager = DatabaseManager()