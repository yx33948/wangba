"""iPhone Detect Scanner."""

from __future__ import annotations

import asyncio
import logging
import socket
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol, Sequence

from homeassistant.util import dt as dt_util
from pyroute2 import IPRoute

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CMD_IP_NEIGH = "ip -4 neigh show nud reachable"
CMD_ARP = "arp -ne"


@dataclass(slots=True, kw_only=True)
class DeviceData:
    ip_address: str
    consider_home: timedelta
    title: str
    _reachable: bool = False
    _last_seen: datetime | None = None


async def pinger(loop: asyncio.AbstractEventLoop, ip_addresses: list[str]) -> list[str]:
    """Ping devices using ICMP and return list of reachable IPs."""
    reachable = []
    
    # Use real ICMP ping via subprocess
    import platform
    import subprocess
    
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    
    async def ping_one(ip: str) -> bool:
        """Ping a single IP address."""
        try:
            # Use faster timeout for Windows (milliseconds) / Linux (seconds)
            if platform.system().lower() == 'windows':
                # Windows: -w 500 means 500ms timeout
                cmd = ['ping', '-n', '1', '-w', '500', ip]
            else:
                # Linux: -W 1 means 1 second timeout
                cmd = ['ping', '-c', '1', '-W', '1', ip]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await asyncio.wait_for(proc.wait(), timeout=1.5)
            success = proc.returncode == 0
            
            if success:
                _LOGGER.debug(f"✓ Ping OK: {ip}")
            else:
                _LOGGER.debug(f"✗ Ping FAIL: {ip}")
                
            return success
        except (asyncio.TimeoutError, Exception) as e:
            _LOGGER.debug(f"✗ Ping timeout/error for {ip}: {e}")
            return False
    
    # Ping all IPs in parallel (much faster than sequential)
    results = await asyncio.gather(*[ping_one(ip) for ip in ip_addresses], return_exceptions=True)
    
    for ip, result in zip(ip_addresses, results):
        if isinstance(result, bool) and result:
            reachable.append(ip)
    
    _LOGGER.info(f"Ping results: {len(reachable)}/{len(ip_addresses)} online - {reachable}")
    return reachable


async def get_arp_subprocess(cmd: Sequence) -> list[str]:
    """Return list of IPv4 devices reachable by the network."""
    response = []
    if isinstance(cmd, str):
        cmd = cmd.split()

    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, close_fds=False)

        async with asyncio.timeout(2):
            result, _ = await proc.communicate()
        if result:
            response = result.decode().splitlines()
    except Exception as exc:
        _LOGGER.debug("Exception on ARP lookup: %s", exc)

    return response


class ScannerException(Exception):
    """Scanner exception."""


class Scanner(Protocol):
    """Scanner class for getting ARP cache records."""

    async def get_arp_records(self, hass: HomeAssistant) -> list[str]:
        """Return list of IPv4 devices reachable by the network."""
        return []


class ScannerIPRoute:
    """Get ARP cache records using pyroute2."""

    def _get_arp_records(self) -> list[str]:
        """Return list of IPv4 devices reachable by the network."""
        response = []
        try:
            with closing(IPRoute()) as ipr:
                result = ipr.get_neighbours(family=socket.AF_INET, match=lambda x: x["state"] == 2)
            response = [dev["attrs"][0][1] for dev in result]
        except Exception as exc:
            _LOGGER.debug("Exception on ARP lookup: %s", exc)

        return response

    async def get_arp_records(self, hass: HomeAssistant) -> list[str]:
        """Return list of IPv4 devices reachable by the network."""
        response = await hass.async_add_executor_job(self._get_arp_records)
        return response


class ScannerIPNeigh:
    """Get ARP cache records using subprocess."""

    async def get_arp_records(self, hass: HomeAssistant = None) -> list[str]:
        """Return list of IPv4 devices reachable by the network."""
        response = []
        result = await get_arp_subprocess(CMD_IP_NEIGH.split())
        if result:
            response = [row.split()[0] for row in result if row.count(":") == 5]

        return response


class ScannerArp:
    """Get ARP cache records using subprocess."""

    async def get_arp_records(self, hass: HomeAssistant = None) -> list[str]:
        """Return list of IPv4 devices reachable by the network."""
        response = []
        result = await get_arp_subprocess(CMD_ARP.split())
        if result:
            response = [row.split()[0] for row in result if row.count(":") == 5]

        return response


async def async_update_devices(hass: HomeAssistant, scanner: Scanner, devices: dict[str, DeviceData]) -> None:
    """Update reachability for all tracked devices."""
    if not devices:
        return
    
    ip_addresses = [device.ip_address for device in devices.values()]

    # Step 1: Ping devices (primary and most reliable method)
    ping_reachable = await pinger(hass.loop, ip_addresses)

    # Step 2: Get devices found in ARP (fallback method)
    arp_reachable = set()
    try:
        arp_records = await scanner.get_arp_records(hass)
        if arp_records:
            arp_reachable = set(ip_addresses).intersection(arp_records)
            if arp_reachable:
                _LOGGER.debug(f"ARP found additional devices: {arp_reachable - set(ping_reachable)}")
    except Exception as e:
        _LOGGER.debug(f"ARP lookup failed (not critical): {e}")

    # Combine results: device is online if found by EITHER ping OR ARP
    reachable_ip = set(ping_reachable) | arp_reachable
    
    if reachable_ip:
        _LOGGER.info(f"🟢 Online devices: {len(reachable_ip)}/{len(ip_addresses)} - {sorted(reachable_ip)}")
    else:
        _LOGGER.warning(f"🔴 No devices detected online! Checked {len(ip_addresses)} IPs: {ip_addresses}")

    # Update reachable devices
    now = dt_util.utcnow()
    for device in devices.values():
        was_reachable = device._reachable
        device._reachable = device.ip_address in reachable_ip
        
        if device._reachable:
            device._last_seen = now
            if not was_reachable:
                _LOGGER.warning(f"✅ Device ONLINE: {device.ip_address} ({device.title})")
        else:
            if was_reachable:
                # Device just went offline, log it
                time_since_seen = (now - device._last_seen).total_seconds() if device._last_seen else 0
                _LOGGER.warning(f"⚠️ Device OFFLINE: {device.ip_address} ({device.title}) - last seen {int(time_since_seen)}s ago")


async def async_get_scanner(hass: HomeAssistant) -> Scanner:
    """Return Scanner to use."""

    if await ScannerIPRoute().get_arp_records(hass):
        return ScannerIPRoute()

    if await ScannerIPNeigh().get_arp_records():
        return ScannerIPNeigh()

    if await ScannerArp().get_arp_records():
        return ScannerArp()

    raise ScannerException("No scanner tool available")
