"""MCP Search Server - Web search, PDF parsing, and content extraction."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import mcp.server.stdio

from .tools.duckduckgo import search_duckduckgo
from .tools.unified_search import search_with_fallback
from .tools.maps_tool import search_maps
from .tools.wikipedia import search_wikipedia, get_wikipedia_summary, get_wikipedia_content
from .tools.link_parser import extract_content_from_url
from .tools.pdf_parser import parse_pdf
from .tools.datetime_tool import get_current_datetime
from .tools.geolocation import get_location_by_ip
from .enrich import enrich_results

# New search tools
from .tools.arxiv import search_arxiv, search_arxiv_by_category
from .tools.github import search_github_repos, get_github_readme
from .tools.reddit import search_reddit, get_reddit_comments
from .tools.pubmed import search_pubmed
from .tools.gdelt import search_gdelt
from .tools.credibility import assess_source_credibility
from .tools.summarizer import summarize_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("mcp-search-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_web",
            description="Search the web with smart fallback across multiple engines (DuckDuckGo, Qwant, Brave, Startpage). Returns search results with titles, URLs, and snippets. Auto-fallback ensures results even if primary engine fails.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "mode": {
                        "type": "string",
                        "description": "Search mode: 'web' for regular web search, 'news' for news search",
                        "enum": ["web", "news"],
                        "default": "web",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10,
                    },
                    "timelimit": {
                        "type": ["string", "null"],
                        "description": "Filter results by time: 'd' (past day), 'w' (past week), 'm' (past month), 'y' (past year), null (all time)",
                        "enum": ["d", "w", "m", "y", None],
                    },
                    "engine": {
                        "type": "string",
                        "description": "Specific search engine to use: 'duckduckgo', 'qwant', 'brave', 'startpage', or leave empty for smart fallback (default: auto-fallback)",
                        "enum": ["duckduckgo", "qwant", "brave", "startpage"],
                    },
                    "use_fallback": {
                        "type": "boolean",
                        "description": "Enable automatic fallback to other engines if primary fails (default: true)",
                        "default": True,
                    },
                    "no_cache": {
                        "type": "boolean",
                        "description": "Disable caching for this request (default: false)",
                        "default": False,
                    },
                    "enrich_results": {
                        "type": "boolean",
                        "description": "Fetch a short preview from top results (default: false)",
                        "default": False,
                    },
                    "enrich_top_k": {
                        "type": "integer",
                        "description": "How many top results to enrich (default: 3)",
                        "default": 3,
                    },
                    "enrich_max_chars": {
                        "type": "integer",
                        "description": "Max preview chars per result (default: 600)",
                        "default": 600,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_maps",
            description="Search places/addresses using OpenStreetMap Nominatim.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "country_codes": {
                        "type": "string",
                        "description": "Comma-separated ISO country codes (e.g., 'ru', 'us,ca')",
                    },
                    "no_cache": {"type": "boolean", "default": False},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_wikipedia",
            description="Search Wikipedia for articles. Returns a list of matching articles with titles, snippets, and URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_wikipedia_summary",
            description="Get a summary of a specific Wikipedia article. Returns the article introduction and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The Wikipedia article title"}
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="extract_webpage_content",
            description="Extract and parse content from a web page URL. Uses multiple parsing methods (Readability, Newspaper3k, BeautifulSoup) to get clean text content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to extract content from"}
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="parse_pdf",
            description="Extract text content from a PDF file. Supports PDF files from URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL of the PDF file"},
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters to extract (default: 50000)",
                        "default": 50000,
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="get_current_datetime",
            description="Get current date and time with timezone information. Use this tool to know what time it is right now, today's date, day of week, etc. Essential for time-aware responses.",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (e.g., 'UTC', 'Europe/Moscow', 'America/New_York'). Default: 'UTC'",
                        "default": "UTC",
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include additional details like day of week, week number, etc. Default: true",
                        "default": True,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_location_by_ip",
            description="Get geolocation information based on IP address. Returns country, city, timezone, coordinates, ISP, and more. Useful for location-aware responses and automatic timezone detection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "IP address to lookup (e.g., '8.8.8.8'). If not provided, detects the server's public IP location.",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="search_arxiv",
            description="Search academic papers on arXiv. Returns scientific publications with metadata, abstracts, authors, and PDF links. Supports various categories like cs.AI, cs.LG, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (supports arXiv query syntax)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional arXiv category filter (e.g., 'cs.AI', 'cs.LG')",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_github",
            description="Search GitHub repositories. Returns repository metadata including stars, language, description, and URLs. Great for finding open-source projects and code examples.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'LLM agents language:python')",
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by: 'stars', 'forks', or 'updated' (default: 'stars')",
                        "default": "stars",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_github_readme",
            description="Get README content from a GitHub repository. Useful for understanding what a project does.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in format 'owner/repo' (e.g., 'openai/gpt-4')",
                    },
                },
                "required": ["repo"],
            },
        ),
        Tool(
            name="search_reddit",
            description="Search Reddit posts and discussions. Returns posts with titles, scores, comments count, and content. Can search specific subreddits or all of Reddit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "subreddit": {
                        "type": "string",
                        "description": "Optional subreddit to search in (e.g., 'LocalLLaMA')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                    "time_filter": {
                        "type": "string",
                        "description": "Time filter: 'hour', 'day', 'week', 'month', 'year', 'all' (default: 'all')",
                        "default": "all",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_reddit_comments",
            description="Get comments from a specific Reddit post. Useful for reading discussions and community insights.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Reddit post URL"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of comments (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="search_pubmed",
            description="Search medical and scientific publications on PubMed. Returns peer-reviewed research articles with abstracts, authors, journal info, and DOIs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'machine learning in medicine')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_gdelt",
            description="Search news articles using GDELT Global Database. Returns recent news from around the world with metadata about sources and publication dates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (news keyword)"},
                    "timespan": {
                        "type": "string",
                        "description": "Time span: '1d', '7d', '1m' (default: '1d')",
                        "default": "1d",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_wikipedia_content",
            description="Get full Wikipedia article content with sections and related articles. More detailed than search_wikipedia.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Wikipedia article title"},
                    "lang": {
                        "type": "string",
                        "description": "Language code (default: 'en')",
                        "default": "en",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="assess_source_credibility",
            description="Assess credibility of a web source using Bayesian analysis. Evaluates 30+ signals including domain age (via WHOIS), content quality, citation network, and metadata. Returns credibility score (0-1) with confidence intervals and recommendation. No API keys required.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to assess"},
                    "title": {"type": "string", "description": "Document title (optional)"},
                    "content": {
                        "type": "string",
                        "description": "Full text content (optional, improves accuracy)",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Structured metadata (optional): year, authors, citations, doi, is_peer_reviewed",
                        "properties": {
                            "year": {"type": "integer"},
                            "authors": {"type": "array", "items": {"type": "string"}},
                            "citations": {"type": "integer"},
                            "doi": {"type": "string"},
                            "is_peer_reviewed": {"type": "boolean"},
                        },
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="summarize_text",
            description="Summarize long text using multiple strategies (TF-IDF extractive, keyword-based, or heuristic). Fast, works without API keys. Best for articles, papers, documents. Uses NLTK if available, falls back to simple heuristic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to summarize"},
                    "strategy": {
                        "type": "string",
                        "description": "Summarization strategy: 'auto' (default), 'extractive_tfidf', 'extractive_keyword', 'heuristic'",
                        "enum": ["auto", "extractive_tfidf", "extractive_keyword", "heuristic"],
                        "default": "auto",
                    },
                    "compression_ratio": {
                        "type": "number",
                        "description": "Target compression ratio 0-1 (default: 0.3 = 30% of original)",
                        "minimum": 0.1,
                        "maximum": 0.9,
                        "default": 0.3,
                    },
                },
                "required": ["text"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(
    name: str, arguments: Any
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    try:
        if name == "search_web":
            query = arguments.get("query")
            mode = arguments.get("mode")
            limit = arguments.get("limit", 10)
            timelimit = arguments.get("timelimit")
            engine = arguments.get("engine")
            use_fallback = arguments.get("use_fallback", True)
            no_cache = arguments.get("no_cache", False)
            do_enrich = arguments.get("enrich_results", False)
            enrich_top_k = arguments.get("enrich_top_k", 3)
            enrich_max_chars = arguments.get("enrich_max_chars", 600)

            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            if mode is None:
                lowered_query = query.lower()
                mode = (
                    "news"
                    if any(term in lowered_query for term in ["новост", "news", "сейчас"])
                    else "web"
                )

            logger.info(
                f"Searching web for: {query} (mode={mode}, timelimit={timelimit}, "
                f"engine={engine or 'auto'}, fallback={use_fallback})"
            )

            # Use unified search with fallback
            results = await search_with_fallback(
                query=query,
                limit=limit,
                timelimit=timelimit,
                mode=mode,
                engine=engine,
                no_cache=no_cache,
                use_fallback=use_fallback,
            )

            if do_enrich and results:
                results = await enrich_results(
                    results,
                    top_k=int(enrich_top_k),
                    max_chars=int(enrich_max_chars),
                    no_cache=no_cache,
                )

            if not results:
                return [TextContent(type="text", text="No results found")]

            formatted_results = "# Search Results\n\n"
            for i, result in enumerate(results, 1):
                formatted_results += f"## {i}. {result.get('title', 'No title')}\n"
                formatted_results += f"**URL:** {result.get('url', 'No URL')}\n"
                formatted_results += f"**Snippet:** {result.get('snippet', 'No snippet')}\n\n"

                if result.get("preview"):
                    formatted_results += f"**Preview:** {result.get('preview')}\n\n"

            return [TextContent(type="text", text=formatted_results)]

        elif name == "search_maps":
            query = arguments.get("query")
            limit = arguments.get("limit", 5)
            country_codes = arguments.get("country_codes")
            no_cache = arguments.get("no_cache", False)
            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            results = await search_maps(
                query,
                limit=limit,
                country_codes=country_codes,
                no_cache=no_cache,
            )
            if not results:
                return [TextContent(type="text", text="No results found")]

            formatted_output = "# Maps Results\n\n"
            for i, result in enumerate(results, 1):
                formatted_output += f"## {i}. {result.get('title','No title')}\n"
                if result.get("url"):
                    formatted_output += f"**URL:** {result.get('url')}\n"
                formatted_output += f"**Snippet:** {result.get('snippet','')}\n\n"
            return [TextContent(type="text", text=formatted_output)]

        elif name == "search_wikipedia":
            query = arguments.get("query")
            limit = arguments.get("limit", 5)

            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            logger.info(f"Searching Wikipedia for: {query}")
            results = await search_wikipedia(query, limit)

            if not results:
                return [TextContent(type="text", text="No results found")]

            formatted_results = "# Wikipedia Search Results\n\n"
            for i, result in enumerate(results, 1):
                formatted_results += f"## {i}. {result.get('title', 'No title')}\n"
                formatted_results += f"**URL:** {result.get('url', 'No URL')}\n"
                formatted_results += f"**Snippet:** {result.get('snippet', 'No snippet')}\n\n"

            return [TextContent(type="text", text=formatted_results)]

        elif name == "get_wikipedia_summary":
            title = arguments.get("title")

            if not title:
                return [TextContent(type="text", text="Error: title parameter is required")]

            logger.info(f"Getting Wikipedia summary for: {title}")
            result = await get_wikipedia_summary(title)

            formatted_result = f"# {result.get('title', 'Wikipedia Article')}\n\n"
            formatted_result += f"**URL:** {result.get('url', 'No URL')}\n\n"
            formatted_result += f"{result.get('extract', 'No content available')}\n"

            return [TextContent(type="text", text=formatted_result)]

        elif name == "extract_webpage_content":
            url = arguments.get("url")

            if not url:
                return [TextContent(type="text", text="Error: url parameter is required")]

            logger.info(f"Extracting content from: {url}")
            content = await extract_content_from_url(url)

            if content.startswith("Error"):
                return [TextContent(type="text", text=content)]

            formatted_content = f"# Extracted Content from {url}\n\n{content}"
            return [TextContent(type="text", text=formatted_content)]

        elif name == "parse_pdf":
            url = arguments.get("url")
            max_chars = arguments.get("max_chars", 50000)

            if not url:
                return [TextContent(type="text", text="Error: url parameter is required")]

            logger.info(f"Parsing PDF from: {url}")
            content = await parse_pdf(url, max_chars)

            if content.startswith("Error"):
                return [TextContent(type="text", text=content)]

            formatted_content = f"# PDF Content from {url}\n\n{content}"
            return [TextContent(type="text", text=formatted_content)]

        elif name == "get_current_datetime":
            timezone = arguments.get("timezone", "UTC")
            include_details = arguments.get("include_details", True)

            logger.info(f"Getting current datetime for timezone: {timezone}")
            result = await get_current_datetime(timezone, include_details)

            if "error" in result:
                formatted_output = f"# ❌ Error\n\n{result['error']}\n\n"
                if "available_timezones_sample" in result:
                    formatted_output += "## Available timezones (sample):\n"
                    for tz in result["available_timezones_sample"]:
                        formatted_output += f"- {tz}\n"
                return [TextContent(type="text", text=formatted_output)]

            # Format successful result
            formatted_output = "# 🕐 Current Date and Time\n\n"
            formatted_output += f"**Timezone:** {result['timezone']}\n"
            formatted_output += f"**Date:** {result['date']}\n"
            formatted_output += f"**Time:** {result['time']}\n"
            formatted_output += f"**ISO Format:** {result['datetime']}\n"
            formatted_output += f"**Unix Timestamp:** {result['timestamp']}\n\n"

            if include_details and "formatted" in result:
                formatted_output += "## Formatted Representations\n\n"
                formatted_output += f"**Full:** {result['formatted']['full']}\n"
                formatted_output += f"**Date (long):** {result['formatted']['date_long']}\n"
                formatted_output += f"**Date (short):** {result['formatted']['date_short']}\n"
                formatted_output += f"**Time (12h):** {result['formatted']['time_12h']}\n"
                formatted_output += f"**Time (24h):** {result['formatted']['time_24h']}\n\n"

                formatted_output += "## Additional Details\n\n"
                formatted_output += (
                    f"**Day of Week:** {result['day_of_week']} (day #{result['day_of_week_num']})\n"
                )
                formatted_output += f"**Week Number:** {result['week_number']}\n"
                formatted_output += f"**Year:** {result['year']}\n"
                formatted_output += f"**Month:** {result['month']}\n"
                formatted_output += f"**Day:** {result['day']}\n"

            return [TextContent(type="text", text=formatted_output)]

        elif name == "get_location_by_ip":
            ip_address = arguments.get("ip_address")

            logger.info(f"Getting location for IP: {ip_address or 'auto'}")
            result = await get_location_by_ip(ip_address)

            if "error" in result:
                formatted_output = f"# ❌ Error\n\n{result['error']}\n"
                formatted_output += f"**IP:** {result.get('ip', 'unknown')}\n"
                return [TextContent(type="text", text=formatted_output)]

            # Format successful result
            formatted_output = "# 📍 Location Information\n\n"
            formatted_output += f"**IP Address:** {result.get('ip', 'N/A')}\n\n"

            formatted_output += "## Location\n\n"
            formatted_output += f"**Country:** {result.get('country', 'N/A')} ({result.get('country_code', 'N/A')})\n"
            formatted_output += (
                f"**Region:** {result.get('region', 'N/A')} ({result.get('region_code', 'N/A')})\n"
            )
            formatted_output += f"**City:** {result.get('city', 'N/A')}\n"
            if result.get("zip"):
                formatted_output += f"**ZIP Code:** {result.get('zip')}\n"

            formatted_output += "\n## Timezone\n\n"
            formatted_output += f"**Timezone:** {result.get('timezone', 'N/A')}\n"

            formatted_output += "\n## Coordinates\n\n"
            formatted_output += f"**Latitude:** {result.get('latitude', 'N/A')}\n"
            formatted_output += f"**Longitude:** {result.get('longitude', 'N/A')}\n"

            formatted_output += "\n## Network Information\n\n"
            formatted_output += f"**ISP:** {result.get('isp', 'N/A')}\n"
            formatted_output += f"**Organization:** {result.get('organization', 'N/A')}\n"
            if result.get("as_number"):
                formatted_output += f"**AS Number:** {result.get('as_number')}\n"

            return [TextContent(type="text", text=formatted_output)]

        elif name == "search_arxiv":
            query = arguments.get("query")
            max_results = arguments.get("max_results", 10)
            category = arguments.get("category")

            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            logger.info(f"Searching arXiv for: {query}")

            if category:
                results = await search_arxiv_by_category(category, query, max_results)
            else:
                results = await search_arxiv(query, max_results)

            if not results:
                return [TextContent(type="text", text="No arXiv papers found")]

            formatted_results = "# ArXiv Search Results\n\n"
            for i, paper in enumerate(results, 1):
                formatted_results += f"## {i}. {paper.get('title', 'No title')}\n"
                formatted_results += f"**Authors:** {', '.join(paper.get('authors', []))}\n"
                formatted_results += f"**Published:** {paper.get('published', 'N/A')}\n"
                formatted_results += f"**Category:** {paper.get('primary_category', 'N/A')}\n"
                formatted_results += f"**arXiv ID:** {paper.get('id', 'N/A')}\n"
                if paper.get("pdf_url"):
                    formatted_results += f"**PDF:** {paper['pdf_url']}\n"
                if paper.get("abs_url"):
                    formatted_results += f"**URL:** {paper['abs_url']}\n"
                formatted_results += f"\n**Abstract:** {paper.get('abstract', 'No abstract')}\n\n"

            return [TextContent(type="text", text=formatted_results)]

        elif name == "search_github":
            query = arguments.get("query")
            sort = arguments.get("sort", "stars")
            max_results = arguments.get("max_results", 5)

            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            logger.info(f"Searching GitHub for: {query}")
            results = await search_github_repos(query, sort, max_results)

            if not results:
                return [TextContent(type="text", text="No GitHub repositories found")]

            formatted_results = "# GitHub Search Results\n\n"
            for i, repo in enumerate(results, 1):
                formatted_results += f"## {i}. {repo.get('full_name', 'No name')}\n"
                formatted_results += (
                    f"**Description:** {repo.get('description', 'No description')}\n"
                )
                formatted_results += f"**URL:** {repo.get('url', 'N/A')}\n"
                formatted_results += f"**Stars:** ⭐ {repo.get('stars', 0)}\n"
                formatted_results += f"**Language:** {repo.get('language', 'N/A')}\n"
                formatted_results += f"**Updated:** {repo.get('updated_at', 'N/A')}\n\n"

            return [TextContent(type="text", text=formatted_results)]

        elif name == "get_github_readme":
            repo = arguments.get("repo")

            if not repo:
                return [TextContent(type="text", text="Error: repo parameter is required")]

            logger.info(f"Getting README for: {repo}")
            content = await get_github_readme(repo)

            if not content:
                return [TextContent(type="text", text=f"README not found for {repo}")]

            formatted_content = f"# README: {repo}\n\n{content}"
            return [TextContent(type="text", text=formatted_content)]

        elif name == "search_reddit":
            query = arguments.get("query")
            subreddit = arguments.get("subreddit")
            limit = arguments.get("limit", 10)
            time_filter = arguments.get("time_filter", "all")

            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            logger.info(f"Searching Reddit for: {query}")
            results = await search_reddit(query, subreddit, limit, "relevance", time_filter)

            if not results:
                return [TextContent(type="text", text="No Reddit posts found")]

            formatted_results = "# Reddit Search Results\n\n"
            for i, post in enumerate(results, 1):
                formatted_results += f"## {i}. {post.get('title', 'No title')}\n"
                formatted_results += f"**Subreddit:** r/{post.get('subreddit', 'N/A')}\n"
                formatted_results += f"**Author:** u/{post.get('author', 'N/A')}\n"
                formatted_results += f"**Score:** {post.get('score', 0)} | **Comments:** {post.get('num_comments', 0)}\n"
                formatted_results += f"**URL:** {post.get('url', 'N/A')}\n"
                formatted_results += f"**Date:** {post.get('created_utc', 'N/A')}\n"
                if post.get("text"):
                    formatted_results += f"\n**Text:** {post['text']}\n"
                formatted_results += "\n"

            return [TextContent(type="text", text=formatted_results)]

        elif name == "get_reddit_comments":
            url = arguments.get("url")
            limit = arguments.get("limit", 10)

            if not url:
                return [TextContent(type="text", text="Error: url parameter is required")]

            logger.info(f"Getting Reddit comments from: {url}")
            results = await get_reddit_comments(url, limit)

            if not results:
                return [
                    TextContent(type="text", text="No comments found or error fetching comments")
                ]

            formatted_results = f"# Reddit Comments\n\n**Post:** {url}\n\n"
            for i, comment in enumerate(results, 1):
                formatted_results += f"## Comment {i}\n"
                formatted_results += f"**Author:** u/{comment.get('author', 'N/A')}\n"
                formatted_results += f"**Score:** {comment.get('score', 0)}\n"
                formatted_results += f"**Date:** {comment.get('created_utc', 'N/A')}\n"
                formatted_results += f"\n{comment.get('body', 'No content')}\n\n"

            return [TextContent(type="text", text=formatted_results)]

        elif name == "search_pubmed":
            query = arguments.get("query")
            max_results = arguments.get("max_results", 10)

            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            logger.info(f"Searching PubMed for: {query}")
            results = await search_pubmed(query, max_results)

            if not results:
                return [TextContent(type="text", text="No PubMed articles found")]

            formatted_results = "# PubMed Search Results\n\n"
            for i, article in enumerate(results, 1):
                formatted_results += f"## {i}. {article.get('title', 'No title')}\n"
                formatted_results += f"**Authors:** {', '.join(article.get('authors', [])[:5])}\n"
                formatted_results += f"**Journal:** {article.get('journal', 'N/A')}\n"
                formatted_results += f"**Published:** {article.get('pub_date', 'N/A')}\n"
                formatted_results += f"**PMID:** {article.get('pmid', 'N/A')}\n"
                formatted_results += f"**URL:** {article.get('url', 'N/A')}\n"
                if article.get("doi"):
                    formatted_results += f"**DOI:** {article['doi']}\n"
                formatted_results += f"\n**Abstract:** {article.get('abstract', 'No abstract')}\n\n"

            return [TextContent(type="text", text=formatted_results)]

        elif name == "search_gdelt":
            query = arguments.get("query")
            timespan = arguments.get("timespan", "1d")
            max_results = arguments.get("max_results", 10)

            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            logger.info(f"Searching GDELT for: {query}")
            results = await search_gdelt(query, timespan, max_results)

            if not results:
                return [TextContent(type="text", text="No GDELT news articles found")]

            formatted_results = "# GDELT News Results\n\n"
            for i, article in enumerate(results, 1):
                formatted_results += f"## {i}. {article.get('title', 'No title')}\n"
                formatted_results += f"**URL:** {article.get('url', 'N/A')}\n"
                formatted_results += f"**Domain:** {article.get('domain', 'N/A')}\n"
                formatted_results += f"**Country:** {article.get('country', 'N/A')}\n"
                formatted_results += f"**Date:** {article.get('date', 'N/A')}\n\n"

            return [TextContent(type="text", text=formatted_results)]

        elif name == "assess_source_credibility":
            url = arguments.get("url")
            title = arguments.get("title")
            content = arguments.get("content")
            metadata = arguments.get("metadata")

            if not url:
                return [TextContent(type="text", text="Error: url parameter is required")]

            logger.info(f"Assessing credibility of: {url}")
            result = await assess_source_credibility(url, title, content, metadata)

            # Format output
            formatted_output = f"# Credibility Assessment for {result['domain']}\n\n"
            formatted_output += f"**URL:** {result['url']}\n"
            formatted_output += f"**Category:** {result['category']}\n\n"

            formatted_output += "## Credibility Score\n\n"
            formatted_output += f"**Score:** {result['credibility_score']} / 1.0\n"
            formatted_output += f"**Confidence Interval:** {result['confidence_interval'][0]} - {result['confidence_interval'][1]}\n"
            formatted_output += f"**Uncertainty:** ±{result['uncertainty']}\n"
            formatted_output += f"**PageRank:** {result['pagerank']}\n\n"

            formatted_output += f"## Recommendation\n\n{result['recommendation']}\n\n"

            formatted_output += "## Signal Analysis\n\n"
            formatted_output += f"**Prior:** {result['prior']} (category baseline)\n"
            formatted_output += (
                f"**Likelihood Ratio:** {result['likelihood_ratio']} (evidence strength)\n\n"
            )

            formatted_output += "### Key Signals (top 10)\n\n"
            sorted_signals = sorted(result["signals"].items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
            for signal, value in sorted_signals:
                bar = "█" * int(value * 20)
                formatted_output += f"- **{signal}:** {value:.3f} {bar}\n"

            return [TextContent(type="text", text=formatted_output)]

        elif name == "summarize_text":
            text = arguments.get("text")
            strategy = arguments.get("strategy", "auto")
            compression_ratio = arguments.get("compression_ratio", 0.3)

            if not text:
                return [TextContent(type="text", text="Error: text parameter is required")]

            logger.info(f"Summarizing text ({len(text)} chars) with strategy: {strategy}")
            result = await summarize_text(text, strategy, compression_ratio)

            if not result:
                return [TextContent(type="text", text="Error: Failed to summarize text")]

            # Format output
            formatted_output = "# Text Summary\n\n"
            formatted_output += f"**Method:** {result['method']}\n"

            if "stats" in result:
                formatted_output += "**Statistics:**\n"
                for key, value in result["stats"].items():
                    formatted_output += f"- {key}: {value}\n"

            formatted_output += f"\n## Summary\n\n{result['summary']}\n"

            return [TextContent(type="text", text=formatted_output)]

        elif name == "get_wikipedia_content":
            title = arguments.get("title")
            lang = arguments.get("lang", "en")

            if not title:
                return [TextContent(type="text", text="Error: title parameter is required")]

            logger.info(f"Getting Wikipedia content for: {title}")
            result = await get_wikipedia_content(title, lang)

            if not result:
                return [TextContent(type="text", text=f"Wikipedia article not found: {title}")]

            formatted_result = f"# {result.get('title', 'Wikipedia Article')}\n\n"
            formatted_result += f"**URL:** {result.get('url', 'N/A')}\n\n"

            # Add sections
            for section in result.get("sections", []):
                formatted_result += f"## {section.get('title', 'Section')}\n\n"
                for content in section.get("content", []):
                    formatted_result += f"{content}\n\n"

            # Add related articles
            related = result.get("related", [])
            if related:
                formatted_result += "\n## Related Articles\n\n"
                for article in related[:10]:
                    formatted_result += f"- {article}\n"

            return [TextContent(type="text", text=formatted_result)]

        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run():
    """Entry point for the server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
