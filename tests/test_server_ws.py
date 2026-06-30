import pytest
from fastapi.testclient import TestClient
from server.app import app
from server.config import server_config
from shared.protocol import make_call


def test_websocket_authenticated():
    client = TestClient(app)
    orig_debug = server_config.debug
    server_config.debug = False
    try:
        # 1. No token -> should reject/close with 1008 policy violation
        with pytest.raises(Exception):
            with client.websocket_connect("/ws") as websocket:
                websocket.send_text(make_call("ping").to_json())
                
        # 2. Correct token -> should connect and respond to RPC
        from server.auth.jwt_handler import create_token_pair
        tokens = create_token_pair("test-user", "test-device")
        access_token = tokens["access_token"]
        
        with client.websocket_connect(f"/ws?token={access_token}") as websocket:
            websocket.send_text(make_call("ping").to_json())
            resp = websocket.receive_text()
            assert "pong" in resp
    finally:
        server_config.debug = orig_debug
