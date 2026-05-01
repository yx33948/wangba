"""Room-level control, config, and automation helpers for netcafe automation."""

from __future__ import annotations

import copy
import csv
import hashlib
import ipaddress
import io
import logging
import re
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CSV_CONTENT,
    CONF_DEVICES,
    DOMAIN,
    FIELD_IP_ADDRESS,
    FIELD_ROOM_NAME,
)
from .notifications import (
    default_wechat_notification_config,
    normalize_notifications_config,
)
from .storage_manager import StorageManager

_LOGGER = logging.getLogger(__name__)

ROOM_CONFIG_VERSION = 4
ROOM_ID_SEPARATOR = "::"
MAX_RUNTIME_LOGS = 200
ROOM_NAME_KEYWORDS = ("包厢", "包房", "包间", "房间", "房", "间", "室", "区")
AC_HINT_KEYWORDS = ("空调", "ac", "air_condition", "aircondition")
FRESH_AIR_HINT_KEYWORDS = ("新风", "fresh_air", "freshair", "fan")
ROOM_OCCUPANCY_KEYWORDS = ("单人", "双人", "三人", "四人", "多人", "VIP")
ROOM_AREA_EXACT_NAMES = (
    "办公室",
    "前台",
    "大厅",
    "走廊",
    "吧台",
    "仓库",
    "机房",
    "休息区",
    "办公区",
    "前台区",
    "大厅区",
    "服务区",
    "收银区",
)
LIGHT_INCLUDE_KEYWORDS = ("筒灯", "灯带", "牛眼灯", "射灯", "门牌灯", "主灯")
LIGHT_EXCLUDE_KEYWORDS = (
    "指示灯",
    "模式",
    "场景",
    "情景",
    "氛围",
    "背光",
    "夜灯",
    "按键",
    "面板",
    "无线",
    "蓝牙",
    "网关",
)
ENERGY_POWER_KEYWORDS = ("实时功率", "当前功率", "有功功率", "总功率", "功率", "power")
ENERGY_DAILY_KEYWORDS = ("日电耗", "日用电", "今日电耗", "今日用电", "当日电耗", "daily energy")
ENERGY_MONTHLY_KEYWORDS = ("月电耗", "月用电", "本月电耗", "本月用电", "monthly energy")
ROOM_CAPTURE_KEYWORDS = (
    "VIP包厢",
    "VIP包间",
    "KTV包间",
    "KTV包房",
    "推拿房",
    "沐足房",
    "足浴房",
    "智能房",
    "麻将房",
    "电竞房",
    "单人包厢",
    "双人包厢",
    "三人包厢",
    "四人包厢",
    "多人包厢",
    "单人包间",
    "双人包间",
    "三人包间",
    "四人包间",
    "多人包间",
    "单人包",
    "双人包",
    "三人包",
    "四人包",
    "多人包",
    "包厢",
    "包间",
    "包房",
    "房间",
    "包",
    "房",
)
ROOM_STRIP_SUFFIXES = (
    "空调面板",
    "空调开关",
    "空调电源",
    "空调",
    "灯带射灯",
    "灯带",
    "射灯",
    "筒灯",
    "主灯",
    "副灯",
    "灯",
    "开关",
    "总控",
    "新风系统",
    "新风机",
    "新风",
    "排风扇",
    "排风",
    "排气扇",
    "排气",
    "实时功率",
    "当前功率",
    "有功功率",
    "功率",
    "自动化",
)


def build_room_id(entry_id: str, room_name: str) -> str:
    """Build a stable room id from entry and room name."""
    return f"{entry_id}{ROOM_ID_SEPARATOR}{room_name}"


def split_room_id(room_id: str) -> tuple[str, str]:
    """Split the stored room id into entry id and room name."""
    parts = str(room_id or "").split(ROOM_ID_SEPARATOR, 1)
    if len(parts) != 2:
        raise ValueError("room_id 格式不正确")
    return parts[0], parts[1]


def _default_selected_season() -> str:
    """Return a sensible default season based on the current month."""
    month = dt_util.now().month
    return "summer" if 4 <= month <= 9 else "winter"


def _default_room_config(room_id: str, room_name: str) -> dict[str, Any]:
    """Return the default config for one room."""
    return {
        "room_id": room_id,
        "room_name": room_name,
        "entities": {
            "ac": "",
            "lights": [],
            "fresh_air": "",
        },
        "lighting_presets": {
            "full_on": [],
            "half_on": [],
            "full_off": [],
        },
        "lighting_filters": {
            "entity_keywords": [],
            "half_on_keywords": [],
        },
        "entity_filters": {
            "ac_include_keywords": [],
            "ac_exclude_keywords": [],
            "light_include_keywords": [],
            "light_exclude_keywords": [],
            "fresh_air_include_keywords": [],
            "fresh_air_exclude_keywords": [],
        },
        "modes": {
            "selected_season": _default_selected_season(),
            "summer": {
                "enabled": True,
                "hvac_mode": "cool",
                "temperature": 26,
                "fan_mode": "auto",
            },
            "winter": {
                "enabled": True,
                "hvac_mode": "heat",
                "temperature": 22,
                "fan_mode": "auto",
            },
            "custom": {
                "enabled": True,
                "hvac_mode": "auto",
                "temperature": 24,
                "fan_mode": "auto",
            },
        },
        "automation": {
            "enabled": False,
            "logging_enabled": True,
            "trigger_mode": "device_tracker",
            "offline_confirm_seconds": 45,
            "presence_sensor_entity": "",
            "device_tracker_entity": "",
            "presence_sensor_include_keywords": [],
            "presence_sensor_exclude_keywords": [],
            "device_tracker_include_keywords": [],
            "device_tracker_exclude_keywords": [],
            "schedule": {
                "enabled": False,
                "start_time": "00:00",
                "end_time": "23:59",
            },
            "ac": {
                "enabled": False,
                "auto_on": False,
                "auto_off": False,
                "on_delay_sec": 0,
                "off_delay_sec": 60,
                "target_include_keywords": [],
                "target_exclude_keywords": [],
                "manual_override": True,
                "restore_delay_sec": 1800,
                "season_strategy": "selected",
                "temperature_limits_enabled": False,
                "min_temperature": 16,
                "max_temperature": 30,
            },
            "light": {
                "enabled": False,
                "auto_on": False,
                "auto_off": False,
                "on_delay_sec": 0,
                "off_delay_sec": 60,
                "target_include_keywords": [],
                "target_exclude_keywords": [],
                "arrival_preset": "half_on",
                "departure_preset": "full_off",
            },
            "fresh_air": {
                "enabled": False,
                "auto_on": False,
                "auto_off": False,
                "on_delay_sec": 0,
                "off_delay_sec": 60,
                "target_include_keywords": [],
                "target_exclude_keywords": [],
                "fan_mode": "auto",
            },
        },
        "subcontrol": {
            "enabled": True,
            "allow_ac_power": True,
            "allow_ac_temperature": True,
            "allow_ac_mode": True,
            "allow_ac_fan_mode": True,
            "allow_light_control": True,
            "enforce_selected_season": False,
            "inherit_temperature_limits": True,
            "custom_temperature_limits_enabled": False,
            "min_temperature": 16,
            "max_temperature": 30,
        },
    }


def _default_global_settings() -> dict[str, Any]:
    """Return default global settings shared by all rooms."""
    room_defaults = _default_room_config("", "")
    return {
        "entity_filters": copy.deepcopy(room_defaults["entity_filters"]),
        "modes": copy.deepcopy(room_defaults["modes"]),
        "automation": copy.deepcopy(room_defaults["automation"]),
        "subcontrol_trust": {
            "enabled": False,
            "allowed_cidrs": [],
            "trust_proxy_headers": False,
        },
    }


def _default_dashboard_config() -> dict[str, Any]:
    """Return default dashboard-wide settings."""
    return {
        "energy": {
            "realtime_power_entity": "",
            "daily_energy_entity": "",
            "monthly_energy_entity": "",
            "price_per_kwh": 0.0,
        }
    }


def _default_ui_config() -> dict[str, Any]:
    """Return default panel UI settings."""
    return {
        "theme": {
            "selected": "light",
            "auto_by_time": False,
            "day_theme": "light",
            "night_theme": "dark",
            "day_start_time": "08:00",
            "night_start_time": "18:00",
        }
    }


def _default_notifications_config() -> dict[str, Any]:
    """Return default notification settings."""
    return {
        "wechat": default_wechat_notification_config(),
    }


def _safe_bool(value: Any, default: bool = False) -> bool:
    """Return bool with a default fallback."""
    if value is None:
        return default
    return bool(value)


def _safe_int(value: Any, default: int) -> int:
    """Return int with a default fallback."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float | None = None) -> float | None:
    """Return float with a default fallback."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_time_text(value: Any, default: str) -> str:
    """Return HH:MM text with validation."""
    text = str(value or "").strip()
    try:
        parsed = datetime.strptime(text, "%H:%M")
        return parsed.strftime("%H:%M")
    except (TypeError, ValueError):
        return default


def _parse_time_text(value: str) -> time | None:
    """Parse one HH:MM time string."""
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        return None


def _safe_entity_list(value: Any) -> list[str]:
    """Normalize entity id lists."""
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    else:
        return []

    normalized: list[str] = []
    for item in items:
        entity_id = str(item or "").strip()
        if entity_id and "." in entity_id and entity_id not in normalized:
            normalized.append(entity_id)
    return normalized


def _safe_entity_id(value: Any) -> str:
    """Normalize a single entity id."""
    entity_id = str(value or "").strip()
    if entity_id and "." in entity_id:
        return entity_id
    return ""


def _safe_keyword_list(value: Any) -> list[str]:
    """Normalize keyword text/list into a de-duplicated string list."""
    if isinstance(value, str):
        items = re.split(r"[\n,，;；]+", value)
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        return []

    normalized: list[str] = []
    for item in items:
        keyword = str(item or "").strip()
        if keyword and keyword not in normalized:
            normalized.append(keyword)
    return normalized


def _safe_non_negative_float(value: Any, default: float = 0.0) -> float:
    """Return a non-negative float with fallback."""
    number = _safe_float(value, default)
    if number is None:
        return float(default)
    return max(0.0, float(number))


def _normalize_dashboard_config(value: Any) -> dict[str, Any]:
    """Normalize dashboard-wide settings."""
    base = _default_dashboard_config()
    raw = value if isinstance(value, dict) else {}
    energy = raw.get("energy", {})
    if not isinstance(energy, dict):
        energy = {}
    base["energy"] = {
        "realtime_power_entity": _safe_entity_id(energy.get("realtime_power_entity")),
        "daily_energy_entity": _safe_entity_id(energy.get("daily_energy_entity")),
        "monthly_energy_entity": _safe_entity_id(energy.get("monthly_energy_entity")),
        "price_per_kwh": _safe_non_negative_float(energy.get("price_per_kwh"), 0.0),
    }
    return base


def _normalize_ui_theme_key(value: Any) -> str:
    """Normalize one UI theme key."""
    theme = str(value or "").strip().lower()
    if theme == "ocean":
        theme = "tech"
    return theme if theme in {"light", "dark", "tech"} else "light"


def _normalize_ui_config(value: Any) -> dict[str, Any]:
    """Normalize panel UI settings."""
    base = _default_ui_config()
    raw = value if isinstance(value, dict) else {}
    theme = raw.get("theme", {})
    if not isinstance(theme, dict):
        theme = {}
    base["theme"] = {
        "selected": _normalize_ui_theme_key(theme.get("selected")),
        "auto_by_time": _safe_bool(theme.get("auto_by_time"), False),
        "day_theme": _normalize_ui_theme_key(theme.get("day_theme")),
        "night_theme": _normalize_ui_theme_key(theme.get("night_theme")),
        "day_start_time": _safe_time_text(theme.get("day_start_time"), "08:00"),
        "night_start_time": _safe_time_text(theme.get("night_start_time"), "18:00"),
    }
    return base


def _normalize_match_text(value: str) -> str:
    """Normalize entity and room text for fuzzy matching."""
    text = str(value or "").strip().lower()
    return re.sub(r"[\s_\-－]+", "", text)


def _normalize_inline_text(value: str) -> str:
    """Normalize one display text without removing CJK characters."""
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip())


def _pad_room_number(value: str) -> str:
    """Normalize one room number to 3 digits when numeric."""
    text = str(value or "").strip()
    if text.isdigit():
        return f"{int(text):03d}"
    return text


def _pad_numbers_in_text(value: str) -> str:
    """Pad every number token in one room phrase without changing the words."""
    return re.sub(r"\d+", lambda match: _pad_room_number(match.group(0)), str(value or ""))


def _normalize_room_phrase(value: str) -> str:
    """Normalize spacing and number width while preserving the original room words."""
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("－", "-").replace("/", "-")
    text = _pad_numbers_in_text(text)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", "", text)
    return text


def _extract_room_number_tokens(value: str) -> list[str]:
    """Extract one or more ordered room numbers from text."""
    tokens = re.findall(r"\d+", str(value or ""))
    return [_pad_room_number(item) for item in tokens if item]


def _expand_room_number_span(number_tokens: list[str]) -> list[str]:
    """Expand a room range when the text represents a numeric span."""
    cleaned = [str(item or "").strip() for item in number_tokens if str(item or "").strip()]
    if not cleaned:
        return []
    if len(cleaned) == 1:
        return cleaned

    if len(cleaned) == 2 and all(item.isdigit() for item in cleaned):
        start = int(cleaned[0])
        end = int(cleaned[1])
        if start <= end and end - start <= 20:
            return [f"{number:03d}" for number in range(start, end + 1)]

    deduped: list[str] = []
    seen: set[str] = set()
    for item in cleaned:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _format_room_number_span(room_numbers: list[str]) -> str:
    """Format normalized room numbers into one display prefix."""
    numbers = [str(item or "").strip() for item in room_numbers if str(item or "").strip()]
    if not numbers:
        return ""
    if len(numbers) == 1:
        return f"{numbers[0]}号"
    return f"{numbers[0]}号-{numbers[-1]}号"


def _build_canonical_room_key(room_numbers: list[str], occupancy_type: str, category: str) -> str:
    """Build a stable canonical room key while preserving the matched room words."""
    prefix = _format_room_number_span(room_numbers)
    if not prefix:
        return ""
    occupancy = str(occupancy_type or "").strip()
    return f"{prefix}{occupancy}{str(category or '').strip()}"


def _derive_non_numeric_area_name(entity_name: str) -> str:
    """Extract a non-numeric room or area name such as 办公室 or 前台区."""
    candidate = _normalize_inline_text(entity_name)
    if not candidate:
        return ""

    changed = True
    while changed:
        changed = False
        for pattern in _get_room_name_strip_patterns():
            next_value = pattern.sub("", candidate).strip()
            if next_value != candidate:
                candidate = next_value
                changed = True
        compacted = re.sub(r"[\s\-_/\u3000]+$", "", candidate).strip()
        if compacted != candidate:
            candidate = compacted
            changed = True

    candidate = re.sub(r"\s+(空调|灯|灯带|开关|新风|排气|自动化)$", "", candidate, flags=re.IGNORECASE).strip()
    normalized = _normalize_room_phrase(candidate)
    if not normalized:
        return ""

    if normalized in {_normalize_room_phrase(item) for item in ROOM_AREA_EXACT_NAMES}:
        return normalized

    if re.search(r"(?:区|室)$", normalized):
        return normalized

    return ""


def _extract_entity_room_group(entity_name: str) -> dict[str, Any] | None:
    """Extract a canonical room group from one entity friendly name."""
    source = re.sub(r"\s+", " ", str(entity_name or "").replace("_", " ").strip())
    if not source:
        return None

    patterns = [
        re.compile(
            r"(?P<numbers>\d+\s*号?(?:(?:\s*[-－/]\s*|\s+)\d+\s*号?)*)\s*(?P<occupancy>VIP|单人|双人|三人|四人|多人)?\s*(?P<category>包厢|包间|包房|房间|房)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<numbers>\d+)\s*(?P<occupancy>VIP|单人|双人|三人|四人|多人)?\s*(?P<category>包厢|包间|包房|房间|房)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<numbers>\d+\s*号?(?:(?:\s*[-－/]\s*|\s+)\d+\s*号?)*)\s*(?P<purpose>[\u4e00-\u9fffA-Za-z0-9]+?)\s*(?P<category>包房|包间|房间|房|间|室|区)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<numbers>\d+\s*号?(?:(?:\s*[-－/]\s*|\s+)\d+\s*号?)*)\s*(?P<category>包厢|包房|包间|房间|房|间|室|区)",
            re.IGNORECASE,
        ),
    ]

    best: dict[str, Any] | None = None
    for pattern in patterns:
        for match in pattern.finditer(source):
            numbers = _expand_room_number_span(_extract_room_number_tokens(match.group("numbers")))
            if not numbers:
                continue
            canonical = _normalize_room_phrase(match.group(0))
            if not canonical:
                continue
            candidate = {
                "canonical_room_key": canonical,
                "display_name": canonical,
                "room_numbers": numbers,
                "room_range_start": numbers[0],
                "room_range_end": numbers[-1],
                "occupancy_type": str(match.groupdict().get("occupancy") or "").strip().upper(),
                "area_keyword": str(match.group("category") or "").strip(),
                "source_text": match.group(0).strip(),
            }
            if best is None or len(candidate["source_text"]) > len(best["source_text"]):
                best = candidate

    if best is not None:
        return best

    area_name = _derive_non_numeric_area_name(source)
    if not area_name:
        return None

    return {
        "canonical_room_key": area_name,
        "display_name": area_name,
        "room_numbers": [],
        "room_range_start": "",
        "room_range_end": "",
        "occupancy_type": "",
        "area_keyword": area_name,
        "source_text": area_name,
    }


def _room_number_variants(room_name: str) -> list[str]:
    """Extract numeric room variants such as 026 -> [026, 26]."""
    variants: list[str] = []
    seen: set[str] = set()

    for match in re.finditer(r"\d+(?:[-－]\d+)?", str(room_name or "")):
        raw = match.group(0).replace("－", "-")
        candidates = [raw]
        if "-" in raw:
            parts = [part for part in raw.split("-") if part]
            trimmed_parts = [str(int(part)) if part.isdigit() else part for part in parts]
            candidates.extend(parts)
            if trimmed_parts:
                candidates.append("-".join(trimmed_parts))
                candidates.extend(trimmed_parts)
        elif raw.isdigit():
            trimmed = str(int(raw))
            candidates.append(trimmed)

        for item in candidates:
            token = str(item or "").strip()
            if not token or token in seen:
                continue
            seen.add(token)
            variants.append(token)

    return variants


def _get_room_prefix_patterns(room_name: str) -> list[re.Pattern[str]]:
    """Build ordered regex patterns that should match the room prefix."""
    patterns: list[re.Pattern[str]] = []
    seen: set[str] = set()

    for token in _room_number_variants(room_name):
        normalized = str(token or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if "-" in normalized:
            expr = re.escape(normalized).replace(r"\-", r"\s*[-－]\s*")
            patterns.append(re.compile(rf"^{expr}", re.IGNORECASE))
        elif normalized.isdigit():
            patterns.append(re.compile(rf"^0*{int(normalized)}", re.IGNORECASE))
        else:
            patterns.append(re.compile(rf"^{re.escape(normalized)}", re.IGNORECASE))

    room_name_text = _normalize_inline_text(room_name)
    if room_name_text:
        patterns.append(re.compile(rf"^{re.escape(room_name_text)}", re.IGNORECASE))
    return patterns


def _get_room_name_strip_patterns() -> list[re.Pattern[str]]:
    """Return patterns used to strip device suffixes from entity names."""
    patterns = [
        re.compile(rf"({re.escape(item)})(?:\s*\d+)?$", re.IGNORECASE)
        for item in ROOM_STRIP_SUFFIXES
    ]
    patterns.extend(
        [
            re.compile(r"(空调面板|空调开关|空调电源|空调)$", re.IGNORECASE),
            re.compile(r"(灯带射灯|灯带|射灯|筒灯|吸顶灯|吊灯|壁灯|主灯|副灯|门牌灯|指示灯|氛围灯|灯具|灯泡|照明灯|照明|灯)(?:\s*\d+)?$", re.IGNORECASE),
            re.compile(r"(新风系统|新风机|新风|排风扇|排风|换气扇|换气|排气扇|排气)$", re.IGNORECASE),
            re.compile(r"(总控开关|开关面板|开关|插座|按钮|电源|总控)$", re.IGNORECASE),
            re.compile(r"(实时功率|当前功率|有功功率|功率|power)$", re.IGNORECASE),
            re.compile(r"(自动化|automation|联动)$", re.IGNORECASE),
        ]
    )
    return patterns


def _extract_structured_room_name(entity_name: str) -> str:
    """Extract room-like phrases such as 026号单人包厢 or 030号-031号双人包厢."""
    candidate = re.sub(r"\s+", " ", str(entity_name or "").replace("_", " ").strip())
    if not candidate:
        return ""

    patterns = [
        re.compile(
            r"(\d+\s*号?(?:(?:\s*[-－/]\s*|\s+)\d+\s*号?)?\s*(?:vip\s*)?(?:单人|双人)?(?:包厢|包间|包房|房间|房))",
            re.IGNORECASE,
        ),
        re.compile(
            r"((?:vip\s*)?\d+\s*(?:包厢|包间|包房|房间|房))",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:
        match = pattern.search(candidate)
        if match:
            return match.group(1).strip()
    return ""


def _candidate_mentions_room(candidate: str, room_name: str) -> bool:
    """Return True when the candidate text plausibly belongs to the room."""
    candidate_text = _normalize_inline_text(candidate)
    if not candidate_text:
        return False

    normalized_candidate = _normalize_match_text(candidate_text)
    normalized_room = _normalize_match_text(_normalize_inline_text(room_name))
    if normalized_room and normalized_room in normalized_candidate:
        return True

    for token in _room_number_variants(room_name):
        token_text = str(token or "").strip()
        if not token_text:
            continue
        normalized_token = _normalize_match_text(token_text)
        if normalized_token and normalized_token in normalized_candidate:
            return True
        if token_text.isdigit() and re.search(rf"0*{int(token_text)}(?:\s*号)?", candidate_text, re.IGNORECASE):
            return True

    return False


def _derive_room_name_candidate(entity_name: str, room_name: str) -> str:
    """Extract a human room name from one entity friendly name."""
    candidate = _extract_structured_room_name(entity_name) or _normalize_inline_text(entity_name)
    if not candidate:
        return ""

    if not _candidate_mentions_room(candidate, room_name):
        return ""

    candidate_lower = candidate.lower()
    for keyword in sorted(ROOM_CAPTURE_KEYWORDS, key=lambda item: (-len(item), item)):
        index = candidate_lower.find(str(keyword).lower())
        if index <= 0:
            continue
        captured = candidate[: index + len(keyword)].strip()
        if captured and _candidate_mentions_room(captured, room_name):
            return captured

    changed = True
    while changed:
        changed = False
        for pattern in _get_room_name_strip_patterns():
            next_value = pattern.sub("", candidate).strip()
            if next_value != candidate:
                candidate = next_value
                changed = True
        compacted = re.sub(r"[\s\-_/\u3000]+$", "", candidate).strip()
        if compacted != candidate:
            candidate = compacted
            changed = True

    candidate = re.sub(r"\s+(空调|灯|灯带|开关|新风|排气|自动化)$", "", candidate, flags=re.IGNORECASE).strip()
    room_numbers = set(_room_number_variants(room_name))
    if not candidate:
        return ""
    if candidate in room_numbers or _normalize_match_text(candidate) == _normalize_match_text(room_name):
        return ""
    return candidate


def _resolve_room_display_name(
    room_name: str,
    entity_ids: list[str],
    entity_lookup: dict[str, str],
) -> tuple[str, dict[str, int]]:
    """Resolve a richer display name from matched entity names."""
    scores: dict[str, int] = {}
    for entity_id in entity_ids:
        friendly_name = str(entity_lookup.get(entity_id) or "").strip()
        candidate = _derive_room_name_candidate(friendly_name, room_name)
        if not candidate:
            continue
        weight = 3 if entity_id.startswith(("climate.", "fan.", "switch.")) else 2
        scores[candidate] = scores.get(candidate, 0) + weight

    if not scores:
        return room_name, {}

    best = sorted(
        scores.items(),
        key=lambda item: (-int(item[1]), -len(item[0]), item[0]),
    )[0][0]
    return best, scores


def _contains_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    """Return True when any keyword is present in the normalized text."""
    haystack = str(text or "").lower()
    return any(str(keyword).lower() in haystack for keyword in keywords)


def _is_allowed_light_entity(domain: str, friendly_name: str, entity_id: str) -> bool:
    """Return whether the entity should participate in room light matching."""
    combined = f"{friendly_name} {entity_id}".lower()
    if _contains_any_keyword(combined, LIGHT_EXCLUDE_KEYWORDS):
        return False

    if domain == "switch":
        return _contains_any_keyword(combined, LIGHT_INCLUDE_KEYWORDS)

    if domain == "light":
        return True

    return False


def _classify_group_candidate(candidate: dict[str, Any]) -> str | None:
    """Map one entity candidate into a room-control bucket."""
    entity_id = str(candidate.get("entity_id") or "").strip()
    friendly_name = str(candidate.get("friendly_name") or "").strip().lower()
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""

    if domain == "climate":
        return "ac"
    if domain == "light":
        return "lights"
    if domain == "fan":
        return "fresh_air"
    if domain != "switch":
        return None

    combined = f"{friendly_name} {entity_id.lower()}"
    if any(keyword in combined for keyword in FRESH_AIR_HINT_KEYWORDS):
        return "fresh_air"
    if any(keyword in combined for keyword in AC_HINT_KEYWORDS):
        return "ac"
    if _is_allowed_light_entity(domain, friendly_name, entity_id):
        return "lights"
    return None


def _resolve_entity_room_groups(
    candidates_by_domain: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Group entities by canonical room key extracted from friendly names."""
    groups: dict[str, dict[str, Any]] = {}

    for domain_items in candidates_by_domain.values():
        for candidate in domain_items:
            entity_id = str(candidate.get("entity_id") or "").strip()
            friendly_name = str(candidate.get("friendly_name") or "").strip()
            if not entity_id or not friendly_name:
                continue

            room_group = _extract_entity_room_group(friendly_name)
            if room_group is None:
                continue

            room_key = str(room_group["canonical_room_key"])
            group = groups.setdefault(
                room_key,
                {
                    "canonical_room_key": room_key,
                    "display_name": room_group["display_name"],
                    "room_numbers": list(room_group["room_numbers"]),
                    "room_range_start": room_group["room_range_start"],
                    "room_range_end": room_group["room_range_end"],
                    "occupancy_type": room_group["occupancy_type"],
                    "entities": {
                        "ac": [],
                        "lights": [],
                        "fresh_air": [],
                    },
                    "entity_ids": [],
                    "source_names": [],
                },
            )

            if entity_id not in group["entity_ids"]:
                group["entity_ids"].append(entity_id)
            if friendly_name not in group["source_names"]:
                group["source_names"].append(friendly_name)

            bucket = _classify_group_candidate(candidate)
            if bucket and entity_id not in group["entities"][bucket]:
                group["entities"][bucket].append(entity_id)

    return groups


def _find_room_group_for_record(
    room_record: dict[str, Any],
    room_groups: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the canonical room group that covers the room record."""
    room_name = str(room_record.get("room_name") or "")
    normalized_room_name = _normalize_room_phrase(room_name)
    room_numbers = _room_number_variants(room_name)
    normalized_numbers = {_pad_room_number(item) for item in room_numbers if str(item or "").strip().isdigit()}
    matched_groups: list[dict[str, Any]] = []
    for group in room_groups.values():
        group_numbers = set(group.get("room_numbers") or [])
        group_name = _normalize_room_phrase(str(group.get("display_name") or ""))
        if normalized_numbers and normalized_numbers & group_numbers:
            matched_groups.append(group)
            continue
        if normalized_room_name and group_name and normalized_room_name == group_name:
            matched_groups.append(group)

    if not matched_groups:
        return None

    matched_groups.sort(
        key=lambda item: (
            -len(item.get("room_numbers") or []),
            -len(str(item.get("display_name") or "")),
            str(item.get("display_name") or ""),
        )
    )
    return matched_groups[0]


def _resolve_room_display_from_group(
    room_record: dict[str, Any],
    room_config: dict[str, Any],
    room_groups: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, int], dict[str, Any] | None]:
    """Resolve one room display name from canonical entity groups."""
    matched_group = _find_room_group_for_record(room_record, room_groups)
    if matched_group is None:
        return room_record["room_name"], {}, None

    scores = {str(matched_group["display_name"]): len(matched_group.get("entity_ids") or [])}
    merged_entities = {
        "ac": str(room_config.get("entities", {}).get("ac") or "").strip(),
        "lights": [str(item).strip() for item in room_config.get("entities", {}).get("lights", []) if str(item).strip()],
        "fresh_air": str(room_config.get("entities", {}).get("fresh_air") or "").strip(),
    }

    if not merged_entities["ac"] and matched_group["entities"]["ac"]:
        merged_entities["ac"] = matched_group["entities"]["ac"][0]
    if not merged_entities["lights"] and matched_group["entities"]["lights"]:
        merged_entities["lights"] = list(matched_group["entities"]["lights"])
    if not merged_entities["fresh_air"] and matched_group["entities"]["fresh_air"]:
        merged_entities["fresh_air"] = matched_group["entities"]["fresh_air"][0]

    return str(matched_group["display_name"]), scores, {
        **matched_group,
        "entities": merged_entities,
    }


def _room_aliases(room_name: str) -> list[str]:
    """Build room aliases that may appear in HA entity names."""
    aliases: list[str] = []
    seen: set[str] = set()

    def _add_alias(value: str) -> None:
        normalized = _normalize_match_text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            aliases.append(normalized)

    room_name_text = str(room_name or "").strip()
    _add_alias(room_name_text)

    for token in _room_number_variants(room_name_text):
        _add_alias(token)
        for keyword in ROOM_NAME_KEYWORDS:
            _add_alias(f"{token}{keyword}")
            _add_alias(f"{token}号{keyword}")
            _add_alias(f"{keyword}{token}")

    return aliases


def _score_room_match(room_name: str, entity_id: str, friendly_name: str) -> int:
    """Return a fuzzy match score between one room and one HA entity."""
    score = 0
    raw_text = f"{friendly_name} {entity_id}".lower()
    normalized_text = _normalize_match_text(raw_text)
    aliases = _room_aliases(room_name)

    room_name_alias = _normalize_match_text(room_name)
    if room_name_alias and room_name_alias in normalized_text:
        score += 120

    for alias in aliases:
        if alias and alias in normalized_text:
            score += 80 if len(alias) > 3 else 45

    for token in _room_number_variants(room_name):
        if not token:
            continue
        if token in raw_text or token in normalized_text:
            score += 20

        if token.isdigit():
            token_pattern = re.escape(str(int(token)))
            for keyword in ROOM_NAME_KEYWORDS:
                if re.search(rf"0*{token_pattern}(?:号)?(?:\s*vip)?{keyword}", raw_text):
                    score += 70
                if re.search(rf"{keyword}\s*0*{token_pattern}", raw_text):
                    score += 55

    return score


def _infer_room_entities(
    room_name: str,
    candidates_by_domain: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Infer room-to-entity bindings from current HA state names."""
    best_ac: tuple[int, str] | None = None
    best_fresh_air: tuple[int, str] | None = None
    light_matches: list[tuple[int, str]] = []

    def _candidate_text(candidate: dict[str, Any]) -> str:
        return f"{candidate.get('friendly_name', '')} {candidate.get('entity_id', '')}".lower()

    for candidate in candidates_by_domain.get("climate", []):
        entity_id = str(candidate.get("entity_id") or "").strip()
        score = _score_room_match(room_name, entity_id, str(candidate.get("friendly_name") or ""))
        if score <= 0:
            continue
        if best_ac is None or score > best_ac[0]:
            best_ac = (score, entity_id)

    for candidate in candidates_by_domain.get("fan", []):
        entity_id = str(candidate.get("entity_id") or "").strip()
        score = _score_room_match(room_name, entity_id, str(candidate.get("friendly_name") or ""))
        if score <= 0:
            continue
        if best_fresh_air is None or score > best_fresh_air[0]:
            best_fresh_air = (score, entity_id)

    for candidate in candidates_by_domain.get("light", []):
        entity_id = str(candidate.get("entity_id") or "").strip()
        friendly_name = str(candidate.get("friendly_name") or "")
        if not _is_allowed_light_entity("light", friendly_name, entity_id):
            continue
        score = _score_room_match(room_name, entity_id, friendly_name)
        if score > 0:
            light_matches.append((score, entity_id))

    for candidate in candidates_by_domain.get("switch", []):
        entity_id = str(candidate.get("entity_id") or "").strip()
        friendly_name = str(candidate.get("friendly_name") or "")
        score = _score_room_match(room_name, entity_id, friendly_name)
        if score <= 0:
            continue

        candidate_text = _candidate_text(candidate)
        if any(keyword in candidate_text for keyword in AC_HINT_KEYWORDS):
            boosted = score + 25
            if best_ac is None or boosted > best_ac[0]:
                best_ac = (boosted, entity_id)

        if any(keyword in candidate_text for keyword in FRESH_AIR_HINT_KEYWORDS):
            boosted = score + 25
            if best_fresh_air is None or boosted > best_fresh_air[0]:
                best_fresh_air = (boosted, entity_id)

        if _is_allowed_light_entity("switch", friendly_name, entity_id):
            light_matches.append((score, entity_id))

    light_matches.sort(key=lambda item: (-item[0], item[1]))
    inferred_lights: list[str] = []
    for _score, entity_id in light_matches:
        if entity_id not in inferred_lights:
            inferred_lights.append(entity_id)

    return {
        "ac": best_ac[1] if best_ac else "",
        "lights": inferred_lights,
        "fresh_air": best_fresh_air[1] if best_fresh_air else "",
    }


def explain_room_entity_inference(
    room_name: str,
    candidates_by_domain: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Return detailed scoring diagnostics for one room."""
    ranked: dict[str, list[dict[str, Any]]] = {
        "ac": [],
        "lights": [],
        "fresh_air": [],
    }

    for candidate in candidates_by_domain.get("climate", []):
        entity_id = str(candidate.get("entity_id") or "").strip()
        friendly_name = str(candidate.get("friendly_name") or "").strip()
        score = _score_room_match(room_name, entity_id, friendly_name)
        if score > 0:
            ranked["ac"].append(
                {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "entity_name": candidate.get("entity_name") or friendly_name,
                    "domain": "climate",
                    "score": score,
                }
            )

    for candidate in candidates_by_domain.get("fan", []):
        entity_id = str(candidate.get("entity_id") or "").strip()
        friendly_name = str(candidate.get("friendly_name") or "").strip()
        score = _score_room_match(room_name, entity_id, friendly_name)
        if score > 0:
            ranked["fresh_air"].append(
                {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "entity_name": candidate.get("entity_name") or friendly_name,
                    "domain": "fan",
                    "score": score,
                }
            )

    for candidate in candidates_by_domain.get("light", []):
        entity_id = str(candidate.get("entity_id") or "").strip()
        friendly_name = str(candidate.get("friendly_name") or "").strip()
        if not _is_allowed_light_entity("light", friendly_name, entity_id):
            continue
        score = _score_room_match(room_name, entity_id, friendly_name)
        if score > 0:
            ranked["lights"].append(
                {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "entity_name": candidate.get("entity_name") or friendly_name,
                    "domain": "light",
                    "score": score,
                }
            )

    for candidate in candidates_by_domain.get("switch", []):
        entity_id = str(candidate.get("entity_id") or "").strip()
        friendly_name = str(candidate.get("friendly_name") or "").strip()
        score = _score_room_match(room_name, entity_id, friendly_name)
        if score <= 0:
            continue

        candidate_text = f"{friendly_name} {entity_id}".lower()
        if any(keyword in candidate_text for keyword in AC_HINT_KEYWORDS):
            ranked["ac"].append(
                {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "entity_name": candidate.get("entity_name") or friendly_name,
                    "domain": "switch",
                    "score": score + 25,
                }
            )

        if any(keyword in candidate_text for keyword in FRESH_AIR_HINT_KEYWORDS):
            ranked["fresh_air"].append(
                {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "entity_name": candidate.get("entity_name") or friendly_name,
                    "domain": "switch",
                    "score": score + 25,
                }
            )

        if _is_allowed_light_entity("switch", friendly_name, entity_id):
            ranked["lights"].append(
                {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "entity_name": candidate.get("entity_name") or friendly_name,
                    "domain": "switch",
                    "score": score,
                }
            )

    for key in ranked:
        ranked[key].sort(key=lambda item: (-int(item["score"]), str(item["entity_id"])))
        ranked[key] = ranked[key][:10]

    inferred = _infer_room_entities(room_name, candidates_by_domain)
    return {
        "room_name": room_name,
        "room_aliases": _room_aliases(room_name),
        "room_number_variants": _room_number_variants(room_name),
        "selected": inferred,
        "ranked": ranked,
    }


def _collect_entity_candidates_for_inference(hass: HomeAssistant) -> dict[str, list[dict[str, Any]]]:
    """Collect lightweight state data for automatic room matching."""
    candidates: dict[str, list[dict[str, Any]]] = {
        "climate": [],
        "light": [],
        "fan": [],
        "switch": [],
    }

    for state in hass.states.async_all():
        entity_id = state.entity_id
        domain = entity_id.split(".", 1)[0]
        if domain not in candidates:
            continue
        candidates[domain].append(
            {
                "entity_id": entity_id,
                "friendly_name": state.name,
                "entity_name": _clean_entity_display_name(hass, entity_id, state.name),
            }
        )

    return candidates


def _build_entity_name_lookup(candidates_by_domain: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    """Build an entity_id -> friendly_name lookup."""
    lookup: dict[str, str] = {}
    for items in candidates_by_domain.values():
        for item in items:
            entity_id = str(item.get("entity_id") or "").strip()
            if entity_id:
                lookup[entity_id] = str(item.get("friendly_name") or entity_id).strip()
    return lookup


def _clean_entity_display_name(hass: HomeAssistant, entity_id: str, state_name: str) -> str:
    """Return the entity's own name without the HA device-name prefix."""
    fallback = str(state_name or entity_id or "").strip()
    custom_name = ""
    original_name = ""
    device_names: list[str] = []
    try:
        entity_entry = er.async_get(hass).async_get(entity_id)
    except Exception:  # pragma: no cover - registry access is best-effort
        entity_entry = None

    if entity_entry is not None:
        custom_name = str(
            getattr(entity_entry, "name_by_user", "")
            or getattr(entity_entry, "name", "")
            or ""
        ).strip()
        original_name = str(getattr(entity_entry, "original_name", "") or "").strip()
        device_id = getattr(entity_entry, "device_id", None)
        if device_id:
            try:
                device_entry = dr.async_get(hass).async_get(device_id)
            except Exception:  # pragma: no cover - registry access is best-effort
                device_entry = None
            device_names = [
                getattr(device_entry, "name_by_user", "") if device_entry is not None else "",
                getattr(device_entry, "name", "") if device_entry is not None else "",
            ]

    for candidate_label, candidate in (("custom", custom_name), ("fallback", fallback)):
        candidate_text = str(candidate or "").strip()
        for device_name in device_names:
            prefix = str(device_name or "").strip()
            if prefix and candidate_text.startswith(prefix):
                cleaned = candidate_text[len(prefix) :].strip(" -_·|/")
                if cleaned:
                    return cleaned
        if candidate_label == "custom" and candidate_text and candidate_text != entity_id:
            return candidate_text

    if original_name:
        return original_name

    if fallback and fallback != entity_id:
        return fallback

    return fallback or entity_id


def normalize_room_config(
    raw_config: dict[str, Any] | None,
    *,
    room_id: str,
    room_name: str,
) -> dict[str, Any]:
    """Normalize one room config into a stable schema."""
    base = _default_room_config(room_id, room_name)
    raw = raw_config if isinstance(raw_config, dict) else {}

    entities = raw.get("entities", {})
    if not isinstance(entities, dict):
        entities = {}
    base["entities"] = {
        "ac": _safe_entity_id(entities.get("ac")),
        "lights": _safe_entity_list(entities.get("lights")),
        "fresh_air": _safe_entity_id(entities.get("fresh_air")),
    }

    presets = raw.get("lighting_presets", {})
    if not isinstance(presets, dict):
        presets = {}
    base["lighting_presets"] = {
        "full_on": _safe_entity_list(presets.get("full_on")),
        "half_on": _safe_entity_list(presets.get("half_on")),
        "full_off": _safe_entity_list(presets.get("full_off")),
    }

    lighting_filters = raw.get("lighting_filters", {})
    if not isinstance(lighting_filters, dict):
        lighting_filters = {}
    base["lighting_filters"] = {
        "entity_keywords": _safe_keyword_list(lighting_filters.get("entity_keywords")),
        "half_on_keywords": _safe_keyword_list(lighting_filters.get("half_on_keywords")),
    }

    entity_filters = raw.get("entity_filters", {})
    if not isinstance(entity_filters, dict):
        entity_filters = {}
    base["entity_filters"] = {
        "ac_include_keywords": _safe_keyword_list(entity_filters.get("ac_include_keywords")),
        "ac_exclude_keywords": _safe_keyword_list(entity_filters.get("ac_exclude_keywords")),
        "light_include_keywords": _safe_keyword_list(entity_filters.get("light_include_keywords")),
        "light_exclude_keywords": _safe_keyword_list(entity_filters.get("light_exclude_keywords")),
        "fresh_air_include_keywords": _safe_keyword_list(entity_filters.get("fresh_air_include_keywords")),
        "fresh_air_exclude_keywords": _safe_keyword_list(entity_filters.get("fresh_air_exclude_keywords")),
    }

    modes = raw.get("modes", {})
    if not isinstance(modes, dict):
        modes = {}

    for season in ("summer", "winter", "custom"):
        season_raw = modes.get(season, {})
        if not isinstance(season_raw, dict):
            season_raw = {}
        base["modes"][season] = {
            "enabled": _safe_bool(season_raw.get("enabled"), True),
            "hvac_mode": str(
                season_raw.get("hvac_mode") or base["modes"][season]["hvac_mode"]
            ).strip(),
            "temperature": _safe_float(
                season_raw.get("temperature"),
                float(base["modes"][season]["temperature"]),
            ),
            "fan_mode": str(
                season_raw.get("fan_mode") or base["modes"][season]["fan_mode"]
            ).strip(),
        }

    selected_season = str(
        modes.get("selected_season") or base["modes"]["selected_season"]
    ).strip()
    if selected_season not in {"summer", "winter", "custom"}:
        selected_season = base["modes"]["selected_season"]
    base["modes"]["selected_season"] = selected_season

    automation = raw.get("automation", {})
    if not isinstance(automation, dict):
        automation = {}
    base["automation"]["enabled"] = _safe_bool(automation.get("enabled"), False)
    base["automation"]["logging_enabled"] = _safe_bool(
        automation.get("logging_enabled"),
        True,
    )
    trigger_mode = str(
        automation.get("trigger_mode")
        or automation.get("online_mode")
        or automation.get("presence_mode")
        or "device_tracker"
    ).strip().lower()
    if trigger_mode not in {"device_tracker", "sensor", "hybrid"}:
        trigger_mode = "device_tracker"
    base["automation"]["trigger_mode"] = trigger_mode
    base["automation"]["offline_confirm_seconds"] = max(
        5,
        min(300, _safe_int(automation.get("offline_confirm_seconds"), 45)),
    )
    base["automation"]["presence_sensor_entity"] = _safe_entity_id(
        automation.get("presence_sensor_entity")
    )
    base["automation"]["device_tracker_entity"] = _safe_entity_id(
        automation.get("device_tracker_entity")
    )
    base["automation"]["presence_sensor_include_keywords"] = _safe_keyword_list(
        automation.get("presence_sensor_include_keywords")
    )
    base["automation"]["presence_sensor_exclude_keywords"] = _safe_keyword_list(
        automation.get("presence_sensor_exclude_keywords")
    )
    base["automation"]["device_tracker_include_keywords"] = _safe_keyword_list(
        automation.get("device_tracker_include_keywords")
    )
    base["automation"]["device_tracker_exclude_keywords"] = _safe_keyword_list(
        automation.get("device_tracker_exclude_keywords")
    )

    schedule_automation = automation.get("schedule", {})
    if not isinstance(schedule_automation, dict):
        schedule_automation = {}
    base["automation"]["schedule"] = {
        "enabled": _safe_bool(schedule_automation.get("enabled"), False),
        "start_time": _safe_time_text(
            schedule_automation.get("start_time"),
            "00:00",
        ),
        "end_time": _safe_time_text(
            schedule_automation.get("end_time"),
            "23:59",
        ),
    }

    ac_automation = automation.get("ac", {})
    if not isinstance(ac_automation, dict):
        ac_automation = {}
    base["automation"]["ac"] = {
        "enabled": _safe_bool(ac_automation.get("enabled"), False),
        "auto_on": _safe_bool(ac_automation.get("auto_on"), False),
        "auto_off": _safe_bool(ac_automation.get("auto_off"), False),
        "on_delay_sec": _safe_int(ac_automation.get("on_delay_sec"), 0),
        "off_delay_sec": _safe_int(ac_automation.get("off_delay_sec"), 60),
        "target_include_keywords": _safe_keyword_list(ac_automation.get("target_include_keywords")),
        "target_exclude_keywords": _safe_keyword_list(ac_automation.get("target_exclude_keywords")),
        "manual_override": _safe_bool(ac_automation.get("manual_override"), True),
        "restore_delay_sec": _safe_int(ac_automation.get("restore_delay_sec"), 1800),
        "season_strategy": str(ac_automation.get("season_strategy") or "selected").strip().lower(),
        "temperature_limits_enabled": _safe_bool(
            ac_automation.get("temperature_limits_enabled"),
            False,
        ),
        "min_temperature": _safe_float(ac_automation.get("min_temperature"), 16.0),
        "max_temperature": _safe_float(ac_automation.get("max_temperature"), 30.0),
    }
    if base["automation"]["ac"]["season_strategy"] not in {"selected", "summer", "winter", "custom"}:
        base["automation"]["ac"]["season_strategy"] = "selected"
    min_temperature = _safe_float(base["automation"]["ac"].get("min_temperature"), 16.0)
    max_temperature = _safe_float(base["automation"]["ac"].get("max_temperature"), 30.0)
    if min_temperature is None:
        min_temperature = 16.0
    if max_temperature is None:
        max_temperature = 30.0
    if min_temperature > max_temperature:
        min_temperature, max_temperature = max_temperature, min_temperature
    base["automation"]["ac"]["min_temperature"] = max(16.0, min(32.0, min_temperature))
    base["automation"]["ac"]["max_temperature"] = max(
        base["automation"]["ac"]["min_temperature"],
        min(32.0, max_temperature),
    )

    light_automation = automation.get("light", {})
    if not isinstance(light_automation, dict):
        light_automation = {}
    arrival_preset = str(light_automation.get("arrival_preset") or "half_on").strip()
    if arrival_preset not in {"full_on", "half_on", "full_off"}:
        arrival_preset = "half_on"
    departure_preset = str(light_automation.get("departure_preset") or "full_off").strip()
    if departure_preset not in {"full_on", "half_on", "full_off"}:
        departure_preset = "full_off"
    base["automation"]["light"] = {
        "enabled": _safe_bool(light_automation.get("enabled"), False),
        "auto_on": _safe_bool(light_automation.get("auto_on"), False),
        "auto_off": _safe_bool(light_automation.get("auto_off"), False),
        "on_delay_sec": _safe_int(light_automation.get("on_delay_sec"), 0),
        "off_delay_sec": _safe_int(light_automation.get("off_delay_sec"), 60),
        "target_include_keywords": _safe_keyword_list(light_automation.get("target_include_keywords")),
        "target_exclude_keywords": _safe_keyword_list(light_automation.get("target_exclude_keywords")),
        "arrival_preset": arrival_preset,
        "departure_preset": departure_preset,
    }

    fresh_air_automation = automation.get("fresh_air", {})
    if not isinstance(fresh_air_automation, dict):
        fresh_air_automation = {}
    base["automation"]["fresh_air"] = {
        "enabled": _safe_bool(fresh_air_automation.get("enabled"), False),
        "auto_on": _safe_bool(fresh_air_automation.get("auto_on"), False),
        "auto_off": _safe_bool(fresh_air_automation.get("auto_off"), False),
        "on_delay_sec": _safe_int(fresh_air_automation.get("on_delay_sec"), 0),
        "off_delay_sec": _safe_int(fresh_air_automation.get("off_delay_sec"), 60),
        "target_include_keywords": _safe_keyword_list(fresh_air_automation.get("target_include_keywords")),
        "target_exclude_keywords": _safe_keyword_list(fresh_air_automation.get("target_exclude_keywords")),
        "fan_mode": str(fresh_air_automation.get("fan_mode") or "auto").strip(),
    }

    for preset_name in ("full_on", "half_on", "full_off"):
        preset_entities = base["lighting_presets"][preset_name]
        base["lighting_presets"][preset_name] = [
            entity_id
            for entity_id in preset_entities
            if entity_id in base["entities"]["lights"]
        ]

    subcontrol = raw.get("subcontrol", {})
    if not isinstance(subcontrol, dict):
        subcontrol = {}
    base["subcontrol"] = {
        "enabled": _safe_bool(subcontrol.get("enabled"), True),
        "allow_ac_power": _safe_bool(subcontrol.get("allow_ac_power"), True),
        "allow_ac_temperature": _safe_bool(subcontrol.get("allow_ac_temperature"), True),
        "allow_ac_mode": _safe_bool(subcontrol.get("allow_ac_mode"), True),
        "allow_ac_fan_mode": _safe_bool(subcontrol.get("allow_ac_fan_mode"), True),
        "allow_light_control": _safe_bool(subcontrol.get("allow_light_control"), True),
        "enforce_selected_season": _safe_bool(subcontrol.get("enforce_selected_season"), False),
        "inherit_temperature_limits": _safe_bool(subcontrol.get("inherit_temperature_limits"), True),
        "custom_temperature_limits_enabled": _safe_bool(
            subcontrol.get("custom_temperature_limits_enabled"),
            False,
        ),
        "min_temperature": _safe_float(subcontrol.get("min_temperature"), 16.0),
        "max_temperature": _safe_float(subcontrol.get("max_temperature"), 30.0),
    }
    sub_min_temperature = _safe_float(base["subcontrol"].get("min_temperature"), 16.0)
    sub_max_temperature = _safe_float(base["subcontrol"].get("max_temperature"), 30.0)
    if sub_min_temperature is None:
        sub_min_temperature = 16.0
    if sub_max_temperature is None:
        sub_max_temperature = 30.0
    if sub_min_temperature > sub_max_temperature:
        sub_min_temperature, sub_max_temperature = sub_max_temperature, sub_min_temperature
    base["subcontrol"]["min_temperature"] = max(16.0, min(32.0, sub_min_temperature))
    base["subcontrol"]["max_temperature"] = max(
        base["subcontrol"]["min_temperature"],
        min(32.0, sub_max_temperature),
    )

    return base


def normalize_global_settings(raw_config: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize the shared global settings schema."""
    normalized = normalize_room_config(raw_config, room_id="", room_name="")
    defaults = _default_global_settings()
    raw_subcontrol_trust = {}
    if isinstance(raw_config, dict):
        raw_subcontrol_trust = raw_config.get("subcontrol_trust", {})
    if raw_subcontrol_trust is None:
        raw_subcontrol_trust = {}
    if not isinstance(raw_subcontrol_trust, dict):
        raise ValueError("global_settings.subcontrol_trust 必须是对象")

    allowed_cidrs: list[str] = []
    raw_allowed_cidrs = raw_subcontrol_trust.get("allowed_cidrs", [])
    if raw_allowed_cidrs is None:
        raw_allowed_cidrs = []
    if not isinstance(raw_allowed_cidrs, list):
        raise ValueError("global_settings.subcontrol_trust.allowed_cidrs 必须是数组")
    for item in raw_allowed_cidrs:
        cidr = str(item or "").strip()
        if not cidr:
            continue
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as err:
            raise ValueError(f"分机局域网白名单 CIDR 无效: {cidr}") from err
        normalized_cidr = str(network)
        if normalized_cidr not in allowed_cidrs:
            allowed_cidrs.append(normalized_cidr)

    return {
        "entity_filters": copy.deepcopy(normalized.get("entity_filters", defaults["entity_filters"])),
        "modes": copy.deepcopy(normalized.get("modes", defaults["modes"])),
        "automation": copy.deepcopy(normalized.get("automation", defaults["automation"])),
        "subcontrol_trust": {
            "enabled": _safe_bool(
                raw_subcontrol_trust.get("enabled"),
                defaults["subcontrol_trust"]["enabled"],
            ),
            "allowed_cidrs": allowed_cidrs,
            "trust_proxy_headers": _safe_bool(
                raw_subcontrol_trust.get("trust_proxy_headers"),
                defaults["subcontrol_trust"]["trust_proxy_headers"],
            ),
        },
    }


def _merge_global_settings_into_room_config(
    room_config: dict[str, Any],
    global_settings: dict[str, Any] | None,
) -> dict[str, Any]:
    """Overlay global automation and filter settings onto one room config."""
    merged = copy.deepcopy(room_config)
    normalized_global = normalize_global_settings(global_settings)
    merged["entity_filters"] = copy.deepcopy(normalized_global["entity_filters"])
    merged["modes"] = copy.deepcopy(normalized_global["modes"])
    merged["automation"] = copy.deepcopy(normalized_global["automation"])
    return normalize_room_config(
        merged,
        room_id=str(room_config.get("room_id") or ""),
        room_name=str(room_config.get("room_name") or ""),
    )


def _entity_keyword_text(entity_id: str, entity_name_lookup: dict[str, str]) -> str:
    """Build the searchable text for one entity."""
    friendly_name = str(entity_name_lookup.get(entity_id) or "").strip()
    return f"{friendly_name} {entity_id}".strip().lower()


def _match_entity_keywords(
    entity_id: str,
    entity_name_lookup: dict[str, str],
    include_keywords: list[str] | None,
    exclude_keywords: list[str] | None,
) -> bool:
    """Return whether one entity passes include/exclude keyword rules."""
    text = _entity_keyword_text(entity_id, entity_name_lookup)
    include = [str(item or "").strip().lower() for item in include_keywords or [] if str(item or "").strip()]
    exclude = [str(item or "").strip().lower() for item in exclude_keywords or [] if str(item or "").strip()]
    if include and not any(keyword in text for keyword in include):
        return False
    if any(keyword in text for keyword in exclude):
        return False
    return True


def _filter_entity_candidates(
    entity_ids: list[str],
    entity_name_lookup: dict[str, str],
    include_keywords: list[str] | None,
    exclude_keywords: list[str] | None,
) -> list[str]:
    """Filter entity ids by keyword rules while keeping original order."""
    result: list[str] = []
    for entity_id in entity_ids:
        text = str(entity_id or "").strip()
        if not text or text in result:
            continue
        if _match_entity_keywords(text, entity_name_lookup, include_keywords, exclude_keywords):
            result.append(text)
    return result


def _apply_global_entity_filters_to_room_config(
    room_config: dict[str, Any],
    *,
    matched_group: dict[str, Any] | None,
    inferred: dict[str, Any] | None,
    entity_name_lookup: dict[str, str],
) -> dict[str, Any]:
    """Apply global entity filters to the room's candidate entities."""
    filtered = copy.deepcopy(room_config)
    entity_filters = filtered.get("entity_filters", {})

    matched_entities = matched_group.get("entities", {}) if isinstance(matched_group, dict) else {}
    inferred_entities = inferred if isinstance(inferred, dict) else {}

    ac_candidates = [
        str(filtered["entities"].get("ac") or "").strip(),
        *[str(item or "").strip() for item in matched_entities.get("ac", []) or []],
        str(inferred_entities.get("ac") or "").strip(),
    ]
    fresh_candidates = [
        str(filtered["entities"].get("fresh_air") or "").strip(),
        *[str(item or "").strip() for item in matched_entities.get("fresh_air", []) or []],
        str(inferred_entities.get("fresh_air") or "").strip(),
    ]
    light_candidates = [
        *[str(item or "").strip() for item in filtered["entities"].get("lights", []) or []],
        *[str(item or "").strip() for item in matched_entities.get("lights", []) or []],
        *[str(item or "").strip() for item in inferred_entities.get("lights", []) or []],
    ]

    visible_ac = _filter_entity_candidates(
        ac_candidates,
        entity_name_lookup,
        entity_filters.get("ac_include_keywords"),
        entity_filters.get("ac_exclude_keywords"),
    )
    visible_fresh = _filter_entity_candidates(
        fresh_candidates,
        entity_name_lookup,
        entity_filters.get("fresh_air_include_keywords"),
        entity_filters.get("fresh_air_exclude_keywords"),
    )
    visible_lights = _filter_entity_candidates(
        light_candidates,
        entity_name_lookup,
        entity_filters.get("light_include_keywords"),
        entity_filters.get("light_exclude_keywords"),
    )

    filtered["entities"]["ac"] = visible_ac[0] if visible_ac else ""
    filtered["entities"]["fresh_air"] = visible_fresh[0] if visible_fresh else ""
    filtered["entities"]["lights"] = visible_lights
    filtered["lighting_presets"]["full_on"] = list(visible_lights)
    filtered["lighting_presets"]["full_off"] = list(visible_lights)
    filtered["lighting_presets"]["half_on"] = [
        entity_id
        for entity_id in filtered["lighting_presets"].get("half_on", [])
        if entity_id in visible_lights
    ]
    return filtered


def _build_runtime_entity_name_lookup(
    hass: HomeAssistant,
    entity_ids: list[str],
) -> dict[str, str]:
    """Build a lightweight entity name lookup from current HA state."""
    lookup: dict[str, str] = {}
    for entity_id in entity_ids:
        normalized = str(entity_id or "").strip()
        if not normalized or normalized in lookup:
            continue
        state = hass.states.get(normalized)
        if state is None:
            lookup[normalized] = normalized
            continue
        friendly_name = str(state.attributes.get("friendly_name") or state.name or normalized).strip()
        lookup[normalized] = friendly_name or normalized
    return lookup


def _filter_automation_target_entity_ids(
    hass: HomeAssistant,
    entity_ids: list[str],
    include_keywords: list[str] | None,
    exclude_keywords: list[str] | None,
) -> list[str]:
    """Apply automation-only keyword filters to resolved entity ids."""
    normalized_ids = [str(item or "").strip() for item in entity_ids if str(item or "").strip()]
    if not normalized_ids:
        return []
    lookup = _build_runtime_entity_name_lookup(hass, normalized_ids)
    return _filter_entity_candidates(
        normalized_ids,
        lookup,
        include_keywords,
        exclude_keywords,
    )


def _parse_numeric_state_value(value: Any) -> float | None:
    """Parse one sensor-like state value into a float when possible."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"unknown", "unavailable", "none"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _convert_power_to_kw(value: float | None, unit: str) -> float | None:
    """Convert power readings to kW when unit is known."""
    if value is None:
        return None
    normalized = str(unit or "").strip().lower()
    if normalized in {"kw", "kilowatt", "kilowatts"}:
        return float(value)
    if normalized in {"w", "watt", "watts"}:
        return float(value) / 1000.0
    return None


def _convert_energy_to_kwh(value: float | None, unit: str) -> float | None:
    """Convert energy readings to kWh when unit is known."""
    if value is None:
        return None
    normalized = str(unit or "").strip().lower()
    if normalized in {"kwh", "kw·h", "kw h"}:
        return float(value)
    if normalized in {"wh", "w·h", "w h"}:
        return float(value) / 1000.0
    return None


def _runtime_store(hass: HomeAssistant) -> dict[str, Any]:
    """Return the room automation runtime store."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    return domain_data.setdefault(
        "room_control_runtime",
        {
            "rooms": {},
            "logs": [],
        },
    )


def _get_cached_room_config(hass: HomeAssistant, room_id: str) -> dict[str, Any] | None:
    """Return one normalized room config from cache when available."""
    try:
        entry_id, _room_name = split_room_id(room_id)
    except ValueError:
        return None

    cache = hass.data.setdefault(DOMAIN, {}).get("room_control_config_cache", {})
    entry_config = cache.get(entry_id)
    if not isinstance(entry_config, dict):
        return None
    rooms = entry_config.get("rooms", {})
    if not isinstance(rooms, dict):
        return None
    room_config = rooms.get(room_id)
    return room_config if isinstance(room_config, dict) else None


def _room_logging_enabled(hass: HomeAssistant, room_id: str) -> bool:
    """Return whether runtime logs should be recorded for one room."""
    room_config = _get_cached_room_config(hass, room_id)
    if not room_config:
        return True
    automation = room_config.get("automation", {})
    if not isinstance(automation, dict):
        return True
    return _safe_bool(automation.get("logging_enabled"), True)


def _append_runtime_log(
    hass: HomeAssistant,
    *,
    room_id: str,
    room_name: str,
    level: str,
    source: str,
    action: str,
    message: str,
    entity_ids: list[str] | None = None,
) -> None:
    """Append one runtime log line."""
    if not _room_logging_enabled(hass, room_id):
        return

    runtime = _runtime_store(hass)
    log_item = {
        "timestamp": dt_util.now().isoformat(),
        "room_id": room_id,
        "room_name": room_name,
        "level": level,
        "source": source,
        "action": action,
        "message": message,
        "entity_ids": entity_ids or [],
    }
    runtime["logs"].insert(0, log_item)
    del runtime["logs"][MAX_RUNTIME_LOGS:]
    if str(level or "").strip().lower() in {"error", "warning"}:
        from .notifications import async_notify_runtime_log

        hass.async_create_task(async_notify_runtime_log(hass, copy.deepcopy(log_item)))


def _schedule_allows_automation(room_config: dict[str, Any]) -> bool:
    """Return whether current time is within the configured schedule."""
    automation = room_config.get("automation", {})
    if not isinstance(automation, dict):
        return True
    schedule = automation.get("schedule", {})
    if not isinstance(schedule, dict):
        return True
    if not _safe_bool(schedule.get("enabled"), False):
        return True

    start_text = _safe_time_text(schedule.get("start_time"), "00:00")
    end_text = _safe_time_text(schedule.get("end_time"), "23:59")
    start_time = _parse_time_text(start_text)
    end_time = _parse_time_text(end_text)
    if start_time is None or end_time is None:
        return True

    now_time = dt_util.now().time().replace(second=0, microsecond=0)
    if start_time <= end_time:
        return start_time <= now_time <= end_time
    return now_time >= start_time or now_time <= end_time


def _apply_ac_temperature_limits(room_config: dict[str, Any], temperature: float | None) -> float | None:
    """Clamp AC temperature to configured limits when enabled."""
    if temperature is None:
        return None
    automation = room_config.get("automation", {})
    ac_automation = automation.get("ac", {}) if isinstance(automation, dict) else {}
    if not isinstance(ac_automation, dict):
        return temperature
    if not _safe_bool(ac_automation.get("temperature_limits_enabled"), False):
        return temperature

    min_temperature = _safe_float(ac_automation.get("min_temperature"), 16.0)
    max_temperature = _safe_float(ac_automation.get("max_temperature"), 30.0)
    if min_temperature is None:
        min_temperature = 16.0
    if max_temperature is None:
        max_temperature = 30.0
    if min_temperature > max_temperature:
        min_temperature, max_temperature = max_temperature, min_temperature
    return max(min_temperature, min(max_temperature, temperature))


def _get_subcontrol_config(room_config: dict[str, Any]) -> dict[str, Any]:
    """Return normalized subcontrol config."""
    subcontrol = room_config.get("subcontrol", {})
    if not isinstance(subcontrol, dict):
        subcontrol = {}
    return {
        "enabled": _safe_bool(subcontrol.get("enabled"), True),
        "allow_ac_power": _safe_bool(subcontrol.get("allow_ac_power"), True),
        "allow_ac_temperature": _safe_bool(subcontrol.get("allow_ac_temperature"), True),
        "allow_ac_mode": _safe_bool(subcontrol.get("allow_ac_mode"), True),
        "allow_ac_fan_mode": _safe_bool(subcontrol.get("allow_ac_fan_mode"), True),
        "allow_light_control": _safe_bool(subcontrol.get("allow_light_control"), True),
        "enforce_selected_season": _safe_bool(subcontrol.get("enforce_selected_season"), False),
        "inherit_temperature_limits": _safe_bool(subcontrol.get("inherit_temperature_limits"), True),
        "custom_temperature_limits_enabled": _safe_bool(
            subcontrol.get("custom_temperature_limits_enabled"),
            False,
        ),
        "min_temperature": _safe_float(subcontrol.get("min_temperature"), 16.0),
        "max_temperature": _safe_float(subcontrol.get("max_temperature"), 30.0),
    }


def _get_effective_subcontrol_temperature_range(
    room_config: dict[str, Any],
    ac_snapshot: dict[str, Any] | None = None,
) -> tuple[int, int]:
    """Return the effective AC temperature range for subcontrol."""
    minimum = 16
    maximum = 32

    if isinstance(ac_snapshot, dict):
        attributes = ac_snapshot.get("attributes", {})
        if isinstance(attributes, dict):
            minimum = _safe_int(attributes.get("min_temp"), minimum)
            maximum = _safe_int(attributes.get("max_temp"), maximum)

    minimum = max(16, min(32, minimum))
    maximum = max(minimum, min(32, maximum))

    subcontrol = _get_subcontrol_config(room_config)
    ac_automation = room_config.get("automation", {}).get("ac", {})
    if _safe_bool(subcontrol.get("custom_temperature_limits_enabled"), False):
        sub_minimum = _safe_float(subcontrol.get("min_temperature"), float(minimum))
        sub_maximum = _safe_float(subcontrol.get("max_temperature"), float(maximum))
        minimum = int(max(minimum, sub_minimum if sub_minimum is not None else minimum))
        maximum = int(min(maximum, sub_maximum if sub_maximum is not None else maximum))
        if minimum > maximum:
            minimum, maximum = maximum, minimum
    elif (
        isinstance(ac_automation, dict)
        and subcontrol.get("inherit_temperature_limits")
        and _safe_bool(ac_automation.get("temperature_limits_enabled"), False)
    ):
        minimum = int(max(minimum, _safe_float(ac_automation.get("min_temperature"), float(minimum)) or minimum))
        maximum = int(min(maximum, _safe_float(ac_automation.get("max_temperature"), float(maximum)) or maximum))
        if minimum > maximum:
            minimum, maximum = maximum, minimum

    return minimum, maximum


def _subcontrol_temperature_violation_reason(
    room_config: dict[str, Any],
    temperature: float,
    ac_snapshot: dict[str, Any] | None = None,
) -> str | None:
    """Return a validation message when requested temperature is out of range."""
    minimum, maximum = _get_effective_subcontrol_temperature_range(room_config, ac_snapshot)
    if temperature < minimum or temperature > maximum:
        return f"总控已限制温度范围为 {minimum}-{maximum}℃"
    return None


def _build_subcontrol_capability(
    *,
    enabled: bool,
    reason: str = "",
) -> dict[str, Any]:
    """Build one subcontrol capability descriptor."""
    return {"enabled": bool(enabled), "reason": str(reason or "").strip()}


def _get_subcontrol_allowed_hvac_modes(
    room_config: dict[str, Any],
    ac_snapshot: dict[str, Any] | None,
    subcontrol: dict[str, Any],
) -> list[str]:
    """Return HVAC modes exposed to the subcontrol client."""
    entity_modes = [
        str(mode).strip()
        for mode in ((ac_snapshot or {}).get("hvac_modes") or [])
        if str(mode).strip()
    ]
    if not entity_modes:
        return []

    configured_modes: list[str] = []
    seasons = ("summer", "winter", "custom")
    if subcontrol.get("enforce_selected_season"):
        seasons = (str(room_config.get("modes", {}).get("selected_season") or "summer"),)

    for season in seasons:
        season_config = room_config.get("modes", {}).get(season, {})
        if not isinstance(season_config, dict) or not season_config.get("enabled", True):
            continue
        hvac_mode = str(season_config.get("hvac_mode") or "").strip()
        if hvac_mode:
            configured_modes.append(hvac_mode)

    allowed_modes = []
    for mode in configured_modes:
        if mode in entity_modes and mode not in allowed_modes:
            allowed_modes.append(mode)

    return allowed_modes or entity_modes


def _build_subcontrol_ui_state(
    room_config: dict[str, Any],
    room_record: dict[str, Any],
    *,
    ac_snapshot: dict[str, Any] | None,
    light_snapshots: list[dict[str, Any]],
    automation_paused: bool,
) -> dict[str, Any]:
    """Return computed subcontrol availability and reasons for one room."""
    subcontrol = _get_subcontrol_config(room_config)
    global_reason = ""
    if automation_paused:
        global_reason = "自动化已暂停，分机控制不可用"
    elif not subcontrol.get("enabled"):
        global_reason = "总控已禁用该房间分机控制"
    elif not _schedule_allows_automation(room_config):
        global_reason = "当前不在总控允许的工作时段内"

    ac_entity_id = room_config["entities"]["ac"]
    ac_is_climate = bool(ac_snapshot and ac_snapshot.get("domain") == "climate")
    light_bound = bool(room_config["entities"]["lights"])
    temp_min, temp_max = _get_effective_subcontrol_temperature_range(room_config, ac_snapshot)
    allowed_hvac_modes = _get_subcontrol_allowed_hvac_modes(room_config, ac_snapshot, subcontrol)
    allowed_fan_modes = [
        str(mode).strip()
        for mode in ((ac_snapshot or {}).get("fan_modes") or [])
        if str(mode).strip()
    ]

    def _reason_for(disabled_by_policy: bool, message: str) -> str:
        if global_reason:
            return global_reason
        if disabled_by_policy:
            return message
        return ""

    caps = {
        "ac_power": _build_subcontrol_capability(
            enabled=bool(not global_reason and ac_entity_id and subcontrol.get("allow_ac_power")),
            reason=_reason_for(not ac_entity_id, "当前房间未绑定空调")
            or _reason_for(not subcontrol.get("allow_ac_power"), "总控已禁用分机空调电源控制"),
        ),
        "ac_temperature": _build_subcontrol_capability(
            enabled=bool(
                not global_reason
                and ac_is_climate
                and subcontrol.get("allow_ac_temperature")
            ),
            reason=_reason_for(not ac_entity_id, "当前房间未绑定空调")
            or _reason_for(not ac_is_climate, "当前空调不是 climate 实体，无法调温")
            or _reason_for(not subcontrol.get("allow_ac_temperature"), "总控已禁用分机温度调节"),
        ),
        "ac_mode": _build_subcontrol_capability(
            enabled=bool(
                not global_reason
                and ac_is_climate
                and subcontrol.get("allow_ac_power")
                and subcontrol.get("allow_ac_mode")
                and not subcontrol.get("enforce_selected_season")
            ),
            reason=_reason_for(not ac_entity_id, "当前房间未绑定空调")
            or _reason_for(not ac_is_climate, "当前空调不是 climate 实体，无法切换模式")
            or _reason_for(not subcontrol.get("allow_ac_power"), "总控已禁用分机空调电源控制")
            or _reason_for(subcontrol.get("enforce_selected_season"), "总控已锁定季节模式，分机不可切换模式")
            or _reason_for(not subcontrol.get("allow_ac_mode"), "总控已禁用分机模式切换"),
        ),
        "ac_fan_mode": _build_subcontrol_capability(
            enabled=bool(
                not global_reason
                and ac_is_climate
                and subcontrol.get("allow_ac_fan_mode")
                and bool((ac_snapshot or {}).get("fan_modes"))
            ),
            reason=_reason_for(not ac_entity_id, "当前房间未绑定空调")
            or _reason_for(not ac_is_climate, "当前空调不是 climate 实体，无法切换风速")
            or _reason_for(not subcontrol.get("allow_ac_fan_mode"), "总控已禁用分机风速切换")
            or _reason_for(not bool((ac_snapshot or {}).get("fan_modes")), "当前空调不支持风速调节"),
        ),
        "light_control": _build_subcontrol_capability(
            enabled=bool(not global_reason and light_bound and subcontrol.get("allow_light_control")),
            reason=_reason_for(not light_bound, "当前房间未绑定灯光")
            or _reason_for(not subcontrol.get("allow_light_control"), "总控已禁用分机灯光控制"),
        ),
    }

    return {
        "ui_caps": caps,
        "ui_reasons": {key: value["reason"] for key, value in caps.items()},
        "effective_limits": {
            "ac_temperature_min": temp_min,
            "ac_temperature_max": temp_max,
        },
        "allowed_controls": {
            "hvac_modes": allowed_hvac_modes if subcontrol.get("allow_ac_mode") else [],
            "fan_modes": allowed_fan_modes if subcontrol.get("allow_ac_fan_mode") else [],
            "temperature_min": temp_min,
            "temperature_max": temp_max,
        },
        "subcontrol": subcontrol,
        "runtime": {
            "ac_manual_override_until": room_record.get("runtime", {}).get("ac_manual_override_until")
            if isinstance(room_record.get("runtime"), dict)
            else None,
            "schedule_allowed": _schedule_allows_automation(room_config),
        },
    }


def _normalize_local_ips(local_ip: str | list[str]) -> list[str]:
    """Normalize one or more local IP values."""
    local_ips = (
        [str(item or "").strip() for item in local_ip]
        if isinstance(local_ip, list)
        else [str(local_ip or "").strip()]
    )
    return [item for item in local_ips if item]


async def async_get_subcontrol_mapping_payload(hass: HomeAssistant) -> dict[str, Any]:
    """Return the current CSV mapping payload used by subcontrol clients."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise LookupError("未找到 netcafe_automation 配置项")

    mapping_by_ip: dict[str, dict[str, Any]] = {}
    source_entry_ids: list[str] = []

    for entry in entries:
        storage = StorageManager(hass, entry.entry_id)
        csv_content = await storage.async_load_csv()
        if not csv_content:
            csv_content = str(entry.data.get(CONF_CSV_CONTENT, "") or "")
        csv_content = str(csv_content or "").lstrip("\ufeff").strip()
        if not csv_content:
            continue

        source_entry_ids.append(entry.entry_id)
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            ip_address = str(row.get(FIELD_IP_ADDRESS, "") or "").strip()
            room_name = str(row.get(FIELD_ROOM_NAME, "") or "").strip()
            if not ip_address or not room_name:
                continue

            room_id = build_room_id(entry.entry_id, room_name)
            candidate = {
                "entry_id": entry.entry_id,
                "entry_title": entry.title,
                "room_id": room_id,
                "room_name": room_name,
                "ip_address": ip_address,
            }
            existing = mapping_by_ip.get(ip_address)
            if existing and existing["room_id"] != room_id:
                raise RuntimeError(
                    f"IP {ip_address} 在主机 CSV 中重复分配到多个房间："
                    f"{existing['room_name']} / {room_name}"
                )
            mapping_by_ip[ip_address] = candidate

    if not mapping_by_ip:
        raise LookupError("未找到可用的 IP 映射 CSV")

    records = sorted(
        mapping_by_ip.values(),
        key=lambda item: (item["entry_title"], item["room_name"], item["ip_address"]),
    )
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([FIELD_IP_ADDRESS, FIELD_ROOM_NAME])
    for item in records:
        writer.writerow([item["ip_address"], item["room_name"]])

    csv_content = output.getvalue()
    return {
        "csv_content": csv_content,
        "hash": hashlib.sha256(csv_content.encode("utf-8")).hexdigest(),
        "row_count": len(records),
        "entry_ids": source_entry_ids,
        "generated_at": dt_util.utcnow().isoformat(),
        "records": records,
    }


async def async_get_room_record_by_local_ip(
    hass: HomeAssistant, local_ip: str | list[str]
) -> dict[str, Any]:
    """Resolve one room record by exact local IP match against the latest CSV source."""
    local_ips = _normalize_local_ips(local_ip)
    local_ips = [item for item in local_ips if item]
    if not local_ips:
        raise ValueError("缺少 local_ip")

    mapping_payload = await async_get_subcontrol_mapping_payload(hass)
    mapping_by_ip = {
        item["ip_address"]: item
        for item in mapping_payload.get("records", [])
        if item.get("ip_address")
    }
    matched_mappings: list[dict[str, Any]] = []
    for ip_address in local_ips:
        matched = mapping_by_ip.get(ip_address)
        if matched is None:
            continue
        if not any(item["room_id"] == matched["room_id"] for item in matched_mappings):
            matched_mappings.append({**matched, "matched_local_ip": ip_address})

    if not matched_mappings:
        raise LookupError(f"IP {', '.join(local_ips)} 未在主机当前 CSV 中分配")
    if len(matched_mappings) > 1:
        raise RuntimeError(f"本机 IP {', '.join(local_ips)} 在主机 CSV 中匹配到多个房间，无法唯一识别")

    mapping_record = matched_mappings[0]
    room_record = next(
        (item for item in get_room_records(hass) if item["room_id"] == mapping_record["room_id"]),
        None,
    )
    if room_record is None:
        raise RuntimeError(
            f"IP {mapping_record['matched_local_ip']} 已在主机 CSV 中分配到房间"
            f" {mapping_record['room_name']}，但主机房间运行时尚未就绪"
        )

    return {
        **room_record,
        "matched_local_ip": mapping_record["matched_local_ip"],
        "mapping_hash": mapping_payload["hash"],
        "mapping_generated_at": mapping_payload["generated_at"],
        "mapping_entry_id": mapping_record["entry_id"],
    }


async def async_get_subcontrol_bootstrap(
    hass: HomeAssistant,
    local_ip: str | list[str],
    *,
    license_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bootstrap payload for one subcontrol client."""
    room_record = await async_get_room_record_by_local_ip(hass, local_ip)
    system_config = await async_load_system_config(hass)
    room_config = system_config["rooms"].get(
        room_record["room_id"],
        _default_room_config(room_record["room_id"], room_record["room_name"]),
    )

    ac_snapshot = (
        _build_entity_snapshot(hass, room_config["entities"]["ac"])
        if room_config["entities"]["ac"]
        else None
    )
    light_snapshots = [
        _build_entity_snapshot(hass, entity_id)
        for entity_id in room_config["entities"]["lights"]
    ]
    runtime = _runtime_store(hass)
    room_state = _get_room_state(runtime, room_record["room_id"])
    room_record_with_runtime = {
        **room_record,
        "runtime": {
            "ac_manual_override_until": (
                room_state.get("ac_manual_override_until").isoformat()
                if room_state.get("ac_manual_override_until")
                else None
            ),
        },
    }
    license_status = license_status or {}
    ui_state = _build_subcontrol_ui_state(
        room_config,
        room_record_with_runtime,
        ac_snapshot=ac_snapshot,
        light_snapshots=light_snapshots,
        automation_paused=bool(hass.data.get(DOMAIN, {}).get("automation_paused")),
    )

    return {
        "room_id": room_record["room_id"],
        "room_name": room_record["room_name"],
        "entry_title": room_record["entry_title"],
        "local_ip": room_record.get("matched_local_ip") or (local_ip[0] if isinstance(local_ip, list) else local_ip),
        "matched_local_ip": room_record.get("matched_local_ip"),
        "resolved_by": "netcafe_automation_csv_ip",
        "mapping_hash": room_record.get("mapping_hash"),
        "mapping_generated_at": room_record.get("mapping_generated_at"),
        "mapping_entry_id": room_record.get("mapping_entry_id"),
        "policy": {
            "subcontrol": ui_state["subcontrol"],
            "automation": room_config["automation"],
            "runtime": ui_state["runtime"],
        },
        "ac": ac_snapshot,
        "lights": light_snapshots,
        "ui_caps": ui_state["ui_caps"],
        "ui_reasons": ui_state["ui_reasons"],
        "effective_limits": ui_state["effective_limits"],
        "allowed_controls": ui_state["allowed_controls"],
        "license": license_status,
        "server_time": dt_util.now().isoformat(),
    }


def _subcontrol_denied_message(
    room_config: dict[str, Any],
    action: str,
    *,
    value: Any = None,
) -> str | None:
    """Return denial reason for a subcontrol action."""
    subcontrol = _get_subcontrol_config(room_config)
    if not subcontrol.get("enabled"):
        return "总控已禁用该房间分机控制"
    if not _schedule_allows_automation(room_config):
        return "当前不在总控允许的工作时段内"

    ac_entity_id = room_config["entities"]["ac"]
    light_entity_ids = room_config["entities"]["lights"]
    if action in {"ac_turn_on", "ac_turn_off"}:
        if not ac_entity_id:
            return "当前房间未绑定空调"
        if not subcontrol.get("allow_ac_power"):
            return "总控已禁用分机空调电源控制"
        if action == "ac_turn_on" and subcontrol.get("enforce_selected_season"):
            return None
    elif action == "ac_set_temperature":
        if not ac_entity_id:
            return "当前房间未绑定空调"
        if not str(ac_entity_id).startswith("climate."):
            return "当前空调不是 climate 实体，无法调温"
        if not subcontrol.get("allow_ac_temperature"):
            return "总控已禁用分机温度调节"
        temperature = _safe_float(value)
        if temperature is None:
            return "temperature 无效"
        if subcontrol.get("inherit_temperature_limits"):
            violation = _subcontrol_temperature_violation_reason(room_config, temperature)
            if violation:
                return violation
    elif action == "ac_set_hvac_mode":
        if not ac_entity_id:
            return "当前房间未绑定空调"
        if not str(ac_entity_id).startswith("climate."):
            return "当前空调不是 climate 实体，无法切换模式"
        if not subcontrol.get("allow_ac_power"):
            return "总控已禁用分机空调电源控制"
        if subcontrol.get("enforce_selected_season"):
            return "总控已锁定季节模式，分机不可切换模式"
        if not subcontrol.get("allow_ac_mode"):
            return "总控已禁用分机模式切换"
    elif action == "ac_set_fan_mode":
        if not ac_entity_id:
            return "当前房间未绑定空调"
        if not str(ac_entity_id).startswith("climate."):
            return "当前空调不是 climate 实体，无法切换风速"
        if not subcontrol.get("allow_ac_fan_mode"):
            return "总控已禁用分机风速切换"
    elif action.startswith("light_"):
        if not light_entity_ids:
            return "当前房间未绑定灯光"
        if not subcontrol.get("allow_light_control"):
            return "总控已禁用分机灯光控制"
    elif action.startswith("fresh_air_"):
        return "当前分机不支持新风控制"
    return None


def _get_cached_room_config_for_record(
    hass: HomeAssistant,
    entry_id: str,
    room_id: str,
    room_name: str,
) -> dict[str, Any]:
    """Return one normalized room config from the in-memory cache when available."""
    domain_data = hass.data.get(DOMAIN, {})
    cache = domain_data.get("room_control_config_cache", {})
    entry_config = cache.get(entry_id, {}) if isinstance(cache, dict) else {}
    rooms = entry_config.get("rooms", {}) if isinstance(entry_config, dict) else {}
    raw_room_config = rooms.get(room_id) if isinstance(rooms, dict) else None
    return normalize_room_config(raw_room_config, room_id=room_id, room_name=room_name)


def _match_keyword_filters(text: str, include_keywords: list[str], exclude_keywords: list[str]) -> bool:
    """Return whether one text passes include/exclude keyword filtering."""
    source = str(text or "").lower()
    include_list = [str(item or "").strip().lower() for item in include_keywords if str(item or "").strip()]
    exclude_list = [str(item or "").strip().lower() for item in exclude_keywords if str(item or "").strip()]
    if include_list and not any(keyword in source for keyword in include_list):
        return False
    if any(keyword in source for keyword in exclude_list):
        return False
    return True


def _presence_state_is_active(state: Any) -> bool:
    """Return whether a sensor-like or tracker-like state should count as occupied."""
    raw_state = str(getattr(state, "state", "") or "").strip().lower()
    if raw_state in {"home", "on", "online", "connected", "present", "occupied", "detected", "open", "true"}:
        return True
    if raw_state in {"off", "offline", "disconnected", "not_home", "away", "absent", "unoccupied", "clear", "false", "unknown", "unavailable"}:
        return False
    numeric = _safe_float(raw_state)
    if numeric is not None:
        return numeric > 0
    return False


def _collect_room_presence_matches(
    hass: HomeAssistant,
    room_name: str,
    *,
    domains: tuple[str, ...],
    include_keywords: list[str],
    exclude_keywords: list[str],
    explicit_entity_id: str = "",
) -> list[dict[str, Any]]:
    """Return matched presence entities for one room."""
    matches: list[dict[str, Any]] = []
    explicit_id = str(explicit_entity_id or "").strip()
    explicit_state = hass.states.get(explicit_id) if explicit_id else None
    if explicit_state is not None:
        matches.append(
            {
                "entity_id": explicit_id,
                "friendly_name": str(explicit_state.name or explicit_id).strip(),
                "score": 9999,
                "is_active": _presence_state_is_active(explicit_state),
            }
        )

    for state in hass.states.async_all():
        entity_id = str(getattr(state, "entity_id", "") or "").strip()
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain not in domains:
            continue
        if explicit_id and entity_id == explicit_id:
            continue
        friendly_name = str(getattr(state, "name", "") or entity_id).strip()
        source_text = f"{friendly_name} {entity_id}"
        if not _match_keyword_filters(source_text, include_keywords, exclude_keywords):
            continue
        score = _score_room_match(room_name, entity_id, friendly_name)
        if score <= 0:
            continue
        matches.append(
            {
                "entity_id": entity_id,
                "friendly_name": friendly_name,
                "score": score,
                "is_active": _presence_state_is_active(state),
            }
        )

    matches.sort(key=lambda item: (-int(item["score"]), str(item["entity_id"])))
    return matches


def _resolve_room_occupancy(
    hass: HomeAssistant,
    room_config: dict[str, Any],
    room_name: str,
    fallback_occupied_count: int,
    fallback_total_count: int,
) -> tuple[bool, int, int]:
    """Resolve occupancy using configured trigger mode with fallback to computer connectivity."""
    automation = room_config.get("automation", {}) if isinstance(room_config, dict) else {}
    trigger_mode = str(automation.get("trigger_mode") or "device_tracker").strip().lower()
    if trigger_mode not in {"device_tracker", "sensor", "hybrid"}:
        trigger_mode = "device_tracker"

    tracker_matches: list[dict[str, Any]] = []
    sensor_matches: list[dict[str, Any]] = []
    if trigger_mode in {"device_tracker", "hybrid"}:
        tracker_matches = _collect_room_presence_matches(
            hass,
            room_name,
            domains=("device_tracker",),
            include_keywords=automation.get("device_tracker_include_keywords", []) or [],
            exclude_keywords=automation.get("device_tracker_exclude_keywords", []) or [],
            explicit_entity_id=str(automation.get("device_tracker_entity") or ""),
        )
    if trigger_mode in {"sensor", "hybrid"}:
        sensor_matches = _collect_room_presence_matches(
            hass,
            room_name,
            domains=("sensor", "binary_sensor"),
            include_keywords=automation.get("presence_sensor_include_keywords", []) or [],
            exclude_keywords=automation.get("presence_sensor_exclude_keywords", []) or [],
            explicit_entity_id=str(automation.get("presence_sensor_entity") or ""),
        )

    tracker_active = sum(1 for item in tracker_matches if item.get("is_active"))
    sensor_active = sum(1 for item in sensor_matches if item.get("is_active"))
    matched_total = len(tracker_matches) + len(sensor_matches)
    active_total = tracker_active + sensor_active

    if trigger_mode == "device_tracker" and tracker_matches:
        return tracker_active > 0, active_total, matched_total
    if trigger_mode == "sensor" and sensor_matches:
        return sensor_active > 0, active_total, matched_total
    if trigger_mode == "hybrid" and (tracker_matches or sensor_matches):
        return active_total > 0, active_total, matched_total
    return fallback_occupied_count > 0, fallback_occupied_count, max(fallback_total_count, 0)


def get_room_records(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Return all room records with current occupancy state."""
    domain_data = hass.data.get(DOMAIN, {})
    devices = domain_data.get(CONF_DEVICES, {})
    room_records: list[dict[str, Any]] = []

    for entry in hass.config_entries.async_entries(DOMAIN):
        rooms_data = domain_data.get(entry.entry_id, {})
        if not isinstance(rooms_data, dict):
            continue

        for room_name, room_config in rooms_data.items():
            if not isinstance(room_config, dict):
                continue
            computers = []
            occupied_count = 0
            for computer in room_config.get("computers", []):
                if not isinstance(computer, dict):
                    continue
                entity_id = str(computer.get("entity_id") or "").strip()
                ip_address = str(computer.get("ip_address") or "").strip()
                device = devices.get(entity_id)
                entity_state = hass.states.get(entity_id)
                is_connected = bool(device and getattr(device, "_reachable", False))
                if is_connected:
                    occupied_count += 1
                computers.append(
                    {
                        "entity_id": entity_id,
                        "ip_address": ip_address,
                        "friendly_name": entity_state.name if entity_state else "",
                        "host_name": (
                            str(entity_state.attributes.get("host_name") or "")
                            if entity_state is not None
                            else ""
                        ),
                        "is_connected": is_connected,
                        "probe_state": getattr(device, "_probe_state", "") if device else "",
                        "last_probe_method": getattr(device, "_last_probe_method", "") if device else "",
                        "last_seen": (
                            getattr(device, "_last_seen", None).isoformat()
                            if device and getattr(device, "_last_seen", None)
                            else None
                        ),
                    }
                )

            room_id = build_room_id(entry.entry_id, room_name)
            normalized_room_config = _get_cached_room_config_for_record(hass, entry.entry_id, room_id, room_name)
            occupied, resolved_occupied_count, resolved_total_count = _resolve_room_occupancy(
                hass,
                normalized_room_config,
                room_name,
                occupied_count,
                len(computers),
            )
            actual_computer_total = len(computers)

            room_records.append(
                {
                    "entry_id": entry.entry_id,
                    "entry_title": entry.title,
                    "room_name": room_name,
                    "room_id": room_id,
                    "occupied": occupied,
                    "occupied_count": resolved_occupied_count,
                    "computer_count": actual_computer_total,
                    "presence_match_count": resolved_total_count,
                    "computers": computers,
                }
            )

    room_records.sort(key=lambda item: (item["entry_title"], item["room_name"]))
    return room_records


def _build_entity_snapshot(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Build a frontend-friendly state snapshot."""
    state = hass.states.get(entity_id)
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    if state is None:
        return {
            "entity_id": entity_id,
            "domain": domain,
            "exists": False,
            "available": False,
            "friendly_name": entity_id,
            "entity_name": entity_id,
            "state": "missing",
        }

    attributes = dict(state.attributes)
    snapshot: dict[str, Any] = {
        "entity_id": entity_id,
        "domain": domain,
        "exists": True,
        "available": state.state not in {"unavailable", "unknown"},
        "friendly_name": state.name,
        "entity_name": _clean_entity_display_name(hass, entity_id, state.name),
        "state": state.state,
        "last_changed": state.last_changed.isoformat(),
        "attributes": attributes,
    }

    if domain == "climate":
        snapshot.update(
            {
                "is_on": state.state not in {"off", "unavailable", "unknown"},
                "hvac_mode": state.state,
                "hvac_modes": attributes.get("hvac_modes", []),
                "temperature": attributes.get("temperature"),
                "current_temperature": attributes.get("current_temperature"),
                "fan_mode": attributes.get("fan_mode"),
                "fan_modes": attributes.get("fan_modes", []),
                "supported": {
                    "temperature": attributes.get("temperature") is not None,
                    "hvac_mode": bool(attributes.get("hvac_modes")),
                    "fan_mode": bool(attributes.get("fan_modes")),
                },
            }
        )
    elif domain == "light":
        brightness = attributes.get("brightness")
        snapshot.update(
            {
                "is_on": state.state == "on",
                "brightness_pct": round((float(brightness) / 255.0) * 100, 1)
                if brightness is not None
                else None,
            }
        )
    elif domain == "fan":
        snapshot.update(
            {
                "is_on": state.state == "on",
                "preset_mode": attributes.get("preset_mode"),
                "preset_modes": attributes.get("preset_modes", []),
                "percentage": attributes.get("percentage"),
            }
        )
    elif domain == "sensor":
        unit = (
            attributes.get("unit_of_measurement")
            or attributes.get("native_unit_of_measurement")
            or ""
        )
        numeric_value = _parse_numeric_state_value(state.state)
        snapshot.update(
            {
                "numeric_value": numeric_value,
                "unit_of_measurement": unit,
                "device_class": attributes.get("device_class"),
                "state_class": attributes.get("state_class"),
            }
        )
    else:
        snapshot.update({"is_on": state.state == "on"})

    return snapshot


def _build_light_preset_entities(room_config: dict[str, Any], preset_name: str) -> list[str]:
    """Return the effective entity list for one lighting preset."""
    selected_lights = room_config["entities"]["lights"]
    preset_lights = room_config["lighting_presets"].get(preset_name, [])
    if preset_lights:
        return preset_lights

    if preset_name == "full_on":
        return selected_lights
    if preset_name == "full_off":
        return selected_lights
    if preset_name == "half_on":
        half = max(1, len(selected_lights) // 2) if selected_lights else 0
        return selected_lights[:half]
    return []


def _is_energy_sensor_candidate(state: Any) -> bool:
    """Return whether one HA state looks like a power/energy sensor."""
    if state is None or not str(getattr(state, "entity_id", "")).startswith("sensor."):
        return False
    attributes = dict(getattr(state, "attributes", {}) or {})
    unit = str(
        attributes.get("unit_of_measurement")
        or attributes.get("native_unit_of_measurement")
        or ""
    ).strip().lower()
    device_class = str(attributes.get("device_class") or "").strip().lower()
    combined = f"{getattr(state, 'name', '')} {getattr(state, 'entity_id', '')}".lower()

    if device_class in {"power", "energy"}:
        return True
    if unit in {"w", "kw", "wh", "kwh"}:
        return True
    if any(keyword.lower() in combined for keyword in (*ENERGY_POWER_KEYWORDS, *ENERGY_DAILY_KEYWORDS, *ENERGY_MONTHLY_KEYWORDS)):
        return True
    return False


async def _load_entry_config(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    """Load entry config from storage and cache it."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    cache = domain_data.setdefault("room_control_config_cache", {})
    if entry_id in cache:
        return copy.deepcopy(cache[entry_id])

    storage_managers = domain_data.get("storage_managers", {})
    storage = storage_managers.get(entry_id)
    if storage is None:
        cache[entry_id] = {
            "version": ROOM_CONFIG_VERSION,
            "rooms": {},
            "dashboard": _default_dashboard_config(),
            "ui": _default_ui_config(),
            "notifications": _default_notifications_config(),
            "global_settings": _default_global_settings(),
        }
        return copy.deepcopy(cache[entry_id])

    data = await storage.async_load_config()
    if not isinstance(data, dict):
        data = {}
    if not isinstance(data.get("rooms"), dict):
        data["rooms"] = {}
    data["dashboard"] = _normalize_dashboard_config(data.get("dashboard"))
    data["ui"] = _normalize_ui_config(data.get("ui"))
    data["notifications"] = normalize_notifications_config(data.get("notifications"))
    data["global_settings"] = normalize_global_settings(data.get("global_settings"))
    data["version"] = ROOM_CONFIG_VERSION
    cache[entry_id] = data
    return copy.deepcopy(data)


def _store_entry_config_cache(hass: HomeAssistant, entry_id: str, config_data: dict[str, Any]) -> None:
    """Update the entry config cache."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    cache = domain_data.setdefault("room_control_config_cache", {})
    cache[entry_id] = copy.deepcopy(config_data)


async def async_load_system_config(hass: HomeAssistant) -> dict[str, Any]:
    """Load and normalize room config for all configured entries."""
    config_data: dict[str, Any] = {
        "version": ROOM_CONFIG_VERSION,
        "rooms": {},
        "dashboard": _default_dashboard_config(),
        "ui": _default_ui_config(),
        "notifications": _default_notifications_config(),
        "global_settings": _default_global_settings(),
    }
    room_records = get_room_records(hass)
    inference_candidates = _collect_entity_candidates_for_inference(hass)
    room_groups = _resolve_entity_room_groups(inference_candidates)
    entity_name_lookup = _build_entity_name_lookup(inference_candidates)

    for entry in hass.config_entries.async_entries(DOMAIN):
        entry_config = await _load_entry_config(hass, entry.entry_id)
        config_data["dashboard"] = _normalize_dashboard_config(entry_config.get("dashboard"))
        config_data["ui"] = _normalize_ui_config(entry_config.get("ui"))
        config_data["notifications"] = normalize_notifications_config(entry_config.get("notifications"))
        config_data["global_settings"] = normalize_global_settings(entry_config.get("global_settings"))
        break

    for room_record in room_records:
        entry_config = await _load_entry_config(hass, room_record["entry_id"])
        room_configs = entry_config.get("rooms", {})
        raw_room_config = room_configs.get(room_record["room_id"])
        normalized = normalize_room_config(
            raw_room_config,
            room_id=room_record["room_id"],
            room_name=room_record["room_name"],
        )
        normalized = _merge_global_settings_into_room_config(normalized, config_data["global_settings"])
        matched_group = _find_room_group_for_record(room_record, room_groups)
        inferred = _infer_room_entities(room_record["room_name"], inference_candidates)

        if matched_group is not None:
            if not normalized["entities"]["ac"] and matched_group["entities"]["ac"]:
                normalized["entities"]["ac"] = matched_group["entities"]["ac"][0]
            if not normalized["entities"]["lights"] and matched_group["entities"]["lights"]:
                normalized["entities"]["lights"] = list(matched_group["entities"]["lights"])
            if not normalized["entities"]["fresh_air"] and matched_group["entities"]["fresh_air"]:
                normalized["entities"]["fresh_air"] = matched_group["entities"]["fresh_air"][0]

        if not normalized["entities"]["ac"] and inferred["ac"]:
            normalized["entities"]["ac"] = inferred["ac"]
        if not normalized["entities"]["lights"] and inferred["lights"]:
            normalized["entities"]["lights"] = inferred["lights"]
        if not normalized["entities"]["fresh_air"] and inferred["fresh_air"]:
            normalized["entities"]["fresh_air"] = inferred["fresh_air"]

        normalized = _apply_global_entity_filters_to_room_config(
            normalized,
            matched_group=matched_group,
            inferred=inferred,
            entity_name_lookup=entity_name_lookup,
        )
        config_data["rooms"][room_record["room_id"]] = normalized
    return config_data


async def async_get_room_name_diagnostics(hass: HomeAssistant) -> dict[str, Any]:
    """Return derived room display names and raw scoring details."""
    room_records = get_room_records(hass)
    system_config = await async_load_system_config(hass)
    inference_candidates = _collect_entity_candidates_for_inference(hass)
    room_groups = _resolve_entity_room_groups(inference_candidates)
    rooms: list[dict[str, Any]] = []

    for room_record in room_records:
        room_id = room_record["room_id"]
        room_config = system_config["rooms"].get(
            room_id,
            _default_room_config(room_id, room_record["room_name"]),
        )
        display_name, scores, matched_group = _resolve_room_display_from_group(
            room_record,
            room_config,
            room_groups,
        )
        entity_ids = list(matched_group.get("entity_ids") or []) if matched_group else []
        if not entity_ids:
            entity_ids = [
                str(room_config["entities"].get("ac") or "").strip(),
                *[str(item).strip() for item in room_config["entities"].get("lights", [])],
                str(room_config["entities"].get("fresh_air") or "").strip(),
            ]
            entity_ids = [item for item in entity_ids if item]
        rooms.append(
            {
                "room_id": room_id,
                "room_name": room_record["room_name"],
                "display_name": display_name,
                "display_name_scores": scores,
                "entity_ids": entity_ids,
                "matched_group": matched_group,
            }
        )

    return {
        "rooms": rooms,
        "groups": sorted(room_groups.values(), key=lambda item: str(item.get("display_name") or "")),
    }


async def async_save_system_config(hass: HomeAssistant, partial_config: dict[str, Any]) -> dict[str, Any]:
    """Merge and save room config into entry storage files."""
    if not isinstance(partial_config, dict):
        raise ValueError("config 必须是对象")

    partial_rooms = partial_config.get("rooms")
    if partial_rooms is None:
        partial_rooms = {}
    if not isinstance(partial_rooms, dict):
        raise ValueError("config.rooms 必须是对象")
    existing_dashboard_config = _default_dashboard_config()
    existing_ui_config = _default_ui_config()
    existing_notifications_config = _default_notifications_config()
    existing_global_settings = _default_global_settings()
    for entry in hass.config_entries.async_entries(DOMAIN):
        entry_config = await _load_entry_config(hass, entry.entry_id)
        existing_dashboard_config = _normalize_dashboard_config(entry_config.get("dashboard"))
        existing_ui_config = _normalize_ui_config(entry_config.get("ui"))
        existing_notifications_config = normalize_notifications_config(entry_config.get("notifications"))
        existing_global_settings = normalize_global_settings(entry_config.get("global_settings"))
        break
    dashboard_config = (
        _normalize_dashboard_config(partial_config.get("dashboard"))
        if "dashboard" in partial_config
        else existing_dashboard_config
    )
    ui_config = (
        _normalize_ui_config(partial_config.get("ui"))
        if "ui" in partial_config
        else existing_ui_config
    )
    notifications_config = (
        normalize_notifications_config(partial_config.get("notifications"))
        if "notifications" in partial_config
        else existing_notifications_config
    )
    global_settings = (
        normalize_global_settings(partial_config.get("global_settings"))
        if "global_settings" in partial_config
        else existing_global_settings
    )

    room_records = get_room_records(hass)
    room_records_by_id = {item["room_id"]: item for item in room_records}
    updates_by_entry: dict[str, dict[str, Any]] = {}

    for room_id, room_payload in partial_rooms.items():
        room_record = room_records_by_id.get(room_id)
        if room_record is None:
            continue
        normalized = normalize_room_config(
            room_payload if isinstance(room_payload, dict) else {},
            room_id=room_record["room_id"],
            room_name=room_record["room_name"],
        )
        updates_by_entry.setdefault(room_record["entry_id"], {})[room_id] = normalized

    domain_data = hass.data.setdefault(DOMAIN, {})
    storage_managers = domain_data.get("storage_managers", {})
    save_results: dict[str, Any] = {
        "version": ROOM_CONFIG_VERSION,
        "rooms": {},
        "dashboard": dashboard_config,
        "ui": ui_config,
        "notifications": notifications_config,
        "global_settings": global_settings,
    }

    for entry in hass.config_entries.async_entries(DOMAIN):
        storage = storage_managers.get(entry.entry_id)
        if storage is None:
            continue

        entry_room_records = [item for item in room_records if item["entry_id"] == entry.entry_id]
        entry_config = await _load_entry_config(hass, entry.entry_id)
        existing_rooms = entry_config.get("rooms", {})
        merged_rooms: dict[str, Any] = {}

        for room_record in entry_room_records:
            room_id = room_record["room_id"]
            source = updates_by_entry.get(entry.entry_id, {}).get(room_id, existing_rooms.get(room_id))
            merged_rooms[room_id] = normalize_room_config(
                source,
                room_id=room_id,
                room_name=room_record["room_name"],
            )
            save_results["rooms"][room_id] = merged_rooms[room_id]

        entry_config_to_save = {
            "version": ROOM_CONFIG_VERSION,
            "rooms": merged_rooms,
            "dashboard": dashboard_config,
            "ui": ui_config,
            "notifications": notifications_config,
            "global_settings": global_settings,
        }
        saved = await storage.async_save_config(entry_config_to_save)
        if not saved:
            raise RuntimeError(f"配置保存失败: {entry.title}")
        _store_entry_config_cache(hass, entry.entry_id, entry_config_to_save)

    return save_results


def _get_room_state(runtime: dict[str, Any], room_id: str) -> dict[str, Any]:
    """Return or create the room runtime state."""
    return runtime["rooms"].setdefault(
        room_id,
        {
            "occupied": None,
            "pending": {},
            "ac_manual_override_until": None,
        },
    )


def _cancel_room_pending(room_state: dict[str, Any]) -> None:
    """Cancel all pending handles for one room."""
    pending = room_state.get("pending", {})
    for cancel_callback in pending.values():
        try:
            cancel_callback()
        except Exception:
            pass
    pending.clear()


def _cancel_room_pending_prefix(room_state: dict[str, Any], prefix: str) -> None:
    """Cancel pending callbacks with the given key prefix."""
    pending = room_state.get("pending", {})
    for key in list(pending.keys()):
        if not key.startswith(prefix):
            continue
        cancel_callback = pending.pop(key, None)
        if cancel_callback:
            try:
                cancel_callback()
            except Exception:
                pass


async def async_initialize_room_control_runtime(hass: HomeAssistant) -> None:
    """Sync runtime state with current rooms without executing automations."""
    runtime = _runtime_store(hass)
    current_room_ids = {item["room_id"] for item in get_room_records(hass)}

    for room_id in list(runtime["rooms"].keys()):
        if room_id not in current_room_ids:
            _cancel_room_pending(runtime["rooms"][room_id])
            runtime["rooms"].pop(room_id, None)

    for room_record in get_room_records(hass):
        room_state = _get_room_state(runtime, room_record["room_id"])
        room_state["occupied"] = room_record["occupied"]
        if not room_record["occupied"]:
            room_state["ac_manual_override_until"] = None


async def async_reset_room_control_runtime(
    hass: HomeAssistant,
    *,
    clear_logs: bool = False,
) -> None:
    """Cancel pending room automations and optionally clear logs."""
    runtime = _runtime_store(hass)
    for room_state in runtime["rooms"].values():
        _cancel_room_pending(room_state)
        room_state["occupied"] = None
        room_state["ac_manual_override_until"] = None
    if clear_logs:
        runtime["logs"] = []


async def async_get_recent_room_logs(hass: HomeAssistant, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent runtime logs."""
    runtime = _runtime_store(hass)
    return copy.deepcopy(runtime["logs"][: max(0, limit)])


async def async_get_room_overview(hass: HomeAssistant) -> dict[str, Any]:
    """Build the read-only overview for dashboard pages."""
    system_config = await async_load_system_config(hass)
    dashboard_config = _normalize_dashboard_config(system_config.get("dashboard"))
    runtime = _runtime_store(hass)
    inference_candidates = _collect_entity_candidates_for_inference(hass)
    room_groups = _resolve_entity_room_groups(inference_candidates)
    rooms: list[dict[str, Any]] = []

    for room_record in get_room_records(hass):
        room_config = system_config["rooms"].get(
            room_record["room_id"],
            _default_room_config(room_record["room_id"], room_record["room_name"]),
        )
        display_name, display_scores, matched_group = _resolve_room_display_from_group(
            room_record,
            room_config,
            room_groups,
        )
        resolved_entities = room_config["entities"]
        ac_snapshot = None
        if resolved_entities["ac"]:
            ac_snapshot = _build_entity_snapshot(hass, resolved_entities["ac"])

        light_snapshots = [
            _build_entity_snapshot(hass, entity_id)
            for entity_id in resolved_entities["lights"]
        ]
        fresh_air_snapshot = None
        if resolved_entities["fresh_air"]:
            fresh_air_snapshot = _build_entity_snapshot(
                hass,
                resolved_entities["fresh_air"],
            )

        lights_on = sum(1 for item in light_snapshots if item.get("is_on"))
        room_state = _get_room_state(runtime, room_record["room_id"])
        rooms.append(
            {
                **room_record,
                "display_name": display_name,
                "display_name_scores": display_scores,
                "matched_group": matched_group,
                "mapped": {
                    "ac": ac_snapshot,
                    "lights": light_snapshots,
                    "fresh_air": fresh_air_snapshot,
                },
                "summary": {
                    "light_total": len(light_snapshots),
                    "light_on": lights_on,
                    "has_mapping": bool(
                        resolved_entities["ac"]
                        or resolved_entities["lights"]
                        or resolved_entities["fresh_air"]
                    ),
                },
                "runtime": {
                    "ac_manual_override_until": (
                        room_state.get("ac_manual_override_until").isoformat()
                        if room_state.get("ac_manual_override_until")
                        else None
                    ),
                    "schedule_allowed": _schedule_allows_automation(room_config),
                },
            }
        )

    energy_settings = dashboard_config.get("energy", {})
    realtime_power_snapshot = (
        _build_entity_snapshot(hass, energy_settings.get("realtime_power_entity"))
        if energy_settings.get("realtime_power_entity")
        else None
    )
    daily_energy_snapshot = (
        _build_entity_snapshot(hass, energy_settings.get("daily_energy_entity"))
        if energy_settings.get("daily_energy_entity")
        else None
    )
    monthly_energy_snapshot = (
        _build_entity_snapshot(hass, energy_settings.get("monthly_energy_entity"))
        if energy_settings.get("monthly_energy_entity")
        else None
    )

    realtime_power_kw = _convert_power_to_kw(
        realtime_power_snapshot.get("numeric_value") if realtime_power_snapshot else None,
        realtime_power_snapshot.get("unit_of_measurement") if realtime_power_snapshot else "",
    )
    daily_energy_kwh = _convert_energy_to_kwh(
        daily_energy_snapshot.get("numeric_value") if daily_energy_snapshot else None,
        daily_energy_snapshot.get("unit_of_measurement") if daily_energy_snapshot else "",
    )
    monthly_energy_kwh = _convert_energy_to_kwh(
        monthly_energy_snapshot.get("numeric_value") if monthly_energy_snapshot else None,
        monthly_energy_snapshot.get("unit_of_measurement") if monthly_energy_snapshot else "",
    )
    price_per_kwh = _safe_non_negative_float(energy_settings.get("price_per_kwh"), 0.0)

    return {
        "rooms": rooms,
        "groups": sorted(room_groups.values(), key=lambda item: str(item.get("display_name") or "")),
        "logs": await async_get_recent_room_logs(hass, limit=30),
        "energy": {
            "settings": dashboard_config.get("energy", {}),
            "realtime_power": realtime_power_snapshot,
            "daily_energy": daily_energy_snapshot,
            "monthly_energy": monthly_energy_snapshot,
            "realtime_power_kw": realtime_power_kw,
            "daily_energy_kwh": daily_energy_kwh,
            "monthly_energy_kwh": monthly_energy_kwh,
            "price_per_kwh": price_per_kwh,
            "daily_cost": round(daily_energy_kwh * price_per_kwh, 2)
            if daily_energy_kwh is not None
            else None,
            "monthly_cost": round(monthly_energy_kwh * price_per_kwh, 2)
            if monthly_energy_kwh is not None
            else None,
        },
        "server_time": dt_util.now().isoformat(),
    }


async def async_get_entity_candidates(hass: HomeAssistant) -> dict[str, Any]:
    """Return supported entities for mapping selection."""
    climate_entities: list[dict[str, Any]] = []
    light_entities: list[dict[str, Any]] = []
    fan_entities: list[dict[str, Any]] = []
    switch_entities: list[dict[str, Any]] = []
    sensor_entities: list[dict[str, Any]] = []
    binary_sensor_entities: list[dict[str, Any]] = []
    device_tracker_entities: list[dict[str, Any]] = []

    for state in hass.states.async_all():
        entity_id = state.entity_id
        domain = entity_id.split(".", 1)[0]
        item = {
            "entity_id": entity_id,
            "friendly_name": state.name,
            "entity_name": _clean_entity_display_name(hass, entity_id, state.name),
            "state": state.state,
            "attributes": dict(state.attributes),
        }
        if domain == "climate":
            climate_entities.append(item)
        elif domain == "light":
            light_entities.append(item)
        elif domain == "fan":
            fan_entities.append(item)
        elif domain == "switch":
            switch_entities.append(item)
        elif domain == "sensor":
            sensor_entities.append(item)
        elif domain == "binary_sensor":
            binary_sensor_entities.append(item)
        elif domain == "device_tracker":
            device_tracker_entities.append(item)

    def _sort_key(item: dict[str, Any]) -> tuple[str, str]:
        return (str(item.get("friendly_name") or ""), str(item.get("entity_id") or ""))

    climate_entities.sort(key=_sort_key)
    light_entities.sort(key=_sort_key)
    fan_entities.sort(key=_sort_key)
    switch_entities.sort(key=_sort_key)
    sensor_entities.sort(key=_sort_key)
    binary_sensor_entities.sort(key=_sort_key)
    device_tracker_entities.sort(key=_sort_key)

    return {
        "climate": climate_entities,
        "light": light_entities,
        "fan": fan_entities,
        "switch": switch_entities,
        "sensor": sensor_entities,
        "binary_sensor": binary_sensor_entities,
        "device_tracker": device_tracker_entities,
    }


async def _async_turn_on_entity(hass: HomeAssistant, entity_id: str) -> None:
    """Turn on one entity using the most compatible service."""
    domain = entity_id.split(".", 1)[0]
    if domain == "climate" and hass.services.has_service("climate", "set_hvac_mode"):
        state = hass.states.get(entity_id)
        preferred_modes = [
            "cool",
            "heat",
            "auto",
            "heat_cool",
            "fan_only",
            "dry",
        ]
        hvac_modes = []
        current_mode = ""
        if state is not None:
            hvac_modes = list(state.attributes.get("hvac_modes", []) or [])
            current_mode = str(state.state or "").strip().lower()
        target_mode = current_mode if current_mode and current_mode not in {"off", "unavailable", "unknown"} else ""
        if not target_mode:
            for candidate in preferred_modes:
                if candidate in hvac_modes:
                    target_mode = candidate
                    break
        if target_mode:
            await hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": entity_id, "hvac_mode": target_mode},
                blocking=True,
            )
            return
    if hass.services.has_service(domain, "turn_on"):
        await hass.services.async_call(domain, "turn_on", {"entity_id": entity_id}, blocking=True)
    else:
        await hass.services.async_call("homeassistant", "turn_on", {"entity_id": entity_id}, blocking=True)


async def _async_turn_off_entity(hass: HomeAssistant, entity_id: str) -> None:
    """Turn off one entity using the most compatible service."""
    domain = entity_id.split(".", 1)[0]
    if domain == "climate" and hass.services.has_service("climate", "set_hvac_mode"):
        state = hass.states.get(entity_id)
        hvac_modes = list((state.attributes.get("hvac_modes", []) if state is not None else []) or [])
        if "off" in hvac_modes:
            await hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": entity_id, "hvac_mode": "off"},
                blocking=True,
            )
            return
    if hass.services.has_service(domain, "turn_off"):
        await hass.services.async_call(domain, "turn_off", {"entity_id": entity_id}, blocking=True)
    else:
        await hass.services.async_call("homeassistant", "turn_off", {"entity_id": entity_id}, blocking=True)


async def _async_apply_ac_season(
    hass: HomeAssistant,
    room_config: dict[str, Any],
    *,
    source: str,
    entity_id_override: str | None = None,
) -> dict[str, Any]:
    """Apply the selected room mode to the mapped AC entity."""
    entity_id = str(entity_id_override or room_config["entities"]["ac"] or "").strip()
    if not entity_id:
        raise ValueError("未配置空调实体")

    domain = entity_id.split(".", 1)[0]
    selected_season = room_config["modes"]["selected_season"]
    season_config = room_config["modes"][selected_season]
    if not season_config.get("enabled", True):
        raise ValueError(f"{selected_season} 模式未启用")

    if domain == "climate":
        await _async_turn_on_entity(hass, entity_id)
        hvac_mode = str(season_config.get("hvac_mode") or "").strip()
        if hvac_mode and hass.services.has_service("climate", "set_hvac_mode"):
            await hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": entity_id, "hvac_mode": hvac_mode},
                blocking=True,
            )
        temperature = _apply_ac_temperature_limits(
            room_config,
            _safe_float(season_config.get("temperature")),
        )
        if temperature is not None and hass.services.has_service("climate", "set_temperature"):
            await hass.services.async_call(
                "climate",
                "set_temperature",
                {"entity_id": entity_id, "temperature": temperature},
                blocking=True,
            )
        fan_mode = str(season_config.get("fan_mode") or "").strip()
        if fan_mode and hass.services.has_service("climate", "set_fan_mode"):
            await hass.services.async_call(
                "climate",
                "set_fan_mode",
                {"entity_id": entity_id, "fan_mode": fan_mode},
                blocking=True,
            )
    else:
        await _async_turn_on_entity(hass, entity_id)

    mode_label = {
        "summer": "夏季",
        "winter": "冬季",
        "custom": "自定义",
    }.get(selected_season, selected_season)
    return {"entity_ids": [entity_id], "message": f"已应用{mode_label}模式", "source": source}


async def _async_apply_light_preset(
    hass: HomeAssistant,
    room_config: dict[str, Any],
    preset_name: str,
    *,
    entity_ids_override: list[str] | None = None,
) -> dict[str, Any]:
    """Apply a lighting preset."""
    entity_ids = (
        [str(item or "").strip() for item in entity_ids_override or [] if str(item or "").strip()]
        if entity_ids_override is not None
        else _build_light_preset_entities(room_config, preset_name)
    )
    if not entity_ids:
        raise ValueError("当前预设没有可执行的灯光实体")

    if preset_name == "full_off":
        await hass.services.async_call(
            "homeassistant",
            "turn_off",
            {"entity_id": entity_ids},
            blocking=True,
        )
    else:
        await hass.services.async_call(
            "homeassistant",
            "turn_on",
            {"entity_id": entity_ids},
            blocking=True,
        )

    return {"entity_ids": entity_ids, "message": f"已执行灯光预设 {preset_name}"}


async def _async_apply_fresh_air_mode(
    hass: HomeAssistant,
    room_config: dict[str, Any],
    *,
    turn_on: bool,
    preset_mode: str | None = None,
    entity_id_override: str | None = None,
) -> dict[str, Any]:
    """Apply a fresh air action to the mapped entity."""
    entity_id = str(entity_id_override or room_config["entities"]["fresh_air"] or "").strip()
    if not entity_id:
        raise ValueError("未配置新风实体")

    domain = entity_id.split(".", 1)[0]
    if not turn_on:
        await _async_turn_off_entity(hass, entity_id)
        return {"entity_ids": [entity_id], "message": "已关闭新风"}

    await _async_turn_on_entity(hass, entity_id)

    if domain == "fan":
        state = hass.states.get(entity_id)
        preset_modes = []
        if state is not None:
            preset_modes = list(state.attributes.get("preset_modes", []) or [])
        if preset_mode and preset_mode in preset_modes and hass.services.has_service("fan", "set_preset_mode"):
            await hass.services.async_call(
                "fan",
                "set_preset_mode",
                {"entity_id": entity_id, "preset_mode": preset_mode},
                blocking=True,
            )

    return {"entity_ids": [entity_id], "message": "已开启新风"}


async def _async_restore_room_ac_if_needed(
    hass: HomeAssistant,
    room_id: str,
    room_name: str,
) -> None:
    """Restore AC automation after a temporary manual override."""
    if hass.data.get(DOMAIN, {}).get("automation_paused"):
        return

    runtime = _runtime_store(hass)
    room_state = _get_room_state(runtime, room_id)
    room_state["ac_manual_override_until"] = None

    room_record = next((item for item in get_room_records(hass) if item["room_id"] == room_id), None)
    if room_record is None or not room_record.get("occupied"):
        return

    system_config = await async_load_system_config(hass)
    room_config = system_config["rooms"].get(room_id)
    if room_config is None:
        return

    automation = room_config.get("automation", {})
    ac_automation = automation.get("ac", {}) if isinstance(automation, dict) else {}
    if not _safe_bool(automation.get("enabled"), False):
        return
    if not _safe_bool(ac_automation.get("auto_on"), False):
        return
    if not _schedule_allows_automation(room_config):
        _append_runtime_log(
            hass,
            room_id=room_id,
            room_name=room_name,
            level="info",
            source="automation",
            action="ac_manual_restore_skipped",
            message="手动覆盖恢复时间已到，但当前不在工作时段内",
        )
        return

    try:
        result = await _async_apply_ac_season(hass, room_config, source="automation")
        _append_runtime_log(
            hass,
            room_id=room_id,
            room_name=room_name,
            level="info",
            source="automation",
            action="ac_manual_restore",
            message=result["message"],
            entity_ids=result.get("entity_ids", []),
        )
    except Exception as err:
        _append_runtime_log(
            hass,
            room_id=room_id,
            room_name=room_name,
            level="error",
            source="automation",
            action="ac_manual_restore",
            message=f"恢复自动设定失败: {err}",
        )


def _mark_ac_manual_override(
    hass: HomeAssistant,
    room_id: str,
    room_name: str,
    room_config: dict[str, Any],
    *,
    source: str = "manual",
) -> None:
    """Mark manual AC override and optionally schedule restoration."""
    runtime = _runtime_store(hass)
    room_state = _get_room_state(runtime, room_id)
    _cancel_room_pending_prefix(room_state, "ac_")

    ac_automation = room_config.get("automation", {}).get("ac", {})
    if not isinstance(ac_automation, dict):
        room_state["ac_manual_override_until"] = None
        return

    if not _safe_bool(ac_automation.get("manual_override"), True):
        room_state["ac_manual_override_until"] = None
        return

    restore_delay = _safe_int(ac_automation.get("restore_delay_sec"), 1800)
    existing = room_state["pending"].pop("ac_manual_restore", None)
    if existing:
        try:
            existing()
        except Exception:
            pass

    if restore_delay <= 0:
        room_state["ac_manual_override_until"] = None
        return

    room_state["ac_manual_override_until"] = dt_util.utcnow() + timedelta(seconds=restore_delay)

    @callback
    def _restore(_now: Any) -> None:
        room_state["pending"].pop("ac_manual_restore", None)
        hass.async_create_task(_async_restore_room_ac_if_needed(hass, room_id, room_name))

    room_state["pending"]["ac_manual_restore"] = async_call_later(hass, restore_delay, _restore)

    _append_runtime_log(
        hass,
        room_id=room_id,
        room_name=room_name,
        level="info",
        source=source,
        action="ac_manual_override",
        message=f"已启用空调手动覆盖，{restore_delay} 秒后恢复自动设定",
    )


async def async_execute_room_action(
    hass: HomeAssistant,
    room_id: str,
    action: str,
    *,
    source: str = "manual",
    value: Any = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Execute one room-level action."""
    room_records = {item["room_id"]: item for item in get_room_records(hass)}
    room_record = room_records.get(room_id)
    if room_record is None:
        raise ValueError("包厢不存在")

    system_config = await async_load_system_config(hass)
    room_config = system_config["rooms"].get(room_id)
    if room_config is None:
        raise ValueError("包厢配置不存在")

    if source == "subcontrol":
        denied_message = _subcontrol_denied_message(room_config, action, value=value)
        if denied_message:
            _append_runtime_log(
                hass,
                room_id=room_id,
                room_name=room_record["room_name"],
                level="warning",
                source=source,
                action="subcontrol_denied",
                message=f"{action}: {denied_message}",
            )
            raise PermissionError(denied_message)

    automation_config = room_config.get("automation", {}) if isinstance(room_config, dict) else {}
    automation_ac_targets = _filter_automation_target_entity_ids(
        hass,
        [str(room_config["entities"].get("ac") or "").strip()],
        automation_config.get("ac", {}).get("target_include_keywords") if isinstance(automation_config.get("ac"), dict) else [],
        automation_config.get("ac", {}).get("target_exclude_keywords") if isinstance(automation_config.get("ac"), dict) else [],
    )
    automation_light_targets = _filter_automation_target_entity_ids(
        hass,
        room_config["entities"].get("lights", []) or [],
        automation_config.get("light", {}).get("target_include_keywords") if isinstance(automation_config.get("light"), dict) else [],
        automation_config.get("light", {}).get("target_exclude_keywords") if isinstance(automation_config.get("light"), dict) else [],
    )
    automation_fresh_targets = _filter_automation_target_entity_ids(
        hass,
        [str(room_config["entities"].get("fresh_air") or "").strip()],
        automation_config.get("fresh_air", {}).get("target_include_keywords") if isinstance(automation_config.get("fresh_air"), dict) else [],
        automation_config.get("fresh_air", {}).get("target_exclude_keywords") if isinstance(automation_config.get("fresh_air"), dict) else [],
    )

    result: dict[str, Any]
    mark_manual_override = False
    if action == "ac_turn_on":
        entity_id = automation_ac_targets[0] if source == "automation" and automation_ac_targets else room_config["entities"]["ac"]
        if not entity_id:
            raise ValueError("未配置空调实体")
        if source == "subcontrol" and _get_subcontrol_config(room_config).get("enforce_selected_season"):
            result = await _async_apply_ac_season(hass, room_config, source=source)
        else:
            await _async_turn_on_entity(hass, entity_id)
            result = {"entity_ids": [entity_id], "message": "已开启空调"}
        mark_manual_override = source in {"manual", "subcontrol"}
    elif action == "ac_turn_off":
        entity_id = automation_ac_targets[0] if source == "automation" and automation_ac_targets else room_config["entities"]["ac"]
        if not entity_id:
            raise ValueError("未配置空调实体")
        await _async_turn_off_entity(hass, entity_id)
        result = {"entity_ids": [entity_id], "message": "已关闭空调"}
        mark_manual_override = source in {"manual", "subcontrol"}
    elif action == "ac_set_temperature":
        entity_id = room_config["entities"]["ac"]
        if not entity_id or not entity_id.startswith("climate."):
            raise ValueError("当前空调不支持温度设置")
        temperature = _safe_float(value)
        if temperature is None:
            raise ValueError("temperature 无效")
        temperature = _apply_ac_temperature_limits(room_config, temperature)
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": entity_id, "temperature": temperature},
            blocking=True,
        )
        result = {"entity_ids": [entity_id], "message": f"空调温度已设为 {temperature:g}℃"}
        mark_manual_override = source in {"manual", "subcontrol"}
    elif action == "ac_set_hvac_mode":
        entity_id = room_config["entities"]["ac"]
        if not entity_id or not entity_id.startswith("climate."):
            raise ValueError("当前空调不支持模式切换")
        hvac_mode = str(value or "").strip()
        if not hvac_mode:
            raise ValueError("hvac_mode 无效")
        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": entity_id, "hvac_mode": hvac_mode},
            blocking=True,
        )
        result = {"entity_ids": [entity_id], "message": f"空调模式已切换为 {hvac_mode}"}
        mark_manual_override = source in {"manual", "subcontrol"}
    elif action == "ac_set_fan_mode":
        entity_id = room_config["entities"]["ac"]
        if not entity_id or not entity_id.startswith("climate."):
            raise ValueError("当前空调不支持风速切换")
        fan_mode = str(value or "").strip()
        if not fan_mode:
            raise ValueError("fan_mode 无效")
        await hass.services.async_call(
            "climate",
            "set_fan_mode",
            {"entity_id": entity_id, "fan_mode": fan_mode},
            blocking=True,
        )
        result = {"entity_ids": [entity_id], "message": f"空调风速已切换为 {fan_mode}"}
        mark_manual_override = source in {"manual", "subcontrol"}
    elif action == "ac_apply_season":
        season = str(value or "").strip() or room_config["modes"]["selected_season"]
        if season not in {"summer", "winter", "custom"}:
            raise ValueError("season 无效")
        room_config["modes"]["selected_season"] = season
        if persist:
            global_settings = normalize_global_settings(system_config.get("global_settings"))
            global_settings["modes"]["selected_season"] = season
            system_config["global_settings"] = global_settings
            await async_save_system_config(hass, system_config)
            await async_reset_room_control_runtime(hass)
            await async_initialize_room_control_runtime(hass)
        result = await _async_apply_ac_season(
            hass,
            room_config,
            source=source,
            entity_id_override=automation_ac_targets[0] if source == "automation" and automation_ac_targets else None,
        )
    elif action == "light_apply_preset":
        preset_name = str(value or "").strip()
        if preset_name not in {"full_on", "half_on", "full_off"}:
            raise ValueError("preset 无效")
        result = await _async_apply_light_preset(
            hass,
            room_config,
            preset_name,
            entity_ids_override=automation_light_targets if source == "automation" else None,
        )
    elif action == "light_toggle":
        payload = value if isinstance(value, dict) else {}
        entity_id = _safe_entity_id(payload.get("entity_id"))
        if not entity_id or entity_id not in room_config["entities"]["lights"]:
            raise ValueError("灯光实体未绑定到该包厢")
        if _safe_bool(payload.get("turn_on"), False):
            await _async_turn_on_entity(hass, entity_id)
            result = {"entity_ids": [entity_id], "message": "已开启灯光"}
        else:
            await _async_turn_off_entity(hass, entity_id)
            result = {"entity_ids": [entity_id], "message": "已关闭灯光"}
    elif action == "light_set_brightness":
        payload = value if isinstance(value, dict) else {}
        entity_id = _safe_entity_id(payload.get("entity_id"))
        if not entity_id or entity_id not in room_config["entities"]["lights"]:
            raise ValueError("灯光实体未绑定到该包厢")
        if not entity_id.startswith("light."):
            raise ValueError("当前实体不支持亮度设置")
        brightness_pct = _safe_int(payload.get("brightness_pct"), 0)
        if brightness_pct <= 0:
            await _async_turn_off_entity(hass, entity_id)
            result = {"entity_ids": [entity_id], "message": "亮度设为 0，已关闭灯光"}
        else:
            await hass.services.async_call(
                "light",
                "turn_on",
                {"entity_id": entity_id, "brightness_pct": min(100, brightness_pct)},
                blocking=True,
            )
            result = {
                "entity_ids": [entity_id],
                "message": f"灯光亮度已设为 {min(100, brightness_pct)}%",
            }
    elif action == "light_set_color_temperature":
        payload = value if isinstance(value, dict) else {}
        entity_id = _safe_entity_id(payload.get("entity_id"))
        if not entity_id or entity_id not in room_config["entities"]["lights"]:
            raise ValueError("灯光实体未绑定到该包厢")
        if not entity_id.startswith("light."):
            raise ValueError("当前实体不支持色温设置")
        kelvin = _safe_int(payload.get("kelvin"), 0)
        if kelvin <= 0:
            raise ValueError("kelvin 无效")
        service_payload = {"entity_id": entity_id, "brightness_pct": 100}
        last_error = None
        for key, value_payload in (
            ("color_temp_kelvin", kelvin),
            ("kelvin", kelvin),
            ("color_temp", round(1000000 / kelvin)),
        ):
            try:
                await hass.services.async_call(
                    "light",
                    "turn_on",
                    {**service_payload, key: value_payload},
                    blocking=True,
                )
                result = {
                    "entity_ids": [entity_id],
                    "message": f"灯光色温已设为 {kelvin}K",
                }
                break
            except Exception as err:  # noqa: BLE001
                last_error = err
        else:
            raise ValueError(f"当前实体不支持色温设置: {last_error}") from last_error
    elif action == "light_set_color":
        payload = value if isinstance(value, dict) else {}
        entity_id = _safe_entity_id(payload.get("entity_id"))
        if not entity_id or entity_id not in room_config["entities"]["lights"]:
            raise ValueError("灯光实体未绑定到该包厢")
        if not entity_id.startswith("light."):
            raise ValueError("当前实体不支持颜色设置")
        rgb_color = payload.get("rgb_color")
        if not isinstance(rgb_color, (list, tuple)) or len(rgb_color) < 3:
            hex_value = str(payload.get("hex") or "").strip().lstrip("#")
            if len(hex_value) == 6:
                try:
                    rgb_color = [
                        int(hex_value[0:2], 16),
                        int(hex_value[2:4], 16),
                        int(hex_value[4:6], 16),
                    ]
                except ValueError as err:
                    raise ValueError("颜色值无效") from err
            else:
                raise ValueError("rgb_color 无效")
        rgb_color = [max(0, min(255, _safe_int(item, 0))) for item in list(rgb_color)[:3]]
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id, "rgb_color": rgb_color},
            blocking=True,
        )
        result = {
            "entity_ids": [entity_id],
            "message": f"灯光颜色已更新为 RGB({rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]})",
        }
    elif action == "fresh_air_turn_on":
        result = await _async_apply_fresh_air_mode(
            hass,
            room_config,
            turn_on=True,
            preset_mode=room_config["automation"]["fresh_air"].get("fan_mode"),
            entity_id_override=automation_fresh_targets[0] if source == "automation" and automation_fresh_targets else None,
        )
    elif action == "fresh_air_turn_off":
        result = await _async_apply_fresh_air_mode(
            hass,
            room_config,
            turn_on=False,
            entity_id_override=automation_fresh_targets[0] if source == "automation" and automation_fresh_targets else None,
        )
    elif action == "fresh_air_set_mode":
        entity_id = room_config["entities"]["fresh_air"]
        if not entity_id or not entity_id.startswith("fan."):
            raise ValueError("当前新风不支持档位设置")
        preset_mode = str(value or "").strip()
        if not preset_mode:
            raise ValueError("preset_mode 无效")
        await hass.services.async_call(
            "fan",
            "set_preset_mode",
            {"entity_id": entity_id, "preset_mode": preset_mode},
            blocking=True,
        )
        result = {"entity_ids": [entity_id], "message": f"新风档位已切换为 {preset_mode}"}
    elif action == "fresh_air_set_percentage":
        entity_id = room_config["entities"]["fresh_air"]
        if not entity_id or not entity_id.startswith("fan."):
            raise ValueError("当前新风不支持风量设置")
        percentage = _safe_int(value, 0)
        if percentage < 0 or percentage > 100:
            raise ValueError("percentage 无效")
        if not hass.services.has_service("fan", "set_percentage"):
            raise ValueError("当前环境不支持 fan.set_percentage 服务")
        await hass.services.async_call(
            "fan",
            "set_percentage",
            {"entity_id": entity_id, "percentage": percentage},
            blocking=True,
        )
        result = {"entity_ids": [entity_id], "message": f"新风风量已设为 {percentage}%"}
    else:
        raise ValueError(f"不支持的动作: {action}")

    if mark_manual_override:
        _mark_ac_manual_override(
            hass,
            room_id,
            room_record["room_name"],
            room_config,
            source=source,
        )

    _append_runtime_log(
        hass,
        room_id=room_id,
        room_name=room_record["room_name"],
        level="info",
        source=source,
        action=action,
        message=result["message"],
        entity_ids=result.get("entity_ids", []),
    )
    return result


def _schedule_room_action(
    hass: HomeAssistant,
    room_record: dict[str, Any],
    *,
    action: str,
    delay_seconds: int,
    expected_occupied: bool,
    value: Any = None,
    persist: bool = False,
) -> None:
    """Schedule one room action and track its cancel handle."""
    runtime = _runtime_store(hass)
    room_state = _get_room_state(runtime, room_record["room_id"])
    key = f"{action}:{expected_occupied}"

    existing = room_state["pending"].pop(key, None)
    if existing:
        try:
            existing()
        except Exception:
            pass

    @callback
    def _run_action(_now: Any) -> None:
        room_state["pending"].pop(key, None)
        hass.async_create_task(
            _async_run_scheduled_room_action(
                hass,
                room_record["room_id"],
                room_record["room_name"],
                expected_occupied=expected_occupied,
                action=action,
                value=value,
                persist=persist,
            )
        )

    room_state["pending"][key] = async_call_later(hass, delay_seconds, _run_action)


async def _async_run_scheduled_room_action(
    hass: HomeAssistant,
    room_id: str,
    room_name: str,
    *,
    expected_occupied: bool,
    action: str,
    value: Any = None,
    persist: bool = False,
) -> None:
    """Run a previously scheduled room action if occupancy still matches."""
    room_records = {item["room_id"]: item for item in get_room_records(hass)}
    room_record = room_records.get(room_id)
    if room_record is None:
        return

    if room_record["occupied"] != expected_occupied:
        _append_runtime_log(
            hass,
            room_id=room_id,
            room_name=room_name,
            level="info",
            source="automation",
            action=action,
            message="跳过已过期任务，包厢占用状态已变化",
        )
        return

    try:
        await async_execute_room_action(
            hass,
            room_id,
            action,
            source="automation",
            value=value,
            persist=persist,
        )
    except Exception as err:
        _LOGGER.error("执行包厢自动化动作失败 %s %s: %s", room_id, action, err, exc_info=True)
        _append_runtime_log(
            hass,
            room_id=room_id,
            room_name=room_name,
            level="error",
            source="automation",
            action=action,
            message=f"自动化执行失败: {err}",
        )


async def async_process_room_automation(hass: HomeAssistant) -> None:
    """Process occupancy changes and schedule per-room automations."""
    if hass.data.get(DOMAIN, {}).get("automation_paused"):
        return

    runtime = _runtime_store(hass)
    system_config = await async_load_system_config(hass)
    room_records = get_room_records(hass)
    current_room_ids = {item["room_id"] for item in room_records}

    for room_id in list(runtime["rooms"].keys()):
        if room_id not in current_room_ids:
            _cancel_room_pending(runtime["rooms"][room_id])
            runtime["rooms"].pop(room_id, None)

    for room_record in room_records:
        room_state = _get_room_state(runtime, room_record["room_id"])
        current_occupied = room_record["occupied"]
        previous_occupied = room_state.get("occupied")
        if previous_occupied is None:
            room_state["occupied"] = current_occupied
            continue
        if previous_occupied == current_occupied:
            continue

        room_state["occupied"] = current_occupied
        _cancel_room_pending(room_state)
        if not current_occupied:
            room_state["ac_manual_override_until"] = None

        room_config = system_config["rooms"].get(
            room_record["room_id"],
            _default_room_config(room_record["room_id"], room_record["room_name"]),
        )
        automation_config = room_config["automation"]
        schedule_allowed = _schedule_allows_automation(room_config)
        if not automation_config.get("enabled"):
            _append_runtime_log(
                hass,
                room_id=room_record["room_id"],
                room_name=room_record["room_name"],
                level="info",
                source="automation",
                action="occupancy_change",
                message=f"占用状态切换为 {'有人' if current_occupied else '无人'}，但自动化总开关未启用",
            )
            continue

        _append_runtime_log(
            hass,
            room_id=room_record["room_id"],
            room_name=room_record["room_name"],
            level="info",
            source="automation",
            action="occupancy_change",
            message=f"包厢状态切换为 {'有人' if current_occupied else '无人'}",
        )

        if current_occupied:
            if not schedule_allowed:
                _append_runtime_log(
                    hass,
                    room_id=room_record["room_id"],
                    room_name=room_record["room_name"],
                    level="info",
                    source="automation",
                    action="schedule_skip",
                    message="当前不在工作时段内，已跳过自动开启动作",
                )
                continue

            ac_config = automation_config["ac"]
            ac_targets = _filter_automation_target_entity_ids(
                hass,
                [str(room_config["entities"].get("ac") or "").strip()],
                ac_config.get("target_include_keywords"),
                ac_config.get("target_exclude_keywords"),
            )
            manual_override_until = room_state.get("ac_manual_override_until")
            manual_override_active = bool(
                manual_override_until and manual_override_until > dt_util.utcnow()
            )
            season_strategy = str(ac_config.get("season_strategy") or "selected").strip().lower()
            target_mode = season_strategy if season_strategy in {"summer", "winter", "custom"} else room_config["modes"]["selected_season"]
            if (
                ac_targets
                and ac_config.get("enabled")
                and ac_config.get("auto_on")
                and not manual_override_active
            ):
                _schedule_room_action(
                    hass,
                    room_record,
                    action="ac_apply_season",
                    delay_seconds=ac_config.get("on_delay_sec", 0),
                    expected_occupied=True,
                    value=target_mode,
                )
            elif (
                ac_targets
                and ac_config.get("enabled")
                and ac_config.get("auto_on")
                and manual_override_active
            ):
                _append_runtime_log(
                    hass,
                    room_id=room_record["room_id"],
                    room_name=room_record["room_name"],
                    level="info",
                    source="automation",
                    action="ac_manual_override_active",
                    message="空调处于手动覆盖期，已跳过自动开启",
                )

            light_config = automation_config["light"]
            light_targets = _filter_automation_target_entity_ids(
                hass,
                room_config["entities"].get("lights", []) or [],
                light_config.get("target_include_keywords"),
                light_config.get("target_exclude_keywords"),
            )
            if light_targets and light_config.get("enabled") and light_config.get("auto_on"):
                _schedule_room_action(
                    hass,
                    room_record,
                    action="light_apply_preset",
                    delay_seconds=light_config.get("on_delay_sec", 0),
                    expected_occupied=True,
                    value=light_config.get("arrival_preset", "half_on"),
                )

            fresh_air_config = automation_config["fresh_air"]
            fresh_targets = _filter_automation_target_entity_ids(
                hass,
                [str(room_config["entities"].get("fresh_air") or "").strip()],
                fresh_air_config.get("target_include_keywords"),
                fresh_air_config.get("target_exclude_keywords"),
            )
            if fresh_targets and fresh_air_config.get("enabled") and fresh_air_config.get("auto_on"):
                _schedule_room_action(
                    hass,
                    room_record,
                    action="fresh_air_turn_on",
                    delay_seconds=fresh_air_config.get("on_delay_sec", 0),
                    expected_occupied=True,
                )
        else:
            ac_config = automation_config["ac"]
            ac_targets = _filter_automation_target_entity_ids(
                hass,
                [str(room_config["entities"].get("ac") or "").strip()],
                ac_config.get("target_include_keywords"),
                ac_config.get("target_exclude_keywords"),
            )
            if ac_targets and ac_config.get("enabled") and ac_config.get("auto_off"):
                _schedule_room_action(
                    hass,
                    room_record,
                    action="ac_turn_off",
                    delay_seconds=ac_config.get("off_delay_sec", 0),
                    expected_occupied=False,
                )

            light_config = automation_config["light"]
            light_targets = _filter_automation_target_entity_ids(
                hass,
                room_config["entities"].get("lights", []) or [],
                light_config.get("target_include_keywords"),
                light_config.get("target_exclude_keywords"),
            )
            if light_targets and light_config.get("enabled") and light_config.get("auto_off"):
                _schedule_room_action(
                    hass,
                    room_record,
                    action="light_apply_preset",
                    delay_seconds=light_config.get("off_delay_sec", 0),
                    expected_occupied=False,
                    value=light_config.get("departure_preset", "full_off"),
                )

            fresh_air_config = automation_config["fresh_air"]
            fresh_targets = _filter_automation_target_entity_ids(
                hass,
                [str(room_config["entities"].get("fresh_air") or "").strip()],
                fresh_air_config.get("target_include_keywords"),
                fresh_air_config.get("target_exclude_keywords"),
            )
            if fresh_targets and fresh_air_config.get("enabled") and fresh_air_config.get("auto_off"):
                _schedule_room_action(
                    hass,
                    room_record,
                    action="fresh_air_turn_off",
                    delay_seconds=fresh_air_config.get("off_delay_sec", 0),
                    expected_occupied=False,
                )
