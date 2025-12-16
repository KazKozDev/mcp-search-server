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
from .tools.healthcheck import healthcheck
from .tools.maps_tool import search_maps
from .tools.wikipedia import search_wikipedia, get_wikipedia_summary
from .tools.link_parser import extract_content_from_url
from .tools.pdf_parser import parse_pdf
from .tools.datetime_tool import get_current_datetime
from .tools.geolocation import get_location_by_ip
from .enrich import enrich_results

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("mcp-search-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_web",
            description="Search the web using DuckDuckGo. Returns a list of search results with titles, URLs, and snippets. Supports filtering by time for recent results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Search mode: 'web' for regular web search, 'news' for DuckDuckGo News",
                        "enum": ["web", "news"],
                        "default": "web",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    },
                    "timelimit": {
                        "type": ["string", "null"],
                        "description": "Filter results by time: 'd' (past day), 'w' (past week), 'm' (past month), 'y' (past year), null (all time)",
                        "enum": ["d", "w", "m", "y", None]
                    },
                    "region": {
                        "type": "string",
                        "description": "DuckDuckGo region/locale code (e.g., 'ru-ru', 'us-en', 'wt-wt'). If omitted, server picks a default based on the query.",
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
                    }
                },
                "required": ["query"]
            }
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
            name="healthcheck",
            description="Run quick healthcheck across providers (DDG web/news, RSS, Wikipedia, content extractor).",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="search_wikipedia",
            description="Search Wikipedia for articles. Returns a list of matching articles with titles, snippets, and URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_wikipedia_summary",
            description="Get a summary of a specific Wikipedia article. Returns the article introduction and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The Wikipedia article title"
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="extract_webpage_content",
            description="Extract and parse content from a web page URL. Uses multiple parsing methods (Readability, Newspaper3k, BeautifulSoup) to get clean text content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to extract content from"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="parse_pdf",
            description="Extract text content from a PDF file. Supports PDF files from URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the PDF file"
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters to extract (default: 50000)",
                        "default": 50000
                    }
                },
                "required": ["url"]
            }
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
                        "default": "UTC"
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include additional details like day of week, week number, etc. Default: true",
                        "default": True
                    }
                },
                "required": []
            }
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
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    try:
        if name == "search_web":
            query = arguments.get("query")
            mode = arguments.get("mode")
            limit = arguments.get("limit", 10)
            timelimit = arguments.get("timelimit")
            region = arguments.get("region")
            no_cache = arguments.get("no_cache", False)
            do_enrich = arguments.get("enrich_results", False)
            enrich_top_k = arguments.get("enrich_top_k", 3)
            enrich_max_chars = arguments.get("enrich_max_chars", 600)

            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            if mode is None:
                lowered_query = query.lower()
                mode = "news" if any(term in lowered_query for term in ["новост", "news", "сейчас"]) else "web"

            logger.info(f"Searching web for: {query} (mode={mode}, timelimit={timelimit}, region={region})")
            results = await search_duckduckgo(
                query=query,
                limit=limit,
                timelimit=timelimit,
                mode=mode,
                region=region,
                no_cache=no_cache,
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

        elif name == "healthcheck":
            result = await healthcheck()
            import json
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

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
            import json
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
                formatted_output += f"**Day of Week:** {result['day_of_week']} (day #{result['day_of_week_num']})\n"
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
            formatted_output += f"**Region:** {result.get('region', 'N/A')} ({result.get('region_code', 'N/A')})\n"
            formatted_output += f"**City:** {result.get('city', 'N/A')}\n"
            if result.get('zip'):
                formatted_output += f"**ZIP Code:** {result.get('zip')}\n"

            formatted_output += "\n## Timezone\n\n"
            formatted_output += f"**Timezone:** {result.get('timezone', 'N/A')}\n"

            formatted_output += "\n## Coordinates\n\n"
            formatted_output += f"**Latitude:** {result.get('latitude', 'N/A')}\n"
            formatted_output += f"**Longitude:** {result.get('longitude', 'N/A')}\n"

            formatted_output += "\n## Network Information\n\n"
            formatted_output += f"**ISP:** {result.get('isp', 'N/A')}\n"
            formatted_output += f"**Organization:** {result.get('organization', 'N/A')}\n"
            if result.get('as_number'):
                formatted_output += f"**AS Number:** {result.get('as_number')}\n"

            return [TextContent(type="text", text=formatted_output)]

        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def run():
    """Entry point for the server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
