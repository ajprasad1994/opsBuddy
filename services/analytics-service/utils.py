"""
Utility functions for OpsBuddy Analytics Service.
"""

import time
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance."""
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger

def log_operation(operation: str, service: str, data: Dict[str, Any], level: str = "INFO"):
    """Log operation with structured data."""
    logger = get_logger(f"operation.{service}")

    log_data = {
        "operation": operation,
        "service": service,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data
    }

    message = f"Operation: {operation} - Service: {service}"
    if data:
        message += f" - Data: {json.dumps(data, default=str)}"

    if level.upper() == "ERROR":
        logger.error(message, extra=log_data)
    elif level.upper() == "WARNING":
        logger.warning(message, extra=log_data)
    else:
        logger.info(message, extra=log_data)

def format_timestamp(timestamp: Optional[float] = None) -> str:
    """Format timestamp as ISO string."""
    if timestamp is None:
        timestamp = time.time()
    return datetime.fromtimestamp(timestamp).isoformat() + "Z"

def safe_json_loads(data: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON data."""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None

def safe_json_dumps(data: Any) -> str:
    """Safely serialize data to JSON."""
    try:
        return json.dumps(data, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(data)

def calculate_uptime(start_time: float) -> float:
    """Calculate uptime in seconds."""
    return time.time() - start_time

def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def extract_service_from_url(url: str) -> str:
    """Extract service name from URL."""
    # Simple extraction based on common patterns
    if "gateway" in url:
        return "gateway"
    elif "file" in url:
        return "file-service"
    elif "utility" in url:
        return "utility-service"
    elif "ui" in url:
        return "ui-service"
    elif "analytics" in url:
        return "analytics-service"
    else:
        return "unknown"

def validate_service_name(service_name: str) -> bool:
    """Validate service name format."""
    import re
    pattern = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
    return bool(re.match(pattern, service_name))

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input."""
    if not isinstance(value, str):
        return str(value)

    # Remove potentially harmful characters
    sanitized = "".join(char for char in value if ord(char) >= 32 and ord(char) <= 126)

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized

def generate_log_id() -> str:
    """Generate unique log ID."""
    import uuid
    return str(uuid.uuid4())

def parse_log_level(level: str) -> int:
    """Convert log level string to numeric value."""
    level_map = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50
    }
    return level_map.get(level.upper(), 20)

def is_error_level(level: str) -> bool:
    """Check if log level indicates an error."""
    return level.upper() in ["ERROR", "CRITICAL"]

def is_warning_level(level: str) -> bool:
    """Check if log level indicates a warning."""
    return level.upper() in ["WARNING", "ERROR", "CRITICAL"]

def extract_numeric_metrics(data: Dict[str, Any]) -> Dict[str, float]:
    """Extract numeric values from log data for metrics."""
    numeric_metrics = {}

    for key, value in data.items():
        if isinstance(value, (int, float)):
            numeric_metrics[key] = float(value)
        elif isinstance(value, str):
            # Try to extract numbers from strings
            import re
            numbers = re.findall(r'\d+\.?\d*', value)
            if numbers:
                try:
                    numeric_metrics[f"{key}_extracted"] = float(numbers[0])
                except ValueError:
                    pass

    return numeric_metrics

def calculate_data_size(data: Any) -> int:
    """Calculate approximate size of data in bytes."""
    return len(safe_json_dumps(data).encode('utf-8'))

def get_memory_usage() -> Dict[str, float]:
    """Get current memory usage (Linux only)."""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
            "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            "memory_percent": process.memory_percent()
        }
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}

def get_system_info() -> Dict[str, Any]:
    """Get basic system information."""
    try:
        import platform
        import os

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "cpu_count": os.cpu_count(),
            "pid": os.getpid(),
            "uptime": time.time()  # This would need to be calculated from system start
        }
    except Exception as e:
        return {"error": str(e)}

def create_health_response(service_name: str, status: str, **kwargs) -> Dict[str, Any]:
    """Create standardized health check response."""
    response = {
        "status": status,
        "service": service_name,
        "timestamp": format_timestamp(),
        **kwargs
    }

    if status == "healthy":
        response.update({
            "database": "healthy",
            "log_collector": "healthy"
        })
    elif status == "degraded":
        response.update({
            "database": kwargs.get("database", "unhealthy"),
            "log_collector": kwargs.get("log_collector", "unhealthy")
        })

    return response

def retry_async(async_func, max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying async functions."""
    async def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await async_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying...")
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"All {max_retries} attempts failed")

        raise last_exception

    return wrapper

class Timer:
    """Context manager for timing operations."""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        logger.debug(f"{self.name} took {elapsed:.3f} seconds")

class RateLimiter:
    """Simple rate limiter for API endpoints."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.min_interval = 60.0 / requests_per_minute

    async def acquire(self) -> bool:
        """Acquire permission to proceed."""
        now = time.time()

        # Remove old requests
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]

        if len(self.requests) >= self.requests_per_minute:
            return False

        self.requests.append(now)
        return True

    async def wait_for_slot(self):
        """Wait until a slot is available."""
        while not await self.acquire():
            await asyncio.sleep(self.min_interval)

# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=100)