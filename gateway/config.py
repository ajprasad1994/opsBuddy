"""
Configuration management for OpsBuddy API Gateway.
Defines service endpoints, routing rules, and gateway settings.
"""

from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
import os


class ServiceConfig(BaseSettings):
    """Configuration for individual microservices."""
    
    name: str
    host: str = "localhost"
    port: int
    health_endpoint: str = "/health"
    timeout: int = 30
    retries: int = 3
    circuit_breaker_threshold: int = 5


class GatewaySettings(BaseSettings):
    """API Gateway configuration settings."""
    
    # Gateway Configuration
    gateway_name: str = "OpsBuddy API Gateway"
    gateway_version: str = "1.0.0"
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    debug: bool = True
    environment: str = "development"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Service Discovery Configuration
    service_discovery_enabled: bool = True
    service_health_check_interval: int = 30  # seconds
    
    # Rate Limiting (future enhancement)
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Circuit Breaker Configuration
    circuit_breaker_enabled: bool = True
    circuit_breaker_timeout: int = 60  # seconds
    
    # CORS Configuration
    cors_origins: List[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
    
    # Service Endpoints
    @property
    def services(self) -> Dict[str, ServiceConfig]:
        """Get service configurations."""
        return {
            "file": ServiceConfig(
                name="file-service",
                host=os.getenv("FILE_SERVICE_HOST", "localhost"),
                port=int(os.getenv("FILE_SERVICE_PORT", "8001")),
                health_endpoint="/health"
            ),
            "utility": ServiceConfig(
                name="utility-service", 
                host=os.getenv("UTILITY_SERVICE_HOST", "localhost"),
                port=int(os.getenv("UTILITY_SERVICE_PORT", "8002")),
                health_endpoint="/health"
            ),
            "analytics": ServiceConfig(
                name="analytics-service",
                host=os.getenv("ANALYTICS_SERVICE_HOST", "localhost"),
                port=int(os.getenv("ANALYTICS_SERVICE_PORT", "8003")),
                health_endpoint="/health"
            ),
            "incident": ServiceConfig(
                name="incident-service",
                host=os.getenv("INCIDENT_SERVICE_HOST", "localhost"),
                port=int(os.getenv("INCIDENT_SERVICE_PORT", "8004")),
                health_endpoint="/health"
            ),
            "timeseries": ServiceConfig(
                name="timeseries-service",
                host=os.getenv("TIMESERIES_SERVICE_HOST", "localhost"),
                port=int(os.getenv("TIMESERIES_SERVICE_PORT", "8004")),
                health_endpoint="/health"
            )
        }
    
    @property
    def service_urls(self) -> Dict[str, str]:
        """Get service base URLs."""
        return {
            service_name: f"http://{config.host}:{config.port}"
            for service_name, config in self.services.items()
        }
    
    @property
    def routing_rules(self) -> Dict[str, str]:
        """Get routing rules for API paths."""
        return {
            "/api/files": "file",
            "/api/utils": "utility",
            "/api/analytics": "analytics",
            "/api/incidents": "incident",
            "/api/timeseries": "timeseries"
        }
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


# Global settings instance
settings = GatewaySettings()
