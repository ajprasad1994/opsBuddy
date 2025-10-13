"""
Log transformation and validation service for OpsBuddy Analytics Service.
Transforms incoming logs into standardized schema for storage.
"""

import time
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import re

from config import settings
from utils import get_logger

logger = get_logger("log_transformer")

class LogTransformer:
    """Transforms and validates log entries."""

    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()

    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize log validation rules."""
        return {
            "timestamp": {
                "required": True,
                "type": "string",
                "format": "iso_datetime"
            },
            "level": {
                "required": True,
                "type": "string",
                "allowed_values": settings.allowed_log_levels
            },
            "logger": {
                "required": True,
                "type": "string",
                "min_length": 1,
                "max_length": 100
            },
            "message": {
                "required": True,
                "type": "string",
                "min_length": 1,
                "max_length": 10000
            },
            "service": {
                "required": True,
                "type": "string",
                "min_length": 1,
                "max_length": 50
            },
            "operation": {
                "required": False,
                "type": "string",
                "max_length": 100
            },
            "data": {
                "required": False,
                "type": "object"
            },
            "host": {
                "required": False,
                "type": "string",
                "max_length": 100
            },
            "user_id": {
                "required": False,
                "type": "string",
                "max_length": 100
            }
        }

    async def transform_log(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Transform and validate a log entry."""
        try:
            # Validate log entry
            validated_data = await self._validate_log_entry(log_entry)

            # Generate standardized log entry
            standardized_log = {
                "log_id": str(uuid.uuid4()),
                "timestamp": self._normalize_timestamp(validated_data.get("timestamp")),
                "level": validated_data.get("level", "INFO").upper(),
                "logger": validated_data.get("logger", "unknown"),
                "message": validated_data.get("message", ""),
                "service": validated_data.get("service", "unknown"),
                "operation": validated_data.get("operation"),
                "data": validated_data.get("data", {}),
                "host": validated_data.get("host", "unknown"),
                "user_id": validated_data.get("user_id"),
                "received_at": datetime.utcnow().isoformat() + "Z",
                "processing_time": time.time(),
                "schema_version": "1.0"
            }

            # Add derived fields
            standardized_log.update(self._derive_additional_fields(standardized_log))

            logger.debug(f"Transformed log entry: {standardized_log['log_id']}")
            return standardized_log

        except Exception as e:
            logger.error(f"Failed to transform log entry: {str(e)}")
            raise ValueError(f"Log transformation failed: {str(e)}")

    async def _validate_log_entry(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Validate log entry against schema rules."""
        if not isinstance(log_entry, dict):
            raise ValueError("Log entry must be a dictionary")

        validated_data = {}
        errors = []

        # Check required fields
        for field, rules in self.validation_rules.items():
            if rules.get("required", False) and field not in log_entry:
                errors.append(f"Required field '{field}' is missing")
                continue

            if field in log_entry:
                value = log_entry[field]

                # Type validation
                if rules.get("type") == "string":
                    if value is not None and not isinstance(value, str):
                        errors.append(f"Field '{field}' must be a string")
                        continue
                    # Length validation
                    if value is not None:
                        if "min_length" in rules and len(value) < rules["min_length"]:
                            errors.append(f"Field '{field}' must be at least {rules['min_length']} characters")
                        if "max_length" in rules and len(value) > rules["max_length"]:
                            errors.append(f"Field '{field}' must be at most {rules['max_length']} characters")

                elif rules.get("type") == "object":
                    if value is not None and not isinstance(value, dict):
                        errors.append(f"Field '{field}' must be an object")
                        continue

                # Format validation for timestamp
                if field == "timestamp" and rules.get("format") == "iso_datetime":
                    if not self._is_valid_iso_datetime(value):
                        errors.append(f"Field '{field}' must be in ISO datetime format")

                # Allowed values validation
                if "allowed_values" in rules and value not in rules["allowed_values"]:
                    errors.append(f"Field '{field}' must be one of: {rules['allowed_values']}")

                validated_data[field] = value

        if errors:
            raise ValueError(f"Log validation failed: {'; '.join(errors)}")

        return validated_data

    def _normalize_timestamp(self, timestamp_str: str) -> str:
        """Normalize timestamp to ISO format with timezone."""
        try:
            # Parse the timestamp
            if timestamp_str.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(timestamp_str)

            # Ensure UTC timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.isoformat()
        except ValueError:
            # If parsing fails, use current time
            logger.warning(f"Invalid timestamp format: {timestamp_str}, using current time")
            return datetime.utcnow().isoformat() + "Z"

    def _is_valid_iso_datetime(self, timestamp_str: str) -> bool:
        """Check if timestamp is in valid ISO format."""
        try:
            if timestamp_str.endswith('Z'):
                datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                datetime.fromisoformat(timestamp_str)
            return True
        except ValueError:
            return False

    def _derive_additional_fields(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Derive additional fields from log entry."""
        derived_fields = {}

        try:
            # Parse timestamp for time-based fields
            timestamp = log_entry.get("timestamp", "")
            if timestamp:
                try:
                    if timestamp.endswith('Z'):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromisoformat(timestamp)

                    derived_fields["hour"] = dt.hour
                    derived_fields["day_of_week"] = dt.weekday()
                    derived_fields["date"] = dt.date().isoformat()
                    derived_fields["is_weekend"] = dt.weekday() >= 5
                except ValueError:
                    pass

            # Derive message characteristics
            message = log_entry.get("message", "")
            if message and isinstance(message, str):
                derived_fields["message_length"] = len(message)
                derived_fields["has_error_keywords"] = self._contains_error_keywords(message)
                derived_fields["has_warning_keywords"] = self._contains_warning_keywords(message)

            # Derive data characteristics
            data = log_entry.get("data", {})
            if data and isinstance(data, dict):
                derived_fields["data_field_count"] = len(data)
                derived_fields["data_size"] = len(str(data))

                # Extract numeric metrics if present
                numeric_fields = {}
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        numeric_fields[f"metric_{key}"] = value

                if numeric_fields:
                    derived_fields["numeric_metrics"] = numeric_fields

            # Service-specific derivations
            service = log_entry.get("service", "")
            if service:
                derived_fields["service_category"] = self._categorize_service(service)

        except Exception as e:
            logger.warning(f"Failed to derive additional fields: {str(e)}")

        return derived_fields

    def _contains_error_keywords(self, message: str) -> bool:
        """Check if message contains error keywords."""
        error_keywords = [
            "error", "exception", "failed", "failure", "critical", "fatal",
            "stack trace", "traceback", "null pointer", "timeout", "connection refused"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in error_keywords)

    def _contains_warning_keywords(self, message: str) -> bool:
        """Check if message contains warning keywords."""
        warning_keywords = [
            "warning", "warn", "deprecated", "slow", "performance",
            "memory", "disk space", "high load", "overload"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in warning_keywords)

    def _categorize_service(self, service: str) -> str:
        """Categorize service based on name."""
        service_lower = service.lower()

        if "gateway" in service_lower:
            return "infrastructure"
        elif "file" in service_lower:
            return "storage"
        elif "utility" in service_lower or "system" in service_lower:
            return "operations"
        elif "ui" in service_lower:
            return "frontend"
        elif "analytics" in service_lower:
            return "analytics"
        elif "timeseries" in service_lower:
            return "database"
        else:
            return "unknown"

    async def transform_logs_batch(self, log_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform a batch of log entries."""
        transformed_logs = []

        for log_entry in log_entries:
            try:
                transformed_log = await self.transform_log(log_entry)
                transformed_logs.append(transformed_log)
            except Exception as e:
                logger.warning(f"Skipping invalid log entry: {str(e)}")
                continue

        logger.info(f"Transformed {len(transformed_logs)}/{len(log_entries)} log entries")
        return transformed_logs

    def get_validation_schema(self) -> Dict[str, Any]:
        """Get the current validation schema."""
        return self.validation_rules.copy()

    def update_validation_rules(self, new_rules: Dict[str, Any]):
        """Update validation rules (for dynamic configuration)."""
        self.validation_rules.update(new_rules)
        logger.info("Updated log validation rules")

# Global log transformer instance
log_transformer = LogTransformer()