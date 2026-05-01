"""Sensor platform for netcafe_automation."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, HUB_MANUFACTURER, HUB_MODEL, HUB_NAME
from .license_manager import get_license_manager
from .weather_service import (
    NetcafeWeatherCoordinator,
    get_weather_entry_config,
)

_LOGGER = logging.getLogger(__name__)

LICENSE_SENSOR_UNIQUE_ID = f"{DOMAIN}_license"
LICENSE_CHECK_INTERVAL = timedelta(minutes=1)
MONTH_UPDATE_INTERVAL = timedelta(hours=1)

HUB_VERSION = "3.1.0"

WEATHER_ICON_MAP = {
    "00": "mdi:weather-sunny",
    "01": "mdi:weather-partly-cloudy",
    "02": "mdi:weather-cloudy",
    "03": "mdi:weather-partly-rainy",
    "04": "mdi:weather-lightning-rainy",
    "05": "mdi:weather-hail",
    "06": "mdi:weather-snowy-rainy",
    "07": "mdi:weather-rainy",
    "08": "mdi:weather-pouring",
    "09": "mdi:weather-pouring",
    "10": "mdi:weather-pouring",
    "11": "mdi:weather-pouring",
    "12": "mdi:weather-pouring",
    "13": "mdi:weather-snowy",
    "14": "mdi:weather-snowy",
    "15": "mdi:weather-snowy-heavy",
    "16": "mdi:weather-snowy-heavy",
    "17": "mdi:weather-snowy-heavy",
    "18": "mdi:weather-fog",
    "19": "mdi:weather-hail",
    "20": "mdi:weather-dust",
    "21": "mdi:weather-rainy",
    "22": "mdi:weather-pouring",
    "23": "mdi:weather-pouring",
    "24": "mdi:weather-pouring",
    "25": "mdi:weather-pouring",
    "26": "mdi:weather-snowy",
    "27": "mdi:weather-snowy-heavy",
    "28": "mdi:weather-snowy-heavy",
    "29": "mdi:weather-windy",
    "30": "mdi:weather-windy",
    "31": "mdi:weather-windy-variant",
    "32": "mdi:weather-fog",
    "49": "mdi:weather-fog",
    "53": "mdi:weather-hazy",
    "54": "mdi:weather-hazy",
    "55": "mdi:weather-hazy",
    "56": "mdi:weather-hazy",
    "57": "mdi:weather-fog",
    "58": "mdi:weather-fog",
    "301": "mdi:weather-lightning",
    "302": "mdi:weather-snowy-heavy",
}


def _build_hub_device_info(entry_id: str) -> DeviceInfo:
    """Return the primary integration device info."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"hub_{entry_id}")},
        name=HUB_NAME,
        model=HUB_MODEL,
        manufacturer=HUB_MANUFACTURER,
        sw_version=HUB_VERSION,
    )


def _get_license_manager(hass: HomeAssistant):
    """Return a cached license manager."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    license_mgr = domain_data.get("license_manager")
    if license_mgr is None:
        license_mgr = get_license_manager(hass)
        domain_data["license_manager"] = license_mgr
    return license_mgr


async def _async_get_weather_coordinator(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> NetcafeWeatherCoordinator:
    """Return one weather coordinator per entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    coordinators = domain_data.setdefault("weather_coordinators", {})
    coordinator = coordinators.get(config_entry.entry_id)
    if coordinator is None:
        coordinator = NetcafeWeatherCoordinator(hass, config_entry)
        coordinators[config_entry.entry_id] = coordinator

        @callback
        def _remove_weather_coordinator() -> None:
            """Drop the cached weather coordinator for this entry."""
            coordinators.pop(config_entry.entry_id, None)

        config_entry.async_on_unload(_remove_weather_coordinator)
    return coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for one config entry."""
    weather_coordinator = await _async_get_weather_coordinator(hass, config_entry)
    hass.async_create_task(weather_coordinator.async_refresh())

    entities: list[SensorEntity] = [
        LicenseExpirationSensor(hass, config_entry),
        LicenseStatusSensor(hass, config_entry),
        LicenseDaysRemainingSensor(hass, config_entry),
        CurrentMonthSensor(hass, config_entry),
        CurrentWeatherSensor(config_entry, weather_coordinator),
        CurrentWeatherTemperatureSensor(config_entry, weather_coordinator),
        CurrentWeatherHumiditySensor(config_entry, weather_coordinator),
    ]

    async_add_entities(entities, True)
    _LOGGER.info("Added %d sensor entities for %s", len(entities), config_entry.title)


class LicenseBaseSensor(SensorEntity):
    """Base class for periodically refreshed license sensors."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the base license sensor."""
        self.hass = hass
        self._entry_id = config_entry.entry_id
        self._attr_device_info = _build_hub_device_info(self._entry_id)
        self._unsub_update = None

    async def async_added_to_hass(self) -> None:
        """Handle entity addition."""
        await super().async_added_to_hass()
        await self._async_update_state()
        self._unsub_update = async_track_time_interval(
            self.hass,
            self._async_update_state,
            LICENSE_CHECK_INTERVAL,
            cancel_on_shutdown=True,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None
        await super().async_will_remove_from_hass()

    async def _async_get_status(self) -> dict[str, Any]:
        """Fetch current license status."""
        license_mgr = _get_license_manager(self.hass)
        return await self.hass.async_add_executor_job(license_mgr.get_license_status)

    async def _async_update_state(self, *_: Any) -> None:
        """Refresh sensor state."""
        raise NotImplementedError


class LicenseExpirationSensor(LicenseBaseSensor):
    """Sensor showing license expiration date and time."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = f"{LICENSE_SENSOR_UNIQUE_ID}_{self._entry_id}_date"
        self._attr_name = "卡密到期时间"

    async def _async_update_state(self, *_: Any) -> None:
        """Refresh sensor state."""
        status = await self._async_get_status()
        expire_date = status.get("expire_date")

        if expire_date:
            try:
                expire_dt = datetime.fromisoformat(str(expire_date))
                expire_dt = dt_util.as_local(expire_dt)
                self._attr_native_value = expire_dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                self._attr_native_value = str(expire_date)
        else:
            self._attr_native_value = "未激活"

        self._attr_extra_state_attributes = {
            "days_remaining": status.get("days_remaining", 0),
            "hours_remaining": status.get("hours_remaining", 0),
            "is_valid": status.get("is_valid", False),
            "is_expired": status.get("is_expired", True),
            "message": status.get("message", ""),
        }
        self.async_write_ha_state()


class LicenseStatusSensor(LicenseBaseSensor):
    """Sensor showing current license status."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = f"{LICENSE_SENSOR_UNIQUE_ID}_{self._entry_id}_status"
        self._attr_name = "卡密状态"
        self._attr_icon = "mdi:shield-check"

    async def _async_update_state(self, *_: Any) -> None:
        """Refresh sensor state."""
        status = await self._async_get_status()
        is_valid = bool(status.get("is_valid", False))
        is_expired = bool(status.get("is_expired", False))

        if is_valid and not is_expired:
            self._attr_native_value = "有效"
            self._attr_icon = "mdi:shield-check"
        elif is_expired:
            self._attr_native_value = "已过期"
            self._attr_icon = "mdi:shield-off"
        else:
            self._attr_native_value = "无效"
            self._attr_icon = "mdi:shield-alert"

        self._attr_extra_state_attributes = {
            "days_remaining": status.get("days_remaining", 0),
            "hours_remaining": status.get("hours_remaining", 0),
            "message": status.get("message", ""),
            "key": status.get("key", ""),
        }
        self.async_write_ha_state()


class LicenseDaysRemainingSensor(LicenseBaseSensor):
    """Sensor showing days remaining until expiration."""

    _attr_icon = "mdi:calendar-account"
    _attr_native_unit_of_measurement = "天"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass, config_entry)
        self._attr_unique_id = f"{LICENSE_SENSOR_UNIQUE_ID}_{self._entry_id}_days"
        self._attr_name = "卡密剩余天数"

    async def _async_update_state(self, *_: Any) -> None:
        """Refresh sensor state."""
        status = await self._async_get_status()
        days_remaining = int(status.get("days_remaining", 0))
        self._attr_native_value = days_remaining

        if days_remaining > 7:
            self._attr_icon = "mdi:calendar-check"
        elif days_remaining > 3:
            self._attr_icon = "mdi:calendar-alert"
        else:
            self._attr_icon = "mdi:calendar-remove"

        self._attr_extra_state_attributes = {
            "is_valid": status.get("is_valid", False),
            "is_expired": status.get("is_expired", True),
            "is_expiring_soon": status.get("is_expiring_soon", False),
        }
        self.async_write_ha_state()


class CurrentMonthSensor(SensorEntity):
    """Sensor exposing the current month."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-month"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the month sensor."""
        self.hass = hass
        self._entry_id = config_entry.entry_id
        self._attr_unique_id = f"{DOMAIN}_{self._entry_id}_month"
        self._attr_name = "当前月份"
        self._attr_device_info = _build_hub_device_info(self._entry_id)
        self._unsub_update = None

    async def async_added_to_hass(self) -> None:
        """Handle entity addition."""
        await super().async_added_to_hass()
        self._async_update_state()
        self._unsub_update = async_track_time_interval(
            self.hass,
            self._handle_time_change,
            MONTH_UPDATE_INTERVAL,
            cancel_on_shutdown=True,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None
        await super().async_will_remove_from_hass()

    async def _handle_time_change(self, *_: Any) -> None:
        """Refresh on schedule."""
        self._async_update_state()

    def _async_update_state(self) -> None:
        """Refresh the month state."""
        now = dt_util.now()
        month_number = now.month
        self._attr_native_value = f"{month_number:02d}月"
        self._attr_extra_state_attributes = {
            "year": now.year,
            "month_number": month_number,
            "quarter": ((month_number - 1) // 3) + 1,
            "season": _get_season(month_number),
            "iso": now.strftime("%Y-%m"),
        }
        self.async_write_ha_state()


class CurrentWeatherSensor(
    CoordinatorEntity[NetcafeWeatherCoordinator],
    SensorEntity,
):
    """Sensor showing the configured current weather."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: NetcafeWeatherCoordinator,
    ) -> None:
        """Initialize the weather sensor."""
        super().__init__(coordinator)
        self._entry_id = config_entry.entry_id
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_{self._entry_id}_weather"
        self._attr_name = "当前天气"
        self._attr_device_info = _build_hub_device_info(self._entry_id)
        self._attr_icon = "mdi:weather-cloudy"

    @property
    def native_value(self) -> str:
        """Return sensor state."""
        data = self.coordinator.data or {}
        if not data.get("configured", False):
            return "未配置"
        return str(data.get("weather") or "未知")

    @property
    def icon(self) -> str:
        """Return a dynamic icon."""
        data = self.coordinator.data or {}
        if not data.get("configured", False):
            return "mdi:weather-cloudy-alert"
        code = str(data.get("weather_code", "")).strip()
        return WEATHER_ICON_MAP.get(code, "mdi:weather-cloudy")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra weather details."""
        data = self.coordinator.data or {}
        if not data.get("configured", False):
            config = get_weather_entry_config(self._config_entry)
            return {
                "configured": False,
                "domain": config.get("weather_domain"),
                "tip": "请在集成选项中搜索并选择天气地点。",
            }

        return {
            "configured": True,
            "location": data.get("location_name"),
            "area_id": data.get("area_id"),
            "area_code": data.get("area_code"),
            "domain": data.get("domain"),
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "aqi": data.get("aqi"),
            "precipitation": data.get("precipitation"),
            "pressure": data.get("pressure"),
            "visibility": data.get("visibility"),
            "wind_direction": data.get("wind_direction"),
            "wind_speed": data.get("wind_speed"),
            "wind_level": data.get("wind_level"),
            "hourly_forecast": data.get("hourly_forecast"),
            "forecast_keypoint": data.get("forecast_keypoint"),
            "minutely_forecast": data.get("minutely_forecast"),
            "limit_number": data.get("limit_number"),
            "updated_at": data.get("updated_at"),
            "stale": data.get("stale", False),
            "last_error": data.get("last_error"),
            "alarms": data.get("alarms", []),
            "indexes": data.get("indexes", {}),
        }


class _WeatherMetricSensor(
    CoordinatorEntity[NetcafeWeatherCoordinator],
    SensorEntity,
):
    """Base sensor for weather metrics."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: NetcafeWeatherCoordinator,
        *,
        suffix: str,
        name: str,
        metric_key: str,
        icon: str,
        unit: str,
        device_class: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._metric_key = metric_key
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_weather_{suffix}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_info = _build_hub_device_info(config_entry.entry_id)
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def available(self) -> bool:
        data = self.coordinator.data or {}
        return bool(data.get("configured")) and data.get(self._metric_key) is not None

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data or {}
        if not data.get("configured", False):
            return None
        return data.get(self._metric_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "location": data.get("location_name"),
            "weather": data.get("weather"),
            "updated_at": data.get("updated_at"),
            "stale": data.get("stale", False),
            "last_error": data.get("last_error"),
        }


class CurrentWeatherTemperatureSensor(_WeatherMetricSensor):
    """Sensor showing current weather temperature."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: NetcafeWeatherCoordinator,
    ) -> None:
        super().__init__(
            config_entry,
            coordinator,
            suffix="temperature",
            name="天气温度",
            metric_key="temperature",
            icon="mdi:thermometer",
            unit="°C",
            device_class="temperature",
        )


class CurrentWeatherHumiditySensor(_WeatherMetricSensor):
    """Sensor showing current weather humidity."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: NetcafeWeatherCoordinator,
    ) -> None:
        super().__init__(
            config_entry,
            coordinator,
            suffix="humidity",
            name="天气湿度",
            metric_key="humidity",
            icon="mdi:water-percent",
            unit="%",
            device_class="humidity",
        )


def _get_season(month: int) -> str:
    """Return a simple Chinese season label."""
    if month in (3, 4, 5):
        return "春"
    if month in (6, 7, 8):
        return "夏"
    if month in (9, 10, 11):
        return "秋"
    return "冬"
