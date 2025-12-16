"""Simple JSON file cache with TTL."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from .config_loader import get_cache_dir

logger = logging.getLogger(__name__)


def _cache_path(cache_dir: Path, cache_key: str) -> Path:
    key_hash = hashlib.md5(cache_key.encode("utf-8")).hexdigest()
    return cache_dir / f"{key_hash}.json"


def get_cached_json(cache_key: str, ttl_seconds: int, *, no_cache: bool = False) -> Optional[Any]:
    """Get cached JSON data if present and not expired.

    Args:
        cache_key: Unique key for cache entry.
        ttl_seconds: Time-to-live for this entry.
        no_cache: If true, bypass cache.

    Returns:
        Cached data or None.
    """
    if no_cache:
        return None

    cache_dir = get_cache_dir()
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.debug(f"Failed to create cache dir {cache_dir}: {exc}")
        return None

    path = _cache_path(cache_dir, cache_key)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        ts = float(payload.get("timestamp", 0))
        if (time.time() - ts) > ttl_seconds:
            return None
        return payload.get("data")
    except Exception as exc:
        logger.debug(f"Failed to read cache entry {path}: {exc}")
        return None


def set_cached_json(cache_key: str, data: Any, *, no_cache: bool = False) -> None:
    """Save JSON-serializable data to cache.

    Args:
        cache_key: Unique key for cache entry.
        data: JSON-serializable value.
        no_cache: If true, don't write cache.
    """
    if no_cache:
        return

    cache_dir = get_cache_dir()
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.debug(f"Failed to create cache dir {cache_dir}: {exc}")
        return

    path = _cache_path(cache_dir, cache_key)
    try:
        payload = {"timestamp": time.time(), "data": data}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.debug(f"Failed to write cache entry {path}: {exc}")
