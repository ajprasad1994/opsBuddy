"""
WebSocket server for OpsBuddy Monitor Service.
Provides real-time communication for service health updates.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Any
from datetime import datetime

import websockets
from websockets.server import WebSocketServerProtocol

from config import settings
from redis_client import redis_client

logger = logging.getLogger("monitor_service.websocket_server")

class WebSocketServer:
    """WebSocket server for real-time service health updates."""

    def __init__(self):
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self._server = None
        self._running = False

    async def start_server(self, host: str = "0.0.0.0", port: int = 8006):
        """Start the WebSocket server."""
        if self._running:
            logger.warning("WebSocket server already running")
            return

        try:
            self._server = await websockets.serve(
                self._handle_connection,
                host,
                port,
                ping_interval=settings.websocket_config["ping_interval"],
                ping_timeout=settings.websocket_config["ping_timeout"],
                max_size=2**20,  # 1MB max message size
                max_queue=32
            )

            self._running = True
            logger.info(f"WebSocket server started on {host}:{port}")

            # Subscribe to Redis updates
            await redis_client.subscribe_to_websocket_updates(self._handle_redis_message)

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {str(e)}")
            raise

    async def stop_server(self):
        """Stop the WebSocket server."""
        if not self._running:
            return

        self._running = False

        # Close all client connections
        if self.connected_clients:
            await asyncio.gather(
                *[client.close() for client in self.connected_clients],
                return_exceptions=True
            )
        self.connected_clients.clear()

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        logger.info("WebSocket server stopped")

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection."""
        client_id = id(websocket)
        logger.info(f"New WebSocket connection: {client_id}")

        # Add client to connected clients
        self.connected_clients.add(websocket)

        try:
            # Send initial connection message
            await self._send_to_client(websocket, {
                "type": "connection_established",
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id
            })

            # Handle messages from client
            async for message in websocket:
                try:
                    await self._handle_client_message(websocket, message)
                except Exception as e:
                    logger.error(f"Error handling client message: {str(e)}")
                    break

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
        finally:
            # Remove client from connected clients
            self.connected_clients.discard(websocket)

    async def _handle_client_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle message from WebSocket client."""
        try:
            data = json.loads(message)

            message_type = data.get("type")

            if message_type == "subscribe":
                await self._handle_subscribe(websocket, data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(websocket, data)
            elif message_type == "ping":
                await self._send_to_client(websocket, {"type": "pong"})
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"Error processing client message: {str(e)}")

    async def _handle_subscribe(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle client subscription request."""
        subscriptions = data.get("subscriptions", ["health_updates"])

        response = {
            "type": "subscription_confirmed",
            "subscriptions": subscriptions,
            "timestamp": datetime.utcnow().isoformat()
        }

        await self._send_to_client(websocket, response)
        logger.debug(f"Client subscribed to: {subscriptions}")

    async def _handle_unsubscribe(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle client unsubscription request."""
        subscriptions = data.get("subscriptions", [])

        response = {
            "type": "unsubscription_confirmed",
            "subscriptions": subscriptions,
            "timestamp": datetime.utcnow().isoformat()
        }

        await self._send_to_client(websocket, response)
        logger.debug(f"Client unsubscribed from: {subscriptions}")

    async def _handle_redis_message(self, message: str):
        """Handle message from Redis."""
        try:
            data = json.loads(message)

            # Broadcast to all connected clients
            if self.connected_clients:
                await self._broadcast_to_clients({
                    "type": "redis_message",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                })

        except Exception as e:
            logger.error(f"Error handling Redis message: {str(e)}")

    async def _send_to_client(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Send message to a specific client."""
        try:
            message = json.dumps(data, default=str)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {str(e)}")

    async def _broadcast_to_clients(self, data: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.connected_clients:
            return

        message = json.dumps(data, default=str)
        tasks = []

        # Create tasks for sending to all clients
        for client in self.connected_clients:
            if not client.closed:
                task = asyncio.create_task(self._send_to_client_silent(client, message))
                tasks.append(task)

        # Wait for all sends to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_client_silent(self, websocket: WebSocketServerProtocol, message: str):
        """Send message to client without raising exceptions."""
        try:
            await websocket.send(message)
        except Exception:
            # Remove failed client
            self.connected_clients.discard(websocket)

    async def broadcast_health_update(self, service_name: str, status: Dict[str, Any]):
        """Broadcast service health update to all clients."""
        update_data = {
            "type": "health_update",
            "service": service_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }

        await self._broadcast_to_clients(update_data)
        logger.debug(f"Broadcast health update for {service_name}")

    async def broadcast_system_status(self, system_status: Dict[str, Any]):
        """Broadcast overall system status to all clients."""
        status_data = {
            "type": "system_status",
            "status": system_status,
            "timestamp": datetime.utcnow().isoformat()
        }

        await self._broadcast_to_clients(status_data)
        logger.debug("Broadcast system status update")

    def get_connection_count(self) -> int:
        """Get number of connected clients."""
        return len(self.connected_clients)

    def is_running(self) -> bool:
        """Check if WebSocket server is running."""
        return self._running

# Global WebSocket server instance
websocket_server = WebSocketServer()