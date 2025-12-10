"""网吧智能自动化集成"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.device_tracker import CONF_CONSIDER_HOME
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICES, CONF_IP_ADDRESS, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
import voluptuous as vol

from .const import (
    CONF_CSV_CONTENT,
    CONF_ENABLE_AUTOMATION,
    DEFAULT_CONSIDER_HOME,
    DOMAIN,
    FIELD_CLIMATE_ENTITY,
    FIELD_COVER_ENTITY,
    FIELD_ENTITY_ID,
    FIELD_IP_ADDRESS,
    FIELD_LIGHT_ENTITY,
    FIELD_ROOM_NAME,
    PREFIX_CLIMATE,
    PREFIX_COVER,
    PREFIX_DEVICE_TRACKER,
    PREFIX_INPUT_BOOLEAN,
    PREFIX_LIGHT,
    PROBE_INTERVAL,
    SERVICE_EXPORT_CSV,
    SERVICE_IMPORT_CSV_DIRECT,
    SERVICE_IMPORT_CSV_FROM_FILE,
    SERVICE_RELOAD_CSV,
)
from .coordinator import NetcafeUpdateCoordinator
from .room_manager import RoomManager
from .scanner import (
    DeviceData,
    Scanner,
    ScannerException,
    async_get_scanner,
    async_update_devices,
)
from .storage_manager import StorageManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]
TRACKER_INTERVAL = timedelta(seconds=PROBE_INTERVAL)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the netcafe_automation component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize device tracker storage
    devices: dict[str, DeviceData] = {}
    hass.data[DOMAIN][CONF_DEVICES] = devices
    
    # Initialize scanner
    try:
        scanner: Scanner = await async_get_scanner(hass)
        hass.data[DOMAIN]["scanner"] = scanner
    except ScannerException as error:
        _LOGGER.warning("Scanner not available yet: %s", error)
        # Don't fail setup, scanner will be initialized when entry is added

    async def _update_devices(*_) -> None:
        """Update reachability for all tracked devices."""
        scanner = hass.data[DOMAIN].get("scanner")
        coordinators = hass.data[DOMAIN].get("coordinators", {})
        
        if scanner and devices:
            await async_update_devices(hass, scanner, devices)
            
            # Trigger coordinator updates to refresh device_tracker states
            for entity_id, coordinator in coordinators.items():
                if entity_id in devices:
                    coordinator.async_set_updated_data(coordinator.is_reachable)
                    _LOGGER.debug(
                        "Updated %s: reachable=%s", 
                        entity_id, 
                        coordinator.is_reachable
                    )

    # Track time interval for device updates
    hass.data[DOMAIN]["update_listener"] = async_track_time_interval(
        hass, _update_devices, TRACKER_INTERVAL, cancel_on_shutdown=True
    )

    async def reload_from_csv_service(call: ServiceCall) -> None:
        """Handle reload from CSV service call - hot reload without full restart."""
        _LOGGER.info("🔄 Hot reloading configuration from CSV files...")
        
        # Hot reload all entries in parallel
        entries = hass.config_entries.async_entries(DOMAIN)
        reload_tasks = [
            hass.config_entries.async_reload(entry.entry_id)
            for entry in entries
        ]
        
        if reload_tasks:
            await asyncio.gather(*reload_tasks, return_exceptions=True)
            _LOGGER.info("✅ All entries hot reloaded successfully")
        else:
            _LOGGER.warning("No entries found to reload")

    async def export_csv_service(call: ServiceCall) -> None:
        """Handle export CSV service call."""
        filename = call.data.get("filename", "netcafe_rooms")
        
        # Ensure www directory exists
        www_path = hass.config.path("www")
        await hass.async_add_executor_job(_ensure_directory, www_path)
        
        # Get all room managers and export their configuration
        rooms_data = {}
        for entry_id in list(hass.data[DOMAIN].keys()):
            if isinstance(hass.data[DOMAIN][entry_id], RoomManager):
                room_manager: RoomManager = hass.data[DOMAIN][entry_id]
                rooms_data.update(room_manager.rooms)
        
        if not rooms_data:
            _LOGGER.warning("No rooms data available to export")
            return
        
        # Generate CSV content
        csv_content = _generate_csv_from_rooms(rooms_data)
        
        # Write to file
        output_path = f"{www_path}/{filename}.csv"
        await hass.async_add_executor_job(_write_file, output_path, csv_content)
        
        _LOGGER.info("CSV exported to %s (accessible at /local/%s.csv)", output_path, filename)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD_CSV,
        reload_from_csv_service,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_CSV,
        export_csv_service,
        schema=vol.Schema({
            vol.Optional("filename", default="netcafe_rooms"): cv.string,
        }),
    )

    async def import_csv_from_file_service(call: ServiceCall) -> None:
        """Handle import CSV from file service call - File-based storage."""
        filename = call.data.get("filename", "netcafe_import.csv")
        
        # Read from www directory
        www_path = hass.config.path("www")
        import_path = f"{www_path}/{filename}"
        
        try:
            # Read CSV file
            csv_content = await hass.async_add_executor_job(_read_file, import_path)
            
            if not csv_content:
                _LOGGER.error("CSV file is empty: %s", import_path)
                return
            
            _LOGGER.info("CSV imported from %s", import_path)
            
            # Save to file storage for all config entries
            entries = hass.config_entries.async_entries(DOMAIN)
            for entry in entries:
                storage = StorageManager(hass, entry.entry_id)
                if await storage.async_save_csv(csv_content):
                    _LOGGER.info("✅ CSV saved to file storage for entry: %s", entry.title)
                else:
                    _LOGGER.error("Failed to save CSV for entry: %s", entry.title)
            
            # Reload all entries
            for entry in entries:
                await hass.config_entries.async_reload(entry.entry_id)
            
            _LOGGER.info("All entries reloaded with new CSV configuration")
            
        except FileNotFoundError:
            _LOGGER.error("CSV file not found: %s", import_path)
        except Exception as err:
            _LOGGER.error("Error importing CSV: %s", err)

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_CSV_FROM_FILE,
        import_csv_from_file_service,
        schema=vol.Schema({
            vol.Optional("filename", default="netcafe_import.csv"): cv.string,
        }),
    )

    async def import_csv_direct_service(call: ServiceCall) -> None:
        """Handle import CSV directly from content (no file) - File-based storage."""
        csv_content = call.data.get("csv_content", "")
        
        if not csv_content:
            _LOGGER.error("CSV content is empty")
            return
        
        _LOGGER.info("Importing CSV directly from content (%d bytes)", len(csv_content))
        
        try:
            # Get all config entries
            entries = hass.config_entries.async_entries(DOMAIN)
            
            if not entries:
                _LOGGER.error("No netcafe_automation config entries found")
                return
            
            for entry in entries:
                # Initialize storage manager for this entry
                storage = StorageManager(hass, entry.entry_id)
                
                # Save CSV to file instead of config_entry
                if await storage.async_save_csv(csv_content):
                    _LOGGER.info("✅ CSV saved to file for entry: %s", entry.title)
                else:
                    _LOGGER.error("❌ Failed to save CSV for entry: %s", entry.title)
                    continue
            
            # Hot reload mechanism - update without full reload
            _LOGGER.info("🔄 Starting hot reload of all entries...")
            
            for entry in entries:
                try:
                    # Get room manager for this entry
                    room_manager = hass.data[DOMAIN].get(entry.entry_id)
                    
                    if room_manager and hasattr(room_manager, 'async_reload'):
                        # Direct reload of room manager (faster)
                        await room_manager.async_reload()
                        _LOGGER.info("✅ Hot reloaded room manager: %s", entry.title)
                    else:
                        # Fallback to full entry reload
                        await hass.config_entries.async_reload(entry.entry_id)
                        _LOGGER.info("✅ Reloaded entry: %s", entry.title)
                        
                except Exception as err:
                    _LOGGER.error("Failed to reload %s: %s", entry.title, err)
                    # Try full reload as fallback
                    try:
                        await hass.config_entries.async_reload(entry.entry_id)
                        _LOGGER.info("✅ Fallback reload succeeded: %s", entry.title)
                    except Exception as fallback_err:
                        _LOGGER.error("Fallback reload also failed: %s", fallback_err)
            
            _LOGGER.info("✅ All entries processed with new CSV configuration")
            _LOGGER.info("CSV content preview: %s...", csv_content[:100])
            
        except Exception as err:
            _LOGGER.error("❌ Error importing CSV: %s", err, exc_info=True)

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_CSV_DIRECT,
        import_csv_direct_service,
        schema=vol.Schema({
            vol.Required("csv_content"): cv.string,
        }),
    )

    async def get_storage_info_service(call: ServiceCall) -> None:
        """Get storage file information for debugging."""
        entries = hass.config_entries.async_entries(DOMAIN)
        
        for entry in entries:
            storage = StorageManager(hass, entry.entry_id)
            info = storage.get_storage_info()
            _LOGGER.info("Storage info for '%s':", entry.title)
            _LOGGER.info("  Directory: %s", info["storage_dir"])
            for file_type, file_info in info["files"].items():
                if file_info["exists"]:
                    _LOGGER.info("  %s: %s (%d bytes)", 
                                 file_type, file_info["path"], file_info["size"])
                else:
                    _LOGGER.info("  %s: %s (not found)", file_type, file_info["path"])

    hass.services.async_register(
        DOMAIN,
        "get_storage_info",
        get_storage_info_service,
        schema=vol.Schema({}),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up netcafe_automation from a config entry - File-based storage with hot reload."""
    _LOGGER.debug("Setting up netcafe_automation config entry: %s", entry.title)

    # Copy blueprint to HA blueprints directory
    await hass.async_add_executor_job(_copy_blueprint_to_ha, hass)
    
    # Register hub device for integration
    from homeassistant.helpers import device_registry as dr
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "netcafe_hub")},
        name="网吧自动化中心",
        model="Automation Hub",
        manufacturer="网吧自动化",
        sw_version="2.0.0",
    )

    # Initialize storage manager
    storage = StorageManager(hass, entry.entry_id)
    
    # Try to load CSV from file first, fallback to config_entry for migration
    csv_content = await storage.async_load_csv()
    
    if not csv_content:
        # Migration: check if CSV is in old config_entry format
        _LOGGER.info("CSV not found in file storage, checking config_entry for migration")
        csv_content = entry.data.get(CONF_CSV_CONTENT, "")
        
        if csv_content:
            # Migrate to file storage
            _LOGGER.info("Migrating CSV from config_entry to file storage")
            if await storage.async_save_csv(csv_content):
                _LOGGER.info("✅ CSV migrated to file storage successfully")
            else:
                _LOGGER.warning("Failed to migrate CSV to file storage")
    
    if not csv_content:
        _LOGGER.warning("No CSV content found in file or config_entry")
    
    # Store storage manager in hass.data for later use
    hass.data[DOMAIN].setdefault("storage_managers", {})[entry.entry_id] = storage
    
    enable_automation = entry.data.get(CONF_ENABLE_AUTOMATION, True)

    # Ensure scanner is available
    if "scanner" not in hass.data[DOMAIN]:
        try:
            scanner: Scanner = await async_get_scanner(hass)
            hass.data[DOMAIN]["scanner"] = scanner
        except ScannerException as error:
            raise PlatformNotReady(error)

    # Parse CSV and create room manager
    room_manager = RoomManager(hass, entry)
    
    try:
        rooms_data = await hass.async_add_executor_job(
            _parse_csv_content, csv_content
        )
        
        # Create device trackers for computers
        devices = hass.data[DOMAIN][CONF_DEVICES]
        coordinators = hass.data[DOMAIN].setdefault("coordinators", {})
        
        for room_name, room_config in rooms_data.items():
            for computer in room_config.get("computers", []):
                entity_id = computer["entity_id"]
                ip_address = computer["ip_address"]
                
                if entity_id not in devices:
                    # Create device data
                    device = DeviceData(
                        ip_address=ip_address,
                        consider_home=timedelta(seconds=DEFAULT_CONSIDER_HOME),
                        title=f"{room_name} - {ip_address}",
                    )
                    devices[entity_id] = device
                    
                    _LOGGER.info("📱 Creating device_tracker: %s for IP: %s", entity_id, ip_address)
                    
                    # Create coordinator
                    coordinator = NetcafeUpdateCoordinator(hass, device)
                    await coordinator.async_config_entry_first_refresh()
                    coordinators[entity_id] = coordinator
        
        await room_manager.async_setup_rooms(rooms_data, enable_automation)
        
        hass.data[DOMAIN][entry.entry_id] = room_manager
        
        # Forward setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        
        _LOGGER.info(
            "Successfully set up netcafe_automation with %d rooms and %d devices",
            len(rooms_data),
            len(devices)
        )
        
    except Exception as err:
        _LOGGER.error("Error setting up netcafe_automation: %s", err)
        return False

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    else:
        unload_ok = True

    if unload_ok:
        room_manager = hass.data[DOMAIN].pop(entry.entry_id, None)
        if room_manager:
            await room_manager.async_cleanup()

    return unload_ok


def _parse_csv_content(csv_content: str) -> dict[str, dict[str, Any]]:
    """Parse CSV content and organize by room - v3.0 simplified format."""
    rooms: dict[str, dict[str, Any]] = {}
    
    if not csv_content:
        return rooms
    
    # Remove BOM if present
    if csv_content.startswith('\ufeff'):
        csv_content = csv_content[1:]
        _LOGGER.debug("Removed BOM from CSV content")
    
    # Try to detect delimiter (comma or tab)
    delimiter = ','
    first_line = csv_content.split('\n')[0] if '\n' in csv_content else csv_content
    
    comma_count = first_line.count(',')
    tab_count = first_line.count('\t')
    
    if tab_count > comma_count:
        delimiter = '\t'
        _LOGGER.debug("Detected tab delimiter in CSV")
    
    csv_file = io.StringIO(csv_content)
    reader = csv.DictReader(csv_file, delimiter=delimiter)
    
    # Strip whitespace from field names
    if reader.fieldnames:
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
    
    for row in reader:
        # Strip keys and values
        cleaned_row = {k.strip() if k else k: v.strip() if v else v for k, v in row.items()}
        room_name = cleaned_row.get(FIELD_ROOM_NAME, "")
        ip_address = cleaned_row.get(FIELD_IP_ADDRESS, "")
        
        # v3.0: Optional entity fields
        climate_entity = cleaned_row.get(FIELD_CLIMATE_ENTITY, "")
        light_entity = cleaned_row.get(FIELD_LIGHT_ENTITY, "")
        cover_entity = cleaned_row.get(FIELD_COVER_ENTITY, "")
        
        # Backwards compatibility: check old entity_id field
        legacy_entity_id = cleaned_row.get(FIELD_ENTITY_ID, "")
        
        if not room_name:
            continue
        
        # Initialize room if not exists
        if room_name not in rooms:
            rooms[room_name] = {
                "computers": [],
                "climates": [],
                "lights": [],
                "covers": [],
                "dnd_switch": None,
            }
        
        # v3.0: Process IP address - auto-create device_tracker
        if ip_address:
            # Generate device_tracker entity_id from IP
            ip_slug = ip_address.replace(".", "_")
            device_tracker_id = f"device_tracker.netcafe_{ip_slug}"
            
            rooms[room_name]["computers"].append({
                "entity_id": device_tracker_id,
                "ip_address": ip_address,
            })
            _LOGGER.info("✅ Auto-generated device_tracker: %s for IP: %s in room: %s", device_tracker_id, ip_address, room_name)
        
        # Process optional entities
        if climate_entity:
            # Support semicolon-separated multiple entities
            for entity in climate_entity.split(';'):
                entity = entity.strip()
                if entity and entity.startswith(PREFIX_CLIMATE):
                    if entity not in rooms[room_name]["climates"]:
                        rooms[room_name]["climates"].append(entity)
        
        if light_entity:
            # Support semicolon-separated multiple entities
            for entity in light_entity.split(';'):
                entity = entity.strip()
                if entity and entity.startswith(PREFIX_LIGHT):
                    if entity not in rooms[room_name]["lights"]:
                        rooms[room_name]["lights"].append(entity)
        
        if cover_entity:
            # Support semicolon-separated multiple entities
            for entity in cover_entity.split(';'):
                entity = entity.strip()
                if entity and entity.startswith(PREFIX_COVER):
                    if entity not in rooms[room_name]["covers"]:
                        rooms[room_name]["covers"].append(entity)
        
        # Backwards compatibility: process legacy entity_id field
        if legacy_entity_id:
            if legacy_entity_id.startswith(PREFIX_DEVICE_TRACKER):
                # Legacy format: use provided entity_id
                rooms[room_name]["computers"].append({
                    "entity_id": legacy_entity_id,
                    "ip_address": ip_address,
                })
            elif legacy_entity_id.startswith(PREFIX_CLIMATE):
                if legacy_entity_id not in rooms[room_name]["climates"]:
                    rooms[room_name]["climates"].append(legacy_entity_id)
            elif legacy_entity_id.startswith(PREFIX_LIGHT):
                if legacy_entity_id not in rooms[room_name]["lights"]:
                    rooms[room_name]["lights"].append(legacy_entity_id)
            elif legacy_entity_id.startswith(PREFIX_COVER):
                if legacy_entity_id not in rooms[room_name]["covers"]:
                    rooms[room_name]["covers"].append(legacy_entity_id)
            elif legacy_entity_id.startswith(PREFIX_INPUT_BOOLEAN) and "dnd" in legacy_entity_id:
                rooms[room_name]["dnd_switch"] = legacy_entity_id
    
    _LOGGER.info("Parsed %d rooms with simplified v3.0 format", len(rooms))
    return rooms


def _generate_csv_from_rooms(rooms_data: dict[str, dict[str, Any]]) -> str:
    """Generate CSV content from rooms data."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([FIELD_ROOM_NAME, FIELD_ENTITY_ID, FIELD_IP_ADDRESS])
    
    # Write rows
    for room_name, room_config in rooms_data.items():
        # Export computers with IP addresses
        for computer in room_config.get("computers", []):
            writer.writerow([
                room_name,
                computer["entity_id"],
                computer.get("ip_address", ""),
            ])
        
        # Export climates
        for climate_id in room_config.get("climates", []):
            writer.writerow([room_name, climate_id, ""])
        
        # Export lights
        for light_id in room_config.get("lights", []):
            writer.writerow([room_name, light_id, ""])
        
        # Export covers
        for cover_id in room_config.get("covers", []):
            writer.writerow([room_name, cover_id, ""])
        
        # Export DND switch if custom
        dnd_switch = room_config.get("dnd_switch")
        if dnd_switch and not dnd_switch.startswith(f"input_boolean.dnd_"):
            writer.writerow([room_name, dnd_switch, ""])
    
    return output.getvalue()


def _ensure_directory(path: str) -> None:
    """Ensure directory exists."""
    import os
    os.makedirs(path, exist_ok=True)


def _write_file(path: str, content: str) -> None:
    """Write content to file."""
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def _read_file(path: str) -> str:
    """Read content from file."""
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def _copy_blueprint_to_ha(hass: HomeAssistant) -> None:
    """Copy blueprint file to Home Assistant blueprints directory."""
    import os
    import shutil
    
    # Source blueprint file
    source_blueprint = os.path.join(
        os.path.dirname(__file__),
        "blueprints",
        "netcafe_room_automation.yaml"
    )
    
    # Destination in HA blueprints directory
    blueprints_dir = hass.config.path("blueprints", "automation", "netcafe_automation")
    dest_blueprint = os.path.join(blueprints_dir, "netcafe_room_automation.yaml")
    
    try:
        # Create directory if not exists
        os.makedirs(blueprints_dir, exist_ok=True)
        
        # Copy blueprint file
        shutil.copy2(source_blueprint, dest_blueprint)
        _LOGGER.info("Blueprint copied to %s", dest_blueprint)
    except Exception as err:
        _LOGGER.error("Error copying blueprint: %s", err)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        # Migration code here if needed in future
        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry)

    return True
