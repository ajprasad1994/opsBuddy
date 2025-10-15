#!/usr/bin/env python3
"""
Generate recent ERROR and CRITICAL logs for testing Analytics tab
"""

import asyncio
import random
import json
from datetime import datetime, timedelta, timezone
import requests

def generate_recent_error_logs():
    """Generate recent error logs via API calls"""

    # Analytics service endpoint
    analytics_url = "http://localhost:8003/logs"

    services = ["api-gateway", "file-service", "utility-service", "analytics-service", "ui-service"]
    operations = ["user_login", "file_upload", "data_query", "api_request", "system_check"]
    error_messages = {
        "ERROR": [
            "Database connection failed",
            "API request timeout",
            "Invalid user credentials",
            "File upload failed - disk space low",
            "Service unavailable",
            "Authentication token expired",
            "Permission denied",
            "Resource not found"
        ],
        "CRITICAL": [
            "System out of memory",
            "Database connection lost",
            "Critical security breach detected",
            "Service crashed - automatic restart failed",
            "Data corruption detected",
            "Disk failure detected",
            "Network connectivity lost"
        ]
    }

    print(f"Generating recent ERROR and CRITICAL logs...")

    # Generate logs for the last 60 minutes
    base_time = datetime.now(timezone.utc)

    for i in range(15):  # Generate 15 recent logs
        # Create timestamp within last 60 minutes
        minutes_ago = random.randint(1, 60)
        timestamp = base_time - timedelta(minutes=minutes_ago)

        # Choose log level (focus on errors and critical)
        level = random.choices(
            ["ERROR", "CRITICAL"],
            weights=[0.7, 0.3]  # 70% ERROR, 30% CRITICAL
        )[0]

        service = random.choice(services)
        operation = random.choice(operations)
        message = random.choice(error_messages[level])

        # Create log entry similar to what the analytics service expects
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "service": service,
            "level": level,
            "logger": f"service.{service}",
            "operation": operation,
            "host": f"server-{random.randint(1, 3)}",
            "message": message,
            "data": {
                "user_id": f"user_{random.randint(1, 100)}",
                "request_id": f"req_{random.randint(1000, 9999)}",
                "response_time": round(random.uniform(0.1, 5.0), 2),
                "status_code": random.choice([400, 401, 403, 404, 500, 503])
            }
        }

        try:
            # Try to send to analytics service (it might not have an endpoint for this)
            # For now, just print the log entry
            print(f"Generated {level} log: {service} - {operation} - {message} at {timestamp}")
        except Exception as e:
            print(f"Error sending log: {e}")

    print("Finished generating recent error logs!")

if __name__ == "__main__":
    generate_recent_error_logs()