#!/usr/bin/env python3
"""
Sample data generator for OpsBuddy InfluxDB.
Generates synthetic logs and metrics data for testing and demonstration.
"""

import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the services directory to Python path to import modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'analytics-service'))

from database import DatabaseManager
from config import settings
from utils import get_logger

logger = get_logger("sample_data_generator")

class SampleDataGenerator:
    """Generates sample data for InfluxDB."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.services = [
            "api-gateway",
            "file-service",
            "utility-service",
            "analytics-service",
            "ui-service"
        ]
        self.log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.operations = [
            "user_login", "file_upload", "data_query", "system_check",
            "api_request", "data_processing", "user_logout", "error_handling"
        ]

    async def generate_sample_logs(self, days: int = 7, logs_per_day: int = 100):
        """Generate sample log entries."""
        logger.info(f"Generating {days * logs_per_day} sample log entries...")

        logs = []
        base_time = datetime.utcnow() - timedelta(days=days)

        for day in range(days):
            current_date = base_time + timedelta(days=day)

            for hour in range(24):
                current_hour = current_date + timedelta(hours=hour)

                # Generate logs for this hour
                for log_num in range(logs_per_day // 24):
                    # Add some randomness to the timestamp
                    timestamp = current_hour + timedelta(
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    )

                    log_entry = {
                        "timestamp": timestamp,
                        "service": random.choice(self.services),
                        "level": random.choices(
                            self.log_levels,
                            weights=[0.3, 0.4, 0.15, 0.1, 0.05]  # More INFO and DEBUG logs
                        )[0],
                        "logger": f"service.{random.choice(self.services)}",
                        "operation": random.choice(self.operations),
                        "host": f"server-{random.randint(1, 3)}",
                        "message": self._generate_log_message(),
                        "data": {
                            "user_id": f"user_{random.randint(1, 100)}",
                            "request_id": f"req_{random.randint(1000, 9999)}",
                            "response_time": round(random.uniform(0.1, 5.0), 2),
                            "status_code": random.choice([200, 201, 400, 404, 500])
                        }
                    }

                    logs.append(log_entry)

        # Store logs in batches
        batch_size = 100
        for i in range(0, len(logs), batch_size):
            batch = logs[i:i + batch_size]
            await self.db_manager.store_logs(batch)
            logger.info(f"Stored batch {i//batch_size + 1}/{(len(logs)-1)//batch_size + 1}")

        logger.info(f"Successfully generated {len(logs)} sample log entries")

    async def generate_sample_metrics(self, days: int = 7):
        """Generate sample metrics."""
        logger.info(f"Generating sample metrics for {days} days...")

        metrics = []
        base_time = datetime.utcnow() - timedelta(days=days)

        for day in range(days):
            current_date = base_time + timedelta(days=day)

            for hour in range(24):
                current_hour = current_date + timedelta(hours=hour)

                # Generate metrics for this hour
                for service in self.services:
                    # Response time metric
                    response_time_metric = {
                        "service": service,
                        "metric_type": "gauge",
                        "value": random.uniform(0.1, 2.0),
                        "timestamp": current_hour,
                        "tags": {
                            "metric_name": "response_time",
                            "unit": "seconds"
                        }
                    }

                    # Request count metric
                    request_count_metric = {
                        "service": service,
                        "metric_type": "counter",
                        "value": random.randint(50, 500),
                        "timestamp": current_hour,
                        "tags": {
                            "metric_name": "request_count",
                            "unit": "count"
                        }
                    }

                    # Error rate metric
                    error_rate_metric = {
                        "service": service,
                        "metric_type": "gauge",
                        "value": random.uniform(0.0, 0.1),  # 0-10% error rate
                        "timestamp": current_hour,
                        "tags": {
                            "metric_name": "error_rate",
                            "unit": "percentage"
                        }
                    }

                    # CPU usage metric
                    cpu_usage_metric = {
                        "service": service,
                        "metric_type": "gauge",
                        "value": random.uniform(10.0, 80.0),  # 10-80% CPU usage
                        "timestamp": current_hour,
                        "tags": {
                            "metric_name": "cpu_usage",
                            "unit": "percentage"
                        }
                    }

                    metrics.extend([
                        response_time_metric,
                        request_count_metric,
                        error_rate_metric,
                        cpu_usage_metric
                    ])

        # Store metrics in batches
        batch_size = 50
        for i in range(0, len(metrics), batch_size):
            batch = metrics[i:i + batch_size]
            await self.db_manager.store_metrics(batch)
            logger.info(f"Stored metrics batch {i//batch_size + 1}/{(len(metrics)-1)//batch_size + 1}")

        logger.info(f"Successfully generated {len(metrics)} sample metric entries")

    def _generate_log_message(self) -> str:
        """Generate a realistic log message."""
        messages = [
            "User authentication successful",
            "File uploaded successfully",
            "Processing request from client",
            "Database connection established",
            "Cache updated successfully",
            "API endpoint called",
            "Data validation completed",
            "System health check passed",
            "Configuration loaded",
            "Request processed in {response_time}ms",
            "Error occurred while processing request",
            "Connection timeout after 30 seconds",
            "Invalid request parameters received",
            "Database query executed successfully",
            "Service started successfully",
            "Memory usage within normal limits",
            "Disk space check completed",
            "SSL certificate validation passed",
            "Load balancer health check received",
            "Background task completed"
        ]

        return random.choice(messages)

async def main():
    """Main function to generate sample data."""
    try:
        # Initialize database connection
        generator = SampleDataGenerator()

        # Connect to database
        connected = await generator.db_manager.connect()
        if not connected:
            logger.error("Failed to connect to InfluxDB")
            return

        logger.info("Connected to InfluxDB successfully")

        # Generate sample data
        await generator.generate_sample_logs(days=7, logs_per_day=50)
        await generator.generate_sample_metrics(days=7)

        # Disconnect
        await generator.db_manager.disconnect()

        logger.info("Sample data generation completed successfully!")

    except Exception as e:
        logger.error(f"Error generating sample data: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())