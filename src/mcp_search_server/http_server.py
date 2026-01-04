"""
HTTP Server for MCP Search Server - Smithery Deployment.

This module provides an HTTP endpoint using MCP's built-in SSE server capabilities.
It reuses the same server logic as the stdio version.
"""

import logging
import os
from importlib import metadata

import contextlib

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .registry import register_all_tools, get_tool_list
from . import server as stdio_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_package_version() -> str:
    try:
        return metadata.version("mcp-search-server")
    except Exception:
        return "0.0.0"


def _base_url(request: Request) -> str:
    # Starlette's request.url is derived from ASGI scope headers.
    # Prefer that so we generate correct $id behind proxies when possible.
    return str(request.base_url).rstrip("/")


async def well_known_mcp_config(request: Request) -> JSONResponse:
    base = _base_url(request)
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"{base}/.well-known/mcp-config",
        "title": "MCP Session Configuration",
        "description": "Configuration for connecting to this MCP server",
        "x-query-style": "dot+bracket",
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    return JSONResponse(schema)


async def mcp_server_card(request: Request) -> JSONResponse:
    registry = stdio_server.get_global_registry()
    tools = {}
    for tool in get_tool_list(registry):
        input_schema = getattr(tool, "inputSchema", None)
        tools[tool.name] = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": input_schema,
            "operationId": tool.name,
        }

    card = {
        "server": {
            "name": "mcp-search-server",
            "version": _get_package_version(),
            "transport": "http",
        },
        "capabilities": {
            "tools": tools,
            "resources": [],
            "prompts": [],
        },
    }
    return JSONResponse(card)


def create_http_app():
    """Create Starlette app with MCP SSE endpoint."""
    # Initialize registry
    logger.info("Initializing tool registry for HTTP server...")
    register_all_tools(stdio_server.app)
    stats = stdio_server.get_global_registry().get_statistics()
    logger.info(f"Registry initialized. Available tools: {stats['total_tools']}")

    # Create session manager without security restrictions for Smithery scanning
    session_manager = StreamableHTTPSessionManager(
        stdio_server.app,
        # Disable DNS rebinding protection to allow Smithery to scan
        allowed_origins=None
    )

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette):
        async with session_manager.run():
            yield

    # Create main Starlette app with:
    # - the MCP Streamable HTTP endpoint at /mcp
    # - a well-known config schema endpoint for Smithery
    # - optional well-known server card aliases for scanners
    app = Starlette(
        lifespan=lifespan,
        routes=[
            Mount("/mcp", app=session_manager.handle_request),
            Route("/.well-known/mcp-config", endpoint=well_known_mcp_config, methods=["GET"]),
            # Back-compat / convenience aliases. Some scanners look for a well-known server card.
            Route("/.well-known/mcp", endpoint=mcp_server_card, methods=["GET"]),
            Route("/.well-known/mcp.json", endpoint=mcp_server_card, methods=["GET"]),
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
    logger.info(f"MCP endpoint: http://0.0.0.0:{port}/mcp")

    app = create_http_app()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run_http()
