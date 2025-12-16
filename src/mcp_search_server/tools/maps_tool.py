"""Maps/geocoding search tool."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import aiohttp

from ..cache_store import get_cached_json, set_cached_json
from ..config_loader import get_cache_ttl_seconds, get_maps_config

logger = logging.getLogger(__name__)


async def search_maps(
    query: str,
    *,
    limit: int = 5,
    country_codes: Optional[str] = None,
    no_cache: bool = False,
) -> List[Dict[str, Any]]:
    """Search places using OpenStreetMap Nominatim."""
    maps_cfg = get_maps_config()
    endpoint = maps_cfg.get("nominatim_endpoint", "https://nominatim.openstreetmap.org/search")
    user_agent = maps_cfg.get("user_agent", "mcp-search-server")

    ttl = get_cache_ttl_seconds("enrich")
    cache_key = f"maps|q={query}|limit={limit}|country_codes={country_codes}"
    cached = get_cached_json(cache_key, ttl_seconds=ttl, no_cache=no_cache)
    if isinstance(cached, list):
        return cached[:limit]

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": str(limit),
        "addressdetails": "1",
    }
    if country_codes:
        params["countrycodes"] = country_codes

    headers = {"User-Agent": user_agent}

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                endpoint, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
    except Exception as exc:
        logger.debug(f"Nominatim request failed: {exc}")
        return []

    results: List[Dict[str, Any]] = []
    for item in data or []:
        display_name = str(item.get("display_name", ""))
        lat = item.get("lat")
        lon = item.get("lon")
        osm_type = item.get("osm_type")
        osm_id = item.get("osm_id")

        url = ""
        if osm_type and osm_id:
            url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"

        results.append(
            {
                "title": display_name,
                "url": url,
                "snippet": f"lat={lat}, lon={lon}",
                "lat": lat,
                "lon": lon,
                "source": "nominatim",
            }
        )

    set_cached_json(cache_key, results, no_cache=no_cache)
    return results[:limit]
