"""
Configuration settings for OpsBuddy Monitor Service.
"""

import os
from typing import List, Dict, Any

class Settings:
    """Application settings with environment variable support."""

    # Service Configuration
    service_name: str = "OpsBuddy Monitor Service"
    service_version: str = "1.0.0"
    service_host: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    service_port: int = int(os.getenv("SERVICE_PORT", "8005"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")

    # Redis Configuration
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Health Monitoring Configuration
    health_check_interval: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # seconds
    service_timeout: int = int(os.getenv("SERVICE_TIMEOUT", "10"))  # seconds
    max_consecutive_failures: int = int(os.getenv("MAX_CONSECUTIVE_FAILURES", "3"))
    retry_delay: int = int(os.getenv("RETRY_DELAY", "5"))  # seconds

    # Service URLs for health monitoring
    service_urls: Dict[str, str] = {
        "api-gateway": os.getenv("GATEWAY_URL", "http://api-gateway:8000"),
        "file-service": os.getenv("FILE_SERVICE_URL", "http://file-service:8001"),
        "utility-service": os.getenv("UTILITY_SERVICE_URL", "http://utility-service:8002"),
        "analytics-service": os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8003"),
        "incident-service": os.getenv("INCIDENT_SERVICE_URL", "http://incident-service:8004"),
        "ui-service": os.getenv("UI_SERVICE_URL", "http://ui-service:3000"),
        "monitor-service": f"http://monitor-service:{service_port}"
    }

    # Redis Channels
    redis_channel_health: str = os.getenv("REDIS_CHANNEL_HEALTH", "service_health")
    redis_channel_websocket: str = os.getenv("REDIS_CHANNEL_WEBSOCKET", "websocket_updates")
    redis_channel_errors: str = os.getenv("REDIS_CHANNEL_ERRORS", "error_logs")

    # WebSocket Configuration
    websocket_ping_interval: int = int(os.getenv("WEBSOCKET_PING_INTERVAL", "20"))  # seconds
    websocket_ping_timeout: int = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "10"))  # seconds
    max_websocket_connections: int = int(os.getenv("MAX_WEBSOCKET_CONNECTIONS", "1000"))

    # Health Check Configuration
    health_check_endpoints: Dict[str, str] = {
        "api-gateway": "/health",
        "file-service": "/health",
        "utility-service": "/health",
        "analytics-service": "/health",
        "incident-service": "/health",
        "ui-service": "/health",
        "monitor-service": "/health"
    }

    # Service Groups for monitoring
    service_groups: Dict[str, List[str]] = {
        "core": ["api-gateway", "file-service", "utility-service"],
        "analytics": ["analytics-service", "incident-service"],
        "ui": ["ui-service"],
        "monitoring": ["monitor-service"]
    }

    @property
    def redis_client_config(self) -> Dict[str, Any]:
        """Get Redis client configuration."""
        config = {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "decode_responses": True
        }
        if self.redis_password:
            config["password"] = self.redis_password
        return config

    @property
    def health_monitoring_config(self) -> Dict[str, Any]:
        """Get health monitoring configuration."""
        return {
            "interval": self.health_check_interval,
            "timeout": self.service_timeout,
            "max_failures": self.max_consecutive_failures,
            "retry_delay": self.retry_delay,
            "service_urls": self.service_urls,
            "endpoints": self.health_check_endpoints
        }

    @property
    def websocket_config(self) -> Dict[str, Any]:
        """Get WebSocket configuration."""
        return {
            "ping_interval": self.websocket_ping_interval,
            "ping_timeout": self.websocket_ping_timeout,
            "max_connections": self.max_websocket_connections
        }

# Global settings instance
settings = Settings()