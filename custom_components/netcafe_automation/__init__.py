"""智慧网吧集成 - 简化版，仅支持IP设备跟踪"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_DEVICES, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
import voluptuous as vol

from .const import (
    CONF_CSV_CONTENT,
    DEFAULT_CONSIDER_HOME,
    DOMAIN,
    FAST_ONLINE_INTERVAL,
    FIELD_IP_ADDRESS,
    FIELD_ROOM_NAME,
    HUB_MANUFACTURER,
    HUB_MODEL,
    HUB_NAME,
    SERVICE_CLEAR_ALL_DEVICE_TRACKERS,
    SERVICE_EXPORT_CSV,
    SERVICE_CLEAR_ALL_DATA,
    SERVICE_IMPORT_CSV_DIRECT,
    SERVICE_IMPORT_CSV_FROM_FILE,
    SERVICE_RELOAD_CSV,
)
from .coordinator import NetcafeUpdateCoordinator
from .scanner import (
    DeviceData,
    PROBE_STATE_OFFLINE,
    Scanner,
    ScannerException,
    async_get_scanner,
    async_update_devices,
)
from .storage_manager import StorageManager
from .license_manager import (
    get_license_manager,
    is_license_valid,
    get_license_info,
    LicenseManager
)
from .notifications import async_check_daily_brief, async_notify_device_transition
from .room_control import (
    async_initialize_room_control_runtime,
    async_process_room_automation,
    async_reset_room_control_runtime,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.BUTTON, Platform.SENSOR]
TRACKER_INTERVAL = timedelta(seconds=FAST_ONLINE_INTERVAL)
LICENSE_CHECK_INTERVAL = timedelta(hours=6)  # 低频兜底检查，避免网络抖动导致误判

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def _handle_device_notification_transitions(
    hass: HomeAssistant,
    devices_ref: dict[str, DeviceData],
    previous_states: dict[str, dict[str, Any]],
) -> None:
    """Emit offline/recovery notifications after one device scan."""
    for entity_id, device in devices_ref.items():
        previous = previous_states.get(entity_id, {})
        previous_probe = previous.get("probe_state")
        previous_reachable = bool(previous.get("reachable"))
        current_probe = getattr(device, "_probe_state", "")
        current_reachable = bool(getattr(device, "_reachable", False))
        if current_probe == PROBE_STATE_OFFLINE and previous_reachable and previous_probe != PROBE_STATE_OFFLINE:
            await async_notify_device_transition(hass, config={}, device=device, is_offline=True)
        elif previous_probe == PROBE_STATE_OFFLINE and current_reachable:
            await async_notify_device_transition(hass, config={}, device=device, is_offline=False)


async def _daily_brief_tick(_now, hass: HomeAssistant) -> None:
    """Check and send the daily brief when due."""
    try:
        await async_check_daily_brief(hass)
    except Exception as err:
        _LOGGER.warning("检查每日日报任务失败: %s", err)


async def _async_clear_entry_data(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clear all runtime/storage/entity data for one config entry."""
    storage = StorageManager(hass, entry.entry_id)
    await storage.async_delete_all()

    devices = hass.data[DOMAIN].get(CONF_DEVICES, {})
    coordinators = hass.data[DOMAIN].get("coordinators", {})
    rooms_data = hass.data[DOMAIN].get(entry.entry_id, {})

    for room_config in rooms_data.values():
        for computer in room_config.get("computers", []):
            entity_id = computer.get("entity_id")
            if not entity_id:
                continue
            coordinators.pop(entity_id, None)
            devices.pop(entity_id, None)

    hass.data[DOMAIN][entry.entry_id] = {}

    if CONF_CSV_CONTENT in entry.data:
        new_data = dict(entry.data)
        new_data.pop(CONF_CSV_CONTENT, None)
        hass.config_entries.async_update_entry(entry, data=new_data)

    entity_reg = er.async_get(hass)
    to_remove = [
        ent.entity_id
        for ent in entity_reg.entities.values()
        if ent.config_entry_id == entry.entry_id and ent.domain == "device_tracker"
    ]
    for entity_id in to_remove:
        entity_reg.async_remove(entity_id)

    _LOGGER.info(
        "Cleared entry %s: removed %d device_tracker entities",
        entry.entry_id,
        len(to_remove),
    )


async def _async_purge_all_netcafe_trackers(hass: HomeAssistant) -> int:
    """Purge all netcafe device_tracker entities, including ungrouped/orphan ones."""
    entity_reg = er.async_get(hass)

    to_remove: list[str] = []
    for ent in entity_reg.entities.values():
        if ent.domain != "device_tracker":
            continue

        unique_id = ent.unique_id or ""
        platform = getattr(ent, "platform", "")
        if (
            ent.entity_id.startswith("device_tracker.netcafe_")
            or unique_id.startswith(f"{DOMAIN}_")
            or platform == DOMAIN
        ):
            to_remove.append(ent.entity_id)

    for entity_id in to_remove:
        entity_reg.async_remove(entity_id)
        if hass.states.get(entity_id) is not None:
            hass.states.async_remove(entity_id)

    devices = hass.data[DOMAIN].get(CONF_DEVICES, {})
    coordinators = hass.data[DOMAIN].get("coordinators", {})

    for entity_id in list(devices):
        if entity_id.startswith("device_tracker.netcafe_"):
            devices.pop(entity_id, None)

    for entity_id in list(coordinators):
        if entity_id.startswith("device_tracker.netcafe_"):
            coordinators.pop(entity_id, None)

    return len(to_remove)


def _build_tracker_unique_id(config_entry_id: str, ip_address: str) -> str:
    """Build the device_tracker unique id used by this integration."""
    return f"{DOMAIN}_{config_entry_id}_{str(ip_address or '').replace('.', '_')}"


def _collect_room_entity_rows(rooms_data: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten room config into comparable entity rows."""
    rows: list[dict[str, str]] = []
    if not isinstance(rooms_data, dict):
        return rows

    for room_config in rooms_data.values():
        if not isinstance(room_config, dict):
            continue
        for computer in room_config.get("computers", []):
            if not isinstance(computer, dict):
                continue
            entity_id = str(computer.get("entity_id") or "").strip()
            ip_address = str(computer.get("ip_address") or "").strip()
            if not entity_id or not ip_address:
                continue
            rows.append(
                {
                    "entity_id": entity_id,
                    "ip_address": ip_address,
                }
            )
    return rows


def _remove_stale_tracker_entities(
    hass: HomeAssistant,
    *,
    config_entry_id: str,
    old_rooms_data: dict[str, Any],
    new_rooms_data: dict[str, Any],
) -> int:
    """Remove device_tracker registry/state entries that disappeared from CSV."""
    entity_reg = er.async_get(hass)
    old_rows = _collect_room_entity_rows(old_rooms_data)
    new_entity_ids = {
        row["entity_id"]
        for row in _collect_room_entity_rows(new_rooms_data)
    }

    removed_count = 0
    for row in old_rows:
        entity_id = row["entity_id"]
        ip_address = row["ip_address"]
        if entity_id in new_entity_ids:
            continue

        unique_id = _build_tracker_unique_id(config_entry_id, ip_address)
        registry_entity_id = entity_reg.async_get_entity_id("device_tracker", DOMAIN, unique_id)
        target_entity_id = registry_entity_id or entity_id

        if target_entity_id and entity_reg.async_get(target_entity_id):
            entity_reg.async_remove(target_entity_id)
            removed_count += 1
            _LOGGER.info(
                "Removed stale device_tracker entity after CSV update: %s (ip=%s)",
                target_entity_id,
                ip_address,
            )

        if target_entity_id and hass.states.get(target_entity_id) is not None:
            hass.states.async_remove(target_entity_id)

    return removed_count


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the netcafe_automation component."""
    hass.data.setdefault(DOMAIN, {})
    
    devices: dict[str, DeviceData] = {}
    hass.data[DOMAIN][CONF_DEVICES] = devices
    
    try:
        scanner: Scanner = await async_get_scanner(hass)
        hass.data[DOMAIN]["scanner"] = scanner
    except ScannerException as error:
        _LOGGER.warning("Scanner not available yet: %s", error)

    # 初始化自动化暂停状态（在卡密检查之后设置，_pause_automation 依赖此字段）
    hass.data[DOMAIN]["automation_paused"] = False

    async def _update_devices(*_) -> None:
        """Update reachability for all tracked devices."""
        if hass.data[DOMAIN].get("automation_paused"):
            return

        scanner = hass.data[DOMAIN].get("scanner")
        coordinators = hass.data[DOMAIN].get("coordinators", {})

        if scanner and devices:
            previous_states = {
                entity_id: {
                    "probe_state": getattr(device, "_probe_state", ""),
                    "reachable": bool(getattr(device, "_reachable", False)),
                }
                for entity_id, device in devices.items()
            }
            await async_update_devices(hass, scanner, devices)
            await _handle_device_notification_transitions(hass, devices, previous_states)

            for entity_id, coordinator in coordinators.items():
                if entity_id in devices:
                    coordinator.async_set_updated_data(coordinator.is_reachable)
            await async_process_room_automation(hass)

    hass.data[DOMAIN]["update_listener"] = async_track_time_interval(
        hass, _update_devices, TRACKER_INTERVAL, cancel_on_shutdown=True
    )

    async def _daily_brief_listener(now) -> None:
        await _daily_brief_tick(now, hass)

    hass.data[DOMAIN]["daily_brief_listener"] = async_track_time_interval(
        hass, _daily_brief_listener, timedelta(minutes=1), cancel_on_shutdown=True
    )

    async def reload_from_csv_service(call: ServiceCall) -> None:
        """Handle reload from CSV service call."""
        _LOGGER.info("Reloading configuration from CSV files...")
        
        entries = hass.config_entries.async_entries(DOMAIN)
        reload_tasks = [
            hass.config_entries.async_reload(entry.entry_id)
            for entry in entries
        ]
        
        if reload_tasks:
            await asyncio.gather(*reload_tasks, return_exceptions=True)
            _LOGGER.info("All entries reloaded successfully")
        else:
            _LOGGER.warning("No entries found to reload")

    async def export_csv_service(call: ServiceCall) -> None:
        """Handle export CSV service call."""
        filename = call.data.get("filename", "netcafe_devices")
        
        www_path = hass.config.path("www")
        await hass.async_add_executor_job(_ensure_directory, www_path)
        
        devices_data = hass.data[DOMAIN].get(CONF_DEVICES, {})
        
        if not devices_data:
            _LOGGER.warning("No devices data available to export")
            return
        
        csv_content = _generate_csv_from_devices(devices_data)
        
        output_path = f"{www_path}/{filename}.csv"
        await hass.async_add_executor_job(_write_file, output_path, csv_content)
        
        _LOGGER.info("CSV exported to %s", output_path)

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
            vol.Optional("filename", default="netcafe_devices"): cv.string,
        }),
    )

    async def import_csv_from_file_service(call: ServiceCall) -> None:
        """Handle import CSV from file service call."""
        filename = call.data.get("filename", "netcafe_import.csv")
        
        www_path = hass.config.path("www")
        import_path = f"{www_path}/{filename}"
        
        try:
            csv_content = await hass.async_add_executor_job(_read_file, import_path)
            
            if not csv_content:
                _LOGGER.error("CSV file is empty: %s", import_path)
                return
            
            _LOGGER.info("CSV imported from %s", import_path)
            
            entries = hass.config_entries.async_entries(DOMAIN)
            for entry in entries:
                storage = StorageManager(hass, entry.entry_id)
                if await storage.async_save_csv(csv_content):
                    _LOGGER.info("CSV saved to file storage for entry: %s", entry.title)
            
            for entry in entries:
                await hass.config_entries.async_reload(entry.entry_id)
            
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
        """Handle import CSV directly from content."""
        csv_content = call.data.get("csv_content", "")
        
        if not csv_content:
            _LOGGER.error("CSV content is empty")
            return
        
        _LOGGER.info("Importing CSV directly from content (%d bytes)", len(csv_content))
        
        try:
            entries = hass.config_entries.async_entries(DOMAIN)
            
            if not entries:
                _LOGGER.error("No netcafe_automation config entries found")
                return
            
            for entry in entries:
                storage = StorageManager(hass, entry.entry_id)
                
                if await storage.async_save_csv(csv_content):
                    _LOGGER.info("CSV saved to file for entry: %s", entry.title)
            
            for entry in entries:
                await hass.config_entries.async_reload(entry.entry_id)
            
            _LOGGER.info("All entries processed with new CSV configuration")
            
        except Exception as err:
            _LOGGER.error("Error importing CSV: %s", err)

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_CSV_DIRECT,
        import_csv_direct_service,
        schema=vol.Schema({
            vol.Required("csv_content"): cv.string,
        }),
    )

    async def clear_all_data_service(call: ServiceCall) -> None:
        """Handle clear all tracked entities/data service call."""
        target_entry_id = call.data.get("entry_id")
        entries = hass.config_entries.async_entries(DOMAIN)

        if target_entry_id:
            entries = [entry for entry in entries if entry.entry_id == target_entry_id]

        if not entries:
            _LOGGER.warning("No matching entries found for clear_all_data")
            return

        for entry in entries:
            await _async_clear_entry_data(hass, entry)

        _LOGGER.info("clear_all_data completed for %d entries", len(entries))

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_ALL_DATA,
        clear_all_data_service,
        schema=vol.Schema({
            vol.Optional("entry_id"): cv.string,
        }),
    )

    async def clear_all_device_trackers_service(call: ServiceCall) -> None:
        """One-click clear all netcafe device_tracker entities and persisted sources."""
        entries = hass.config_entries.async_entries(DOMAIN)

        for entry in entries:
            await _async_clear_entry_data(hass, entry)

        purged_count = await _async_purge_all_netcafe_trackers(hass)

        _LOGGER.info(
            "clear_all_device_trackers completed for %d entries, purged %d trackers",
            len(entries),
            purged_count,
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_ALL_DEVICE_TRACKERS,
        clear_all_device_trackers_service,
        schema=vol.Schema({}),
    )

    # ==================== 卡密验证相关代码 ====================
    _LOGGER.info("初始化卡密验证系统...")
    
    # 初始化卡密管理器 - 传入 hass 以获取正确的存储路径
    license_mgr = get_license_manager(hass)
    # 必须在 executor 中调用，因为内部会发起同步 HTTP 请求
    license_status = await hass.async_add_executor_job(license_mgr.get_license_status)
    
    _LOGGER.info(f"卡密状态: {license_status['message']}")
    if license_status.get("is_valid"):
        _LOGGER.info(f"✓ 卡密验证通过。{license_status['message']}")
    else:
        _LOGGER.warning(
            "ℹ️ 当前未激活或卡密不可用，但后端集成继续加载。卡密改由 1.html 面板管理。\n"
            f"当前状态: {license_status['message']}"
        )
    
    # 设置卡密状态到 hass.data
    hass.data[DOMAIN]["license_status"] = license_status
    hass.data[DOMAIN]["license_manager"] = license_mgr
    
    async def _check_license_callback(*_):
        """定时检查卡密状态"""
        license_mgr = hass.data[DOMAIN].get("license_manager")
        if not license_mgr:
            return

        old_status = hass.data[DOMAIN].get("license_status", {})
        # 必须在 executor 中调用，因为内部会发起同步 HTTP 请求
        new_status = await hass.async_add_executor_job(license_mgr.get_license_status)

        # 更新状态
        hass.data[DOMAIN]["license_status"] = new_status

        # 检查是否即将到期
        if new_status.get('is_expiring_soon') and not old_status.get('is_expiring_soon'):
            _LOGGER.warning(
                f"⚠️ 卡密即将到期！{new_status['message']}"
            )
    
    # 启动低频兜底卡密检查
    hass.data[DOMAIN]["license_check_listener"] = async_track_time_interval(
        hass, 
        _check_license_callback, 
        LICENSE_CHECK_INTERVAL, 
        cancel_on_shutdown=True
    )
    
    # 注册卡密验证服务
    async def activate_license_service(call: ServiceCall) -> None:
        """激活卡密服务"""
        license_key = call.data.get("license_key", "")
        device_id = call.data.get("device_id", "")
        
        if not license_key:
            _LOGGER.error("激活卡密失败：未提供卡密")
            return
        
        license_mgr = hass.data[DOMAIN].get("license_manager")
        if not license_mgr:
            license_mgr = get_license_manager(hass)
            hass.data[DOMAIN]["license_manager"] = license_mgr

        normalized_device_id = await hass.async_add_executor_job(
            license_mgr.get_activation_device_id, device_id
        )
        
        result = await hass.async_add_executor_job(
            license_mgr.activate_license, license_key, normalized_device_id
        )
        
        if result.get("success"):
            _LOGGER.info(f"✓ 卡密激活成功！到期日期：{result.get('expire_date')}")
            hass.data[DOMAIN]["license_status"] = await hass.async_add_executor_job(license_mgr.get_license_status)
            # 如果当前处于暂停状态，激活成功后自动恢复
            if hass.data[DOMAIN].get("automation_paused"):
                _LOGGER.info("卡密激活成功，自动恢复自动化功能")
                await _resume_automation(hass)
            await _reload_inactive_config_entries_after_activation(hass)
        else:
            _LOGGER.error(f"✗ 卡密激活失败：{result.get('error')}")
    
    hass.services.async_register(
        DOMAIN,
        "activate_license",
        activate_license_service,
        schema=vol.Schema({
            vol.Required("license_key"): cv.string,
            vol.Optional("device_id", default=""): cv.string,
        }),
    )
    
    async def get_license_status_service(call: ServiceCall) -> None:
        """获取卡密状态服务"""
        license_mgr = hass.data[DOMAIN].get("license_manager")
        if license_mgr:
            status = await hass.async_add_executor_job(license_mgr.get_license_status)
            _LOGGER.info(f"卡密状态查询：{status['message']}")
    
    hass.services.async_register(
        DOMAIN,
        "get_license_status",
        get_license_status_service,
        schema=vol.Schema({}),
    )
    
    async def deactivate_license_service(call: ServiceCall) -> None:
        """停用卡密服务"""
        license_mgr = hass.data[DOMAIN].get("license_manager")
        if license_mgr:
            if await hass.async_add_executor_job(license_mgr.deactivate_license):
                hass.data[DOMAIN]["license_status"] = await hass.async_add_executor_job(
                    license_mgr.get_license_status
                )
                await _pause_automation(hass)
                _LOGGER.info("卡密已停用，所有自动化功能已暂停")
    
    hass.services.async_register(
        DOMAIN,
        "deactivate_license",
        deactivate_license_service,
        schema=vol.Schema({}),
    )

    async def renew_license_service(call: ServiceCall) -> None:
        """在线延期卡密服务"""
        license_mgr = hass.data[DOMAIN].get("license_manager")
        if license_mgr:
            await hass.async_add_executor_job(license_mgr.get_license_status)
        if not license_mgr or not license_mgr.current_license:
            _LOGGER.error("延期失败：未找到当前激活的卡密")
            return

        extra_days = call.data.get("extra_days", 30)

        import asyncio
        loop = asyncio.get_running_loop()
        success, data = await loop.run_in_executor(
            None, license_mgr.online_verifier.renew, license_mgr.current_license.key, extra_days
        )

        if success and data:
            machine_id = license_mgr.get_activation_device_id("")
            refresh_result = await loop.run_in_executor(
                None,
                license_mgr.activate_license,
                license_mgr.current_license.key,
                machine_id,
            )
            if not refresh_result.get("success"):
                _LOGGER.warning(
                    "卡密延期后重新获取离线票据失败，保留旧票据直到下次刷新：%s",
                    refresh_result.get("error", "unknown error"),
                )

            hass.data[DOMAIN]["license_status"] = await hass.async_add_executor_job(license_mgr.get_license_status)
            _LOGGER.info(f"✓ 卡密延期成功！增加 {extra_days} 天，新到期：{data.get('new_expire_date')}")
            # 如果当前处于暂停状态，延期成功后自动恢复
            if hass.data[DOMAIN].get("automation_paused"):
                _LOGGER.info("卡密延期成功，自动恢复自动化功能")
                await _resume_automation(hass)
        else:
            error = license_mgr.online_verifier.last_error or "未知错误"
            _LOGGER.error(f"✗ 卡密延期失败：{error}")

    hass.services.async_register(
        DOMAIN,
        "renew_license",
        renew_license_service,
        schema=vol.Schema({
            vol.Required("extra_days", default=30): cv.positive_int,
        }),
    )

    async def create_trial_license_service(call: ServiceCall) -> None:
        """创建临时试用卡密服务"""
        hours = call.data.get("hours", 24)
        notes = call.data.get("notes", "")

        license_mgr = hass.data[DOMAIN].get("license_manager")
        if not license_mgr:
            license_mgr = get_license_manager(hass)
            hass.data[DOMAIN]["license_manager"] = license_mgr

        import asyncio
        loop = asyncio.get_running_loop()
        success, data = await loop.run_in_executor(
            None, license_mgr.online_verifier.create_trial, hours, notes
        )

        if success and data:
            trial_key = data.get('license_key', '')
            trial_expire = data.get('expire_date')
            if trial_key and trial_expire:
                license_mgr.record_issued_trial(trial_key, trial_expire)
            _LOGGER.info(
                f"✓ 试用卡密创建成功！key={trial_key}, "
                f"有效期={data.get('hours')}小时, 到期={data.get('expire_date')}"
            )
            hass.data[DOMAIN]["last_trial_key"] = trial_key
        else:
            error = license_mgr.online_verifier.last_error or "未知错误"
            _LOGGER.error(f"✗ 创建试用卡密失败：{error}")

    hass.services.async_register(
        DOMAIN,
        "create_trial_license",
        create_trial_license_service,
        schema=vol.Schema({
            vol.Optional("hours", default=24): cv.positive_int,
            vol.Optional("notes", default=""): cv.string,
        }),
    )
    
    _LOGGER.info("卡密验证系统初始化完成")
    # ==================== 卡密验证结束 ====================

    # ==================== 包厢管理面板 ====================
    from .www import (
        ensure_panel_event_bridge,
        NetcafeDashboard1View,
        NetcafeAutomationConfigView,
        NetcafeAutomationBlueprintSaveView,
        NetcafeAutomationSaveView,
        NetcafePanelAssetView,
        NetcafePanelUploadView,
        NetcafePanelCurrentLogoView,
        NetcafePanelWeatherConfigView,
        NetcafePanelWeatherSearchView,
        NetcafeWeatherView,
        NetcafeIndex2View,
        NetcafeIndexView,
        NetcafePanelConfigSystemView,
        NetcafePanelNotificationsConfigView,
        NetcafePanelNotificationsStatusView,
        NetcafePanelNotificationsTestView,
        NetcafePanelNotificationsPreviewView,
        NetcafePanelNotificationsWechatQrView,
        NetcafePanelEntitiesView,
        NetcafePanelHistoryView,
        NetcafePanelEventsView,
        NetcafePanelWebSocketView,
        NetcafePanelLicenseActivateView,
        NetcafePanelAuthLoginView,
        NetcafePanelAuthRegisterView,
        NetcafePanelAuthSessionView,
        NetcafePanelLicenseStatusView,
        NetcafePanelOverviewView,
        NetcafePanelRoomActionView,
        NetcafePanelServiceView,
        NetcafePanelStatesView,
        NetcafeSubcontrolAppView,
        NetcafeSubcontrolActionView,
        NetcafeSubcontrolAssetView,
        NetcafeSubcontrolBootstrapView,
        NetcafeSubcontrolMappingView,
        NetcafeSubcontrolLicenseActivateView,
        NetcafeSubcontrolLicenseStatusView,
        NetcafePanelView,
        NetcafeIconsStaticView,
        NetcafeRootStaticView,
    )
    hass.http.register_view(NetcafeDashboard1View)
    hass.http.register_view(NetcafePanelView)
    hass.http.register_view(NetcafeIndexView)
    hass.http.register_view(NetcafeIndex2View)
    hass.http.register_view(NetcafeAutomationConfigView)
    hass.http.register_view(NetcafeAutomationBlueprintSaveView)
    hass.http.register_view(NetcafeAutomationSaveView)
    hass.http.register_view(NetcafePanelAssetView)
    hass.http.register_view(NetcafePanelUploadView)
    hass.http.register_view(NetcafePanelCurrentLogoView)
    hass.http.register_view(NetcafePanelWeatherConfigView)
    hass.http.register_view(NetcafePanelWeatherSearchView)
    hass.http.register_view(NetcafeWeatherView)
    hass.http.register_view(NetcafePanelConfigSystemView)
    hass.http.register_view(NetcafePanelNotificationsConfigView)
    hass.http.register_view(NetcafePanelNotificationsStatusView)
    hass.http.register_view(NetcafePanelNotificationsTestView)
    hass.http.register_view(NetcafePanelNotificationsPreviewView)
    hass.http.register_view(NetcafePanelNotificationsWechatQrView)
    hass.http.register_view(NetcafePanelEntitiesView)
    hass.http.register_view(NetcafePanelHistoryView)
    hass.http.register_view(NetcafePanelEventsView)
    hass.http.register_view(NetcafePanelWebSocketView)
    hass.http.register_view(NetcafePanelOverviewView)
    hass.http.register_view(NetcafePanelRoomActionView)
    hass.http.register_view(NetcafePanelStatesView)
    hass.http.register_view(NetcafePanelServiceView)
    hass.http.register_view(NetcafePanelAuthRegisterView)
    hass.http.register_view(NetcafePanelAuthLoginView)
    hass.http.register_view(NetcafePanelAuthSessionView)
    hass.http.register_view(NetcafePanelLicenseStatusView)
    hass.http.register_view(NetcafePanelLicenseActivateView)
    hass.http.register_view(NetcafeSubcontrolAppView)
    hass.http.register_view(NetcafeSubcontrolAssetView)
    hass.http.register_view(NetcafeSubcontrolBootstrapView)
    hass.http.register_view(NetcafeSubcontrolMappingView)
    hass.http.register_view(NetcafeSubcontrolActionView)
    hass.http.register_view(NetcafeSubcontrolLicenseStatusView)
    hass.http.register_view(NetcafeSubcontrolLicenseActivateView)
    hass.http.register_view(NetcafeIconsStaticView)
    hass.http.register_view(NetcafeRootStaticView)
    ensure_panel_event_bridge(hass)
    _LOGGER.info("包厢管理面板已注册，访问: http://<HA地址>:8123/api/netcafe/panel")
    _LOGGER.info("1.html 面板已注册，访问: http://<HA地址>:8123/api/netcafe/1.html")
    _LOGGER.info("分机小窗入口已注册，访问: http://<HA地址>:8123/api/netcafe/subcontrol/app")
    _LOGGER.info("数据大屏入口已注册，访问: http://<HA地址>:8123/api/netcafe/index")
    _LOGGER.info("数据大屏入口已注册，访问: http://<HA地址>:8123/api/netcafe/index2")
    _LOGGER.info("自动化配置入口已注册，访问: http://<HA地址>:8123/api/netcafe/automation")
    # ==================== 包厢管理面板结束 ====================

    return True


async def _pause_automation(hass: HomeAssistant) -> None:
    """暂停所有自动化功能."""
    if hass.data[DOMAIN].get("automation_paused"):
        return

    _LOGGER.info("正在暂停所有自动化功能...")

    # 设置暂停标志
    hass.data[DOMAIN]["automation_paused"] = True
    await async_reset_room_control_runtime(hass)

    # 停止设备跟踪定时器
    update_listener = hass.data[DOMAIN].get("update_listener")
    if update_listener:
        try:
            update_listener()
            hass.data[DOMAIN]["update_listener"] = None
            _LOGGER.info("已停止设备跟踪定时器")
        except Exception as e:
            _LOGGER.warning("停止设备跟踪定时器时出错: %s", e)

    # 将所有设备实体设为不可达并清除 last_seen，确保 is_connected 立即返回 False
    devices = hass.data[DOMAIN].get(CONF_DEVICES, {})
    coordinators = hass.data[DOMAIN].get("coordinators", {})
    for entity_id in list(devices.keys()):
        device = devices[entity_id]
        # 直接切到 offline，确保暂停期间设备状态立即失效
        device._reachable = False
        device._probe_state = PROBE_STATE_OFFLINE
        device._last_seen = None
        device._consecutive_failures = 0
        device._last_probe_method = "paused"
        if entity_id in coordinators:
            coordinators[entity_id].async_set_updated_data(False)

    # 更新 license_status 到 hass.data
    license_mgr = hass.data[DOMAIN].get("license_manager")
    if license_mgr:
        try:
            status = await hass.async_add_executor_job(license_mgr.get_license_status)
            hass.data[DOMAIN]["license_status"] = status
        except Exception:
            pass

    _LOGGER.info("所有自动化功能已暂停")


async def _resume_automation(hass: HomeAssistant) -> None:
    """恢复所有自动化功能."""
    if not hass.data[DOMAIN].get("automation_paused"):
        return

    _LOGGER.info("正在恢复所有自动化功能...")

    # 清除暂停标志
    hass.data[DOMAIN]["automation_paused"] = False

    # 更新 license_status 到 hass.data
    license_mgr = hass.data[DOMAIN].get("license_manager")
    if license_mgr:
        try:
            status = await hass.async_add_executor_job(license_mgr.get_license_status)
            hass.data[DOMAIN]["license_status"] = status
        except Exception:
            pass

    # 先停止旧的定时器（如果还在的话）
    old_listener = hass.data[DOMAIN].get("update_listener")
    if old_listener:
        try:
            old_listener()
        except Exception:
            pass
        hass.data[DOMAIN]["update_listener"] = None

    # 重启设备跟踪定时器
    tracker_interval = timedelta(seconds=FAST_ONLINE_INTERVAL)
    devices_ref = hass.data[DOMAIN].get(CONF_DEVICES, {})

    async def _update_devices_resumed(*_) -> None:
        """Update reachability for all tracked devices (resumed)."""
        if hass.data[DOMAIN].get("automation_paused"):
            return

        scanner = hass.data[DOMAIN].get("scanner")
        coordinators = hass.data[DOMAIN].get("coordinators", {})

        if scanner and devices_ref:
            previous_states = {
                entity_id: {
                    "probe_state": getattr(device, "_probe_state", ""),
                    "reachable": bool(getattr(device, "_reachable", False)),
                }
                for entity_id, device in devices_ref.items()
            }
            await async_update_devices(hass, scanner, devices_ref)
            await _handle_device_notification_transitions(hass, devices_ref, previous_states)

            for entity_id, coordinator in coordinators.items():
                if entity_id in devices_ref:
                    coordinator.async_set_updated_data(coordinator.is_reachable)
            await async_process_room_automation(hass)

    hass.data[DOMAIN]["update_listener"] = async_track_time_interval(
        hass, _update_devices_resumed, tracker_interval, cancel_on_shutdown=True
    )

    # 立即刷新一次当前设备状态，恢复在线显示
    try:
        await _update_devices_resumed()
    except Exception as e:
        _LOGGER.warning("恢复自动化后立即刷新设备状态失败: %s", e)

    await async_initialize_room_control_runtime(hass)

    _LOGGER.info("所有自动化功能已恢复")


async def _reload_inactive_config_entries_after_activation(hass: HomeAssistant) -> None:
    """Reload config entries that were blocked before license activation."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state == ConfigEntryState.LOADED:
            continue
        _LOGGER.info(
            "Reloading inactive config entry after license activation: %s",
            entry.title,
        )
        await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up netcafe_automation from a config entry."""
    _LOGGER.debug("Setting up netcafe_automation config entry: %s", entry.title)
    
    # 卡密状态仅用于 1.html 面板展示与管理，不再阻止后端配置项加载
    license_mgr = hass.data[DOMAIN].get("license_manager")
    if not license_mgr:
        license_mgr = get_license_manager(hass)
        hass.data[DOMAIN]["license_manager"] = license_mgr

    from homeassistant.helpers import device_registry as dr
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"hub_{entry.entry_id}")},
        name=HUB_NAME,
        model=HUB_MODEL,
        manufacturer=HUB_MANUFACTURER,
        sw_version="3.0.0",
    )

    storage = StorageManager(hass, entry.entry_id)

    csv_content = await storage.async_load_csv()

    if not csv_content:
        _LOGGER.info("CSV not found in file storage, checking config_entry")
        csv_content = entry.data.get(CONF_CSV_CONTENT, "")

        if csv_content:
            _LOGGER.info("Migrating CSV from config_entry to file storage")
            await storage.async_save_csv(csv_content)

    hass.data[DOMAIN].setdefault("storage_managers", {})[entry.entry_id] = storage

    if not csv_content:
        _LOGGER.warning("No CSV content found for %s, setup button platform only", entry.title)
        hass.data[DOMAIN][entry.entry_id] = {}
        try:
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        except ValueError as err:
            if "already been setup" in str(err):
                _LOGGER.warning("Platform was already set up, continuing: %s", err)
            else:
                raise

        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
        return True

    if "scanner" not in hass.data[DOMAIN]:
        try:
            scanner: Scanner = await async_get_scanner(hass)
            hass.data[DOMAIN]["scanner"] = scanner
        except ScannerException as error:
            raise PlatformNotReady(error)

    try:
        rooms_data = await hass.async_add_executor_job(
            _parse_csv_content, csv_content
        )

        devices = hass.data[DOMAIN][CONF_DEVICES]
        coordinators = hass.data[DOMAIN].setdefault("coordinators", {})

        # 关键修复：基于旧数据清理，但旧数据可能在 hass.data[DOMAIN][entry.entry_id] 中
        old_rooms_data = hass.data[DOMAIN].get(entry.entry_id, {})
        if old_rooms_data:
            _LOGGER.info("Cleaning up %d old rooms before setup", len(old_rooms_data))
            for room_name, room_config in old_rooms_data.items():
                for computer in room_config.get("computers", []):
                    entity_id = computer.get("entity_id")
                    if entity_id:
                        # 清理旧的 coordinator
                        if entity_id in coordinators:
                            coordinators.pop(entity_id, None)
                            _LOGGER.debug("Cleaned up old coordinator: %s", entity_id)
                        # 清理旧的设备
                        if entity_id in devices:
                            devices.pop(entity_id, None)
                            _LOGGER.debug("Cleaned up old device: %s", entity_id)
            removed_entities = _remove_stale_tracker_entities(
                hass,
                config_entry_id=entry.entry_id,
                old_rooms_data=old_rooms_data,
                new_rooms_data=rooms_data,
            )
            if removed_entities:
                _LOGGER.info(
                    "Removed %d stale device_tracker entities that no longer exist in CSV",
                    removed_entities,
                )
        else:
            _LOGGER.debug("No old rooms data found for cleanup (first setup)")

        # 保存 rooms_data 到 hass.data，让 device_tracker 平台能访问
        hass.data[DOMAIN][entry.entry_id] = rooms_data

        # 创建新的设备和 coordinators（在平台设置之前）
        refresh_tasks: list[asyncio.Future] = []
        for room_name, room_config in rooms_data.items():
            for computer in room_config.get("computers", []):
                entity_id = computer["entity_id"]
                ip_address = computer["ip_address"]

                # 创建新设备
                device = DeviceData(
                    ip_address=ip_address,
                    consider_home=timedelta(seconds=DEFAULT_CONSIDER_HOME),
                    title=f"{room_name} - {ip_address}",
                    room_name=room_name,
                )
                devices[entity_id] = device

                ip_last_octet = ip_address.split('.')[-1]
                display_name = f"{room_name}{ip_last_octet}"

                _LOGGER.info("Creating device_tracker: %s for IP: %s (name: %s)",
                            entity_id, ip_address, display_name)

                coordinator = NetcafeUpdateCoordinator(hass, entry, device)
                coordinators[entity_id] = coordinator
                refresh_tasks.append(coordinator.async_refresh())

        if refresh_tasks:
            refresh_results = await asyncio.gather(*refresh_tasks, return_exceptions=True)
            refresh_failures = [result for result in refresh_results if isinstance(result, Exception)]
            if refresh_failures:
                raise refresh_failures[0]

        # 最后 forward entry setups（在设备和 coordinators 准备好之后）
        try:
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        except ValueError as err:
            if "already been setup" in str(err):
                _LOGGER.warning("Platform was already set up, continuing: %s", err)
            else:
                raise

        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        _LOGGER.info(
            "Successfully set up netcafe_automation with %d rooms and %d devices",
            len(rooms_data),
            len(devices)
        )
        await async_initialize_room_control_runtime(hass)

    except Exception as err:
        _LOGGER.error("Error setting up netcafe_automation: %s", err, exc_info=True)
        return False

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("Reload requested for config entry: %s", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = True

    # 获取该条目的数据（在删除之前）
    rooms_data = hass.data[DOMAIN].get(entry.entry_id, {})

    # 尝试卸载平台（包括 button），不依赖 state，避免遗漏卸载导致重复 setup
    _LOGGER.debug("Unloading platforms for entry %s", entry.entry_id)
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    except ValueError as err:
        _LOGGER.debug("Platform was never loaded: %s", err)
        unload_ok = True
    except Exception as err:
        _LOGGER.warning("Unexpected error unloading platforms: %s", err)
        unload_ok = True

    # 清理该条目相关的 devices 和 coordinators
    if rooms_data:
        devices = hass.data[DOMAIN].get(CONF_DEVICES, {})
        coordinators = hass.data[DOMAIN].get("coordinators", {})

        _LOGGER.info("Cleaning up %d rooms for entry %s", len(rooms_data), entry.entry_id)
        for room_name, room_config in rooms_data.items():
            for computer in room_config.get("computers", []):
                entity_id = computer.get("entity_id")
                if entity_id:
                    # 清理 coordinator
                    if entity_id in coordinators:
                        coordinators.pop(entity_id, None)
                        _LOGGER.debug("Removed coordinator: %s", entity_id)
                    # 清理 device
                    if entity_id in devices:
                        devices.pop(entity_id, None)
                        _LOGGER.debug("Removed device: %s", entity_id)

    # 不要删除 hass.data[DOMAIN][entry.entry_id]
    # 保留它，以便下次 setup 能读取旧数据进行清理
    # 下次 setup 会用新数据覆盖它

    # 删除 storage manager
    storage_managers = hass.data[DOMAIN].get("storage_managers", {})
    storage_managers.pop(entry.entry_id, None)
    config_cache = hass.data[DOMAIN].get("room_control_config_cache", {})
    config_cache.pop(entry.entry_id, None)

    # 删除天气 coordinator 缓存，避免 reload 后复用失效实例
    weather_coordinators = hass.data[DOMAIN].get("weather_coordinators", {})
    weather_coordinators.pop(entry.entry_id, None)

    # 仅重置内存中的卡密管理器，保留持久化卡密文件
    from .license_manager import reset_license_manager
    reset_license_manager()
    _LOGGER.info("已重置卡密管理器缓存，保留本地卡密文件")
    await async_initialize_room_control_runtime(hass)

    _LOGGER.info("Unload completed for entry %s: %s", entry.entry_id, "success" if unload_ok else "failed")
    return unload_ok


def _parse_csv_content(csv_content: str) -> dict[str, dict[str, Any]]:
    """Parse CSV content and organize by room - simplified format (ip_address, room_name)."""
    rooms: dict[str, dict[str, Any]] = {}

    if not csv_content:
        return rooms

    if csv_content.startswith('\ufeff'):
        csv_content = csv_content[1:]

    # 支持逗号、制表符和空格作为分隔符
    delimiter = ','
    first_line = csv_content.split('\n')[0] if '\n' in csv_content else csv_content

    comma_count = first_line.count(',')
    tab_count = first_line.count('\t')
    space_count = first_line.count(' ')

    # 优先级：制表符 > 逗号 > 空格
    if tab_count > comma_count:
        delimiter = '\t'
    elif comma_count == 0 and space_count > 0:
        delimiter = ' '

    csv_file = io.StringIO(csv_content)
    reader = csv.DictReader(csv_file, delimiter=delimiter)

    if reader.fieldnames:
        reader.fieldnames = [name.strip() for name in reader.fieldnames]

    for row in reader:
        cleaned_row = {k.strip() if k else k: v.strip() if v else v for k, v in row.items()}
        room_name = cleaned_row.get(FIELD_ROOM_NAME, "")
        ip_address = cleaned_row.get(FIELD_IP_ADDRESS, "")

        if not room_name or not ip_address:
            continue

        if room_name not in rooms:
            rooms[room_name] = {
                "computers": [],
            }

        ip_slug = ip_address.replace(".", "_")
        device_tracker_id = f"device_tracker.netcafe_{ip_slug}"

        rooms[room_name]["computers"].append({
            "entity_id": device_tracker_id,
            "ip_address": ip_address,
        })
        _LOGGER.info("Auto-generated device_tracker: %s for IP: %s in room: %s", 
                     device_tracker_id, ip_address, room_name)

    _LOGGER.info("Parsed %d rooms from CSV", len(rooms))
    return rooms


def _generate_csv_from_devices(devices_data: dict[str, DeviceData]) -> str:
    """Generate CSV content from devices data."""
    output = io.StringIO()
    writer = csv.writer(output)

    # 新顺序：ip_address, room_name
    writer.writerow([FIELD_IP_ADDRESS, FIELD_ROOM_NAME])

    for entity_id, device in devices_data.items():
        writer.writerow([
            device.ip_address,
            device.room_name or "Unknown",
        ])

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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)
    return True
