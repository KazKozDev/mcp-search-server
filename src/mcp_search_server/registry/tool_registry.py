"""Tool registry for dynamic tool management and discovery."""

import logging
from typing import Dict, List, Optional, Set, Any, Callable
from collections import defaultdict

from ..tools.base import BaseTool, ToolCategory, ToolPriority

logger = logging.getLogger(__name__)

# Global registry instance
_global_registry: Optional["ToolRegistry"] = None


class ToolRegistry:
    """
    Central registry for managing MCP tools.

    Features:
    - Register tools with metadata
    - Filter tools by category, priority, tags
    - Support deferred loading (lazy loading)
    - Track tool usage and performance
    - Search tools by query

    Usage:
        registry = ToolRegistry()
        registry.register_tool(my_tool)

        # Get tools by category
        web_tools = registry.get_tools_by_category(ToolCategory.WEB)

        # Search tools
        results = registry.search_tools("search web")

        # Load deferred tool
        tool = await registry.load_tool("search_wikipedia")
    """

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}  # Loaded tools
        self._deferred_tools: Dict[str, Dict[str, Any]] = {}  # Tools to load on demand
        self._loaded_categories: Set[str] = set()  # Categories that have been loaded

        # Indexes for fast lookup
        self._by_category: Dict[ToolCategory, List[str]] = defaultdict(list)
        self._by_priority: Dict[ToolPriority, List[str]] = defaultdict(list)
        self._by_tag: Dict[str, List[str]] = defaultdict(list)

        # Statistics
        self._load_count = 0
        self._search_count = 0

    def register_tool(
        self,
        tool: BaseTool,
        defer: bool = False,
        loader_func: Optional[Callable] = None,
    ) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance to register
            defer: If True, don't load immediately (lazy loading)
            loader_func: Optional function to load the tool later

        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools or tool.name in self._deferred_tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")

        if defer and loader_func:
            # Store for deferred loading
            self._deferred_tools[tool.name] = {
                "category": tool.category,
                "priority": tool.priority,
                "loader": loader_func,
                "metadata": tool.metadata.to_dict(),
            }
            logger.debug(f"Registered deferred tool: {tool.name}")
        else:
            # Load immediately
            self._tools[tool.name] = tool
            self._index_tool(tool)
            logger.debug(f"Registered tool: {tool.name}")

    def _index_tool(self, tool: BaseTool) -> None:
        """Add tool to indexes for fast lookup."""
        # Index by category
        if tool.name not in self._by_category[tool.category]:
            self._by_category[tool.category].append(tool.name)

        # Index by priority
        if tool.name not in self._by_priority[tool.priority]:
            self._by_priority[tool.priority].append(tool.name)

        # Index by tags
        for tag in tool.metadata.tags:
            if tool.name not in self._by_tag[tag]:
                self._by_tag[tag].append(tool.name)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all loaded tools.

        Returns:
            List of all loaded tool instances
        """
        return list(self._tools.values())

    def get_all_tool_names(self) -> List[str]:
        """
        Get names of all tools (loaded and deferred).

        Returns:
            List of tool names
        """
        return list(self._tools.keys()) + list(self._deferred_tools.keys())

    def get_loaded_tool_names(self) -> List[str]:
        """
        Get names of loaded tools only.

        Returns:
            List of loaded tool names
        """
        return list(self._tools.keys())

    def get_deferred_tool_names(self) -> List[str]:
        """
        Get names of deferred (not yet loaded) tools.

        Returns:
            List of deferred tool names
        """
        return list(self._deferred_tools.keys())

    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Get all loaded tools in a category.

        Args:
            category: Tool category

        Returns:
            List of tools in the category
        """
        tool_names = self._by_category.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_tools_by_priority(self, priority: ToolPriority) -> List[BaseTool]:
        """
        Get all loaded tools with a priority level.

        Args:
            priority: Tool priority

        Returns:
            List of tools with the priority
        """
        tool_names = self._by_priority.get(priority, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_tools_by_tag(self, tag: str) -> List[BaseTool]:
        """
        Get all loaded tools with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of tools with the tag
        """
        tool_names = self._by_tag.get(tag, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def _get_searchable_tools(self, category: Optional[ToolCategory] = None) -> List[Any]:
        """
        Get all tools (loaded and deferred) for searching.
        Returns mixed list of Tool instances and deferred info dicts.
        """
        results = []

        # Add loaded tools
        loaded = self.get_tools_by_category(category) if category else self.get_all_tools()
        results.extend(loaded)

        # Add deferred tools
        for name, info in self._deferred_tools.items():
            if category and info["category"] != category:
                continue

            # Create a lightweight searchable object/proxy
            # Or just use the BaseTool if we can... we can't fully instantiate it without loading.
            # But search usually just needs metadata.
            # Let's create a minimal object that mimics BaseTool just for search.

            class DeferredToolProxy:
                def __init__(self, name, info):
                    self.name = name
                    self.description = info["metadata"].get("description", "")
                    self.category = info["category"]
                    self.priority = info["priority"]
                    self.metadata = type(
                        "Metadata",
                        (),
                        {
                            "tags": info["metadata"].get("tags", []),
                            "input_schema": info["metadata"].get("input_schema", {}),
                        },
                    )()
                    self.defer_loading = True

                def matches_query(self, query: str) -> bool:
                    q = query.lower()
                    if q in self.name.lower():
                        return True
                    if q in self.description.lower():
                        return True
                    if any(q in t.lower() for t in self.metadata.tags):
                        return True
                    return False

            results.append(DeferredToolProxy(name, info))

        return results

    def search_tools(
        self,
        query: str,
        category: Optional[ToolCategory] = None,
        limit: int = 10,
    ) -> List[Any]:
        """
        Search for tools matching a query.
        Searches in both loaded and deferred tools.

        Args:
            query: Search query (matches name, description, tags)
            category: Optional category filter
            limit: Maximum number of results

        Returns:
            List of matching tools (Tool instances or proxies)
        """
        self._search_count += 1

        # Get all tools to search
        tools = self._get_searchable_tools(category)

        # Filter by query
        results = [tool for tool in tools if tool.matches_query(query)]

        # Sort by relevance
        query_lower = query.lower()
        results.sort(
            key=lambda t: (
                0 if t.name.lower() == query_lower else 1,  # Exact match first
                -len(t.name),  # Shorter names first
            )
        )

        return results[:limit]

    async def load_tool(self, name: str) -> BaseTool:
        """
        Load a deferred tool on demand.

        Args:
            name: Tool name to load

        Returns:
            Loaded tool instance

        Raises:
            ValueError: If tool not found or already loaded
        """
        # Check if already loaded
        if name in self._tools:
            logger.debug(f"Tool {name} already loaded")
            return self._tools[name]

        # Check if deferred
        if name not in self._deferred_tools:
            raise ValueError(f"Tool {name} not found in registry")

        # Load the tool
        tool_info = self._deferred_tools[name]
        loader = tool_info["loader"]

        logger.info(f"Loading deferred tool: {name}")
        tool = await loader()

        # Register as loaded
        self._tools[name] = tool
        self._index_tool(tool)
        del self._deferred_tools[name]

        self._load_count += 1

        return tool

    async def load_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Load all deferred tools in a category.

        Args:
            category: Category to load

        Returns:
            List of loaded tools
        """
        if category.value in self._loaded_categories:
            logger.debug(f"Category {category.value} already loaded")
            return self.get_tools_by_category(category)

        # Find deferred tools in this category
        deferred_in_category = [
            name for name, info in self._deferred_tools.items() if info["category"] == category
        ]

        logger.info(f"Loading category {category.value}: {len(deferred_in_category)} tools")

        # Load all tools in category
        loaded_tools = []
        for tool_name in deferred_in_category:
            try:
                tool = await self.load_tool(tool_name)
                loaded_tools.append(tool)
            except Exception as e:
                logger.error(f"Failed to load tool {tool_name}: {e}")

        self._loaded_categories.add(category.value)

        return loaded_tools

    def is_tool_loaded(self, name: str) -> bool:
        """
        Check if a tool is loaded.

        Args:
            name: Tool name

        Returns:
            True if tool is loaded
        """
        return name in self._tools

    def is_category_loaded(self, category: ToolCategory) -> bool:
        """
        Check if a category is fully loaded.

        Args:
            category: Category to check

        Returns:
            True if category is loaded
        """
        return category.value in self._loaded_categories

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_tools": len(self._tools) + len(self._deferred_tools),
            "loaded_tools": len(self._tools),
            "deferred_tools": len(self._deferred_tools),
            "loaded_categories": len(self._loaded_categories),
            "load_count": self._load_count,
            "search_count": self._search_count,
            "tools_by_category": {
                cat.value: len(tools) for cat, tools in self._by_category.items()
            },
            "tools_by_priority": {
                pri.value: len(tools) for pri, tools in self._by_priority.items()
            },
        }

    def get_all_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get MCP Tool definitions for all loaded tools.

        Returns:
            List of MCP Tool definition dictionaries
        """
        return [tool.to_mcp_tool() for tool in self._tools.values()]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool by name.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
        """
        # Load if deferred
        if name in self._deferred_tools:
            await self.load_tool(name)

        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        # Execute with tracking
        return await tool.execute_with_tracking(**arguments)

    def clear(self) -> None:
        """Clear all tools from registry (for testing)."""
        self._tools.clear()
        self._deferred_tools.clear()
        self._loaded_categories.clear()
        self._by_category.clear()
        self._by_priority.clear()
        self._by_tag.clear()
        self._load_count = 0
        self._search_count = 0


def get_global_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """Reset the global registry (for testing)."""
    global _global_registry
    _global_registry = None
