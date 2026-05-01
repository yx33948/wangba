"""Device tracker platform for netcafe automation."""

from __future__ import annotations

import logging

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, HUB_MANUFACTURER, HUB_MODEL, HUB_NAME
from .coordinator import NetcafeUpdateCoordinator
from .scanner import DeviceData

_LOGGER = logging.getLogger(__name__)


def _ip_slug(ip_address: str) -> str:
    """Build slug from ip address."""
    return ip_address.replace(".", "_")


def _build_unique_id(config_entry_id: str, ip_address: str) -> str:
    """Build unique id for device_tracker entity."""
    return f"{DOMAIN}_{config_entry_id}_{_ip_slug(ip_address)}"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker for netcafe automation."""
    # 获取该条目的 rooms_data，只处理属于该条目的设备
    rooms_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
    coordinators: dict[str, NetcafeUpdateCoordinator] = hass.data[DOMAIN].get(
        "coordinators", {}
    )

    _LOGGER.info("Device tracker setup for entry %s: found %d rooms",
                 config_entry.entry_id, len(rooms_data))

    if not rooms_data:
        _LOGGER.warning("No rooms data found for entry %s", config_entry.entry_id)
        return

    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import device_registry as dr

    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    hub_device = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, f"hub_{config_entry.entry_id}")},
        name=HUB_NAME,
        model=HUB_MODEL,
        manufacturer=HUB_MANUFACTURER,
        sw_version="3.0.0",
    )

    _LOGGER.info("Hub device: %s (id: %s)", hub_device.name, hub_device.id)

    # 只为属于该条目的设备创建实体
    entities = []
    entity_ids_to_add = set()

    for room_name, room_config in rooms_data.items():
        for computer in room_config.get("computers", []):
            entity_id = computer.get("entity_id")
            if entity_id and entity_id in coordinators:
                entity_ids_to_add.add(entity_id)

    _LOGGER.info("Found %d device trackers to add for this entry", len(entity_ids_to_add))

    for entity_id in entity_ids_to_add:
        coord = coordinators[entity_id]
        unique_id = _build_unique_id(config_entry.entry_id, coord.device.ip_address)
        existing_entity_id = entity_reg.async_get_entity_id(
            "device_tracker", DOMAIN, unique_id
        )
        existing_entity = entity_reg.async_get(existing_entity_id or entity_id)
        if existing_entity:
            _LOGGER.debug(
                "Entity already exists: %s, updating device_id to %s",
                existing_entity.entity_id,
                hub_device.id,
            )
            # 更新已存在实体的 device_id，使其归集到 Hub 设备下
            entity_reg.async_update_entity(
                existing_entity.entity_id,
                device_id=hub_device.id,
            )
            # 仍然需要添加实体对象，否则实体不会工作
        else:
            _LOGGER.debug("Creating new entity: %s", entity_id)

        entities.append(NetcafeDeviceTracker(coord, entity_id, config_entry.entry_id))

    if entities:
        async_add_entities(entities, True)
        _LOGGER.info("Added %d device_tracker entities for entry %s", len(entities), config_entry.entry_id)
    else:
        _LOGGER.warning("No entities to add for entry %s", config_entry.entry_id)


class NetcafeDeviceTracker(CoordinatorEntity, ScannerEntity):
    """Representation of a netcafe device tracker."""

    _attr_has_entity_name = False  # 改为 False，使用完整名称
    _attr_should_poll = False

    def __init__(
        self, 
        coordinator: NetcafeUpdateCoordinator, 
        entity_id: str,
        config_entry_id: str,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self.device: DeviceData = coordinator.device
        self._config_entry_id = config_entry_id

        object_id = entity_id.split(".", 1)[1] if "." in entity_id else entity_id
        self._attr_suggested_object_id = object_id
        self._attr_unique_id = _build_unique_id(config_entry_id, self.device.ip_address)
        
        # 使用完整名称
        ip_last_octet = self.device.ip_address.split('.')[-1]
        if self.device.room_name:
            self._attr_name = f"{self.device.room_name}{ip_last_octet}"
        else:
            self._attr_name = f"电脑 {self.device.ip_address}"
        
        # 关键：将实体归集到 Hub 设备下
        # 提供完整的 device_info，确保实体正确关联到设备
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"hub_{config_entry_id}")},
            name=HUB_NAME,
            model=HUB_MODEL,
            manufacturer=HUB_MANUFACTURER,
            sw_version="3.0.0",
        )

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for entity registry."""
        return self._attr_unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return hub device info to bind entities under integration device."""
        return self._attr_device_info

    @property
    def ip_address(self) -> str | None:
        """Return IP address."""
        return self.device.ip_address

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose scanner diagnostics for tuning offline detection."""
        return {
            "probe_state": self.device._probe_state,
            "last_probe_method": self.device._last_probe_method or None,
            "consecutive_failures": self.device._consecutive_failures,
            "last_seen": self.device._last_seen.isoformat() if self.device._last_seen else None,
            "last_ping_ok_at": self.device._last_ping_ok_at.isoformat() if self.device._last_ping_ok_at else None,
            "last_retry_failed_at": self.device._last_retry_failed_at.isoformat() if self.device._last_retry_failed_at else None,
        }

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected."""
        if self.hass.data.get(DOMAIN, {}).get("automation_paused"):
            return False
        return self.coordinator.is_reachable

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
