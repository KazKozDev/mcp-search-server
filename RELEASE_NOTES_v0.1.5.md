# Release Notes v0.1.5

**Release Date:** December 25, 2025

## 🎉 Major Features

### Smart Multi-Engine Search with Automatic Fallback

Version 0.1.5 introduces a revolutionary **smart search system** with automatic fallback across multiple search engines. Never worry about search failures again!

**How it works:**
1. **DuckDuckGo** (primary) - Fast, reliable, works out of the box
2. **Qwant** (backup) - European search engine
3. **Brave Search** (fallback) - Browser-based with anti-bot bypass
4. **Startpage** (fallback) - Privacy-focused Google proxy

The system automatically falls back to the next engine if the previous one returns less than 3 results.

### Playwright Browser Automation

New optional browser automation support for JavaScript-heavy sites:

- **Firefox** (primary) - More stable on macOS
- **Chromium** (fallback) - Alternative browser
- **Anti-bot bypass** - Defeats Cloudflare, JavaScript challenges
- **Smart rendering** - Only used when needed

## 🚀 New Features

### 1. Search Engine Selection
Choose your preferred search engine:

```json
{
  "query": "machine learning",
  "engine": "brave",
  "use_fallback": false
}
```

Supported engines: `duckduckgo`, `qwant`, `brave`, `startpage`

### 2. Fallback Control
Enable or disable automatic fallback:

```json
{
  "query": "Python programming",
  "use_fallback": true
}
```

### 3. Browser Dependencies (Optional)
Install browser support separately:

```bash
pip install -e ".[browser]"
playwright install firefox
```

### 4. Enhanced Documentation
- **MIGRATION.md** - Complete migration guide from v0.1.4
- **FALLBACK_ENGINES.md** - Detailed engine documentation
- **requirements-browser.txt** - Browser-specific dependencies

## 📊 Performance

| Engine     | Speed    | Reliability | Browser Required |
|------------|----------|-------------|------------------|
| DuckDuckGo | ~1-2s    | 99%         | ❌ No            |
| Qwant      | ~1-2s    | 70%         | ❌ No            |
| Brave      | ~3-5s    | 95%         | ✅ Yes           |
| Startpage  | ~3-5s    | 80%         | ✅ Yes           |

## 🔧 Breaking Changes

**None** - This is a fully backward-compatible release. Your existing code will continue to work without any changes.

## 📝 Migration Guide

### Option 1: No Changes (Recommended)
Your existing code works as-is:

```json
{
  "query": "Python programming",
  "limit": 10
}
```

### Option 2: Enable Browser Support (Optional)
For maximum reliability with Brave/Startpage:

```bash
pip install playwright
playwright install firefox
```

### Option 3: Use Specific Engine
Choose your preferred search engine:

```json
{
  "query": "AI news",
  "engine": "brave",
  "use_fallback": false
}
```

## 🐛 Bug Fixes

- **Fixed:** Chromium crashes on macOS (SEGV_ACCERR signal)
- **Fixed:** Anti-bot protection blocking Brave Search
- **Fixed:** Brave Search HTML parsing for new structure
- **Fixed:** Browser detection flags

## 🎯 Recommendations

### For Production
- Use default settings (auto-fallback)
- Optionally install Playwright for maximum reliability

### For Maximum Speed
- Disable fallback: `"use_fallback": false`
- Don't install Playwright

### For Maximum Reliability
- Install Playwright with Firefox
- Use auto-fallback: `"use_fallback": true`

## 📚 Documentation

- [Migration Guide](MIGRATION.md)
- [Search Engine Documentation](FALLBACK_ENGINES.md)
- [README](README.md)
- [Changelog](CHANGELOG.md)

## 🙏 Credits

Special thanks to:
- Playwright team for excellent browser automation
- DuckDuckGo for reliable search API
- The open-source community

## 🔗 Links

- **PyPI:** https://pypi.org/project/mcp-search-server/
- **GitHub:** https://github.com/KazKozDev/mcp-search-server
- **Issues:** https://github.com/KazKozDev/mcp-search-server/issues

## 📦 Installation

```bash
# Basic installation (DuckDuckGo + Qwant)
pip install mcp-search-server==0.1.5

# With browser support (all engines)
pip install mcp-search-server[browser]==0.1.5
playwright install firefox
```

---

**Full Changelog:** https://github.com/KazKozDev/mcp-search-server/blob/main/CHANGELOG.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)
