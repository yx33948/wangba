"""
智慧网吧卡密授权管理

重构后的授权模型：
- 激活时必须在线验证
- 运行时只认服务端签发的离线票据
- 票据绑定单机 machine_id
- 仅在明确的服务端拒绝时才禁用
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import logging
import math
import os
import random
import re
import socket
import ssl
import string
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

MODULE_DIR = os.path.dirname(__file__)
LICENSE_SERVER_CONFIG_FILENAME = "license_server_endpoints.json"
LICENSE_SERVER_PUBLIC_KEY_FILENAME = "license_ticket_public_key.pem"
DEFAULT_API_BASE_URL = "https://baota.yx33948.top/api/"
DEFAULT_API_FALLBACK_BASE_URLS = ["https://121.199.64.33/api/"]
API_TIMEOUT = 15
API_MAX_RETRIES = 3
TICKET_VERSION = 1
PERMANENT_LICENSE_EXPIRE_DATE = datetime(2099, 12, 31, 23, 59, 59)
PERMANENT_LICENSE_DAYS = 9999
NETWORK_COOLDOWN_ON_SERVER_REJECT = 300
NETWORK_COOLDOWN_ON_NETWORK_ERROR = 120
NETWORK_COOLDOWN_MAX = 600
NETWORK_BACKOFF_BASE = 2
MACHINE_ID_PREFIX = "ha-"

SERVER_REJECTION_CODES = {
    "machine_mismatch": "当前机器与卡密绑定机器不一致",
    "activation_limit_reached": "卡密授权次数已用完",
    "license_disabled": "卡密已被禁用",
    "license_revoked": "卡密已被撤销",
    "license_banned": "卡密已被封禁",
    "license_expired": "卡密已过期",
}

LEGACY_REJECTION_KEYWORDS = (
    "不存在",
    "已被撤销",
    "已过期",
    "激活次数已用完",
    "禁用",
    "停用",
    "封禁",
    "失效",
)

_PUBLIC_KEY_CACHE: Dict[str, Any] = {"path": None, "mtime": None, "key": None}


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    text = str(value or "").strip()
    if len(text) % 4:
        text += "=" * (4 - (len(text) % 4))
    return base64.urlsafe_b64decode(text.encode("utf-8"))


def _mask_license_key(value: str) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if len(text) <= 8:
        return text
    return f"{text[:4]}...{text[-8:]}"


def _normalize_base_url(base_url: str) -> str:
    normalized = str(base_url or "").strip()
    if not normalized:
        return ""
    normalized = normalized.rstrip("/")
    if normalized.endswith("/license.php"):
        normalized = normalized[:-12]
    return normalized + "/"


def _mask_secret(value: str, keep_start: int = 4, keep_end: int = 4) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= keep_start + keep_end:
        return "*" * len(text)
    return f"{text[:keep_start]}{'*' * max(4, len(text) - keep_start - keep_end)}{text[-keep_end:]}"


def _first_existing_path(paths: list[str]) -> str:
    for path in paths:
        if path and os.path.exists(path):
            return path
    return ""


def _sha256_file(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _datetime_to_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ticket_payload_fields(ticket: Dict[str, Any]) -> list[str]:
    return [
        str(ticket.get("version") or TICKET_VERSION),
        str(ticket.get("license_key") or "").strip().upper(),
        str(ticket.get("license_type") or ""),
        str(ticket.get("license_status") or ""),
        str(ticket.get("machine_id") or ""),
        str(ticket.get("expire_at") or ""),
        str(ticket.get("issued_at") or ""),
        str(ticket.get("refresh_after") or ""),
        str(ticket.get("ticket_expire_at") or ""),
        str(ticket.get("activation_limit") or 0),
        str(ticket.get("activation_count") or 0),
    ]


def build_license_ticket_payload(ticket: Dict[str, Any]) -> str:
    return "|".join(_ticket_payload_fields(ticket))


def _normalize_error_code(code: Any, message: str = "") -> str:
    text = str(code or "").strip().lower()
    if text:
        return text
    lowered = str(message or "").lower()
    for error_code in SERVER_REJECTION_CODES:
        if error_code in lowered:
            return error_code
    if any(keyword in message for keyword in LEGACY_REJECTION_KEYWORDS):
        return "server_rejected"
    return ""


def _get_license_server_config_paths(config_dir: Optional[str] = None) -> list[str]:
    paths = []
    if config_dir:
        paths.append(os.path.join(config_dir, LICENSE_SERVER_CONFIG_FILENAME))
    env_path = str(os.environ.get("NETCAFE_LICENSE_SERVER_CONFIG", "")).strip()
    if env_path:
        paths.append(env_path)
    paths.append(os.path.join(MODULE_DIR, LICENSE_SERVER_CONFIG_FILENAME))
    return paths


def _get_public_key_paths(config_dir: Optional[str] = None) -> list[str]:
    paths = []
    if config_dir:
        paths.append(os.path.join(config_dir, LICENSE_SERVER_PUBLIC_KEY_FILENAME))
    env_path = str(os.environ.get("NETCAFE_LICENSE_PUBLIC_KEY", "")).strip()
    if env_path:
        paths.append(env_path)
    paths.append(os.path.join(MODULE_DIR, LICENSE_SERVER_PUBLIC_KEY_FILENAME))
    return paths


def load_license_server_settings(config_dir: Optional[str] = None) -> Dict[str, Any]:
    settings: Dict[str, Any] = {
        "api_base_url": DEFAULT_API_BASE_URL,
        "fallback_api_base_urls": list(DEFAULT_API_FALLBACK_BASE_URLS),
        "admin_api_token": "",
    }
    for path in _get_license_server_config_paths(config_dir):
        if not path or not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                continue
            base_url = payload.get("api_base_url") or payload.get("primary_api_base_url")
            fallback_urls = payload.get("fallback_api_base_urls") or payload.get("api_fallback_base_urls")
            admin_token = payload.get("admin_api_token") or ""
            if base_url:
                settings["api_base_url"] = str(base_url)
            if isinstance(fallback_urls, list):
                settings["fallback_api_base_urls"] = [str(item) for item in fallback_urls if str(item).strip()]
            if admin_token:
                settings["admin_api_token"] = str(admin_token).strip()
            break
        except Exception:
            continue
    settings["api_base_url"] = _normalize_base_url(settings["api_base_url"]) or DEFAULT_API_BASE_URL
    settings["fallback_api_base_urls"] = [
        _normalize_base_url(url)
        for url in settings.get("fallback_api_base_urls", [])
        if _normalize_base_url(url)
    ]
    return settings


def _load_public_key(config_dir: Optional[str] = None):
    for path in _get_public_key_paths(config_dir):
        if not path or not os.path.exists(path):
            continue
        try:
            mtime = os.path.getmtime(path)
            if _PUBLIC_KEY_CACHE["path"] == path and _PUBLIC_KEY_CACHE["mtime"] == mtime:
                return _PUBLIC_KEY_CACHE["key"]
            with open(path, "rb") as handle:
                public_key = serialization.load_pem_public_key(handle.read())
            _PUBLIC_KEY_CACHE.update({"path": path, "mtime": mtime, "key": public_key})
            return public_key
        except Exception:
            continue
    raise FileNotFoundError("未找到卡密票据公钥文件")


def verify_server_signature(payload: str, signature: str, config_dir: Optional[str] = None) -> bool:
    try:
        public_key = _load_public_key(config_dir)
        public_key.verify(
            _base64url_decode(signature),
            payload.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except (FileNotFoundError, InvalidSignature, ValueError, TypeError):
        return False


@dataclass
class LicenseTicket:
    key: str
    license_type: str = "date"
    license_status: str = "inactive"
    machine_id: str = ""
    expire_date: Optional[datetime] = None
    issued_at: Optional[datetime] = None
    refresh_after: Optional[datetime] = None
    ticket_expire_at: Optional[datetime] = None
    expire_at_raw: str = ""
    issued_at_raw: str = ""
    refresh_after_raw: str = ""
    ticket_expire_at_raw: str = ""
    activation_limit: int = 1
    activation_count: int = 0
    signature: str = ""
    version: int = TICKET_VERSION
    activation_date: Optional[datetime] = None
    status_code: str = ""
    is_trial: bool = False
    is_active: bool = True

    @property
    def is_permanent(self) -> bool:
        return self.license_type == "permanent" or (
            self.expire_date is not None and self.expire_date >= PERMANENT_LICENSE_EXPIRE_DATE
        )

    def to_ticket_dict(self) -> Dict[str, Any]:
        return {
            "license_key": self.key,
            "license_type": self.license_type,
            "license_status": self.license_status,
            "machine_id": self.machine_id,
            "expire_at": self.expire_at_raw or _datetime_to_iso(self.expire_date),
            "issued_at": self.issued_at_raw or _datetime_to_iso(self.issued_at),
            "refresh_after": self.refresh_after_raw or _datetime_to_iso(self.refresh_after),
            "ticket_expire_at": self.ticket_expire_at_raw or _datetime_to_iso(self.ticket_expire_at),
            "activation_limit": self.activation_limit,
            "activation_count": self.activation_count,
            "version": self.version,
            "signature": self.signature,
        }

    @classmethod
    def from_ticket_dict(cls, data: Dict[str, Any]) -> "LicenseTicket":
        key = str(data.get("license_key") or data.get("key") or "").strip().upper()
        expire_at_raw = str(data.get("expire_at") or data.get("expire_date") or "")
        issued_at_raw = str(data.get("issued_at") or "")
        refresh_after_raw = str(data.get("refresh_after") or "")
        ticket_expire_at_raw = str(data.get("ticket_expire_at") or data.get("server_ticket_expire_at") or "")
        expire_date = _parse_datetime(expire_at_raw)
        ticket = cls(
            key=key,
            license_type=str(data.get("license_type") or "date"),
            license_status=str(data.get("license_status") or data.get("status") or "inactive"),
            machine_id=str(data.get("machine_id") or data.get("device_id") or "").strip(),
            expire_date=expire_date,
            issued_at=_parse_datetime(issued_at_raw),
            refresh_after=_parse_datetime(refresh_after_raw),
            ticket_expire_at=_parse_datetime(ticket_expire_at_raw),
            expire_at_raw=expire_at_raw,
            issued_at_raw=issued_at_raw,
            refresh_after_raw=refresh_after_raw,
            ticket_expire_at_raw=ticket_expire_at_raw,
            activation_limit=_safe_int(data.get("activation_limit") or data.get("max_activations"), 1),
            activation_count=_safe_int(data.get("activation_count"), 0),
            signature=str(data.get("signature") or data.get("ticket_signature") or data.get("server_ticket_signature") or ""),
            version=_safe_int(data.get("version") or data.get("ticket_version") or data.get("server_ticket_version"), TICKET_VERSION),
            activation_date=_parse_datetime(data.get("activation_date")) or _parse_datetime(issued_at_raw),
            status_code=str(data.get("status_code") or ""),
            is_trial=key.startswith("TRIAL"),
        )
        ticket.is_active = ticket.license_status not in {"disabled", "revoked", "banned", "expired"}
        return ticket


@dataclass
class RuntimeMeta:
    last_successful_refresh_at: Optional[datetime] = None
    last_refresh_attempt_at: Optional[datetime] = None
    last_error: str = ""
    last_server_reason: str = ""
    cached_at: Optional[datetime] = None
    source: str = ""
    status_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_successful_refresh_at": _datetime_to_iso(self.last_successful_refresh_at),
            "last_refresh_attempt_at": _datetime_to_iso(self.last_refresh_attempt_at),
            "last_error": self.last_error,
            "last_server_reason": self.last_server_reason,
            "cached_at": _datetime_to_iso(self.cached_at),
            "source": self.source,
            "status_code": self.status_code,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeMeta":
        return cls(
            last_successful_refresh_at=_parse_datetime(data.get("last_successful_refresh_at")),
            last_refresh_attempt_at=_parse_datetime(data.get("last_refresh_attempt_at")),
            last_error=str(data.get("last_error") or ""),
            last_server_reason=str(data.get("last_server_reason") or ""),
            cached_at=_parse_datetime(data.get("cached_at")),
            source=str(data.get("source") or ""),
            status_code=str(data.get("status_code") or ""),
        )


class OnlineLicenseVerifier:
    _logger = logging.getLogger("license_manager")
    _request_lock = threading.Lock()
    _network_error_count = 0
    _network_error_cooldown = 0.0

    def __init__(
        self,
        api_url: str = None,
        timeout: int = None,
        fallback_urls: Optional[list[str]] = None,
        admin_api_token: str = "",
    ):
        self.api_url = self._normalize_api_url(api_url or DEFAULT_API_BASE_URL)
        self.timeout = timeout or API_TIMEOUT
        self.max_retries = API_MAX_RETRIES
        self.admin_api_token = str(admin_api_token or "").strip()
        self.fallback_urls = list(fallback_urls or [])
        self.last_error: Optional[str] = None
        self.last_error_code: str = ""
        self._cooldown_until: float = 0.0
        self._api_candidates = self._build_api_candidates()

    @staticmethod
    def _normalize_api_url(base_url: str) -> str:
        normalized = (base_url or "").rstrip("/")
        if normalized.endswith("/license.php"):
            return normalized
        return f"{normalized}/license.php"

    @staticmethod
    def _is_ip_host(hostname: Optional[str]) -> bool:
        if not hostname:
            return False
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False

    def _build_api_candidates(self) -> list[Dict[str, Any]]:
        primary_parsed = urllib.parse.urlparse(self.api_url)
        primary_host = primary_parsed.hostname or ""
        candidates: list[Dict[str, Any]] = []

        def add_candidate(url: str, host_header: Optional[str] = None, skip_hostname_check: bool = False) -> None:
            normalized_url = self._normalize_api_url(url)
            parsed = urllib.parse.urlparse(normalized_url)
            if not parsed.scheme or not parsed.hostname:
                return
            candidate = {"url": normalized_url, "host_header": host_header, "skip_hostname_check": skip_hostname_check}
            if candidate not in candidates:
                candidates.append(candidate)

        add_candidate(self.api_url)
        for fallback_url in self.fallback_urls:
            fallback_host = urllib.parse.urlparse(fallback_url).hostname
            host_header = primary_host if self._is_ip_host(fallback_host) and primary_host else None
            add_candidate(fallback_url, host_header=host_header, skip_hostname_check=bool(host_header))
        return candidates

    @classmethod
    def _log(cls, msg: str, level: str = "info") -> None:
        getattr(cls._logger, level)(msg)

    @classmethod
    def _reset_network_error_stats(cls) -> None:
        if cls._network_error_count > 0:
            cls._network_error_count = 0
            cls._network_error_cooldown = 0
            cls._log("网络连接恢复正常，重置错误统计")

    @classmethod
    def _update_network_error_stats(cls) -> None:
        cls._network_error_count += 1
        cooldown = min(
            NETWORK_COOLDOWN_ON_NETWORK_ERROR * (NETWORK_BACKOFF_BASE ** (cls._network_error_count - 1)),
            NETWORK_COOLDOWN_MAX,
        )
        cls._network_error_cooldown = time.time() + cooldown
        cls._log(f"网络错误累计 {cls._network_error_count} 次，冷却 {cooldown} 秒", "warning")

    def _create_ssl_context(self, candidate: Dict[str, Any]) -> Optional[ssl.SSLContext]:
        if not candidate["url"].lower().startswith("https://"):
            return None
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        if candidate.get("skip_hostname_check"):
            context.check_hostname = False
        return context

    def _request_once(self, candidate: Dict[str, Any], payload: Dict[str, Any], action: str) -> tuple[int, str]:
        parsed = urllib.parse.urlparse(candidate["url"])
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NetcafeLicenseVerifier/2.0",
            "Connection": "close",
        }
        if action in {"renew", "create_trial"}:
            if not self.admin_api_token:
                raise PermissionError("未配置管理员 API Token，无法执行该操作")
            headers["X-License-Admin-Token"] = self.admin_api_token
        if candidate.get("host_header"):
            headers["Host"] = candidate["host_header"]
        body = json.dumps(payload).encode("utf-8")
        connection = None
        try:
            if scheme == "https":
                connection = http.client.HTTPSConnection(
                    host,
                    port,
                    timeout=self.timeout,
                    context=self._create_ssl_context(candidate),
                )
            else:
                connection = http.client.HTTPConnection(host, port, timeout=self.timeout)
            connection.request("POST", path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read().decode("utf-8", errors="replace")
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _make_request(self, action: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        is_validation = action in {"verify", "refresh"}
        lock_acquired = False
        if is_validation:
            if time.time() < self._cooldown_until:
                remaining = int(self._cooldown_until - time.time())
                self.last_error = f"冷却中（{remaining}秒）"
                self.last_error_code = "cooldown"
                return None
            if time.time() < self._network_error_cooldown:
                remaining = int(self._network_error_cooldown - time.time())
                self.last_error = f"网络冷却中（{remaining}秒）"
                self.last_error_code = "network_cooldown"
                return None
            lock_acquired = self._request_lock.acquire(blocking=False)
            if not lock_acquired:
                self.last_error = "已有刷新请求在执行中"
                self.last_error_code = "deduped"
                return None

        try:
            payload = {"action": action, **data}
            for attempt in range(1, self.max_retries + 1):
                should_retry = False
                for candidate in self._api_candidates:
                    endpoint = candidate["url"]
                    try:
                        status, response_body = self._request_once(candidate, payload, action)
                    except (OSError, ssl.SSLError, http.client.HTTPException) as err:
                        self.last_error = f"连接失败: {getattr(err, 'reason', err)}"
                        self.last_error_code = "network_error"
                        self._log(
                            f"在线请求连接异常 action={action}, endpoint={endpoint}, attempt={attempt}/{self.max_retries}: {err}",
                            "warning",
                        )
                        should_retry = True
                        continue
                    except PermissionError as err:
                        self.last_error = str(err)
                        self.last_error_code = "permission_error"
                        self._log(
                            f"在线请求缺少管理员鉴权 action={action}, endpoint={endpoint}: {self.last_error}",
                            "warning",
                        )
                        should_retry = False
                        break
                    except Exception as err:
                        self.last_error = f"请求错误: {err}"
                        self.last_error_code = "request_error"
                        self._log(f"在线请求异常 action={action}, endpoint={endpoint}: {self.last_error}", "error")
                        should_retry = False
                        break

                    try:
                        result = json.loads(response_body) if response_body else {}
                    except json.JSONDecodeError as err:
                        self.last_error = f"请求错误: JSON decode failed: {err}"
                        self.last_error_code = "json_error"
                        self._log(f"在线请求异常 action={action}, endpoint={endpoint}: {self.last_error}", "error")
                        should_retry = False
                        break

                    if 200 <= status < 400:
                        self.last_error = None
                        self.last_error_code = ""
                        self._reset_network_error_stats()
                        self._log(f"在线请求成功 action={action}, status={status}, attempt={attempt}, endpoint={endpoint}")
                        return result

                    message = ""
                    if isinstance(result, dict):
                        message = str(result.get("message") or "")
                        error_code = _normalize_error_code(
                            result.get("error_code") or result.get("code"),
                            message,
                        )
                    else:
                        error_code = ""
                    self.last_error = message or f"HTTP {status}"
                    self.last_error_code = error_code or f"http_{status}"
                    self._log(
                        f"在线请求HTTP错误 action={action}, endpoint={endpoint}, code={status}, error={self.last_error}",
                        "warning",
                    )
                    if is_validation and status in (403, 404, 410):
                        self._cooldown_until = time.time() + NETWORK_COOLDOWN_ON_SERVER_REJECT
                    return result if isinstance(result, dict) else None

                if should_retry and attempt < self.max_retries:
                    time.sleep(NETWORK_BACKOFF_BASE ** attempt)
                elif should_retry:
                    self.last_error = f"连接失败（已重试{self.max_retries}次）: {self.last_error}"
                    self.last_error_code = "network_error"
                    self._log(f"在线请求最终失败 action={action}: {self.last_error}", "error")
            if is_validation:
                self._update_network_error_stats()
            return None
        finally:
            if is_validation and lock_acquired:
                self._request_lock.release()

    def is_network_error(self, error: Optional[str] = None) -> bool:
        message = (error or self.last_error or "").lower()
        if not message:
            return False
        keywords = (
            "连接",
            "network",
            "cooldown",
            "timeout",
            "timed out",
            "connection",
            "reset",
            "refused",
            "unreachable",
            "dns",
            "urlopen error",
            "请求失败",
            "无响应",
            "temporarily unavailable",
        )
        return any(keyword in message for keyword in keywords) or self.last_error_code in {
            "network_error",
            "network_cooldown",
        }

    def _extract_ticket_result(self, result: Optional[Dict[str, Any]]) -> tuple[bool, Optional[Dict[str, Any]]]:
        if not isinstance(result, dict):
            if not self.last_error:
                self.last_error = "请求失败，无响应"
            return False, None
        if result.get("success"):
            data = result.get("data") or {}
            if isinstance(data, dict):
                return True, data
            return True, {}
        self.last_error = str(result.get("message") or self.last_error or "服务器返回验证失败")
        self.last_error_code = _normalize_error_code(result.get("error_code"), self.last_error)
        return False, None

    def verify(self, license_key: str, machine_id: str = "") -> tuple[bool, Optional[Dict[str, Any]]]:
        result = self._make_request("verify", {"license_key": license_key, "machine_id": machine_id})
        return self._extract_ticket_result(result)

    def activate(self, license_key: str, machine_id: str = "") -> tuple[bool, Optional[Dict[str, Any]]]:
        payload = {"license_key": license_key, "machine_id": machine_id, "device_id": machine_id}
        result = self._make_request("activate", payload)
        return self._extract_ticket_result(result)

    def refresh(self, license_key: str, machine_id: str = "", ticket_signature: str = "") -> tuple[bool, Optional[Dict[str, Any]]]:
        payload = {
            "license_key": license_key,
            "machine_id": machine_id,
            "ticket_signature": ticket_signature,
        }
        result = self._make_request("refresh", payload)
        return self._extract_ticket_result(result)

    def renew(self, license_key: str, extra_days: int) -> tuple[bool, Optional[Dict[str, Any]]]:
        result = self._make_request("renew", {"license_key": license_key, "extra_days": extra_days})
        if result and result.get("success"):
            return True, result.get("data", {})
        self.last_error = result.get("message", "") if isinstance(result, dict) else self.last_error or "未知错误"
        return False, None

    def create_trial(self, hours: int = 24, notes: str = "") -> tuple[bool, Optional[Dict[str, Any]]]:
        result = self._make_request("create_trial", {"hours": hours, "notes": notes})
        if result and result.get("success"):
            return True, result.get("data", {})
        self.last_error = result.get("message", "") if isinstance(result, dict) else self.last_error or "未知错误"
        return False, None

    def get_info(self, license_key: str) -> Optional[Dict[str, Any]]:
        result = self._make_request("info", {"license_key": license_key})
        if result and result.get("success"):
            return result.get("data")
        return None


class LicenseManager:
    def __init__(self, storage_path: str = None, hass=None):
        if storage_path is None:
            if hass is not None:
                storage_path = hass.config.path(".netcafe_license.json")
            else:
                storage_path = os.path.join(MODULE_DIR, ".netcafe_license.json")
        self.storage_path = storage_path
        self._hass = hass
        self._config_dir = hass.config.config_dir if hass is not None else None
        self.server_settings = load_license_server_settings(self._config_dir)
        self.current_license: Optional[LicenseTicket] = None
        self.runtime_meta = RuntimeMeta()
        self.issued_trial_cache: Dict[str, str] = {}
        self._online_verifier: Optional[OnlineLicenseVerifier] = None
        self._loaded = False
        self._machine_id_cache: Optional[str] = None

    @property
    def online_verifier(self) -> OnlineLicenseVerifier:
        if self._online_verifier is None:
            self.server_settings = load_license_server_settings(self._config_dir)
            self._online_verifier = OnlineLicenseVerifier(
                api_url=self.server_settings.get("api_base_url"),
                fallback_urls=self.server_settings.get("fallback_api_base_urls") or [],
                admin_api_token=self.server_settings.get("admin_api_token", ""),
            )
        return self._online_verifier

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load_license()
            self._loaded = True

    def _parse_datetime_value(self, value: Any) -> Optional[datetime]:
        return _parse_datetime(value)

    def _prune_issued_trial_cache(self) -> bool:
        now = datetime.now()
        removed = False
        for key, expire_value in list(self.issued_trial_cache.items()):
            expire_date = self._parse_datetime_value(expire_value)
            if not expire_date or expire_date <= now:
                self.issued_trial_cache.pop(key, None)
                removed = True
        return removed

    def record_issued_trial(self, trial_key: str, expire_date: Any) -> bool:
        normalized_key = str(trial_key or "").strip().upper()
        parsed_expire = self._parse_datetime_value(expire_date)
        if not normalized_key or not parsed_expire:
            return False
        self.issued_trial_cache[normalized_key] = parsed_expire.isoformat()
        self._prune_issued_trial_cache()
        self._save_license()
        return True

    def _get_issued_trial_expire(self, trial_key: str) -> Optional[datetime]:
        normalized_key = str(trial_key or "").strip().upper()
        expire_value = self.issued_trial_cache.get(normalized_key)
        expire_date = self._parse_datetime_value(expire_value)
        if not expire_date or expire_date <= datetime.now():
            if normalized_key in self.issued_trial_cache:
                self.issued_trial_cache.pop(normalized_key, None)
            return None
        return expire_date

    def _validate_license_key(self, key: str) -> tuple[bool, Optional[datetime], str]:
        normalized = str(key or "").strip().upper()
        if not normalized:
            return False, None, "卡密不能为空"
        if not (
            re.fullmatch(r"[A-Z0-9]{20}-\d{8}", normalized)
            or re.fullmatch(r"TRIAL[A-Z0-9]{17}-\d{8}", normalized)
            or re.fullmatch(r"TRIAL[A-Z0-9]{17}", normalized)
        ):
            return False, None, "卡密格式不正确"
        expire = self._decode_key_expire(normalized)
        return True, expire, ""

    def _decode_key_expire(self, key: str) -> Optional[datetime]:
        if "-" not in key:
            return None
        parts = key.rsplit("-", 1)
        if len(parts) != 2 or len(parts[1]) != 8:
            return None
        try:
            expire_date = datetime.strptime(parts[1], "%Y%m%d")
            return expire_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            return None

    def generate_license_key(self, days: int = 30) -> str:
        random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=20))
        expire_date = (datetime.now() + timedelta(days=max(1, days))).strftime("%Y%m%d")
        return f"{random_part}-{expire_date}"

    def _legacy_ticket_from_payload(self, data: Dict[str, Any]) -> Optional[LicenseTicket]:
        if not isinstance(data, dict):
            return None
        ticket = data.get("license_ticket")
        if isinstance(ticket, dict):
            return LicenseTicket.from_ticket_dict(ticket)
        if data.get("license"):
            license_data = data.get("license")
            if isinstance(license_data, dict):
                key = str(license_data.get("key") or "").strip().upper()
                if key:
                    return LicenseTicket(
                        key=key,
                        license_type="permanent" if _parse_datetime(license_data.get("expire_date")) and _parse_datetime(license_data.get("expire_date")) >= PERMANENT_LICENSE_EXPIRE_DATE else "date",
                        license_status="active" if license_data.get("is_active", True) else "disabled",
                        machine_id=str(license_data.get("device_id") or ""),
                        expire_date=_parse_datetime(license_data.get("expire_date")),
                        activation_date=_parse_datetime(license_data.get("activation_date")),
                        issued_at=_parse_datetime(license_data.get("activation_date")),
                        ticket_expire_at=_parse_datetime(license_data.get("server_ticket_expire_at")),
                        signature=str(license_data.get("server_ticket_signature") or ""),
                        version=_safe_int(license_data.get("server_ticket_version"), TICKET_VERSION),
                        activation_limit=1,
                        activation_count=1 if license_data.get("is_active") else 0,
                        is_trial=key.startswith("TRIAL"),
                        is_active=bool(license_data.get("is_active", True)),
                    )
        return None

    def _load_license(self) -> None:
        self.current_license = None
        self.runtime_meta = RuntimeMeta()
        self.issued_trial_cache = {}
        if not os.path.exists(self.storage_path):
            self._loaded = True
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                self.issued_trial_cache = payload.get("issued_trial_cache", {}) or {}
                self.runtime_meta = RuntimeMeta.from_dict(payload.get("runtime_meta", {}) or {})
                self.current_license = self._legacy_ticket_from_payload(payload)
                self._prune_issued_trial_cache()
                if self.current_license:
                    self.current_license.is_active = self.current_license.license_status not in {
                        "disabled",
                        "revoked",
                        "banned",
                        "expired",
                    }
        except Exception as err:
            logging.getLogger(__name__).warning("加载卡密失败: %s", err)
        self._loaded = True

    def _save_license(self) -> None:
        try:
            self._prune_issued_trial_cache()
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            payload = {
                "license_ticket": self.current_license.to_ticket_dict() if self.current_license else None,
                "runtime_meta": self.runtime_meta.to_dict(),
                "issued_trial_cache": self.issued_trial_cache,
                "last_check": datetime.now().isoformat(),
            }
            with open(self.storage_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            self._loaded = True
        except Exception as err:
            logging.getLogger(__name__).warning("保存卡密失败: %s", err)

    def _read_machine_sources(self) -> list[str]:
        values = []
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as handle:
                        text = handle.read().strip()
                    if text:
                        values.append(text)
            except Exception:
                continue
        try:
            values.append(socket.gethostname())
        except Exception:
            pass
        if self._config_dir:
            values.append(self._config_dir)
        if self._hass is not None:
            try:
                values.append(str(self._hass.config.path(".")))
            except Exception:
                pass
        return [item for item in values if item]

    def _compute_default_machine_id(self) -> str:
        if self._machine_id_cache:
            return self._machine_id_cache
        sources = self._read_machine_sources()
        if not sources:
            sources = [MODULE_DIR]
        digest = hashlib.sha256("|".join(sources).encode("utf-8")).hexdigest()[:40]
        self._machine_id_cache = f"{MACHINE_ID_PREFIX}{digest}"
        return self._machine_id_cache

    def get_activation_device_id(self, device_id: str = "") -> str:
        raw = str(device_id or "").strip()
        if raw:
            if len(raw) <= 64:
                return raw
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
            return f"{MACHINE_ID_PREFIX}{digest}"
        if self.current_license and self.current_license.machine_id:
            return self.current_license.machine_id
        return self._compute_default_machine_id()

    def _extract_license_ticket(self, online_data: Optional[Dict[str, Any]], fallback_key: str = "") -> Optional[LicenseTicket]:
        if not isinstance(online_data, dict):
            return None
        ticket_payload = online_data.get("license_ticket")
        if not isinstance(ticket_payload, dict):
            ticket_payload = {
                "license_key": online_data.get("license_key") or fallback_key,
                "license_type": online_data.get("license_type") or ("permanent" if online_data.get("is_permanent") else "date"),
                "license_status": online_data.get("license_status") or online_data.get("status") or ("active" if online_data.get("valid") else "inactive"),
                "machine_id": online_data.get("machine_id") or online_data.get("device_id") or "",
                "expire_at": online_data.get("expire_at") or online_data.get("expire_date"),
                "issued_at": online_data.get("issued_at"),
                "refresh_after": online_data.get("refresh_after"),
                "ticket_expire_at": online_data.get("ticket_expire_at") or online_data.get("server_ticket_expire_at"),
                "activation_limit": online_data.get("activation_limit") or online_data.get("max_activations") or 1,
                "activation_count": online_data.get("activation_count") or 0,
                "version": online_data.get("version") or online_data.get("ticket_version") or online_data.get("server_ticket_version") or TICKET_VERSION,
                "signature": online_data.get("signature") or online_data.get("ticket_signature") or online_data.get("server_ticket_signature") or "",
            }
        ticket = LicenseTicket.from_ticket_dict(ticket_payload)
        if not ticket.key:
            return None
        if not ticket.expire_date and ticket.key.startswith("TRIAL"):
            ticket.expire_date = self._get_issued_trial_expire(ticket.key) or self._decode_key_expire(ticket.key)
        if not ticket.expire_date:
            ticket.expire_date = self._decode_key_expire(ticket.key)
        if not ticket.refresh_after:
            ticket.refresh_after = ticket.ticket_expire_at
        if not ticket.issued_at:
            ticket.issued_at = datetime.now()
        if not ticket.activation_date:
            ticket.activation_date = ticket.issued_at
        ticket.status_code = str(online_data.get("error_code") or "")
        ticket.is_active = ticket.license_status not in {"disabled", "revoked", "banned", "expired"}
        return ticket

    def _set_runtime_state(self, *, error: str = "", status_code: str = "", server_reason: str = "", source: str = "") -> None:
        self.runtime_meta.last_error = error
        self.runtime_meta.status_code = status_code
        self.runtime_meta.last_server_reason = server_reason
        if source:
            self.runtime_meta.source = source

    def _apply_ticket(self, ticket: LicenseTicket, source: str = "") -> None:
        self.current_license = ticket
        self.current_license.is_active = ticket.license_status not in {"disabled", "revoked", "banned", "expired"}
        now = datetime.now()
        self.runtime_meta.cached_at = now
        self.runtime_meta.last_successful_refresh_at = now
        self.runtime_meta.last_refresh_attempt_at = now
        self.runtime_meta.last_error = ""
        self.runtime_meta.last_server_reason = ""
        self.runtime_meta.status_code = "valid_ticket"
        if source:
            self.runtime_meta.source = source
        self._save_license()

    def _is_ticket_signature_valid(self, ticket: Optional[LicenseTicket]) -> bool:
        if not ticket or not ticket.signature:
            return False
        payload = build_license_ticket_payload(ticket.to_ticket_dict())
        is_valid = verify_server_signature(payload, ticket.signature, self._config_dir)
        if not is_valid:
            logging.getLogger("license_manager").warning(
                "票据验签失败 payload=%s signature_prefix=%s key=%s machine_id=%s",
                payload,
                str(ticket.signature or "")[:32],
                _mask_license_key(ticket.key),
                ticket.machine_id or "-",
            )
        return is_valid

    def _is_machine_match(self, ticket: Optional[LicenseTicket]) -> bool:
        if not ticket:
            return False
        expected = self.get_activation_device_id("")
        actual = str(ticket.machine_id or "").strip()
        return actual == "" or actual == expected

    def _is_ticket_business_expired(self, ticket: Optional[LicenseTicket]) -> bool:
        if not ticket:
            return True
        if ticket.is_permanent:
            return False
        if not ticket.expire_date:
            return False
        return datetime.now() >= ticket.expire_date

    def _is_ticket_cache_valid(self, ticket: Optional[LicenseTicket]) -> bool:
        if not ticket or not ticket.ticket_expire_at:
            return False
        return datetime.now() < ticket.ticket_expire_at

    def _needs_refresh(self, ticket: Optional[LicenseTicket]) -> bool:
        if not ticket:
            return False
        if ticket.ticket_expire_at and datetime.now() >= ticket.ticket_expire_at:
            return True
        return bool(ticket.refresh_after and datetime.now() >= ticket.refresh_after)

    def _map_server_rejection(self, error_code: str, message: str) -> tuple[str, str]:
        normalized = _normalize_error_code(error_code, message)
        if normalized in SERVER_REJECTION_CODES:
            return f"server_rejected_{normalized}", SERVER_REJECTION_CODES[normalized]
        if normalized == "server_rejected":
            return "server_rejected", message or "服务端拒绝当前卡密"
        return normalized or "", message or "服务端拒绝当前卡密"

    def _refresh_ticket(self, reason_source: str = "refresh") -> bool:
        if not self.current_license:
            return False
        machine_id = self.get_activation_device_id("")
        self.runtime_meta.last_refresh_attempt_at = datetime.now()
        ok, data = self.online_verifier.refresh(self.current_license.key, machine_id, self.current_license.signature)
        if ok and data:
            ticket = self._extract_license_ticket(data, self.current_license.key)
            if ticket:
                self._apply_ticket(ticket, source=reason_source)
                return True
        if self.online_verifier.is_network_error():
            self._set_runtime_state(
                error=self.online_verifier.last_error or "网络异常",
                status_code="refresh_network_error",
                source=reason_source,
            )
            self._save_license()
            return self._is_ticket_cache_valid(self.current_license)
        status_code, message = self._map_server_rejection(
            self.online_verifier.last_error_code,
            self.online_verifier.last_error or "",
        )
        self._set_runtime_state(error=message, status_code=status_code, server_reason=message, source=reason_source)
        if self.current_license:
            self.current_license.license_status = "disabled"
            self.current_license.is_active = False
            self._save_license()
        return False

    def activate_license(self, key: str, device_id: str = None) -> Dict[str, Any]:
        try:
            self._ensure_loaded()
            key = str(key or "").strip().upper()
            is_format_ok, _, error_msg = self._validate_license_key(key)
            if not is_format_ok:
                return {"success": False, "error": error_msg}
            machine_id = self.get_activation_device_id(device_id or "")
            ok, data = self.online_verifier.activate(key, machine_id)
            if not ok or not data:
                error_detail = self.online_verifier.last_error or "服务器返回验证失败"
                return {"success": False, "error": f"在线验证失败: {error_detail}"}
            ticket = self._extract_license_ticket(data, key)
            if not ticket:
                return {"success": False, "error": "在线验证失败: 服务端未返回有效票据"}
            if not self._is_ticket_signature_valid(ticket):
                return {"success": False, "error": "在线验证失败: 服务端票据签名无效"}
            if ticket.machine_id and ticket.machine_id != machine_id:
                return {"success": False, "error": "在线验证失败: 服务端返回的绑定机器与当前机器不一致"}
            self._apply_ticket(ticket, source="activate")
            days_remaining = self.get_days_remaining()
            return {
                "success": True,
                "expire_date": _datetime_to_iso(ticket.expire_date),
                "days_remaining": days_remaining,
                "online_verified": True,
                "is_trial": ticket.is_trial,
                "is_permanent": ticket.is_permanent,
                "machine_id": ticket.machine_id,
                "ticket_expire_at": _datetime_to_iso(ticket.ticket_expire_at),
            }
        except Exception as err:
            return {"success": False, "error": str(err)}

    def verify_license(self, online_verify: bool = False) -> bool:
        self._ensure_loaded()
        if not self.current_license:
            self._set_runtime_state(error="未激活卡密", status_code="no_license")
            return False
        ticket = self.current_license
        if not self._is_ticket_signature_valid(ticket):
            ticket.is_active = False
            self._set_runtime_state(
                error="本地票据签名无效",
                status_code="invalid_ticket_signature",
                source="cached_bundle",
            )
            self._save_license()
            return False
        if not self._is_machine_match(ticket):
            ticket.is_active = False
            message = SERVER_REJECTION_CODES["machine_mismatch"]
            self._set_runtime_state(error=message, status_code="server_rejected_machine_mismatch", source="cached_bundle")
            self._save_license()
            return False
        if ticket.license_status in {"disabled", "revoked", "banned"}:
            ticket.is_active = False
            _, message = self._map_server_rejection(ticket.license_status, "")
            self._set_runtime_state(error=message, status_code=f"server_rejected_{ticket.license_status}", source="cached_bundle")
            self._save_license()
            return False
        if self._is_ticket_business_expired(ticket):
            ticket.is_active = False
            self._set_runtime_state(error="卡密已过期", status_code="server_rejected_license_expired", source="cached_bundle")
            self._save_license()
            return False

        if self._needs_refresh(ticket):
            refreshed = self._refresh_ticket(reason_source="refresh")
            if refreshed:
                return True
            if self.runtime_meta.status_code == "refresh_network_error":
                return self._is_ticket_cache_valid(ticket)
            return False

        self._set_runtime_state(status_code="valid_ticket", source="cached_bundle")
        ticket.is_active = True
        return True

    def get_days_remaining(self) -> int:
        self._ensure_loaded()
        if not self.current_license:
            return -1
        if self.current_license.is_permanent:
            return PERMANENT_LICENSE_DAYS
        if not self.current_license.expire_date:
            return -1
        delta = self.current_license.expire_date - datetime.now()
        if delta.total_seconds() <= 0:
            return -1
        return max(0, math.ceil(delta.total_seconds() / 86400))

    def get_license_status(self) -> Dict[str, Any]:
        self._ensure_loaded()
        if not self.current_license:
            return {
                "is_valid": False,
                "status_code": "no_license",
                "message": "未激活卡密",
                "days_remaining": 0,
                "expire_date": None,
                "is_expired": True,
                "license_type": None,
                "ticket_expire_at": None,
                "refresh_after": None,
                "machine_bound": False,
                "machine_match": False,
                "activation_limit": 0,
                "activation_count": 0,
                "last_successful_refresh_at": None,
                "last_error": "",
            }

        is_valid = self.verify_license()
        ticket = self.current_license
        days_remaining = self.get_days_remaining()
        is_expired = days_remaining < 0 and not ticket.is_permanent
        status_code = self.runtime_meta.status_code or ("valid_ticket" if is_valid else "inactive")
        last_error = self.runtime_meta.last_error or ""

        if status_code == "valid_ticket":
            if ticket.is_permanent:
                message = "永久卡密有效"
            elif self._needs_refresh(ticket):
                message = "已进入续签窗口，当前离线票据仍有效"
                status_code = "refresh_window_open"
            else:
                message = f"卡密有效，剩余 {days_remaining} 天"
        elif status_code == "refresh_network_error":
            if self._is_ticket_cache_valid(ticket):
                message = "网络异常，继续使用当前离线票据"
            else:
                message = "离线票据已过期，等待恢复联网"
                status_code = "ticket_expired_waiting_refresh"
        elif status_code.startswith("server_rejected_"):
            message = last_error or "服务端已拒绝当前卡密"
        elif status_code == "invalid_ticket_signature":
            message = last_error or "本地票据签名无效"
        elif is_expired:
            message = "卡密已过期"
        else:
            message = last_error or "卡密当前不可用"

        hours_remaining = 0.0
        if ticket.expire_date and not ticket.is_permanent:
            hours_remaining = max(0.0, round((ticket.expire_date - datetime.now()).total_seconds() / 3600, 1))

        return {
            "is_valid": is_valid,
            "status_code": status_code,
            "message": message,
            "days_remaining": days_remaining,
            "hours_remaining": hours_remaining,
            "expire_date": _datetime_to_iso(ticket.expire_date),
            "license_expire_at": _datetime_to_iso(ticket.expire_date),
            "is_expired": is_expired,
            "is_expiring_soon": (not ticket.is_permanent) and 0 <= days_remaining <= 7,
            "activation_date": _datetime_to_iso(ticket.activation_date),
            "key": ticket.key[-8:] + "****" if ticket.key else None,
            "online_verified": status_code == "valid_ticket",
            "is_permanent": ticket.is_permanent,
            "ticket_expire_at": _datetime_to_iso(ticket.ticket_expire_at),
            "server_ticket_expire_at": _datetime_to_iso(ticket.ticket_expire_at),
            "refresh_after": _datetime_to_iso(ticket.refresh_after),
            "has_server_ticket": self._is_ticket_cache_valid(ticket),
            "last_error": last_error,
            "network_error": status_code == "refresh_network_error",
            "license_type": ticket.license_type,
            "machine_bound": bool(ticket.machine_id),
            "machine_match": self._is_machine_match(ticket),
            "activation_limit": ticket.activation_limit,
            "activation_count": ticket.activation_count,
            "last_successful_refresh_at": _datetime_to_iso(self.runtime_meta.last_successful_refresh_at),
        }

    def get_diagnostics_snapshot(self) -> Dict[str, Any]:
        self._ensure_loaded()
        status = self.get_license_status()
        ticket = self.current_license
        public_key_path = _first_existing_path(_get_public_key_paths(self._config_dir))
        config_path = _first_existing_path(_get_license_server_config_paths(self._config_dir))
        verifier = self.online_verifier

        ticket_payload = ""
        ticket_signature_valid = False
        ticket_dict: Dict[str, Any] | None = None
        if ticket:
            ticket_dict = ticket.to_ticket_dict()
            ticket_payload = build_license_ticket_payload(ticket_dict)
            ticket_signature_valid = self._is_ticket_signature_valid(ticket)

        return {
            "generated_at": _datetime_to_iso(datetime.now()),
            "storage_path": self.storage_path,
            "config_dir": self._config_dir or "",
            "config_file_path": config_path,
            "public_key_path": public_key_path,
            "public_key_sha256": _sha256_file(public_key_path),
            "machine_id": self.get_activation_device_id(""),
            "server_settings": {
                "api_base_url": self.server_settings.get("api_base_url", ""),
                "fallback_api_base_urls": list(self.server_settings.get("fallback_api_base_urls") or []),
                "admin_api_token_masked": _mask_secret(self.server_settings.get("admin_api_token", "")),
            },
            "online_verifier": {
                "api_url": verifier.api_url,
                "fallback_urls": list(verifier.fallback_urls or []),
                "last_error": verifier.last_error,
                "last_error_code": verifier.last_error_code,
            },
            "license_status": status,
            "runtime_meta": self.runtime_meta.to_dict(),
            "ticket": {
                "present": bool(ticket),
                "key_masked": _mask_license_key(ticket.key if ticket else ""),
                "machine_id": ticket.machine_id if ticket else "",
                "license_type": ticket.license_type if ticket else "",
                "license_status": ticket.license_status if ticket else "",
                "expire_at": _datetime_to_iso(ticket.expire_date) if ticket else None,
                "issued_at": _datetime_to_iso(ticket.issued_at) if ticket else None,
                "refresh_after": _datetime_to_iso(ticket.refresh_after) if ticket else None,
                "ticket_expire_at": _datetime_to_iso(ticket.ticket_expire_at) if ticket else None,
                "activation_limit": ticket.activation_limit if ticket else 0,
                "activation_count": ticket.activation_count if ticket else 0,
                "status_code": ticket.status_code if ticket else "",
                "signature_prefix": str(ticket.signature or "")[:32] if ticket else "",
                "signature_valid": ticket_signature_valid,
                "payload": ticket_payload,
                "payload_sha256": hashlib.sha256(ticket_payload.encode("utf-8")).hexdigest() if ticket_payload else "",
                "raw": ticket_dict,
            },
        }

    def deactivate_license(self) -> bool:
        self._ensure_loaded()
        if self.current_license:
            self.current_license = None
            self.runtime_meta = RuntimeMeta(status_code="inactive")
            self._save_license()
            return True
        return False

    def clear_license(self) -> bool:
        self._ensure_loaded()
        self.current_license = None
        self.runtime_meta = RuntimeMeta()
        try:
            if os.path.exists(self.storage_path):
                os.remove(self.storage_path)
            return True
        except Exception:
            return False


_license_manager: Optional[LicenseManager] = None


def reset_license_manager(clear_persisted: bool = False) -> None:
    global _license_manager
    if clear_persisted and _license_manager:
        _license_manager.clear_license()
    _license_manager = None


def get_license_manager(hass=None, force_new: bool = False) -> LicenseManager:
    global _license_manager
    if force_new or _license_manager is None:
        _license_manager = LicenseManager(hass=hass)
    return _license_manager


def is_license_valid() -> bool:
    return get_license_manager().verify_license()


def get_license_info() -> Dict[str, Any]:
    return get_license_manager().get_license_status()
