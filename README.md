

<p align="center">
  <img width="304" alt="log" src="https://github.com/user-attachments/assets/d831a711-9ddd-406a-b984-46e5693959c8" />
</p>

# MCP Search Server
<!-- mcp-name: io.github.KazKozDev/search -->

mcp-name: io.github.KazKozDev/search

[![PyPI version](https://img.shields.io/pypi/v/mcp-search-server.svg)](https://pypi.org/project/mcp-search-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/KazKozDev/mcp-search-server/actions/workflows/ci.yml/badge.svg)](https://github.com/KazKozDev/mcp-search-server/actions/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

MCP (Model Context Protocol) server for web search, content extraction, and PDF parsing.

All tools work out of the box using free public APIs. **No API keys required. No registration needed.**

**Context-Aware AI**: Built-in tools for real-time datetime and geolocation detection give LLMs the ability to understand "here and now" - enabling timezone-aware responses, location-based content, and time-sensitive information without manual configuration.

## Features

- **DateTime Tool**: Get current date and time with timezone awareness
- **Geolocation**: IP-based location detection with timezone, coordinates, and ISP info
- **Web Search**: Smart multi-engine search with automatic fallback
  - **DuckDuckGo** (primary): Fast, reliable, works out of the box
  - **Brave Search** (fallback): Browser-based with anti-bot bypass
  - **Startpage** (fallback): Privacy-focused Google proxy
  - **Qwant** (fallback): European search engine
- **Wikipedia Search**: Search and retrieve Wikipedia articles
- **Web Content Extraction**: Extract clean text from web pages using multiple parsing methods
- **PDF Parsing**: Extract text from PDF files
- **Multi-Source Search**: Parallel search across multiple sources
- **Academic Search**: Search arXiv, PubMed for scientific papers
- **GitHub Search**: Find repositories and README files
- **Reddit Search**: Search posts and comments
- **News Search**: GDELT global news database
- **🆕 Credibility Assessment**: Bayesian source credibility scoring with 30+ signals, domain age (WHOIS), citation network (PageRank), and uncertainty quantification - **no API keys required**
- **🆕 Text Summarization**: Multi-strategy summarization (TF-IDF extractive, keyword-based, heuristic) - fast, accurate, **no API keys required**
- **🆕 File Management**: Read/write files with support for text, PDF, Word, Excel, and images - fully async, secure, **no external services required**
- **🆕 Calculator**: Advanced mathematical calculations with trigonometry, logarithms, constants (pi, e), and more - safe expression evaluation, **no eval() vulnerabilities**

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

### Optional: Browser-based search engines

To enable **Brave Search** and **Startpage** with anti-bot bypass (using Playwright):

```bash
# Install optional browser dependencies
pip install -e ".[browser]"

# Install Firefox browser (recommended - more stable on macOS)
playwright install firefox

# Alternative: Install Chromium browser
playwright install chromium
```

**Note**: DuckDuckGo works perfectly without Playwright. Browser support is only needed for Brave and Startpage fallback engines.

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

Search the web with smart multi-engine fallback (DuckDuckGo → Qwant → Brave → Startpage).

**Parameters:**
- `query` (string, required): The search query
- `limit` (integer, optional): Maximum number of results (default: 10)
- `mode` (string, optional): Search mode - `'web'` (default) or `'news'`
- `timelimit` (string, optional): Filter by time - `'d'` (past day), `'w'` (past week), `'m'` (past month), `'y'` (past year), `null` (all time, default)
- `engine` (string, optional): Specific search engine - `'duckduckgo'`, `'brave'`, `'startpage'`, `'qwant'` (default: auto-fallback)
- `use_fallback` (boolean, optional): Enable automatic fallback to other engines (default: `true`)
- `no_cache` (boolean, optional): Disable cache (default: `false`)

**Examples:**

Auto-fallback search (recommended):
```json
{
  "query": "Python async programming",
  "limit": 5,
  "use_fallback": true
}
```

Search using specific engine:
```json
{
  "query": "machine learning",
  "limit": 10,
  "engine": "brave",
  "use_fallback": false
}
```

Search for recent news (past day):
```json
{
  "query": "latest AI developments",
  "limit": 10,
  "mode": "news",
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

### 10. assess_source_credibility 🆕

Assess the credibility of web sources using advanced Bayesian analysis with 30+ signals.

**Parameters:**
- `url` (string, required): URL to assess
- `title` (string, optional): Document title
- `content` (string, optional): Full text content (improves accuracy)
- `metadata` (object, optional): Structured metadata (year, authors, citations, doi, is_peer_reviewed)

**Example:**
```json
{
  "url": "https://arxiv.org/abs/2301.00234",
  "title": "Deep Learning for Medical Imaging",
  "metadata": {
    "year": 2023,
    "is_peer_reviewed": true,
    "citations": 42
  }
}
```

**Returns:**
- Credibility score (0-1)
- Confidence interval (e.g., 0.75 ± 0.08)
- Category (academic, news, code, forum, blog, government)
- PageRank score from citation network
- 30+ individual signal scores
- Recommendation (✓✓ Excellent / ✓ Good / ⚠ Caution / ✗ Limited)

**Features:**
- **Real Domain Age**: WHOIS-based domain registration date checking
- **Citation Network**: PageRank algorithm for link analysis
- **Bayesian Inference**: Prior probabilities + likelihood + posterior
- **30+ Signals**: Domain reputation, content quality, metadata analysis
- **Uncertainty Quantification**: Confidence intervals based on evidence
- **No API Keys Required**: All analysis runs locally

**Optional Enhancement:**
Install WHOIS support for real domain age checking:
```bash
pip install mcp-search-server[credibility]
```

**Documentation:**
See [docs/CREDIBILITY_ASSESSMENT.md](docs/CREDIBILITY_ASSESSMENT.md) for detailed usage, examples, and technical details.

### 11. summarize_text 🆕

Summarize long text using multiple strategies (TF-IDF, keyword-based, or heuristic).

**Parameters:**
- `text` (string, required): Text to summarize
- `strategy` (string, optional): "auto" (default), "extractive_tfidf", "extractive_keyword", "heuristic"
- `compression_ratio` (number, optional): Target compression 0.1-0.9 (default: 0.3 = 30%)

**Example:**
```json
{
  "text": "Long article text here...",
  "strategy": "extractive_tfidf",
  "compression_ratio": 0.3
}
```

**Returns:**
- Summary text
- Method used (extractive-tfidf, extractive-keyword, heuristic-3sent)
- Statistics (original/summary length, compression ratio, sentences)

**Strategies:**
- **extractive_tfidf** (best): Uses TF-IDF scoring to select important sentences. Requires NLTK.
- **extractive_keyword**: Prioritizes sentences with entities and key terms. Requires NLTK.
- **heuristic**: Ultra-fast fallback (first + middle + last sentences). No dependencies.
- **auto**: Automatically picks best available strategy.

**Features:**
- **Fast**: ~50ms for typical article (with NLTK), ~5ms (heuristic)
- **No API Keys**: All processing local
- **Smart Selection**: Maintains original sentence order
- **Graceful Degradation**: Falls back if NLTK unavailable

**Optional Enhancement:**
Install NLTK for better quality:
```bash
pip install mcp-search-server[summarizer]
```

**Use Cases:**
- Summarize web articles before credibility assessment
- Condense research papers for quick review
- Extract key points from long documents
- Generate previews for search results

---

### 12. File Management Tools 🆕

Comprehensive file operations supporting text, PDF, Word, Excel, and images.

#### read_file

Read content from a file (text, PDF, Word, Excel, images).

**Parameters:**
- `path` (string, required): File path (relative paths use `data/files/` as base)

**Example:**
```json
{
  "path": "notes.txt"
}
```

**Returns:**
- File content (text, extracted PDF/Word text, Excel data, or image metadata)
- File metadata (size, path, existence status)

#### write_file

Write or create a file.

**Parameters:**
- `path` (string, required): File path (relative paths use `data/files/` as base)
- `content` (string, required): Content to write (UTF-8 text)

**Example:**
```json
{
  "path": "output.txt",
  "content": "Hello, World!"
}
```

**Returns:**
- Success message with file metadata

#### append_file

Append content to an existing file (or create if doesn't exist).

**Parameters:**
- `path` (string, required): File path
- `content` (string, required): Content to append

**Example:**
```json
{
  "path": "log.txt",
  "content": "\nNew log entry"
}
```

#### list_files

List contents of a directory.

**Parameters:**
- `path` (string, optional): Directory path (empty for default `data/files/`)

**Example:**
```json
{
  "path": ""
}
```

**Returns:**
- List of files and directories with sizes and types

#### delete_file

Delete a file (security: only within `data/files/`).

**Parameters:**
- `path` (string, required): File path to delete

**Example:**
```json
{
  "path": "temp.txt"
}
```

**File Management Features:**
- **Supported Formats:**
  - Text files (UTF-8)
  - PDF documents (via pypdf)
  - Word documents (.docx via python-docx)
  - Excel spreadsheets (.xlsx/.xls via openpyxl/xlrd)
  - Images (JPG, PNG, GIF, BMP, WebP, TIFF via Pillow)
- **Security:**
  - All files stored in `data/files/` directory
  - Protection against path traversal attacks
  - Validation of file paths
- **Limits:**
  - Maximum file size: 10 MB
  - UTF-8 encoding for text files
- **Async Support:** All operations are non-blocking

**Optional Dependencies for Advanced Formats:**
```bash
pip install pypdf python-docx openpyxl xlrd Pillow
```

**Use Cases:**
- Save search results to files
- Log activity and errors
- Read configuration files
- Process uploaded documents
- Extract data from PDFs and Excel files
- Manage conversation history

**See also:** [File Manager Integration Guide](FILE_MANAGER_GUIDE.md) for detailed documentation and examples.

---

### 13. Calculator 🆕

Perform advanced mathematical calculations safely.

**Parameters:**
- `expression` (string, required): Mathematical expression to calculate

**Example:**
```json
{
  "expression": "sqrt(144) + sin(pi/2) * 10"
}
```

**Returns:**
- Calculation result with formatted output
- Expression type (int/float)
- Error message if calculation fails

**Supported Operations:**
- **Arithmetic:** `+`, `-`, `*`, `/`, `**` (power), `%` (modulo), `//` (floor division)
- **Parentheses:** Full support for nested parentheses
- **Constants:**
  - `pi` - π (3.14159...)
  - `e` - Euler's number (2.71828...)
  - `tau` - τ (2π)
  - `inf` - Infinity
  - `nan` - Not a Number

**Mathematical Functions:**

*Basic Functions:*
- `abs(x)` - Absolute value
- `round(x)` - Round to nearest integer
- `min(x, y, ...)` - Minimum value
- `max(x, y, ...)` - Maximum value
- `sqrt(x)` - Square root
- `pow(x, y)` - Power (x^y)

*Logarithmic Functions:*
- `log(x)` - Natural logarithm (base e)
- `log10(x)` - Base-10 logarithm
- `log2(x)` - Base-2 logarithm
- `exp(x)` - e^x

*Trigonometric Functions:*
- `sin(x)`, `cos(x)`, `tan(x)` - Basic trig functions (radians)
- `asin(x)`, `acos(x)`, `atan(x)` - Inverse trig functions
- `atan2(y, x)` - Two-argument arctangent
- `degrees(x)` - Convert radians to degrees
- `radians(x)` - Convert degrees to radians

*Hyperbolic Functions:*
- `sinh(x)`, `cosh(x)`, `tanh(x)` - Hyperbolic functions
- `asinh(x)`, `acosh(x)`, `atanh(x)` - Inverse hyperbolic functions

*Other Functions:*
- `ceil(x)` - Round up to nearest integer
- `floor(x)` - Round down to nearest integer
- `factorial(n)` - n! (factorial)
- `gcd(a, b)` - Greatest common divisor
- `lcm(a, b)` - Least common multiple

**Usage Examples:**
```python
# Basic arithmetic
"2 + 2"                    # 4
"(5 + 3) * 2"             # 16
"2**8"                    # 256 (2^8)
"17 % 5"                  # 2 (modulo)

# Square roots and powers
"sqrt(144)"               # 12
"pow(2, 10)"              # 1024

# Trigonometry
"sin(pi/2)"               # 1.0
"cos(0)"                  # 1.0
"tan(pi/4)"               # 1.0
"degrees(pi)"             # 180.0

# Logarithms
"log(e)"                  # 1.0 (ln(e))
"log10(100)"              # 2.0
"log2(1024)"              # 10.0

# Complex expressions
"sqrt(pow(3,2) + pow(4,2))"  # 5 (Pythagorean theorem)
"factorial(5)"            # 120
"gcd(48, 18)"            # 6
```

**Safety Features:**
- **No eval():** Uses AST parsing for safe evaluation
- **Sandboxed:** Only whitelisted functions allowed
- **Type validation:** Prevents code injection
- **Error handling:** Graceful error messages for invalid expressions

**Performance:**
- Fast: ~1ms for simple calculations
- Non-blocking: Async support for integration
- Memory efficient: No external dependencies

**Use Cases:**
- Scientific calculations
- Engineering computations
- Financial calculations (compound interest, NPV)
- Geometry and trigonometry
- Statistical computations
- Unit conversions with formulas

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
