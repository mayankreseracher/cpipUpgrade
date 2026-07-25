"""
Tests for WebSocket connection handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from server.ws.hub import ConnectionHub, DeviceConnection
from server.exceptions import WebSocketError, ErrorCode


class TestConnectionHub:
    """Tests for WebSocket connection hub."""
    
    @pytest.mark.asyncio
    async def test_connect_new_device(self):
        """Test connecting a new device."""
        hub = ConnectionHub()
        
        mock_ws = AsyncMock()
        conn = await hub.connect("device-001", mock_ws, {"platform": "android"})
        
        assert conn.device_id == "device-001"
        assert conn.metadata == {"platform": "android"}
        assert hub.connected_count == 1
        mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reconnect_closes_old_connection(self):
        """Test that reconnecting closes the old connection."""
        hub = ConnectionHub()
        
        # First connection
        mock_ws1 = AsyncMock()
        await hub.connect("device-001", mock_ws1)
        assert hub.connected_count == 1
        
        # Second connection with same device_id
        mock_ws2 = AsyncMock()
        await hub.connect("device-001", mock_ws2)
        
        assert hub.connected_count == 1  # Still only 1 connection
        mock_ws1.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_device(self):
        """Test disconnecting a device."""
        hub = ConnectionHub()
        
        mock_ws = AsyncMock()
        await hub.connect("device-001", mock_ws)
        assert hub.connected_count == 1
        
        await hub.disconnect("device-001")
        assert hub.connected_count == 0
        mock_ws.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_to_device_success(self):
        """Test sending message to connected device."""
        from shared.protocol import make_heartbeat
        
        hub = ConnectionHub()
        mock_ws = AsyncMock()
        await hub.connect("device-001", mock_ws)
        
        msg = make_heartbeat()
        result = await hub.send_to_device("device-001", msg)
        
        assert result is True
        mock_ws.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_to_device_not_found(self):
        """Test sending to non-existent device returns False."""
        from shared.protocol import make_heartbeat
        
        hub = ConnectionHub()
        msg = make_heartbeat()
        result = await hub.send_to_device("nonexistent", msg)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_devices(self):
        """Test listing connected devices."""
        hub = ConnectionHub()
        
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        await hub.connect("device-001", mock_ws1)
        await hub.connect("device-002", mock_ws2)
        
        devices = hub.list_devices()
        assert sorted(devices) == ["device-001", "device-002"]


class TestDeviceConnection:
    """Tests for device connection tracking."""
    
    def test_connection_metadata(self):
        """Test connection stores metadata."""
        mock_ws = Mock()
        metadata = {"platform": "android", "version": "1.0"}
        
        conn = DeviceConnection(
            device_id="device-001",
            websocket=mock_ws,
            metadata=metadata,
        )
        
        assert conn.device_id == "device-001"
        assert conn.metadata == metadata
        assert conn.execution_count == 0
        assert conn.connected_at > 0
