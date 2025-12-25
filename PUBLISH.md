# Publishing v0.1.5 to PyPI

## ✅ Already Done

1. **Code committed and pushed:**
   - Commit: `d83222d`
   - Tag: `v0.1.5`
   - GitHub: ✅ Pushed

2. **GitHub Release created:**
   - URL: https://github.com/KazKozDev/mcp-search-server/releases/tag/v0.1.5
   - Release notes: ✅ Added
   - Artifacts: ✅ Attached (wheel + tar.gz)

3. **Package built:**
   - `dist/mcp_search_server-0.1.5-py3-none-any.whl` (80K)
   - `dist/mcp_search_server-0.1.5.tar.gz` (72K)
   - Validation: ✅ Passed (`twine check`)

## 📦 To Publish on PyPI

You need to upload the package manually with your PyPI API token:

```bash
# Set your PyPI API token
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxx  # Your PyPI API token

# Upload to PyPI
python -m twine upload dist/mcp_search_server-0.1.5*
```

Or use interactive mode:

```bash
python -m twine upload dist/mcp_search_server-0.1.5*
# Enter your API token when prompted
```

## 🔐 Getting PyPI API Token

1. Go to https://pypi.org/manage/account/token/
2. Create a new API token for the project
3. Copy the token (starts with `pypi-`)
4. Use it as password when uploading

## 📝 After Publishing

1. **Verify the release:**
   - Check PyPI: https://pypi.org/project/mcp-search-server/
   - Version should show: 0.1.5
   - Release date: 2025-12-25

2. **Test installation:**
   ```bash
   pip install mcp-search-server==0.1.5
   pip install mcp-search-server[browser]==0.1.5
   ```

3. **Announce the release:**
   - Update GitHub README if needed
   - Announce in relevant communities
   - Update documentation links

## 📊 Release Summary

**Version:** 0.1.5
**Release Date:** 2025-12-25
**GitHub:** ✅ Published
**PyPI:** ⏳ Pending (requires API token)

**Key Features:**
- Smart multi-engine search fallback
- Playwright browser automation
- Firefox + Chromium support
- Anti-bot bypass
- Optional browser dependencies

**Files to Upload:**
- `mcp_search_server-0.1.5-py3-none-any.whl`
- `mcp_search_server-0.1.5.tar.gz`

Both files are in the `dist/` directory and ready to upload.
