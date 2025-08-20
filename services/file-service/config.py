"""
Configuration management for OpsBuddy File Service.
Uses Pydantic settings for environment variable validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    service_name: str = "File Service"
    service_version: str = "1.0.0"
    service_host: str = "0.0.0.0"
    service_port: int = 8001
    debug: bool = True
    environment: str = "development"
    
    # Database Configuration
    influxdb_host: str = "localhost"
    influxdb_port: int = 8086
    influxdb_username: Optional[str] = None
    influxdb_password: Optional[str] = None
    influxdb_database: str = "opsbuddy"
    influxdb_token: Optional[str] = "test_token"
    influxdb_org: Optional[str] = "test_org"
    influxdb_url: Optional[str] = "http://localhost:8086"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # File Service Configuration
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    upload_directory: str = "./uploads"
    
    @property
    def allowed_file_types(self) -> List[str]:
        """Get allowed file types from environment or use default."""
        env_types = os.getenv("ALLOWED_FILE_TYPES")
        if env_types:
            return [t.strip() for t in env_types.split(",")]
        return ["txt", "log", "json", "csv", "yaml", "yml"]
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
