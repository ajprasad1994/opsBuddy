"""
Configuration settings for OpsBuddy Analytics Service.
"""

import os
from typing import List, Optional

class Settings:
    """Application settings with environment variable support."""

    # Service Configuration
    service_name: str = "OpsBuddy Analytics Service"
    service_version: str = "1.0.0"
    service_host: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    service_port: int = int(os.getenv("SERVICE_PORT", "8003"))
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

    # Log Collection Configuration
    log_collection_interval: int = int(os.getenv("LOG_COLLECTION_INTERVAL", "30"))  # seconds
    batch_size: int = int(os.getenv("BATCH_SIZE", "100"))  # logs per batch
    retention_days: int = int(os.getenv("RETENTION_DAYS", "30"))  # days to keep logs

    # Service URLs for log collection
    service_urls: dict = {
        "gateway": os.getenv("GATEWAY_URL", "http://api-gateway:8000"),
        "file-service": os.getenv("FILE_SERVICE_URL", "http://file-service:8001"),
        "utility-service": os.getenv("UTILITY_SERVICE_URL", "http://utility-service:8002"),
        "ui-service": os.getenv("UI_SERVICE_URL", "http://ui-service:3000")
    }

    # Log validation settings
    max_log_size: int = int(os.getenv("MAX_LOG_SIZE", "1048576"))  # 1MB max log entry
    allowed_log_levels: List[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    required_log_fields: List[str] = ["timestamp", "level", "logger", "message", "service"]

    # Analytics settings
    default_query_limit: int = int(os.getenv("DEFAULT_QUERY_LIMIT", "1000"))
    max_query_limit: int = int(os.getenv("MAX_QUERY_LIMIT", "10000"))
    cache_timeout: int = int(os.getenv("CACHE_TIMEOUT", "300"))  # 5 minutes

    # Performance settings
    connection_pool_size: int = int(os.getenv("CONNECTION_POOL_SIZE", "10"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds

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
    def log_collection_config(self) -> dict:
        """Get log collection configuration."""
        return {
            "interval": self.log_collection_interval,
            "batch_size": self.batch_size,
            "service_urls": self.service_urls,
            "timeout": self.request_timeout
        }

# Global settings instance
settings = Settings()