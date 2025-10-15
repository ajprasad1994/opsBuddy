"""
Redis client for OpsBuddy Monitor Service.
Handles pub/sub messaging for real-time service health updates.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime

import redis.asyncio as redis
from redis.asyncio.client import PubSub

from config import settings

logger = logging.getLogger("monitor_service.redis_client")

class RedisClient:
    """Redis client wrapper for pub/sub operations."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[PubSub] = None
        self._connected = False
        self._subscribers = {}

    async def connect(self) -> bool:
        """Connect to Redis server."""
        try:
            self.redis_client = redis.Redis(**settings.redis_client_config)
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            logger.info("Successfully connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Redis server."""
        try:
            if self.pubsub:
                await self.pubsub.close()
            if self.redis_client:
                await self.redis_client.close()
            self._connected = False
            logger.info("Disconnected from Redis")
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {str(e)}")

    async def publish_health_update(self, service_name: str, status: Dict[str, Any]):
        """Publish service health update to Redis channel."""
        if not self._connected or not self.redis_client:
            logger.warning("Redis not connected, cannot publish health update")
            return False

        try:
            message = {
                "service": service_name,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }

            await self.redis_client.publish(
                settings.redis_channel_health,
                json.dumps(message, default=str)
            )

            logger.debug(f"Published health update for {service_name}: {status.get('health', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish health update: {str(e)}")
            return False

    async def publish_websocket_update(self, update_type: str, data: Dict[str, Any]):
        """Publish WebSocket update to Redis channel."""
        if not self._connected or not self.redis_client:
            logger.warning("Redis not connected, cannot publish websocket update")
            return False

        try:
            message = {
                "type": update_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }

            await self.redis_client.publish(
                settings.redis_channel_websocket,
                json.dumps(message, default=str)
            )

            logger.debug(f"Published websocket update: {update_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish websocket update: {str(e)}")
            return False

    async def subscribe_to_health_updates(self, callback: Callable[[str], None]):
        """Subscribe to health update channel."""
        if not self._connected or not self.redis_client:
            logger.error("Redis not connected, cannot subscribe to health updates")
            return False

        try:
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe(settings.redis_channel_health)
            self._subscribers['health'] = callback

            # Start background listener
            asyncio.create_task(self._listen_for_messages())

            logger.info(f"Subscribed to health updates channel: {settings.redis_channel_health}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to health updates: {str(e)}")
            return False

    async def subscribe_to_websocket_updates(self, callback: Callable[[str], None]):
        """Subscribe to websocket update channel."""
        if not self._connected or not self.redis_client:
            logger.error("Redis not connected, cannot subscribe to websocket updates")
            return False

        try:
            if not self.pubsub:
                self.pubsub = self.redis_client.pubsub()

            await self.pubsub.subscribe(settings.redis_channel_websocket)
            self._subscribers['websocket'] = callback

            logger.info(f"Subscribed to websocket updates channel: {settings.redis_channel_websocket}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to websocket updates: {str(e)}")
            return False

    async def subscribe_to_error_logs(self, callback: Callable[[str], None]):
        """Subscribe to error logs channel."""
        if not self._connected or not self.redis_client:
            logger.error("Redis not connected, cannot subscribe to error logs")
            return False

        try:
            if not self.pubsub:
                self.pubsub = self.redis_client.pubsub()

            await self.pubsub.subscribe(settings.redis_channel_errors)
            self._subscribers['errors'] = callback

            logger.info(f"Subscribed to error logs channel: {settings.redis_channel_errors}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to error logs: {str(e)}")
            return False

    async def _listen_for_messages(self):
        """Background task to listen for Redis messages."""
        if not self.pubsub:
            return

        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    data = message['data'].decode('utf-8')

                    # Route message to appropriate callback
                    if channel == settings.redis_channel_health and 'health' in self._subscribers:
                        await self._handle_health_message(data)
                    elif channel == settings.redis_channel_websocket and 'websocket' in self._subscribers:
                        await self._handle_websocket_message(data)
                    elif channel == settings.redis_channel_errors and 'errors' in self._subscribers:
                        await self._handle_error_message(data)

        except Exception as e:
            logger.error(f"Error listening for Redis messages: {str(e)}")

    async def _handle_health_message(self, data: str):
        """Handle incoming health update message."""
        try:
            message = json.loads(data)
            callback = self._subscribers.get('health')
            if callback:
                await callback(data)
        except Exception as e:
            logger.error(f"Error handling health message: {str(e)}")

    async def _handle_websocket_message(self, data: str):
        """Handle incoming websocket update message."""
        try:
            message = json.loads(data)
            callback = self._subscribers.get('websocket')
            if callback:
                await callback(data)
        except Exception as e:
            logger.error(f"Error handling websocket message: {str(e)}")

    async def _handle_error_message(self, data: str):
        """Handle incoming error log message."""
        try:
            message = json.loads(data)
            callback = self._subscribers.get('errors')
            if callback:
                await callback(data)
        except Exception as e:
            logger.error(f"Error handling error message: {str(e)}")

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected

# Global Redis client instance
redis_client = RedisClient()