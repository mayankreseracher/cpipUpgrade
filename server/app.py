"""
cpip Cloud API — FastAPI Application.

Main entry point for the cloud backend server.
Includes REST API, WebSocket hub, and lifecycle management
with comprehensive error handling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from server.api import auth, builds, execution, health, packages
from server.config import server_config
from server.db.session import close_db, init_db
from server.exceptions import CPIPException, ErrorCode, WebSocketError, ValidationError as CPIPValidationError
from server.models import DeviceRegistration, ErrorResponse
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


# ── Error Handlers ────────────────────────────────────────────────────

@app.exception_handler(CPIPException)
async def cpip_exception_handler(request, exc: CPIPException):
    """Handle custom CPIP exceptions with structured error responses."""
    logger.error(
        f"CPIP Exception: {exc.error_code} - {exc.message}",
        extra={"status": exc.status_code, "details": exc.details},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "status": 422,
            "details": {"errors": exc.errors()},
        },
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
    """Initialize server resources on startup."""
    logger.info(f"cpip server v{VERSION} starting...")
    logger.info(f"Configuration: {server_config}")
    
    await init_db()
    
    # Start heartbeat loop
    asyncio.create_task(
        hub.heartbeat_loop(
            interval=server_config.session.heartbeat_interval
        )
    )
    
    # Start session cleanup loop
    asyncio.create_task(_session_cleanup_loop())
    
    logger.info("Server ready.")


@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    await close_db()
    logger.info("Server shutdown complete.")


async def _session_cleanup_loop():
    """Periodically clean stale sessions."""
    logger.info(
        f"Starting session cleanup loop "
        f"(interval: {server_config.session.cleanup_interval}s, "
        f"max_idle: {server_config.session.max_idle_seconds}s)"
    )
    
    while True:
        await asyncio.sleep(server_config.session.cleanup_interval)
        try:
            removed = session_manager.cleanup_stale(
                max_idle_seconds=server_config.session.max_idle_seconds
            )
            if removed > 0:
                logger.info(
                    f"Session cleanup: removed {removed} stale session(s), "
                    f"active: {session_manager.active_count}"
                )
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")


# ── WebSocket Endpoint ───────────────────────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for device connections.
    
    Handles:
    - Session initialization and device registration
    - Heartbeat ACKs for connection health monitoring
    - RPC calls with error handling and responses
    """
    device_id = "unknown"
    conn = None
    
    try:
        # Accept and register connection
        conn = await hub.connect(device_id, websocket)
        
        # Process incoming messages
        async for raw in websocket.iter_text():
            try:
                msg = RPCMessage.from_json(raw)
                
                # Handle session initialization
                if msg.type == MessageType.SESSION_INIT:
                    device_id = msg.params.get("device_id", device_id)
                    
                    # Re-register with correct device ID if changed
                    if device_id != conn.device_id:
                        await hub.disconnect(conn.device_id)
                        conn = await hub.connect(device_id, websocket, msg.params)
                    else:
                        conn.metadata = msg.params
                    
                    from shared.protocol import make_notification
                    
                    response = make_notification(
                        "session.ack",
                        {"session_id": device_id, "timestamp": time.time()},
                    )
                    await websocket.send_text(response.to_json())
                    logger.info(f"Session initialized for {device_id}")
                    continue
                
                # Handle heartbeat ACKs
                if msg.type == MessageType.HEARTBEAT_ACK:
                    conn.last_heartbeat = time.time()
                    logger.debug(f"Heartbeat ACK from {device_id}")
                    continue
                
                # Handle RPC calls
                if msg.type == MessageType.CALL:
                    session_manager.update_activity(device_id)
                    response = await dispatcher.dispatch(msg)
                    await websocket.send_text(response.to_json())
                    continue
                
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from {device_id}: {e}")
                try:
                    error_response = make_error(
                        msg_id="unknown",
                        code=-32700,
                        message="Parse error",
                    )
                    await websocket.send_text(error_response.to_json())
                except Exception:
                    pass
                
            except Exception as e:
                logger.error(f"WS message processing error for {device_id}: {e}")
                try:
                    error_response = make_error(
                        msg_id="unknown",
                        code=-32603,
                        message="Internal error",
                    )
                    await websocket.send_text(error_response.to_json())
                except Exception as send_err:
                    logger.error(f"Failed to send error response: {send_err}")
                    break
    
    except WebSocketDisconnect:
        logger.info(f"Device {device_id} disconnected")
    
    except WebSocketError as e:
        logger.error(f"WebSocket error for {device_id}: {e.message}")
    
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket handler: {e}", exc_info=True)
    
    finally:
        if conn:
            await hub.disconnect(conn.device_id)


# ── Device Registration (REST) ────────────────────────────────────────


@app.post("/api/v1/devices/register", response_model=dict)
async def register_device(data: DeviceRegistration) -> dict:
    """Register/update device information.
    
    Args:
        data: DeviceRegistration with validated device_id
    
    Returns:
        Registration confirmation with device_id
    
    Raises:
        ValidationError: If device_id is invalid
    """
    logger.info(
        f"Registering device {data.device_id} "
        f"(platform: {data.platform}, version: {data.version})"
    )
    
    return {
        "status": "ok",
        "device_id": data.device_id,
        "timestamp": time.time(),
    }


# ── Root ──────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "cpip Cloud API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
    }
