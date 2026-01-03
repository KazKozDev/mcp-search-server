"""Pytest configuration and fixtures for MCP Search Server."""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from mcp_search_server.registry import get_global_registry, reset_global_registry

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def registry():
    """Fixture to provide a clean registry for each test."""
    # Reset before test
    reset_global_registry()
    registry = get_global_registry()
    yield registry
    # Cleanup after test
    reset_global_registry()

@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return [
        {
            "title": "Example Result 1",
            "url": "https://example.com/1",
            "snippet": "This is a sample search result snippet",
        },
        {
            "title": "Example Result 2",
            "url": "https://example.com/2",
            "snippet": "Another sample search result snippet",
        },
    ]

@pytest.fixture
def mock_tool_config():
    """Mock configuration for tools."""
    return {
        "tools": {
            "test_tool": {
                "category": "analysis",
                "priority": "LOW",
                "defer_loading": True,
                "description": "A test tool",
            }
        }
    }
