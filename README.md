
<p align="center">
  <img width="304" alt="logo" src="https://github.com/user-attachments/assets/d831a711-9ddd-406a-b984-46e5693959c8" />
</p>

# MCP Search Server

[![PyPI version](https://img.shields.io/pypi/v/mcp-search-server.svg)](https://pypi.org/project/mcp-search-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/KazKozDev/mcp-search-server/actions/workflows/ci.yml/badge.svg)](https://github.com/KazKozDev/mcp-search-server/actions/workflows/ci.yml)

MCP server providing **24 tools** for web search, content extraction, and data processing. **No API keys required.**

## Installation

```bash
pip install mcp-search-server
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "search": {
      "command": "mcp-search-server"
    }
  }
}
```

## Available Tools (24)

### Web Search & Content

<details>
<summary><b>search_web</b> - Multi-engine web search with smart fallback</summary>

Search the web using DuckDuckGo, Brave, Startpage, or Qwant with automatic fallback if one engine fails.

**Parameters:**
- `query` (required): Search query
- `limit`: Max results (default: 10)
- `mode`: `"web"` or `"news"`
- `timelimit`: `"d"` (day), `"w"` (week), `"m"` (month), `"y"` (year)
- `engine`: `"duckduckgo"`, `"brave"`, `"startpage"`, `"qwant"` (default: auto)

**Example:**
```json
{"query": "Python async programming", "limit": 5, "mode": "news"}
```
</details>

<details>
<summary><b>search_maps</b> - Location and places search</summary>

Search for places, addresses, and locations with geographic coordinates.

**Parameters:**
- `query` (required): Place or address to search
- `limit`: Max results (default: 5)

**Example:**
```json
{"query": "coffee shops near Times Square NYC", "limit": 3}
```
</details>

<details>
<summary><b>extract_webpage_content</b> - Extract clean text from web pages</summary>

Extract readable content from any webpage, removing ads, navigation, and boilerplate. Uses multiple parsing methods with automatic fallback.

**Parameters:**
- `url` (required): URL to extract content from

**Example:**
```json
{"url": "https://example.com/article"}
```
</details>

<details>
<summary><b>parse_pdf</b> - Extract text from PDF files</summary>

Download and extract text content from PDF documents.

**Parameters:**
- `url` (required): PDF URL
- `max_chars`: Maximum characters to extract (default: 50000)

**Example:**
```json
{"url": "https://arxiv.org/pdf/2303.08774.pdf", "max_chars": 100000}
```
</details>

### Wikipedia

<details>
<summary><b>search_wikipedia</b> - Search Wikipedia articles</summary>

Search Wikipedia for articles matching a query.

**Parameters:**
- `query` (required): Search query
- `limit`: Max results (default: 5)

**Example:**
```json
{"query": "machine learning", "limit": 3}
```
</details>

<details>
<summary><b>get_wikipedia_summary</b> - Get article summary</summary>

Get a concise summary of a Wikipedia article.

**Parameters:**
- `title` (required): Article title

**Example:**
```json
{"title": "Artificial Intelligence"}
```
</details>

<details>
<summary><b>get_wikipedia_content</b> - Get full article content</summary>

Get the complete content of a Wikipedia article with all sections.

**Parameters:**
- `title` (required): Article title
- `lang`: Language code (default: "en")

**Example:**
```json
{"title": "Quantum computing", "lang": "en"}
```
</details>

### Academic & Research

<details>
<summary><b>search_arxiv</b> - Search arXiv papers</summary>

Search arXiv for academic papers in physics, mathematics, computer science, and more.

**Parameters:**
- `query` (required): Search query
- `max_results`: Max results (default: 10)
- `category`: arXiv category (e.g., "cs.AI", "physics")

**Example:**
```json
{"query": "transformer neural networks", "max_results": 5, "category": "cs.AI"}
```
</details>

<details>
<summary><b>search_pubmed</b> - Search medical/biomedical papers</summary>

Search PubMed for biomedical and life science research papers.

**Parameters:**
- `query` (required): Search query
- `max_results`: Max results (default: 10)

**Example:**
```json
{"query": "CRISPR gene therapy", "max_results": 5}
```
</details>

<details>
<summary><b>search_gdelt</b> - Search global news (GDELT)</summary>

Search the GDELT database for global news articles and events.

**Parameters:**
- `query` (required): Search query
- `timespan`: `"1d"`, `"7d"`, or `"1m"` (default: "1d")
- `max_results`: Max results (default: 10)

**Example:**
```json
{"query": "climate summit", "timespan": "7d", "max_results": 5}
```
</details>

### GitHub

<details>
<summary><b>search_github</b> - Search GitHub repositories</summary>

Search GitHub for repositories by keywords, with sorting options.

**Parameters:**
- `query` (required): Search query
- `max_results`: Max results (default: 5)
- `sort`: `"stars"`, `"forks"`, `"updated"` (default: "stars")

**Example:**
```json
{"query": "python web framework", "max_results": 10, "sort": "stars"}
```
</details>

<details>
<summary><b>get_github_readme</b> - Get repository README</summary>

Fetch the README file content from a GitHub repository.

**Parameters:**
- `repo` (required): Repository in "owner/repo" format

**Example:**
```json
{"repo": "langchain-ai/langchain"}
```
</details>

### Reddit

<details>
<summary><b>search_reddit</b> - Search Reddit posts</summary>

Search Reddit for posts across all subreddits or within a specific one.

**Parameters:**
- `query` (required): Search query
- `subreddit`: Specific subreddit (optional)
- `limit`: Max results (default: 10)
- `time_filter`: `"hour"`, `"day"`, `"week"`, `"month"`, `"year"`, `"all"`

**Example:**
```json
{"query": "best programming languages 2024", "subreddit": "programming", "limit": 5}
```
</details>

<details>
<summary><b>get_reddit_comments</b> - Get post comments</summary>

Fetch comments from a specific Reddit post.

**Parameters:**
- `url` (required): Reddit post URL
- `limit`: Max comments (default: 10)

**Example:**
```json
{"url": "https://www.reddit.com/r/Python/comments/abc123/post_title/", "limit": 20}
```
</details>

### Date, Time & Location

<details>
<summary><b>get_current_datetime</b> - Get current date/time with timezone</summary>

Get the current date and time for any timezone. Essential for time-aware AI responses.

**Parameters:**
- `timezone`: Timezone name (default: "UTC")
- `include_details`: Include additional info (default: true)

**Example:**
```json
{"timezone": "America/New_York", "include_details": true}
```

**Returns:** ISO datetime, date/time components, day of week, week number, Unix timestamp.
</details>

<details>
<summary><b>get_location_by_ip</b> - IP geolocation lookup</summary>

Get geographic location from an IP address: country, city, timezone, coordinates, ISP.

**Parameters:**
- `ip_address`: IP to lookup (optional, uses server IP if omitted)

**Example:**
```json
{"ip_address": "8.8.8.8"}
```

**Returns:** Country, region, city, ZIP, timezone, lat/lon, ISP, AS number.
</details>

### Analysis & Processing

<details>
<summary><b>assess_source_credibility</b> - Bayesian credibility scoring</summary>

Assess web source credibility using 30+ signals, domain age (WHOIS), and citation network analysis.

**Parameters:**
- `url` (required): URL to assess
- `title`: Document title (optional)
- `content`: Full text content (optional, improves accuracy)
- `metadata`: Additional metadata (year, authors, citations, doi, is_peer_reviewed)

**Example:**
```json
{"url": "https://arxiv.org/abs/2301.00234", "metadata": {"is_peer_reviewed": true}}
```

**Returns:** Credibility score (0-1), confidence interval, category, PageRank, 30+ signal scores.
</details>

<details>
<summary><b>summarize_text</b> - Multi-strategy text summarization</summary>

Summarize long text using TF-IDF, keyword extraction, or heuristic methods.

**Parameters:**
- `text` (required): Text to summarize
- `strategy`: `"auto"`, `"extractive_tfidf"`, `"extractive_keyword"`, `"heuristic"`
- `compression_ratio`: Target ratio 0.1-0.9 (default: 0.3)

**Example:**
```json
{"text": "Long article text here...", "strategy": "extractive_tfidf", "compression_ratio": 0.3}
```

**Returns:** Summary, method used, statistics (original/summary length, compression ratio).
</details>

<details>
<summary><b>calculate</b> - Safe mathematical calculator</summary>

Perform mathematical calculations with trigonometry, logarithms, and constants. Uses AST parsing for safety (no eval).

**Parameters:**
- `expression` (required): Math expression

**Supported:** `+`, `-`, `*`, `/`, `**`, `^`, `%`, `//`, `sqrt`, `sin`, `cos`, `tan`, `log`, `log10`, `exp`, `factorial`, `pi`, `e`, and more.

**Example:**
```json
{"expression": "sqrt(144) + sin(pi/2) * 10"}
```
</details>

### File Management

<details>
<summary><b>read_file</b> - Read file content</summary>

Read content from text, PDF, Word, Excel, or image files.

**Parameters:**
- `path` (required): File path (relative paths use `data/files/` as base)

**Example:**
```json
{"path": "notes.txt"}
```
</details>

<details>
<summary><b>write_file</b> - Write/create file</summary>

Write content to a file (creates if doesn't exist).

**Parameters:**
- `path` (required): File path
- `content` (required): Content to write

**Example:**
```json
{"path": "output.txt", "content": "Hello, World!"}
```
</details>

<details>
<summary><b>append_file</b> - Append to file</summary>

Append content to an existing file.

**Parameters:**
- `path` (required): File path
- `content` (required): Content to append

**Example:**
```json
{"path": "log.txt", "content": "\nNew log entry"}
```
</details>

<details>
<summary><b>list_files</b> - List directory contents</summary>

List files and directories with sizes and types.

**Parameters:**
- `path`: Directory path (default: `data/files/`)

**Example:**
```json
{"path": ""}
```
</details>

<details>
<summary><b>delete_file</b> - Delete file</summary>

Delete a file (restricted to `data/files/` for security).

**Parameters:**
- `path` (required): File path to delete

**Example:**
```json
{"path": "temp.txt"}
```
</details>

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/

# Lint
ruff check src/
```

## License

MIT
