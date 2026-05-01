"""WeChat notification helpers for netcafe automation."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN

try:
    from homeassistant.components.recorder.history import state_changes_during_period
except ImportError:  # pragma: no cover - depends on HA runtime
    state_changes_during_period = None

_LOGGER = logging.getLogger(__name__)

NOTIFY_RUNTIME_KEY = "notifications_runtime"
CHANNEL_PROVIDER = "cn_im_hub_wechat"
CN_IM_HUB_DOMAIN = "cn_im_hub"
CN_IM_HUB_SEND_SERVICE = "send_message"
CN_IM_HUB_WECHAT_SUBENTRY_TYPE = "wechat"
DEFAULT_CHANNEL = "wechat/user_id"
DEFAULT_ALERT_SCOPE = "offline_and_errors"
DEFAULT_DAILY_BRIEF_TIME = "23:00"
DEFAULT_OFFLINE_COOLDOWN_MINUTES = 30
DEFAULT_ERROR_COOLDOWN_MINUTES = 30
STATE_FILENAME = "notifications_state.json"


def default_wechat_notification_config() -> dict[str, Any]:
    """Return default WeChat notification config."""
    return {
        "enabled": False,
        "channel_provider": CHANNEL_PROVIDER,
        "channel": DEFAULT_CHANNEL,
        "target": "",
        "wechat_account_id": "",
        "alert_scope": DEFAULT_ALERT_SCOPE,
        "daily_brief_enabled": True,
        "daily_brief_time": DEFAULT_DAILY_BRIEF_TIME,
        "offline_cooldown_minutes": DEFAULT_OFFLINE_COOLDOWN_MINUTES,
    }


def normalize_wechat_notification_config(value: Any) -> dict[str, Any]:
    """Normalize WeChat notification config."""
    raw = value if isinstance(value, dict) else {}
    config = default_wechat_notification_config()
    config["enabled"] = bool(raw.get("enabled", config["enabled"]))
    config["channel_provider"] = CHANNEL_PROVIDER
    config["channel"] = str(raw.get("channel", DEFAULT_CHANNEL) or "").strip() or DEFAULT_CHANNEL
    config["target"] = str(raw.get("target", raw.get("recipient_id", "")) or "").strip()
    config["wechat_account_id"] = str(raw.get("wechat_account_id", "") or "").strip()
    scope = str(raw.get("alert_scope", DEFAULT_ALERT_SCOPE) or "").strip().lower()
    config["alert_scope"] = scope if scope in {"offline_and_errors", "offline_only", "errors_only"} else DEFAULT_ALERT_SCOPE
    config["daily_brief_enabled"] = bool(raw.get("daily_brief_enabled", config["daily_brief_enabled"]))
    config["daily_brief_time"] = _normalize_time_text(raw.get("daily_brief_time"), DEFAULT_DAILY_BRIEF_TIME)
    try:
        cooldown = max(0, int(raw.get("offline_cooldown_minutes", DEFAULT_OFFLINE_COOLDOWN_MINUTES)))
    except (TypeError, ValueError):
        cooldown = DEFAULT_OFFLINE_COOLDOWN_MINUTES
    config["offline_cooldown_minutes"] = cooldown
    return config


def normalize_notifications_config(value: Any) -> dict[str, Any]:
    """Normalize root notifications config."""
    raw = value if isinstance(value, dict) else {}
    return {
        "wechat": normalize_wechat_notification_config(raw.get("wechat")),
    }


def _normalize_time_text(value: Any, default: str) -> str:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%H:%M").strftime("%H:%M")
    except (TypeError, ValueError):
        return default


def _runtime(hass: HomeAssistant) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    runtime = domain_data.get(NOTIFY_RUNTIME_KEY)
    if not isinstance(runtime, dict):
        runtime = {
            "offline_events": {},
            "error_events": {},
            "last_send_status": "",
            "last_send_at": "",
            "last_send_error": "",
            "channel_status": {},
            "wechat_qr": {},
            "persisted": None,
        }
        domain_data[NOTIFY_RUNTIME_KEY] = runtime
    if runtime.get("persisted") is None:
        runtime["persisted"] = _load_persisted_state(hass)
    return runtime


def _state_file_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("netcafe_data")) / STATE_FILENAME


def _load_persisted_state(hass: HomeAssistant) -> dict[str, Any]:
    path = _state_file_path(hass)
    try:
        if not path.exists():
            return {"daily_brief": {"last_sent_date": ""}}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        _LOGGER.warning("读取通知状态文件失败: %s", err)
        return {"daily_brief": {"last_sent_date": ""}}


def _save_persisted_state(hass: HomeAssistant, payload: dict[str, Any]) -> None:
    path = _state_file_path(hass)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as err:
        _LOGGER.warning("保存通知状态文件失败: %s", err)


def _get_cn_im_hub_entries(hass: HomeAssistant) -> list[Any]:
    return list(hass.config_entries.async_entries(CN_IM_HUB_DOMAIN))


def _get_wechat_accounts(hass: HomeAssistant) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    for entry in _get_cn_im_hub_entries(hass):
        subentries = getattr(entry, "subentries", {}) or {}
        for subentry in subentries.values():
            if str(getattr(subentry, "subentry_type", "") or "").strip() != CN_IM_HUB_WECHAT_SUBENTRY_TYPE:
                continue
            data = dict(getattr(subentry, "data", {}) or {})
            title = str(getattr(subentry, "title", "") or "").strip()
            accounts.append(
                {
                    "entry_id": str(getattr(entry, "entry_id", "") or "").strip(),
                    "subentry_id": str(getattr(subentry, "subentry_id", "") or "").strip(),
                    "title": title,
                    "wechat_account_id": str(data.get("wechat_account_id", "") or "").strip(),
                    "wechat_user_id": str(data.get("wechat_user_id", "") or "").strip(),
                }
            )
    return accounts


def _resolve_wechat_account_hint(hass: HomeAssistant, config: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    accounts = _get_wechat_accounts(hass)
    configured = str(config.get("wechat_account_id", "") or "").strip()
    if configured:
        return configured, accounts
    if len(accounts) == 1:
        only = accounts[0]
        return only.get("title") or only.get("wechat_account_id") or "", accounts
    return "", accounts


def _is_wechat_channel(channel: str) -> bool:
    return str(channel or "").strip().lower().startswith("wechat/")


def _extract_markdown_image_url(markdown: str) -> str:
    matched = re.search(r"!\[[^\]]*\]\(([^)]+)\)", str(markdown or ""))
    return matched.group(1).strip() if matched else ""


def _get_wechat_qr_runtime(hass: HomeAssistant) -> dict[str, Any]:
    runtime = _runtime(hass)
    qr_runtime = runtime.get("wechat_qr")
    if not isinstance(qr_runtime, dict):
        qr_runtime = {}
        runtime["wechat_qr"] = qr_runtime
    return qr_runtime


def _clear_wechat_qr_runtime(hass: HomeAssistant) -> None:
    runtime = _get_wechat_qr_runtime(hass)
    runtime.clear()


def _format_wechat_qr_payload(hass: HomeAssistant) -> dict[str, Any]:
    qr_runtime = _get_wechat_qr_runtime(hass)
    accounts = _get_wechat_accounts(hass)
    active = bool(qr_runtime.get("flow_id"))
    state = str(qr_runtime.get("state", "") or "").strip() or ("connected" if accounts else "idle")
    return {
        "active": active,
        "state": state,
        "flow_id": str(qr_runtime.get("flow_id", "") or "").strip(),
        "step_id": str(qr_runtime.get("step_id", "") or "").strip(),
        "started_at": str(qr_runtime.get("started_at", "") or "").strip(),
        "updated_at": str(qr_runtime.get("updated_at", "") or "").strip(),
        "qr_url": str(qr_runtime.get("qr_url", "") or "").strip(),
        "qr_data_url": str(qr_runtime.get("qr_data_url", "") or "").strip(),
        "message": str(qr_runtime.get("message", "") or "").strip(),
        "error": str(qr_runtime.get("error", "") or "").strip(),
        "accounts": accounts,
        "accounts_count": len(accounts),
    }


def _remember_wechat_qr_result(hass: HomeAssistant, result: dict[str, Any], *, entry_id: str = "") -> dict[str, Any]:
    qr_runtime = _get_wechat_qr_runtime(hass)
    now_text = dt_util.now().isoformat()
    placeholders = result.get("description_placeholders") if isinstance(result, dict) else {}
    placeholders = placeholders if isinstance(placeholders, dict) else {}
    qr_url = str(placeholders.get("wechat_qr_url") or placeholders.get("qr_url") or qr_runtime.get("qr_url", "") or "").strip()
    qr_data_url = str(placeholders.get("wechat_qr_data_url") or "").strip()
    if not qr_data_url:
        qr_data_url = _extract_markdown_image_url(placeholders.get("qr_markdown", ""))

    result_type = str(result.get("type", "") or "").strip().lower()
    state = "idle"
    message = ""
    error = ""
    if result_type == "form":
        state = "pending_scan" if str(result.get("step_id", "") or "") == "auth_wait" else "form"
        errors = result.get("errors") if isinstance(result.get("errors"), dict) else {}
        if errors.get("base") == "auth_not_confirmed":
            message = "二维码已同步，等待微信扫码确认。"
        elif errors:
            error = ",".join(f"{key}:{value}" for key, value in errors.items())
            message = "微信扫码状态待确认。"
        else:
            message = "二维码已同步到面板，请使用微信扫码。"
    elif result_type == "create_entry":
        state = "connected"
        message = "微信账号已连接到 cn_im_hub。"
        qr_url = ""
        qr_data_url = ""
    elif result_type == "abort":
        state = "aborted"
        reason = str(result.get("reason", "") or "").strip()
        error = reason
        message = f"二维码流程已结束: {reason or 'aborted'}"
        qr_url = ""
        qr_data_url = ""
    else:
        state = result_type or "idle"
        message = str(result.get("description", "") or "").strip()

    if entry_id:
        qr_runtime["entry_id"] = entry_id
    qr_runtime["flow_id"] = str(result.get("flow_id", qr_runtime.get("flow_id", "")) or "").strip()
    qr_runtime["step_id"] = str(result.get("step_id", qr_runtime.get("step_id", "")) or "").strip()
    qr_runtime["state"] = state
    qr_runtime["started_at"] = str(qr_runtime.get("started_at", "") or now_text)
    qr_runtime["updated_at"] = now_text
    qr_runtime["qr_url"] = qr_url
    qr_runtime["qr_data_url"] = qr_data_url
    qr_runtime["message"] = message
    qr_runtime["error"] = error
    if state in {"connected", "aborted"}:
        qr_runtime["flow_id"] = ""
        qr_runtime["step_id"] = ""
    return _format_wechat_qr_payload(hass)


async def async_get_wechat_qr_status(hass: HomeAssistant) -> dict[str, Any]:
    """Return the current qr sync status."""
    return _format_wechat_qr_payload(hass)


async def async_start_wechat_qr_flow(hass: HomeAssistant) -> dict[str, Any]:
    """Start a cn_im_hub WeChat qr flow."""
    entries = _get_cn_im_hub_entries(hass)
    if not entries:
        return {
            **_format_wechat_qr_payload(hass),
            "state": "missing_integration",
            "message": "未安装 cn_im_hub，暂时无法同步微信二维码。",
            "error": "cn_im_hub_missing",
        }

    subentries_manager = getattr(hass.config_entries, "subentries", None)
    if subentries_manager is None or not hasattr(subentries_manager, "async_init"):
        return {
            **_format_wechat_qr_payload(hass),
            "state": "unsupported",
            "message": "当前 Home Assistant 版本不支持子配置流同步。",
            "error": "subentry_flow_unsupported",
        }

    existing_flow_id = str(_get_wechat_qr_runtime(hass).get("flow_id", "") or "").strip()
    if existing_flow_id and hasattr(subentries_manager, "async_abort"):
        try:
            subentries_manager.async_abort(existing_flow_id)
        except Exception:
            pass
    _clear_wechat_qr_runtime(hass)

    entry = entries[0]
    try:
        result = await subentries_manager.async_init(
            (entry.entry_id, CN_IM_HUB_WECHAT_SUBENTRY_TYPE),
            context={"source": "user"},
        )
    except Exception as err:
        first_error = err
        try:
            from homeassistant.config_entries import SOURCE_USER, SubentryFlowContext

            result = await subentries_manager.async_init(
                (entry.entry_id, CN_IM_HUB_WECHAT_SUBENTRY_TYPE),
                context=SubentryFlowContext(source=SOURCE_USER),
            )
        except Exception as fallback_err:
            _clear_wechat_qr_runtime(hass)
            return {
                **_format_wechat_qr_payload(hass),
                "state": "failed",
                "message": f"拉起 cn_im_hub 微信二维码失败: {first_error}",
                "error": f"primary={first_error}; fallback={fallback_err}",
            }
    return _remember_wechat_qr_result(hass, result, entry_id=str(entry.entry_id))


async def async_poll_wechat_qr_flow(hass: HomeAssistant) -> dict[str, Any]:
    """Poll one active cn_im_hub WeChat qr flow."""
    qr_runtime = _get_wechat_qr_runtime(hass)
    flow_id = str(qr_runtime.get("flow_id", "") or "").strip()
    if not flow_id:
        return _format_wechat_qr_payload(hass)

    subentries_manager = getattr(hass.config_entries, "subentries", None)
    if subentries_manager is None or not hasattr(subentries_manager, "async_configure"):
        return {
            **_format_wechat_qr_payload(hass),
            "state": "unsupported",
            "message": "当前 Home Assistant 版本不支持二维码轮询。",
            "error": "subentry_flow_unsupported",
        }

    try:
        result = await subentries_manager.async_configure(flow_id, {})
    except Exception as err:
        _clear_wechat_qr_runtime(hass)
        return {
            **_format_wechat_qr_payload(hass),
            "state": "failed",
            "message": "轮询微信二维码状态失败。",
            "error": str(err),
        }
    return _remember_wechat_qr_result(hass, result, entry_id=str(qr_runtime.get("entry_id", "") or ""))


async def async_get_notification_status(hass: HomeAssistant, config: dict[str, Any]) -> dict[str, Any]:
    """Return cn_im_hub notification status."""
    runtime = _runtime(hass)
    status = _detect_channel_status(hass, config)
    runtime["channel_status"] = status
    return {
        **status,
        "last_send_status": runtime.get("last_send_status", ""),
        "last_send_at": runtime.get("last_send_at", ""),
        "last_send_error": runtime.get("last_send_error", ""),
    }


def _detect_channel_status(hass: HomeAssistant, config: dict[str, Any]) -> dict[str, Any]:
    """Detect cn_im_hub availability and config readiness."""
    target = str(config.get("target", "") or "").strip()
    channel = str(config.get("channel", DEFAULT_CHANNEL) or "").strip() or DEFAULT_CHANNEL
    account_id, accounts = _resolve_wechat_account_hint(hass, config)
    explicit_account_id = str(config.get("wechat_account_id", "") or "").strip()
    entries = _get_cn_im_hub_entries(hass)
    service_available = hass.services.has_service(CN_IM_HUB_DOMAIN, CN_IM_HUB_SEND_SERVICE)
    installed = bool(entries) or service_available
    wechat_bound = len(accounts) > 0
    auto_match_enabled = not target
    configured = bool(channel) and (not _is_wechat_channel(channel) or wechat_bound)
    setup_hint = ""
    if not installed:
        setup_hint = "未安装 cn_im_hub 集成，请先在 Home Assistant 中完成安装。"
    elif not service_available:
        setup_hint = "已检测到 cn_im_hub，但发送服务不可用，请检查集成是否正常加载。"
    elif _is_wechat_channel(channel) and not wechat_bound:
        setup_hint = "cn_im_hub 已安装，但还没有绑定微信账号；可在当前页面同步二维码并扫码登录。"
    elif auto_match_enabled:
        setup_hint = "未填写 target，将优先使用 cn_im_hub 当前已选中的微信对象自动匹配。"
    elif not configured:
        setup_hint = "请先补全微信发送配置。"
    else:
        setup_hint = "cn_im_hub 发送服务已就绪。"
    return {
        "provider": CHANNEL_PROVIDER,
        "cn_im_hub_installed": installed,
        "send_service_available": service_available,
        "wechat_configured": configured,
        "wechat_bound": wechat_bound,
        "wechat_accounts_count": len(accounts),
        "wechat_accounts": accounts,
        "channel": channel,
        "target": target,
        "auto_match_enabled": auto_match_enabled,
        "wechat_account_id": explicit_account_id,
        "resolved_wechat_account_id": account_id,
        "setup_hint": setup_hint,
    }


def _alerts_enabled(config: dict[str, Any], *, kind: str) -> bool:
    if not config.get("enabled"):
        return False
    scope = str(config.get("alert_scope", DEFAULT_ALERT_SCOPE) or "").strip().lower()
    if kind == "offline":
        return scope in {"offline_and_errors", "offline_only"}
    if kind == "error":
        return scope in {"offline_and_errors", "errors_only"}
    return False


async def async_notify_device_transition(
    hass: HomeAssistant,
    *,
    config: dict[str, Any],
    device: Any,
    is_offline: bool,
) -> dict[str, Any] | None:
    """Notify when one tracked device changes offline/online state."""
    if not config:
        from .room_control import async_load_system_config

        config = normalize_notifications_config((await async_load_system_config(hass)).get("notifications")).get("wechat", {})
    if not _alerts_enabled(config, kind="offline"):
        return None

    runtime = _runtime(hass)
    entity_key = str(getattr(device, "ip_address", "") or getattr(device, "title", "") or "")
    room_name = str(getattr(device, "room_name", "") or "").strip()
    now = dt_util.now()
    cooldown_minutes = max(0, int(config.get("offline_cooldown_minutes", DEFAULT_OFFLINE_COOLDOWN_MINUTES) or 0))
    offline_events = runtime.setdefault("offline_events", {})
    event_state = offline_events.get(entity_key, {})
    last_offline_at = _parse_dt(event_state.get("last_offline_sent_at"))
    if is_offline and cooldown_minutes > 0 and last_offline_at and now - last_offline_at < timedelta(minutes=cooldown_minutes):
        return None

    title = "设备离线告警" if is_offline else "设备恢复在线"
    current_state = "离线" if is_offline else "在线"
    hint = "请检查终端供电、网络连通性和网卡状态。" if is_offline else "设备已恢复，可继续观察是否稳定。"
    room_prefix = f"{room_name} / " if room_name else ""
    message = f"{room_prefix}{getattr(device, 'title', '') or getattr(device, 'ip_address', '')} 当前状态: {current_state}。{hint}"
    event = {
        "type": "device_offline" if is_offline else "device_recovered",
        "severity": "warning" if is_offline else "info",
        "room_id": "",
        "room_name": room_name,
        "entity_id": getattr(device, "ip_address", ""),
        "title": title,
        "message": message,
        "occurred_at": now.isoformat(),
    }
    result = await async_send_notification_event(hass, config=config, event=event)
    if result.get("success"):
        state = {
            "last_state": "offline" if is_offline else "online",
            "last_offline_sent_at": now.isoformat() if is_offline else event_state.get("last_offline_sent_at", ""),
            "last_recovery_sent_at": now.isoformat() if not is_offline else event_state.get("last_recovery_sent_at", ""),
        }
        offline_events[entity_key] = state
    return result


async def async_notify_runtime_log(hass: HomeAssistant, log_item: dict[str, Any]) -> dict[str, Any] | None:
    """Notify for selected runtime log errors."""
    from .room_control import async_load_system_config

    config = normalize_notifications_config((await async_load_system_config(hass)).get("notifications")).get("wechat", {})
    if not _alerts_enabled(config, kind="error"):
        return None
    level = str(log_item.get("level", "") or "").strip().lower()
    action = str(log_item.get("action", "") or "").strip().lower()
    source = str(log_item.get("source", "") or "").strip().lower()
    if level not in {"error", "warning"}:
        return None
    if not (
        source == "automation"
        or "auth" in action
        or "api" in action
        or "panel" in action
        or "认证" in str(log_item.get("message", ""))
        or "接口" in str(log_item.get("message", ""))
    ):
        return None
    return await async_notify_error(
        hass,
        config=config,
        error_key=f"runtime:{source}:{action}:{str(log_item.get('room_id', ''))}",
        title="自动化异常告警" if source == "automation" else "系统异常告警",
        message=str(log_item.get("message", "") or "").strip(),
        room_id=str(log_item.get("room_id", "") or "").strip(),
        room_name=str(log_item.get("room_name", "") or "").strip(),
        entity_id=",".join(log_item.get("entity_ids", []) or []),
        occurred_at=str(log_item.get("timestamp", "") or dt_util.now().isoformat()),
    )


async def async_notify_panel_error(
    hass: HomeAssistant,
    *,
    title: str,
    message: str,
    error_key: str,
    room_id: str = "",
    room_name: str = "",
    entity_id: str = "",
) -> dict[str, Any] | None:
    """Notify for panel auth/api errors."""
    from .room_control import async_load_system_config

    config = normalize_notifications_config((await async_load_system_config(hass)).get("notifications")).get("wechat", {})
    return await async_notify_error(
        hass,
        config=config,
        error_key=error_key,
        title=title,
        message=message,
        room_id=room_id,
        room_name=room_name,
        entity_id=entity_id,
        occurred_at=dt_util.now().isoformat(),
    )


async def async_notify_error(
    hass: HomeAssistant,
    *,
    config: dict[str, Any],
    error_key: str,
    title: str,
    message: str,
    room_id: str,
    room_name: str,
    entity_id: str,
    occurred_at: str,
) -> dict[str, Any] | None:
    """Notify one deduplicated error event."""
    if not _alerts_enabled(config, kind="error"):
        return None
    runtime = _runtime(hass)
    error_events = runtime.setdefault("error_events", {})
    last_sent_at = _parse_dt(error_events.get(error_key))
    now = dt_util.now()
    if last_sent_at and now - last_sent_at < timedelta(minutes=DEFAULT_ERROR_COOLDOWN_MINUTES):
        return None
    event = {
        "type": "runtime_error",
        "severity": "error",
        "room_id": room_id,
        "room_name": room_name,
        "entity_id": entity_id,
        "title": title,
        "message": message,
        "occurred_at": occurred_at,
    }
    result = await async_send_notification_event(hass, config=config, event=event)
    if result.get("success"):
        error_events[error_key] = now.isoformat()
    return result


async def async_send_test_notification(hass: HomeAssistant, config: dict[str, Any]) -> dict[str, Any]:
    """Send one manual current-log preview message."""
    event = await _build_current_log_event(hass)
    result = await async_send_notification_event(hass, config=config, event=event)
    result["preview_text"] = _format_event_text(event)
    result["title"] = str(event.get("title", "") or "")
    result["occurred_at_text"] = _friendly_time_text(event.get("occurred_at"))
    return result


async def async_get_notification_preview(hass: HomeAssistant) -> dict[str, Any]:
    """Return the current manual-preview payload without sending it."""
    event = await _build_current_log_event(hass)
    return {
        "title": str(event.get("title", "") or ""),
        "occurred_at": str(event.get("occurred_at", "") or ""),
        "occurred_at_text": _friendly_time_text(event.get("occurred_at")),
        "preview_text": _format_event_text(event),
        "event": event,
    }


async def async_send_notification_event(
    hass: HomeAssistant,
    *,
    config: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    """Send one standard notification event through cn_im_hub."""
    runtime = _runtime(hass)
    status = _detect_channel_status(hass, config)
    runtime["channel_status"] = status
    if not status.get("cn_im_hub_installed"):
        return _remember_send_result(runtime, success=False, error="未安装 cn_im_hub 集成")
    if not status.get("send_service_available"):
        return _remember_send_result(runtime, success=False, error="cn_im_hub.send_message 服务不可用")
    if _is_wechat_channel(str(config.get("channel", DEFAULT_CHANNEL) or "")) and not status.get("wechat_bound"):
        return _remember_send_result(runtime, success=False, error="cn_im_hub 尚未绑定微信账号")

    service_data = {
        "channel": str(config.get("channel", DEFAULT_CHANNEL) or "").strip() or DEFAULT_CHANNEL,
        "message": _format_event_text(event),
    }
    target = str(config.get("target", "") or "").strip()
    if target:
        service_data["target"] = target
    account_id = str(config.get("wechat_account_id", "") or "").strip() or str(status.get("resolved_wechat_account_id", "") or "").strip()
    if account_id:
        service_data["wechat_account_id"] = account_id

    try:
        await hass.services.async_call(
            CN_IM_HUB_DOMAIN,
            CN_IM_HUB_SEND_SERVICE,
            service_data,
            blocking=True,
        )
    except Exception as err:
        return _remember_send_result(runtime, success=False, error="cn_im_hub 发送失败", detail=str(err))
    return _remember_send_result(runtime, success=True, detail="消息已交给 cn_im_hub.send_message")


def _remember_send_result(runtime: dict[str, Any], *, success: bool, error: str = "", detail: str = "") -> dict[str, Any]:
    now_text = dt_util.now().isoformat()
    runtime["last_send_status"] = "success" if success else "failed"
    runtime["last_send_at"] = now_text
    runtime["last_send_error"] = error or detail or ""
    return {
        "success": success,
        "sent_at": now_text,
        "message": "发送成功" if success else (error or detail or "发送失败"),
        "detail": detail,
    }


def _format_event_text(event: dict[str, Any]) -> str:
    title = str(event.get("title", "") or "通知").strip()
    occurred_at = _friendly_time_text(event.get("occurred_at"))
    room_name = str(event.get("room_name", "") or "").strip()
    entity_id = str(event.get("entity_id", "") or "").strip()
    state_hint = str(event.get("message", "") or "").strip()
    lines = [f"[智慧网吧] {title}", f"时间: {occurred_at}"]
    if room_name:
        lines.append(f"房间: {room_name}")
    if entity_id:
        lines.append(f"对象: {entity_id}")
    if state_hint:
        lines.append(f"内容: {state_hint}")
    return "\n".join(lines)


def _friendly_time_text(value: Any) -> str:
    dt_value = _parse_dt(value)
    if dt_value is None:
        return dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        return dt_util.as_local(dt_value).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value or "").strip() or dt_util.now().strftime("%Y-%m-%d %H:%M:%S")


def _presence_state_value(value: Any) -> bool:
    raw_state = ""
    if isinstance(value, dict):
        raw_state = str(value.get("state", "") or "").strip().lower()
    else:
        raw_state = str(getattr(value, "state", "") or "").strip().lower()
    if raw_state in {"home", "on", "online", "connected", "present", "occupied", "detected", "open", "true"}:
        return True
    if raw_state in {"off", "offline", "disconnected", "not_home", "away", "absent", "unoccupied", "clear", "false", "unknown", "unavailable"}:
        return False
    try:
        return float(raw_state) > 0
    except (TypeError, ValueError):
        return False


def _history_state_changed_at(value: Any) -> datetime | None:
    if isinstance(value, dict):
        return _parse_dt(value.get("last_changed") or value.get("last_updated"))
    return _parse_dt(getattr(value, "last_changed", None) or getattr(value, "last_updated", None))


def _load_history_rows_sync(
    hass: HomeAssistant,
    start_time: datetime,
    end_time: datetime,
    entity_ids: list[str],
) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = {}
    if state_changes_during_period is None:
        return result
    for entity_id in entity_ids:
        rows = state_changes_during_period(
            hass,
            start_time,
            end_time,
            entity_id,
            False,
            False,
        )
        result[entity_id] = list((rows or {}).get(entity_id, []))
    return result


def _calculate_entity_active_minutes(
    rows: list[Any],
    *,
    current_state: Any,
    start_time: datetime,
    end_time: datetime,
) -> int:
    ordered_rows = sorted(
        [item for item in rows if _history_state_changed_at(item) is not None],
        key=lambda item: _history_state_changed_at(item) or start_time,
    )
    active_since: datetime | None = None
    total_minutes = 0

    for item in ordered_rows:
        changed_at = _history_state_changed_at(item)
        if changed_at is None:
            continue
        is_active = _presence_state_value(item)
        if changed_at <= start_time:
            active_since = start_time if is_active else None
            continue
        if active_since is not None:
            total_minutes += max(0, int((changed_at - active_since).total_seconds() // 60))
            active_since = None
        if is_active:
            active_since = changed_at

    if active_since is None:
        current_changed_at = _parse_dt(getattr(current_state, "last_changed", None)) if current_state is not None else None
        if current_state is not None and _presence_state_value(current_state):
            if not ordered_rows:
                resume_at = start_time
                if current_changed_at is not None:
                    resume_at = max(start_time, current_changed_at)
                active_since = resume_at
    if active_since is not None:
        total_minutes += max(0, int((end_time - active_since).total_seconds() // 60))
    return max(0, total_minutes)


async def _calculate_today_presence_hours(hass: HomeAssistant, rooms: list[dict[str, Any]]) -> float | None:
    from .room_control import _collect_room_presence_matches, _get_cached_room_config_for_record, get_room_records

    if state_changes_during_period is None:
        return None

    now = dt_util.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    room_records = {
        str(item.get("room_id", "") or "").strip(): item
        for item in get_room_records(hass)
    }

    room_sources: dict[str, tuple[str, list[str], list[str]]] = {}
    all_entity_ids: set[str] = set()
    for room in rooms:
        room_id = str(room.get("room_id", "") or "").strip()
        room_name = str(room.get("room_name", "") or "").strip()
        record = room_records.get(room_id)
        if not room_id or record is None:
            continue
        room_config = _get_cached_room_config_for_record(
            hass,
            str(record.get("entry_id", "") or "").strip(),
            room_id,
            room_name,
        )
        automation = room_config.get("automation", {}) if isinstance(room_config, dict) else {}
        trigger_mode = str(automation.get("trigger_mode") or "device_tracker").strip().lower()
        if trigger_mode not in {"device_tracker", "sensor", "hybrid"}:
            trigger_mode = "device_tracker"

        tracker_ids: list[str] = []
        sensor_ids: list[str] = []
        if trigger_mode in {"device_tracker", "hybrid"}:
            tracker_ids = [
                str(item.get("entity_id", "") or "").strip()
                for item in _collect_room_presence_matches(
                    hass,
                    room_name,
                    domains=("device_tracker",),
                    include_keywords=automation.get("device_tracker_include_keywords", []) or [],
                    exclude_keywords=automation.get("device_tracker_exclude_keywords", []) or [],
                    explicit_entity_id=str(automation.get("device_tracker_entity") or ""),
                )
                if str(item.get("entity_id", "") or "").strip()
            ]
        if trigger_mode in {"sensor", "hybrid"}:
            sensor_ids = [
                str(item.get("entity_id", "") or "").strip()
                for item in _collect_room_presence_matches(
                    hass,
                    room_name,
                    domains=("sensor", "binary_sensor"),
                    include_keywords=automation.get("presence_sensor_include_keywords", []) or [],
                    exclude_keywords=automation.get("presence_sensor_exclude_keywords", []) or [],
                    explicit_entity_id=str(automation.get("presence_sensor_entity") or ""),
                )
                if str(item.get("entity_id", "") or "").strip()
            ]
        if not tracker_ids and not sensor_ids:
            continue
        room_sources[room_id] = (trigger_mode, tracker_ids, sensor_ids)
        all_entity_ids.update(tracker_ids)
        all_entity_ids.update(sensor_ids)

    if not all_entity_ids:
        return None

    history_rows = await hass.async_add_executor_job(
        _load_history_rows_sync,
        hass,
        day_start,
        now,
        sorted(all_entity_ids),
    )

    occupied_minutes_total = 0
    for room_id, (trigger_mode, tracker_ids, sensor_ids) in room_sources.items():
        tracker_minutes = max(
            (
                _calculate_entity_active_minutes(
                    history_rows.get(entity_id, []),
                    current_state=hass.states.get(entity_id),
                    start_time=day_start,
                    end_time=now,
                )
                for entity_id in tracker_ids
            ),
            default=0,
        )
        sensor_minutes = max(
            (
                _calculate_entity_active_minutes(
                    history_rows.get(entity_id, []),
                    current_state=hass.states.get(entity_id),
                    start_time=day_start,
                    end_time=now,
                )
                for entity_id in sensor_ids
            ),
            default=0,
        )
        if trigger_mode == "device_tracker":
            occupied_minutes_total += tracker_minutes
        elif trigger_mode == "sensor":
            occupied_minutes_total += sensor_minutes
        else:
            occupied_minutes_total += max(tracker_minutes, sensor_minutes)

    return round(occupied_minutes_total / 60, 1)


async def _build_current_log_event(hass: HomeAssistant) -> dict[str, Any]:
    from .room_control import async_get_recent_room_logs, async_get_room_overview

    overview = await async_get_room_overview(hass)
    rooms = overview.get("rooms", []) if isinstance(overview, dict) else []
    all_logs = await async_get_recent_room_logs(hass, limit=200)
    energy = overview.get("energy", {}) if isinstance(overview, dict) else {}
    now = dt_util.now()
    today = now.date().isoformat()
    logs = [item for item in all_logs if str(item.get("timestamp", "") or "").strip().startswith(today)]

    room_total = len(rooms)
    occupied_total = sum(1 for room in rooms if room.get("occupied"))
    online_devices = 0
    total_devices = 0
    ac_online = ac_on = 0
    light_online = light_on = 0
    fresh_online = fresh_on = 0

    for room in rooms:
        computers = room.get("computers", []) or []
        total_devices += len(computers)
        online_devices += sum(1 for item in computers if item.get("is_connected"))
        mapped = room.get("mapped", {}) if isinstance(room.get("mapped"), dict) else {}
        ac = mapped.get("ac")
        if isinstance(ac, dict) and ac.get("exists", True):
            ac_online += 1 if ac.get("available", True) else 0
            ac_on += 1 if ac.get("is_on") else 0
        lights = mapped.get("lights", []) if isinstance(mapped.get("lights"), list) else []
        light_online += sum(1 for item in lights if isinstance(item, dict) and item.get("available", True))
        light_on += sum(1 for item in lights if isinstance(item, dict) and item.get("is_on"))
        fresh = mapped.get("fresh_air")
        if isinstance(fresh, dict) and fresh.get("exists", True):
            fresh_online += 1 if fresh.get("available", True) else 0
            fresh_on += 1 if fresh.get("is_on") else 0

    online_rate = f"{round((online_devices / total_devices) * 100, 1)}%" if total_devices else "--"
    daily_energy = energy.get("daily_energy_kwh")
    daily_cost = energy.get("daily_cost")
    energy_line = "当日能耗: --"
    if daily_energy is not None:
        energy_line = f"当日能耗: {daily_energy} kWh"
        if daily_cost is not None:
            energy_line += f" / 费用 {daily_cost} 元"

    ac_actions = 0
    light_actions = 0
    fresh_actions = 0
    automation_success_count = 0
    automation_failure_count = 0
    error_logs: list[dict[str, Any]] = []
    warning_logs: list[dict[str, Any]] = []
    exception_logs: list[dict[str, Any]] = []
    offline_logs: list[dict[str, Any]] = []
    for item in logs:
        action = str(item.get("action", "") or "").strip().lower()
        level = str(item.get("level", "") or "").strip().lower()
        source = str(item.get("source", "") or "").strip().lower()
        message = str(item.get("message", "") or "").strip()
        if action.startswith("ac_"):
            ac_actions += 1
        elif action.startswith("light_"):
            light_actions += 1
        elif action.startswith("fresh_air_") or action.startswith("fresh_"):
            fresh_actions += 1
        if source == "automation":
            if level == "error" or "失败" in message:
                automation_failure_count += 1
            elif action not in {
                "occupancy_change",
                "schedule_skip",
                "ac_manual_override_active",
                "ac_manual_restore_skipped",
            }:
                automation_success_count += 1
        if level in {"error", "warning"}:
            exception_logs.append(item)
        if level == "error":
            error_logs.append(item)
        elif level == "warning":
            warning_logs.append(item)
        if "离线" in message or "offline" in message.lower():
            offline_logs.append(item)

    offline_devices: list[str] = []
    for room in rooms:
        room_name = str(room.get("room_name", "") or "").strip()
        computers = room.get("computers", []) or []
        for item in computers:
            if item.get("is_connected"):
                continue
            device_name = str(item.get("title", "") or item.get("ip_address", "") or "终端").strip()
            if room_name:
                offline_devices.append(f"{room_name}/{device_name}")
            else:
                offline_devices.append(device_name)
    offline_devices = offline_devices[:5]

    occupied_hours = await _calculate_today_presence_hours(hass, rooms)
    occupied_hours_line = "今日累计有人时长: --"
    if occupied_hours is not None:
        occupied_hours_line = f"今日累计有人时长: {occupied_hours} 小时"

    recent_error_lines = []
    for item in error_logs[:3]:
        timestamp = str(item.get("timestamp", "") or "").strip()
        hhmm = timestamp[11:16] if len(timestamp) >= 16 else "--:--"
        room_name = str(item.get("room_name", "") or "").strip() or "系统"
        recent_error_lines.append(f"- {hhmm} {room_name}: {str(item.get('message', '') or '').strip()}")

    recent_warning_lines = []
    for item in warning_logs[:3]:
        timestamp = str(item.get("timestamp", "") or "").strip()
        hhmm = timestamp[11:16] if len(timestamp) >= 16 else "--:--"
        room_name = str(item.get("room_name", "") or "").strip() or "系统"
        recent_warning_lines.append(f"- {hhmm} {room_name}: {str(item.get('message', '') or '').strip()}")

    lines: list[str] = [
        f"房间使用: {occupied_total}/{room_total}",
        f"终端在线率: {online_rate} ({online_devices}/{total_devices})",
        f"空调 在线/开启/今日动作: {ac_online}/{ac_on}/{ac_actions}",
        f"灯光 在线/开启/今日动作: {light_online}/{light_on}/{light_actions}",
        f"新风 在线/开启/今日动作: {fresh_online}/{fresh_on}/{fresh_actions}",
        f"自动化执行: 成功 {automation_success_count} / 失败 {automation_failure_count}",
        occupied_hours_line,
        energy_line,
        f"当日异常: {len(exception_logs)} 条 (错误 {len(error_logs)} / 警告 {len(warning_logs)})",
        f"离线相关: {len(offline_logs)} 条 / 当前离线设备: {len(offline_devices)} 台",
    ]
    if offline_devices:
        lines.append("当前离线设备:")
        lines.extend(f"- {item}" for item in offline_devices)
    else:
        lines.append("当前离线设备: 暂无")
    if recent_error_lines:
        lines.append("关键错误:")
        lines.extend(recent_error_lines)
    else:
        lines.append("关键错误: 今日暂无")
    if recent_warning_lines:
        lines.append("重点警告:")
        lines.extend(recent_warning_lines)
    else:
        lines.append("重点警告: 今日暂无")

    return {
        "type": "manual_operations_summary",
        "severity": "info",
        "room_id": "",
        "room_name": "",
        "entity_id": "",
        "title": "今日运行摘要",
        "message": "\n".join(lines),
        "occurred_at": dt_util.now().isoformat(),
    }


async def async_check_daily_brief(hass: HomeAssistant) -> dict[str, Any] | None:
    """Check whether the daily brief should be sent right now."""
    from .room_control import async_load_system_config

    system_config = await async_load_system_config(hass)
    config = normalize_notifications_config(system_config.get("notifications")).get("wechat", {})
    if not config.get("enabled") or not config.get("daily_brief_enabled"):
        return None

    now = dt_util.now()
    target_time = _normalize_time_text(config.get("daily_brief_time"), DEFAULT_DAILY_BRIEF_TIME)
    current_hm = now.strftime("%H:%M")
    if current_hm != target_time:
        return None

    runtime = _runtime(hass)
    persisted = runtime.get("persisted") or _load_persisted_state(hass)
    last_sent_date = str(((persisted.get("daily_brief") or {}).get("last_sent_date")) or "").strip()
    today = now.date().isoformat()
    if last_sent_date == today:
        return None

    event = await _build_daily_brief_event(hass)
    result = await async_send_notification_event(hass, config=config, event=event)
    if result.get("success"):
        persisted.setdefault("daily_brief", {})["last_sent_date"] = today
        runtime["persisted"] = persisted
        await hass.async_add_executor_job(_save_persisted_state, hass, persisted)
    return result


async def _build_daily_brief_event(hass: HomeAssistant) -> dict[str, Any]:
    from .room_control import async_get_room_overview

    overview = await async_get_room_overview(hass)
    rooms = overview.get("rooms", []) if isinstance(overview, dict) else []
    logs = overview.get("logs", []) if isinstance(overview, dict) else []
    energy = overview.get("energy", {}) if isinstance(overview, dict) else {}

    room_total = len(rooms)
    occupied_total = sum(1 for room in rooms if room.get("occupied"))
    online_devices = 0
    total_devices = 0
    ac_online = ac_on = 0
    light_online = light_on = 0
    fresh_online = fresh_on = 0

    for room in rooms:
        computers = room.get("computers", []) or []
        total_devices += len(computers)
        online_devices += sum(1 for item in computers if item.get("is_connected"))
        mapped = room.get("mapped", {}) if isinstance(room.get("mapped"), dict) else {}
        ac = mapped.get("ac")
        if isinstance(ac, dict) and ac.get("exists", True):
            ac_online += 1 if ac.get("available", True) else 0
            ac_on += 1 if ac.get("is_on") else 0
        lights = mapped.get("lights", []) if isinstance(mapped.get("lights"), list) else []
        light_online += sum(1 for item in lights if isinstance(item, dict) and item.get("available", True))
        light_on += sum(1 for item in lights if isinstance(item, dict) and item.get("is_on"))
        fresh = mapped.get("fresh_air")
        if isinstance(fresh, dict) and fresh.get("exists", True):
            fresh_online += 1 if fresh.get("available", True) else 0
            fresh_on += 1 if fresh.get("is_on") else 0

    online_rate = f"{round((online_devices / total_devices) * 100, 1)}%" if total_devices else "--"
    daily_energy = energy.get("daily_energy_kwh")
    daily_cost = energy.get("daily_cost")
    exception_logs = [item for item in logs if str(item.get("level", "")).lower() in {"error", "warning"}]
    recent_exception_lines = [
        f"- {str(item.get('timestamp', ''))[11:16]} {item.get('room_name') or '系统'}: {item.get('message')}"
        for item in exception_logs[:5]
    ]
    energy_line = "当日能耗: --"
    if daily_energy is not None:
        energy_line = f"当日能耗: {daily_energy} kWh"
        if daily_cost is not None:
            energy_line += f" / 费用 {daily_cost} 元"
    message_lines = [
        f"房间总数: {room_total} / 使用中: {occupied_total}",
        f"终端在线率: {online_rate} ({online_devices}/{total_devices})",
        f"空调在线/开启: {ac_online}/{ac_on}",
        f"灯光在线/开启: {light_online}/{light_on}",
        f"新风在线/开启: {fresh_online}/{fresh_on}",
        energy_line,
        f"当日异常数: {len(exception_logs)}",
    ]
    if recent_exception_lines:
        message_lines.append("关键异常:")
        message_lines.extend(recent_exception_lines)
    else:
        message_lines.append("关键异常: 今日暂无高优先级异常。")
    return {
        "type": "daily_brief",
        "severity": "info",
        "room_id": "",
        "room_name": "",
        "entity_id": "",
        "title": "每日日报",
        "message": "\n".join(message_lines),
        "occurred_at": dt_util.now().isoformat(),
    }


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return dt_util.parse_datetime(text)
    except Exception:
        return None
