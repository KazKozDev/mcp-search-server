
<p align="center">
  <img width="304" alt="logo" src="https://github.com/user-attachments/assets/d831a711-9ddd-406a-b984-46e5693959c8" />
</p>

# MCP Search Server

[![PyPI version](https://img.shields.io/pypi/v/mcp-search-server.svg)](https://pypi.org/project/mcp-search-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/KazKozDev/mcp-search-server/actions/workflows/ci.yml/badge.svg)](https://github.com/KazKozDev/mcp-search-server/actions/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

MCP server providing **24 tools** for web search, content extraction, and data processing. **No API keys required.**

## Installation

### From PyPI (recommended)

```bash
pip install mcp-search-server
```

### From source

```bash
git clone https://github.com/KazKozDev/mcp-search-server.git
cd mcp-search-server
pip install -e .
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

**Why LLMs need this:** LLMs have a knowledge cutoff date and cannot access current information. This tool gives them real-time access to the web, enabling answers about recent events, current prices, latest news, and up-to-date documentation.

**What it does:** Searches the web using DuckDuckGo, Brave, Startpage, or Qwant with automatic fallback if one engine fails. Supports web and news modes with time filtering.

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

**Why LLMs need this:** LLMs cannot look up real addresses, business locations, or geographic data. This tool enables location-based queries like finding nearby businesses, getting addresses, and working with geographic coordinates.

**What it does:** Searches for places, addresses, and locations with geographic coordinates. Returns structured location data including names, addresses, and coordinates.

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

**Why LLMs need this:** Raw HTML is cluttered with navigation, ads, and scripts. LLMs need clean, readable text to understand and summarize web content effectively. This tool extracts just the main content.

**What it does:** Extracts readable content from any webpage, removing ads, navigation, and boilerplate. Uses multiple parsing methods (Readability, Newspaper3k, BeautifulSoup) with automatic fallback.

**Parameters:**
- `url` (required): URL to extract content from

**Example:**
```json
{"url": "https://example.com/article"}
```
</details>

<details>
<summary><b>parse_pdf</b> - Extract text from PDF files</summary>

**Why LLMs need this:** PDFs are a common format for research papers, reports, and documentation, but LLMs cannot read binary files directly. This tool converts PDF content to text for analysis.

**What it does:** Downloads and extracts text content from PDF documents using PyPDF2 or pdfplumber with automatic library selection.

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

**Why LLMs need this:** Wikipedia is a reliable, structured knowledge base. While LLMs have some Wikipedia knowledge from training, this tool provides access to the latest content and helps find specific articles on any topic.

**What it does:** Searches Wikipedia for articles matching a query. Returns article titles, snippets, and URLs.

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

**Why LLMs need this:** Quick factual lookups need concise, authoritative information. Wikipedia summaries provide verified facts without the overhead of full articles, perfect for answering specific questions.

**What it does:** Gets a concise summary of a Wikipedia article - the introductory paragraphs that define the topic.

**Parameters:**
- `title` (required): Article title

**Example:**
```json
{"title": "Artificial Intelligence"}
```
</details>

<details>
<summary><b>get_wikipedia_content</b> - Get full article content</summary>

**Why LLMs need this:** For in-depth research, LLMs need complete information with all sections, references, and details. This tool provides the full Wikipedia article for comprehensive analysis.

**What it does:** Gets the complete content of a Wikipedia article with all sections, supporting multiple languages.

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

**Why LLMs need this:** Scientific research moves fast. arXiv hosts the latest preprints in physics, math, CS, and more. This tool gives LLMs access to cutting-edge research before it's even published in journals.

**What it does:** Searches arXiv for academic papers with filtering by category. Returns titles, abstracts, authors, and links.

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

**Why LLMs need this:** Medical and health questions require peer-reviewed sources. PubMed is the authoritative database for biomedical research, enabling LLMs to cite real studies rather than general knowledge.

**What it does:** Searches PubMed for biomedical and life science research papers. Returns titles, abstracts, authors, DOIs, and publication info.

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

**Why LLMs need this:** For current events and global news analysis, LLMs need access to worldwide media coverage. GDELT monitors news from every country, enabling analysis of how stories develop globally.

**What it does:** Searches the GDELT database for global news articles and events with time filtering.

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

**Why LLMs need this:** Developers ask about libraries, frameworks, and code examples. This tool helps LLMs find relevant repositories, compare alternatives, and recommend tools based on real popularity metrics (stars, forks).

**What it does:** Searches GitHub for repositories by keywords with sorting by stars, forks, or update date.

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

**Why LLMs need this:** README files contain installation instructions, API docs, and usage examples. This tool lets LLMs read actual documentation to provide accurate, up-to-date guidance on using any library.

**What it does:** Fetches the README file content from a GitHub repository in markdown format.

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

**Why LLMs need this:** Reddit contains real user experiences, reviews, and discussions. For questions like "what's the best X" or "how do people feel about Y", Reddit provides authentic community perspectives that formal sources lack.

**What it does:** Searches Reddit for posts across all subreddits or within a specific one, with time filtering.

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

**Why LLMs need this:** The real value of Reddit is in the comments - detailed explanations, counterarguments, and community voting. This tool extracts comment threads for deeper analysis of discussions.

**What it does:** Fetches comments from a specific Reddit post with scores and hierarchy.

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

**Why LLMs need this:** LLMs have no concept of "now" - they don't know the current date or time. This tool enables time-aware responses: scheduling, deadlines, "is it open now?", age calculations, and timezone conversions.

**What it does:** Gets the current date and time for any timezone with detailed components (day of week, week number, Unix timestamp).

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

**Why LLMs need this:** LLMs have no concept of "here" - they don't know where the user is. This tool enables location-aware responses: local weather, nearby services, correct timezone, and region-specific information.

**What it does:** Gets geographic location from an IP address including country, city, timezone, coordinates, and ISP info.

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

**Why LLMs need this:** Not all sources are equal. When citing information, LLMs need to distinguish between peer-reviewed research, reputable news, and random blogs. This tool provides objective credibility metrics to support source evaluation.

**What it does:** Assesses web source credibility using 30+ signals including domain age (WHOIS), citation network (PageRank), and content analysis with Bayesian confidence intervals.

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

**Why LLMs need this:** Long documents exceed context limits. Before analyzing a large PDF or article, this tool can create a concise summary, letting LLMs work with more sources without running out of context.

**What it does:** Summarizes long text using TF-IDF extraction, keyword-based selection, or fast heuristic methods. Runs locally with no external APIs.

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

**Why LLMs need this:** LLMs are notoriously bad at math. Even simple arithmetic can produce wrong answers. This tool provides accurate calculations for everything from basic math to trigonometry and logarithms.

**What it does:** Performs mathematical calculations using safe AST parsing (no eval). Supports arithmetic, trigonometry, logarithms, factorials, and mathematical constants.

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

**Why LLMs need this:** Users often want to discuss files on their system. This tool lets LLMs read text, PDFs, Word docs, and more to answer questions about file contents, analyze data, or help with editing.

**What it does:** Reads content from text, PDF, Word, Excel, or image files with automatic format detection.

**Parameters:**
- `path` (required): File path (relative paths use `data/files/` as base)

**Example:**
```json
{"path": "notes.txt"}
```
</details>

<details>
<summary><b>write_file</b> - Write/create file</summary>

**Why LLMs need this:** LLMs can generate code, documents, and data, but without file writing they can only display output. This tool lets them save generated content to actual files users can use.

**What it does:** Writes content to a file, creating it if it doesn't exist. UTF-8 text files only.

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

**Why LLMs need this:** For logging, note-taking, and incremental data collection, appending is safer than overwriting. This tool adds content to existing files without losing previous data.

**What it does:** Appends content to an existing file or creates a new one.

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

**Why LLMs need this:** Before reading or writing files, LLMs need to know what exists. This tool provides directory listings with file sizes and types, enabling file management workflows.

**What it does:** Lists files and directories with sizes and types.

**Parameters:**
- `path`: Directory path (default: `data/files/`)

**Example:**
```json
{"path": ""}
```
</details>

<details>
<summary><b>delete_file</b> - Delete file</summary>

**Why LLMs need this:** Complete file management requires deletion. This tool enables cleanup of temporary files, old outputs, and user-requested deletions with security restrictions.

**What it does:** Deletes a file (restricted to `data/files/` directory for security).

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
---

If you like this project, please give it a star ⭐

For questions, feedback, or support, reach out to:

[Artem KK](https://www.linkedin.com/in/kazkozdev/) | MIT [LICENSE](LICENSE)