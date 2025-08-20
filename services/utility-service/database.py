"""
Database models and connection management for OpsBuddy Utility Service.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.query_api import QueryApi
from influxdb import InfluxDBClient as InfluxDBClientV1

from config import settings


# Database Models
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


class DatabaseManager:
    """Manages InfluxDB connections and operations."""
    
    def __init__(self):
        self._connected = False
        self.version = "2.x"  # Default to 2.x
        self.client = None
        self.write_api = None
        self.query_api = None
        
        # V1 client for legacy support
        self.client_v1 = None
        
    async def connect(self) -> bool:
        """Connect to InfluxDB."""
        try:
            # Try InfluxDB 2.x first
            if await self._connect_v2():
                self.version = "2.x"
                return True
            
            # Fallback to InfluxDB 1.x
            if await self._connect_v1():
                self.version = "1.x"
                return True
            
            return False
            
        except Exception as e:
            print(f"Failed to connect to InfluxDB: {str(e)}")
            return False
    
    async def _connect_v2(self) -> bool:
        """Connect to InfluxDB 2.x."""
        try:
            self.client = InfluxDBClient(
                url=settings.influxdb_url,
                token=settings.influxdb_token,
                org=settings.influxdb_org,
                timeout=30_000
            )
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                self._connected = True
                return True
            
            return False
            
        except Exception as e:
            print(f"Failed to connect to InfluxDB 2.x: {str(e)}")
            return False
    
    async def _connect_v1(self) -> bool:
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
            self._connected = True
            return True
            
        except Exception as e:
            print(f"Failed to connect to InfluxDB 1.x: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from InfluxDB."""
        try:
            if self.client:
                self.client.close()
            if self.client_v1:
                self.client_v1.close()
            self._connected = False
            
        except Exception as e:
            print(f"Error during disconnect: {str(e)}")
    
    async def write_point(self, measurement: str, tags: Dict[str, str], fields: Dict[str, Any], timestamp: Optional[int] = None) -> bool:
        """Write a data point to InfluxDB."""
        if not self._connected:
            print("Database not connected, skipping write operation")
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
                    point.time(timestamp)
                
                self.write_api.write(bucket=settings.influxdb_database, record=point)
                
            else:  # 1.x
                data_point = {
                    "measurement": measurement,
                    "tags": tags,
                    "fields": fields
                }
                
                if timestamp:
                    data_point["time"] = timestamp
                
                self.client_v1.write_points([data_point])
            
            return True
            
        except Exception as e:
            print(f"Failed to write point: {str(e)}")
            return False
    
    async def query_data(self, query: str) -> List[Dict[str, Any]]:
        """Query data from InfluxDB."""
        if not self._connected:
            print("Database not connected, returning empty result")
            return []
            
        try:
            if self.version == "2.x":
                result = self.query_api.query(query, org=settings.influxdb_org)
                
                # Convert to list of dictionaries
                data = []
                for table in result:
                    for record in table.records:
                        data.append({
                            "time": record.get_time(),
                            "measurement": record.get_measurement(),
                            "tags": record.values,
                            "fields": record.values
                        })
                
                return data
                
            else:  # 1.x
                result = self.client_v1.query(query)
                
                # Convert to list of dictionaries
                data = []
                for series in result:
                    for point in series['points']:
                        data.append({
                            "time": point[0],
                            "measurement": series['name'],
                            "tags": dict(zip(series['columns'], point)),
                            "fields": dict(zip(series['columns'], point))
                        })
                
                return data
                
        except Exception as e:
            print(f"Failed to query data: {str(e)}")
            return []
    
    async def delete_data(self, measurement: str, tags: Dict[str, str] = None, start_time: Optional[int] = None, end_time: Optional[int] = None) -> bool:
        """Delete data from InfluxDB."""
        if not self._connected:
            print("Database not connected, skipping delete operation")
            return False
            
        try:
            if self.version == "2.x":
                # InfluxDB 2.x delete API
                delete_api = self.client.delete_api()
                
                # Build delete predicate
                predicate = f'_measurement="{measurement}"'
                if tags:
                    for key, value in tags.items():
                        predicate += f' AND {key}="{value}"'
                
                delete_api.delete(
                    start=start_time or 0,
                    stop=end_time or int(datetime.now(timezone.utc).timestamp() * 1e9),
                    predicate=predicate,
                    bucket=settings.influxdb_database,
                    org=settings.influxdb_org
                )
                
            else:  # 1.x
                # InfluxDB 1.x doesn't support delete, we'll mark as deleted
                delete_tag = {"deleted": "true"}
                if tags:
                    delete_tag.update(tags)
                
                await self.write_point(measurement, delete_tag, {"deleted_at": datetime.now(timezone.utc).isoformat()})
            
            return True
            
        except Exception as e:
            print(f"Failed to delete data: {str(e)}")
            return False


# Global database manager instance
db_manager = DatabaseManager()
