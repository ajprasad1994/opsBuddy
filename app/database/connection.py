"""
Database connection manager for InfluxDB.
Supports both InfluxDB 1.x and 2.x versions.
"""

import asyncio
from typing import Optional, Dict, Any, List
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb import InfluxDBClient as InfluxDBClientV1
from app.config import settings
from app.utils.logger import get_logger, log_operation


logger = get_logger("database")


class InfluxDBManager:
    """Manages InfluxDB connections and operations."""
    
    def __init__(self):
        self.client_v2: Optional[InfluxDBClient] = None
        self.client_v1: Optional[InfluxDBClientV1] = None
        self.write_api = None
        self.query_api = None
        self.bucket_api = None
        self.version: Optional[str] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Establish connection to InfluxDB."""
        try:
            # Try InfluxDB 2.x first
            if settings.influxdb_token and settings.influxdb_org:
                await self._connect_v2()
            else:
                await self._connect_v1()
            
            self._connected = True
            log_operation("connect", "database", {"status": "success", "version": self.version})
            return True
            
        except Exception as e:
            logger.warning(f"Failed to connect to InfluxDB: {str(e)}")
            log_operation("connect", "database", {"status": "failed", "error": str(e)}, "WARNING")
            # Don't fail the application startup if DB is not available
            return False
    
    async def _connect_v2(self):
        """Connect to InfluxDB 2.x."""
        try:
            url = settings.influxdb_url or f"http://{settings.influxdb_host}:{settings.influxdb_port}"
            
            self.client_v2 = InfluxDBClient(
                url=url,
                token=settings.influxdb_token,
                org=settings.influxdb_org,
                timeout=30000
            )
            
            # Test connection
            health = self.client_v2.health()
            if health.status == "pass":
                self.version = "2.x"
                self.write_api = self.client_v2.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client_v2.query_api()
                self.bucket_api = self.client_v2.buckets_api()
                logger.info("Successfully connected to InfluxDB 2.x")
            else:
                raise Exception(f"InfluxDB 2.x health check failed: {health.message}")
                
        except Exception as e:
            logger.error(f"InfluxDB 2.x connection failed: {str(e)}")
            raise
    
    async def _connect_v1(self):
        """Connect to InfluxDB 1.x."""
        try:
            self.client_v1 = InfluxDBClientV1(
                host=settings.influxdb_host,
                port=settings.influxdb_port,
                username=settings.influxdb_username,
                password=settings.influxdb_password,
                database=settings.influxdb_database
            )
            
            # Test connection
            self.client_v1.ping()
            self.version = "1.x"
            logger.info("Successfully connected to InfluxDB 1.x")
            
        except Exception as e:
            logger.error(f"InfluxDB 1.x connection failed: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close database connections."""
        try:
            if self.client_v2:
                self.client_v2.close()
            if self.client_v1:
                self.client_v1.close()
            
            self._connected = False
            log_operation("disconnect", "database", {"status": "success"})
            logger.info("Disconnected from InfluxDB")
            
        except Exception as e:
            logger.error(f"Error disconnecting from InfluxDB: {str(e)}")
    
    async def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected
    
    async def write_point(self, measurement: str, tags: Dict[str, str], fields: Dict[str, Any], timestamp: Optional[int] = None) -> bool:
        """Write a data point to InfluxDB."""
        if not self._connected:
            logger.warning("Database not connected, skipping write operation")
            return False
            
        try:
            if self.version == "2.x":
                point = Point(measurement)
                
                # Add tags
                for key, value in tags.items():
                    point.tag(key, value)
                
                # Add fields
                for key, value in fields.items():
                    point.field(key, value)
                
                # Add timestamp if provided
                if timestamp:
                    point.time(timestamp, WritePrecision.NS)
                
                self.write_api.write(bucket=settings.influxdb_database, record=point)
                
            else:  # v1.x
                data = {
                    "measurement": measurement,
                    "tags": tags,
                    "fields": fields
                }
                
                if timestamp:
                    data["time"] = timestamp
                
                self.client_v1.write_points([data])
            
            log_operation("write", "database", {
                "measurement": measurement,
                "tags": tags,
                "fields": fields
            })
            return True
            
        except Exception as e:
            logger.error(f"Failed to write point: {str(e)}")
            log_operation("write", "database", {
                "status": "failed",
                "error": str(e),
                "measurement": measurement
            }, "ERROR")
            return False
    
    async def query_data(self, query: str) -> List[Dict[str, Any]]:
        """Query data from InfluxDB."""
        if not self._connected:
            logger.warning("Database not connected, returning empty result")
            return []
            
        try:
            if self.version == "2.x":
                result = self.query_api.query(query, org=settings.influxdb_org)
                # Convert FluxTable to list of dicts
                data = []
                for table in result:
                    for record in table.records:
                        data.append({
                            "time": record.get_time(),
                            "value": record.get_value(),
                            "field": record.get_field(),
                            "measurement": record.get_measurement()
                        })
                return data
            else:  # v1.x
                result = self.client_v1.query(query)
                return list(result.get_points())
                
        except Exception as e:
            logger.error(f"Failed to query data: {str(e)}")
            log_operation("query", "database", {
                "status": "failed",
                "error": str(e),
                "query": query
            }, "ERROR")
            return []
    
    async def delete_data(self, measurement: str, tags: Dict[str, str] = None, start_time: Optional[int] = None, end_time: Optional[int] = None) -> bool:
        """Delete data from InfluxDB."""
        if not self._connected:
            logger.warning("Database not connected, skipping delete operation")
            return False
            
        try:
            if self.version == "2.x":
                # InfluxDB 2.x delete API
                delete_api = self.client_v2.delete_api()
                start = f"1970-01-01T00:00:00Z" if start_time is None else f"{start_time}"
                stop = f"2100-01-01T00:00:00Z" if end_time is None else f"{end_time}"
                
                tag_predicates = []
                if tags:
                    for key, value in tags.items():
                        tag_predicates.append(f'{key}="{value}"')
                
                predicate = " AND ".join(tag_predicates) if tag_predicates else ""
                
                delete_api.delete(
                    start=start,
                    stop=stop,
                    predicate=predicate,
                    bucket=settings.influxdb_database
                )
            else:  # v1.x
                # InfluxDB 1.x doesn't support delete, use retention policy instead
                logger.warning("Delete operation not supported in InfluxDB 1.x")
                return False
            
            log_operation("delete", "database", {
                "measurement": measurement,
                "tags": tags,
                "start_time": start_time,
                "end_time": end_time
            })
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete data: {str(e)}")
            log_operation("delete", "database", {
                "status": "failed",
                "error": str(e),
                "measurement": measurement
            }, "ERROR")
            return False


# Global database manager instance
db_manager = InfluxDBManager()
