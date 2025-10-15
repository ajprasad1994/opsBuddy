"""
InfluxDB integration for OpsBuddy Incident Service.
Handles querying recent logs for incident detection.
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

logger = get_logger("incident_database")

class DatabaseManager:
    """Manages InfluxDB connections and operations for incident detection."""

    def __init__(self):
        self._client: Optional[InfluxDBClient] = None
        self._connected: bool = False
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

            # Initialize query API
            self._query_api = self._client.query_api()
            self._connected = True
            logger.info("Successfully connected to InfluxDB")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {str(e)}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from InfluxDB."""
        try:
            if self._client:
                self._client.close()
            self._connected = False
            logger.info("Disconnected from InfluxDB")
        except Exception as e:
            logger.error(f"Error disconnecting from InfluxDB: {str(e)}")

    async def query_recent_logs(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Query recent logs from InfluxDB for incident detection."""
        if not self._connected or not self._query_api:
            logger.error("Cannot query logs: not connected to database")
            return []

        try:
            # Set time range for recent logs
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=minutes)

            # Build Flux query for recent logs
            flux_query = f'''
            from(bucket: "opsbuddy-logs")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> limit(n: {settings.query_batch_size})
            |> sort(columns: ["_time"], desc: true)
            '''

            logger.debug(f"Executing recent logs query: {flux_query}")
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

            logger.debug(f"Retrieved {len(logs)} recent log entries from InfluxDB")
            return logs

        except Exception as e:
            logger.error(f"Failed to query recent logs from InfluxDB: {str(e)}")
            raise

    async def query_errors_since(self, timestamp: str) -> List[Dict[str, Any]]:
        """Query error logs since a specific timestamp."""
        if not self._connected or not self._query_api:
            logger.error("Cannot query errors: not connected to database")
            return []

        try:
            # Build Flux query for errors since timestamp
            flux_query = f'''
            from(bucket: "opsbuddy-logs")
            |> range(start: {timestamp})
            |> filter(fn: (r) => r.level == "ERROR" or r.level == "CRITICAL" or r.level == "FATAL")
            |> limit(n: {settings.query_batch_size})
            |> sort(columns: ["_time"], desc: true)
            '''

            logger.debug(f"Executing error query: {flux_query}")
            result = self._query_api.query(flux_query, org=settings.influxdb_org)

            # Process results
            errors = []
            for table in result:
                for record in table.records:
                    error_entry = {
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
                            data_fields[key[5:]] = value

                    if data_fields:
                        error_entry["data"] = data_fields

                    errors.append(error_entry)

            logger.debug(f"Retrieved {len(errors)} error entries from InfluxDB")
            return errors

        except Exception as e:
            logger.error(f"Failed to query errors from InfluxDB: {str(e)}")
            raise

    async def query_service_errors(self, service: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Query errors for a specific service within the last N hours."""
        if not self._connected or not self._query_api:
            logger.error("Cannot query service errors: not connected to database")
            return []

        try:
            # Set time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            # Build Flux query for service errors
            flux_query = f'''
            from(bucket: "opsbuddy-logs")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r.service == "{service}")
            |> filter(fn: (r) => r.level == "ERROR" or r.level == "CRITICAL" or r.level == "FATAL")
            |> limit(n: {settings.query_batch_size})
            |> sort(columns: ["_time"], desc: true)
            '''

            logger.debug(f"Executing service error query: {flux_query}")
            result = self._query_api.query(flux_query, org=settings.influxdb_org)

            # Process results
            errors = []
            for table in result:
                for record in table.records:
                    error_entry = {
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
                            data_fields[key[5:]] = value

                    if data_fields:
                        error_entry["data"] = data_fields

                    errors.append(error_entry)

            logger.debug(f"Retrieved {len(errors)} error entries for service {service}")
            return errors

        except Exception as e:
            logger.error(f"Failed to query service errors from InfluxDB: {str(e)}")
            raise

    async def get_incident_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of incidents and errors in the last N hours."""
        if not self._connected or not self._query_api:
            return {}

        try:
            # Set time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            # Query for error statistics
            flux_query = f'''
            from(bucket: "opsbuddy-logs")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r.level == "ERROR" or r.level == "CRITICAL" or r.level == "FATAL")
            |> group(columns: ["service", "level"])
            |> count()
            |> group(columns: ["service"])
            '''

            logger.debug(f"Executing incident summary query: {flux_query}")
            result = self._query_api.query(flux_query, org=settings.influxdb_org)

            # Process results
            incident_summary = {
                "total_errors": 0,
                "services_affected": 0,
                "error_breakdown": {},
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            }

            service_errors = {}
            for table in result:
                for record in table.records:
                    service = record.values.get("service")
                    level = record.values.get("level")
                    count = record.get_value()

                    if service not in service_errors:
                        service_errors[service] = {
                            "total_errors": 0,
                            "error_levels": {}
                        }

                    service_errors[service]["total_errors"] += count
                    service_errors[service]["error_levels"][level] = count
                    incident_summary["total_errors"] += count

            incident_summary["services_affected"] = len(service_errors)
            incident_summary["error_breakdown"] = service_errors

            # Get most recent errors for context
            recent_errors = await self.query_recent_logs(minutes=30)
            error_logs = [log for log in recent_errors if log.get("level") in settings.error_levels]

            incident_summary["recent_error_count"] = len(error_logs)
            incident_summary["recent_errors"] = error_logs[:10]  # Last 10 errors

            return incident_summary

        except Exception as e:
            logger.error(f"Failed to get incident summary: {str(e)}")
            return {}

# Global database manager instance
db_manager = DatabaseManager()