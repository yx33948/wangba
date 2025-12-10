"""Sensor platform for netcafe automation."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SEASON_SUMMER, SEASON_WINTER, SEASON_SPRING_AUTUMN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor for netcafe automation."""
    # Create season sensor
    season_sensor = NetcafeSeasonSensor(hass, config_entry)
    async_add_entities([season_sensor], True)
    _LOGGER.info("Created netcafe season sensor")


class NetcafeSeasonSensor(SensorEntity):
    """Representation of netcafe season sensor."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_icon = "mdi:weather-partly-cloudy"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._config_entry = config_entry
        
        # Use fixed entity_id so it's easy to reference
        self._attr_unique_id = f"{DOMAIN}_season"
        self._attr_name = "网吧季节"
        self.entity_id = "sensor.netcafe_season"  # Fixed entity ID
        self._attr_native_value = self._calculate_season()
        
        # Update at midnight every day
        async_track_time_change(
            hass, self._async_update_season, hour=0, minute=0, second=0
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info - all entities under one device."""
        return {
            "identifiers": {(DOMAIN, "netcafe_hub")},
            "name": "网吧自动化中心",
            "model": "Automation Hub",
            "manufacturer": "网吧自动化",
            "sw_version": "2.0.0",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        now = dt_util.now()
        return {
            "month": now.month,
            "day": now.day,
            "season_name_cn": self._get_season_name_cn(self._attr_native_value),
            "last_update": now.isoformat(),
        }

    def _calculate_season(self) -> str:
        """Calculate current season based on date."""
        now = dt_util.now()
        month = now.month
        day = now.day
        
        # 季节划分（北半球中国标准）：
        # 春季：3月1日 - 5月31日
        # 夏季：6月1日 - 8月31日
        # 秋季：9月1日 - 11月30日
        # 冬季：12月1日 - 2月28/29日
        
        if month in (6, 7, 8):
            return SEASON_SUMMER
        elif month in (12, 1, 2):
            return SEASON_WINTER
        elif month in (3, 4, 5):
            return SEASON_SPRING_AUTUMN  # 春季
        else:  # 9, 10, 11
            return SEASON_SPRING_AUTUMN  # 秋季

    def _get_season_name_cn(self, season: str) -> str:
        """Get Chinese season name."""
        if season == SEASON_SUMMER:
            return "夏季"
        elif season == SEASON_WINTER:
            return "冬季"
        elif season == SEASON_SPRING_AUTUMN:
            now = dt_util.now()
            if now.month in (3, 4, 5):
                return "春季"
            else:
                return "秋季"
        return "未知"

    async def _async_update_season(self, now: datetime) -> None:
        """Update season at midnight."""
        new_season = self._calculate_season()
        if new_season != self._attr_native_value:
            _LOGGER.info("Season changed from %s to %s", self._attr_native_value, new_season)
            self._attr_native_value = new_season
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._attr_native_value = self._calculate_season()
        self.async_write_ha_state()
        _LOGGER.info("Season sensor initialized: %s", self._attr_native_value)
