"""
Logging configuration for OpsBuddy application.
Provides structured logging with JSON format and configurable levels.
"""

import logging
import sys
from typing import Any, Dict
from app.config import settings


def setup_logger() -> logging.Logger:
    """Set up and configure the application logger."""
    
    # Create logger
    logger = logging.getLogger("opsbuddy")
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Set formatter based on configuration
    if settings.log_format.lower() == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance with the specified name."""
    if name:
        return logging.getLogger(f"opsbuddy.{name}")
    return logging.getLogger("opsbuddy")


# Initialize the main logger
logger = setup_logger()


def log_operation(operation: str, service: str, details: Dict[str, Any] = None, level: str = "INFO"):
    """Log a CRUD or database operation with structured information."""
    
    log_data = {
        "operation": operation,
        "service": service,
        "timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None)),
    }
    
    if details:
        log_data.update(details)
    
    log_message = f"Operation: {operation} | Service: {service}"
    if details:
        log_message += f" | Details: {details}"
    
    log_func = getattr(logger, level.lower())
    log_func(log_message, extra=log_data)
