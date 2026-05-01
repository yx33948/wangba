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
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_CSV_CONTENT,
    CONF_DEVICES,
    CSV_TEMPLATE,
    DOMAIN,
    FIELD_IP_ADDRESS,
    FIELD_ROOM_NAME,
)
from .license_manager import get_license_manager
from .storage_manager import StorageManager
from .weather_service import (
    CONF_WEATHER_AREA_CODE,
    CONF_WEATHER_AREA_ID,
    CONF_WEATHER_AREA_NAME,
    CONF_WEATHER_DOMAIN,
    CONF_WEATHER_LATITUDE,
    CONF_WEATHER_LONGITUDE,
    CONF_WEATHER_SEARCH,
    DEFAULT_WEATHER_DOMAIN,
    NetcafeWeatherClient,
    build_weather_entry_data,
    get_weather_entry_config,
    normalize_weather_domain,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_base_url(url: str | None) -> str:
    """Normalize Home Assistant base URL."""
    return str(url or "").strip().rstrip("/")


def _get_hass_base_url(hass: HomeAssistant) -> str:
    """Get the best available Home Assistant base URL."""
    config = getattr(hass, "config", None)
    api = getattr(config, "api", None)
    candidates = [
        getattr(config, "external_url", None),
        getattr(config, "internal_url", None),
        getattr(api, "base_url", None),
    ]

    for candidate in candidates:
        normalized = _normalize_base_url(candidate)
        if normalized:
            return normalized

    return ""


def _is_entry_loaded(entry: config_entries.ConfigEntry | None) -> bool:
    """Return whether a config entry is already loaded."""
    if entry is None:
        return False

    state_enum = getattr(config_entries, "ConfigEntryState", None)
    loaded_state = getattr(state_enum, "LOADED", None)
    if loaded_state is None:
        return str(getattr(entry, "state", "")).lower().endswith("loaded")
    return getattr(entry, "state", None) == loaded_state


async def _async_refresh_license_runtime(
    hass: HomeAssistant,
    license_mgr: Any,
    config_entry: config_entries.ConfigEntry | None = None,
) -> dict[str, Any]:
    """Refresh cached license state and restore runtime behavior."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data["license_manager"] = license_mgr

    status = await hass.async_add_executor_job(license_mgr.get_license_status)
    domain_data["license_status"] = status

    if status.get("is_valid"):
        if domain_data.get("automation_paused"):
            from . import _resume_automation

            await _resume_automation(hass)

        entries = (
            [config_entry]
            if config_entry is not None
            else hass.config_entries.async_entries(DOMAIN)
        )
        for entry in entries:
            if entry is None or _is_entry_loaded(entry):
                continue
            await hass.config_entries.async_reload(entry.entry_id)
    elif not domain_data.get("automation_paused"):
        from . import _pause_automation

        await _pause_automation(hass)

    return status


async def _async_show_first_setup_notification(hass: HomeAssistant) -> None:
    """Show first-time setup URLs in a persistent notification."""
    if not hass.services.has_service("persistent_notification", "create"):
        return

    base_url = _get_hass_base_url(hass)
    automation_path = "/api/netcafe/automation"
    panel_path = "/api/netcafe/panel"
    automation_url = f"{base_url}{automation_path}" if base_url else automation_path
    panel_url = f"{base_url}{panel_path}" if base_url else panel_path

    message = (
        "首次配置已完成。\n\n"
        f"远程配置地址：{automation_url}\n"
        f"页面地址：{panel_url}\n\n"
        "建议先收藏这两个地址，后续维护会更方便。"
    )

    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "智慧网吧配置地址",
            "message": message,
            "notification_id": "netcafe_automation_first_setup_urls",
        },
        blocking=True,
    )


def _generate_csv_from_device_list(devices: list[dict[str, str]]) -> str:
    """Generate CSV content from device list."""
    if not devices:
        return CSV_TEMPLATE

    output = io.StringIO()
    writer = csv.writer(output)
    # 新顺序：ip_address, room_name
    writer.writerow([FIELD_IP_ADDRESS, FIELD_ROOM_NAME])

    for device in devices:
        writer.writerow([device.get("ip_address", ""), device.get("room_name", "")])

    return output.getvalue()


def _detect_encoding(content_bytes: bytes) -> str:
    """Detect the encoding of CSV content."""
    encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']
    
    for encoding in encodings:
        try:
            content_bytes.decode(encoding)
            _LOGGER.debug("Detected encoding: %s", encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue
    
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
        if isinstance(csv_content, bytes):
            encoding = _detect_encoding(csv_content)
            csv_content = csv_content.decode(encoding)
        
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
        
        if not reader.fieldnames:
            return False, "CSV file has no headers", 0
        
        fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
        
        required_fields = {FIELD_ROOM_NAME, FIELD_IP_ADDRESS}
        missing_fields = required_fields - set(fieldnames)
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}. Required: ip_address,room_name", 0
        
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        reader.fieldnames = fieldnames
        
        rooms = set()
        row_count = 0
        
        for row in reader:
            cleaned_row = {k.strip() if k else k: v.strip() if v else v for k, v in row.items()}
            room_name = cleaned_row.get(FIELD_ROOM_NAME, "")
            ip_address = cleaned_row.get(FIELD_IP_ADDRESS, "")
            
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
        self._pending_csv_content: str | None = None
        self._pending_room_count: int = 0
        self._weather_defaults: dict[str, Any] = {
            CONF_WEATHER_DOMAIN: DEFAULT_WEATHER_DOMAIN,
            CONF_WEATHER_SEARCH: "",
            CONF_WEATHER_AREA_ID: "",
        }
        self._weather_area_options: dict[str, str] = {}
        self._devices: list[dict[str, str]] = []  # 存储设备列表 [{"room_name": "1号包厢", "ip_address": "192.168.1.101"}]

    async def _async_create_initial_entry(
        self,
        room_count: int,
        csv_content: str,
        weather_config: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Create the initial config entry and show setup URLs once."""
        if not self._async_current_entries():
            await _async_show_first_setup_notification(self.hass)

        return self.async_create_entry(
            title=f"智慧网吧 ({room_count} 个包间)",
            data={
                CONF_CSV_CONTENT: csv_content,
                **(weather_config or {}),
            },
        )

    async def _async_prepare_weather_step(
        self, room_count: int, csv_content: str
    ) -> FlowResult:
        """Store setup data, then continue to weather selection."""
        self._pending_room_count = room_count
        self._pending_csv_content = csv_content
        self._weather_defaults = {
            CONF_WEATHER_DOMAIN: DEFAULT_WEATHER_DOMAIN,
            CONF_WEATHER_SEARCH: "",
            CONF_WEATHER_AREA_ID: "",
        }
        self._weather_area_options = {}
        return await self.async_step_weather()

    def _build_weather_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        """Build the weather form schema."""
        selected_area_id = str(defaults.get(CONF_WEATHER_AREA_ID, "")).strip()
        schema: dict[Any, Any] = {
            vol.Required(
                CONF_WEATHER_DOMAIN,
                default=normalize_weather_domain(
                    defaults.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN)
                ),
            ): str,
            vol.Optional(
                CONF_WEATHER_SEARCH,
                default=str(defaults.get(CONF_WEATHER_SEARCH, "")).strip(),
            ): str,
        }

        if self._weather_area_options:
            if selected_area_id not in self._weather_area_options:
                selected_area_id = next(iter(self._weather_area_options))
            schema[
                vol.Optional(CONF_WEATHER_AREA_ID, default=selected_area_id)
            ] = vol.In(self._weather_area_options)

        return vol.Schema(schema)

    async def async_step_weather(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure the weather location."""
        errors: dict[str, str] = {}
        current_input = {**self._weather_defaults}
        if user_input:
            current_input.update(user_input)

        current_input[CONF_WEATHER_DOMAIN] = normalize_weather_domain(
            current_input.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN)
        )
        search = str(current_input.get(CONF_WEATHER_SEARCH, "")).strip()
        area_id = str(current_input.get(CONF_WEATHER_AREA_ID, "")).strip()

        if user_input is not None:
            client = NetcafeWeatherClient(
                self.hass, current_input.get(CONF_WEATHER_DOMAIN)
            )

            if area_id:
                try:
                    station = await client.async_get_station(area_id=area_id)
                except Exception as err:
                    _LOGGER.error("Weather station lookup failed: %s", err)
                    errors["base"] = "weather_lookup_failed"
                else:
                    return await self._async_create_initial_entry(
                        self._pending_room_count,
                        self._pending_csv_content or CSV_TEMPLATE,
                        build_weather_entry_data(
                            current_input[CONF_WEATHER_DOMAIN], station
                        ),
                    )
            elif search:
                try:
                    self._weather_area_options = await client.async_search_locations(
                        search
                    )
                except Exception as err:
                    _LOGGER.error("Weather location search failed: %s", err)
                    errors["base"] = "weather_search_failed"
                else:
                    if not self._weather_area_options:
                        errors["base"] = "weather_location_not_found"
            else:
                errors["base"] = "weather_location_required"

        self._weather_defaults = {
            CONF_WEATHER_DOMAIN: current_input[CONF_WEATHER_DOMAIN],
            CONF_WEATHER_SEARCH: search,
            CONF_WEATHER_AREA_ID: area_id,
        }

        return self.async_show_form(
            step_id="weather",
            data_schema=self._build_weather_schema(self._weather_defaults),
            errors=errors,
            description_placeholders={
                "tip": (
                    "天气服务器域默认使用 weather.com.cn。"
                    "请输入城市或区县搜索，选择地点后再次提交即可完成。"
                ),
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step without requiring license activation."""
        license_mgr = get_license_manager(self.hass)
        license_status = await self.hass.async_add_executor_job(
            license_mgr.get_license_status
        )

        if user_input is not None:
            method = user_input.get("input_method")

            if method == "form":
                return await self.async_step_form()
            elif method == "csv":
                return await self.async_step_csv()

        data_schema = vol.Schema({
            vol.Required("input_method"): vol.In({
                "form": "📝 表单化添加（推荐）",
                "csv": "📋 CSV 批量导入",
            }),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            description_placeholders={
                "license_status": license_status.get("message", "未激活卡密"),
                "expire_date": license_status.get('expire_date', '未知'),
            },
        )

    async def async_step_activate_license(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle license activation."""
        errors: dict[str, str] = {}
        license_mgr = get_license_manager(self.hass)
        license_status = await self.hass.async_add_executor_job(
            license_mgr.get_license_status
        )
        
        if user_input is not None:
            license_key = user_input.get("license_key", "").strip()
            
            if not license_key:
                errors["license_key"] = "卡密不能为空"
            elif len(license_key) < 16:
                errors["license_key"] = "卡密格式不正确"
            else:
                # 尝试激活卡密（必须在 executor 中运行，避免阻塞事件循环）
                normalized_device_id = await self.hass.async_add_executor_job(
                    license_mgr.get_activation_device_id, ""
                )
                result = await self.hass.async_add_executor_job(
                    license_mgr.activate_license, license_key, normalized_device_id
                )
                
                if result.get("success"):
                    _LOGGER.info(f"✓ 卡密激活成功！到期日期：{result.get('expire_date')}")
                    # 激活成功后，返回选择配置方式
                    await _async_refresh_license_runtime(self.hass, license_mgr)
                    return await self.async_step_user()
                else:
                    errors["base"] = result.get("error", "激活失败")
        
        # 生成状态提示
        status_hint = ""
        if license_status.get('is_expired'):
            status_hint = f"⚠️ 卡密已过期 {abs(license_status.get('days_remaining', 0))} 天"
        else:
            status_hint = f"⚠️ {license_status.get('message', '卡密无效')}"
        
        data_schema = vol.Schema({
            vol.Required("license_key", default=""): str,
        })

        return self.async_show_form(
            step_id="activate_license",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "status_hint": status_hint,
                "tip": "请输入您购买的卡密，格式示例：XXXXXXXXXXXXXXXX-20261231",
            },
        )

    async def async_step_form(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle form-based device addition."""
        errors: dict[str, str] = {}

        if user_input is not None:
            room_name = user_input.get("room_name", "").strip()
            ip_address = user_input.get("ip_address", "").strip()
            action = user_input.get("action", "add")

            if action == "add":
                # 添加设备
                if not room_name:
                    errors["room_name"] = "room_name_required"
                elif not ip_address:
                    errors["ip_address"] = "ip_address_required"
                else:
                    # 验证 IP 地址格式
                    import ipaddress
                    try:
                        ipaddress.ip_address(ip_address)
                    except ValueError:
                        errors["ip_address"] = "invalid_ip"

                    if not errors:
                        self._devices.append({
                            "room_name": room_name,
                            "ip_address": ip_address,
                        })
                        _LOGGER.info("Added device: %s - %s", room_name, ip_address)
                        # 清空输入框，准备添加下一个
                        room_name = ""
                        ip_address = ""

                        # 重新显示表单，显示更新的设备列表
                        device_list_html = self._generate_device_list_html()

                        data_schema = vol.Schema({
                            vol.Optional("room_name", default=""): str,
                            vol.Optional("ip_address", default=""): str,
                            vol.Required("action", default="add"): vol.In({
                                "add": "➕ 添加设备",
                                "finish": "✅ 完成配置",
                                "import_csv": "📋 改为 CSV 导入",
                            }),
                        })

                        return self.async_show_form(
                            step_id="form",
                            data_schema=data_schema,
                            errors=errors,
                            description_placeholders={
                                "device_list": device_list_html,
                                "device_count": str(len(self._devices)),
                                "room_count": str(len(set(d["room_name"] for d in self._devices))),
                            },
                        )

            elif action == "finish":
                # 完成配置
                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    # 生成 CSV
                    csv_content = await self.hass.async_add_executor_job(
                        _generate_csv_from_device_list, self._devices
                    )

                    # 统计包厢数量
                    rooms = set(device["room_name"] for device in self._devices)

                    return await self._async_prepare_weather_step(
                        len(rooms), csv_content
                    )

            elif action == "import_csv":
                # 切换到 CSV 导入
                return await self.async_step_csv()

        # 构建设备列表显示（首次显示表单时）
        device_list_html = self._generate_device_list_html()

        data_schema = vol.Schema({
            vol.Optional("room_name", default=""): str,
            vol.Optional("ip_address", default=""): str,
            vol.Required("action", default="add"): vol.In({
                "add": "➕ 添加设备",
                "finish": "✅ 完成配置",
                "import_csv": "📋 改为 CSV 导入",
            }),
        })

        return self.async_show_form(
            step_id="form",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_list": device_list_html,
                "device_count": str(len(self._devices)),
                "room_count": str(len(set(d["room_name"] for d in self._devices))),
            },
        )

    def _generate_device_list_html(self) -> str:
        """Generate HTML representation of device list."""
        if not self._devices:
            return "<i>暂无设备</i>"

        html = "<table style='width: 100%; border-collapse: collapse;'>"
        html += "<tr style='background: #f0f0f0;'><th style='padding: 8px; border: 1px solid #ddd;'>包厢名称</th><th style='padding: 8px; border: 1px solid #ddd;'>IP 地址</th></tr>"

        for i, device in enumerate(self._devices[:20], 1):  # 最多显示 20 个
            html += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>{device['room_name']}</td><td style='padding: 8px; border: 1px solid #ddd;'>{device['ip_address']}</td></tr>"

        if len(self._devices) > 20:
            html += f"<tr><td colspan='2' style='padding: 8px; border: 1px solid #ddd; text-align: center;'>... 还有 {len(self._devices) - 20} 个设备</td></tr>"

        html += "</table>"
        return html

    async def async_step_csv(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle CSV upload."""
        errors: dict[str, str] = {}

        if user_input is not None:
            csv_content = user_input.get(CONF_CSV_CONTENT, "").strip()

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
                        return await self._async_prepare_weather_step(
                            room_count, csv_content
                        )

                except Exception as err:
                    _LOGGER.error("Error processing CSV: %s", err)
                    errors["base"] = "cannot_read_file"

        data_schema = vol.Schema({
            vol.Required(CONF_CSV_CONTENT, default=CSV_TEMPLATE): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="csv",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "tip": "请粘贴包含 room_name 和 ip_address 两列的 CSV 内容",
            },
        )

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
        self._config_entry = config_entry
        self._devices: list[dict[str, str]] = []
        self._current_csv = config_entry.data.get(CONF_CSV_CONTENT, "")
        weather_config = get_weather_entry_config(config_entry)
        self._weather_defaults: dict[str, Any] = {
            CONF_WEATHER_DOMAIN: weather_config.get(
                CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN
            ),
            CONF_WEATHER_SEARCH: "",
            CONF_WEATHER_AREA_ID: weather_config.get(CONF_WEATHER_AREA_ID, ""),
        }
        self._weather_area_options: dict[str, str] = {}

    async def _async_load_current_csv(self) -> None:
        """Load the latest CSV from file storage when available."""
        storage = StorageManager(self.hass, self._config_entry.entry_id)
        stored_csv = await storage.async_load_csv()
        if stored_csv:
            self._current_csv = stored_csv
        else:
            self._current_csv = self._config_entry.data.get(CONF_CSV_CONTENT, "")

    def _build_weather_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        """Build the weather settings schema."""
        selected_area_id = str(defaults.get(CONF_WEATHER_AREA_ID, "")).strip()
        schema: dict[Any, Any] = {
            vol.Required(
                CONF_WEATHER_DOMAIN,
                default=normalize_weather_domain(
                    defaults.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN)
                ),
            ): str,
            vol.Optional(
                CONF_WEATHER_SEARCH,
                default=str(defaults.get(CONF_WEATHER_SEARCH, "")).strip(),
            ): str,
        }

        if self._weather_area_options:
            if selected_area_id not in self._weather_area_options:
                selected_area_id = next(iter(self._weather_area_options))
            schema[
                vol.Optional(CONF_WEATHER_AREA_ID, default=selected_area_id)
            ] = vol.In(self._weather_area_options)

        return vol.Schema(schema)

    async def async_step_weather_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage weather settings."""
        errors: dict[str, str] = {}
        current_input = {**self._weather_defaults}
        if user_input:
            current_input.update(user_input)

        current_input[CONF_WEATHER_DOMAIN] = normalize_weather_domain(
            current_input.get(CONF_WEATHER_DOMAIN, DEFAULT_WEATHER_DOMAIN)
        )
        search = str(current_input.get(CONF_WEATHER_SEARCH, "")).strip()
        area_id = str(current_input.get(CONF_WEATHER_AREA_ID, "")).strip()

        if user_input is not None:
            client = NetcafeWeatherClient(
                self.hass, current_input.get(CONF_WEATHER_DOMAIN)
            )

            if area_id:
                try:
                    station = await client.async_get_station(area_id=area_id)
                except Exception as err:
                    _LOGGER.error("Weather station lookup failed: %s", err)
                    errors["base"] = "weather_lookup_failed"
                else:
                    new_data = dict(self._config_entry.data)
                    new_data.update(
                        build_weather_entry_data(
                            current_input[CONF_WEATHER_DOMAIN], station
                        )
                    )
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data=new_data,
                    )
                    await self.hass.config_entries.async_reload(
                        self._config_entry.entry_id
                    )
                    return self.async_create_entry(title="", data={})
            elif search:
                try:
                    self._weather_area_options = await client.async_search_locations(
                        search
                    )
                except Exception as err:
                    _LOGGER.error("Weather location search failed: %s", err)
                    errors["base"] = "weather_search_failed"
                else:
                    if not self._weather_area_options:
                        errors["base"] = "weather_location_not_found"
            else:
                errors["base"] = "weather_location_required"

        self._weather_defaults = {
            CONF_WEATHER_DOMAIN: current_input[CONF_WEATHER_DOMAIN],
            CONF_WEATHER_SEARCH: search,
            CONF_WEATHER_AREA_ID: area_id,
        }

        return self.async_show_form(
            step_id="weather_settings",
            data_schema=self._build_weather_schema(self._weather_defaults),
            errors=errors,
            description_placeholders={
                "tip": (
                    "天气服务器域默认使用 weather.com.cn。"
                    "请输入城市或区县搜索，选择地点后再次提交即可保存。"
                ),
            },
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        await self._async_load_current_csv()

        # 首先检查卡密状态
        license_mgr = get_license_manager(self.hass)
        license_status = await self.hass.async_add_executor_job(
            license_mgr.get_license_status
        )
        
        errors: dict[str, str] = {}

        if user_input is not None:
            action = user_input.get("action")

            if action == "reload":
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)
                return self.async_create_entry(title="", data={})

            elif action == "add_devices":
                # 加载现有设备
                await self._load_existing_devices()
                return await self.async_step_add_devices()

            elif action == "update_csv":
                return await self.async_step_update_csv()

            elif action == "manage_weather":
                return await self.async_step_weather_settings()

            elif action == "manage_license":
                return await self.async_step_activate_license()

        # 显示当前配置统计
        room_count = 0
        device_count = 0
        weather_config = get_weather_entry_config(self._config_entry)
        weather_location = weather_config.get(CONF_WEATHER_AREA_NAME, "") or "未配置"
        if self._current_csv:
            is_valid, _, rooms = await self.hass.async_add_executor_job(
                _validate_csv_content, self._current_csv
            )
            if is_valid:
                room_count = rooms
                # 解析设备数量
                try:
                    csv_file = io.StringIO(self._current_csv)
                    reader = csv.DictReader(csv_file)
                    device_count = sum(1 for row in reader if row.get(FIELD_ROOM_NAME) and row.get(FIELD_IP_ADDRESS))
                except:
                    pass

        data_schema = vol.Schema({
            vol.Required("action"): vol.In({
                "reload": "🔄 重新加载配置",
                "add_devices": "➕ 添加/删除设备（可视化）",
                "update_csv": "📋 更新 CSV 文件",
                "manage_weather": f"☁️ 天气设置 ({weather_location})",
                "manage_license": f"🔑 卡密管理 ({license_status.get('message', '未知状态')})",
            }),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "room_count": str(room_count),
                "device_count": str(device_count),
                "license_status": license_status.get('message', '未知状态'),
            },
        )
    
    async def async_step_activate_license(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle license activation in options flow."""
        errors: dict[str, str] = {}
        license_mgr = get_license_manager(self.hass)
        license_status = await self.hass.async_add_executor_job(
            license_mgr.get_license_status
        )
        
        if user_input is not None:
            action = user_input.get("action", "")
            
            if action == "deactivate":
                # 停用当前卡密
                await self.hass.async_add_executor_job(license_mgr.deactivate_license)
                await _async_refresh_license_runtime(
                    self.hass,
                    license_mgr,
                    self._config_entry,
                )
                return await self.async_step_init()
            
            license_key = user_input.get("license_key", "").strip()
            
            if not license_key:
                errors["license_key"] = "卡密不能为空"
            elif len(license_key) < 16:
                errors["license_key"] = "卡密格式不正确"
            else:
                # 尝试激活卡密（必须在 executor 中运行，避免阻塞事件循环）
                normalized_device_id = await self.hass.async_add_executor_job(
                    license_mgr.get_activation_device_id, ""
                )
                result = await self.hass.async_add_executor_job(
                    license_mgr.activate_license, license_key, normalized_device_id
                )
                
                if result.get("success"):
                    _LOGGER.info(f"✓ 卡密激活成功！到期日期：{result.get('expire_date')}")
                    # 激活成功后，返回选项界面
                    await _async_refresh_license_runtime(
                        self.hass,
                        license_mgr,
                        self._config_entry,
                    )
                    return await self.async_step_init()
                else:
                    errors["base"] = result.get("error", "激活失败")
        
        # 生成状态提示
        status_hint = ""
        if license_status.get('is_expired'):
            status_hint = f"⚠️ 卡密已过期 {abs(license_status.get('days_remaining', 0))} 天"
        elif not license_status.get('is_valid', False):
            status_hint = f"⚠️ {license_status.get('message', '卡密无效')}"
        else:
            status_hint = f"✅ {license_status.get('message', '卡密有效')}"
        
        data_schema = vol.Schema({
            vol.Optional("license_key", default=""): str,
            vol.Optional("action", default=""): vol.In({
                "": "激活/更新卡密",
                "deactivate": "🔓 停用当前卡密",
            }),
        })

        return self.async_show_form(
            step_id="activate_license",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "status_hint": status_hint,
                "current_key": license_status.get('key', ''),
                "tip": "请输入新卡密激活（格式：XXXXXXXXXXXXXXXX-20261231）",
            },
        )

    async def _load_existing_devices(self):
        """从当前 CSV 加载设备列表."""
        self._devices = []
        await self._async_load_current_csv()
        if not self._current_csv:
            return

        try:
            csv_file = io.StringIO(self._current_csv)
            reader = csv.DictReader(csv_file)

            for row in reader:
                room_name = row.get(FIELD_ROOM_NAME, "").strip()
                ip_address = row.get(FIELD_IP_ADDRESS, "").strip()
                if room_name and ip_address:
                    self._devices.append({
                        "room_name": room_name,
                        "ip_address": ip_address,
                    })
        except Exception as err:
            _LOGGER.error("Error loading existing devices: %s", err)

    async def _async_apply_device_changes(self) -> bool:
        """Persist the current device list and reload the config entry."""
        if not self._devices:
            return False

        csv_content = await self.hass.async_add_executor_job(
            _generate_csv_from_device_list, self._devices
        )
        storage = StorageManager(self.hass, self._config_entry.entry_id)
        if not await storage.async_save_csv(csv_content):
            return False

        new_data = dict(self._config_entry.data)
        new_data[CONF_CSV_CONTENT] = csv_content
        self._current_csv = csv_content

        rooms = set(device["room_name"] for device in self._devices)
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            title=f"智慧网吧 ({len(rooms)} 个包间)",
            data=new_data,
        )
        await self.hass.config_entries.async_reload(self._config_entry.entry_id)
        return True

    def _device_step_placeholders(self) -> dict[str, str]:
        """Build shared description placeholders for the device editor."""
        return {
            "device_list": self._generate_device_list_html(),
            "device_count": str(len(self._devices)),
            "room_count": str(len(set(d["room_name"] for d in self._devices))),
            "tip": "添加或删除后会立即保存并重新加载。删除设备时，请填写与列表完全一致的包厢名称和 IP 地址。",
        }

    async def async_step_add_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or remove devices visually."""
        errors: dict[str, str] = {}

        if user_input is not None:
            room_name = user_input.get("room_name", "").strip()
            ip_address = user_input.get("ip_address", "").strip()
            action = user_input.get("action", "add")

            if action == "add":
                if not room_name:
                    errors["room_name"] = "room_name_required"
                elif not ip_address:
                    errors["ip_address"] = "ip_address_required"
                else:
                    import ipaddress
                    try:
                        ipaddress.ip_address(ip_address)
                    except ValueError:
                        errors["ip_address"] = "invalid_ip"

                    if not errors:
                        exists = any(
                            item["room_name"] == room_name
                            and item["ip_address"] == ip_address
                            for item in self._devices
                        )
                        if not exists:
                            self._devices.append({
                                "room_name": room_name,
                                "ip_address": ip_address,
                            })
                            _LOGGER.info("Added device: %s - %s", room_name, ip_address)

                        if not await self._async_apply_device_changes():
                            errors["base"] = "cannot_read_file"
                        else:
                            return self.async_create_entry(title="", data={})

            elif action == "remove":
                if not room_name:
                    errors["room_name"] = "room_name_required"
                elif not ip_address:
                    errors["ip_address"] = "ip_address_required"
                else:
                    before_count = len(self._devices)
                    self._devices = [
                        item for item in self._devices
                        if not (
                            item["room_name"] == room_name
                            and item["ip_address"] == ip_address
                        )
                    ]
                    if len(self._devices) != before_count:
                        _LOGGER.info("Removed device: %s - %s", room_name, ip_address)
                        if self._devices:
                            if not await self._async_apply_device_changes():
                                errors["base"] = "cannot_read_file"
                            else:
                                return self.async_create_entry(title="", data={})
                        else:
                            errors["base"] = "no_devices"

            elif action == "finish":
                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    if not await self._async_apply_device_changes():
                        errors["base"] = "cannot_read_file"
                    else:
                        return self.async_create_entry(title="", data={})

        data_schema = vol.Schema({
            vol.Optional("room_name", default=""): str,
            vol.Optional("ip_address", default=""): str,
            vol.Required("action", default="add"): vol.In({
                "add": "➕ 添加并立即生效",
                "remove": "➖ 删除并立即生效",
                "finish": "🔄 按当前列表重新加载",
            }),
        })

        return self.async_show_form(
            step_id="add_devices",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=self._device_step_placeholders(),
        )

    def _generate_device_list_html(self) -> str:
        """Generate HTML representation of device list."""
        if not self._devices:
            return "<i>暂无设备</i>"

        html = "<table style='width: 100%; border-collapse: collapse;'>"
        html += "<tr style='background: #f0f0f0;'><th style='padding: 8px; border: 1px solid #ddd;'>包厢名称</th><th style='padding: 8px; border: 1px solid #ddd;'>IP 地址</th></tr>"

        for device in self._devices[:30]:  # 最多显示 30 个
            html += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>{device['room_name']}</td><td style='padding: 8px; border: 1px solid #ddd;'>{device['ip_address']}</td></tr>"

        if len(self._devices) > 30:
            html += f"<tr><td colspan='2' style='padding: 8px; border: 1px solid #ddd; text-align: center;'>... 还有 {len(self._devices) - 30} 个设备</td></tr>"

        html += "</table>"
        return html

    async def async_step_update_csv(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Update CSV content."""
        errors: dict[str, str] = {}

        await self._async_load_current_csv()

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
                        storage = StorageManager(self.hass, self._config_entry.entry_id)
                        if not await storage.async_save_csv(csv_content):
                            errors["base"] = "cannot_read_file"
                            return self.async_show_form(
                                step_id="update_csv",
                                data_schema=vol.Schema({
                                    vol.Required("csv_content", default=csv_content): TextSelector(
                                        TextSelectorConfig(
                                            type=TextSelectorType.TEXT,
                                            multiline=True,
                                        )
                                    ),
                                }),
                                errors=errors,
                            )

                        new_data = dict(self._config_entry.data)
                        new_data[CONF_CSV_CONTENT] = csv_content
                        self._current_csv = csv_content

                        self.hass.config_entries.async_update_entry(
                            self._config_entry,
            title=f"智慧网吧 ({room_count} 个包间)",
                            data=new_data,
                        )

                        await self.hass.config_entries.async_reload(self._config_entry.entry_id)
                        return self.async_create_entry(title="", data={})

                except Exception as err:
                    _LOGGER.error("Error updating CSV: %s", err)
                    errors["base"] = "cannot_read_file"

        current_csv = self._current_csv or CSV_TEMPLATE

        data_schema = vol.Schema({
            vol.Required("csv_content", default=current_csv): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="update_csv",
            data_schema=data_schema,
            errors=errors,
        )
