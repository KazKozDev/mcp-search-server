# Migration Guide: v0.1.4 → v0.1.5

## Summary of Changes

Version 0.1.5 introduces **smart multi-engine search** with automatic fallback support. This is a **backward-compatible** update - your existing code will continue to work without changes.

## What's New

### Multi-Engine Search Support

The `search_web` tool now supports multiple search engines with automatic fallback:

- **DuckDuckGo** (primary): Fast, reliable, works out of the box
- **Qwant** (backup): European search engine
- **Brave Search** (fallback): Requires Playwright for anti-bot bypass
- **Startpage** (fallback): Privacy-focused Google proxy, requires Playwright

### New Parameters

The `search_web` tool has new **optional** parameters:

```json
{
  "query": "your search",
  "limit": 10,
  "mode": "web",              // NEW: 'web' or 'news'
  "engine": "duckduckgo",     // NEW: specific engine or auto-fallback
  "use_fallback": true,       // NEW: enable/disable automatic fallback
  "no_cache": false           // NEW: disable caching
}
```

## Breaking Changes

**None** - This is a fully backward-compatible update.

## Migration Steps

### Option 1: No Changes Required (Recommended)

Your existing code will continue to work:

```json
{
  "query": "Python programming",
  "limit": 10
}
```

This will use DuckDuckGo by default with automatic fallback to other engines if needed.

### Option 2: Enable Browser-Based Search (Optional)

To use Brave Search and Startpage with anti-bot protection:

```bash
# Install Playwright
pip install playwright

# Install Firefox browser (recommended)
playwright install firefox
```

Or install via package extras:

```bash
pip install -e ".[browser]"
playwright install firefox
```

### Option 3: Use Specific Engine

You can now specify which search engine to use:

```json
{
  "query": "Python programming",
  "engine": "brave",
  "use_fallback": false
}
```

Available engines: `"duckduckgo"`, `"brave"`, `"startpage"`, `"qwant"`

## Performance Considerations

- **DuckDuckGo**: ~1-2 seconds (fastest)
- **Brave/Startpage**: ~3-5 seconds (requires browser rendering)
- **Auto-fallback**: Adds 0-5 seconds only if primary engine fails

## Recommended Setup

### For Production
- Use default settings (DuckDuckGo with fallback)
- Optionally install Playwright for maximum reliability

### For Maximum Speed
- Disable fallback: `"use_fallback": false`
- Don't install Playwright

### For Maximum Reliability
- Install Playwright with Firefox
- Use auto-fallback: `"use_fallback": true`

## Dependencies Update

### Required (no changes)
All existing dependencies remain the same.

### Optional (new)
- `playwright>=1.40.0` - For browser-based search engines

Install with:
```bash
pip install -e ".[browser]"
```

Or via requirements file:
```bash
pip install -r requirements-browser.txt
```

## Testing Your Setup

Test DuckDuckGo (should work immediately):
```bash
python -c "from mcp_search_server.tools.duckduckgo import DuckDuckGoSearchTool; import asyncio; asyncio.run(DuckDuckGoSearchTool().search('test', 3))"
```

Test Playwright availability:
```bash
python -c "from playwright.async_api import async_playwright; print('Playwright OK')"
```

## Troubleshooting

### Playwright Not Working
```bash
# Reinstall Firefox
playwright install --force firefox

# Or try Chromium
playwright install --force chromium
```

### Search Engines Blocked
This is expected for Brave/Startpage without Playwright. The system will automatically fall back to DuckDuckGo.

### Slow Search Results
- DuckDuckGo is fast (~1-2s)
- Browser rendering is slower (~3-5s)
- Consider using `"engine": "duckduckgo"` with `"use_fallback": false` for maximum speed

## Documentation

- See [FALLBACK_ENGINES.md](FALLBACK_ENGINES.md) for detailed engine documentation
- See [README.md](README.md) for updated API reference
- See [CHANGELOG.md](CHANGELOG.md) for complete list of changes

## Need Help?

If you encounter any issues during migration, please:
1. Check the logs for error messages
2. Verify Playwright installation: `playwright install firefox`
3. Test individual components using the test scripts
4. Open an issue on GitHub with details
