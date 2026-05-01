"""Weather helpers for netcafe_automation."""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_WEATHER_DOMAIN = "weather_domain"
CONF_WEATHER_SEARCH = "weather_search"
CONF_WEATHER_AREA_ID = "weather_area_id"
CONF_WEATHER_AREA_NAME = "weather_area_name"
CONF_WEATHER_AREA_CODE = "weather_area_code"
CONF_WEATHER_LATITUDE = "weather_latitude"
CONF_WEATHER_LONGITUDE = "weather_longitude"

DEFAULT_WEATHER_DOMAIN = "weather.com.cn"
DEFAULT_WEATHER_UPDATE_INTERVAL = timedelta(minutes=10)

HTTP_REFERER = "https://m.weather.com.cn/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def normalize_weather_domain(domain: str | None) -> str:
    """Normalize weather host input."""
    value = str(domain or "").strip()
    value = re.sub(r"^\s*https?://", "", value, flags=re.IGNORECASE)
    value = value.strip().strip("/")
    return value or DEFAULT_WEATHER_DOMAIN


def get_weather_entry_config(config_entry: ConfigEntry | None) -> dict[str, Any]:
    """Return merged weather-related config for one entry."""
    if config_entry is None:
        return {
            CONF_WEATHER_DOMAIN: DEFAULT_WEATHER_DOMAIN,
        }

    merged = {
        **(config_entry.data or {}),
        **(config_entry.options or {}),
    }
    merged[CONF_WEATHER_DOMAIN] = normalize_weather_domain(
        merged.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN)
    )
    return merged


@dataclass(slots=True)
class WeatherStation:
    """Resolved weather station info."""

    area_id: str
    area_name: str
    area_code: str
    latitude: float | None
    longitude: float | None

    @classmethod
    def from_api_data(cls, payload: dict[str, Any]) -> "WeatherStation":
        """Build station info from weather.com.cn payload."""
        return cls(
            area_id=str(payload.get("areaid", "")).strip(),
            area_name=str(payload.get("namecn", "")).strip(),
            area_code=str(payload.get("nameen", "")).strip(),
            latitude=_to_float(payload.get("lat")),
            longitude=_to_float(payload.get("lng")),
        )


def build_weather_entry_data(
    domain: str, station: WeatherStation
) -> dict[str, Any]:
    """Convert a resolved station into config entry data."""
    return {
        CONF_WEATHER_DOMAIN: normalize_weather_domain(domain),
        CONF_WEATHER_AREA_ID: station.area_id,
        CONF_WEATHER_AREA_NAME: station.area_name,
        CONF_WEATHER_AREA_CODE: station.area_code,
        CONF_WEATHER_LATITUDE: station.latitude,
        CONF_WEATHER_LONGITUDE: station.longitude,
    }


def _to_float(value: Any) -> float | None:
    """Convert a loosely typed numeric field to float."""
    if value in (None, ""):
        return None
    try:
        text = str(value).strip()
        text = re.sub(r"[^0-9.+-]", "", text)
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _load_json_payload(text: str) -> Any:
    """Parse JSON or JSONP payloads returned by weather.com.cn."""
    content = str(text or "").strip()
    if not content:
        raise ValueError("Empty payload")

    try:
        return json.loads(content)
    except json.JSONDecodeError as err:
        jsonp_match = re.search(
            r"^[^(]+\(\s*(\[.*\]|\{.*\})\s*\)\s*;?\s*$",
            content,
            re.DOTALL,
        )
        if jsonp_match:
            return json.loads(jsonp_match.group(1))

        start_positions = [
            pos for pos in (content.find("["), content.find("{")) if pos != -1
        ]
        end_positions = [
            pos for pos in (content.rfind("]"), content.rfind("}")) if pos != -1
        ]
        if start_positions and end_positions:
            start = min(start_positions)
            end = max(end_positions)
            if end > start:
                return json.loads(content[start : end + 1])

        preview = content[:160].replace("\n", " ").replace("\r", " ")
        raise ValueError(f"Unable to parse weather payload: {preview}") from err


class NetcafeWeatherClient:
    """Minimal weather.com.cn client."""

    def __init__(self, hass: HomeAssistant, domain: str | None = None) -> None:
        """Initialize weather client."""
        self.hass = hass
        self.domain = normalize_weather_domain(domain)
        self.session = aiohttp_client.async_get_clientsession(hass)

    def api_url(self, path: str, node: str = "d1", *, with_time: bool = True) -> str:
        """Build an API URL for weather.com.cn."""
        clean_path = path.lstrip("/")
        if with_time:
            sep = "&" if "?" in clean_path else "?"
            clean_path = f"{clean_path}{sep}_={int(time.time() * 1000)}"
        return f"https://{node}.{self.domain}/{clean_path}".replace(
            "https://www", "http://www"
        )

    async def _async_get_text(
        self,
        path: str,
        *,
        node: str = "d1",
        params: dict[str, Any] | None = None,
        with_time: bool = True,
    ) -> str:
        """GET text from weather.com.cn."""
        url = self.api_url(path, node=node, with_time=with_time)
        headers = {
            "Referer": HTTP_REFERER,
            "User-Agent": USER_AGENT,
        }
        async with self.session.get(
            url,
            params=params,
            headers=headers,
            allow_redirects=False,
            ssl=False,
        ) as response:
            text = await response.text()
            if not text:
                raise ClientError(f"Empty response from {url}")
            if response.status >= 400:
                raise ClientError(f"{response.status} from {url}")
            return text

    async def async_search_locations(self, keyword: str) -> dict[str, str]:
        """Search cities/counties."""
        query = str(keyword or "").strip()
        if not query:
            return {}

        text = await self._async_get_text(
            "search",
            node="toy1",
            params={"cityname": query},
            with_time=False,
        )

        payload = _load_json_payload(text)
        if not isinstance(payload, list):
            raise ValueError(
                f"Unexpected weather search payload type: {type(payload).__name__}"
            )

        results: dict[str, str] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            ref = item.get("ref")
            if not ref:
                continue
            parts = str(ref).split("~")
            area_id = parts[0] if parts else ""
            if len(area_id) > 9 or len(parts) < 10:
                continue
            results[area_id] = f"{parts[9]}-{parts[2]}"
        return results

    async def async_get_station(
        self,
        *,
        area_id: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> WeatherStation:
        """Resolve a station from area id or HA location."""
        params: dict[str, Any] = {"method": "stationinfo"}
        clean_area_id = str(area_id or "").strip()
        if clean_area_id and clean_area_id != "auto":
            params["areaid"] = clean_area_id
        else:
            lat = latitude if latitude is not None else self.hass.config.latitude
            lon = longitude if longitude is not None else self.hass.config.longitude
            if lat is None or lon is None:
                raise ValueError("Latitude/longitude is required for auto weather lookup")
            params["lat"] = lat
            params["lng"] = lon

        text = await self._async_get_text(
            "geong/v1/api",
            node="d7",
            params={"params": json.dumps(params, separators=(",", ":"))},
        )
        payload = _load_json_payload(text)
        if not isinstance(payload, dict):
            raise ValueError(
                f"Unexpected weather station payload type: {type(payload).__name__}"
            )
        station_data = payload.get("data", {}).get("station") or {}
        if not station_data:
            raise ValueError(f"Unable to resolve weather station: {params}")
        merged = {
            **(payload.get("location", {}) or {}),
            **station_data,
        }
        return WeatherStation.from_api_data(merged)

    async def async_fetch_weather(
        self,
        *,
        area_id: str,
        area_name: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        """Fetch current weather data for one configured location."""
        station = await self.async_get_station(
            area_id=area_id,
            latitude=latitude,
            longitude=longitude,
        )

        summary_text = await self._async_get_text(
            f"weather_index/{station.area_id}.html"
        )
        alarms_text = await self._async_get_text(
            f"dingzhi/{station.area_id}.html"
        )

        minutely_message: str | None = None
        if station.latitude is not None and station.longitude is not None:
            try:
                minutely_text = await self._async_get_text(
                    "webgis_rain_new/webgis/minute",
                    node="d3",
                    params={
                        "lat": station.latitude,
                        "lon": station.longitude,
                    },
                )
                minutely_payload = _load_json_payload(minutely_text)
                if not isinstance(minutely_payload, dict):
                    minutely_payload = {}
                minutely_message = minutely_payload.get("msg")
            except Exception as err:  # pragma: no cover - network dependent
                _LOGGER.debug("Unable to fetch minutely forecast: %s", err)

        data_sk = _extract_assignment(summary_text, "dataSK")
        data_zs_root = _extract_assignment(summary_text, "dataZS")
        data_zs = (data_zs_root or {}).get("zs") or {}
        alarms_root = _extract_alarm_blob(alarms_text)
        alarms = (alarms_root or {}).get("w") or []

        weather_desc = str(data_sk.get("weather", "")).strip() or "未知"
        weather_code = str(data_sk.get("weathercode", "")).strip()
        indexes = _extract_indexes(data_zs)

        return {
            "configured": True,
            "domain": self.domain,
            "location_name": station.area_name or area_name or station.area_id,
            "area_id": station.area_id,
            "area_code": station.area_code,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "weather": weather_desc,
            "weather_code": weather_code,
            "temperature": _to_float(data_sk.get("temp")),
            "humidity": _to_float(data_sk.get("sd")),
            "aqi": data_sk.get("aqi"),
            "precipitation": _to_float(data_sk.get("rain")),
            "pressure": _to_float(data_sk.get("qy")),
            "visibility": _to_float(data_sk.get("njd")),
            "wind_direction": data_sk.get("WD") or data_sk.get("wde"),
            "wind_speed": _to_float(data_sk.get("wse")),
            "wind_level": data_sk.get("WS"),
            "limit_number": data_sk.get("limitnumber"),
            "updated_at": data_sk.get("time"),
            "hourly_forecast": data_zs.get("ct_des_s"),
            "forecast_keypoint": data_zs.get("ys_des_s"),
            "minutely_forecast": minutely_message,
            "indexes": indexes,
            "alarms": [
                {
                    "province": item.get("w1"),
                    "city": item.get("w2"),
                    "title": item.get("w13"),
                    "description": item.get("w9"),
                    "code": f"{item.get('w4', '')}{item.get('w6', '')}",
                }
                for item in alarms
            ],
        }


def _extract_assignment(text: str, var_name: str) -> dict[str, Any]:
    """Extract a JS object assignment from HTML text."""
    pattern = rf"{re.escape(var_name)}\s*=\s*({{.*?}})\s*;"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return {}
    return json.loads(match.group(1)) or {}


def _extract_alarm_blob(text: str) -> dict[str, Any]:
    """Extract alarm JSON from dingzhi response."""
    match = re.search(r"var alarmDZ\w*\s*=\s*({.*})", text, re.DOTALL)
    if not match:
        return {}
    return json.loads(match.group(1)) or {}


def _extract_indexes(data_zs: dict[str, Any]) -> dict[str, str]:
    """Extract life index text from weather.com.cn summary data."""
    indexes: dict[str, str] = {}
    for key, value in data_zs.items():
        if not key.endswith("_name"):
            continue
        prefix = key[:-5]
        description = data_zs.get(f"{prefix}_des_s")
        if description:
            indexes[str(value)] = str(description)
    return indexes


class NetcafeWeatherCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for configured weather data."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the weather coordinator."""
        self.config_entry = config_entry
        config = get_weather_entry_config(config_entry)
        self._config = config
        self.client = NetcafeWeatherClient(hass, config.get(CONF_WEATHER_DOMAIN))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_weather_{config_entry.entry_id}",
            update_interval=DEFAULT_WEATHER_UPDATE_INTERVAL,
            config_entry=config_entry,
        )

    def _current_config(self) -> dict[str, Any]:
        """Refresh cached entry config."""
        self._config = get_weather_entry_config(self.config_entry)
        self.client.domain = self._config.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN)
        return self._config

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest weather data while keeping stale data on failure."""
        config = self._current_config()
        area_id = str(config.get(CONF_WEATHER_AREA_ID, "")).strip()
        if not area_id:
            return {
                "configured": False,
                "domain": config.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN),
                "location_name": "",
                "last_error": None,
                "stale": False,
            }

        try:
            data = await self.client.async_fetch_weather(
                area_id=area_id,
                area_name=str(config.get(CONF_WEATHER_AREA_NAME, "")).strip(),
                latitude=config.get(CONF_WEATHER_LATITUDE),
                longitude=config.get(CONF_WEATHER_LONGITUDE),
            )
            data["last_error"] = None
            data["stale"] = False
            return data
        except Exception as err:  # pragma: no cover - network dependent
            _LOGGER.warning("Weather update failed for %s: %s", area_id, err)
            if self.data:
                stale = dict(self.data)
                stale["last_error"] = str(err)
                stale["stale"] = True
                return stale
            return {
                "configured": True,
                "domain": config.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN),
                "location_name": str(config.get(CONF_WEATHER_AREA_NAME, "")).strip(),
                "area_id": area_id,
                "last_error": str(err),
                "stale": True,
            }
