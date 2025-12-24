"""Configuration loader for MCP Search Server."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from mcp_search_server import __version__

logger = logging.getLogger(__name__)


def _project_root() -> Path:
    """Return project root directory (repository root)."""
    # Prefer current working directory when running as an installed package or from a
    # different entrypoint.
    cwd = Path.cwd()
    if (cwd / "config" / "search_config.json").exists():
        return cwd

    # Fallback for running from source tree.
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_search_config() -> dict[str, Any]:
    """Load search configuration from `config/search_config.json`.

    Returns:
        Parsed configuration dictionary. If config file doesn't exist or can't be read,
        returns a minimal default config.
    """
    default_config: dict[str, Any] = {
        "cache": {
            "dir": "~/.mcp-search-cache",
            "ttl_seconds": {"web": 21600, "news": 1200, "rss": 900, "enrich": 86400},
        },
        "results": {
            "max_per_domain": 3,
            "dedupe": {
                "enabled": True,
                "title_similarity_threshold": 0.92,
                "normalize_urls": True,
            },
        },
        "enrich": {"default_enabled": False, "top_k": 3, "max_chars": 600},
        "maps": {
            "nominatim_endpoint": "https://nominatim.openstreetmap.org/search",
            "user_agent": f"mcp-search-server/{__version__} (+https://localhost)",
        },
        "rss_sources": [],
    }

    config_path = _project_root() / "config" / "search_config.json"
    if not config_path.exists():
        return default_config

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            logger.warning("search_config.json root is not an object; using defaults")
            return default_config
        return {**default_config, **raw}
    except Exception as exc:
        logger.warning(f"Failed to read config at {config_path}: {exc}. Using defaults.")
        return default_config


def get_cache_dir() -> Path:
    """Return expanded cache directory path."""
    cache_dir = str(load_search_config().get("cache", {}).get("dir", "~/.mcp-search-cache"))
    return Path(cache_dir).expanduser()


def get_cache_ttl_seconds(kind: str) -> int:
    """Return TTL for cache kind ('web'|'news'|'rss'|'enrich')."""
    ttl = load_search_config().get("cache", {}).get("ttl_seconds", {}).get(kind, 3600)
    try:
        return int(ttl)
    except Exception:
        return 3600


def get_results_max_per_domain() -> int:
    """Return maximum number of results per domain."""
    value = load_search_config().get("results", {}).get("max_per_domain", 3)
    try:
        return int(value)
    except Exception:
        return 3


def get_dedupe_enabled() -> bool:
    """Return whether dedupe is enabled."""
    return bool(load_search_config().get("results", {}).get("dedupe", {}).get("enabled", True))


def get_title_similarity_threshold() -> float:
    """Return title similarity threshold for dedupe."""
    value = (
        load_search_config()
        .get("results", {})
        .get("dedupe", {})
        .get("title_similarity_threshold", 0.92)
    )
    try:
        return float(value)
    except Exception:
        return 0.92


def get_normalize_urls_enabled() -> bool:
    """Return whether URL normalization is enabled."""
    return bool(
        load_search_config().get("results", {}).get("dedupe", {}).get("normalize_urls", True)
    )


def get_enrich_defaults() -> dict[str, int | bool]:
    """Return default enrichment settings."""
    enrich = load_search_config().get("enrich", {})
    return {
        "enabled": bool(enrich.get("default_enabled", False)),
        "top_k": int(enrich.get("top_k", 3)),
        "max_chars": int(enrich.get("max_chars", 600)),
    }


def get_rss_sources() -> list[dict[str, Any]]:
    """Return RSS sources list."""
    sources = load_search_config().get("rss_sources", [])
    return sources if isinstance(sources, list) else []


def get_maps_config() -> dict[str, str]:
    """Return maps config."""
    maps_cfg = load_search_config().get("maps", {})
    if not isinstance(maps_cfg, dict):
        return {}
    return {
        "nominatim_endpoint": str(
            maps_cfg.get("nominatim_endpoint", "https://nominatim.openstreetmap.org/search")
        ),
        "user_agent": str(maps_cfg.get("user_agent", f"mcp-search-server/{__version__}")),
    }
