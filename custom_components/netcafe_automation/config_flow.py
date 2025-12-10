"""Config flow for 网吧智能自动化 integration."""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    FileSelector,
    FileSelectorConfig,
    BooleanSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    EntitySelector,
    EntitySelectorConfig,
)

from .const import (
    CONF_CSV_CONTENT,
    CONF_ENABLE_AUTOMATION,
    CONF_TEMPERATURE_ENTITY,
    CONF_WEATHER_ENTITY,
    CSV_TEMPLATE,
    DOMAIN,
    FIELD_ENTITY_ID,
    FIELD_IP_ADDRESS,
    FIELD_ROOM_NAME,
)

_LOGGER = logging.getLogger(__name__)


def _detect_encoding(content_bytes: bytes) -> str:
    """Detect the encoding of CSV content."""
    # Try common encodings for Chinese text
    encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']
    
    for encoding in encodings:
        try:
            content_bytes.decode(encoding)
            _LOGGER.debug("Detected encoding: %s", encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Default to utf-8
    _LOGGER.warning("Could not detect encoding, defaulting to utf-8")
    return 'utf-8'


def _validate_csv_content(csv_content: str) -> tuple[bool, str, int]:
    """Validate CSV content format.
    
    Returns:
        Tuple of (is_valid, error_message, room_count)
    """
    if not csv_content:
        return False, "CSV content is empty", 0
    
    try:
        # If content is bytes, convert to string with proper encoding
        if isinstance(csv_content, bytes):
            encoding = _detect_encoding(csv_content)
            csv_content = csv_content.decode(encoding)
            _LOGGER.debug("Decoded CSV with %s encoding", encoding)
        
        # Remove BOM if present
        if csv_content.startswith('\ufeff'):
            csv_content = csv_content[1:]
            _LOGGER.debug("Removed BOM from CSV content")
        
        # Try to detect delimiter (comma or tab)
        delimiter = ','
        first_line = csv_content.split('\n')[0] if '\n' in csv_content else csv_content
        
        # Count delimiters in first line
        comma_count = first_line.count(',')
        tab_count = first_line.count('\t')
        
        if tab_count > comma_count:
            delimiter = '\t'
            _LOGGER.debug("Detected tab delimiter")
        else:
            _LOGGER.debug("Using comma delimiter")
        
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        
        # Check headers
        if not reader.fieldnames:
            return False, "CSV file has no headers", 0
        
        # Strip whitespace from field names
        fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
        _LOGGER.debug("CSV field names: %s", fieldnames)
        
        # v3.0: Simplified format - only room_name and ip_address required
        required_fields = {FIELD_ROOM_NAME, FIELD_IP_ADDRESS}
        missing_fields = required_fields - set(fieldnames)
        
        # Check if first row looks like data instead of headers
        if missing_fields:
            # Check if it looks like the user forgot to include headers
            if len(fieldnames) >= 2:
                _LOGGER.error("First row appears to be data or headers missing. Required: room_name,ip_address")
                return False, "请在第一行添加标题: room_name,ip_address （可选：climate_entity,light_entity,cover_entity）", 0
            
            _LOGGER.error("Missing fields: %s, Found fields: %s", missing_fields, fieldnames)
            return False, f"缺少必需字段: {', '.join(missing_fields)}。新格式只需要: room_name,ip_address", 0
        
        # Re-create reader with cleaned field names
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        reader.fieldnames = fieldnames
        
        # Count valid rows and rooms
        rooms = set()
        row_count = 0
        
        for row in reader:
            # Strip keys and values
            cleaned_row = {k.strip() if k else k: v.strip() if v else v for k, v in row.items()}
            room_name = cleaned_row.get(FIELD_ROOM_NAME, "")
            ip_address = cleaned_row.get(FIELD_IP_ADDRESS, "")
            
            # v3.0: Only room_name and ip_address required
            if room_name and ip_address:
                rooms.add(room_name)
                row_count += 1
        
        if row_count == 0:
            return False, "No valid rows found in CSV", 0
        
        _LOGGER.info("CSV validation successful: %d rooms, %d rows", len(rooms), row_count)
        return True, "", len(rooms)
        
    except Exception as err:
        _LOGGER.error("CSV validation error: %s", err)
        return False, f"CSV parsing error: {str(err)}", 0


class NetcafeAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 网吧智能自动化."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._csv_content: str | None = None
        self._room_count: int = 0
        self._weather_entity: str | None = None
        self._temperature_entity: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - directly to climate sensors."""
        # Skip all CSV input, go directly to climate mode
        return await self.async_step_climate_mode()





    async def async_step_climate_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select climate control sensors (optional)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # 获取可选的传感器配置
            self._weather_entity = user_input.get(CONF_WEATHER_ENTITY, "")
            self._temperature_entity = user_input.get(CONF_TEMPERATURE_ENTITY, "")
            
            # 不需要验证，都是可选的
            return await self.async_step_confirm()

        # 显示选择表单（所有字段都是可选的）
        data_schema = vol.Schema({
            vol.Optional(CONF_WEATHER_ENTITY): EntitySelector(
                EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(CONF_TEMPERATURE_ENTITY): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
        })

        return self.async_show_form(
            step_id="climate_mode",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": """**空调控制传感器（可选）**

**优先级：** 天气 > 温度 > 季节

• **天气实体：** 根据室外温度（≥26°C 冷气，≤16°C 暖气）
• **温度传感器：** 根据室内温度（≥26°C 冷气，≤20°C 暖气）
• **季节传感器：** 系统自动创建，按日期判断（默认）

**提示：** 留空使用默认季节传感器，或配置多个互为备份
                """,
            },
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm the setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            enable_automation = user_input.get(CONF_ENABLE_AUTOMATION, True)
            
            # 构建配置数据
            data = {
                CONF_CSV_CONTENT: self._csv_content,
                CONF_ENABLE_AUTOMATION: enable_automation,
            }
            
            # 添加可选的传感器配置
            if self._weather_entity:
                data[CONF_WEATHER_ENTITY] = self._weather_entity
            if self._temperature_entity:
                data[CONF_TEMPERATURE_ENTITY] = self._temperature_entity
            
            # Create config entry
            return self.async_create_entry(
                title=f"网吧自动化 ({self._room_count} 个包间)",
                data=data,
            )

        # Show confirmation form
        data_schema = vol.Schema({
            vol.Required(CONF_ENABLE_AUTOMATION, default=True): BooleanSelector(),
        })

        return self.async_show_form(
            step_id="confirm",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "room_count": str(self._room_count),
            },
        )

    async def _read_file_content(self, file_id: str) -> str:
        """Read uploaded file content with proper encoding handling.
        
        In HA, FileSelector provides the content directly or as a file path.
        """
        content = file_id
        
        # If it's bytes, decode with encoding detection
        if isinstance(content, bytes):
            encoding = _detect_encoding(content)
            content = content.decode(encoding)
            _LOGGER.debug("File decoded with %s encoding", encoding)
        
        return content

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NetcafeAutomationOptionsFlow:
        """Get the options flow for this handler."""
        return NetcafeAutomationOptionsFlow(config_entry)


class NetcafeAutomationOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for 网吧智能自动化."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._csv_content: str | None = None
        self._room_count: int = 0

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            action = user_input.get("action")
            
            if action == "reload":
                # Reload with existing CSV
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})
            
            elif action == "update_csv":
                return await self.async_step_update_csv()
            
            elif action == "toggle_automation":
                # Toggle automation enable/disable
                new_data = dict(self.config_entry.data)
                new_data[CONF_ENABLE_AUTOMATION] = not new_data.get(CONF_ENABLE_AUTOMATION, True)
                
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                )
                
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        current_automation_status = self.config_entry.data.get(CONF_ENABLE_AUTOMATION, True)
        
        data_schema = vol.Schema({
            vol.Required("action"): vol.In({
                "reload": "重新加载配置",
                "update_csv": "更新 CSV 文件",
                "toggle_automation": f"{'禁用' if current_automation_status else '启用'}自动化",
            }),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_update_csv(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Update CSV content."""
        errors: dict[str, str] = {}

        if user_input is not None:
            csv_content = user_input.get("csv_content", "").strip()
            
            if not csv_content:
                errors["base"] = "no_csv_file"
            else:
                try:
                    is_valid, error_msg, room_count = await self.hass.async_add_executor_job(
                        _validate_csv_content, csv_content
                    )
                    
                    if not is_valid:
                        errors["base"] = "invalid_csv"
                        _LOGGER.error("CSV validation failed: %s", error_msg)
                    else:
                        # Update config entry with new CSV
                        new_data = dict(self.config_entry.data)
                        new_data[CONF_CSV_CONTENT] = csv_content
                        
                        self.hass.config_entries.async_update_entry(
                            self.config_entry,
                            title=f"网吧自动化 ({room_count} 个包间)",
                            data=new_data,
                        )
                        
                        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                        return self.async_create_entry(title="", data={})
                        
                except Exception as err:
                    _LOGGER.error("Error updating CSV: %s", err)
                    errors["base"] = "cannot_read_file"

        data_schema = vol.Schema({
            vol.Optional(
                "csv_content",
                description={"suggested_value": CSV_TEMPLATE}
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                    multiple=False,
                )
            ),
        })

        return self.async_show_form(
            step_id="update_csv",
            data_schema=data_schema,
            errors=errors,
        )

    async def _read_file_content(self, file_id: str) -> str:
        """Read uploaded file content with proper encoding handling."""
        content = file_id
        
        # If it's bytes, decode with encoding detection
        if isinstance(content, bytes):
            encoding = _detect_encoding(content)
            content = content.decode(encoding)
            _LOGGER.debug("File decoded with %s encoding", encoding)
        
        return content
