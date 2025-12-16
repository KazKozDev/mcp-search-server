"""DateTime tool for MCP Search Server - provides current date and time information."""

from datetime import datetime, timezone
from typing import Dict, Any
import pytz


async def get_current_datetime(
    timezone_name: str = "UTC", include_details: bool = True
) -> Dict[str, Any]:
    """
    Get current date and time with timezone information.

    Args:
        timezone_name: Timezone name (e.g., "UTC", "Europe/Moscow", "America/New_York")
        include_details: Include additional details like day of week, week number, etc.

    Returns:
        Dictionary with datetime information
    """
    try:
        # Get timezone
        if timezone_name == "UTC":
            tz = timezone.utc
        else:
            tz = pytz.timezone(timezone_name)

        # Get current time in specified timezone
        now = datetime.now(tz)

        result = {
            "datetime": now.isoformat(),
            "timezone": timezone_name,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": int(now.timestamp()),
        }

        if include_details:
            result.update(
                {
                    "year": now.year,
                    "month": now.month,
                    "day": now.day,
                    "hour": now.hour,
                    "minute": now.minute,
                    "second": now.second,
                    "day_of_week": now.strftime("%A"),
                    "day_of_week_num": now.weekday() + 1,  # 1 = Monday, 7 = Sunday
                    "week_number": now.isocalendar()[1],
                    "formatted": {
                        "full": now.strftime("%A, %B %d, %Y %H:%M:%S %Z"),
                        "date_long": now.strftime("%B %d, %Y"),
                        "date_short": now.strftime("%d/%m/%Y"),
                        "time_12h": now.strftime("%I:%M:%S %p"),
                        "time_24h": now.strftime("%H:%M:%S"),
                    },
                }
            )

        return result

    except pytz.exceptions.UnknownTimeZoneError:
        return {
            "error": f"Unknown timezone: {timezone_name}",
            "available_timezones_sample": [
                "UTC",
                "Europe/Moscow",
                "Europe/London",
                "America/New_York",
                "America/Los_Angeles",
                "Asia/Tokyo",
                "Asia/Shanghai",
            ],
        }
    except Exception as e:
        return {"error": f"Error getting datetime: {str(e)}"}


async def list_timezones(region: str = "all") -> Dict[str, Any]:
    """
    List available timezones.

    Args:
        region: Region filter ("all", "Europe", "America", "Asia", "Africa", "Australia")

    Returns:
        Dictionary with list of timezones
    """
    try:
        all_timezones = pytz.all_timezones

        if region.lower() == "all":
            # Group by continent
            grouped = {}
            for tz in all_timezones:
                if "/" in tz:
                    continent = tz.split("/")[0]
                    if continent not in grouped:
                        grouped[continent] = []
                    grouped[continent].append(tz)

            # Get sample from each continent
            result = {}
            for continent, zones in sorted(grouped.items()):
                result[continent] = zones[:5]  # First 5 from each continent

            return {
                "total_timezones": len(all_timezones),
                "sample_by_region": result,
                "note": "Use region parameter to get full list for specific region",
            }
        else:
            # Filter by region
            filtered = [tz for tz in all_timezones if tz.startswith(region)]
            return {"region": region, "timezones": filtered, "count": len(filtered)}

    except Exception as e:
        return {"error": f"Error listing timezones: {str(e)}"}
