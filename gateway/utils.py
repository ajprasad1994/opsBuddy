"""
Utility functions for OpsBuddy API Gateway.
Includes logging, health checks, circuit breaker, and request handling utilities.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import httpx
from fastapi import Request, Response
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class CircuitBreaker:
    """Simple circuit breaker implementation for service resilience."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        return True  # HALF_OPEN
    
    def on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None
    
    def on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ServiceHealthChecker:
    """Service health monitoring and checking."""
    
    def __init__(self, services: Dict[str, Any]):
        self.services = services
        self.health_status = {}
        self.last_check = {}
    
    async def check_service_health(self, service_name: str, service_config: Any) -> Dict[str, Any]:
        """Check health of a specific service."""
        try:
            health_url = f"http://{service_config.host}:{service_config.port}{service_config.health_endpoint}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(health_url)
                
                if response.status_code == 200:
                    health_data = response.json()
                    self.health_status[service_name] = {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds(),
                        "last_check": datetime.now(timezone.utc).isoformat(),
                        "details": health_data
                    }
                else:
                    self.health_status[service_name] = {
                        "status": "unhealthy",
                        "response_time": response.elapsed.total_seconds(),
                        "last_check": datetime.now(timezone.utc).isoformat(),
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            self.health_status[service_name] = {
                "status": "unhealthy",
                "last_check": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
        
        self.last_check[service_name] = datetime.now(timezone.utc)
        return self.health_status[service_name]
    
    async def check_all_services(self) -> Dict[str, Any]:
        """Check health of all services."""
        tasks = []
        for service_name, service_config in self.services.items():
            task = self.check_service_health(service_name, service_config)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.health_status
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get current health status of a service."""
        return self.health_status.get(service_name, {"status": "unknown"})


def log_request(request: Request, target_service: str, method: str, path: str):
    """Log incoming request details."""
    logger.info(
        "API Gateway Request",
        method=method,
        path=path,
        target_service=target_service,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown"),
        timestamp=datetime.now(timezone.utc).isoformat()
    )


def log_response(response: Response, target_service: str, method: str, path: str, status_code: int):
    """Log response details."""
    logger.info(
        "API Gateway Response",
        method=method,
        path=path,
        target_service=target_service,
        status_code=status_code,
        response_time=response.headers.get("x-response-time", "unknown"),
        timestamp=datetime.now(timezone.utc).isoformat()
    )


def log_error(error: Exception, target_service: str, method: str, path: str):
    """Log error details."""
    logger.error(
        "API Gateway Error",
        method=method,
        path=path,
        target_service=target_service,
        error_type=type(error).__name__,
        error_message=str(error),
        timestamp=datetime.now(timezone.utc).isoformat()
    )


async def forward_request(
    request: Request,
    target_url: str,
    timeout: int = 30
) -> Tuple[Response, float]:
    """Forward request to target service and return response with timing."""
    start_time = time.time()
    
    # Prepare headers (exclude host and connection headers)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("connection", None)
    
    # Prepare query parameters
    query_params = dict(request.query_params)
    
    # Prepare body for different content types
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
        except Exception:
            pass
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=query_params,
                content=body
            )
            
            response_time = time.time() - start_time
            
            # Create FastAPI Response object
            fastapi_response = Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
            
            # Add response time header
            fastapi_response.headers["x-response-time"] = f"{response_time:.3f}s"
            
            return fastapi_response, response_time
            
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Failed to forward request to {target_url}: {str(e)}")
        raise


def determine_target_service(path: str, routing_rules: Dict[str, str]) -> Optional[str]:
    """Determine which service should handle the request based on path."""
    for route_prefix, service_name in routing_rules.items():
        if path.startswith(route_prefix):
            return service_name
    return None


def build_target_url(service_name: str, service_urls: Dict[str, str], path: str) -> str:
    """Build the target URL for forwarding the request."""
    base_url = service_urls.get(service_name)
    if not base_url:
        raise ValueError(f"Unknown service: {service_name}")
    
    # Remove the API prefix from the path when forwarding
    if path.startswith("/api/"):
        # Extract the service-specific path
        path_parts = path.split("/", 3)  # Split into ["", "api", "service", "rest_of_path"]
        if len(path_parts) >= 3:
            service_path = "/" + path_parts[2]  # Get "/service"
            remaining_path = "/" + "/".join(path_parts[3:]) if len(path_parts) > 3 else ""
            return f"{base_url}{service_path}{remaining_path}"
    
    return f"{base_url}{path}"
