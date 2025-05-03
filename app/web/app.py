import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp

from app.core.config import Config  # Assuming this exists and works

# Make sure the import path is correct relative to this file's location
from .templates import HTML
from .websocket import (
    register_websocket_handler,  # Assuming this calls app.add_websocket_route or uses @app.websocket
)

# --- Basic Logging Setup (Add if you don't have one elsewhere) ---
logging.basicConfig(level=logging.INFO)
# ----------------------------------------------------------------

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    logger.info("Creating FastAPI app...")
    app = FastAPI()

    # Configure CORS with WebSocket support
    # WARNING: "*" is insecure for production. List specific origins instead.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "*"
        ],  # e.g., ["http://localhost:3000", "https://yourfrontend.com"]
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # allow_websockets=True,  # Explicitly allow WebSocket
    )
    logger.info("CORS middleware added.")

    # Add trusted host middleware
    # WARNING: "*" is insecure for production. List specific hosts instead.
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["*", "localhost", "127.0.0.1"]
    )  # Be more specific in prod
    logger.info("TrustedHost middleware added.")

    @app.middleware("http")
    async def catch_exceptions(
        request: Request, call_next: ASGIApp
    ) -> JSONResponse | Any:
        """Catch exceptions and log them."""
        try:
            response = await call_next(request)  # type: ignore
            return response
        # Note: WebSocket upgrade errors might not be caught here easily
        # as they aren't standard HTTP request/response cycles after the initial upgrade.
        except Exception as e:
            logger.error(f"HTTP Request error: {e}", exc_info=True)  # Add traceback
            # Avoid sending detailed errors to client in production
            return JSONResponse(
                status_code=500, content={"detail": "Internal Server Error"}
            )

    # Mount static directory
    try:
        app.mount("/static", StaticFiles(directory=Config.STATIC_DIR), name="static")
        logger.info(f"Mounted static directory '{Config.STATIC_DIR}' at /static")
    except Exception as e:
        logger.error(f"Failed to mount static directory '{Config.STATIC_DIR}': {e}")

    @app.get("/")
    async def get() -> HTMLResponse:
        return HTMLResponse(HTML)

    # Optional: WebSocket health check (remains an HTTP GET endpoint)
    @app.get("/ws/health")
    async def websocket_health() -> dict:
        # This just confirms the HTTP part of the server is running,
        # not necessarily that WebSockets are configured correctly.
        return {"status": "ok"}

    # Register WebSocket handler(s)
    try:
        register_websocket_handler(app)  # CRITICAL: Ensure this defines /ws/cv_builder
        logger.info("WebSocket handler registration called.")
    except Exception as e:
        logger.error(
            f"Failed during WebSocket handler registration: {e}", exc_info=True
        )

    logger.info("FastAPI app creation complete.")
    return app


def is_port_in_use(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            s.close()
            return False
        except OSError:
            return True


def find_available_port(start_port: int = 8000, max_port: int = 9000) -> int:
    """Find an available port between start_port and max_port."""
    for port in range(start_port, max_port):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")


if __name__ == "__main__":
    try:
        port = find_available_port()
        print(f"Starting server on port {port}")
        app = create_app()
        uvicorn.run(app, host="127.0.0.1", port=port)
    except Exception as e:
        print(f"Failed to start server: {e}")
        exit(1)
