"""
cpip Cloud API — FastAPI Application.

Main entry point for the cloud backend server.
Includes REST API, WebSocket hub, and lifecycle management.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.api import auth, builds, execution, health, packages
from server.config import server_config
from server.db.session import close_db, init_db
from server.ws.hub import hub
from server.ws.rpc import dispatcher
from server.ws.sessions import session_manager
from shared.constants import VERSION
from shared.protocol import MessageType, RPCMessage

logger = logging.getLogger("cpip.server")

# ── Application ──────────────────────────────────────────────────────

app = FastAPI(
    title="cpip Cloud API",
    description="Cloud-Powered Package Intelligence for Android Termux",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(packages.router)
app.include_router(builds.router)
app.include_router(execution.router)


# ── Lifecycle ────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info(f"cpip server v{VERSION} starting...")
    await init_db()
    # Start heartbeat loop
    asyncio.create_task(hub.heartbeat_loop())
    # Start session cleanup
    asyncio.create_task(_session_cleanup_loop())
    logger.info("Server ready.")


@app.on_event("shutdown")
async def shutdown():
    await close_db()
    logger.info("Server shutdown complete.")


async def _session_cleanup_loop():
    """Periodically clean stale sessions."""
    while True:
        await asyncio.sleep(300)
        session_manager.cleanup_stale()


# ── WebSocket Endpoint ───────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for device connections."""
    auth_header = websocket.headers.get("authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = websocket.query_params.get("token")

    user = None
    from server.config import server_config
    if token:
        if server_config.debug and token.startswith("dev_"):
            user = {"sub": "dev-user", "device_id": token[4:], "tier": "dev"}
        else:
            from server.auth.jwt_handler import decode_token
            user = decode_token(token)

    if not user:
        if server_config.debug:
            user = {"sub": "anonymous", "device_id": "local", "tier": "dev"}
        else:
            # Reject connection by closing with policy violation code
            await websocket.close(code=1008)
            return

    device_id = user.get("device_id", "unknown")
    try:
        conn = await hub.connect(device_id, websocket)

        async for raw in websocket.iter_text():
            try:
                msg = RPCMessage.from_json(raw)

                # Handle session init
                if msg.type == MessageType.SESSION_INIT:
                    # Update metadata
                    conn.metadata = msg.params
                    from shared.protocol import make_notification
                    await websocket.send_text(
                        make_notification("session.ack", {"session_id": device_id}).to_json()
                    )
                    continue

                # Handle heartbeat
                if msg.type == MessageType.HEARTBEAT_ACK:
                    conn.last_heartbeat = time.time()
                    continue

                # Handle RPC calls
                if msg.type == MessageType.CALL:
                    response = await dispatcher.dispatch(msg)
                    await websocket.send_text(response.to_json())
                    continue

            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error(f"WS error for {device_id}: {e}")
                continue

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS connection error: {e}")
    finally:
        await hub.disconnect(device_id)


# ── Device Registration (REST fallback) ──────────────────────────────

@app.post("/api/v1/devices/register")
async def register_device(data: dict):
    """Register/update device information."""
    return {"status": "ok", "device_id": data.get("device_id", "unknown")}


# ── Root ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "cpip Cloud API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
    }
