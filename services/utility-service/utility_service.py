"""
Utility Service for OpsBuddy - Standalone Microservice
Handles utility configurations, system utilities, and health checks.
"""

import uuid
import platform
import subprocess
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

# Try to import psutil, provide fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from config import settings
from database import db_manager, UtilityConfig
from utils import get_logger, log_operation


logger = get_logger("utility_service")


class UtilityService:
    """Service for managing utility operations and configurations."""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
    
    async def create_config(self, name: str, category: str, value: Any, description: str = None) -> Optional[UtilityConfig]:
        """Create a new utility configuration."""
        try:
            config_id = str(uuid.uuid4())
            
            config = UtilityConfig(
                config_id=config_id,
                name=name,
                category=category,
                value=value,
                description=description
            )
            
            # Store configuration in database
            success = await self._store_config(config)
            if not success:
                raise Exception("Failed to store configuration in database")
            
            log_operation("create", "utility_service", {
                "config_id": config_id,
                "name": name,
                "category": category
            })
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to create utility config {name}: {str(e)}")
            log_operation("create", "utility_service", {
                "status": "failed",
                "error": str(e),
                "name": name
            }, "ERROR")
            raise
    
    async def read_config(self, config_id: str) -> Optional[UtilityConfig]:
        """Read a utility configuration by ID."""
        try:
            config = await self._get_config(config_id)
            if config:
                log_operation("read", "utility_service", {"config_id": config_id})
            return config
            
        except Exception as e:
            logger.error(f"Failed to read utility config {config_id}: {str(e)}")
            log_operation("read", "utility_service", {
                "status": "failed",
                "error": str(e),
                "config_id": config_id
            }, "ERROR")
            return None
    
    async def update_config(self, config_id: str, name: str = None, category: str = None, value: Any = None, description: str = None, is_active: bool = None) -> Optional[UtilityConfig]:
        """Update a utility configuration."""
        try:
            config = await self._get_config(config_id)
            if not config:
                raise ValueError(f"Configuration with ID {config_id} not found")
            
            # Update fields if provided
            if name is not None:
                config.name = name
            if category is not None:
                config.category = category
            if value is not None:
                config.value = value
            if description is not None:
                config.description = description
            if is_active is not None:
                config.is_active = is_active
            
            config.updated_at = datetime.now(timezone.utc)
            
            # Update in database
            success = await self._update_config(config)
            if not success:
                raise Exception("Failed to update configuration in database")
            
            log_operation("update", "utility_service", {
                "config_id": config_id,
                "changes": {
                    "name": name, "category": category, "value": value,
                    "description": description, "is_active": is_active
                }
            })
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to update utility config {config_id}: {str(e)}")
            log_operation("update", "utility_service", {
                "status": "failed",
                "error": str(e),
                "config_id": config_id
            }, "ERROR")
            raise
    
    async def delete_config(self, config_id: str) -> bool:
        """Delete a utility configuration."""
        try:
            config = await self._get_config(config_id)
            if not config:
                raise ValueError(f"Configuration with ID {config_id} not found")
            
            # Delete from database
            success = await self._delete_config(config_id)
            if not success:
                raise Exception("Failed to delete configuration from database")
            
            log_operation("delete", "utility_service", {"config_id": config_id})
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete utility config {config_id}: {str(e)}")
            log_operation("delete", "utility_service", {
                "status": "failed",
                "error": str(e),
                "config_id": config_id
            }, "ERROR")
            raise
    
    async def list_configs(self, category: str = None, is_active: bool = None, limit: int = 100, offset: int = 0) -> List[UtilityConfig]:
        """List utility configurations with optional filtering."""
        try:
            # Build query based on filters
            query_parts = []
            
            if category:
                query_parts.append(f'tags["category"] = "{category}"')
            
            if is_active is not None:
                query_parts.append(f'fields["is_active"] = {str(is_active).lower()}')
            
            # Add measurement and limit
            query = f'from(bucket: "{settings.influxdb_database}") |> range(start: -30d)'
            
            if query_parts:
                query += f' |> filter(fn: (r) => {" and ".join(query_parts)})'
            
            query += f' |> limit(n: {limit}, offset: {offset})'
            
            # Execute query
            results = await db_manager.query_data(query)
            
            # Convert results to UtilityConfig objects
            configs = []
            for result in results:
                try:
                    config = self._result_to_config(result, result.get("tags", {}).get("config_id", ""))
                    if config:
                        configs.append(config)
                except Exception as e:
                    logger.warning(f"Failed to parse result: {e}")
                    continue
            
            log_operation("list", "utility_service", {
                "count": len(configs),
                "filters": {"category": category, "is_active": is_active}
            })
            
            return configs
            
        except Exception as e:
            logger.error(f"Failed to list configs: {str(e)}")
            log_operation("list", "utility_service", {
                "status": "failed",
                "error": str(e)
            }, "ERROR")
            raise
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information and statistics."""
        try:
            # Get basic system information
            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "uptime": (datetime.now(timezone.utc) - self.start_time).total_seconds()
            }
            
            # Add psutil-based information if available
            if PSUTIL_AVAILABLE and psutil:
                try:
                    system_info.update({
                        "cpu_count": psutil.cpu_count(),
                        "memory_total": psutil.virtual_memory().total,
                        "memory_available": psutil.virtual_memory().available,
                        "disk_usage": psutil.disk_usage('/').percent
                    })
                except Exception as e:
                    logger.warning(f"Failed to get psutil system info: {str(e)}")
                    system_info.update({
                        "cpu_count": "unknown",
                        "memory_total": "unknown",
                        "memory_available": "unknown",
                        "disk_usage": "unknown"
                    })
            else:
                system_info.update({
                    "cpu_count": "psutil not available",
                    "memory_total": "psutil not available",
                    "memory_available": "psutil not available",
                    "disk_usage": "psutil not available"
                })
            
            log_operation("system_info", "utility_service", {"status": "success"})
            
            return system_info
            
        except Exception as e:
            logger.error(f"Failed to get system info: {str(e)}")
            log_operation("system_info", "utility_service", {
                "status": "failed",
                "error": str(e)
            }, "ERROR")
            raise
    
    async def execute_command(self, command: str, timeout: int = None) -> Dict[str, Any]:
        """Execute a system command safely."""
        try:
            # Validate command
            if not self._is_command_allowed(command):
                raise ValueError(f"Command '{command}' is not allowed")
            
            # Set timeout
            if timeout is None:
                timeout = settings.command_timeout
            
            # Execute command
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Prepare response
            response = {
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout[:settings.max_command_output],
                "stderr": result.stderr[:settings.max_command_output],
                "execution_time": 0  # Could be enhanced with timing
            }
            
            log_operation("execute_command", "utility_service", {
                "command": command,
                "return_code": result.returncode
            })
            
            return response
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command '{command}' timed out after {timeout} seconds")
            raise ValueError(f"Command timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {str(e)}")
            log_operation("execute_command", "utility_service", {
                "status": "failed",
                "error": str(e),
                "command": command
            }, "ERROR")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for the utility service."""
        try:
            # Check database connection
            db_status = "healthy" if db_manager._connected else "unhealthy"
            
            # Get system info
            system_info = await self.get_system_info()
            
            health_status = {
                "status": "healthy" if db_status == "healthy" else "degraded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database": db_status,
                "system": system_info,
                "uptime": system_info.get("uptime", 0)
            }
            
            log_operation("health_check", "utility_service", {"status": health_status["status"]})
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "uptime": (datetime.now(timezone.utc) - self.start_time).total_seconds()
            }
    
    def _is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed to be executed."""
        base_command = command.split()[0] if command else ""
        return base_command in settings.allowed_commands_list
    
    async def _store_config(self, config: UtilityConfig) -> bool:
        """Store utility configuration in database."""
        try:
            # Convert config to InfluxDB point
            tags = {
                "config_id": config.config_id,
                "name": config.name,
                "category": config.category
            }
            
            fields = {
                "value": str(config.value),
                "description": config.description or "",
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat(),
                "is_active": config.is_active
            }
            
            success = await db_manager.write_point(
                measurement="utility_config",
                tags=tags,
                fields=fields,
                timestamp=int(config.created_at.timestamp() * 1e9)
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to store config: {str(e)}")
            raise
    
    async def _get_config(self, config_id: str) -> Optional[UtilityConfig]:
        """Get utility configuration from database."""
        try:
            query = f'''
            from(bucket: "{settings.influxdb_database}")
            |> range(start: -30d)
            |> filter(fn: (r) => r["_measurement"] == "utility_config")
            |> filter(fn: (r) => r["tags"]["config_id"] == "{config_id}")
            |> last()
            '''
            
            results = await db_manager.query_data(query)
            
            if not results:
                return None
            
            return self._result_to_config(results[0], config_id)
            
        except Exception as e:
            logger.error(f"Failed to get config: {str(e)}")
            raise
    
    async def _update_config(self, config: UtilityConfig) -> bool:
        """Update utility configuration in database."""
        try:
            # Delete old config
            await self._delete_config(config.config_id)
            
            # Store new config
            return await self._store_config(config)
            
        except Exception as e:
            logger.error(f"Failed to update config: {str(e)}")
            raise
    
    async def _delete_config(self, config_id: str) -> bool:
        """Delete utility configuration from database."""
        try:
            success = await db_manager.delete_data(
                measurement="utility_config",
                tags={"config_id": config_id}
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete config: {str(e)}")
            raise
    
    def _result_to_config(self, result: Dict[str, Any], config_id: str) -> Optional[UtilityConfig]:
        """Convert InfluxDB result to UtilityConfig object."""
        try:
            return UtilityConfig(
                config_id=result.get("tags", {}).get("config_id", config_id),
                name=result.get("tags", {}).get("name", ""),
                category=result.get("tags", {}).get("category", ""),
                value=eval(result.get("fields", {}).get("value", "None")),
                description=result.get("fields", {}).get("description", ""),
                created_at=datetime.fromisoformat(result.get("fields", {}).get("created_at", datetime.now(timezone.utc).isoformat())),
                updated_at=datetime.fromisoformat(result.get("fields", {}).get("updated_at", datetime.now(timezone.utc).isoformat())),
                is_active=result.get("fields", {}).get("is_active", True)
            )
        except Exception as e:
            logger.error(f"Failed to convert result to config: {str(e)}")
            return None


# Global service instance
utility_service = UtilityService()
