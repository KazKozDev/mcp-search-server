"""Tests for utility functions."""

import pytest
from mcp_search_server.utils import run_parallel_searches


@pytest.mark.asyncio
async def test_run_parallel_searches():
    """Test parallel search execution."""
    # This is a placeholder test
    # In a real scenario, you would mock the actual search functions
    assert callable(run_parallel_searches)
