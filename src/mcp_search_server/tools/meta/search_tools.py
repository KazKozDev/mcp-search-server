"""Tool discovery meta-tool for searching available tools."""

import logging
from typing import List, Dict, Optional, Any

from ..base import ToolCategory

logger = logging.getLogger(__name__)


async def search_tools(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search for available tools by description, name, or tags.

    This meta-tool allows LLMs to discover what tools are available
    without loading all tools upfront. Essential for token optimization.

    Args:
        query: Search query (matches name, description, tags)
        category: Optional category filter (web, knowledge, social, analysis, context, files)
        limit: Maximum number of results (default: 10)

    Returns:
        List of matching tools with metadata

    Examples:
        >>> await search_tools("search web")
        [{"name": "search_web", "description": "...", "category": "web"}]

        >>> await search_tools("github", category="social")
        [{"name": "search_github", ...}, {"name": "get_github_readme", ...}]
    """
    from ...registry import get_global_registry

    registry = get_global_registry()

    # Parse category if provided
    tool_category = None
    if category:
        try:
            tool_category = ToolCategory[category.upper()]
        except KeyError:
            logger.warning(f"Invalid category: {category}")

    # Search in registry
    results = registry.search_tools(query, category=tool_category, limit=limit)

    # Format results
    formatted_results = []
    for tool in results:
        result = {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category.value,
            "priority": tool.priority.value,
            "tags": tool.metadata.tags,
        }

        # Add schema info if available
        if tool.metadata.input_schema:
            result["has_schema"] = True
            # Include required parameters
            if "required" in tool.metadata.input_schema:
                result["required_params"] = tool.metadata.input_schema["required"]

        formatted_results.append(result)

    logger.info(f"Found {len(formatted_results)} tools matching '{query}'")
    return formatted_results


async def list_tool_categories() -> List[Dict[str, Any]]:
    """
    List all available tool categories.

    Returns:
        List of categories with metadata
    """
    from ...registry import CategoryManager

    manager = CategoryManager()
    categories = manager.get_all_categories()

    results = []
    for category in categories:
        config = manager.get_category_config(category)
        results.append(
            {
                "name": category.value,
                "display_name": config.get("name", category.value.title()),
                "description": config.get("description", ""),
                "priority": config.get("priority", "MEDIUM"),
                "icon": config.get("icon", "🔧"),
                "tools_count": config.get("tools_count", 0),
            }
        )

    return results


async def get_tool_info(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool metadata or None if not found
    """
    from ...registry import get_global_registry

    registry = get_global_registry()
    tool = registry.get_tool(tool_name)

    if not tool:
        # Check if it's a deferred tool
        if tool_name in registry.get_deferred_tool_names():
            logger.info(f"Tool {tool_name} is deferred, loading...")
            tool = await registry.load_tool(tool_name)
        else:
            logger.warning(f"Tool not found: {tool_name}")
            return None

    return {
        "name": tool.name,
        "description": tool.description,
        "category": tool.category.value,
        "priority": tool.priority.value,
        "tags": tool.metadata.tags,
        "input_schema": tool.metadata.input_schema,
        "defer_loading": tool.metadata.defer_loading,
        "statistics": tool.get_statistics(),
    }
