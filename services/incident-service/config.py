"""
Configuration settings for OpsBuddy Incident Service.
"""

import os
from typing import List, Optional

class Settings:
    """Application settings with environment variable support."""

    # Service Configuration
    service_name: str = "OpsBuddy Incident Service"
    service_version: str = "1.0.0"
    service_host: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    service_port: int = int(os.getenv("SERVICE_PORT", "8004"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")

    # Database Configuration (InfluxDB)
    influxdb_host: str = os.getenv("INFLUXDB_HOST", "localhost")
    influxdb_port: int = int(os.getenv("INFLUXDB_PORT", "8086"))
    influxdb_token: str = os.getenv("INFLUXDB_TOKEN", "your_influxdb_token_here")
    influxdb_org: str = os.getenv("INFLUXDB_ORG", "opsbuddy")
    influxdb_database: str = os.getenv("INFLUXDB_DATABASE", "opsbuddy")
    influxdb_url: str = os.getenv("INFLUXDB_URL", "http://localhost:8086")

    # Redis Configuration
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Incident Monitoring Configuration
    monitoring_interval: int = int(os.getenv("MONITORING_INTERVAL", "30"))  # seconds
    query_batch_size: int = int(os.getenv("QUERY_BATCH_SIZE", "1000"))  # logs per query
    error_retention_hours: int = int(os.getenv("ERROR_RETENTION_HOURS", "24"))  # hours to keep error data

    # Redis Pub/Sub Configuration
    redis_channel_incidents: str = os.getenv("REDIS_CHANNEL_INCIDENTS", "incidents")
    redis_channel_errors: str = os.getenv("REDIS_CHANNEL_ERRORS", "error_logs")
    redis_channel_analytics: str = os.getenv("REDIS_CHANNEL_ANALYTICS", "analytics_updates")

    # Service URLs for monitoring
    service_urls: dict = {
        "gateway": os.getenv("GATEWAY_URL", "http://api-gateway:8000"),
        "file-service": os.getenv("FILE_SERVICE_URL", "http://file-service:8001"),
        "utility-service": os.getenv("UTILITY_SERVICE_URL", "http://utility-service:8002"),
        "analytics-service": os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8003"),
        "ui-service": os.getenv("UI_SERVICE_URL", "http://ui-service:3000")
    }

    # Log filtering settings
    error_levels: List[str] = ["ERROR", "CRITICAL", "FATAL"]
    warning_levels: List[str] = ["WARNING", "ERROR", "CRITICAL", "FATAL"]
    monitored_operations: List[str] = ["*"]  # Monitor all operations by default

    # Performance settings
    connection_pool_size: int = int(os.getenv("CONNECTION_POOL_SIZE", "10"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds
    max_query_time: int = int(os.getenv("MAX_QUERY_TIME", "60"))  # seconds

    @property
    def influxdb_client_config(self) -> dict:
        """Get InfluxDB client configuration."""
        return {
            "url": self.influxdb_url,
            "token": self.influxdb_token,
            "org": self.influxdb_org,
            "timeout": self.request_timeout * 1000  # milliseconds
        }

    @property
    def redis_client_config(self) -> dict:
        """Get Redis client configuration."""
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "password": self.redis_password if self.redis_password else None,
            "decode_responses": True,
            "socket_connect_timeout": self.request_timeout,
            "socket_timeout": self.request_timeout
        }

    @property
    def monitoring_config(self) -> dict:
        """Get monitoring configuration."""
        return {
            "interval": self.monitoring_interval,
            "batch_size": self.query_batch_size,
            "error_retention_hours": self.error_retention_hours,
            "timeout": self.request_timeout
        }

# Global settings instance
settings = Settings()