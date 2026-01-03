"""MCP Search Server Tools - Organized by category.

This module provides access to all tools organized into categories:
- web: Web search and content extraction
- knowledge: Wikipedia, academic sources (arXiv, PubMed, GDELT)
- social: GitHub and Reddit
- analysis: Credibility assessment, summarization, calculations
- context: Date/time and geolocation
- files: File management
- meta: Tool discovery (Phase 4)

All tools are re-exported at the top level for backward compatibility.
"""

# Import base classes
from .base import (
    BaseTool,
    FunctionTool,
    ToolMetadata,
    ToolCategory,
    ToolPriority,
)

# Web Search & Content (6 tools)
from .web import (
    search_web,
    search_duckduckgo,
    extract_webpage_content,
    parse_pdf,
    search_maps,
    parse_rss,
)

# Knowledge & Academic (6 tools)
from .knowledge import (
    search_wikipedia,
    get_wikipedia_summary,
    get_wikipedia_content,
    search_arxiv,
    search_pubmed,
    search_gdelt,
)

# Social & Code (4 tools)
from .social import (
    search_github,
    get_github_readme,
    search_reddit,
    get_reddit_comments,
)

# Analysis & Processing (3 tools)
from .analysis import (
    assess_source_credibility,
    summarize_text,
    calculator,
)

# Context & Location (2 tools)
from .context import (
    get_current_datetime,
    get_location_by_ip,
)

# File Management (1 tool - contains multiple functions)
from .files import (
    file_manager,
)

# Meta tools (Phase 4)
from .meta import (
    search_tools,
    list_tool_categories,
    get_tool_info,
)

__all__ = [
    # Base classes
    "BaseTool",
    "FunctionTool",
    "ToolMetadata",
    "ToolCategory",
    "ToolPriority",
    # Web
    "search_web",
    "search_duckduckgo",
    "extract_webpage_content",
    "parse_pdf",
    "search_maps",
    "parse_rss",
    # Knowledge
    "search_wikipedia",
    "get_wikipedia_summary",
    "get_wikipedia_content",
    "search_arxiv",
    "search_pubmed",
    "search_gdelt",
    # Social
    "search_github",
    "get_github_readme",
    "search_reddit",
    "get_reddit_comments",
    # Analysis
    "assess_source_credibility",
    "summarize_text",
    "calculator",
    # Context
    "get_current_datetime",
    "get_location_by_ip",
    # Files
    "file_manager",
    # Meta
    "search_tools",
    "list_tool_categories",
    "get_tool_info",
]
