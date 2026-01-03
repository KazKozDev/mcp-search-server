"""Tool loader with automatic registration from categories."""

import asyncio
import logging
import importlib
from typing import List, Callable, Dict, Any, Optional

from mcp.server import Server
from mcp.types import Tool

from ..tools.base import ToolCategory, ToolPriority, ToolMetadata, FunctionTool, BaseTool
from .tool_registry import ToolRegistry, get_global_registry
from .category_manager import CategoryManager

logger = logging.getLogger(__name__)


def load_tool_config() -> Dict[str, Any]:
    """
    Load tool configuration from YAML.
    
    Returns:
        Tool configuration dictionary
    """
    import yaml
    import os
    from pathlib import Path
    
    # Try multiple locations
    possible_paths = [
        "config/tool_config.yaml",
        Path(__file__).parent.parent.parent.parent / "config" / "tool_config.yaml",
    ]
    
    for path in possible_paths:
        path_str = str(path)
        if os.path.exists(path_str):
            try:
                with open(path_str, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load tool config from {path_str}: {e}")
                return {}
    
    logger.warning("Tool config not found, using defaults")
    return {"tools": {}, "defaults": {}}


def _get_module_path(tool_name: str, config: Dict[str, Any]) -> str:
    """Helper to determine import path for a tool based on convention."""
    category = config.get("category", "web")
    
    # Map common tool names to their modules if they don't follow standard convention
    # This separation allows us to move files freely in future without breaking config
    module_map = {
        "search_web": "unified_search",
        "search_duckduckgo": "duckduckgo",
        "extract_webpage_content": "link_parser",
        "assess_source_credibility": "credibility",
    }
    
    module_name = module_map.get(tool_name, tool_name)
    # Remove 'search_' prefix if it exists in tool name but not module
    if module_name.startswith("search_") and module_name not in ["search_web"]:
        # Try simple name (e.g. search_github -> github) works for most
        simple_name = module_name.replace("search_", "")
        return f"..tools.{category}.{simple_name}"
        
    return f"..tools.{category}.{module_name}"


def register_tool_from_config(
    server: Server,
    registry: ToolRegistry,
    tool_name: str,
    tool_conf: Dict[str, Any],
) -> None:
    """
    Register a tool based on configuration, supporting deferred loading.
    
    Args:
        server: MCP Server instance
        registry: Tool registry
        tool_name: Name of the tool
        tool_conf: Configuration dict for the tool
    """
    category_str = tool_conf.get("category", "web").upper()
    try:
        category = ToolCategory[category_str]
    except KeyError:
        logger.warning(f"Unknown category {category_str} for tool {tool_name}, defaulting to WEB")
        category = ToolCategory.WEB

    priority_str = tool_conf.get("priority", "MEDIUM").upper()
    priority = getattr(ToolPriority, priority_str, ToolPriority.MEDIUM)
    
    defer_loading = tool_conf.get("defer_loading", True)
    
    # Force load if schema is missing so we can generate it from function signature
    if defer_loading and not tool_conf.get("input_schema"):
        # We need to load the tool to inspect the function and generate schema
        logger.debug(f"Forcing load of {tool_name} to generate input schema")
        defer_loading = False
    
    # Metadata for the tool
    description = tool_conf.get("description", f"Tool {tool_name}")
    tags = tool_conf.get("tags", [])
    
    metadata = ToolMetadata(
        name=tool_name,
        description=description,
        category=category,
        priority=priority,
        tags=tags,
        defer_loading=defer_loading
    )

    if defer_loading:
        # Define the loader function
        async def loader() -> BaseTool:
            logger.info(f"Lazy loading tool: {tool_name}")
            return _import_and_get_tool(tool_name, tool_conf)

        # Create a placeholder function tool that triggers the loader
        # But wait, registry handles deferment. We just need to pass the loader func.
        # However, BaseTool requires a synchronous initialization usually. 
        # For Registry's deferred loading, we register with a loader_func.
        
        # We construct a dummy/proxy tool to holding metadata in registry?
        # Actually registry.register_tool with defer=True takes a tool instance AND a loader.
        # But we probably don't want to import the module to create the tool instance yet.
        # We need a lightweight way to register.
        
        # Let's create a minimal ProxyTool or ensure registry can handle bare metadata.
        # Registry.register_tool expects a BaseTool instance.
        # So we create a dummy FunctionTool with the correct metadata but a no-op func.
        dummy_tool = FunctionTool(metadata, lambda: None)
        
        registry.register_tool(dummy_tool, defer=True, loader_func=loader)
        logger.debug(f"Registered deferred tool: {tool_name}")
        
    else:
        # Load immediately
        try:
            tool_instance = _import_and_get_tool(tool_name, tool_conf)
            registry.register_tool(tool_instance, defer=False)
            logger.debug(f"Registered immediate tool: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to load immediate tool {tool_name}: {e}")


def _import_and_get_tool(tool_name: str, tool_conf: Dict[str, Any]) -> BaseTool:
    """
    Dynamically import and return the tool instance.
    This assumes that the module exports the tool function or class.
    """
    # 1. Determine module and import it
    # We rely on the reorganization structure: mcp_search_server.tools.<category>.<module>
    category = tool_conf.get("category", "web")
    
    # Heuristic map to find module name from tool name
    # Most tools follow: search_github -> social.github
    # Some don't: search_web -> web.unified_search
    
    module_name = tool_name
    if tool_name == "search_web": module_name = "unified_search"
    elif tool_name == "extract_webpage_content": module_name = "link_parser"
    elif tool_name == "assess_source_credibility": module_name = "credibility"
    elif tool_name.startswith("search_"): module_name = tool_name.replace("search_", "")
    elif tool_name.startswith("get_"): module_name = tool_name.replace("get_", "") # e.g. get_current_datetime -> datetime_tool? No, datetime_tool is module
    
    # Specific fixes for our structure
    if tool_name == "get_current_datetime": module_name = "datetime_tool"
    if tool_name == "get_location_by_ip": module_name = "geolocation"
    if "wikipedia" in tool_name: module_name = "wikipedia"
    if "github" in tool_name: module_name = "github"
    if "reddit" in tool_name: module_name = "reddit"
    if "file" in tool_name: module_name = "file_manager"
    
    import_path = f"mcp_search_server.tools.{category}.{module_name}"
    
    try:
        module = importlib.import_module(import_path)
    except ImportError:
        # Fallback to importing from category package directly
        import_path = f"mcp_search_server.tools.{category}"
        logger.debug(f"Module import failed, trying category package: {import_path}")
        module = importlib.import_module(import_path)

    # 2. Get the function from the module
    # The function name usually matches tool_name, but sometimes aliased
    func = getattr(module, tool_name, None)
    
    # Handle aliases (e.g. search_github -> search_github_repos)
    if not func:
        if tool_name == "search_github": func = getattr(module, "search_github_repos", None)
        elif tool_name == "search_reddit": func = getattr(module, "search_reddit_posts", None)
        elif tool_name == "get_reddit_comments": func = getattr(module, "get_reddit_post_comments", None)
        elif tool_name == "extract_webpage_content": func = getattr(module, "extract_content_from_url", None)
        elif tool_name == "parse_rss": func = getattr(module, "search_rss", None)
    
    if not func:
        raise ImportError(f"Could not find function for {tool_name} in {import_path}")

    # 3. Create metdata and tool wrapper
    # We recreate metadata to ensure it's fresh
    metadata = ToolMetadata(
        name=tool_name,
        description=tool_conf.get("description", ""),
        category=ToolCategory[tool_conf.get("category", "web").upper()],
        priority=getattr(ToolPriority, tool_conf.get("priority", "MEDIUM").upper(), ToolPriority.MEDIUM),
        tags=tool_conf.get("tags", []),
        # In a real scenario, we'd extract the schema from the function signature or config
        # For now, we assume schema handling is done inside the tool wrapper or server
    )
    
    return FunctionTool(metadata, func)


def register_all_tools(server: Server) -> ToolRegistry:
    """
    Register all tools from configuration.
    
    Args:
        server: MCP Server instance
        
    Returns:
        Configured ToolRegistry
    """
    registry = get_global_registry()
    config = load_tool_config()
    tools_conf = config.get("tools", {})
    
    # Always register meta tools immediately
    from ..tools.meta import search_tools, list_tool_categories, get_tool_info
    
    meta_tools = [
        ("search_tools", search_tools, "Search available tools"),
        ("list_tool_categories", list_tool_categories, "List tool categories"),
        ("get_tool_info", get_tool_info, "Get detailed tool info"),
    ]
    
    for name, func, desc in meta_tools:
        meta = ToolMetadata(
            name=name,
            description=desc,
            category=ToolCategory.META,
            priority=ToolPriority.HIGH,
            tags=["meta", "discovery"],
            defer_loading=False
        )
        registry.register_tool(FunctionTool(meta, func), defer=False)

    # Register other tools from config
    logger.info(f"Registering {len(tools_conf)} tools from config...")
    
    for name, conf in tools_conf.items():
        register_tool_from_config(server, registry, name, conf)
    
    stats = registry.get_statistics()
    logger.info(
        f"Registration complete. Total: {stats['total_tools']}, "
        f"Loaded: {stats['loaded_tools']}, Deferred: {stats['deferred_tools']}"
    )
    
    return registry


def get_tool_list(registry: ToolRegistry) -> List[Tool]:
    """
    Get list of all REGISTERED tools as MCP Tool objects.
    Note: For deferred tools, this returns their metadata without loading implementation.
    """
    tools = []
    # Combine loaded and deferred tools
    all_names = registry.get_all_tool_names()
    
    for name in all_names:
        tool = registry.get_tool(name)
        if tool:
            # Loaded tool
            mcp_tool = Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.metadata.input_schema or {}, 
            )
            tools.append(mcp_tool)
        else:
            # Deferred tool - need to look up metadata from registry internals or config
            # Registry internals are cleaner.
            # But currently registry store for deferred is just a dict with metadata dict.
            deferred_info = registry._deferred_tools.get(name)
            if deferred_info:
                meta = deferred_info.get("metadata", {})
                mcp_tool = Tool(
                    name=name,
                    description=meta.get("description", ""),
                    inputSchema=meta.get("input_schema") or {},
                )
                tools.append(mcp_tool)
    
    return tools
