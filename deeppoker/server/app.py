"""
FastAPI Application Entry Point for DeepPoker.

This module creates and configures the FastAPI application with:
- HTTP routes for game management
- WebSocket endpoint for real-time communication
- Static file serving for frontend
- CORS middleware for development
"""

import os
import logging
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from deeppoker.server.routes import router
from deeppoker.server.websocket import websocket_endpoint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="DeepPoker R1",
        description="Texas Hold'em Poker Game Engine with WebSocket API",
        version="0.1.0",
    )
    
    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include HTTP routes
    app.include_router(router)
    
    # WebSocket endpoint
    app.websocket("/ws")(websocket_endpoint)
    
    # Mount static files
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "client", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Mounted static files from {static_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}")
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("DeepPoker R1 server starting up...")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("DeepPoker R1 server shutting down...")
    
    return app


# Create the application instance
app = create_app()


def main():
    """Run the server (for use as entry point)."""
    import uvicorn
    uvicorn.run(
        "deeppoker.server.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
