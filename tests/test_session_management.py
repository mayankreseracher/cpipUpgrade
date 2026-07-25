"""
Tests for session management.
"""

import time
import pytest

from server.ws.sessions import SessionManager, ExecutionSession


class TestSessionManager:
    """Tests for execution session management."""
    
    def test_create_session(self):
        """Test creating a new session."""
        manager = SessionManager()
        
        session = manager.create("session-001", "device-001")
        
        assert session.session_id == "session-001"
        assert session.device_id == "device-001"
        assert session.execution_count == 0
        assert manager.active_count == 1
    
    def test_get_session(self):
        """Test retrieving a session."""
        manager = SessionManager()
        session = manager.create("session-001", "device-001")
        
        retrieved = manager.get("session-001")
        assert retrieved is session
    
    def test_get_nonexistent_session(self):
        """Test getting non-existent session returns None."""
        manager = SessionManager()
        assert manager.get("nonexistent") is None
    
    def test_get_by_device(self):
        """Test getting all sessions for a device."""
        manager = SessionManager()
        
        manager.create("session-001", "device-001")
        manager.create("session-002", "device-001")
        manager.create("session-003", "device-002")
        
        device1_sessions = manager.get_by_device("device-001")
        assert len(device1_sessions) == 2
        assert all(s.device_id == "device-001" for s in device1_sessions)
    
    def test_update_activity(self):
        """Test updating session activity."""
        manager = SessionManager()
        session = manager.create("session-001", "device-001")
        
        initial_active = session.last_active
        time.sleep(0.01)  # Small delay
        
        manager.update_activity("session-001")
        
        assert session.last_active > initial_active
        assert session.execution_count == 1
    
    def test_remove_session(self):
        """Test removing a session."""
        manager = SessionManager()
        manager.create("session-001", "device-001")
        assert manager.active_count == 1
        
        manager.remove("session-001")
        assert manager.active_count == 0
        assert manager.get("session-001") is None
    
    def test_cleanup_stale_sessions(self):
        """Test cleaning up stale sessions."""
        manager = SessionManager()
        
        # Create sessions
        session1 = manager.create("session-001", "device-001")
        session2 = manager.create("session-002", "device-001")
        
        # Make session1 stale by setting old last_active time
        session1.last_active = time.time() - 7200  # 2 hours ago
        
        # Cleanup with 1 hour timeout
        removed = manager.cleanup_stale(max_idle_seconds=3600)
        
        assert removed == 1
        assert manager.active_count == 1
        assert manager.get("session-002") is not None
        assert manager.get("session-001") is None
    
    def test_cleanup_all_stale_sessions(self):
        """Test cleaning up all stale sessions."""
        manager = SessionManager()
        
        session1 = manager.create("session-001", "device-001")
        session2 = manager.create("session-002", "device-001")
        
        # Make both stale
        session1.last_active = time.time() - 7200
        session2.last_active = time.time() - 7200
        
        removed = manager.cleanup_stale(max_idle_seconds=3600)
        
        assert removed == 2
        assert manager.active_count == 0
