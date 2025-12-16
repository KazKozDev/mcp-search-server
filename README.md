

<img width="304" alt="log" src="https://github.com/user-attachments/assets/d831a711-9ddd-406a-b984-46e5693959c8" />

# MCP Search Server
<!-- mcp-name: io.github.KazKozDev/search -->

mcp-name: io.github.KazKozDev/search

[![PyPI version](https://badge.fury.io/py/mcp-search-server.svg)](https://badge.fury.io/py/mcp-search-server)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/KazKozDev/mcp-search-server/actions/workflows/ci.yml/badge.svg)](https://github.com/KazKozDev/mcp-search-server/actions/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

MCP (Model Context Protocol) server for web search, content extraction, and PDF parsing.

**🔓 No API keys required! No registration needed!** All tools work out of the box using free public APIs.

**🌍 Context-Aware AI**: Built-in tools for real-time datetime and geolocation detection give LLMs the ability to understand "here and now" - enabling timezone-aware responses, location-based content, and time-sensitive information without manual configuration.

## Features

- **DateTime Tool**: Get current date and time with timezone awareness - lets LLMs know what time it is right now
- **Geolocation**: IP-based location detection with timezone, coordinates, and ISP info - helps LLMs understand where users are located
- **Web Search**: Search the web using DuckDuckGo
- **Wikipedia Search**: Search and retrieve Wikipedia articles
- **Web Content Extraction**: Extract clean text from web pages using multiple parsing methods
- **PDF Parsing**: Extract text from PDF files
- **Multi-Source Search**: Parallel search across multiple sources

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Install from PyPI (recommended)

```bash
pip install mcp-search-server
```

### Install from source

```bash
git clone https://github.com/KazKozDev/mcp-search-server.git
cd mcp-search-server
pip install -e .
```

## Usage

### Running the server

The server can be run directly:

```bash
python -m mcp_search_server.server
```

Or using the installed script:

```bash
mcp-search-server
```

### Configuration for Claude Desktop

Add this to your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "search": {
      "command": "python",
      "args": [
        "-m",
        "mcp_search_server.server"
      ]
    }
  }
}
```

Or if you installed it as a package:

```json
{
  "mcpServers": {
    "search": {
      "command": "mcp-search-server"
    }
  }
}
```

### Configuration for other MCP clients

The server uses stdio transport, so it can be integrated with any MCP client that supports stdio.

## Available Tools

### 1. search_web

Search the web using DuckDuckGo with optional time filtering.

**Parameters:**
- `query` (string, required): The search query
- `limit` (integer, optional): Maximum number of results (default: 10)
- `timelimit` (string, optional): Filter by time - `'d'` (past day), `'w'` (past week), `'m'` (past month), `'y'` (past year), `null` (all time, default)

**Examples:**
```json
{
  "query": "Python async programming",
  "limit": 5
}
```

Search for recent news (past day):
```json
{
  "query": "latest AI developments",
  "limit": 10,
  "timelimit": "d"
}
```

### 2. search_wikipedia

Search Wikipedia for articles.

**Parameters:**
- `query` (string, required): The search query
- `limit` (integer, optional): Maximum number of results (default: 5)

**Example:**
```json
{
  "query": "Machine Learning",
  "limit": 3
}
```

### 3. get_wikipedia_summary

Get a summary of a specific Wikipedia article.

**Parameters:**
- `title` (string, required): The Wikipedia article title

**Example:**
```json
{
  "title": "Artificial Intelligence"
}
```

### 4. extract_webpage_content

Extract clean text content from a web page.

**Parameters:**
- `url` (string, required): The URL to extract content from

**Example:**
```json
{
  "url": "https://example.com/article"
}
```

**Features:**
- Multiple parsing methods (Readability, Newspaper3k, BeautifulSoup)
- Automatic fallback if one method fails
- Cleans boilerplate content (ads, navigation, etc.)

### 5. parse_pdf

Extract text from PDF files.

**Parameters:**
- `url` (string, required): The URL of the PDF file
- `max_chars` (integer, optional): Maximum characters to extract (default: 50000)

**Example:**
```json
{
  "url": "https://example.com/document.pdf",
  "max_chars": 100000
}
```

**Features:**
- Supports PyPDF2 and pdfplumber
- Automatic library selection

### 6. search_multi

Search multiple sources in parallel (web + Wikipedia).

**Parameters:**
- `query` (string, required): The search query
- `web_limit` (integer, optional): Max web results (default: 5)
- `wiki_limit` (integer, optional): Max Wikipedia results (default: 3)

**Example:**
```json
{
  "query": "Python programming",
  "web_limit": 5,
  "wiki_limit": 3
}
```

**Features:**
- Runs searches in parallel for faster results
- Combines results from multiple sources
- Returns structured output with clear source attribution

### 7. get_current_datetime

Get current date and time with timezone information. Essential for time-aware AI responses.

**Parameters:**
- `timezone` (string, optional): Timezone name (default: "UTC")
- `include_details` (boolean, optional): Include additional details (default: true)

**Example:**
```json
{
  "timezone": "Europe/Moscow",
  "include_details": true
}
```

**Returns:**
- ISO datetime string
- Date and time components
- Day of week, week number
- Multiple formatted representations
- Unix timestamp

**Features:**
- Supports 596+ timezones worldwide
- Automatic timezone conversion
- Detailed formatting options
- Graceful error handling for invalid timezones

### 8. list_timezones

List available timezones by region.

**Parameters:**
- `region` (string, optional): Region filter - "all", "Europe", "America", "Asia", "Africa", "Australia" (default: "all")

**Example:**
```json
{
  "region": "Europe"
}
```

**Features:**
- Lists all available timezone names
- Filter by continent/region
- Useful for discovering correct timezone names

### 9. get_location_by_ip

Get geolocation information based on IP address. Returns country, city, timezone, coordinates, ISP, and more.

**Parameters:**
- `ip_address` (string, optional): IP address to lookup (e.g., "8.8.8.8"). If not provided, detects the server's public IP location.

**Example:**
```json
{
  "ip_address": "8.8.8.8"
}
```

**Returns:**
- IP address
- Country, region, city, ZIP code
- Timezone (can be used with get_current_datetime!)
- Latitude and longitude coordinates
- ISP and organization information
- AS number

**Features:**
- Free API, no API key required
- Automatic timezone detection for location-aware responses
- Works with both IPv4 and IPv6
- Graceful error handling for invalid/private IPs
- Perfect companion to datetime tool for automatic timezone detection

**Use Cases:**
- Auto-detect user's timezone for time-aware responses
- Location-based content customization
- Network diagnostics and IP analysis
- Geographic data for analytics

## Development

### Install development dependencies

```bash
pip install -e ".[dev]"
```

### Running tests

```bash
pytest
```

### Code formatting

```bash
black src/
```

### Linting

```bash
ruff check src/
```

## Architecture

### Tools

- **DuckDuckGo Search** ([tools/duckduckgo.py](src/mcp_search_server/tools/duckduckgo.py))
  - Async web scraping from DuckDuckGo HTML and Lite versions
  - Result caching (24 hours)
  - Retry logic with backoff

- **Wikipedia** ([tools/wikipedia.py](src/mcp_search_server/tools/wikipedia.py))
  - Wikipedia API integration
  - Article search and summary retrieval
  - HTML cleaning

- **Link Parser** ([tools/link_parser.py](src/mcp_search_server/tools/link_parser.py))
  - Multiple parsing methods (Readability, Newspaper3k, BeautifulSoup)
  - Early exit optimization
  - Content cleaning

- **PDF Parser** ([tools/pdf_parser.py](src/mcp_search_server/tools/pdf_parser.py))
  - PyPDF2 and pdfplumber support
  - Automatic library selection
  - Page-by-page extraction with limits

## Caching

The server uses local caching for search results:

- **Location**: `~/.mcp-search-cache/`
- **TTL**: 24 hours
- **Format**: JSON

## Troubleshooting

### PDF parsing not working

Install one of the PDF libraries:

```bash
pip install PyPDF2
# or
pip install pdfplumber
```

### Web content extraction fails

The server tries multiple methods automatically:
1. Readability (best for articles)
2. Newspaper3k (good for news sites)
3. BeautifulSoup (fallback for all sites)

If all methods fail, check:
- The URL is accessible
- The site doesn't block automated access
- Your internet connection

### Wikipedia search returns no results

- Check your internet connection
- Try a different search term
- The Wikipedia API might be temporarily unavailable

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
