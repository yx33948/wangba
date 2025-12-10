"""Storage manager for Netcafe Automation - File-based storage."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class StorageManager:
    """Manage file-based storage for netcafe automation."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize storage manager."""
        self.hass = hass
        self.entry_id = entry_id
        
        # 使用 HA 的 config 目录下的自定义子目录
        self.storage_dir = Path(hass.config.path("netcafe_data"))
        self.config_file = self.storage_dir / f"{entry_id}_config.json"
        self.rooms_file = self.storage_dir / f"{entry_id}_rooms.json"
        self.csv_file = self.storage_dir / f"{entry_id}_import.csv"
        
        # 确保目录存在
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure storage directory exists."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            _LOGGER.debug("Storage directory ready: %s", self.storage_dir)
        except Exception as err:
            _LOGGER.error("Failed to create storage directory: %s", err)

    async def async_save_csv(self, csv_content: str) -> bool:
        """Save CSV content to file."""
        try:
            await self.hass.async_add_executor_job(
                self._write_file, self.csv_file, csv_content
            )
            _LOGGER.info("CSV saved to: %s", self.csv_file)
            return True
        except Exception as err:
            _LOGGER.error("Failed to save CSV: %s", err)
            return False

    async def async_load_csv(self) -> str | None:
        """Load CSV content from file."""
        try:
            if not self.csv_file.exists():
                _LOGGER.warning("CSV file not found: %s", self.csv_file)
                return None
            
            content = await self.hass.async_add_executor_job(
                self._read_file, self.csv_file
            )
            _LOGGER.debug("CSV loaded from: %s (%d bytes)", self.csv_file, len(content))
            return content
        except Exception as err:
            _LOGGER.error("Failed to load CSV: %s", err)
            return None

    async def async_save_rooms(self, rooms_data: dict[str, dict[str, Any]]) -> bool:
        """Save parsed rooms data to JSON file."""
        try:
            data = {
                "version": 1,
                "rooms": rooms_data
            }
            await self.hass.async_add_executor_job(
                self._write_json, self.rooms_file, data
            )
            _LOGGER.info("Rooms data saved to: %s", self.rooms_file)
            return True
        except Exception as err:
            _LOGGER.error("Failed to save rooms data: %s", err)
            return False

    async def async_load_rooms(self) -> dict[str, dict[str, Any]] | None:
        """Load parsed rooms data from JSON file."""
        try:
            if not self.rooms_file.exists():
                _LOGGER.info("Rooms file not found, will parse from CSV: %s", self.rooms_file)
                return None
            
            data = await self.hass.async_add_executor_job(
                self._read_json, self.rooms_file
            )
            
            if data and "rooms" in data:
                _LOGGER.debug("Rooms data loaded from: %s", self.rooms_file)
                return data["rooms"]
            
            return None
        except Exception as err:
            _LOGGER.error("Failed to load rooms data: %s", err)
            return None

    async def async_save_config(self, config_data: dict[str, Any]) -> bool:
        """Save configuration to JSON file."""
        try:
            data = {
                "version": 1,
                "config": config_data
            }
            await self.hass.async_add_executor_job(
                self._write_json, self.config_file, data
            )
            _LOGGER.info("Config saved to: %s", self.config_file)
            return True
        except Exception as err:
            _LOGGER.error("Failed to save config: %s", err)
            return False

    async def async_load_config(self) -> dict[str, Any] | None:
        """Load configuration from JSON file."""
        try:
            if not self.config_file.exists():
                _LOGGER.info("Config file not found: %s", self.config_file)
                return None
            
            data = await self.hass.async_add_executor_job(
                self._read_json, self.config_file
            )
            
            if data and "config" in data:
                _LOGGER.debug("Config loaded from: %s", self.config_file)
                return data["config"]
            
            return None
        except Exception as err:
            _LOGGER.error("Failed to load config: %s", err)
            return None

    async def async_delete_all(self) -> bool:
        """Delete all storage files."""
        try:
            for file_path in [self.config_file, self.rooms_file, self.csv_file]:
                if file_path.exists():
                    await self.hass.async_add_executor_job(file_path.unlink)
                    _LOGGER.info("Deleted: %s", file_path)
            return True
        except Exception as err:
            _LOGGER.error("Failed to delete storage files: %s", err)
            return False

    def get_storage_info(self) -> dict[str, Any]:
        """Get storage file information."""
        info = {
            "storage_dir": str(self.storage_dir),
            "files": {}
        }
        
        for name, file_path in [
            ("config", self.config_file),
            ("rooms", self.rooms_file),
            ("csv", self.csv_file)
        ]:
            if file_path.exists():
                size = file_path.stat().st_size
                info["files"][name] = {
                    "path": str(file_path),
                    "size": size,
                    "exists": True
                }
            else:
                info["files"][name] = {
                    "path": str(file_path),
                    "exists": False
                }
        
        return info

    @staticmethod
    def _write_file(file_path: Path, content: str) -> None:
        """Write content to file (sync)."""
        file_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _read_file(file_path: Path) -> str:
        """Read content from file (sync)."""
        return file_path.read_text(encoding="utf-8")

    @staticmethod
    def _write_json(file_path: Path, data: dict[str, Any]) -> None:
        """Write JSON data to file (sync)."""
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    @staticmethod
    def _read_json(file_path: Path) -> dict[str, Any]:
        """Read JSON data from file (sync)."""
        content = file_path.read_text(encoding="utf-8")
        return json.loads(content)
