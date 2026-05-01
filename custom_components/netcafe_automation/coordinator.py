"""Update coordinator for Netcafe Automation."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .scanner import DeviceData

_LOGGER = logging.getLogger(__name__)


class NetcafeUpdateCoordinator(DataUpdateCoordinator[bool]):
    """Update coordinator for Netcafe device tracker."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device: DeviceData,
    ) -> None:
        """Initialize update coordinator."""
        self.device = device
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {device.title}",
            update_interval=None,  # Manual updates via scanner
            config_entry=config_entry,
        )

    @property
    def is_reachable(self) -> bool:
        """Return if device is reachable."""
        return self.device._reachable

    async def _async_update_data(self) -> bool:
        """Fetch data from API endpoint."""
        return self.is_reachable
