"""
WebSocket connection hub with robust error handling.

Manages active device connections, message routing,
heartbeat monitoring, and session lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from server.exceptions import ErrorCode, WebSocketError
from shared.protocol import (
    MessageType,
    RPCMessage,
    make_error,
    make_heartbeat,
)

logger = logging.getLogger(__name__)


@dataclass
class DeviceConnection:
    """Represents an active WebSocket connection from a device."""

    device_id: str
    websocket: WebSocket
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class ConnectionHub:
    """Manages all WebSocket connections from devices."""

    def __init__(self):
        self._connections: dict[str, DeviceConnection] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        device_id: str,
        websocket: WebSocket,
        metadata: dict | None = None,
    ) -> DeviceConnection:
        """Accept and register a new device connection."""
        try:
            await websocket.accept()
        except Exception as e:
            logger.error(f"Failed to accept WebSocket for {device_id}: {e}")
            raise WebSocketError(
                f"Failed to accept connection: {e}",
                ErrorCode.WS_ACCEPT_FAILED,
                {"device_id": device_id},
            )

        conn = DeviceConnection(
            device_id=device_id, websocket=websocket, metadata=metadata or {}
        )
        
        async with self._lock:
            # Close existing connection for this device
            if device_id in self._connections:
                try:
                    old_conn = self._connections[device_id]
                    await old_conn.websocket.close(code=1008, reason="Replaced")
                    logger.info(f"Closed previous connection for {device_id}")
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.warning(f"Error closing previous connection: {e}")
            
            self._connections[device_id] = conn
            logger.info(f"Device {device_id} connected (total: {len(self._connections)})")
        
        return conn

    async def disconnect(self, device_id: str) -> None:
        """Disconnect a device and clean up."""
        async with self._lock:
            conn = self._connections.pop(device_id, None)
            if conn:
                try:
                    await conn.websocket.close()
                except WebSocketDisconnect:
                    pass  # Already disconnected
                except Exception as e:
                    logger.warning(f"Error closing connection for {device_id}: {e}")
                
                uptime = time.time() - conn.connected_at
                logger.info(
                    f"Device {device_id} disconnected (uptime: {uptime:.1f}s, "
                    f"remaining: {len(self._connections)})"
                )

    async def send_to_device(self, device_id: str, message: RPCMessage) -> bool:
        """Send a message to a specific device.
        
        Returns:
            True if sent successfully, False if device not found or send failed.
        """
        conn = self._connections.get(device_id)
        if not conn:
            logger.debug(f"Device {device_id} not found for message send")
            return False
        
        try:
            await conn.websocket.send_text(message.to_json())
            return True
        except WebSocketDisconnect:
            logger.info(f"Device {device_id} disconnected during send")
            await self.disconnect(device_id)
            return False
        except Exception as e:
            logger.error(f"Failed to send to {device_id}: {e}")
            await self.disconnect(device_id)
            return False

    async def broadcast(self, message: RPCMessage) -> int:
        """Broadcast a message to all connected devices.
        
        Returns:
            Number of devices the message was successfully sent to.
        """
        sent = 0
        failed = 0
        for device_id in list(self._connections.keys()):
            if await self.send_to_device(device_id, message):
                sent += 1
            else:
                failed += 1
        
        if failed:
            logger.warning(
                f"Broadcast sent to {sent} device(s), "
                f"failed for {failed} device(s)"
            )
        
        return sent

    def get_connection(self, device_id: str) -> DeviceConnection | None:
        """Get connection object for a device."""
        return self._connections.get(device_id)

    @property
    def connected_count(self) -> int:
        """Get count of connected devices."""
        return len(self._connections)

    def list_devices(self) -> list[str]:
        """Get list of connected device IDs."""
        return list(self._connections.keys())

    async def heartbeat_loop(self, interval: int = 30) -> None:
        """Send periodic heartbeats and clean dead connections.
        
        Args:
            interval: Heartbeat interval in seconds. Connections without
                     heartbeat response for 3x interval are considered dead.
        """
        logger.info(f"Starting heartbeat loop with {interval}s interval")
        
        while True:
            await asyncio.sleep(interval)
            now = time.time()
            dead_connections = []
            
            for device_id in list(self._connections.keys()):
                conn = self._connections.get(device_id)
                if not conn:
                    continue
                
                # Check for dead connections (no heartbeat response)
                if now - conn.last_heartbeat > interval * 3:
                    logger.warning(
                        f"Device {device_id} heartbeat timeout "
                        f"({now - conn.last_heartbeat:.1f}s without response)"
                    )
                    dead_connections.append(device_id)
                else:
                    # Send heartbeat
                    try:
                        await conn.websocket.send_text(make_heartbeat().to_json())
                    except (WebSocketDisconnect, Exception) as e:
                        logger.debug(f"Failed to send heartbeat to {device_id}: {e}")
                        dead_connections.append(device_id)
            
            # Clean up dead connections
            for device_id in dead_connections:
                await self.disconnect(device_id)


# Global hub instance
hub = ConnectionHub()
