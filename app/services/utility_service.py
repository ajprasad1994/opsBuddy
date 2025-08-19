"""
Utility Service for OpsBuddy application.
Handles utility configurations, system utilities, and health checks.
"""

import uuid
import platform
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

# Try to import psutil, provide fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from app.database import db_manager, UtilityConfig
from app.utils.logger import get_logger, log_operation


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
                "fields_updated": {
                    "name": name is not None,
                    "category": category is not None,
                    "value": value is not None,
                    "description": description is not None,
                    "is_active": is_active is not None
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
    
    async def list_configs(self, category: str = None, is_active: bool = None, limit: int = 100) -> List[UtilityConfig]:
        """List utility configurations with optional filtering."""
        try:
            # Query database for configurations
            query = "SELECT * FROM utility_config"
            conditions = []
            
            if category:
                conditions.append(f"category = '{category}'")
            
            if is_active is not None:
                conditions.append(f"is_active = {str(is_active).lower()}")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += f" ORDER BY created_at DESC LIMIT {limit}"
            
            results = await db_manager.query_data(query)
            
            # Convert results to UtilityConfig objects
            configs = []
            for result in results:
                try:
                    config = UtilityConfig(**result)
                    configs.append(config)
                except Exception as e:
                    logger.warning(f"Failed to parse utility config: {str(e)}")
            
            log_operation("list", "utility_service", {
                "count": len(configs),
                "filters": {"category": category, "is_active": is_active, "limit": limit}
            })
            
            return configs
            
        except Exception as e:
            logger.error(f"Failed to list utility configs: {str(e)}")
            log_operation("list", "utility_service", {
                "status": "failed",
                "error": str(e)
            }, "ERROR")
            return []
    
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
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        try:
            # Check database connection
            db_status = "healthy" if await db_manager.is_connected() else "unhealthy"
            
            # Get system metrics
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
            log_operation("health_check", "utility_service", {
                "status": "failed",
                "error": str(e)
            }, "ERROR")
            
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "uptime": (datetime.now(timezone.utc) - self.start_time).total_seconds()
            }
    
    async def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a system command (with safety restrictions)."""
        try:
            # Define allowed commands for security
            allowed_commands = [
                "ls", "pwd", "whoami", "date", "uptime", "df", "free",
                "ps", "top", "netstat", "ss", "ping", "nslookup"
            ]
            
            command_parts = command.split()
            base_command = command_parts[0]
            
            if base_command not in allowed_commands:
                raise ValueError(f"Command '{base_command}' is not allowed for security reasons")
            
            # Execute command (this is a simplified version)
            # In production, you'd want more sophisticated command execution
            import subprocess
            import asyncio
            
            process = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                result = {
                    "command": command,
                    "return_code": process.returncode,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                    "success": process.returncode == 0
                }
                
                log_operation("execute_command", "utility_service", {
                    "command": command,
                    "success": result["success"],
                    "return_code": result["return_code"]
                })
                
                return result
                
            except asyncio.TimeoutError:
                process.kill()
                raise Exception(f"Command execution timed out after {timeout} seconds")
                
        except Exception as e:
            logger.error(f"Failed to execute command '{command}': {str(e)}")
            log_operation("execute_command", "utility_service", {
                "status": "failed",
                "error": str(e),
                "command": command
            }, "ERROR")
            raise
    
    async def _store_config(self, config: UtilityConfig) -> bool:
        """Store utility configuration in the database."""
        try:
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
            
            return await db_manager.write_point(
                measurement="utility_config",
                tags=tags,
                fields=fields,
                timestamp=int(config.created_at.timestamp() * 1e9)
            )
            
        except Exception as e:
            logger.error(f"Failed to store utility config: {str(e)}")
            return False
    
    async def _get_config(self, config_id: str) -> Optional[UtilityConfig]:
        """Retrieve utility configuration from the database."""
        try:
            query = f'SELECT * FROM utility_config WHERE tags["config_id"] = "{config_id}" ORDER BY time DESC LIMIT 1'
            results = await db_manager.query_data(query)
            
            if results:
                result = results[0]
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
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get utility config: {str(e)}")
            return None
    
    async def _update_config(self, config: UtilityConfig) -> bool:
        """Update utility configuration in the database."""
        try:
            # For time-series databases, we typically write a new point
            return await self._store_config(config)
            
        except Exception as e:
            logger.error(f"Failed to update utility config: {str(e)}")
            return False
    
    async def _delete_config(self, config_id: str) -> bool:
        """Delete utility configuration from the database."""
        try:
            return await db_manager.delete_data(
                measurement="utility_config",
                tags={"config_id": config_id}
            )
            
        except Exception as e:
            logger.error(f"Failed to delete utility config: {str(e)}")
            return False


# Global utility service instance
utility_service = UtilityService()
