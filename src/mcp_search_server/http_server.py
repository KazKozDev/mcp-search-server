"""
HTTP Server for MCP Search Server - Smithery Deployment.

This module provides an HTTP endpoint using MCP's built-in SSE server capabilities.
It reuses the same server logic as the stdio version.
"""

import logging
import os

import uvicorn
from mcp.server import Server
from mcp.server.sse import sse_server
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from .registry import register_all_tools, get_tool_list
from . import server as stdio_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_http_app():
    """Create Starlette app with MCP SSE endpoint."""
    # Initialize registry
    logger.info("Initializing tool registry for HTTP server...")
    register_all_tools(stdio_server.app)
    stats = stdio_server.get_global_registry().get_statistics()
    logger.info(f"Registry initialized. Available tools: {stats['total_tools']}")

    # Create SSE app from the stdio server
    sse_app = sse_server(stdio_server.app)

    # Create main Starlette app with SSE mounted at /mcp
    app = Starlette(
        routes=[
            Mount("/mcp", app=sse_app),
        ]
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


def run_http():
    """Run the HTTP server."""
    port = int(os.environ.get("PORT", 8080))

    logger.info(f"Starting MCP HTTP server on port {port}...")
    logger.info(f"SSE endpoint: http://0.0.0.0:{port}/mcp/sse")

    app = create_http_app()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run_http()
