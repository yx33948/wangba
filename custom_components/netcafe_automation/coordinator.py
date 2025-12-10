"""Update coordinator for Netcafe Automation."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .scanner import DeviceData

_LOGGER = logging.getLogger(__name__)


class NetcafeUpdateCoordinator(DataUpdateCoordinator[bool]):
    """Update coordinator for Netcafe device tracker."""

    def __init__(self, hass: HomeAssistant, device: DeviceData) -> None:
        """Initialize update coordinator."""
        self.device = device
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {device.title}",
            update_interval=None,  # Manual updates via scanner
        )

    @property
    def is_reachable(self) -> bool:
        """Return if device is reachable."""
        if self.device._reachable:
            return True
        
        if self.device._last_seen:
            now = dt_util.utcnow()
            time_since_seen = now - self.device._last_seen
            return time_since_seen < self.device.consider_home
        
        return False

    async def _async_update_data(self) -> bool:
        """Fetch data from API endpoint."""
        return self.is_reachable
