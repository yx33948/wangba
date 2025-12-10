"""Device tracker platform for netcafe automation."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NetcafeUpdateCoordinator
from .scanner import DeviceData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker for netcafe automation."""
    coordinators: dict[str, NetcafeUpdateCoordinator] = hass.data[DOMAIN].get(
        "coordinators", {}
    )
    
    _LOGGER.info("🔍 Device tracker setup: found %d coordinators", len(coordinators))
    
    if not coordinators:
        _LOGGER.warning("⚠️ No coordinators found, skipping device_tracker setup")
        return
    
    # Update entity registry to ensure entities are under the correct device
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import device_registry as dr
    
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    
    # Get or create the main hub device
    hub_device = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "netcafe_hub")},
        name="网吧自动化中心",
        model="Automation Hub",
        manufacturer="网吧自动化",
        sw_version="2.0.0",
    )
    
    _LOGGER.info("📱 Hub device: %s (id: %s)", hub_device.name, hub_device.id)
    
    entities = []
    for entity_id, coord in coordinators.items():
        # Check if entity already exists
        existing_entity = entity_reg.async_get(entity_id)
        if existing_entity:
            _LOGGER.info("🔄 Updating existing entity: %s", entity_id)
            # Force update entity to use the hub device
            entity_reg.async_update_entity(
                entity_id,
                device_id=hub_device.id,  # Set to hub device
            )
            _LOGGER.info("✅ Updated %s to hub device %s", entity_id, hub_device.id)
        else:
            _LOGGER.info("🆕 Creating new entity: %s", entity_id)
        
        entities.append(NetcafeDeviceTracker(coord, entity_id))
    
    if entities:
        async_add_entities(entities, True)
        _LOGGER.info("✅ Added %d device_tracker entities under netcafe_hub", len(entities))
    else:
        _LOGGER.warning("⚠️ No entities to add")


class NetcafeDeviceTracker(CoordinatorEntity, ScannerEntity):
    """Representation of a netcafe device tracker."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(self, coordinator: NetcafeUpdateCoordinator, entity_id: str) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self.device: DeviceData = coordinator.device
        self.entity_id = entity_id
        
        # Use IP-based unique_id
        ip_slug = self.device.ip_address.replace(".", "_")
        self._attr_unique_id = f"{DOMAIN}_{ip_slug}"
        
        # Use IP-based name
        self._attr_name = f"网吧电脑 {self.device.ip_address}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info - all device_tracker entities under the main integration device."""
        return {
            "identifiers": {(DOMAIN, "netcafe_hub")},
            "name": "网吧自动化中心",
            "model": "Automation Hub",
            "manufacturer": "网吧自动化",
            "sw_version": "2.0.0",
        }

    @property
    def ip_address(self) -> str | None:
        """Return IP address."""
        return self.device.ip_address

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected."""
        return self.coordinator.is_reachable

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
