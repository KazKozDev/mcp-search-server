# Contributing to MCP Search Server

Thank you for your interest in contributing to MCP Search Server! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- pip

### Setting Up Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mcp-search-server.git
   cd mcp-search-server
   ```

3. Install in development mode with dev dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Making Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Format your code:
   ```bash
   black src/
   ```

4. Check for linting issues:
   ```bash
   ruff check src/
   ```

5. Run tests:
   ```bash
   pytest
   ```

6. Commit your changes:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

7. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

8. Create a Pull Request on GitHub

## Coding Standards

### Style Guide

- Follow PEP 8 guidelines
- Use Black for code formatting (line length: 100)
- Use type hints where appropriate
- Write docstrings for all public functions and classes

### Example Function

```python
async def search_example(query: str, limit: int = 10) -> list[dict]:
    """
    Search for examples.

    Args:
        query: The search query string
        limit: Maximum number of results to return

    Returns:
        List of search results as dictionaries

    Raises:
        ValueError: If query is empty
    """
    if not query:
        raise ValueError("Query cannot be empty")

    # Implementation here
    return []
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_search_server

# Run specific test file
pytest tests/test_search.py
```

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage
- Use pytest fixtures for common setup
- Mock external API calls

Example test:

```python
import pytest
from mcp_search_server.tools.duckduckgo import search_duckduckgo

@pytest.mark.asyncio
async def test_search_duckduckgo():
    results = await search_duckduckgo("Python", limit=5)
    assert len(results) <= 5
    assert all("title" in r for r in results)
```

## Adding New Tools

When adding a new MCP tool:

1. Create a new file in `src/mcp_search_server/tools/`
2. Implement the async function
3. Add the tool definition to `server.py` in `list_tools()`
4. Add the tool handler in `call_tool()`
5. Update README.md with tool documentation
6. Add tests for the new tool

## Commit Message Guidelines

Use clear and descriptive commit messages:

- Use the imperative mood ("Add feature" not "Added feature")
- First line should be 50 characters or less
- Add detailed description if needed after a blank line

Good examples:
```
Add Wikipedia search tool

Implement asynchronous Wikipedia search with caching and
error handling. Includes support for article summaries.
```

```
Fix PDF parsing memory leak

Release file handles properly after PDF processing to
prevent memory leaks in long-running servers.
```

## Pull Request Process

1. Update README.md if you've added new features
2. Update CHANGELOG.md (if exists) with your changes
3. Ensure all tests pass
4. Ensure code is formatted and linted
5. Request review from maintainers

### PR Title Format

- `feat: Add new feature`
- `fix: Fix bug description`
- `docs: Update documentation`
- `test: Add or update tests`
- `refactor: Code refactoring`
- `perf: Performance improvement`

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages and stack traces

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the "question" label
- Start a discussion on GitHub Discussions (if enabled)

Thank you for contributing!
