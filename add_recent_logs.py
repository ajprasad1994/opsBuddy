#!/usr/bin/env python3
"""
Script to add recent error and critical logs for testing Analytics tab
"""

import asyncio
import random
import json
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# InfluxDB connection details
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "your_influxdb_token_here"
INFLUXDB_ORG = "opsbuddy"
INFLUXDB_BUCKET = "opsbuddy"

def add_recent_logs():
    """Add recent error and critical logs to InfluxDB"""

    # Initialize InfluxDB client
    client = InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )

    write_api = client.write_api(write_options=SYNCHRONOUS)

    services = ["api-gateway", "file-service", "utility-service", "analytics-service", "ui-service"]
    operations = ["user_login", "file_upload", "data_query", "api_request", "system_check"]
    hosts = ["server-1", "server-2", "server-3"]

    # Generate logs for the last 30 minutes
    base_time = datetime.now(timezone.utc)
    print(f"Adding recent logs starting from {base_time}")

    for i in range(20):  # Generate 20 recent logs
        # Create timestamp within last 30 minutes
        minutes_ago = random.randint(1, 30)
        timestamp = base_time - timedelta(minutes=minutes_ago)

        # Choose log level (more errors and critical)
        level = random.choices(
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            weights=[0.1, 0.2, 0.2, 0.3, 0.2]  # Favor errors and critical
        )[0]

        service = random.choice(services)
        operation = random.choice(operations)
        host = random.choice(hosts)

        # Create log message based on level
        if level == "ERROR":
            messages = [
                "Database connection failed",
                "API request timeout",
                "Invalid user credentials",
                "File upload failed - disk space low",
                "Service unavailable"
            ]
        elif level == "CRITICAL":
            messages = [
                "System out of memory",
                "Database connection lost",
                "Critical security breach detected",
                "Service crashed - automatic restart failed",
                "Data corruption detected"
            ]
        else:
            messages = [
                "User authentication successful",
                "File uploaded successfully",
                "Data query completed",
                "System health check passed"
            ]

        message = random.choice(messages)

        # Create InfluxDB point
        point = Point("logs") \
            .tag("service", service) \
            .tag("level", level) \
            .tag("logger", f"service.{service}") \
            .tag("operation", operation) \
            .tag("host", host) \
            .field("message", message) \
            .field("data_request_id", f"req_{random.randint(1000, 9999)}") \
            .field("data_response_time", round(random.uniform(0.1, 5.0), 2)) \
            .field("data_status_code", random.choice([200, 400, 404, 500, 503])) \
            .field("data_user_id", f"user_{random.randint(1, 100)}") \
            .field("data_size", random.randint(100, 10000)) \
            .time(timestamp)

        # Write to InfluxDB
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)

        print(f"Added {level} log: {service} - {operation} - {message}")

    # Close client
    client.close()
    print("Finished adding recent logs!")

if __name__ == "__main__":
    add_recent_logs()