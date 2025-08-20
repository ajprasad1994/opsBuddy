"""
Utility functions for OpsBuddy File Service.
Includes logging and operation tracking.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any
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


def get_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_operation(operation: str, service: str, data: Dict[str, Any], level: str = "INFO"):
    """Log an operation with structured data."""
    logger = get_logger(service)
    
    log_data = {
        "operation": operation,
        "service": service,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data
    }
    
    if level.upper() == "ERROR":
        logger.error("Operation failed", **log_data)
    elif level.upper() == "WARNING":
        logger.warning("Operation warning", **log_data)
    else:
        logger.info("Operation completed", **log_data)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def validate_file_type(filename: str, allowed_types: list) -> bool:
    """Validate if file type is allowed."""
    if not filename or '.' not in filename:
        return False
    
    file_ext = filename.split('.')[-1].lower()
    return file_ext in allowed_types


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    if not filename or '.' not in filename:
        return ""
    
    return filename.split('.')[-1].lower()


def create_file_id() -> str:
    """Generate a unique file ID."""
    import uuid
    return str(uuid.uuid4())


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime object."""
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        # Fallback to current time if parsing fails
        return get_current_timestamp()
