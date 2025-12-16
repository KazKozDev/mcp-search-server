"""Tests for the MCP server."""

import pytest


def test_basic_imports():
    """Test that basic imports work."""
    from mcp_search_server.server import app
    from mcp_search_server.tools.duckduckgo import search_duckduckgo
    from mcp_search_server.tools.wikipedia import search_wikipedia, get_wikipedia_summary
    from mcp_search_server.tools.link_parser import extract_content_from_url
    from mcp_search_server.tools.pdf_parser import parse_pdf
    from mcp_search_server.tools.datetime_tool import get_current_datetime
    from mcp_search_server.tools.geolocation import get_location_by_ip

    assert app is not None
    assert callable(search_duckduckgo)
    assert callable(search_wikipedia)
    assert callable(get_wikipedia_summary)
    assert callable(extract_content_from_url)
    assert callable(parse_pdf)
    assert callable(get_current_datetime)
    assert callable(get_location_by_ip)


def test_server_exists():
    """Test that the server app is properly initialized."""
    from mcp_search_server.server import app

    assert app is not None
    assert hasattr(app, "name")
    assert app.name == "mcp-search-server"


@pytest.mark.asyncio
async def test_datetime_tool():
    """Test the datetime tool works."""
    from mcp_search_server.tools.datetime_tool import get_current_datetime

    result = await get_current_datetime("UTC", True)

    assert "datetime" in result
    assert "timezone" in result
    assert "timestamp" in result
    assert result["timezone"] == "UTC"
