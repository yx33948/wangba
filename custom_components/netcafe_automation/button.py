"""Button platform for netcafe automation."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HUB_MANUFACTURER,
    HUB_MODEL,
    HUB_NAME,
    SERVICE_CLEAR_ALL_DEVICE_TRACKERS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button platform for one config entry."""
    async_add_entities([NetcafeClearAllDataButton(hass, config_entry)])


class NetcafeClearAllDataButton(ButtonEntity):
    """One-click cleanup button for device_tracker entities."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:delete-sweep"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the cleanup button."""
        self.hass = hass
        self._entry_id = config_entry.entry_id
        self._attr_unique_id = f"{DOMAIN}_{self._entry_id}_clear_all_device_trackers"
        self._attr_name = "一键清除所有device_tracker"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"hub_{self._entry_id}")},
            name=HUB_NAME,
            model=HUB_MODEL,
            manufacturer=HUB_MANUFACTURER,
            sw_version="3.0.0",
        )

    async def async_press(self) -> None:
        """Clear all netcafe device_tracker entities and persisted sources."""
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_CLEAR_ALL_DEVICE_TRACKERS,
            {},
            blocking=True,
        )
