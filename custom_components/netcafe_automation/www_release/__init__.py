"""Netcafe panel web views and room-control APIs."""

from __future__ import annotations

import base64
import asyncio
import ipaddress
import json
import logging
import mimetypes
import os
import ssl
import tempfile
import time
from datetime import datetime
from typing import Any

import yaml
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

try:
    from homeassistant.components.http import KEY_HASS
except ImportError:
    KEY_HASS = None

try:
    from homeassistant.components.http.auth import KEY_HASS_USER
except ImportError:
    KEY_HASS_USER = None

from ..const import DOMAIN
from ..license_manager import get_license_manager, verify_server_signature
from ..notifications import (
    async_get_notification_preview,
    async_get_notification_status,
    async_get_wechat_qr_status,
    async_notify_panel_error,
    async_poll_wechat_qr_flow,
    async_send_test_notification,
    async_start_wechat_qr_flow,
    normalize_notifications_config,
)
from ..room_control import (
    _build_entity_snapshot,
    async_execute_room_action,
    async_get_entity_candidates,
    async_get_room_overview,
    async_get_subcontrol_mapping_payload,
    async_get_subcontrol_bootstrap,
    async_initialize_room_control_runtime,
    async_load_system_config,
    async_reset_room_control_runtime,
    async_save_system_config,
)
from ..weather_service import (
    DEFAULT_WEATHER_DOMAIN,
    CONF_WEATHER_AREA_CODE,
    CONF_WEATHER_AREA_ID,
    CONF_WEATHER_AREA_NAME,
    CONF_WEATHER_DOMAIN,
    CONF_WEATHER_LATITUDE,
    CONF_WEATHER_LONGITUDE,
    NetcafeWeatherClient,
    NetcafeWeatherCoordinator,
    build_weather_entry_data,
    get_weather_entry_config,
    normalize_weather_domain,
)

try:
    from homeassistant.components.recorder.history import state_changes_during_period
except ImportError:  # pragma: no cover - depends on HA runtime
    state_changes_during_period = None

_LOGGER = logging.getLogger(__name__)

_WWW_ROOT = os.path.dirname(__file__)
_ASSETS_ROOT = os.path.join(_WWW_ROOT, "assets")
_ICONS_ROOT = os.path.join(_WWW_ROOT, "icons")
_DASHBOARD_HTML_PATH = os.path.join(_WWW_ROOT, "1.html")
_PANEL_HTML_PATH = _DASHBOARD_HTML_PATH
_INDEX_HTML_PATH = _DASHBOARD_HTML_PATH
_INDEX2_HTML_PATH = os.path.join(_WWW_ROOT, "index2.html")
_AUTOMATION_CONFIG_HTML_PATH = os.path.join(_WWW_ROOT, "automation_config.html")
_SUBCONTROL_APP_HTML_PATH = os.path.join(_WWW_ROOT, "subcontrol_app.html")
_ROOT_STATIC_FILES = {
    "1.css": os.path.join(_WWW_ROOT, "1.css"),
    "automation_refactor.css": os.path.join(_WWW_ROOT, "automation_refactor.css"),
    "1.js": os.path.join(_WWW_ROOT, "1.js"),
    "config.js": os.path.join(_WWW_ROOT, "config.js"),
    "data-service.js": os.path.join(_WWW_ROOT, "data-service.js"),
    "login.html": os.path.join(_WWW_ROOT, "login.html"),
    "2.html": os.path.join(_WWW_ROOT, "2.html"),
    "3.html": os.path.join(_WWW_ROOT, "3.html"),
    "4.html": os.path.join(_WWW_ROOT, "4.html"),
    "5.html": os.path.join(_WWW_ROOT, "5.html"),
    "2.css": os.path.join(_WWW_ROOT, "2.css"),
    "3.css": os.path.join(_WWW_ROOT, "3.css"),
    "4.css": os.path.join(_WWW_ROOT, "4.css"),
    "5.css": os.path.join(_WWW_ROOT, "5.css"),
    "2.js": os.path.join(_WWW_ROOT, "2.js"),
    "3.js": os.path.join(_WWW_ROOT, "3.js"),
    "4.js": os.path.join(_WWW_ROOT, "4.js"),
    "5.js": os.path.join(_WWW_ROOT, "5.js"),
    "开灯.png": os.path.join(_WWW_ROOT, "开灯.png"),
    "关灯.png": os.path.join(_WWW_ROOT, "关灯.png"),
    "favicon.ico": os.path.join(_WWW_ROOT, "favicon.ico"),
    "favicon.png": os.path.join(_WWW_ROOT, "favicon.png"),
}
_TEXT_FILE_CACHE: dict[str, tuple[float, str]] = {}
_AUTH_HEADER = "X-Netcafe-Auth"
_AUTH_TOKEN_VERSION = 1
_PANEL_EVENT_SUBSCRIBERS = "panel_event_subscribers"
_PANEL_EVENT_BRIDGE_UNSUB = "panel_event_bridge_unsub"
_PANEL_EVENT_THROTTLE_HANDLE = "panel_event_throttle_handle"
_PANEL_EVENT_THROTTLE_PENDING = "panel_event_throttle_pending"
_PANEL_EVENT_STATS = "panel_event_stats"
_PANEL_OVERVIEW_STATS = "panel_overview_stats"
_PANEL_ACTION_TRACE_STATS = "panel_action_trace_stats"
_PANEL_EVENT_RELEVANT_DOMAINS = {
    "binary_sensor",
    "climate",
    "device_tracker",
    "fan",
    "input_boolean",
    "light",
    "media_player",
    "person",
    "sensor",
    "switch",
}


def _get_panel_event_stats(hass: HomeAssistant) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    stats = domain_data.get(_PANEL_EVENT_STATS)
    if not isinstance(stats, dict):
        stats = {
            "bridge_enabled": False,
            "subscriber_count": 0,
            "ws_connection_count": 0,
            "sse_connection_count": 0,
            "event_count": 0,
            "broadcast_count": 0,
            "dropped_count": 0,
            "last_entity_id": "",
            "last_state": "",
            "last_event_at_ms": 0,
            "last_snapshot_built_at_ms": 0,
            "last_emit_scheduled_at_ms": 0,
            "last_broadcast_started_at_ms": 0,
            "last_broadcast_finished_at_ms": 0,
            "last_bridge_delay_ms": None,
            "last_emit_batch_size": 0,
            "last_ws_connected_at_ms": 0,
            "last_ws_closed_at_ms": 0,
            "last_sse_connected_at_ms": 0,
            "last_sse_closed_at_ms": 0,
            "recent_entities": [],
            "recent_event_history": [],
        }
        domain_data[_PANEL_EVENT_STATS] = stats
    return stats


def _get_panel_overview_stats(hass: HomeAssistant) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    stats = domain_data.get(_PANEL_OVERVIEW_STATS)
    if not isinstance(stats, dict):
        stats = {
            "request_count": 0,
            "last_started_at_ms": 0,
            "last_finished_at_ms": 0,
            "last_duration_ms": None,
            "last_room_count": 0,
            "last_group_count": 0,
            "last_error": "",
            "recent_durations_ms": [],
        }
        domain_data[_PANEL_OVERVIEW_STATS] = stats
    return stats


def _get_panel_action_trace_stats(hass: HomeAssistant) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    stats = domain_data.get(_PANEL_ACTION_TRACE_STATS)
    if not isinstance(stats, dict):
        stats = {
            "count": 0,
            "recent": [],
        }
        domain_data[_PANEL_ACTION_TRACE_STATS] = stats
    return stats


def _append_panel_action_trace(hass: HomeAssistant, trace: dict[str, Any]) -> None:
    stats = _get_panel_action_trace_stats(hass)
    stats["count"] = int(stats.get("count", 0) or 0) + 1
    recent = list(stats.get("recent", []))
    recent.append(trace)
    stats["recent"] = recent[-30:]


def _record_panel_recent_entity(stats: dict[str, Any], payload: dict[str, Any]) -> None:
    recent = stats.get("recent_entities")
    if not isinstance(recent, list):
        recent = []
    recent.append(
        {
            "entity_id": payload.get("entity_id", ""),
            "state": payload.get("state"),
            "ts": payload.get("ts"),
            "server_event_at_ms": payload.get("server_event_at_ms"),
            "server_snapshot_at_ms": payload.get("server_snapshot_at_ms"),
            "server_broadcast_at_ms": payload.get("server_broadcast_at_ms"),
        }
    )
    stats["recent_entities"] = recent[-20:]
    history = stats.get("recent_event_history")
    if not isinstance(history, list):
        history = []
    snapshot = payload.get("snapshot") if isinstance(payload.get("snapshot"), dict) else {}
    history.append(
        {
            "entity_id": payload.get("entity_id", ""),
            "domain": payload.get("domain", ""),
            "state": payload.get("state"),
            "ts": payload.get("ts"),
            "server_event_at_ms": payload.get("server_event_at_ms"),
            "server_emit_at_ms": payload.get("server_emit_at_ms"),
            "server_broadcast_at_ms": payload.get("server_broadcast_at_ms"),
            "server_bridge_delay_ms": payload.get("server_bridge_delay_ms"),
            "snapshot_state": snapshot.get("state"),
            "snapshot_hvac_mode": snapshot.get("hvac_mode"),
            "snapshot_temperature": snapshot.get("temperature"),
            "snapshot_current_temperature": snapshot.get("current_temperature"),
            "snapshot_is_on": snapshot.get("is_on"),
            "snapshot_brightness_pct": snapshot.get("brightness_pct"),
            "snapshot_percentage": snapshot.get("percentage"),
            "last_changed": snapshot.get("last_changed"),
        }
    )
    stats["recent_event_history"] = history[-200:]


class RemoteAuthError(RuntimeError):
    """Raised when the remote auth service returns an application error."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def _read_text_file_sync(file_path: str) -> str | None:
    """Synchronously read one text file."""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    return None


def _read_binary_file_sync(file_path: str) -> bytes | None:
    """Synchronously read one binary file."""
    if os.path.exists(file_path):
        with open(file_path, "rb") as file:
            return file.read()
    return None


_ALLOWED_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"}
_MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2 MB
_HA_WWW_UPLOAD_SUBDIR = "netcafe"
_BRAND_LOGO_BASENAME = "brand_logo"


def _get_primary_config_entry(hass: HomeAssistant) -> ConfigEntry | None:
    """Return the first loaded config entry for this integration."""
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


async def _get_weather_coordinator(hass: HomeAssistant) -> NetcafeWeatherCoordinator | None:
    """Return or create the cached weather coordinator."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    coordinators = domain_data.setdefault("weather_coordinators", {})
    entry = _get_primary_config_entry(hass)
    if entry is None:
        return None
    coordinator = coordinators.get(entry.entry_id)
    if coordinator is None:
        coordinator = NetcafeWeatherCoordinator(hass, entry)
        coordinators[entry.entry_id] = coordinator
    return coordinator


def _write_binary_file_sync(file_path: str, data: bytes) -> None:
    """Synchronously write binary content atomically."""
    directory = os.path.dirname(file_path)
    os.makedirs(directory, exist_ok=True)
    temp_path = None
    fd, temp_path = tempfile.mkstemp(prefix=".netcafe_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(data)
        os.replace(temp_path, file_path)
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def _delete_file_if_exists_sync(file_path: str) -> None:
    """Delete one file if it exists."""
    if os.path.exists(file_path):
        os.remove(file_path)


def _ensure_directory_sync(directory: str) -> None:
    """Ensure one directory exists."""
    os.makedirs(directory, exist_ok=True)


def _find_uploaded_brand_logo_path(config_dir: str) -> str | None:
    """Find the current uploaded brand logo inside Home Assistant www."""
    upload_dir = os.path.join(config_dir, "www", _HA_WWW_UPLOAD_SUBDIR)
    for ext in sorted(_ALLOWED_UPLOAD_EXTENSIONS):
        candidate = os.path.join(upload_dir, _BRAND_LOGO_BASENAME + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


def _write_text_file_atomic_sync(file_path: str, content: str) -> None:
    """Atomically write text content."""
    directory = os.path.dirname(file_path)
    os.makedirs(directory, exist_ok=True)

    temp_path = None
    fd, temp_path = tempfile.mkstemp(prefix=".netcafe_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)
        os.replace(temp_path, file_path)
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def _validate_yaml_filename(filename: str) -> str:
    """Validate blueprint filename."""
    normalized = str(filename or "").strip()
    if not normalized:
        raise ValueError("缺少蓝图文件名")
    if normalized != os.path.basename(normalized):
        raise ValueError("文件名不能包含路径")
    if normalized in {".", ".."} or ".." in normalized:
        raise ValueError("文件名不合法")
    if not normalized.lower().endswith((".yaml", ".yml")):
        raise ValueError("文件名必须以 .yaml 或 .yml 结尾")
    return normalized


def _save_blueprint_sync(config_dir: str, filename: str, content: str) -> str:
    """Save a blueprint file into the HA config dir."""
    safe_filename = _validate_yaml_filename(filename)
    if not str(content or "").strip():
        raise ValueError("蓝图内容不能为空")

    blueprint_dir = os.path.join(config_dir, "blueprints", "automation")
    blueprint_path = os.path.join(blueprint_dir, safe_filename)
    _write_text_file_atomic_sync(blueprint_path, content)
    return f"/config/blueprints/automation/{safe_filename}"


def _save_automations_sync(config_dir: str, automations: list[dict[str, Any]]) -> dict[str, int | str]:
    """Merge and save automations into automations.yaml."""
    if not isinstance(automations, list) or not automations:
        raise ValueError("自动化配置不能为空")

    automations_path = os.path.join(config_dir, "automations.yaml")
    existing_content = _read_text_file_sync(automations_path) or ""

    if existing_content.strip():
        existing_data = yaml.safe_load(existing_content)
    else:
        existing_data = []

    if existing_data is None:
        existing_data = []
    if not isinstance(existing_data, list):
        raise ValueError("automations.yaml 不是列表格式，无法自动合并")

    existing_index: dict[str, int] = {}
    for index, item in enumerate(existing_data):
        if not isinstance(item, dict):
            raise ValueError("automations.yaml 包含非对象条目，无法自动合并")
        automation_id = str(item.get("id", "")).strip()
        if automation_id:
            existing_index[automation_id] = index

    created = 0
    updated = 0
    for item in automations:
        if not isinstance(item, dict):
            raise ValueError("自动化配置格式错误，必须是对象列表")
        automation_id = str(item.get("id", "")).strip()
        if not automation_id:
            raise ValueError("自动化配置缺少 id，无法保存")
        normalized_item = dict(item)
        if automation_id in existing_index:
            existing_data[existing_index[automation_id]] = normalized_item
            updated += 1
        else:
            existing_index[automation_id] = len(existing_data)
            existing_data.append(normalized_item)
            created += 1

    yaml_content = yaml.safe_dump(existing_data, allow_unicode=True, sort_keys=False, indent=2)
    _write_text_file_atomic_sync(automations_path, yaml_content)
    return {
        "created": created,
        "updated": updated,
        "total": len(automations),
        "path": "/config/automations.yaml",
    }


async def _load_text_file(hass: HomeAssistant, file_path: str) -> str | None:
    """Load one text file and refresh the cache when the file changes."""
    if not os.path.exists(file_path):
        _TEXT_FILE_CACHE.pop(file_path, None)
        return None

    mtime = os.path.getmtime(file_path)
    cached = _TEXT_FILE_CACHE.get(file_path)
    if cached and cached[0] == mtime:
        return cached[1]

    content = await hass.async_add_executor_job(_read_text_file_sync, file_path)
    if content is None:
        _TEXT_FILE_CACHE.pop(file_path, None)
        return None

    _TEXT_FILE_CACHE[file_path] = (mtime, content)
    return content


def _resolve_asset_path(asset_path: str) -> str | None:
    """Resolve a safe path under the assets directory."""
    normalized = os.path.normpath(asset_path or "").lstrip("\\/")
    if not normalized or normalized.startswith("..") or os.path.isabs(normalized):
        return None

    full_path = os.path.normpath(os.path.join(_ASSETS_ROOT, normalized))
    try:
        if os.path.commonpath([_ASSETS_ROOT, full_path]) != _ASSETS_ROOT:
            return None
    except ValueError:
        return None
    return full_path


def _resolve_icons_path(asset_path: str) -> str | None:
    """Resolve a safe path under the icons directory."""
    normalized = os.path.normpath(asset_path or "").lstrip("\\/")
    if not normalized or normalized.startswith("..") or os.path.isabs(normalized):
        return None

    full_path = os.path.normpath(os.path.join(_ICONS_ROOT, normalized))
    try:
        if os.path.commonpath([_ICONS_ROOT, full_path]) != _ICONS_ROOT:
            return None
    except ValueError:
        return None
    return full_path


def _get_license_manager_from_hass(hass: HomeAssistant):
    """Return a cached license manager."""
    license_mgr = hass.data[DOMAIN].get("license_manager")
    if not license_mgr:
        license_mgr = get_license_manager(hass)
        hass.data[DOMAIN]["license_manager"] = license_mgr
    return license_mgr


def _get_hass_from_request(request, fallback_hass: HomeAssistant | None = None) -> HomeAssistant | None:
    """Extract the Home Assistant instance from an aiohttp request."""
    hass = getattr(request, "hass", None)
    if hass is not None:
        return hass

    app = getattr(request, "app", None)
    if app is not None:
        try:
            if KEY_HASS is not None:
                hass = app.get(KEY_HASS)
                if hass is not None:
                    return hass
            hass = app.get("hass")
            if hass is not None:
                return hass
        except Exception:
            pass

    config_dict = getattr(request, "config_dict", None)
    if config_dict is not None:
        try:
            hass = config_dict.get("hass")
            if hass is not None:
                return hass
        except Exception:
            pass

    return fallback_hass


async def _get_license_status(hass: HomeAssistant) -> dict[str, Any]:
    """Return the latest license status."""
    license_mgr = _get_license_manager_from_hass(hass)
    status = await hass.async_add_executor_job(license_mgr.get_license_status)
    hass.data[DOMAIN]["license_status"] = status
    return status


async def _sync_license_from_panel_auth(
    hass: HomeAssistant,
    auth_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Sync the locally cached license file from the panel-authenticated user."""
    license_key = str((auth_payload or {}).get("license_key", "")).strip().upper()
    if not license_key:
        return await _get_license_status(hass)

    license_mgr = _get_license_manager_from_hass(hass)

    try:
        normalized_device_id = await hass.async_add_executor_job(
            license_mgr.get_activation_device_id,
            "",
        )
        result = await hass.async_add_executor_job(
            license_mgr.activate_license,
            license_key,
            normalized_device_id,
        )
        if result.get("success"):
            status = await _get_license_status(hass)
            if hass.data[DOMAIN].get("automation_paused") and status.get("is_valid"):
                from .. import _resume_automation

                await _resume_automation(hass)
            return status

        _LOGGER.warning(
            "面板登录后同步卡密失败，继续沿用本地状态: %s",
            result.get("error", "unknown error"),
        )
    except Exception as err:
        _LOGGER.warning("面板登录后同步卡密异常，继续沿用本地状态: %s", err)

    return await _get_license_status(hass)


def _base64url_decode(value: str) -> bytes:
    padded = str(value or "").replace("-", "+").replace("_", "/")
    if len(padded) % 4:
        padded += "=" * (4 - (len(padded) % 4))
    return base64.b64decode(padded.encode("utf-8"))


def _get_auth_token_from_request(request) -> str:
    header_token = str(request.headers.get(_AUTH_HEADER, "")).strip()
    if header_token:
        return header_token
    authorization = str(request.headers.get("Authorization", "")).strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    query_token = str(request.query.get("token", "")).strip()
    if query_token:
        return query_token
    return ""


def _verify_panel_auth_token(token: str, hass: HomeAssistant | None = None) -> tuple[bool, dict[str, Any] | None, str]:
    token_text = str(token or "").strip()
    if not token_text or "." not in token_text:
        return False, None, "请先登录后再访问系统。"

    payload_part, signature = token_text.split(".", 1)
    config_dir = hass.config.config_dir if hass is not None else None
    if not verify_server_signature(payload_part, signature, config_dir):
        return False, None, "登录令牌签名无效"

    try:
        payload = json.loads(_base64url_decode(payload_part).decode("utf-8"))
    except Exception:
        return False, None, "登录令牌内容错误"

    if not isinstance(payload, dict):
        return False, None, "登录令牌内容错误"
    if int(payload.get("ver", 0)) != _AUTH_TOKEN_VERSION:
        return False, None, "登录令牌版本不支持"
    if int(payload.get("exp", 0)) <= int(time.time()):
        return False, None, "登录已过期，请重新登录"
    if not str(payload.get("username", "")).strip():
        return False, None, "登录令牌缺少用户名"
    if not str(payload.get("license_key", "")).strip():
        return False, None, "登录令牌缺少卡密"

    return True, payload, ""


def _auth_required_response(view: HomeAssistantView, message: str) -> web.Response:
    return view.json(
        {
            "success": False,
            "auth_required": True,
            "message": message,
        },
        status_code=401,
    )


def _subcontrol_access_denied_response(
    view: HomeAssistantView,
    message: str,
    *,
    status_code: int = 403,
    auth_required: bool = False,
    lan_trust_required: bool = False,
    client_ip: str = "",
) -> web.Response:
    payload: dict[str, Any] = {
        "success": False,
        "message": message,
    }
    if auth_required:
        payload["auth_required"] = True
    if lan_trust_required:
        payload["lan_trust_required"] = True
    if client_ip:
        payload["client_ip"] = client_ip
    return view.json(payload, status_code=status_code)


def _get_request_user(request) -> Any:
    """Return the authenticated HA user when available."""
    user = None
    try:
        if KEY_HASS_USER is not None:
            user = request.get(KEY_HASS_USER)
    except Exception:
        user = None
    if user is None:
        try:
            user = request.get("hass_user")
        except Exception:
            user = None
    if user is None:
        try:
            user = request.get("user")
        except Exception:
            user = None
    if user is None:
        user = getattr(request, "user", None)
    return user


def _get_request_remote_ip(request, *, trust_proxy_headers: bool = False) -> str:
    """Resolve the request source IP for subcontrol LAN allowlist checks."""
    if trust_proxy_headers:
        forwarded_for = str(request.headers.get("X-Forwarded-For", "")).strip()
        if forwarded_for:
            candidate = forwarded_for.split(",", 1)[0].strip()
            if candidate:
                return candidate
        x_real_ip = str(request.headers.get("X-Real-IP", "")).strip()
        if x_real_ip:
            return x_real_ip
    remote = str(getattr(request, "remote", "") or "").strip()
    if remote:
        return remote
    transport = getattr(request, "transport", None)
    if transport is not None:
        peername = transport.get_extra_info("peername")
        if isinstance(peername, tuple) and peername:
            return str(peername[0] or "").strip()
    return ""


async def _require_subcontrol_access(
    view: HomeAssistantView,
    hass: HomeAssistant,
    request,
) -> web.Response | None:
    """Allow subcontrol access via HA auth or trusted LAN CIDR ranges."""
    if _get_request_user(request) is not None:
        return None

    system_config = await async_load_system_config(hass)
    global_settings = system_config.get("global_settings", {}) if isinstance(system_config, dict) else {}
    subcontrol_trust = (
        global_settings.get("subcontrol_trust", {})
        if isinstance(global_settings, dict)
        else {}
    )
    trust_enabled = bool(subcontrol_trust.get("enabled"))
    trust_proxy_headers = bool(subcontrol_trust.get("trust_proxy_headers"))
    allowed_cidrs = [
        str(item or "").strip()
        for item in subcontrol_trust.get("allowed_cidrs", []) or []
        if str(item or "").strip()
    ]
    has_auth_token = bool(_get_auth_token_from_request(request))

    if not trust_enabled:
        if has_auth_token:
            return _subcontrol_access_denied_response(
                view,
                "当前分机未被主机允许访问；如需继续使用旧模式，请确认 HA Token 有效，或在总控中启用分机局域网白名单。",
                status_code=401,
                auth_required=True,
            )
        return _subcontrol_access_denied_response(
            view,
            "当前分机未被主机允许访问，请先在总控中启用分机局域网白名单。",
            status_code=401,
            auth_required=True,
        )

    client_ip = _get_request_remote_ip(request, trust_proxy_headers=trust_proxy_headers)
    if client_ip:
        try:
            client_address = ipaddress.ip_address(client_ip)
        except ValueError:
            client_address = None
        if client_address is not None:
            for cidr in allowed_cidrs:
                try:
                    if client_address in ipaddress.ip_network(cidr, strict=False):
                        return None
                except ValueError:
                    continue

    if has_auth_token:
        return _subcontrol_access_denied_response(
            view,
            f"当前分机 IP {client_ip or '--'} 未被主机允许访问；如需兼容旧模式，请确认 HA Token 有效。",
            status_code=401,
            auth_required=True,
            lan_trust_required=True,
            client_ip=client_ip,
        )
    return _subcontrol_access_denied_response(
        view,
        f"当前分机 IP {client_ip or '--'} 未被主机允许访问，请在总控的分机局域网白名单中加入对应网段。",
        status_code=403,
        lan_trust_required=True,
        client_ip=client_ip,
    )


async def _require_panel_auth(
    view: HomeAssistantView,
    hass: HomeAssistant,
    request,
) -> tuple[dict[str, Any] | None, web.Response | None]:
    token = _get_auth_token_from_request(request)
    valid, payload, message = _verify_panel_auth_token(token, hass)
    if not valid:
        hass.async_create_task(
            async_notify_panel_error(
                hass,
                title="面板认证异常",
                message=message or "请先登录后再访问系统。",
                error_key=f"panel-auth-invalid:{message}",
            )
        )
        return None, _auth_required_response(view, message or "请先登录后再访问系统。")
    try:
        remote_result = await _proxy_remote_auth_request(hass, "session", {"token": token})
        remote_data = remote_result.get("data", {}) if isinstance(remote_result, dict) else {}
        remote_user = remote_data.get("user", {}) if isinstance(remote_data, dict) else {}
        if isinstance(remote_user, dict) and remote_user.get("username"):
            payload = {
                **payload,
                "username": str(remote_user.get("username", payload.get("username", ""))),
                "license_key": str(remote_user.get("license_key", payload.get("license_key", ""))),
                "uid": int(remote_user.get("id", payload.get("uid", 0))),
            }
    except Exception as err:
        hass.async_create_task(
            async_notify_panel_error(
                hass,
                title="面板认证异常",
                message=str(err) or "登录已失效，请重新登录。",
                error_key=f"panel-auth-remote:{type(err).__name__}:{str(err)}",
            )
        )
        return None, _auth_required_response(view, str(err) or "登录已失效，请重新登录。")
    return payload, None


def _get_panel_event_subscribers(hass: HomeAssistant) -> list[asyncio.Queue]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    subscribers = domain_data.get(_PANEL_EVENT_SUBSCRIBERS)
    if not isinstance(subscribers, list):
        subscribers = []
        domain_data[_PANEL_EVENT_SUBSCRIBERS] = subscribers
    _get_panel_event_stats(hass)["subscriber_count"] = len(subscribers)
    return subscribers


async def _broadcast_panel_event(hass: HomeAssistant, payload: dict[str, Any]) -> None:
    subscribers = _get_panel_event_subscribers(hass)
    stats = _get_panel_event_stats(hass)
    stats["broadcast_count"] = int(stats.get("broadcast_count", 0) or 0) + 1
    stats["last_broadcast_started_at_ms"] = int(time.time() * 1000)
    payload["server_broadcast_at_ms"] = stats["last_broadcast_started_at_ms"]
    _record_panel_recent_entity(stats, payload)
    if not subscribers:
        stats["last_broadcast_finished_at_ms"] = int(time.time() * 1000)
        return
    stale: list[asyncio.Queue] = []
    for queue in list(subscribers):
        try:
            if queue.full():
                try:
                    queue.get_nowait()
                    stats["dropped_count"] = int(stats.get("dropped_count", 0) or 0) + 1
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(payload)
        except Exception:
            stale.append(queue)
    if stale:
        for queue in stale:
            if queue in subscribers:
                subscribers.remove(queue)
    stats["subscriber_count"] = len(subscribers)
    stats["last_broadcast_finished_at_ms"] = int(time.time() * 1000)


def _panel_event_payload(entity_id: str, state: str | None = None) -> dict[str, Any]:
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    now_ms = int(time.time() * 1000)
    return {
        "type": "state_changed",
        "entity_id": entity_id,
        "domain": domain,
        "state": state,
        "ts": now_ms,
        "server_event_at_ms": now_ms,
    }


def _is_panel_relevant_entity(entity_id: str) -> bool:
    entity_text = str(entity_id or "").strip().lower()
    if not entity_text or "." not in entity_text:
        return False
    domain = entity_text.split(".", 1)[0]
    return domain in _PANEL_EVENT_RELEVANT_DOMAINS


def ensure_panel_event_bridge(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_PANEL_EVENT_BRIDGE_UNSUB):
        return
    _get_panel_event_stats(hass)["bridge_enabled"] = True

    def _emit_pending() -> None:
        domain_data[_PANEL_EVENT_THROTTLE_HANDLE] = None
        pending = domain_data.pop(_PANEL_EVENT_THROTTLE_PENDING, None)
        if pending:
            if isinstance(pending, dict) and any("." in str(key) for key in pending.keys()):
                payloads = list(pending.values())
            else:
                payloads = [pending]
            stats = _get_panel_event_stats(hass)
            stats["last_emit_batch_size"] = len(payloads)
            for payload in payloads:
                payload["server_emit_at_ms"] = int(time.time() * 1000)
                event_ms = int(payload.get("server_event_at_ms") or payload.get("ts") or 0)
                payload["server_bridge_delay_ms"] = (
                    max(0, payload["server_emit_at_ms"] - event_ms) if event_ms else None
                )
                stats["last_emit_scheduled_at_ms"] = payload["server_emit_at_ms"]
                stats["last_bridge_delay_ms"] = payload.get("server_bridge_delay_ms")
                hass.async_create_task(_broadcast_panel_event(hass, payload))

    @callback
    def _handle_state_changed(event) -> None:
        data = event.data if hasattr(event, "data") and isinstance(event.data, dict) else {}
        entity_id = str(data.get("entity_id", "")).strip()
        if not _is_panel_relevant_entity(entity_id):
            return
        stats = _get_panel_event_stats(hass)
        new_state = data.get("new_state")
        state_text = None
        snapshot = None
        if new_state is not None:
            state_text = str(getattr(new_state, "state", "") or "")
            snapshot = _build_entity_snapshot(hass, entity_id)
        payload = _panel_event_payload(entity_id, state_text)
        if snapshot is not None:
            payload["snapshot"] = snapshot
            payload["server_snapshot_at_ms"] = int(time.time() * 1000)
            stats["last_snapshot_built_at_ms"] = payload["server_snapshot_at_ms"]
        pending = domain_data.get(_PANEL_EVENT_THROTTLE_PENDING)
        if not isinstance(pending, dict):
            pending = {}
        pending[entity_id] = payload
        domain_data[_PANEL_EVENT_THROTTLE_PENDING] = pending
        stats["event_count"] = int(stats.get("event_count", 0) or 0) + 1
        stats["last_entity_id"] = entity_id
        stats["last_state"] = state_text or ""
        stats["last_event_at_ms"] = int(payload.get("server_event_at_ms") or payload.get("ts") or 0)
        handle = domain_data.get(_PANEL_EVENT_THROTTLE_HANDLE)
        if handle is None:
            domain_data[_PANEL_EVENT_THROTTLE_HANDLE] = hass.loop.call_later(0.02, _emit_pending)

    unsub = hass.bus.async_listen("state_changed", _handle_state_changed)
    domain_data[_PANEL_EVENT_BRIDGE_UNSUB] = unsub


def _build_remote_auth_url(hass: HomeAssistant) -> str:
    license_mgr = _get_license_manager_from_hass(hass)
    api_url = getattr(getattr(license_mgr, "online_verifier", None), "api_url", "") or ""
    if api_url.endswith("/license.php"):
        return api_url[: -len("/license.php")] + "/auth.php"
    return api_url.rstrip("/") + "/auth.php"


def _build_remote_auth_candidates(hass: HomeAssistant) -> list[dict[str, Any]]:
    license_mgr = _get_license_manager_from_hass(hass)
    verifier = getattr(license_mgr, "online_verifier", None)
    candidates = []
    raw_candidates = getattr(verifier, "_api_candidates", []) or []

    for candidate in raw_candidates:
        url = str(candidate.get("url") or "").strip()
        if not url:
            continue
        if url.endswith("/license.php"):
            auth_url = url[: -len("/license.php")] + "/auth.php"
        else:
            auth_url = url.rstrip("/") + "/auth.php"
        candidates.append(
            {
                "url": auth_url,
                "host_header": candidate.get("host_header"),
                "skip_hostname_check": bool(candidate.get("skip_hostname_check")),
            }
        )

    if not candidates:
        candidates.append(
            {
                "url": _build_remote_auth_url(hass),
                "host_header": None,
                "skip_hostname_check": False,
            }
        )
    return candidates


def _build_remote_auth_ssl_context(skip_hostname_check: bool) -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    if skip_hostname_check:
        context.check_hostname = False
    return context


async def _proxy_remote_auth_request(
    hass: HomeAssistant,
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    import asyncio
    import http.client
    import urllib.parse

    request_payload = json.dumps({"action": action, **payload}).encode("utf-8")
    last_error: Exception | None = None

    def _request_once(candidate: dict[str, Any]) -> tuple[int, str]:
        parsed = urllib.parse.urlparse(candidate["url"])
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        headers = {
            "Content-Type": "application/json",
            "Connection": "close",
            "User-Agent": "NetcafePanelAuth/1.0",
        }
        if candidate.get("host_header"):
            headers["Host"] = candidate["host_header"]

        connection = None
        try:
            if scheme == "https":
                connection = http.client.HTTPSConnection(
                    host,
                    port,
                    timeout=15,
                    context=_build_remote_auth_ssl_context(bool(candidate.get("skip_hostname_check"))),
                )
            else:
                connection = http.client.HTTPConnection(host, port, timeout=15)
            connection.request("POST", path, body=request_payload, headers=headers)
            response = connection.getresponse()
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    for candidate in _build_remote_auth_candidates(hass):
        try:
            status_code, raw_body = await asyncio.get_running_loop().run_in_executor(
                None,
                _request_once,
                candidate,
            )
            try:
                data = json.loads(raw_body)
            except Exception as err:
                raise RemoteAuthError(f"认证服务返回异常响应: {raw_body[:120] or err}", status_code or 500) from err

            if not isinstance(data, dict):
                raise RemoteAuthError(f"认证服务返回异常响应: HTTP {status_code}", status_code or 500)
            if status_code < 200 or status_code >= 300:
                raise RemoteAuthError(
                    str(data.get("message") or f"认证服务请求失败: HTTP {status_code}"),
                    status_code or 500,
                )
            return data
        except RemoteAuthError:
            raise
        except Exception as err:
            last_error = err
            continue

    raise RemoteAuthError(str(last_error or "认证服务连接失败"), 502)


async def _get_panel_lock_response(
    view: HomeAssistantView,
    hass: HomeAssistant,
) -> web.Response | None:
    """Panel APIs are no longer locked by license status."""
    return None


def _parse_iso_datetime(value: str, field_name: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"缺少 {field_name}")
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except Exception as err:
        raise ValueError(f"{field_name} 格式无效") from err


def _serialize_history_rows(rows: Any, entity_ids: list[str]) -> list[list[dict[str, Any]]]:
    if isinstance(rows, dict):
        return [
            [state.as_dict() if hasattr(state, "as_dict") else dict(state) for state in (rows.get(entity_id) or [])]
            for entity_id in entity_ids
        ]

    if isinstance(rows, list):
        serialized = []
        for entity_rows in rows:
            if not isinstance(entity_rows, list):
                serialized.append([])
                continue
            serialized.append([
                state.as_dict() if hasattr(state, "as_dict") else dict(state)
                for state in entity_rows
            ])
        return serialized

    return [[] for _ in entity_ids]


def _load_history_rows_sync(
    hass: HomeAssistant,
    start_time: datetime,
    end_time: datetime,
    entity_ids: list[str],
) -> dict[str, list[Any]]:
    """Load recorder history rows for multiple entity ids in HA versions that only accept one id."""
    result: dict[str, list[Any]] = {}
    for entity_id in entity_ids:
        try:
            rows = state_changes_during_period(
                hass,
                start_time,
                end_time,
                entity_id,
                False,
                False,
            )
            result[entity_id] = list((rows or {}).get(entity_id, []))
        except Exception:
            result[entity_id] = []
            raise
    return result


class NetcafePanelView(HomeAssistantView):
    """Serve the room dashboard page."""

    url = "/api/netcafe/panel"
    name = "api:netcafe:panel"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        html = await _load_text_file(hass, _PANEL_HTML_PATH)
        if not html:
            return self.json_message("Panel HTML not found", status_code=500)
        return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})


class NetcafeIndexView(HomeAssistantView):
    """Serve the first large screen page."""

    url = "/api/netcafe/index"
    name = "api:netcafe:index"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        html = await _load_text_file(hass, _INDEX_HTML_PATH)
        if not html:
            return self.json_message("Index HTML not found", status_code=500)
        return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})


class NetcafeDashboard1View(HomeAssistantView):
    """Serve the Home Assistant-backed 1.html dashboard page."""

    url = "/api/netcafe/1.html"
    name = "api:netcafe:1html"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        html = await _load_text_file(hass, _DASHBOARD_HTML_PATH)
        if not html:
            return self.json_message("1.html not found", status_code=500)
        return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})


class NetcafeIndex2View(HomeAssistantView):
    """Serve the second large screen page."""

    url = "/api/netcafe/index2"
    name = "api:netcafe:index2"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        html = await _load_text_file(hass, _INDEX2_HTML_PATH)
        if not html:
            return self.json_message("Index2 HTML not found", status_code=500)
        return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})


class NetcafeAutomationConfigView(HomeAssistantView):
    """Serve the authenticated automation config page."""

    url = "/api/netcafe/automation"
    name = "api:netcafe:automation"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        html = await _load_text_file(hass, _AUTOMATION_CONFIG_HTML_PATH)
        if not html:
            return self.json_message("Automation config HTML not found", status_code=500)
        return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})


class NetcafePanelAssetView(HomeAssistantView):
    """Serve static assets used by the panel and config page."""

    url = "/api/netcafe/automation/assets/{asset_path:.*}"
    name = "api:netcafe:automation:assets"
    requires_auth = False

    async def get(self, request, asset_path: str | None = None):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        asset_path = asset_path or request.match_info.get("asset_path", "")
        full_path = _resolve_asset_path(asset_path)
        if not full_path or not os.path.isfile(full_path):
            return self.json_message("Asset not found", status_code=404)
        body = await hass.async_add_executor_job(_read_binary_file_sync, full_path)
        if body is None:
            return self.json_message("Asset not found", status_code=404)
        content_type, _ = mimetypes.guess_type(full_path)
        return web.Response(
            body=body,
            content_type=content_type or "application/octet-stream",
            headers={"Cache-Control": "no-store"},
        )


class NetcafeSubcontrolAppView(HomeAssistantView):
    """Serve the dedicated subcontrol mini app page."""

    url = "/api/netcafe/subcontrol/app"
    name = "api:netcafe:subcontrol:app"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        auth_error = await _require_subcontrol_access(self, hass, request)
        if auth_error is not None:
            return auth_error
        html = await _load_text_file(hass, _SUBCONTROL_APP_HTML_PATH)
        if not html:
            return self.json_message("Subcontrol app HTML not found", status_code=500)
        return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})


class NetcafeSubcontrolAssetView(HomeAssistantView):
    """Serve static assets used by the subcontrol mini app."""

    url = "/api/netcafe/subcontrol/assets/{asset_path:.*}"
    name = "api:netcafe:subcontrol:assets"
    requires_auth = False

    async def get(self, request, asset_path: str | None = None):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        auth_error = await _require_subcontrol_access(self, hass, request)
        if auth_error is not None:
            return auth_error
        asset_path = str(asset_path or request.match_info.get("asset_path", "")).strip()
        full_path = _resolve_asset_path(asset_path)
        if not full_path or not os.path.isfile(full_path):
            return self.json_message("Asset not found", status_code=404)
        body = await hass.async_add_executor_job(_read_binary_file_sync, full_path)
        if body is None:
            return self.json_message("Asset not found", status_code=404)
        content_type, _ = mimetypes.guess_type(full_path)
        return web.Response(
            body=body,
            content_type=content_type or "application/octet-stream",
            headers={"Cache-Control": "no-store"},
        )


class NetcafeRootStaticView(HomeAssistantView):
    """Serve optional root-level static files for index pages."""

    url = "/api/netcafe/{filename:[^/]+}"
    name = "api:netcafe:root:static"
    requires_auth = False

    async def get(self, request, filename: str | None = None):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        filename = str(filename or request.match_info.get("filename", "")).strip()
        if "/" in filename or "\\" in filename:
            return self.json_message("Asset not found", status_code=404)
        full_path = _ROOT_STATIC_FILES.get(filename)
        if not full_path or not os.path.isfile(full_path):
            return self.json_message("Asset not found", status_code=404)
        body = await hass.async_add_executor_job(_read_binary_file_sync, full_path)
        if body is None:
            return self.json_message("Asset not found", status_code=404)
        content_type, _ = mimetypes.guess_type(full_path)
        return web.Response(
            body=body,
            content_type=content_type or "application/octet-stream",
            headers={"Cache-Control": "no-store"},
        )


class NetcafeIconsStaticView(HomeAssistantView):
    """Serve icon assets used by the panel brand selector."""

    url = "/api/netcafe/icons/{asset_path:.*}"
    name = "api:netcafe:icons:static"
    requires_auth = False

    async def get(self, request, asset_path: str | None = None):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)
        asset_path = str(asset_path or request.match_info.get("asset_path", "")).strip()
        full_path = _resolve_icons_path(asset_path)
        if not full_path or not os.path.isfile(full_path):
            return self.json_message("Asset not found", status_code=404)
        body = await hass.async_add_executor_job(_read_binary_file_sync, full_path)
        if body is None:
            return self.json_message("Asset not found", status_code=404)
        content_type, _ = mimetypes.guess_type(full_path)
        return web.Response(
            body=body,
            content_type=content_type or "application/octet-stream",
            headers={"Cache-Control": "no-store"},
        )


class NetcafePanelStatesView(HomeAssistantView):
    """Expose raw HA states for compatibility."""

    url = "/api/netcafe/panel/states"
    name = "api:netcafe:panel:states"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response
        try:
            states = [state.as_dict() for state in hass.states.async_all()]
            return self.json({"success": True, "states": states})
        except Exception as err:
            _LOGGER.error("面板状态接口返回失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": f"状态序列化失败: {err}"}, status_code=500)


class NetcafePanelHistoryView(HomeAssistantView):
    """Proxy HA recorder history through the panel API."""

    url = "/api/netcafe/panel/history"
    name = "api:netcafe:panel:history"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error

        if state_changes_during_period is None:
            return self.json({"success": False, "message": "当前环境未启用 recorder 历史模块"}, status_code=501)

        entity_ids_text = str(request.query.get("entity_ids", "")).strip()
        if not entity_ids_text:
            return self.json({"success": False, "message": "缺少 entity_ids"}, status_code=400)
        entity_ids = [item.strip() for item in entity_ids_text.split(",") if item.strip()]
        if not entity_ids:
            return self.json({"success": False, "message": "entity_ids 不能为空"}, status_code=400)

        try:
            start_time = _parse_iso_datetime(str(request.query.get("start_time", "")), "start_time")
            end_time = _parse_iso_datetime(str(request.query.get("end_time", "")), "end_time")
        except ValueError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)

        if end_time <= start_time:
            return self.json({"success": False, "message": "end_time 必须晚于 start_time"}, status_code=400)

        try:
            rows = await hass.async_add_executor_job(
                _load_history_rows_sync,
                hass,
                start_time,
                end_time,
                entity_ids,
            )
            return self.json({"success": True, "data": _serialize_history_rows(rows, entity_ids)})
        except Exception as err:
            _LOGGER.error("读取面板历史数据失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelOverviewView(HomeAssistantView):
    """Expose room-centric overview data for the dashboard."""

    url = "/api/netcafe/panel/overview"
    name = "api:netcafe:panel:overview"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response
        stats = _get_panel_overview_stats(hass)
        started_at_ms = int(time.time() * 1000)
        stats["request_count"] = int(stats.get("request_count", 0) or 0) + 1
        stats["last_started_at_ms"] = started_at_ms
        try:
            data = await async_get_room_overview(hass)
            license_status = await _get_license_status(hass)
            finished_at_ms = int(time.time() * 1000)
            duration_ms = max(0, finished_at_ms - started_at_ms)
            recent = list(stats.get("recent_durations_ms", []))
            recent.append(duration_ms)
            stats["recent_durations_ms"] = recent[-20:]
            stats["last_finished_at_ms"] = finished_at_ms
            stats["last_duration_ms"] = duration_ms
            stats["last_room_count"] = len(data.get("rooms", []) if isinstance(data, dict) else [])
            stats["last_group_count"] = len(data.get("groups", []) if isinstance(data, dict) else [])
            stats["last_error"] = ""
            return self.json({
                "success": True,
                "data": data,
                "license": license_status,
                "timing": {
                    "overview_started_at_ms": started_at_ms,
                    "overview_finished_at_ms": finished_at_ms,
                    "overview_duration_ms": duration_ms,
                    "room_count": stats["last_room_count"],
                    "group_count": stats["last_group_count"],
                },
            })
        except Exception as err:
            finished_at_ms = int(time.time() * 1000)
            stats["last_finished_at_ms"] = finished_at_ms
            stats["last_duration_ms"] = max(0, finished_at_ms - started_at_ms)
            stats["last_error"] = str(err)
            _LOGGER.error("读取包厢概览失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="面板核心接口异常",
                    message=f"读取包厢概览失败: {err}",
                    error_key=f"panel-overview:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelEventsView(HomeAssistantView):
    """Stream panel invalidation events to the frontend."""

    url = "/api/netcafe/panel/events"
    name = "api:netcafe:panel:events"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response
        if str(request.query.get("probe", "")).strip() == "1":
            return self.json({"success": True, "data": {"supported": True}})

        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        await response.prepare(request)

        queue: asyncio.Queue = asyncio.Queue(maxsize=8)
        subscribers = _get_panel_event_subscribers(hass)
        subscribers.append(queue)
        stats = _get_panel_event_stats(hass)
        stats["sse_connection_count"] = int(stats.get("sse_connection_count", 0) or 0) + 1
        stats["last_sse_connected_at_ms"] = int(time.time() * 1000)
        stats["subscriber_count"] = len(subscribers)

        async def _send(event_name: str, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False)
            await response.write(f"event: {event_name}\ndata: {body}\n\n".encode("utf-8"))

        try:
            await _send("ready", {"type": "ready", "ts": int(time.time() * 1000)})
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=25)
                    await _send("message", payload)
                except asyncio.TimeoutError:
                    await response.write(b": keepalive\n\n")
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        finally:
            if queue in subscribers:
                subscribers.remove(queue)
            stats["subscriber_count"] = len(subscribers)
            stats["last_sse_closed_at_ms"] = int(time.time() * 1000)
            try:
                await response.write_eof()
            except Exception:
                pass
        return response


class NetcafePanelWebSocketView(HomeAssistantView):
    """Stream panel invalidation events to the frontend via WebSocket."""

    url = "/api/netcafe/panel/ws"
    name = "api:netcafe:panel:ws"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        ws = web.WebSocketResponse(heartbeat=20.0, autoping=True)
        await ws.prepare(request)

        queue: asyncio.Queue = asyncio.Queue(maxsize=16)
        subscribers = _get_panel_event_subscribers(hass)
        subscribers.append(queue)
        stats = _get_panel_event_stats(hass)
        stats["ws_connection_count"] = int(stats.get("ws_connection_count", 0) or 0) + 1
        stats["last_ws_connected_at_ms"] = int(time.time() * 1000)
        stats["subscriber_count"] = len(subscribers)

        sender_task: asyncio.Task | None = None

        async def _sender() -> None:
            await ws.send_json({"type": "ready", "ts": int(time.time() * 1000)})
            while True:
                payload = await queue.get()
                await ws.send_str(json.dumps(payload, ensure_ascii=False))

        try:
            sender_task = hass.async_create_task(_sender())
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    text = str(msg.data or "").strip().lower()
                    if text == "ping":
                        await ws.send_str('{"type":"pong"}')
                elif msg.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSED, web.WSMsgType.ERROR):
                    break
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        finally:
            if sender_task is not None:
                sender_task.cancel()
                try:
                    await sender_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            if queue in subscribers:
                subscribers.remove(queue)
            stats["subscriber_count"] = len(subscribers)
            stats["last_ws_closed_at_ms"] = int(time.time() * 1000)
            try:
                await ws.close()
            except Exception:
                pass
        return ws


class NetcafeSubcontrolBootstrapView(HomeAssistantView):
    """Return one resolved room bootstrap payload for subcontrol clients."""

    url = "/api/netcafe/subcontrol/bootstrap"
    name = "api:netcafe:subcontrol:bootstrap"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        auth_error = await _require_subcontrol_access(self, hass, request)
        if auth_error is not None:
            return auth_error

        local_ips = [
            str(value or "").strip()
            for value in request.query.getall("local_ip", [])
            if str(value or "").strip()
        ]
        if not local_ips:
            fallback_ip = _get_request_remote_ip(
                request,
                trust_proxy_headers=bool(
                    ((await async_load_system_config(hass)).get("global_settings", {}) or {})
                    .get("subcontrol_trust", {})
                    .get("trust_proxy_headers")
                ),
            )
            if fallback_ip:
                local_ips = [fallback_ip]
            else:
                return self.json({"success": False, "message": "缺少 local_ip"}, status_code=400)

        try:
            license_status = await _get_license_status(hass)
            data = await async_get_subcontrol_bootstrap(
                hass,
                local_ips,
                license_status=license_status,
            )
            return self.json({"success": True, "data": data})
        except LookupError as err:
            return self.json({"success": False, "message": str(err)}, status_code=404)
        except RuntimeError as err:
            return self.json({"success": False, "message": str(err)}, status_code=409)
        except ValueError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)
        except Exception as err:
            _LOGGER.error("读取分机 bootstrap 失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafeSubcontrolMappingView(HomeAssistantView):
    """Return the current IP-room mapping for subcontrol clients."""

    url = "/api/netcafe/subcontrol/mapping"
    name = "api:netcafe:subcontrol:mapping"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        auth_error = await _require_subcontrol_access(self, hass, request)
        if auth_error is not None:
            return auth_error

        try:
            payload = await async_get_subcontrol_mapping_payload(hass)
            response_payload = {key: value for key, value in payload.items() if key != "records"}
            return self.json({"success": True, "data": response_payload})
        except LookupError as err:
            return self.json({"success": False, "message": str(err)}, status_code=404)
        except Exception as err:
            _LOGGER.error("读取分机映射 CSV 失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelEntitiesView(HomeAssistantView):
    """Return candidate entities for mapping configuration."""

    url = "/api/netcafe/panel/entities"
    name = "api:netcafe:panel:entities"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response
        try:
            return self.json({"success": True, "data": await async_get_entity_candidates(hass)})
        except Exception as err:
            _LOGGER.error("读取实体候选列表失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="面板核心接口异常",
                    message=f"读取实体候选列表失败: {err}",
                    error_key=f"panel-entities:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelRoomActionView(HomeAssistantView):
    """Execute room-level actions without exposing raw service details."""

    url = "/api/netcafe/panel/room/action"
    name = "api:netcafe:panel:room:action"
    requires_auth = False

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        room_id = str(payload.get("room_id", "")).strip()
        action = str(payload.get("action", "")).strip()
        value = payload.get("value")
        persist = bool(payload.get("persist", False))
        if not room_id or not action:
            return self.json({"success": False, "message": "缺少 room_id 或 action"}, status_code=400)

        try:
            license_status = await _get_license_status(hass)
            if not license_status.get("is_valid"):
                return self.json(
                    {
                        "success": False,
                        "message": license_status.get("message") or "卡密无效，分机控制已暂停",
                        "data": {"license": license_status},
                    },
                    status_code=403,
                )
            trace_started_at_ms = int(time.time() * 1000)
            result = await async_execute_room_action(
                hass,
                room_id,
                action,
                value=value,
                persist=persist,
                source="manual",
            )
            trace_finished_at_ms = int(time.time() * 1000)
            entity_ids = list(result.get("entity_ids", []) if isinstance(result, dict) else [])
            entity_states_after_call = []
            for entity_id in entity_ids:
                entity_state = hass.states.get(entity_id)
                entity_states_after_call.append(
                    {
                        "entity_id": entity_id,
                        "state": str(entity_state.state) if entity_state is not None else None,
                        "last_changed": entity_state.last_changed.isoformat() if entity_state is not None else None,
                    }
                )
            trace = {
                "trace_id": f"trace-{trace_started_at_ms}-{room_id}-{action}",
                "room_id": room_id,
                "action": action,
                "value": value,
                "persist": persist,
                "request_received_at_ms": trace_started_at_ms,
                "execute_finished_at_ms": trace_finished_at_ms,
                "execute_duration_ms": max(0, trace_finished_at_ms - trace_started_at_ms),
                "entity_ids": entity_ids,
                "entity_states_after_call": entity_states_after_call,
            }
            _append_panel_action_trace(hass, trace)
            return self.json({"success": True, "data": result, "trace": trace})
        except ValueError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)
        except Exception as err:
            _LOGGER.error("执行包厢动作失败 %s: %s", action, err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafeSubcontrolActionView(HomeAssistantView):
    """Execute constrained room-level actions for one subcontrol client."""

    url = "/api/netcafe/subcontrol/action"
    name = "api:netcafe:subcontrol:action"
    requires_auth = False

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        auth_error = await _require_subcontrol_access(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        room_id = str(payload.get("room_id", "")).strip()
        action = str(payload.get("action", "")).strip()
        value = payload.get("value")
        if not room_id or not action:
            return self.json({"success": False, "message": "缺少 room_id 或 action"}, status_code=400)

        try:
            license_status = await _get_license_status(hass)
            if not license_status.get("is_valid"):
                return self.json(
                    {
                        "success": False,
                        "message": license_status.get("message") or "卡密无效，分机控制已暂停",
                        "data": {"license": license_status},
                    },
                    status_code=403,
                )
            result = await async_execute_room_action(
                hass,
                room_id,
                action,
                value=value,
                persist=False,
                source="subcontrol",
            )
            return self.json({"success": True, "data": result})
        except PermissionError as err:
            return self.json({"success": False, "message": str(err)}, status_code=403)
        except ValueError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)
        except Exception as err:
            _LOGGER.error("执行分机动作失败 %s: %s", action, err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafeSubcontrolLicenseStatusView(HomeAssistantView):
    """Return the current license status for subcontrol clients."""

    url = "/api/netcafe/subcontrol/license/status"
    name = "api:netcafe:subcontrol:license:status"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        auth_error = await _require_subcontrol_access(self, hass, request)
        if auth_error is not None:
            return auth_error
        try:
            return self.json({"success": True, "data": await _get_license_status(hass)})
        except Exception as err:
            _LOGGER.error("读取分机卡密状态失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafeSubcontrolLicenseActivateView(HomeAssistantView):
    """Activate the shared netcafe license for subcontrol clients."""

    url = "/api/netcafe/subcontrol/license/activate"
    name = "api:netcafe:subcontrol:license:activate"
    requires_auth = False

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        auth_error = await _require_subcontrol_access(self, hass, request)
        if auth_error is not None:
            return auth_error

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        license_key = str(payload.get("license_key", "")).strip().upper()
        device_id = str(payload.get("device_id", "")).strip()
        if not license_key:
            return self.json({"success": False, "message": "缺少 license_key"}, status_code=400)

        license_mgr = _get_license_manager_from_hass(hass)
        try:
            normalized_device_id = await hass.async_add_executor_job(
                license_mgr.get_activation_device_id,
                device_id,
            )
            result = await hass.async_add_executor_job(
                license_mgr.activate_license,
                license_key,
                normalized_device_id,
            )
            status = await _get_license_status(hass)

            if result.get("success") and status.get("is_valid"):
                if hass.data[DOMAIN].get("automation_paused"):
                    from .. import _resume_automation

                    await _resume_automation(hass)
                return self.json({"success": True, "data": status})

            message = result.get("error") or status.get("message") or "卡密激活失败"
            return self.json(
                {"success": False, "message": message, "data": status},
                status_code=400,
            )
        except Exception as err:
            _LOGGER.error("分机激活卡密失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelServiceView(HomeAssistantView):
    """Proxy raw HA service calls for authenticated maintenance usage."""

    url = "/api/netcafe/panel/service/{domain}/{service}"
    name = "api:netcafe:panel:service"
    requires_auth = True

    async def post(self, request, domain: str | None = None, service: str | None = None):
        domain = domain or request.match_info.get("domain", "unknown")
        service = service or request.match_info.get("service", "unknown")
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error

        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        if not hass.services.has_service(domain, service):
            return self.json({"success": False, "message": f"服务不存在: {domain}.{service}"}, status_code=404)

        try:
            await hass.services.async_call(
                domain,
                service,
                payload,
                blocking=True,
                return_response=False,
            )
            return self.json({"success": True})
        except Exception as err:
            _LOGGER.error("面板服务调用失败 %s.%s: %s", domain, service, err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafeAutomationBlueprintSaveView(HomeAssistantView):
    """Save a blueprint file into the HA config directory."""

    url = "/api/netcafe/automation/blueprint/save"
    name = "api:netcafe:automation:blueprint:save"
    requires_auth = True

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        filename = str(payload.get("filename", "")).strip()
        content = str(payload.get("content", ""))
        try:
            saved_path = await hass.async_add_executor_job(
                _save_blueprint_sync,
                hass.config.config_dir,
                filename,
                content,
            )
            return self.json({"success": True, "path": saved_path})
        except ValueError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)
        except Exception as err:
            _LOGGER.error("保存蓝图失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafeAutomationSaveView(HomeAssistantView):
    """Keep the old YAML automation export endpoint for compatibility."""

    url = "/api/netcafe/automation/automations/save"
    name = "api:netcafe:automation:automations:save"
    requires_auth = True

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        automations = payload.get("automations")
        try:
            result = await hass.async_add_executor_job(
                _save_automations_sync,
                hass.config.config_dir,
                automations,
            )
            await hass.services.async_call("automation", "reload", {}, blocking=True, return_response=False)
            return self.json({"success": True, "data": result})
        except ValueError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)
        except Exception as err:
            _LOGGER.error("保存自动化配置失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelConfigSystemView(HomeAssistantView):
    """Read and write normalized room config across all entries."""

    url = "/api/netcafe/panel/config/system"
    name = "api:netcafe:panel:config:system"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response
        try:
            config_data = await async_load_system_config(hass)
            return self.json({"success": True, "data": config_data})
        except Exception as err:
            _LOGGER.error("读取统一配置失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="面板核心接口异常",
                    message=f"读取统一配置失败: {err}",
                    error_key=f"panel-config-get:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        config_data = payload.get("config")
        if not isinstance(config_data, dict):
            return self.json({"success": False, "message": "config 必须是对象"}, status_code=400)

        try:
            saved = await async_save_system_config(hass, config_data)
            await async_reset_room_control_runtime(hass)
            await async_initialize_room_control_runtime(hass)
            return self.json({"success": True, "data": saved})
        except ValueError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)
        except Exception as err:
            _LOGGER.error("保存统一配置失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="面板核心接口异常",
                    message=f"保存统一配置失败: {err}",
                    error_key=f"panel-config-post:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelNotificationsConfigView(HomeAssistantView):
    """Read and write notification settings."""

    url = "/api/netcafe/panel/notifications/config"
    name = "api:netcafe:panel:notifications:config"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        try:
            config_data = await async_load_system_config(hass)
            return self.json({"success": True, "data": normalize_notifications_config(config_data.get("notifications"))})
        except Exception as err:
            _LOGGER.error("读取通知配置失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="通知配置异常",
                    message=f"读取通知配置失败: {err}",
                    error_key=f"panel-notify-config-get:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        config_data = payload.get("config")
        if not isinstance(config_data, dict):
            config_data = payload
        try:
            saved = await async_save_system_config(hass, {"notifications": config_data})
            return self.json({"success": True, "data": normalize_notifications_config(saved.get("notifications"))})
        except ValueError as err:
            return self.json({"success": False, "message": str(err)}, status_code=400)
        except Exception as err:
            _LOGGER.error("保存通知配置失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="通知配置异常",
                    message=f"保存通知配置失败: {err}",
                    error_key=f"panel-notify-config-post:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelNotificationsStatusView(HomeAssistantView):
    """Return notification channel status."""

    url = "/api/netcafe/panel/notifications/status"
    name = "api:netcafe:panel:notifications:status"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        try:
            config_data = await async_load_system_config(hass)
            notifications = normalize_notifications_config(config_data.get("notifications"))
            status = await async_get_notification_status(hass, notifications.get("wechat", {}))
            return self.json({"success": True, "data": status})
        except Exception as err:
            _LOGGER.error("读取通知状态失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="通知状态异常",
                    message=f"读取通知状态失败: {err}",
                    error_key=f"panel-notify-status:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelNotificationsTestView(HomeAssistantView):
    """Send one test notification."""

    url = "/api/netcafe/panel/notifications/test"
    name = "api:netcafe:panel:notifications:test"
    requires_auth = False

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        try:
            config_data = await async_load_system_config(hass)
            notifications = normalize_notifications_config(config_data.get("notifications"))
            result = await async_send_test_notification(hass, notifications.get("wechat", {}))
            return self.json({"success": bool(result.get("success")), "data": result, "message": result.get("message", "")})
        except Exception as err:
            _LOGGER.error("测试通知发送失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="通知测试异常",
                    message=f"测试通知发送失败: {err}",
                    error_key=f"panel-notify-test:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelNotificationsPreviewView(HomeAssistantView):
    """Return the current notification preview text without sending."""

    url = "/api/netcafe/panel/notifications/preview"
    name = "api:netcafe:panel:notifications:preview"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        try:
            data = await async_get_notification_preview(hass)
            return self.json({"success": True, "data": data})
        except Exception as err:
            _LOGGER.error("读取通知预览失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="通知预览异常",
                    message=f"读取通知预览失败: {err}",
                    error_key=f"panel-notify-preview:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelNotificationsWechatQrView(HomeAssistantView):
    """Proxy cn_im_hub WeChat qr flow for the panel."""

    url = "/api/netcafe/panel/notifications/wechat/qr"
    name = "api:netcafe:panel:notifications:wechat:qr"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        try:
            status = await async_get_wechat_qr_status(hass)
            return self.json({"success": True, "data": status})
        except Exception as err:
            _LOGGER.error("读取微信二维码状态失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="微信二维码状态异常",
                    message=f"读取微信二维码状态失败: {err}",
                    error_key=f"panel-notify-wechat-qr-get:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        try:
            payload = await request.json()
        except Exception:
            payload = {}
        action = str(payload.get("action", "start") or "start").strip().lower()

        try:
            if action == "poll":
                status = await async_poll_wechat_qr_flow(hass)
            else:
                status = await async_start_wechat_qr_flow(hass)
            success = status.get("state") not in {"missing_integration", "unsupported", "failed"}
            return self.json({"success": success, "data": status, "message": status.get("message", "")})
        except Exception as err:
            _LOGGER.error("同步微信二维码失败: %s", err, exc_info=True)
            hass.async_create_task(
                async_notify_panel_error(
                    hass,
                    title="微信二维码同步异常",
                    message=f"同步微信二维码失败: {err}",
                    error_key=f"panel-notify-wechat-qr-post:{type(err).__name__}:{str(err)}",
                )
            )
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelLicenseStatusView(HomeAssistantView):
    """Return the current license status."""

    url = "/api/netcafe/panel/license/status"
    name = "api:netcafe:panel:license:status"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        try:
            return self.json({"success": True, "data": await _get_license_status(hass)})
        except Exception as err:
            _LOGGER.error("读取卡密状态失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelLicenseActivateView(HomeAssistantView):
    """Activate the license through the panel endpoint."""

    url = "/api/netcafe/panel/license/activate"
    name = "api:netcafe:panel:license:activate"
    requires_auth = True

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        license_key = str(payload.get("license_key", "")).strip().upper()
        device_id = str(payload.get("device_id", "")).strip() or None
        if not license_key:
            return self.json({"success": False, "message": "缺少 license_key"}, status_code=400)

        await hass.services.async_call(
            DOMAIN,
            "activate_license",
            {"license_key": license_key, "device_id": device_id or ""},
            blocking=True,
            return_response=False,
        )
        status = await _get_license_status(hass)
        status_code = 200 if status.get("is_valid") else 400
        return self.json({"success": status.get("is_valid", False), "data": status}, status_code=status_code)


class NetcafePanelAuthRegisterView(HomeAssistantView):
    """Register one panel user through the remote license system."""

    url = "/api/netcafe/panel/auth/register"
    name = "api:netcafe:panel:auth:register"
    requires_auth = False

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        try:
            result = await _proxy_remote_auth_request(
                hass,
                "register",
                {
                    "username": str(payload.get("username", "")).strip(),
                    "password": str(payload.get("password", "")),
                    "license_key": str(payload.get("license_key", "")).strip(),
                    "email": str(payload.get("email", "")).strip(),
                },
            )
            return self.json(result, status_code=200 if result.get("success") else 400)
        except RemoteAuthError as err:
            return self.json({"success": False, "message": str(err)}, status_code=err.status_code)
        except Exception as err:
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelAuthLoginView(HomeAssistantView):
    """Login one panel user through the remote license system."""

    url = "/api/netcafe/panel/auth/login"
    name = "api:netcafe:panel:auth:login"
    requires_auth = False

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        try:
            result = await _proxy_remote_auth_request(
                hass,
                "login",
                {
                    "username": str(payload.get("username", "")).strip(),
                    "password": str(payload.get("password", "")),
                },
            )
            return self.json(result, status_code=200 if result.get("success") else 401)
        except RemoteAuthError as err:
            return self.json({"success": False, "message": str(err)}, status_code=err.status_code)
        except Exception as err:
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelAuthSessionView(HomeAssistantView):
    """Validate one panel auth token."""

    url = "/api/netcafe/panel/auth/session"
    name = "api:netcafe:panel:auth:session"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        payload, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        license_status = await _sync_license_from_panel_auth(hass, payload)
        return self.json(
            {
                "success": True,
                "data": {
                    "user": {
                        "id": int(payload.get("uid", 0)),
                        "username": str(payload.get("username", "")),
                        "license_key": str(payload.get("license_key", "")),
                    },
                    "license": license_status,
                },
            }
        )


class NetcafePanelUploadView(HomeAssistantView):
    """Upload a logo image into Home Assistant's www directory."""

    url = "/api/netcafe/panel/upload/logo"
    name = "api:netcafe:panel:upload:logo"
    requires_auth = False

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        try:
            data_dict = await request.post()
            field = data_dict.get("file")
            if field is None or not getattr(field, "filename", None):
                return self.json({"success": False, "message": "未找到上传文件，请选择 file 字段。"}, status_code=400)

            filename = field.filename or "upload.png"
            ext = os.path.splitext(filename)[1].lower()
            if ext not in _ALLOWED_UPLOAD_EXTENSIONS:
                return self.json(
                    {"success": False, "message": f"不支持的文件类型 {ext}，仅支持: {', '.join(sorted(_ALLOWED_UPLOAD_EXTENSIONS))}"},
                    status_code=400,
                )

            file_data = field.file.read()
            if not file_data:
                return self.json({"success": False, "message": "上传文件内容为空。"}, status_code=400)
            if len(file_data) > _MAX_UPLOAD_SIZE:
                return self.json({"success": False, "message": f"文件大小超过限制 (最大 {_MAX_UPLOAD_SIZE // 1024 // 1024} MB)。"}, status_code=400)

            www_root = hass.config.path("www")
            upload_dir = os.path.join(www_root, _HA_WWW_UPLOAD_SUBDIR)
            safe_name = _BRAND_LOGO_BASENAME + ext
            target_path = os.path.join(upload_dir, safe_name)

            await hass.async_add_executor_job(_ensure_directory_sync, upload_dir)

            stale_paths = [
                os.path.join(upload_dir, _BRAND_LOGO_BASENAME + candidate_ext)
                for candidate_ext in _ALLOWED_UPLOAD_EXTENSIONS
                if candidate_ext != ext
            ]
            for stale_path in stale_paths:
                await hass.async_add_executor_job(_delete_file_if_exists_sync, stale_path)

            await hass.async_add_executor_job(_write_binary_file_sync, target_path, file_data)

            version = int(time.time())
            asset_url = f"/local/{_HA_WWW_UPLOAD_SUBDIR}/{safe_name}?v={version}"
            _LOGGER.info("Logo 图片已上传到 Home Assistant www: %s -> %s", target_path, asset_url)
            return self.json(
                {
                    "success": True,
                    "data": {
                        "url": asset_url,
                        "filename": safe_name,
                        "storage_path": f"/config/www/{_HA_WWW_UPLOAD_SUBDIR}/{safe_name}",
                    },
                }
            )
        except Exception as err:
            _LOGGER.error("Logo 上传失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelCurrentLogoView(HomeAssistantView):
    """Serve the current uploaded brand logo from HA www."""

    url = "/api/netcafe/panel/logo/current"
    name = "api:netcafe:panel:logo:current"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json_message("Home Assistant 实例未就绪", status_code=500)

        logo_path = await hass.async_add_executor_job(_find_uploaded_brand_logo_path, hass.config.config_dir)
        if not logo_path:
            return self.json_message("Logo not found", status_code=404)

        body = await hass.async_add_executor_job(_read_binary_file_sync, logo_path)
        if body is None:
            return self.json_message("Logo not found", status_code=404)

        content_type, _ = mimetypes.guess_type(logo_path)
        return web.Response(
            body=body,
            content_type=content_type or "application/octet-stream",
            headers={"Cache-Control": "no-store"},
        )


class NetcafeWeatherView(HomeAssistantView):
    """Return current weather payload for the panel."""

    url = "/api/netcafe/weather"
    name = "api:netcafe:weather"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)

        coordinator = await _get_weather_coordinator(hass)
        if coordinator is None:
            return self.json({"success": True, "data": {"configured": False, "last_error": "未找到集成配置。"}})

        try:
            if not coordinator.data:
                await coordinator.async_refresh()
            data = dict(coordinator.data or {})
            return self.json({"success": True, "data": data})
        except Exception as err:
            _LOGGER.error("读取天气数据失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelWeatherConfigView(HomeAssistantView):
    """Read and update weather location settings from the panel."""

    url = "/api/netcafe/panel/weather/config"
    name = "api:netcafe:panel:weather:config"
    requires_auth = False

    async def get(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error

        entry = _get_primary_config_entry(hass)
        if entry is None:
            return self.json({"success": True, "data": {"configured": False}})

        config = get_weather_entry_config(entry)
        area_id = str(config.get(CONF_WEATHER_AREA_ID, "")).strip()
        area_name = str(config.get(CONF_WEATHER_AREA_NAME, "")).strip()
        area_code = str(config.get(CONF_WEATHER_AREA_CODE, "")).strip()
        return self.json(
            {
                "success": True,
                "data": {
                    "configured": bool(area_id),
                    "domain": normalize_weather_domain(config.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN)),
                    "area_id": area_id,
                    "area_name": area_name,
                    "area_code": area_code,
                    "latitude": config.get(CONF_WEATHER_LATITUDE),
                    "longitude": config.get(CONF_WEATHER_LONGITUDE),
                },
            }
        )

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error
        lock_response = await _get_panel_lock_response(self, hass)
        if lock_response is not None:
            return lock_response

        entry = _get_primary_config_entry(hass)
        if entry is None:
            return self.json({"success": False, "message": "未找到当前集成配置。"}, status_code=400)

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        area_id = str(payload.get("area_id", "")).strip()
        domain = normalize_weather_domain(payload.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN))
        if not area_id:
            return self.json({"success": False, "message": "请选择天气地区。"}, status_code=400)

        try:
            client = NetcafeWeatherClient(hass, domain)
            station = await client.async_get_station(area_id=area_id)
            new_data = dict(entry.data)
            new_data.update(build_weather_entry_data(domain, station))
            hass.config_entries.async_update_entry(entry, data=new_data)

            coordinator = await _get_weather_coordinator(hass)
            if coordinator is not None:
                await coordinator.async_refresh()

            return self.json(
                {
                    "success": True,
                    "data": {
                        "configured": True,
                        "domain": domain,
                        "area_id": station.area_id,
                        "area_name": station.area_name,
                        "area_code": station.area_code,
                        "latitude": station.latitude,
                        "longitude": station.longitude,
                    },
                }
            )
        except Exception as err:
            _LOGGER.error("保存天气地区失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)


class NetcafePanelWeatherSearchView(HomeAssistantView):
    """Search weather locations from the panel."""

    url = "/api/netcafe/panel/weather/search"
    name = "api:netcafe:panel:weather:search"
    requires_auth = False

    async def post(self, request):
        hass = _get_hass_from_request(request, getattr(self, "hass", None))
        if hass is None:
            return self.json({"success": False, "message": "Home Assistant 实例未就绪"}, status_code=500)
        _, auth_error = await _require_panel_auth(self, hass, request)
        if auth_error is not None:
            return auth_error

        try:
            payload = await request.json()
        except Exception:
            payload = {}

        keyword = str(payload.get("keyword", "")).strip()
        domain = normalize_weather_domain(payload.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN))
        if not keyword:
            return self.json({"success": False, "message": "请输入城市或区县名称。"}, status_code=400)

        try:
            client = NetcafeWeatherClient(hass, domain)
            results = await client.async_search_locations(keyword)
            items = [
                {
                    "area_id": area_id,
                    "label": label,
                }
                for area_id, label in results.items()
            ]
            return self.json({"success": True, "data": {"items": items}})
        except Exception as err:
            _LOGGER.error("搜索天气地区失败: %s", err, exc_info=True)
            return self.json({"success": False, "message": str(err)}, status_code=500)
