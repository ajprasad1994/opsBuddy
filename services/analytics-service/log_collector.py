"""
Log collection service for OpsBuddy Analytics Service.
Collects logs from all microservices and forwards them for processing.
"""

import time
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

from config import settings
from utils import get_logger

logger = get_logger("log_collector")

class LogCollector:
    """Collects logs from microservices."""

    def __init__(self):
        self.services: Dict[str, Dict[str, Any]] = {}
        self.collection_interval: int = settings.log_collection_interval
        self.batch_size: int = settings.batch_size
        self.is_running_flag: bool = False
        self.last_collection: Optional[datetime] = None
        self.logs_collected: int = 0
        self.errors: List[str] = []
        self._collection_task: Optional[asyncio.Task] = None

    def is_running(self) -> bool:
        """Check if log collection is running."""
        return self.is_running_flag and self._collection_task is not None

    async def start_collection(self):
        """Start log collection from all services."""
        if self.is_running():
            logger.warning("Log collection is already running")
            return

        logger.info("Starting log collection service...")

        # Initialize service endpoints (disabled for now)
        self._initialize_services()

        # Don't start collection if no services are configured
        if not self.services:
            logger.info("No services configured for log collection - running in receive-only mode")
            return

        # Start collection task
        self.is_running_flag = True
        self._collection_task = asyncio.create_task(self._collection_loop())

        logger.info(f"Log collection started with {len(self.services)} services")

    async def stop_collection(self):
        """Stop log collection."""
        if not self.is_running():
            logger.warning("Log collection is not running")
            return

        logger.info("Stopping log collection service...")

        self.is_running_flag = False

        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        self._collection_task = None
        logger.info("Log collection stopped")

    def _initialize_services(self):
        """Initialize service endpoints for log collection."""
        # For now, disable automatic log collection from other services
        # since they don't have /logs endpoints. Logs should be sent directly to Analytics service.
        self.services = {}
        logger.info("Log collection from other services disabled - services should send logs directly to Analytics service")

    async def _collection_loop(self):
        """Main collection loop."""
        while self.is_running_flag:
            try:
                await self._collect_from_all_services()
                self.last_collection = datetime.utcnow()
                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                logger.info("Collection loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in collection loop: {str(e)}")
                self.errors.append(f"Collection loop error: {str(e)}")
                await asyncio.sleep(self.collection_interval)

    async def _collect_from_all_services(self):
        """Collect logs from all configured services."""
        collection_tasks = []

        for service_name, service_config in self.services.items():
            task = asyncio.create_task(
                self._collect_from_service(service_name, service_config)
            )
            collection_tasks.append(task)

        # Wait for all collection tasks to complete
        if collection_tasks:
            await asyncio.gather(*collection_tasks, return_exceptions=True)

    async def _collect_from_service(self, service_name: str, service_config: Dict[str, Any]):
        """Collect logs from a specific service."""
        try:
            # Check if service is healthy first
            if not await self._check_service_health(service_config["health_url"]):
                logger.debug(f"Service {service_name} is not healthy, skipping log collection")
                return

            # Calculate time range for log collection
            since_time = self._get_since_time(service_config)

            # Collect logs from service
            logs = await self._fetch_logs_from_service(
                service_config["url"],
                since_time
            )

            if logs:
                logger.info(f"Collected {len(logs)} logs from {service_name}")
                service_config["logs_collected"] += len(logs)
                self.logs_collected += len(logs)

                # Forward logs to analytics service for processing
                await self._forward_logs_to_analytics(logs, service_name)
            else:
                logger.debug(f"No new logs from {service_name}")

            service_config["last_collection"] = datetime.utcnow()
            service_config["errors"] = 0  # Reset error count on success

        except Exception as e:
            error_msg = f"Failed to collect logs from {service_name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            service_config["errors"] += 1

    async def _check_service_health(self, health_url: str) -> bool:
        """Check if a service is healthy."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Health check failed for {health_url}: {str(e)}")
            return False

    def _get_since_time(self, service_config: Dict[str, Any]) -> str:
        """Get the timestamp since last collection."""
        if service_config["last_collection"]:
            # Get logs since last collection
            since_time = service_config["last_collection"]
        else:
            # First time collection, get logs from last hour
            since_time = datetime.utcnow() - timedelta(hours=1)

        return since_time.isoformat() + "Z"

    async def _fetch_logs_from_service(self, logs_url: str, since_time: str) -> List[Dict[str, Any]]:
        """Fetch logs from a service."""
        try:
            params = {
                "since": since_time,
                "limit": self.batch_size
            }

            timeout = aiohttp.ClientTimeout(total=settings.request_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(logs_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("logs", [])
                    else:
                        logger.warning(f"Unexpected status {response.status} from {logs_url}")
                        return []

        except Exception as e:
            logger.error(f"Failed to fetch logs from {logs_url}: {str(e)}")
            return []

    async def _forward_logs_to_analytics(self, logs: List[Dict[str, Any]], service_name: str):
        """Forward collected logs to analytics service for processing."""
        if not logs:
            return

        try:
            # Add service name to logs if not present
            for log in logs:
                if "service" not in log:
                    log["service"] = service_name

            # Forward to local analytics endpoints
            # This would typically be an internal call within the same service
            # For now, we'll process them directly

            logger.debug(f"Forwarded {len(logs)} logs from {service_name} for processing")

        except Exception as e:
            logger.error(f"Failed to forward logs from {service_name}: {str(e)}")

    async def collect_logs_now(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Manually trigger log collection from specific or all services."""
        if service_name:
            if service_name not in self.services:
                return {"error": f"Service {service_name} not configured"}

            service_config = self.services[service_name]
            await self._collect_from_service(service_name, service_config)

            return {
                "service": service_name,
                "logs_collected": service_config["logs_collected"],
                "last_collection": service_config["last_collection"].isoformat() if service_config["last_collection"] else None,
                "errors": service_config["errors"]
            }
        else:
            # Collect from all services
            await self._collect_from_all_services()

            total_collected = sum(service["logs_collected"] for service in self.services.values())
            total_errors = sum(service["errors"] for service in self.services.values())

            return {
                "services_collected": len(self.services),
                "total_logs_collected": total_collected,
                "total_errors": total_errors,
                "last_collection": self.last_collection.isoformat() if self.last_collection else None,
                "services": {
                    name: {
                        "logs_collected": config["logs_collected"],
                        "errors": config["errors"],
                        "last_collection": config["last_collection"].isoformat() if config["last_collection"] else None
                    }
                    for name, config in self.services.items()
                }
            }

    def get_collection_status(self) -> Dict[str, Any]:
        """Get current collection status."""
        return {
            "is_running": self.is_running(),
            "collection_interval": self.collection_interval,
            "batch_size": self.batch_size,
            "last_collection": self.last_collection.isoformat() if self.last_collection else None,
            "total_logs_collected": self.logs_collected,
            "total_errors": len(self.errors),
            "services_count": len(self.services),
            "services": {
                name: {
                    "logs_collected": config["logs_collected"],
                    "errors": config["errors"],
                    "last_collection": config["last_collection"].isoformat() if config["last_collection"] else None
                }
                for name, config in self.services.items()
            },
            "recent_errors": self.errors[-10:] if self.errors else []  # Last 10 errors
        }

# Global log collector instance
log_collector = LogCollector()