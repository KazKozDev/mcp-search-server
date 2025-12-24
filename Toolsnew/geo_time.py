import logging
import requests
from typing import Optional, Dict
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class GeoTimeTool:
    """
    Tool to determine location and current time by IP.
    Provides system context ("here and now").
    """
    
    def __init__(self):
        # Uses ipapi.co free tier (no API key required for basic usage)
        self.geo_api_url = "https://ipapi.co/{ip}/json/"
        self.timeout = 10
    
    def get_public_ip(self) -> Optional[str]:
        """Get public IP address of the host."""
        try:
            resp = requests.get("https://api.ipify.org?format=json", timeout=5)
            if resp.status_code == 200:
                return resp.json().get('ip')
            return None
        except Exception as e:
            logger.warning(f"Failed to get public IP: {e}")
            return None
    
    def get_location_by_ip(self, ip: str = None) -> Optional[Dict]:
        """
        Get location details by IP address.
        
        Args:
            ip: IP address (if None, uses current host public IP)
            
        Returns:
            Dict with location metadata
        """
        if not ip:
            ip = self.get_public_ip()
            if not ip:
                return None
        
        logger.info(f"Getting location for IP: {ip}")
        
        try:
            # Construct URL for ipapi.co
            url = self.geo_api_url.format(ip=ip)
            
            resp = requests.get(
                url, 
                headers={'User-Agent': 'MultiAgentResearchSystem/1.0'},
                timeout=self.timeout
            )
            
            if resp.status_code != 200:
                logger.warning(f"Geolocation API error: {resp.status_code}")
                return None
            
            data = resp.json()
            
            # Check for API error response
            if data.get('error'):
                logger.warning(f"Geolocation API error: {data.get('reason')}")
                return None
            
            return {
                'ip': ip,
                'country': data.get('country_name'),
                'country_code': data.get('country_code'),
                'region': data.get('region'),
                'city': data.get('city'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'timezone': data.get('timezone'),
                'isp': data.get('org'),
                'source': 'geo_lookup'
            }
        
        except Exception as e:
            logger.error(f"Location lookup error for {ip}: {e}")
            return None
    
    def get_current_time(self, timezone_name: str = None) -> Optional[Dict]:
        """
        Get current time in a specific timezone.
        
        Args:
            timezone_name: Timezone string (e.g., 'Europe/London')
            
        Returns:
            Dict with time details
        """
        try:
            if not timezone_name:
                # Fallback to UTC if no timezone provided
                timezone_name = 'UTC'
            
            tz = pytz.timezone(timezone_name)
            now = datetime.now(tz)
            
            return {
                'timezone': timezone_name,
                'iso_time': now.isoformat(),
                'formatted_time': now.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'utc_offset': now.strftime('%z'),
                'is_dst': bool(now.dst()),
                'day_of_week': now.strftime('%A'),
                'source': 'system_time'
            }
        
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone: {timezone_name}")
            return None
        except Exception as e:
            logger.error(f"Time lookup error: {e}")
            return None

    def get_context(self, ip: str = None) -> Optional[Dict]:
        """
        Get comprehensive system context: location + current time.
        This provides the "here and now" context for agents.
        """
        # 1. Get Location
        location = self.get_location_by_ip(ip)
        
        if not location:
            # Fallback to UTC if location fails
            time_info = self.get_current_time('UTC')
            return {
                'location': {'status': 'unknown'},
                'time': time_info,
                'source': 'fallback_context'
            }
        
        # 2. Get Time for that Location
        timezone = location.get('timezone')
        time_info = self.get_current_time(timezone)
        
        return {
            'ip': location.get('ip'),
            'location': {
                'country': location.get('country'),
                'region': location.get('region'),
                'city': location.get('city'),
                'coordinates': {
                    'lat': location.get('latitude'),
                    'lon': location.get('longitude')
                }
            },
            'time': time_info,
            'source': 'geo_context'
        }


def register_tool(registry):
    """Register GeoTime tools in the registry"""
    tool = GeoTimeTool()
    
    registry.register('get_location', tool.get_location_by_ip)
    registry.register('get_current_time', tool.get_current_time)
    registry.register('get_system_context', tool.get_context)
    
    logger.info("Registered GeoTime tools: get_location, get_current_time, get_system_context")
