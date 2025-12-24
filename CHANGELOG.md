# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- None

### Changed
- None

### Deprecated
- None

### Removed
- None

### Fixed
- None

### Security
- None

## [0.1.4] - 2025-12-24

### Added
- **Trafilatura integration** - Advanced article extraction library for superior content quality
- **Undetected ChromeDriver** - Bypasses bot protection on Medium, Cloudflare, and similar services
- **Metadata extraction** - Extract title, author, publication date, description, and language from articles
- **Content caching system** - 24-hour cache with 1000-entry limit for improved performance
- **ArticleMetadata dataclass** - Structured metadata with JSON export and text formatting
- **6-method fallback chain** - Trafilatura → Readability → Newspaper → BeautifulSoup → Undetected Chrome → Selenium
- **SSL security** - Secure connections using certifi certificate validation
- **Human-like scraping** - Random delays and scrolling behavior to avoid detection

### Changed
- **Retry logic enhancement** - 3 attempts with exponential backoff (1s/2s/4s delays)
- **User-Agent rotation** - 5 different browser agents to reduce blocking
- **HTTP handling** - Rate limiting support (429 status), better encoding detection (UTF-8 → Latin-1 fallback)
- **Content size limits** - 5MB maximum with chunked reading to prevent memory issues
- **Early exit optimization** - Methods exit immediately on success, saving 60-70% processing time
- **Error handling** - More granular error messages with retry information
- **Session management** - Cookie jar support and enhanced browser-like headers
- **DuckDuckGo search improvements** - Removed region parameter for better language auto-detection

### Fixed
- **Async compatibility** - Migrated from deprecated `get_event_loop()` to `get_running_loop()`
- **Newspaper3k blocking** - Pre-fetch HTML to avoid blocking event loop
- **BeautifulSoup improvements** - Better content detection with article/main tag priority
- **Encoding issues** - Proper UTF-8 handling with fallback for non-standard encodings
- **DuckDuckGo regional results** - Fixed issue with Bulgarian results for Russian queries by removing forced region assignment

### Performance
- **Success rate improvement** - From ~70% to ~83% on diverse websites
- **Bot-protected sites** - Medium, Forbes, Russian news sites now supported
- **Cache performance** - <0.1s response time on cached requests vs 2-5s for fresh requests

## [0.1.2] - 2025-12-16

### Added
- Selenium-based DuckDuckGo search implementation
- Example MCP client configuration file (mcp_config.json)

### Changed
- DuckDuckGo search now uses Selenium by default

### Removed
- DuckDuckGo images/videos helper module (media_search)
- duckduckgo-search dependency
- healthcheck tool

### Fixed
- None

## [0.1.0] - 2025-12-15

### Added
- Initial release
