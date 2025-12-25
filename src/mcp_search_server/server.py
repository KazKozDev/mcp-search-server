"""MCP Search Server - Web search, PDF parsing, and content extraction."""

import asyncio
import json
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
from .tools.file_manager import file_manager
from .tools.calculator import calculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("mcp-search-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_web",
            title="Web Search",
            description="""Search the web with smart fallback across multiple engines (DuckDuckGo, Qwant, Brave, Startpage). Returns search results with titles, URLs, and snippets. Auto-fallback ensures results even if primary engine fails.

## Examples

### Basic search
```json
{"query": "Python tutorials"}
```

### News search with time filter
```json
{"query": "AI news", "mode": "news", "timelimit": "w", "limit": 5}
```

### Search with specific engine and enrichment
```json
{"query": "machine learning", "engine": "duckduckgo", "enrich_results": true, "enrich_top_k": 3}
```""",
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
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "description": "List of search results",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Result title"},
                                "url": {"type": "string", "description": "Result URL"},
                                "snippet": {
                                    "type": "string",
                                    "description": "Result snippet/description",
                                },
                                "preview": {
                                    "type": "string",
                                    "description": "Enriched preview content (if enrich_results=true)",
                                },
                            },
                            "required": ["title", "url", "snippet"],
                        },
                    },
                    "engine_used": {
                        "type": "string",
                        "description": "Search engine that returned results",
                    },
                    "total_results": {
                        "type": "integer",
                        "description": "Number of results returned",
                    },
                },
                "required": ["results", "total_results"],
            },
        ),
        Tool(
            name="search_maps",
            title="Maps Search",
            description="""Search places, addresses, and points of interest using OpenStreetMap Nominatim geocoding service. Returns locations with coordinates, addresses, and map links.

## Examples

### Find a city
```json
{"query": "Moscow, Russia"}
```

### Search restaurants in a country
```json
{"query": "pizza restaurant", "country_codes": "it", "limit": 3}
```

### Find address with multiple countries
```json
{"query": "Central Park", "country_codes": "us,ca", "limit": 5}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Place name, address, or point of interest to search",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5,
                    },
                    "country_codes": {
                        "type": "string",
                        "description": "Comma-separated ISO country codes to filter results (e.g., 'ru', 'us,ca')",
                    },
                    "no_cache": {
                        "type": "boolean",
                        "description": "Disable caching for this request (default: false)",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "places": {
                        "type": "array",
                        "description": "List of found places",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Place name"},
                                "address": {"type": "string", "description": "Full address"},
                                "latitude": {
                                    "type": "number",
                                    "description": "Latitude coordinate",
                                },
                                "longitude": {
                                    "type": "number",
                                    "description": "Longitude coordinate",
                                },
                                "type": {
                                    "type": "string",
                                    "description": "Place type (city, restaurant, etc.)",
                                },
                                "osm_url": {"type": "string", "description": "OpenStreetMap URL"},
                            },
                            "required": ["name", "address", "latitude", "longitude"],
                        },
                    },
                    "total_results": {"type": "integer", "description": "Number of places found"},
                },
                "required": ["places", "total_results"],
            },
        ),
        Tool(
            name="search_wikipedia",
            title="Wikipedia Search",
            description="""Search Wikipedia for articles. Returns a list of matching articles with titles, snippets, and URLs.

## Examples

### Basic search
```json
{"query": "artificial intelligence"}
```

### Search with more results
```json
{"query": "machine learning algorithms", "limit": 10}
```

### Search in specific language
```json
{"query": "quantum computing", "lang": "en", "limit": 5}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5,
                    },
                    "lang": {
                        "type": "string",
                        "description": "Language code for Wikipedia (default: 'en')",
                        "default": "en",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "articles": {
                        "type": "array",
                        "description": "List of found Wikipedia articles",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Article title"},
                                "url": {"type": "string", "description": "Wikipedia URL"},
                                "snippet": {
                                    "type": "string",
                                    "description": "Article snippet/preview",
                                },
                            },
                            "required": ["title", "url"],
                        },
                    },
                    "total_results": {"type": "integer", "description": "Number of articles found"},
                },
                "required": ["articles", "total_results"],
            },
        ),
        Tool(
            name="get_wikipedia_summary",
            title="Wikipedia Summary",
            description="""Get a summary of a specific Wikipedia article. Returns the article introduction, metadata, and key facts.

## Examples

### Get article summary
```json
{"title": "Python (programming language)"}
```

### Get summary in another language
```json
{"title": "Machine learning", "lang": "en"}
```

### Historical figure
```json
{"title": "Albert Einstein"}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The Wikipedia article title"},
                    "lang": {
                        "type": "string",
                        "description": "Language code for Wikipedia (default: 'en')",
                        "default": "en",
                    },
                },
                "required": ["title"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Article title"},
                    "url": {"type": "string", "description": "Wikipedia URL"},
                    "extract": {"type": "string", "description": "Article summary/introduction"},
                    "description": {"type": "string", "description": "Short description"},
                    "thumbnail": {"type": "string", "description": "Thumbnail image URL"},
                },
                "required": ["title", "url", "extract"],
            },
        ),
        Tool(
            name="extract_webpage_content",
            title="Webpage Content Extractor",
            description="""Extract and parse content from a web page URL. Uses multiple parsing methods (Readability, Newspaper3k, BeautifulSoup) to get clean text content.

## Features
- Automatic content extraction using multiple parsers
- Removes ads, navigation, and other clutter
- Extracts main article text and metadata

## Examples

### Extract article content
```json
{"url": "https://example.com/article"}
```

### Extract news article
```json
{"url": "https://techcrunch.com/2024/01/15/some-article/"}
```

### Extract blog post
```json
{"url": "https://blog.example.com/post/my-post"}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to extract content from"}
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Original URL"},
                    "title": {"type": "string", "description": "Page title"},
                    "content": {"type": "string", "description": "Extracted text content"},
                    "author": {"type": "string", "description": "Article author (if found)"},
                    "published_date": {
                        "type": "string",
                        "description": "Publication date (if found)",
                    },
                    "word_count": {
                        "type": "integer",
                        "description": "Word count of extracted content",
                    },
                },
                "required": ["url", "content"],
            },
        ),
        Tool(
            name="parse_pdf",
            title="PDF Parser",
            description="""Extract text content from a PDF file. Supports PDF files from URLs.

## Features
- Extracts text from all pages
- Handles multi-column layouts
- Preserves paragraph structure

## Examples

### Parse PDF from URL
```json
{"url": "https://arxiv.org/pdf/2301.00001.pdf"}
```

### Parse with character limit
```json
{"url": "https://example.com/document.pdf", "max_chars": 10000}
```

### Parse academic paper
```json
{"url": "https://papers.nips.cc/paper/2024/file/example.pdf", "max_chars": 100000}
```""",
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
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Original PDF URL"},
                    "content": {"type": "string", "description": "Extracted text content"},
                    "num_pages": {"type": "integer", "description": "Number of pages in PDF"},
                    "char_count": {"type": "integer", "description": "Total characters extracted"},
                    "truncated": {
                        "type": "boolean",
                        "description": "Whether content was truncated due to max_chars",
                    },
                },
                "required": ["url", "content"],
            },
        ),
        Tool(
            name="get_current_datetime",
            title="Current DateTime",
            description="""Get current date and time with timezone information. Use this tool to know what time it is right now, today's date, day of week, etc. Essential for time-aware responses.

## Features
- Supports all IANA timezones
- Returns formatted date/time in multiple formats
- Includes day of week, week number, and more

## Examples

### Get UTC time
```json
{}
```

### Get time in Moscow
```json
{"timezone": "Europe/Moscow"}
```

### Get time in New York with full details
```json
{"timezone": "America/New_York", "include_details": true}
```

### Get minimal time info
```json
{"timezone": "Asia/Tokyo", "include_details": false}
```""",
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
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "datetime": {"type": "string", "description": "ISO format datetime"},
                    "timezone": {"type": "string", "description": "Timezone name"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Time in HH:MM:SS format"},
                    "timestamp": {"type": "integer", "description": "Unix timestamp"},
                    "year": {"type": "integer", "description": "Year"},
                    "month": {"type": "integer", "description": "Month (1-12)"},
                    "day": {"type": "integer", "description": "Day of month"},
                    "day_of_week": {"type": "string", "description": "Day name (e.g., Monday)"},
                    "day_of_week_num": {
                        "type": "integer",
                        "description": "Day number (1=Monday, 7=Sunday)",
                    },
                    "week_number": {"type": "integer", "description": "ISO week number"},
                    "formatted": {
                        "type": "object",
                        "description": "Various formatted representations",
                        "properties": {
                            "full": {"type": "string"},
                            "date_long": {"type": "string"},
                            "date_short": {"type": "string"},
                            "time_12h": {"type": "string"},
                            "time_24h": {"type": "string"},
                        },
                    },
                    "error": {
                        "type": "string",
                        "description": "Error message if timezone is invalid",
                    },
                },
                "required": ["datetime", "timezone"],
            },
        ),
        Tool(
            name="get_location_by_ip",
            title="IP Geolocation",
            description="""Get geolocation information based on IP address. Returns country, city, timezone, coordinates, ISP, and more. Useful for location-aware responses and automatic timezone detection.

## Features
- Detects country, region, city from IP
- Returns timezone for the location
- Provides coordinates (latitude/longitude)
- Shows ISP and organization info
- No API key required

## Examples

### Get your current location
```json
{}
```

### Lookup specific IP
```json
{"ip_address": "8.8.8.8"}
```

### Lookup Cloudflare DNS
```json
{"ip_address": "1.1.1.1"}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "IP address to lookup (e.g., '8.8.8.8'). If not provided, detects the server's public IP location.",
                    }
                },
                "required": [],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "ip": {"type": "string", "description": "IP address that was looked up"},
                    "country": {"type": "string", "description": "Country name"},
                    "country_code": {"type": "string", "description": "ISO country code"},
                    "region": {"type": "string", "description": "Region/state name"},
                    "region_code": {"type": "string", "description": "Region code"},
                    "city": {"type": "string", "description": "City name"},
                    "zip": {"type": "string", "description": "ZIP/postal code"},
                    "latitude": {"type": "number", "description": "Latitude coordinate"},
                    "longitude": {"type": "number", "description": "Longitude coordinate"},
                    "timezone": {"type": "string", "description": "IANA timezone name"},
                    "isp": {"type": "string", "description": "Internet Service Provider"},
                    "organization": {"type": "string", "description": "Organization name"},
                    "as_number": {"type": "string", "description": "Autonomous System number"},
                    "error": {"type": "string", "description": "Error message if lookup failed"},
                },
                "required": ["ip"],
            },
        ),
        Tool(
            name="search_arxiv",
            title="ArXiv Search",
            description="""Search academic papers on arXiv preprint server. Returns scientific publications with metadata, abstracts, authors, and PDF links.

## Popular Categories
- **cs.AI** - Artificial Intelligence
- **cs.LG** - Machine Learning
- **cs.CL** - Computation and Language (NLP)
- **cs.CV** - Computer Vision
- **stat.ML** - Statistics Machine Learning
- **physics** - Physics papers

## Examples

### Search by topic
```json
{"query": "transformer attention mechanism", "max_results": 5}
```

### Search in specific category
```json
{"query": "reinforcement learning", "category": "cs.LG", "max_results": 10}
```

### Search by author
```json
{"query": "au:Hinton", "max_results": 5}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query. Supports arXiv syntax: 'au:Author', 'ti:Title', 'abs:Abstract', 'cat:Category'",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by arXiv category (e.g., 'cs.AI', 'cs.LG', 'stat.ML')",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "papers": {
                        "type": "array",
                        "description": "List of found papers",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Paper title"},
                                "authors": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of authors",
                                },
                                "abstract": {"type": "string", "description": "Paper abstract"},
                                "arxiv_id": {"type": "string", "description": "ArXiv paper ID"},
                                "pdf_url": {"type": "string", "description": "Direct PDF link"},
                                "published": {"type": "string", "description": "Publication date"},
                                "category": {"type": "string", "description": "Primary category"},
                            },
                            "required": ["title", "authors", "arxiv_id"],
                        },
                    },
                    "total_results": {"type": "integer", "description": "Number of papers found"},
                },
                "required": ["papers", "total_results"],
            },
        ),
        Tool(
            name="search_github",
            title="GitHub Search",
            description="""Search GitHub repositories. Returns repository metadata including stars, forks, language, description, and URLs.

## Search Syntax
- **language:python** - Filter by programming language
- **stars:>1000** - Minimum stars count
- **topic:machine-learning** - Filter by topic
- **user:openai** - Search user's repos

## Examples

### Find Python ML projects
```json
{"query": "machine learning language:python", "sort": "stars", "max_results": 5}
```

### Find recent active repos
```json
{"query": "LLM agents", "sort": "updated", "max_results": 10}
```

### Search by topic
```json
{"query": "topic:mcp-server", "max_results": 5}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query. Supports GitHub syntax: 'language:py', 'stars:>100', 'topic:ai'",
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort results by: 'stars', 'forks', or 'updated'",
                        "enum": ["stars", "forks", "updated"],
                        "default": "stars",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "repositories": {
                        "type": "array",
                        "description": "List of repositories",
                        "items": {
                            "type": "object",
                            "properties": {
                                "full_name": {
                                    "type": "string",
                                    "description": "Full repo name (owner/repo)",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Repository description",
                                },
                                "url": {"type": "string", "description": "GitHub URL"},
                                "stars": {"type": "integer", "description": "Star count"},
                                "forks": {"type": "integer", "description": "Fork count"},
                                "language": {"type": "string", "description": "Primary language"},
                                "updated_at": {"type": "string", "description": "Last update date"},
                            },
                            "required": ["full_name", "url", "stars"],
                        },
                    },
                    "total_results": {"type": "integer", "description": "Number of repos found"},
                },
                "required": ["repositories", "total_results"],
            },
        ),
        Tool(
            name="get_github_readme",
            title="GitHub README",
            description="""Get README content from a GitHub repository. Useful for understanding what a project does, its installation instructions, and usage examples.

## Features
- Fetches README.md from any public repository
- Returns raw markdown content
- Works with main/master branches

## Examples

### Get OpenAI GPT-4 README
```json
{"repo": "openai/gpt-4"}
```

### Get popular ML framework
```json
{"repo": "pytorch/pytorch"}
```

### Get MCP server example
```json
{"repo": "anthropics/claude-code"}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository in format 'owner/repo' (e.g., 'openai/gpt-4')",
                    },
                },
                "required": ["repo"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository name (owner/repo)"},
                    "content": {
                        "type": "string",
                        "description": "README content in markdown format",
                    },
                    "error": {"type": "string", "description": "Error message if README not found"},
                },
                "required": ["repo"],
            },
        ),
        Tool(
            name="search_reddit",
            title="Reddit Search",
            description="""Search Reddit posts and discussions. Returns posts with titles, scores, comments count, and content. Can search specific subreddits or all of Reddit.

## Popular Subreddits
- **LocalLLaMA** - Local LLM discussions
- **MachineLearning** - ML research and news
- **programming** - General programming
- **Python** - Python language
- **learnprogramming** - Learning to code

## Examples

### Search all of Reddit
```json
{"query": "best programming language 2024"}
```

### Search specific subreddit
```json
{"query": "Claude API", "subreddit": "LocalLLaMA", "limit": 5}
```

### Recent posts only
```json
{"query": "GPT-4 vs Claude", "time_filter": "week", "limit": 10}
```""",
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
                        "enum": ["hour", "day", "week", "month", "year", "all"],
                        "default": "all",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "posts": {
                        "type": "array",
                        "description": "List of Reddit posts",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Post title"},
                                "subreddit": {"type": "string", "description": "Subreddit name"},
                                "author": {"type": "string", "description": "Post author"},
                                "score": {"type": "integer", "description": "Post score (upvotes)"},
                                "num_comments": {
                                    "type": "integer",
                                    "description": "Number of comments",
                                },
                                "url": {"type": "string", "description": "Post URL"},
                                "text": {"type": "string", "description": "Post text content"},
                                "created_utc": {
                                    "type": "string",
                                    "description": "Creation timestamp",
                                },
                            },
                            "required": ["title", "subreddit", "url", "score"],
                        },
                    },
                    "total_results": {"type": "integer", "description": "Number of posts found"},
                },
                "required": ["posts", "total_results"],
            },
        ),
        Tool(
            name="get_reddit_comments",
            title="Reddit Comments",
            description="""Get comments from a specific Reddit post. Useful for reading discussions, community insights, and detailed opinions.

## Examples

### Get comments from a post
```json
{"url": "https://www.reddit.com/r/LocalLLaMA/comments/abc123/title"}
```

### Get more comments
```json
{"url": "https://reddit.com/r/Python/comments/xyz789/discussion", "limit": 20}
```

### Get top comments only
```json
{"url": "https://reddit.com/r/MachineLearning/comments/def456/paper", "limit": 5}
```""",
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
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "comments": {
                        "type": "array",
                        "description": "List of comments",
                        "items": {
                            "type": "object",
                            "properties": {
                                "author": {"type": "string", "description": "Comment author"},
                                "body": {"type": "string", "description": "Comment text"},
                                "score": {
                                    "type": "integer",
                                    "description": "Comment score (upvotes)",
                                },
                                "created_utc": {
                                    "type": "string",
                                    "description": "Creation timestamp",
                                },
                            },
                            "required": ["author", "body", "score"],
                        },
                    },
                    "post_url": {"type": "string", "description": "Original post URL"},
                    "total_comments": {
                        "type": "integer",
                        "description": "Number of comments returned",
                    },
                },
                "required": ["comments", "total_comments"],
            },
        ),
        Tool(
            name="search_pubmed",
            title="PubMed Search",
            description="""Search medical and scientific publications on PubMed. Returns peer-reviewed research articles with abstracts, authors, journal info, and DOIs.

## Features
- Access to 35+ million biomedical citations
- Peer-reviewed medical and life sciences literature
- Full abstracts and metadata
- DOI and PubMed ID for each article

## Search Tips
- Use MeSH terms for better results
- Combine terms with AND/OR
- Use quotation marks for exact phrases

## Examples

### Search for medical AI research
```json
{"query": "machine learning in medicine"}
```

### Find COVID-19 vaccine studies
```json
{"query": "COVID-19 vaccine efficacy", "max_results": 20}
```

### Search specific condition
```json
{"query": "type 2 diabetes treatment guidelines", "max_results": 5}
```""",
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
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "articles": {
                        "type": "array",
                        "description": "List of PubMed articles",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Article title"},
                                "authors": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of authors",
                                },
                                "abstract": {"type": "string", "description": "Article abstract"},
                                "journal": {"type": "string", "description": "Journal name"},
                                "pub_date": {"type": "string", "description": "Publication date"},
                                "pmid": {"type": "string", "description": "PubMed ID"},
                                "doi": {
                                    "type": "string",
                                    "description": "Digital Object Identifier",
                                },
                                "url": {"type": "string", "description": "PubMed URL"},
                            },
                            "required": ["title", "pmid", "url"],
                        },
                    },
                    "total_results": {"type": "integer", "description": "Number of articles found"},
                },
                "required": ["articles", "total_results"],
            },
        ),
        Tool(
            name="search_gdelt",
            title="GDELT News Search",
            description="""Search news articles using GDELT Global Database. Returns recent news from around the world with metadata about sources and publication dates.

## Features
- Real-time global news monitoring
- Coverage of 100+ languages
- News from 240+ countries
- Source domain and country metadata

## Timespan Options
- **1d** - Last 24 hours (default)
- **7d** - Last week
- **1m** - Last month

## Examples

### Search recent news
```json
{"query": "artificial intelligence"}
```

### Search last week's news
```json
{"query": "climate change", "timespan": "7d", "max_results": 20}
```

### Search specific event
```json
{"query": "tech layoffs 2024", "timespan": "1m", "max_results": 15}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (news keyword)"},
                    "timespan": {
                        "type": "string",
                        "description": "Time span: '1d', '7d', '1m' (default: '1d')",
                        "enum": ["1d", "7d", "1m"],
                        "default": "1d",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "articles": {
                        "type": "array",
                        "description": "List of news articles",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Article title"},
                                "url": {"type": "string", "description": "Article URL"},
                                "domain": {"type": "string", "description": "Source domain"},
                                "country": {"type": "string", "description": "Source country code"},
                                "date": {"type": "string", "description": "Publication date"},
                            },
                            "required": ["title", "url", "domain"],
                        },
                    },
                    "total_results": {"type": "integer", "description": "Number of articles found"},
                },
                "required": ["articles", "total_results"],
            },
        ),
        Tool(
            name="get_wikipedia_content",
            title="Wikipedia Full Content",
            description="""Get full Wikipedia article content with sections and related articles. More detailed than get_wikipedia_summary.

## Examples

### Get full article
```json
{"title": "Artificial neural network"}
```

### Get article in another language
```json
{"title": "Deep learning", "lang": "de"}
```

### Get technical article
```json
{"title": "Transformer (machine learning model)"}
```""",
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
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Article title"},
                    "url": {"type": "string", "description": "Wikipedia URL"},
                    "sections": {
                        "type": "array",
                        "description": "Article sections with content",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Section title"},
                                "content": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Section paragraphs",
                                },
                            },
                            "required": ["title", "content"],
                        },
                    },
                    "related": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Related article titles",
                    },
                },
                "required": ["title", "url", "sections"],
            },
        ),
        Tool(
            name="assess_source_credibility",
            title="Source Credibility",
            description="""Assess credibility of a web source using Bayesian analysis. Evaluates 30+ signals including domain age (via WHOIS), content quality, citation network, and metadata. Returns credibility score (0-1) with confidence intervals and recommendation.

## Features
- Bayesian scoring with uncertainty quantification
- Domain age checking via WHOIS
- Content quality analysis
- Category-based prior probabilities
- No API keys required

## Analyzed Signals
- Domain reputation and age
- HTTPS security
- Content formality and neutrality
- Evidence density and references
- Peer review status

## Examples

### Assess a URL
```json
{"url": "https://arxiv.org/abs/2301.00001"}
```

### Assess with title
```json
{"url": "https://example.com/article", "title": "Research on AI Safety"}
```

### Full assessment with metadata
```json
{"url": "https://nature.com/article", "title": "Study Title", "metadata": {"year": 2024, "is_peer_reviewed": true, "citations": 50}}
```""",
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
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Assessed URL"},
                    "domain": {"type": "string", "description": "Domain name"},
                    "category": {
                        "type": "string",
                        "description": "Domain category (academic, news, blog, etc.)",
                    },
                    "credibility_score": {"type": "number", "description": "Score from 0 to 1"},
                    "confidence_interval": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "95% confidence interval [lower, upper]",
                    },
                    "uncertainty": {"type": "number", "description": "Uncertainty estimate"},
                    "prior": {"type": "number", "description": "Category-based prior probability"},
                    "likelihood_ratio": {"type": "number", "description": "Evidence strength"},
                    "pagerank": {"type": "number", "description": "PageRank score"},
                    "signals": {
                        "type": "object",
                        "description": "Individual signal scores",
                    },
                    "recommendation": {
                        "type": "string",
                        "description": "Human-readable recommendation",
                    },
                },
                "required": ["url", "domain", "credibility_score", "recommendation"],
            },
        ),
        Tool(
            name="summarize_text",
            title="Text Summarizer",
            description="""Summarize long text using multiple strategies (TF-IDF extractive, keyword-based, or heuristic). Fast, works without API keys. Best for articles, papers, documents.

## Strategies
- **auto** - Automatically selects best available method (default)
- **extractive_tfidf** - Uses TF-IDF scoring to select key sentences (requires NLTK)
- **extractive_keyword** - Prioritizes sentences with named entities
- **heuristic** - Simple first/middle/last sentences (fastest, always available)

## Features
- No API keys required
- Works offline
- Maintains original sentence structure
- Configurable compression ratio

## Examples

### Auto summarize
```json
{"text": "Long article text here..."}
```

### Summarize with specific strategy
```json
{"text": "Article content...", "strategy": "extractive_tfidf"}
```

### Summarize with custom compression
```json
{"text": "Document text...", "compression_ratio": 0.2}
```""",
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
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Generated summary text"},
                    "method": {"type": "string", "description": "Method used for summarization"},
                    "stats": {
                        "type": "object",
                        "description": "Statistics about the summarization",
                        "properties": {
                            "sentences_original": {"type": "integer"},
                            "sentences_summary": {"type": "integer"},
                            "chars_original": {"type": "integer"},
                            "chars_summary": {"type": "integer"},
                            "compression_ratio": {"type": "string"},
                        },
                    },
                },
                "required": ["summary", "method"],
            },
        ),
        Tool(
            name="read_file",
            title="File Reader",
            description="""Read content from a file. Supports text files, PDFs, Word documents (.docx), Excel files (.xlsx/.xls), and images (JPG/PNG/GIF/BMP/WebP).

## Features
- Reads text files with UTF-8 encoding
- Extracts text from PDF documents
- Parses Word documents (.docx)
- Reads Excel spreadsheets (.xlsx/.xls)
- Analyzes images and returns metadata
- Maximum file size: 10MB

## Examples

### Read a text file
```json
{"path": "notes.txt"}
```

### Read a PDF document
```json
{"path": "report.pdf"}
```

### Read an Excel file
```json
{"path": "data.xlsx"}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read. Relative paths use data/files/ as base directory.",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Resolved file path"},
                    "content": {"type": "string", "description": "File content or extracted text"},
                    "size": {"type": "integer", "description": "File size in bytes"},
                    "exists": {"type": "boolean", "description": "Whether file exists"},
                    "error": {"type": "string", "description": "Error message if read failed"},
                },
                "required": ["path", "exists"],
            },
        ),
        Tool(
            name="write_file",
            title="File Writer",
            description="""Write content to a file. Creates the file if it doesn't exist, overwrites if it does.

## Features
- Creates parent directories if needed
- UTF-8 text encoding
- Maximum content size: 10MB
- Secure path handling (restricted to data/files/)

## Examples

### Write a text file
```json
{"path": "notes.txt", "content": "My notes here..."}
```

### Write JSON data
```json
{"path": "config.json", "content": "{\"key\": \"value\"}"}
```

### Write to subdirectory
```json
{"path": "reports/summary.txt", "content": "Report content..."}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write. Relative paths use data/files/ as base directory.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file (UTF-8 text).",
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Resolved file path"},
                    "message": {"type": "string", "description": "Success or error message"},
                    "size": {"type": "integer", "description": "File size in bytes after writing"},
                    "exists": {
                        "type": "boolean",
                        "description": "Whether file exists after operation",
                    },
                },
                "required": ["path", "message"],
            },
        ),
        Tool(
            name="append_file",
            title="File Appender",
            description="""Append content to an existing file. Creates the file if it doesn't exist.

## Features
- Appends to end of file
- Creates file if not exists
- UTF-8 text encoding
- Secure path handling (restricted to data/files/)

## Examples

### Append to log file
```json
{"path": "log.txt", "content": "New log entry\\n"}
```

### Append data to CSV
```json
{"path": "data.csv", "content": "value1,value2,value3\\n"}
```

### Append note
```json
{"path": "notes.txt", "content": "\\n--- New Note ---\\nContent here..."}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to append to. Relative paths use data/files/ as base directory.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to append to the file (UTF-8 text).",
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Resolved file path"},
                    "message": {"type": "string", "description": "Success or error message"},
                    "size": {
                        "type": "integer",
                        "description": "File size in bytes after appending",
                    },
                    "exists": {
                        "type": "boolean",
                        "description": "Whether file exists after operation",
                    },
                },
                "required": ["path", "message"],
            },
        ),
        Tool(
            name="list_files",
            title="Directory Listing",
            description="""List contents of a directory. Shows files and subdirectories with their sizes.

## Features
- Lists files and directories
- Shows file sizes
- Sorted alphabetically
- Returns structured data

## Examples

### List default directory
```json
{}
```

### List specific directory
```json
{"path": "reports"}
```

### List subdirectory
```json
{"path": "data/exports"}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to directory to list. Empty or omitted for default data/files/ directory.",
                        "default": "",
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Resolved directory path"},
                    "items": {
                        "type": "array",
                        "description": "List of files and directories",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "File or directory name"},
                                "type": {
                                    "type": "string",
                                    "enum": ["file", "directory"],
                                    "description": "Item type",
                                },
                                "size": {
                                    "type": "integer",
                                    "description": "File size in bytes (0 for directories)",
                                },
                            },
                            "required": ["name", "type"],
                        },
                    },
                    "count": {"type": "integer", "description": "Number of items in directory"},
                },
                "required": ["path", "items", "count"],
            },
        ),
        Tool(
            name="delete_file",
            title="File Deleter",
            description="""Delete a file. Only files within the data/files/ directory can be deleted for security.

## Features
- Secure deletion (restricted to data/files/)
- Validates file exists before deletion
- Returns confirmation message

## Security
- Cannot delete files outside data/files/
- Cannot delete directories
- Path traversal protection

## Examples

### Delete a file
```json
{"path": "old_notes.txt"}
```

### Delete file in subdirectory
```json
{"path": "temp/cache.json"}
```

### Delete generated report
```json
{"path": "reports/old_report.pdf"}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to delete.",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Resolved file path"},
                    "success": {
                        "type": "boolean",
                        "description": "Whether deletion was successful",
                    },
                    "message": {"type": "string", "description": "Success or error message"},
                },
                "required": ["path", "success", "message"],
            },
        ),
        Tool(
            name="calculate",
            title="Calculator",
            description="""Perform mathematical calculations safely. Supports arithmetic, trigonometry, logarithms, and more.

## Supported Operations
- **Arithmetic:** +, -, *, /, ** (power), % (modulo), // (floor division)
- **Trigonometry:** sin, cos, tan, asin, acos, atan, atan2
- **Hyperbolic:** sinh, cosh, tanh, asinh, acosh, atanh
- **Logarithms:** log (natural), log10, log2, exp
- **Other:** sqrt, abs, ceil, floor, round, factorial, gcd
- **Constants:** pi, e, tau

## Examples

### Basic arithmetic
```json
{"expression": "2 + 2 * 3"}
```

### Trigonometry
```json
{"expression": "sin(pi/2) + cos(0)"}
```

### Complex calculation
```json
{"expression": "sqrt(16) + log10(100) ** 2"}
```""",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate",
                    },
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Original expression"},
                    "result": {"type": "number", "description": "Calculation result"},
                    "result_type": {
                        "type": "string",
                        "description": "Result type (int, float, complex)",
                    },
                    "formatted": {
                        "type": "string",
                        "description": "Human-readable formatted result",
                    },
                    "error": {
                        "type": "string",
                        "description": "Error message if calculation failed",
                    },
                },
                "required": ["expression"],
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

            # Build structured content for programmatic access
            structured_results = []
            for result in results:
                structured_result = {
                    "title": result.get("title", "No title"),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                }
                if result.get("preview"):
                    structured_result["preview"] = result.get("preview")
                structured_results.append(structured_result)

            structured_content = {
                "results": structured_results,
                "total_results": len(structured_results),
                "engine_used": result.get("engine", engine or "auto-fallback"),
            }

            # Build human-readable formatted text
            formatted_results = "# Search Results\n\n"
            for i, result in enumerate(results, 1):
                formatted_results += f"## {i}. {result.get('title', 'No title')}\n"
                formatted_results += f"**URL:** {result.get('url', 'No URL')}\n"
                formatted_results += f"**Snippet:** {result.get('snippet', 'No snippet')}\n\n"

                if result.get("preview"):
                    formatted_results += f"**Preview:** {result.get('preview')}\n\n"

            # Return both text content and structured JSON
            # Note: structuredContent is included as metadata in the text response
            formatted_results += (
                f"\n---\n<!-- structuredContent: {json.dumps(structured_content)} -->"
            )

            return [TextContent(type="text", text=formatted_results)]

        elif name == "search_maps":
            query = arguments.get("query")
            limit = arguments.get("limit", 5)
            country_codes = arguments.get("country_codes")
            no_cache = arguments.get("no_cache", False)
            if not query:
                return [TextContent(type="text", text="Error: query parameter is required")]

            logger.info(f"Searching maps for: {query}")
            results = await search_maps(
                query,
                limit=limit,
                country_codes=country_codes,
                no_cache=no_cache,
            )
            if not results:
                return [TextContent(type="text", text="No results found")]

            # Build structured content for programmatic access
            structured_places = []
            for result in results:
                structured_place = {
                    "name": result.get("title", "Unknown"),
                    "address": result.get("title", ""),
                    "latitude": float(result.get("lat", 0)),
                    "longitude": float(result.get("lon", 0)),
                    "osm_url": result.get("url", ""),
                }
                structured_places.append(structured_place)

            structured_content = {
                "places": structured_places,
                "total_results": len(structured_places),
            }

            # Build human-readable formatted text
            formatted_output = "# Maps Results\n\n"
            for i, result in enumerate(results, 1):
                formatted_output += f"## {i}. {result.get('title','No title')}\n"
                formatted_output += f"**Coordinates:** {result.get('lat')}, {result.get('lon')}\n"
                if result.get("url"):
                    formatted_output += f"**OSM URL:** {result.get('url')}\n"
                formatted_output += "\n"

            # Append structured content
            formatted_output += (
                f"\n---\n<!-- structuredContent: {json.dumps(structured_content)} -->"
            )

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

            # Build structured content
            structured_papers = []
            for paper in results:
                structured_paper = {
                    "title": paper.get("title", "No title"),
                    "authors": paper.get("authors", []),
                    "abstract": paper.get("abstract", ""),
                    "arxiv_id": paper.get("id", ""),
                    "pdf_url": paper.get("pdf_url", ""),
                    "published": paper.get("published", ""),
                    "category": paper.get("primary_category", ""),
                }
                structured_papers.append(structured_paper)

            structured_content = {
                "papers": structured_papers,
                "total_results": len(structured_papers),
            }

            # Build human-readable output
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

            # Append structured content
            formatted_results += (
                f"\n---\n<!-- structuredContent: {json.dumps(structured_content)} -->"
            )

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

            # Build structured content
            structured_repos = []
            for repo in results:
                structured_repo = {
                    "full_name": repo.get("full_name", ""),
                    "description": repo.get("description", ""),
                    "url": repo.get("url", ""),
                    "stars": repo.get("stars", 0),
                    "forks": repo.get("forks", 0),
                    "language": repo.get("language", ""),
                    "updated_at": repo.get("updated_at", ""),
                }
                structured_repos.append(structured_repo)

            structured_content = {
                "repositories": structured_repos,
                "total_results": len(structured_repos),
            }

            # Build human-readable output
            formatted_results = "# GitHub Search Results\n\n"
            for i, repo in enumerate(results, 1):
                formatted_results += f"## {i}. {repo.get('full_name', 'No name')}\n"
                formatted_results += (
                    f"**Description:** {repo.get('description', 'No description')}\n"
                )
                formatted_results += f"**URL:** {repo.get('url', 'N/A')}\n"
                formatted_results += (
                    f"**Stars:** {repo.get('stars', 0)} | **Forks:** {repo.get('forks', 0)}\n"
                )
                formatted_results += f"**Language:** {repo.get('language', 'N/A')}\n"
                formatted_results += f"**Updated:** {repo.get('updated_at', 'N/A')}\n\n"

            # Append structured content
            formatted_results += (
                f"\n---\n<!-- structuredContent: {json.dumps(structured_content)} -->"
            )

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

        elif name == "read_file":
            path = arguments.get("path")

            if not path:
                return [TextContent(type="text", text="Error: path parameter is required")]

            logger.info(f"Reading file: {path}")
            result = await file_manager.read_file(path)

            # Format output
            formatted_output = f"# File: {result['path']}\n\n"
            formatted_output += f"**Size:** {result['size']} bytes\n"
            formatted_output += f"**Exists:** {result['exists']}\n\n"

            if result["exists"]:
                formatted_output += "## Content\n\n"
                formatted_output += f"```\n{result['content']}\n```\n"
            else:
                formatted_output += result["content"]

            return [TextContent(type="text", text=formatted_output)]

        elif name == "write_file":
            path = arguments.get("path")
            content = arguments.get("content")

            if not path:
                return [TextContent(type="text", text="Error: path parameter is required")]
            if not content:
                return [TextContent(type="text", text="Error: content parameter is required")]

            logger.info(f"Writing file: {path}")
            result = await file_manager.write_file(path, content, append=False)

            # Format output
            formatted_output = "# File Write Result\n\n"
            formatted_output += f"**Path:** {result['path']}\n"
            formatted_output += f"**Size:** {result['size']} bytes\n"
            formatted_output += f"**Status:** {result['message']}\n"

            return [TextContent(type="text", text=formatted_output)]

        elif name == "append_file":
            path = arguments.get("path")
            content = arguments.get("content")

            if not path:
                return [TextContent(type="text", text="Error: path parameter is required")]
            if not content:
                return [TextContent(type="text", text="Error: content parameter is required")]

            logger.info(f"Appending to file: {path}")
            result = await file_manager.write_file(path, content, append=True)

            # Format output
            formatted_output = "# File Append Result\n\n"
            formatted_output += f"**Path:** {result['path']}\n"
            formatted_output += f"**Size:** {result['size']} bytes\n"
            formatted_output += f"**Status:** {result['message']}\n"

            return [TextContent(type="text", text=formatted_output)]

        elif name == "list_files":
            path = arguments.get("path", "")

            logger.info(f"Listing directory: {path or 'default'}")
            result = await file_manager.list_directory(path)

            # Format output
            formatted_output = f"# Directory: {result['path']}\n\n"
            formatted_output += f"**Total items:** {result['count']}\n\n"

            if result["items"]:
                formatted_output += "## Contents\n\n"
                for item in result["items"]:
                    icon = "📁" if item["type"] == "directory" else "📄"
                    size_str = ""
                    if item["type"] == "file":
                        size = item["size"]
                        if size < 1024:
                            size_str = f" ({size} bytes)"
                        elif size < 1024 * 1024:
                            size_str = f" ({size // 1024} KB)"
                        else:
                            size_str = f" ({size // 1024 // 1024} MB)"

                    formatted_output += f"- {icon} **{item['name']}**{size_str}\n"
            else:
                formatted_output += "*Directory is empty*\n"

            return [TextContent(type="text", text=formatted_output)]

        elif name == "delete_file":
            path = arguments.get("path")

            if not path:
                return [TextContent(type="text", text="Error: path parameter is required")]

            logger.info(f"Deleting file: {path}")
            result = await file_manager.delete_file(path)

            # Format output
            formatted_output = "# File Deletion Result\n\n"
            formatted_output += f"**Path:** {result['path']}\n"
            formatted_output += f"**Success:** {result['success']}\n"
            formatted_output += f"**Message:** {result['message']}\n"

            return [TextContent(type="text", text=formatted_output)]

        elif name == "calculate":
            expression = arguments.get("expression")

            if not expression:
                return [TextContent(type="text", text="Error: expression parameter is required")]

            logger.info(f"Calculating: {expression}")
            result = await calculator.calculate_async(expression)

            # Build structured content
            if result["success"]:
                structured_content = {
                    "expression": result["expression"],
                    "result": result["result"],
                    "result_type": result["type"],
                    "formatted": result["formatted"],
                }

                formatted_output = "# Calculation Result\n\n"
                formatted_output += f"**Expression:** `{result['expression']}`\n\n"
                formatted_output += f"**Result:** `{result['result']}`\n\n"
                formatted_output += f"**Type:** {result['type']}\n\n"
                formatted_output += "---\n\n"
                formatted_output += f"```\n{result['formatted']}\n```\n"
            else:
                structured_content = {
                    "expression": result["expression"],
                    "error": result.get("error", "Unknown error"),
                }

                formatted_output = "# Calculation Error\n\n"
                formatted_output += f"**Expression:** `{result['expression']}`\n\n"
                formatted_output += f"**Error:** {result['error']}\n"

            # Append structured content
            formatted_output += (
                f"\n---\n<!-- structuredContent: {json.dumps(structured_content)} -->"
            )

            return [TextContent(type="text", text=formatted_output)]

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
