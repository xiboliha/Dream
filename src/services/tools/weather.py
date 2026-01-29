"""Weather tool for querying weather information."""

import asyncio
import aiohttp
import os
from typing import Optional, Dict, Any
from loguru import logger


class WeatherTool:
    """Tool for fetching weather information using Amap (高德) API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize weather tool.

        Args:
            api_key: Amap API key (can also be set via AMAP_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("AMAP_API_KEY", "")
        self.base_url = "https://restapi.amap.com/v3/weather/weatherInfo"

    async def get_weather(self, city: str) -> Dict[str, Any]:
        """Get current weather for a city.

        Args:
            city: City name in Chinese (e.g., 昆山, 北京)

        Returns:
            Weather information dict
        """
        if not self.api_key:
            logger.warning("Amap API key not configured")
            return {"error": "天气服务未配置", "city": city}

        try:
            params = {
                "key": self.api_key,
                "city": city,
                "extensions": "base",  # base=实况, all=预报
                "output": "JSON"
            }
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_weather(data, city)
                    else:
                        logger.warning(f"Amap API returned {response.status}")
                        return {"error": "无法获取天气信息", "city": city}

        except asyncio.TimeoutError:
            logger.error("Amap API timeout")
            return {"error": "天气查询超时", "city": city}
        except Exception as e:
            logger.error(f"Amap API error: {e}")
            return {"error": "天气查询失败", "city": city}

    def _parse_weather(self, data: Dict, city: str) -> Dict[str, Any]:
        """Parse Amap API response."""
        try:
            if data.get("status") != "1":
                logger.warning(f"Amap API error: {data.get('info')}")
                return {"error": data.get("info", "查询失败"), "city": city}

            lives = data.get("lives", [])
            if not lives:
                return {"error": "未找到天气数据", "city": city}

            current = lives[0]
            return {
                "city": current.get("city", city),
                "province": current.get("province", ""),
                "temperature": current.get("temperature", "未知"),
                "weather": current.get("weather", "未知"),  # 天气现象：晴、多云、小雨等
                "humidity": current.get("humidity", "未知"),
                "wind_direction": current.get("winddirection", ""),
                "wind_power": current.get("windpower", ""),
                "report_time": current.get("reporttime", ""),
                "success": True,
            }
        except Exception as e:
            logger.error(f"Failed to parse Amap weather data: {e}")
            return {"error": "解析天气数据失败", "city": city}

    def format_weather_response(self, weather: Dict[str, Any]) -> str:
        """Format weather data into natural language response.

        Args:
            weather: Weather data dict

        Returns:
            Formatted string for conversation
        """
        if weather.get("error"):
            return f"查不到{weather.get('city', '')}的天气..."

        city = weather.get("city", "")
        temp = weather.get("temperature", "?")
        weather_desc = weather.get("weather", "")
        humidity = weather.get("humidity", "?")
        wind_dir = weather.get("wind_direction", "")
        wind_power = weather.get("wind_power", "")

        # Natural response style
        response = f"{city}现在{temp}度"
        if weather_desc:
            response += f"，{weather_desc}"

        try:
            h = int(humidity)
            if h > 80:
                response += "，有点潮"
            elif h < 30:
                response += "，比较干燥"
        except:
            pass

        if wind_dir and wind_power:
            try:
                wp = int(wind_power.replace("≤", ""))
                if wp >= 4:
                    response += f"，{wind_dir}风{wind_power}级"
            except:
                pass

        return response
