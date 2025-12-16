"""Pytest configuration and fixtures."""
import pytest


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return [
        {
            "title": "Example Result 1",
            "url": "https://example.com/1",
            "snippet": "This is a sample search result snippet"
        },
        {
            "title": "Example Result 2",
            "url": "https://example.com/2",
            "snippet": "Another sample search result snippet"
        }
    ]
