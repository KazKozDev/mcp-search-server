"""
MCP Search Server - Dynamic Modular Architecture.

Features:
- Dynamic tool loading based on configuration
- Deferred loading (lazy import) for reduced startup time and memory
- Category-based organization
- Meta-tools for tool discovery (search_tools)
"""

import asyncio
import logging
from typing import Any, List, Union

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import mcp.server.stdio

from .registry import register_all_tools, get_tool_list, get_global_registry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP Server
app = Server("mcp-search-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """
    List available tools dynamically from the registry.

    This function delegates to the registry to get the list of available tools.
    Deferred tools are included with their metadata, but not loaded yet.
    """
    registry = get_global_registry()

    # If registry is empty (first run), initialize it
    if registry.get_statistics()["total_tools"] == 0:
        logger.info("Initializing tool registry...")
        register_all_tools(app)

    return get_tool_list(registry)


@app.call_tool()
async def call_tool(
    name: str, arguments: Any
) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
    """
    Handle dynamic tool calls via the registry.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of content blocks
    """
    registry = get_global_registry()

    try:
        logger.info(f"Executing tool: {name}")

        # 1. Get tool execution function
        # This will automatically load the tool if it's deferred
        tool = await registry.load_tool(name)

        if not tool:
            raise ValueError(f"Tool not found: {name}")

        # 2. Execute the tool
        # BaseTool/FunctionTool handles execution logic
        result = await tool.execute(**arguments)

        # 3. Format the output
        # Simple text representation for now, can be improved to support structured data
        if isinstance(result, (str, int, float, bool)):
            return [TextContent(type="text", text=str(result))]

        elif isinstance(result, dict):
            # Check for specific keys that indicate formatted content
            # Existing tools often return specific structures, we might need adapters here
            # But BaseTool should standardize this eventually.

            # For backward compatibility with existing tools that return raw dicts
            import json
            text_output = json.dumps(result, indent=2, ensure_ascii=False)
            return [TextContent(type="text", text=text_output)]

        elif isinstance(result, list):
            # List of TextContent already?
            if all(isinstance(x, (TextContent, ImageContent, EmbeddedResource)) for x in result):
                return result
            # Or list of data
            import json
            text_output = json.dumps(result, indent=2, ensure_ascii=False)
            return [TextContent(type="text", text=text_output)]

        else:
            return [TextContent(type="text", text=str(result))]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error executing tool {name}: {str(e)}")]


async def main():
    """Entry point for the server."""
    logger.info("Starting MCP Search Server...")

    # Initialize registry on startup
    # (Optional, as list_tools will do it, but good for fail-fast)
    try:
        register_all_tools(app)
        stats = get_global_registry().get_statistics()
        logger.info(f"Registry initialized. Available tools: {stats['total_tools']}")
    except Exception as e:
        logger.error(f"Failed to initialize registry: {e}")
        # Continue anyway, list_tools might retry or show empty

    # Run server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
