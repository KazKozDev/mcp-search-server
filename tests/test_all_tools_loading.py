"""Smoke tests to ensure all tools can be loaded without errors."""

import pytest
from mcp_search_server.registry import get_global_registry
from mcp_search_server.registry.loader import register_all_tools

@pytest.mark.asyncio
async def test_load_all_tools(registry):
    """
    Attempt to load every single tool in the configuration.
    This verifies that there are no import errors or syntax errors in any tool file.
    """
    class MockServer: pass
    server = MockServer()
    register_all_tools(server)
    
    # Get all registered tool names (loaded + deferred)
    all_names = registry.get_all_tool_names()
    
    print(f"\nFound {len(all_names)} tools. Loading checks...")
    
    failed_tools = []
    
    for name in all_names:
        try:
            # This triggers the import
            await registry.load_tool(name)
        except Exception as e:
            failed_tools.append((name, str(e)))
            
    if failed_tools:
        pytest.fail(f"Failed to load {len(failed_tools)} tools: {failed_tools}")
        
    assert len(registry.get_loaded_tool_names()) == len(all_names)
