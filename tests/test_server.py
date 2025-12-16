"""Tests for the MCP server."""
import pytest
from mcp_search_server.server import app


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns expected tools."""
    tools = await app.list_tools()

    assert len(tools) > 0
    tool_names = [tool.name for tool in tools]

    # Check that essential tools are present
    assert "search_web" in tool_names
    assert "search_wikipedia" in tool_names
    assert "extract_webpage_content" in tool_names
    assert "parse_pdf" in tool_names
    assert "get_current_datetime" in tool_names
    assert "get_location_by_ip" in tool_names


@pytest.mark.asyncio
async def test_tool_schemas():
    """Test that tools have proper schemas."""
    tools = await app.list_tools()

    for tool in tools:
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'inputSchema')
        assert isinstance(tool.inputSchema, dict)
        assert 'type' in tool.inputSchema
