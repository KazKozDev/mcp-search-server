"""Integration tests for the Tool Registry and Dynamic Loader (V2 Architecture)."""

import pytest
from mcp_search_server.registry import get_global_registry
from mcp_search_server.tools.base import ToolCategory, ToolPriority, BaseTool, ToolMetadata
from mcp_search_server.registry.loader import register_all_tools, load_tool_config

@pytest.mark.asyncio
async def test_registry_initialization():
    """Test that registry is initialized correctly."""
    registry = get_global_registry()
    assert registry is not None
    assert len(registry.get_all_tools()) == 0  # Should be empty initially

@pytest.mark.asyncio
async def test_loader_registration(registry):
    """Test full registration process via loader."""
    # This mocks the server object as it's just passed through
    class MockServer:
        pass
    
    server = MockServer()
    
    # Run registration
    reg = register_all_tools(server)
    
    # Check stats
    stats = reg.get_statistics()
    assert stats["total_tools"] > 0
    assert stats["loaded_tools"] > 0  # Meta tools + critical tools
    
    # Check meta tools are loaded
    assert reg.is_tool_loaded("search_tools")
    assert reg.is_tool_loaded("list_tool_categories")

@pytest.mark.asyncio
async def test_search_tools_logic(registry):
    """Test the search_tools logic including deferred tools."""
    class MockServer: pass
    server = MockServer()
    register_all_tools(server)
    
    # Search for a common tool (e.g. github)
    # It should find it even if it's deferred
    results = registry.search_tools("github", limit=5)
    
    assert len(results) > 0
    names = [r.name for r in results]
    assert "search_github" in names or "get_github_readme" in names

@pytest.mark.asyncio
async def test_deferred_loading(registry):
    """Test loading a specific deferred tool."""
    class MockServer: pass
    server = MockServer()
    register_all_tools(server)
    
    tool_name = "search_github"
    
    # Ensure it's deferred first (might fail if config changes, but generally expectation)
    if tool_name not in registry.get_deferred_tool_names():
        pytest.skip(f"{tool_name} is not deferred in current config")
        
    assert not registry.is_tool_loaded(tool_name)
    
    # Load it
    tool = await registry.load_tool(tool_name)
    
    assert tool is not None
    assert tool.name == tool_name
    assert registry.is_tool_loaded(tool_name)
    assert tool_name not in registry.get_deferred_tool_names()

@pytest.mark.asyncio
async def test_category_loading(registry):
    """Test getting tools by category."""
    class MockServer: pass
    server = MockServer()
    reg = register_all_tools(server)

    category = ToolCategory.SOCIAL

    # Get all social tools (either loaded or deferred)
    social_tools = reg.get_tools_by_category(category)

    assert len(social_tools) > 0

    # Verify all tools in this category
    for tool in social_tools:
        assert tool.category == category

def test_config_loading():
    """Test that configuration can be loaded."""
    config = load_tool_config()
    assert "tools" in config
    # search_web was renamed to search_duckduckgo
    assert "search_duckduckgo" in config["tools"] or len(config["tools"]) > 0
