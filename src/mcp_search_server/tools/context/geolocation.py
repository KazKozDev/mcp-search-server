"""Geolocation tool for MCP Search Server - IP-based location detection."""

import asyncio
from typing import Dict, Any, Optional
import aiohttp


async def get_location_by_ip(ip_address: Optional[str] = None) -> Dict[str, Any]:
    """
    Get geolocation information based on IP address.

    Args:
        ip_address: IP address to lookup. If None, uses the public IP of the server.

    Returns:
        Dictionary with location information including country, city, timezone, coordinates, etc.
    """
    try:
        # Use ip-api.com - free, no API key required, 45 requests/minute
        if ip_address:
            url = f"http://ip-api.com/json/{ip_address}"
        else:
            # Get own public IP location
            url = "http://ip-api.com/json/"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("status") == "success":
                        return {
                            "ip": data.get("query"),
                            "country": data.get("country"),
                            "country_code": data.get("countryCode"),
                            "region": data.get("regionName"),
                            "region_code": data.get("region"),
                            "city": data.get("city"),
                            "zip": data.get("zip"),
                            "latitude": data.get("lat"),
                            "longitude": data.get("lon"),
                            "timezone": data.get("timezone"),
                            "isp": data.get("isp"),
                            "organization": data.get("org"),
                            "as_number": data.get("as"),
                            "coordinates": {"lat": data.get("lat"), "lon": data.get("lon")},
                        }
                    else:
                        # API returned error status
                        return {
                            "error": data.get("message", "IP lookup failed"),
                            "ip": ip_address or "auto",
                        }
                else:
                    return {"error": f"HTTP error: {response.status}", "ip": ip_address or "auto"}

    except asyncio.TimeoutError:
        return {"error": "Request timed out", "ip": ip_address or "auto"}
    except Exception as e:
        return {"error": f"Error fetching location: {str(e)}", "ip": ip_address or "auto"}


async def get_multiple_ips_location(ip_addresses: list[str]) -> Dict[str, Any]:
    """
    Get geolocation for multiple IP addresses in parallel.

    Args:
        ip_addresses: List of IP addresses to lookup

    Returns:
        Dictionary mapping IP addresses to their location data
    """
    tasks = [get_location_by_ip(ip) for ip in ip_addresses]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = {}
    for i, ip in enumerate(ip_addresses):
        if isinstance(results[i], Exception):
            output[ip] = {"error": str(results[i])}
        else:
            output[ip] = results[i]

    return output


async def get_timezone_from_ip(ip_address: Optional[str] = None) -> Dict[str, Any]:
    """
    Get just the timezone information from IP address.
    Convenience function for timezone detection.

    Args:
        ip_address: IP address to lookup. If None, uses the public IP of the server.

    Returns:
        Dictionary with timezone information
    """
    location = await get_location_by_ip(ip_address)

    if "error" in location:
        return location

    return {
        "ip": location.get("ip"),
        "timezone": location.get("timezone"),
        "country": location.get("country"),
        "city": location.get("city"),
    }
