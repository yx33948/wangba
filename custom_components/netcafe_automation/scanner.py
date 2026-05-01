"""IP Device Scanner for netcafe automation."""

from __future__ import annotations

import asyncio
import logging
import platform
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol

from homeassistant.util import dt as dt_util

from .const import (
    OFFLINE_CONFIRM_SECONDS,
    OFFLINE_FAILURE_THRESHOLD,
    PING_CONCURRENCY,
    PING_RETRY_DELAY_SECONDS,
    PING_TIMEOUT_MS_WINDOWS,
    PING_TIMEOUT_S_LINUX,
    PING_WAIT_TIMEOUT,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PROBE_STATE_ONLINE = "online"
PROBE_STATE_SUSPECT = "suspect"
PROBE_STATE_OFFLINE = "offline"
OFFLINE_CONFIRM_WINDOW = timedelta(seconds=OFFLINE_CONFIRM_SECONDS)
IS_WINDOWS = platform.system().lower() == "windows"


@dataclass(slots=True, kw_only=True)
class DeviceData:
    ip_address: str
    consider_home: timedelta
    title: str
    room_name: str = ""
    _reachable: bool = False
    _last_seen: datetime | None = None
    _consecutive_failures: int = 0
    _last_probe_method: str = ""
    _probe_state: str = PROBE_STATE_OFFLINE
    _last_ping_ok_at: datetime | None = None
    _last_retry_failed_at: datetime | None = None


async def _ping_one(ip: str, semaphore: asyncio.Semaphore) -> bool:
    """Ping a single IP address."""
    async with semaphore:
        try:
            if IS_WINDOWS:
                cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_MS_WINDOWS), ip]
            else:
                cmd = ["ping", "-c", "1", "-W", str(PING_TIMEOUT_S_LINUX), ip]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=PING_WAIT_TIMEOUT)
            success = proc.returncode == 0

            if success:
                _LOGGER.debug("Ping OK: %s", ip)
            else:
                _LOGGER.debug("Ping FAIL: %s", ip)

            return success
        except (asyncio.TimeoutError, Exception) as err:
            _LOGGER.debug("Ping timeout/error for %s: %s", ip, err)
            return False


async def pinger(ip_addresses: list[str]) -> set[str]:
    """Ping devices using ICMP and return reachable IPs."""
    if not ip_addresses:
        return set()

    semaphore = asyncio.Semaphore(PING_CONCURRENCY)
    results = await asyncio.gather(
        *(_ping_one(ip, semaphore) for ip in ip_addresses),
        return_exceptions=True,
    )

    reachable = {
        ip
        for ip, result in zip(ip_addresses, results)
        if isinstance(result, bool) and result
    }

    _LOGGER.info(
        "Ping results: %d/%d online - %s",
        len(reachable),
        len(ip_addresses),
        sorted(reachable),
    )
    return reachable


class ScannerException(Exception):
    """Scanner exception."""


class Scanner(Protocol):
    """Scanner placeholder kept for integration wiring compatibility."""


class PingScanner:
    """No-op scanner wrapper for ping-only mode."""


def _should_confirm_offline(
    device: DeviceData, now: datetime, offline_confirm_window: timedelta
) -> bool:
    """Return True when the device has enough negative evidence to go offline."""
    if device._consecutive_failures < OFFLINE_FAILURE_THRESHOLD:
        return False

    if device._last_seen is None:
        return True

    return now - device._last_seen >= offline_confirm_window


def _sync_reachability(device: DeviceData) -> None:
    """Expose only online state as connected."""
    device._reachable = device._probe_state == PROBE_STATE_ONLINE


def _format_age_seconds(now: datetime, value: datetime | None) -> int:
    """Return age in whole seconds for logging."""
    if value is None:
        return 0
    return max(0, int((now - value).total_seconds()))


async def _async_get_offline_confirm_window(hass: HomeAssistant) -> timedelta:
    """Return the offline confirm window."""
    return OFFLINE_CONFIRM_WINDOW


async def async_update_devices(
    hass: HomeAssistant, scanner: Scanner, devices: dict[str, DeviceData]
) -> None:
    """Update reachability for all tracked devices using ping only."""
    del scanner  # Ping-only mode keeps the existing call shape.
    if not devices:
        return

    ip_addresses = [device.ip_address for device in devices.values()]
    offline_confirm_window = await _async_get_offline_confirm_window(hass)

    first_pass_reachable = await pinger(ip_addresses)
    retry_candidates = [ip for ip in ip_addresses if ip not in first_pass_reachable]

    retry_reachable: set[str] = set()
    if retry_candidates:
        await asyncio.sleep(PING_RETRY_DELAY_SECONDS)
        retry_reachable = await pinger(retry_candidates)

    online_any = first_pass_reachable | retry_reachable
    now = dt_util.utcnow()

    _LOGGER.info(
        "Presence probe summary: online=%d/%d first_pass=%d retry=%d unresolved=%d",
        len(online_any),
        len(ip_addresses),
        len(first_pass_reachable),
        len(retry_reachable),
        len(ip_addresses) - len(online_any),
    )

    for device in devices.values():
        previous_state = device._probe_state
        previous_reachable = device._reachable
        ping_ok = device.ip_address in first_pass_reachable
        retry_ok = device.ip_address in retry_reachable

        if ping_ok or retry_ok:
            device._probe_state = PROBE_STATE_ONLINE
            device._consecutive_failures = 0
            device._last_seen = now
            device._last_ping_ok_at = now
            device._last_retry_failed_at = None
            device._last_probe_method = "ping" if ping_ok else "ping_retry"
            _sync_reachability(device)
            if previous_state != PROBE_STATE_ONLINE:
                _LOGGER.info(
                    "Device ONLINE: %s (%s) via %s",
                    device.ip_address,
                    device.title,
                    device._last_probe_method,
                )
            continue

        device._last_probe_method = "miss"
        device._last_retry_failed_at = now
        device._consecutive_failures += 1
        device._probe_state = PROBE_STATE_SUSPECT
        _sync_reachability(device)

        if _should_confirm_offline(device, now, offline_confirm_window):
            device._probe_state = PROBE_STATE_OFFLINE
            _sync_reachability(device)
            if previous_reachable or previous_state != PROBE_STATE_OFFLINE:
                time_since_seen = (
                    (now - device._last_seen).total_seconds()
                    if device._last_seen
                    else 0
                )
                _LOGGER.info(
                    "Device OFFLINE: %s (%s) - last_seen=%ds ago, failures=%d, confirm_window=%ss",
                    device.ip_address,
                    device.title,
                    int(time_since_seen),
                    device._consecutive_failures,
                    int(offline_confirm_window.total_seconds()),
                )
        elif previous_state == PROBE_STATE_ONLINE:
            _LOGGER.debug(
                "Device SUSPECT: %s (%s) failures=%d/%d, last_seen=%ds ago",
                device.ip_address,
                device.title,
                device._consecutive_failures,
                OFFLINE_FAILURE_THRESHOLD,
                _format_age_seconds(now, device._last_seen),
            )
        else:
            _LOGGER.debug(
                "Device still pending offline decision: %s (%s) state=%s failures=%d/%d, last_seen=%ds ago",
                device.ip_address,
                device.title,
                device._probe_state,
                device._consecutive_failures,
                OFFLINE_FAILURE_THRESHOLD,
                _format_age_seconds(now, device._last_seen),
            )


async def async_get_scanner(hass: HomeAssistant) -> Scanner:
    """Return the ping-only scanner placeholder."""
    del hass
    _LOGGER.info("Presence detection mode: ping only")
    return PingScanner()
