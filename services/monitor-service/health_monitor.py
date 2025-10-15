"""
Health monitoring service for OpsBuddy.
Polls health endpoints of all microservices and tracks their status.
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from config import settings
from redis_client import redis_client

logger = logging.getLogger("monitor_service.health_monitor")

class ServiceStatus(Enum):
    """Service health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

@dataclass
class ServiceHealth:
    """Service health information."""
    name: str
    url: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    response_time: float = 0.0
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    service_name: str
    status: ServiceStatus
    response_time: float
    timestamp: datetime
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

class HealthMonitor:
    """Monitors health of all microservices."""

    def __init__(self):
        self.services: Dict[str, ServiceHealth] = {}
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._initialize_services()

    def _initialize_services(self):
        """Initialize service health objects."""
        for service_name, url in settings.service_urls.items():
            self.services[service_name] = ServiceHealth(
                name=service_name,
                url=url,
                status=ServiceStatus.UNKNOWN
            )

    async def start_monitoring(self):
        """Start the health monitoring process."""
        if self._monitoring:
            logger.warning("Health monitoring already running")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started health monitoring")

    async def stop_monitoring(self):
        """Stop the health monitoring process."""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped health monitoring")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info(f"Starting monitoring loop with interval: {settings.health_check_interval}s")

        while self._monitoring:
            try:
                logger.debug("Running health check cycle...")
                await self._check_all_services()
                logger.debug("Health check cycle completed")
                await asyncio.sleep(settings.health_check_interval)
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(settings.retry_delay)

    async def _check_all_services(self):
        """Check health of all services."""
        logger.debug(f"Starting health check for {len(self.services)} services")
        tasks = []
        for service_name, service_health in self.services.items():
            task = asyncio.create_task(self._check_service_health(service_name))
            tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug(f"Completed health checks for {len(tasks)} services")

            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error checking service health: {str(result)}")
                else:
                    await self._process_health_result(result)

    async def _check_service_health(self, service_name: str) -> HealthCheckResult:
        """Check health of a specific service."""
        service_health = self.services[service_name]
        start_time = time.time()

        try:
            endpoint = settings.health_check_endpoints.get(service_name, "/health")
            url = f"{service_health.url}{endpoint}"

            timeout = aiohttp.ClientTimeout(total=settings.service_timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response_time = time.time() - start_time

                    if response.status < 400:
                        # Try to parse response as JSON for detailed health info
                        try:
                            health_data = await response.json()
                            status = self._determine_status_from_response(health_data)
                        except:
                            # If not JSON or parsing fails, assume healthy if status < 400
                            status = ServiceStatus.HEALTHY if response.status < 500 else ServiceStatus.UNHEALTHY

                        return HealthCheckResult(
                            service_name=service_name,
                            status=status,
                            response_time=response_time,
                            timestamp=datetime.utcnow(),
                            details={"http_status": response.status}
                        )
                    else:
                        return HealthCheckResult(
                            service_name=service_name,
                            status=ServiceStatus.UNHEALTHY,
                            response_time=response_time,
                            timestamp=datetime.utcnow(),
                            error_message=f"HTTP {response.status}",
                            details={"http_status": response.status}
                        )

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time=response_time,
                timestamp=datetime.utcnow(),
                error_message="Timeout"
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time=response_time,
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )

    def _determine_status_from_response(self, health_data: Dict[str, Any]) -> ServiceStatus:
        """Determine service status from health check response."""
        if not isinstance(health_data, dict):
            return ServiceStatus.HEALTHY

        # Check for explicit status field
        status = health_data.get("status", "").lower()

        if status == "healthy":
            return ServiceStatus.HEALTHY
        elif status == "unhealthy":
            return ServiceStatus.UNHEALTHY
        elif status == "degraded":
            return ServiceStatus.DEGRADED

        # Check for nested service status
        service_status = health_data.get("service", {})
        if isinstance(service_status, dict):
            service_state = service_status.get("status", "").lower()
            if service_state in ["healthy", "unhealthy", "degraded"]:
                return ServiceStatus(service_state)

        # Default to healthy if we can't determine status
        return ServiceStatus.HEALTHY

    async def _process_health_result(self, result: HealthCheckResult):
        """Process health check result and update service status."""
        service_name = result.service_name
        service_health = self.services[service_name]

        # Update service health
        old_status = service_health.status
        service_health.status = result.status
        service_health.response_time = result.response_time
        service_health.last_check = result.timestamp
        service_health.error_message = result.error_message
        service_health.details = result.details

        # Update consecutive failures
        if result.status == ServiceStatus.HEALTHY:
            service_health.consecutive_failures = 0
        else:
            service_health.consecutive_failures += 1

        # Log status change
        if old_status != result.status:
            logger.info(
                f"Service {service_name} status changed: {old_status.value} -> {result.status.value}"
            )

        # Publish update to Redis
        await self._publish_service_update(service_name, service_health)

    async def _publish_service_update(self, service_name: str, service_health: ServiceHealth):
        """Publish service health update to Redis."""
        status_data = {
            "health": service_health.status.value,
            "response_time": service_health.response_time,
            "last_check": service_health.last_check.isoformat() if service_health.last_check else None,
            "consecutive_failures": service_health.consecutive_failures,
            "error_message": service_health.error_message,
            "details": service_health.details
        }

        success = await redis_client.publish_health_update(service_name, status_data)
        if not success:
            logger.warning(f"Failed to publish health update for {service_name}")

    def get_service_status(self, service_name: str) -> Optional[ServiceHealth]:
        """Get current status of a specific service."""
        return self.services.get(service_name)

    def get_all_service_statuses(self) -> Dict[str, ServiceHealth]:
        """Get status of all services."""
        return self.services.copy()

    def get_service_group_status(self, group_name: str) -> Dict[str, ServiceHealth]:
        """Get status of services in a specific group."""
        if group_name not in settings.service_groups:
            return {}

        services_in_group = settings.service_groups[group_name]
        return {
            name: self.services[name]
            for name in services_in_group
            if name in self.services
        }

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        total_services = len(self.services)
        healthy_services = sum(1 for s in self.services.values() if s.status == ServiceStatus.HEALTHY)
        unhealthy_services = sum(1 for s in self.services.values() if s.status == ServiceStatus.UNHEALTHY)
        degraded_services = sum(1 for s in self.services.values() if s.status == ServiceStatus.DEGRADED)
        unknown_services = sum(1 for s in self.services.values() if s.status == ServiceStatus.UNKNOWN)

        # Determine overall status
        if unhealthy_services > 0:
            overall_status = ServiceStatus.UNHEALTHY
        elif degraded_services > 0:
            overall_status = ServiceStatus.DEGRADED
        elif healthy_services == total_services:
            overall_status = ServiceStatus.HEALTHY
        else:
            overall_status = ServiceStatus.UNKNOWN

        return {
            "overall_status": overall_status.value,
            "total_services": total_services,
            "healthy": healthy_services,
            "unhealthy": unhealthy_services,
            "degraded": degraded_services,
            "unknown": unknown_services,
            "timestamp": datetime.utcnow().isoformat()
        }

    def is_monitoring(self) -> bool:
        """Check if monitoring is currently running."""
        return self._monitoring

# Global health monitor instance
health_monitor = HealthMonitor()