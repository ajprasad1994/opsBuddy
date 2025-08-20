"""
Configuration management for OpsBuddy Utility Service.
Uses Pydantic settings for environment variable validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    service_name: str = "Utility Service"
    service_version: str = "1.0.0"
    service_host: str = "0.0.0.0"
    service_port: int = 8002
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
    
    # Utility Service Configuration
    command_timeout: int = 30
    max_command_output: int = 1024 * 1024  # 1MB
    allowed_commands: List[str] = ["ls", "ps", "df", "free", "uptime"]
    
    @property
    def allowed_commands_list(self) -> List[str]:
        """Get allowed commands from environment or use default."""
        env_commands = os.getenv("ALLOWED_COMMANDS")
        if env_commands:
            return [cmd.strip() for cmd in env_commands.split(",")]
        return self.allowed_commands
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
