"""Utilities for result normalization and deduplication."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


_TRACKING_KEYS = {
    "gclid",
    "fbclid",
    "yclid",
    "mc_cid",
    "mc_eid",
}


def normalize_url(url: str) -> str:
    """Normalize URL by removing fragments and common tracking parameters."""
    if not url:
        return url

    parsed = urlparse(url)
    query_items = []
    for k, v in parse_qsl(parsed.query, keep_blank_values=True):
        lk = k.lower()
        if lk.startswith("utm_"):
            continue
        if lk in _TRACKING_KEYS:
            continue
        query_items.append((k, v))

    normalized_query = urlencode(query_items, doseq=True)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            normalized_query,
            "",
        )
    )


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _normalized_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def title_similarity(a: str, b: str) -> float:
    """Compute similarity score for two titles."""
    na = _normalized_title(a)
    nb = _normalized_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(a=na, b=nb).ratio()


def dedupe_and_limit_results(
    results: Iterable[Dict[str, Any]],
    *,
    max_per_domain: int = 3,
    similarity_threshold: float = 0.92,
    normalize_urls: bool = True,
) -> List[Dict[str, Any]]:
    """Deduplicate results and limit number of results per domain.

    Args:
        results: Input result dicts.
        max_per_domain: Max results allowed per domain.
        similarity_threshold: Title similarity ratio to treat as duplicates.
        normalize_urls: If true, normalize URLs before dedupe.

    Returns:
        Cleaned list of results.
    """
    output: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    domain_counts: dict[str, int] = {}

    for item in results:
        title = str(item.get("title", ""))
        url = str(item.get("url", ""))
        if not title or not url:
            continue

        url_norm = normalize_url(url) if normalize_urls else url
        dom = _domain(url_norm)

        if url_norm in seen_urls:
            continue

        if dom:
            count = domain_counts.get(dom, 0)
            if count >= max_per_domain:
                continue

        is_dup = False
        for existing in output:
            if title_similarity(title, str(existing.get("title", ""))) >= similarity_threshold:
                is_dup = True
                break

        if is_dup:
            continue

        new_item = dict(item)
        new_item["url"] = url_norm
        output.append(new_item)
        seen_urls.add(url_norm)

        if dom:
            domain_counts[dom] = domain_counts.get(dom, 0) + 1

    return output
