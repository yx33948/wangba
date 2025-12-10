"""Room Manager for netcafe automation."""

from __future__ import annotations

import logging
import os
from typing import Any
import yaml

from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.group import DOMAIN as GROUP_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import (
    CONF_TEMPERATURE_ENTITY,
    CONF_WEATHER_ENTITY,
    DEFAULT_DELAY_SECONDS,
    DOMAIN,
    SEASON_SPRING_AUTUMN,
    SEASON_SUMMER,
    SEASON_WINTER,
)

_LOGGER = logging.getLogger(__name__)

# 蓝图路径
BLUEPRINT_PATH = "netcafe_automation/netcafe_room_automation.yaml"


class RoomManager:
    """Manage rooms and their automations."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the room manager."""
        self.hass = hass
        self.entry = entry
        self.rooms: dict[str, dict[str, Any]] = {}
        self._automation_ids: list[str] = []
        self._group_ids: list[str] = []
        self._dnd_switches: list[str] = []

    async def async_setup_rooms(
        self, rooms_data: dict[str, dict[str, Any]], enable_automation: bool
    ) -> None:
        """Set up rooms from parsed data."""
        self.rooms = rooms_data

        for room_name, room_config in rooms_data.items():
            room_slug = slugify(room_name)
            
            # DND switch is optional - only use if provided by user in CSV
            # Users can create input_boolean manually in configuration.yaml if needed
            if not room_config.get("dnd_switch"):
                _LOGGER.info("No DND switch provided for %s, automations will run without DND condition", room_name)
            
            # Create groups for computers
            if room_config.get("computers"):
                computer_group = await self._create_computer_group(
                    room_name, room_slug, room_config["computers"]
                )
                room_config["computer_group"] = computer_group
            
            # Create automations if enabled
            if enable_automation and room_config.get("computer_group"):
                await self._create_room_automations(room_name, room_slug, room_config)
        
        # Reload all automations after writing to file
        if enable_automation:
            await self._reload_automations()



    async def _create_computer_group(
        self, room_name: str, room_slug: str, computers: list[dict]
    ) -> str:
        """Create a group for room computers."""
        group_entity_id = f"group.{room_slug}_computers"
        computer_entity_ids = [c["entity_id"] for c in computers]
        
        # Create group via service call
        await self.hass.services.async_call(
            GROUP_DOMAIN,
            "set",
            {
                "object_id": f"{room_slug}_computers",
                "name": f"{room_name} - 电脑",
                "entities": computer_entity_ids,
                "all": False,  # ANY computer online triggers "home"
            },
            blocking=True,
        )
        
        self._group_ids.append(group_entity_id)
        _LOGGER.info("Created computer group: %s with %d entities", 
                     group_entity_id, len(computer_entity_ids))
        return group_entity_id

    async def _create_room_automations(
        self, room_name: str, room_slug: str, room_config: dict
    ) -> None:
        """Create blueprint-based automation for a room."""
        automation_config = self._build_blueprint_automation(
            room_name, room_slug, room_config
        )
        
        self._automation_ids.append(automation_config["id"])
        
        # 写入automations.yaml
        await self.hass.async_add_executor_job(
            self._write_automation_to_file, automation_config
        )

    def _build_blueprint_automation(
        self, room_name: str, room_slug: str, room_config: dict
    ) -> dict:
        """Build a blueprint-based automation configuration."""
        automation_id = f"{DOMAIN}_{room_slug}"
        
        # 获取电脑实体列表
        computer_entities = [c["entity_id"] for c in room_config.get("computers", [])]
        
        # 获取可选的传感器配置
        weather_entity = self.entry.data.get(CONF_WEATHER_ENTITY, "")
        temperature_entity = self.entry.data.get(CONF_TEMPERATURE_ENTITY, "")
        
        automation_config = {
            "id": automation_id,
            "alias": f"【网吧】{room_name} - 智能自动化",
            "use_blueprint": {
                "path": BLUEPRINT_PATH,
                "input": {
                    # 基础设置
                    "room_name": room_name,
                    "computer_entities": computer_entities,
                    "enable_dnd": bool(room_config.get("dnd_switch")),
                    
                    # 灯光设置
                    "enable_lights": len(room_config.get("lights", [])) > 0,
                    "light_entities": room_config.get("lights", []),
                    "light_brightness": 100,
                    
                    # 空调设置
                    "enable_climate": len(room_config.get("climates", [])) > 0,
                    "climate_entities": room_config.get("climates", []),
                    "season_sensor": "sensor.netcafe_season",
                    "weather_entity": weather_entity,
                    "temperature_entity": temperature_entity,
                    "summer_day_temp": 20,
                    "summer_night_temp": 24,
                    "winter_day_temp": 26,
                    "winter_night_temp": 22,
                    
                    # 窗帘设置
                    "enable_covers": len(room_config.get("covers", [])) > 0,
                    "cover_entities": room_config.get("covers", []),
                    "cover_open_on_entry": True,
                    "cover_close_on_leave": True,
                    
                    # 高级设置
                    "delay_seconds": DEFAULT_DELAY_SECONDS,
                    "custom_conditions": [],
                    "custom_actions_on_entry": [],
                    "custom_actions_on_leave": [],
                }
            }
        }
        
        # 记录配置的传感器信息
        sensors_info = []
        if weather_entity:
            sensors_info.append(f"weather: {weather_entity}")
        if temperature_entity:
            sensors_info.append(f"temperature: {temperature_entity}")
        if not sensors_info:
            sensors_info.append("season: sensor.netcafe_season (default)")
        
        _LOGGER.info("Built blueprint automation for room: %s (sensors: %s)", 
                     room_name, ", ".join(sensors_info))
        return automation_config

    def _write_automation_to_file(self, automation_config: dict) -> None:
        """Write automation configuration to automations.yaml"""
        automations_file = self.hass.config.path("automations.yaml")
        
        # 读取现有自动化
        existing_automations = []
        if os.path.exists(automations_file):
            try:
                with open(automations_file, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if content:
                        existing_automations = content if isinstance(content, list) else [content]
            except Exception as err:
                _LOGGER.error("Error reading automations.yaml: %s", err)
        
        # 移除同ID的旧自动化
        automation_id = automation_config["id"]
        existing_automations = [
            a for a in existing_automations 
            if a.get("id") != automation_id
        ]
        
        # 添加新自动化
        existing_automations.append(automation_config)
        
        # 写入文件
        try:
            with open(automations_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    existing_automations,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
            _LOGGER.info("Successfully wrote automation to automations.yaml: %s", automation_id)
        except Exception as err:
            _LOGGER.error("Error writing to automations.yaml: %s", err)
            raise
    
    async def _reload_automations(self) -> None:
        """Reload automations."""
        try:
            # Reload automations
            await self.hass.services.async_call(
                AUTOMATION_DOMAIN,
                "reload",
                {},
                blocking=True,
            )
            _LOGGER.info("Successfully reloaded automations")
        except Exception as err:
            _LOGGER.error("Error reloading automations: %s", err)

    async def async_reload(self) -> None:
        """Hot reload room configuration from storage without full restart."""
        _LOGGER.info("🔄 Hot reloading room manager for entry: %s", self.entry.title)
        
        try:
            # Load CSV from storage
            from .storage_manager import StorageManager
            from . import _parse_csv_content
            
            storage = StorageManager(self.hass, self.entry.entry_id)
            csv_content = await storage.async_load_csv()
            
            if not csv_content:
                _LOGGER.warning("No CSV content found during reload")
                return
            
            # Parse CSV and update rooms
            rooms_data = await self.hass.async_add_executor_job(
                _parse_csv_content, csv_content
            )
            
            # Update room data
            self.rooms = rooms_data
            _LOGGER.info("✅ Room data updated: %d rooms", len(rooms_data))
            
            # Trigger entity updates
            entity_reg = er.async_get(self.hass)
            
            # Update all entities related to this integration
            for entity_id in entity_reg.entities:
                entity = entity_reg.entities[entity_id]
                if entity.config_entry_id == self.entry.entry_id:
                    # Trigger state update
                    state = self.hass.states.get(entity_id)
                    if state:
                        self.hass.states.async_set(entity_id, state.state, state.attributes)
            
            _LOGGER.info("✅ Hot reload completed successfully")
            
        except Exception as err:
            _LOGGER.error("Failed to hot reload: %s", err, exc_info=True)
            # Fallback to full reload
            _LOGGER.info("Attempting full reload...")
            await self.async_cleanup()
            await self.async_setup_rooms(self.rooms, True)

    async def async_cleanup(self) -> None:
        """Clean up created entities and automations."""
        _LOGGER.info("Cleaning up netcafe_automation entities")
        
        # Note: We don't automatically delete created entities as they may be in use
        # User should manually delete if needed
        self._automation_ids.clear()
        self._group_ids.clear()
