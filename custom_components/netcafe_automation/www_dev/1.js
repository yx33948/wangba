// ===== 设备图标SVG定义 =====
const DEVICE_ICONS = {
  computer: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
      <line x1="8" y1="21" x2="16" y2="21"></line>
      <line x1="12" y1="17" x2="12" y2="21"></line>
    </svg>
  `,
  light: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M9 18h6"></path>
      <path d="M10 22h4"></path>
      <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1.36.5 2.6 1.5 3.5.76.76 1.23 1.52 1.41 2.5"></path>
      <line x1="12" y1="2" x2="12" y2="4"></line>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
      <line x1="1" y1="12" x2="3" y2="12"></line>
      <line x1="19.78" y1="4.22" x2="18.36" y2="5.64"></line>
      <line x1="21" y1="12" x2="23" y2="12"></line>
    </svg>
  `,
  ac: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="3" width="18" height="10" rx="2" ry="2"></rect>
      <line x1="7" y1="8" x2="17" y2="8"></line>
      <path d="M12 13v3"></path>
      <path d="M8 16l-2 3"></path>
      <path d="M16 16l2 3"></path>
      <path d="M12 16v3"></path>
      <path d="M8 19l-2 3"></path>
      <path d="M16 19l2 3"></path>
    </svg>
  `,
  fresh: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"></path>
    </svg>
  `,
};

function replaceDeviceIcons() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', replaceDeviceIcons);
    return;
  }
  const iconElements = document.querySelectorAll('.suite-room-device-icon');
  iconElements.forEach(icon => {
    const text = icon.textContent.trim();
    let svgIcon = null;
    if (text === '💻') {
      svgIcon = DEVICE_ICONS.computer;
    } else if (text === '💡') {
      svgIcon = DEVICE_ICONS.light;
    } else if (text === '❄' || text === '❄️') {
      svgIcon = DEVICE_ICONS.ac;
    } else if (text === '🌿') {
      svgIcon = DEVICE_ICONS.fresh;
    }
    if (svgIcon) {
      icon.innerHTML = svgIcon;
    }
  });
}

function observeDeviceIcons() {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.addedNodes.length) {
        replaceDeviceIcons();
      }
    });
  });
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

if (typeof window !== 'undefined') {
  replaceDeviceIcons();
  observeDeviceIcons();
  window.replaceDeviceIcons = replaceDeviceIcons;
}

// ===== 页面元数据 =====
const pageMeta = {
  dashboard: {
    title: "首页概览",
    subtitle: "联控状态、包厢环境与关键告警一屏掌握。",
  },
  room: {
    title: "包厢总览",
    subtitle: "按包厢查看占用状态、设备映射和常用联动操作。",
  },
  ac: {
    title: "空调控制",
    subtitle: "紧凑展示多房间空调状态，按运行模式切换色彩和控制动作。",
  },
  light: {
    title: "灯光控制",
    subtitle: "查看各包厢灯光分组、亮度和预设动作，补齐单灯控制样式。",
  },
  fan: {
    title: "新风控制",
    subtitle: "查看新风在线状态、档位，并联动实际 fan 或 switch 实体。",
  },
  settings: {
    title: "配置管理",
    subtitle: "统一维护连接方式、实体映射、季节模式和自动化参数。",
  },
};

const state = {
  overview: null,
  config: null,
  entities: null,
  license: null,
  energyHistory: {
    daily_kwh: null,
    monthly_kwh: null,
    source: "",
  },
  dailySummary: null,
  authError: "",
  historyAuthError: "",
  historyAuthProbe: null,
  reloadError: "",
  isReloading: false,
  refreshTimer: null,
  panelSocket: null,
  panelEventReconnectTimer: null,
  panelEventRefreshTimer: null,
  panelEventRefreshDueAt: 0,
  panelEventsSupported: null,
  panelEventsProbe: null,
  syncMode: "polling",
  realtimeDebug: {
    socketConnectCount: 0,
    socketOpenAtMs: 0,
    socketCloseAtMs: 0,
    socketErrorCount: 0,
    messageCount: 0,
    lastMessageAtMs: 0,
    lastEntityId: "",
    lastDomain: "",
    lastServerEventAtMs: 0,
    lastServerEmitAtMs: 0,
    lastServerBroadcastAtMs: 0,
    lastReceiveLatencyMs: null,
    lastBridgeDelayMs: null,
    lastRenderDurationMs: null,
    lastRefreshDurationMs: null,
    lastRefreshAtMs: 0,
    recentEvents: [],
    actionTraces: [],
  },
  refreshFailureCount: 0,
  lastSuccessfulReloadAt: 0,
  dashboardLogSignature: "",
  dashboardPriceEditorOpen: false,
  dashboardQuickControl: "ac",
  dashboardRoomSort: "occupied",
  pendingRoomActionKeys: new Set(),
  currentRoomId: null,
  currentSettingsSubPage: "basic",
  currentTheme: "light",
  auth: {
    token: "",
    user: null,
    tab: "login",
  },
  connection: {
    apiBase: "",
  },
  pageFilters: {
    room: { include: "", exclude: "" },
    ac: { include: "", exclude: "" },
    light: { include: "", exclude: "" },
    fan: { include: "", exclude: "" },
  },
  settingsDraft: {},
  isSidebarCollapsed: false,
  modalContext: null,
  weather: null,
  weatherConfig: null,
  weatherSearchResults: [],
  brandLogoCatalog: [],
  brandLogoCatalogLoaded: false,
  notificationConfig: null,
  notificationStatus: null,
  notificationPreview: null,
  notificationQr: null,
  notificationQrPollTimer: null,
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatFriendlyDateTime(value, fallbackText = "") {
  if (fallbackText) return fallbackText;
  return formatDateTime(value);
}

function isIgnorableAsyncChannelError(reason) {
  const text = String(
    reason && typeof reason === "object" && "message" in reason
      ? reason.message
      : reason || "",
  ).trim();
  return text.includes("A listener indicated an asynchronous response by returning true")
    && text.includes("message channel closed before a response was received");
}

function formatTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function safeDurationMs(value) {
  if (value == null || value === "" || Number.isNaN(Number(value))) return null;
  return Math.max(0, Math.round(Number(value)));
}

function appendRealtimeDebugEvent(item) {
  const recent = Array.isArray(state.realtimeDebug.recentEvents) ? state.realtimeDebug.recentEvents.slice(-19) : [];
  recent.push(item);
  state.realtimeDebug.recentEvents = recent;
}

function appendRealtimeActionTrace(item) {
  const recent = Array.isArray(state.realtimeDebug.actionTraces) ? state.realtimeDebug.actionTraces.slice(-19) : [];
  recent.push(item);
  state.realtimeDebug.actionTraces = recent;
}

function normalizeActionExpectedState(action, value) {
  if (action === "ac_set_hvac_mode") return String(value || "").trim().toLowerCase();
  if (action === "ac_turn_on") return "on";
  if (action === "ac_turn_off") return "off";
  if (action === "light_toggle") return value && value.turn_on ? "on" : "off";
  if (action === "fresh_air_turn_on") return "on";
  if (action === "fresh_air_turn_off") return "off";
  return "";
}

function eventSatisfiesActionTrace(trace, payload) {
  if (!trace || !payload) return false;
  const entityId = String(payload.entity_id || "");
  const targetIds = Array.isArray(trace.entity_ids) ? trace.entity_ids : [];
  if (!targetIds.includes(entityId)) return false;
  const expected = String(trace.expected_state || "").trim().toLowerCase();
  if (!expected) return true;
  const stateValue = String(payload.state || payload.snapshot && payload.snapshot.state || "").trim().toLowerCase();
  if (trace.action === "ac_turn_on") return stateValue && stateValue !== "off";
  if (trace.action === "ac_turn_off") return stateValue === "off";
  return stateValue === expected;
}

function triggerModeValue(value) {
  return ["sensor", "device_tracker", "hybrid"].includes(value) ? value : "device_tracker";
}

function defaultRoomConfig(roomId = "", roomName = "") {
  return {
    room_id: roomId,
    room_name: roomName,
    entities: {
      ac: "",
      lights: [],
      fresh_air: "",
    },
    lighting_presets: {
      full_on: [],
      half_on: [],
      full_off: [],
    },
    lighting_filters: {
      entity_keywords: [],
      half_on_keywords: [],
    },
    entity_filters: {
      ac_include_keywords: [],
      ac_exclude_keywords: [],
      light_include_keywords: [],
      light_exclude_keywords: [],
      fresh_air_include_keywords: [],
      fresh_air_exclude_keywords: [],
    },
    subcontrol: {
      enabled: false,
      allow_ac_power: true,
      allow_ac_temperature: true,
      allow_ac_mode: true,
      allow_ac_fan_mode: true,
      allow_light_control: true,
      enforce_selected_season: false,
      inherit_temperature_limits: true,
      custom_temperature_limits_enabled: false,
      min_temperature: 16,
      max_temperature: 30,
    },
    modes: {
      selected_season: "summer",
      summer: {
        enabled: true,
        hvac_mode: "cool",
        temperature: 26,
        fan_mode: "auto",
      },
      winter: {
        enabled: true,
        hvac_mode: "heat",
        temperature: 24,
        fan_mode: "auto",
      },
      custom: {
        enabled: true,
        hvac_mode: "auto",
        temperature: 24,
        fan_mode: "auto",
      },
    },
    automation: {
      enabled: true,
      logging_enabled: true,
      trigger_mode: "device_tracker",
      offline_confirm_seconds: 45,
      presence_sensor_entity: "",
      device_tracker_entity: "",
      presence_sensor_include_keywords: [],
      presence_sensor_exclude_keywords: [],
      device_tracker_include_keywords: [],
      device_tracker_exclude_keywords: [],
      schedule: {
        enabled: false,
        start_time: "00:00",
        end_time: "23:59",
      },
      ac: {
        enabled: false,
        auto_on: false,
        auto_off: false,
        on_delay_sec: 0,
        off_delay_sec: 0,
        target_include_keywords: [],
        target_exclude_keywords: [],
        manual_override: true,
        restore_delay_sec: 0,
        season_strategy: "selected",
        temperature_limits_enabled: false,
        min_temperature: 16,
        max_temperature: 30,
      },
      light: {
        enabled: false,
        auto_on: false,
        auto_off: false,
        on_delay_sec: 0,
        off_delay_sec: 0,
        target_include_keywords: [],
        target_exclude_keywords: [],
        arrival_preset: "full_on",
        departure_preset: "full_off",
      },
      fresh_air: {
        enabled: false,
        auto_on: false,
        auto_off: false,
        on_delay_sec: 0,
        off_delay_sec: 0,
        target_include_keywords: [],
        target_exclude_keywords: [],
        fan_mode: "auto",
      },
    },
  };
}

function normalizeRoomConfig(room, config) {
  const base = defaultRoomConfig(room && room.room_id ? room.room_id : "", room && room.room_name ? room.room_name : "");
  const existing = config || {};
  return {
    ...base,
    ...existing,
    room_id: existing.room_id || base.room_id,
    room_name: existing.room_name || base.room_name,
    entities: {
      ...base.entities,
      ...(existing.entities || {}),
      lights: Array.isArray(existing && existing.entities && existing.entities.lights) ? existing.entities.lights.filter(Boolean) : [],
    },
    lighting_presets: {
      ...base.lighting_presets,
      ...(existing.lighting_presets || {}),
      full_on: Array.isArray(existing && existing.lighting_presets && existing.lighting_presets.full_on) ? existing.lighting_presets.full_on.filter(Boolean) : [],
      half_on: Array.isArray(existing && existing.lighting_presets && existing.lighting_presets.half_on) ? existing.lighting_presets.half_on.filter(Boolean) : [],
      full_off: Array.isArray(existing && existing.lighting_presets && existing.lighting_presets.full_off) ? existing.lighting_presets.full_off.filter(Boolean) : [],
    },
    lighting_filters: {
      ...base.lighting_filters,
      ...(existing.lighting_filters || {}),
      entity_keywords: parseKeywordList(existing && existing.lighting_filters && existing.lighting_filters.entity_keywords),
      half_on_keywords: parseKeywordList(existing && existing.lighting_filters && existing.lighting_filters.half_on_keywords),
    },
    entity_filters: {
      ...base.entity_filters,
      ...(existing.entity_filters || {}),
      ac_include_keywords: parseKeywordList(existing && existing.entity_filters && existing.entity_filters.ac_include_keywords),
      ac_exclude_keywords: parseKeywordList(existing && existing.entity_filters && existing.entity_filters.ac_exclude_keywords),
      light_include_keywords: parseKeywordList(existing && existing.entity_filters && existing.entity_filters.light_include_keywords),
      light_exclude_keywords: parseKeywordList(existing && existing.entity_filters && existing.entity_filters.light_exclude_keywords),
      fresh_air_include_keywords: parseKeywordList(existing && existing.entity_filters && existing.entity_filters.fresh_air_include_keywords),
      fresh_air_exclude_keywords: parseKeywordList(existing && existing.entity_filters && existing.entity_filters.fresh_air_exclude_keywords),
    },
    subcontrol: {
      ...base.subcontrol,
      ...(existing.subcontrol || {}),
    },
    modes: {
      ...base.modes,
      ...(existing.modes || {}),
      summer: {
        ...base.modes.summer,
        ...((existing.modes && existing.modes.summer) || {}),
      },
      winter: {
        ...base.modes.winter,
        ...((existing.modes && existing.modes.winter) || {}),
      },
      custom: {
        ...base.modes.custom,
        ...((existing.modes && existing.modes.custom) || {}),
      },
    },
    automation: {
      ...base.automation,
      ...(existing.automation || {}),
      trigger_mode: triggerModeValue(
        existing && existing.automation && (
          existing.automation.trigger_mode ||
          existing.automation.online_mode ||
          existing.automation.presence_mode
        )
      ),
      presence_sensor_entity: String(existing && existing.automation && existing.automation.presence_sensor_entity || ""),
      device_tracker_entity: String(existing && existing.automation && existing.automation.device_tracker_entity || ""),
      presence_sensor_include_keywords: parseKeywordList(existing && existing.automation && existing.automation.presence_sensor_include_keywords),
      presence_sensor_exclude_keywords: parseKeywordList(existing && existing.automation && existing.automation.presence_sensor_exclude_keywords),
      device_tracker_include_keywords: parseKeywordList(existing && existing.automation && existing.automation.device_tracker_include_keywords),
      device_tracker_exclude_keywords: parseKeywordList(existing && existing.automation && existing.automation.device_tracker_exclude_keywords),
      schedule: {
        ...base.automation.schedule,
        ...((existing.automation && existing.automation.schedule) || {}),
      },
      ac: {
        ...base.automation.ac,
        ...((existing.automation && existing.automation.ac) || {}),
        target_include_keywords: parseKeywordList(existing && existing.automation && existing.automation.ac && existing.automation.ac.target_include_keywords),
        target_exclude_keywords: parseKeywordList(existing && existing.automation && existing.automation.ac && existing.automation.ac.target_exclude_keywords),
      },
      light: {
        ...base.automation.light,
        ...((existing.automation && existing.automation.light) || {}),
        target_include_keywords: parseKeywordList(existing && existing.automation && existing.automation.light && existing.automation.light.target_include_keywords),
        target_exclude_keywords: parseKeywordList(existing && existing.automation && existing.automation.light && existing.automation.light.target_exclude_keywords),
      },
      fresh_air: {
        ...base.automation.fresh_air,
        ...((existing.automation && existing.automation.fresh_air) || {}),
        target_include_keywords: parseKeywordList(existing && existing.automation && existing.automation.fresh_air && existing.automation.fresh_air.target_include_keywords),
        target_exclude_keywords: parseKeywordList(existing && existing.automation && existing.automation.fresh_air && existing.automation.fresh_air.target_exclude_keywords),
      },
    },
  };
}

function defaultGlobalSettings() {
  const defaults = defaultRoomConfig("", "");
  return {
    entity_filters: { ...defaults.entity_filters },
    modes: {
      selected_season: defaults.modes.selected_season,
      summer: { ...defaults.modes.summer },
      winter: { ...defaults.modes.winter },
      custom: { ...defaults.modes.custom },
    },
    automation: {
      ...defaults.automation,
      schedule: { ...defaults.automation.schedule },
      ac: { ...defaults.automation.ac },
      light: { ...defaults.automation.light },
      fresh_air: { ...defaults.automation.fresh_air },
    },
    subcontrol_trust: {
      enabled: false,
      allowed_cidrs: [],
      trust_proxy_headers: false,
    },
  };
}

function normalizeGlobalSettings(config) {
  const defaults = defaultGlobalSettings();
  const normalized = normalizeRoomConfig(null, config || {});
  return {
    entity_filters: {
      ...defaults.entity_filters,
      ...(normalized.entity_filters || {}),
    },
    modes: {
      ...defaults.modes,
      ...(normalized.modes || {}),
      summer: {
        ...defaults.modes.summer,
        ...((normalized.modes && normalized.modes.summer) || {}),
      },
      winter: {
        ...defaults.modes.winter,
        ...((normalized.modes && normalized.modes.winter) || {}),
      },
      custom: {
        ...defaults.modes.custom,
        ...((normalized.modes && normalized.modes.custom) || {}),
      },
    },
    automation: {
      ...defaults.automation,
      ...(normalized.automation || {}),
      schedule: {
        ...defaults.automation.schedule,
        ...((normalized.automation && normalized.automation.schedule) || {}),
      },
      ac: {
        ...defaults.automation.ac,
        ...((normalized.automation && normalized.automation.ac) || {}),
        target_include_keywords: parseKeywordList(normalized && normalized.automation && normalized.automation.ac && normalized.automation.ac.target_include_keywords),
        target_exclude_keywords: parseKeywordList(normalized && normalized.automation && normalized.automation.ac && normalized.automation.ac.target_exclude_keywords),
      },
      light: {
        ...defaults.automation.light,
        ...((normalized.automation && normalized.automation.light) || {}),
        target_include_keywords: parseKeywordList(normalized && normalized.automation && normalized.automation.light && normalized.automation.light.target_include_keywords),
        target_exclude_keywords: parseKeywordList(normalized && normalized.automation && normalized.automation.light && normalized.automation.light.target_exclude_keywords),
      },
      fresh_air: {
        ...defaults.automation.fresh_air,
        ...((normalized.automation && normalized.automation.fresh_air) || {}),
        target_include_keywords: parseKeywordList(normalized && normalized.automation && normalized.automation.fresh_air && normalized.automation.fresh_air.target_include_keywords),
        target_exclude_keywords: parseKeywordList(normalized && normalized.automation && normalized.automation.fresh_air && normalized.automation.fresh_air.target_exclude_keywords),
      },
    },
    subcontrol_trust: {
      ...defaults.subcontrol_trust,
      ...((config && config.subcontrol_trust) || {}),
      allowed_cidrs: parseKeywordList(config && config.subcontrol_trust && config.subcontrol_trust.allowed_cidrs),
    },
  };
}

function getLicenseRemainingDays(status) {
  if (!status || !status.is_valid) return null;
  if (status.expires_at) {
    const expiresAt = new Date(status.expires_at);
    if (!Number.isNaN(expiresAt.getTime())) {
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
      const expiryDay = new Date(expiresAt.getFullYear(), expiresAt.getMonth(), expiresAt.getDate(), 0, 0, 0, 0);
      return Math.ceil((expiryDay.getTime() - today.getTime()) / 86400000);
    }
  }
  const message = String(status.message || "");
  const matched = message.match(/(?:仅剩|剩余)\s*(\d+)\s*天/);
  return matched ? Number(matched[1]) : null;
}

function normalizeApiBase(raw) {
  const text = String(raw || "").trim();
  if (!text) return "";
  return text.replace(/\/+$/, "");
}

function normalizeThemeKey(value) {
  const text = String(value || "").trim().toLowerCase();
  return ["light", "dark"].includes(text) ? text : "light";
}

function themeLabel(theme) {
  const t = normalizeThemeKey(theme);
  if (t === "dark") return "暗黑";
  return "日间";
}

function booleanSetting(value, fallback = false) {
  if (typeof value === "boolean") return value;
  if (value == null || value === "") return Boolean(fallback);
  return ["1", "true", "yes", "on"].includes(String(value).trim().toLowerCase());
}

function normalizeTimeText(value, fallback = "00:00") {
  const match = String(value || "").trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return fallback;
  const hour = Math.max(0, Math.min(23, Number(match[1])));
  const minute = Math.max(0, Math.min(59, Number(match[2])));
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function uiSettingsStorageKey() {
  return "netcafe_panel_ui_settings";
}

function defaultUiSettings() {
  return {
    brand: {
      name: "智享空间",
      subtitle: "Netcafe",
      logo_url: "",
    },
    theme: {
      selected: "light",
      auto_by_time: false,
      day_theme: "light",
      night_theme: "dark",
      day_start_time: "08:00",
      night_start_time: "18:00",
    },
  };
}

function readStoredUiSettings() {
  try {
    const raw = String(window.localStorage.getItem(uiSettingsStorageKey()) || "").trim();
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
}

function normalizeUiSettings(value) {
  const base = defaultUiSettings();
  const storedTheme = normalizeThemeKey(window.localStorage.getItem("netcafe_panel_theme") || base.theme.selected);
  const theme = value && value.theme ? value.theme : {};
  const brand = value && value.brand ? value.brand : {};
  return {
    brand: {
      name: String(brand.name || base.brand.name).trim(),
      subtitle: String(brand.subtitle || base.brand.subtitle || "Netcafe").trim(),
      logo_url: String(brand.logo_url || base.brand.logo_url).trim(),
    },
    theme: {
      selected: normalizeThemeKey(theme.selected || storedTheme),
      auto_by_time: booleanSetting(theme.auto_by_time, base.theme.auto_by_time),
      day_theme: normalizeThemeKey(theme.day_theme || base.theme.day_theme),
      night_theme: normalizeThemeKey(theme.night_theme || base.theme.night_theme),
      day_start_time: normalizeTimeText(theme.day_start_time, base.theme.day_start_time),
      night_start_time: normalizeTimeText(theme.night_start_time, base.theme.night_start_time),
    },
  };
}

function currentUiSettings() {
  const stored = readStoredUiSettings() || {};
  const configUi = state.config && state.config.data && state.config.data.ui ? state.config.data.ui : {};
  return normalizeUiSettings({
    ...configUi,
    ...stored,
    brand: {
      ...((configUi && configUi.brand) || {}),
      ...((stored && stored.brand) || {}),
    },
    theme: {
      ...((configUi && configUi.theme) || {}),
      ...((stored && stored.theme) || {}),
    },
  });
}

function normalizeBrandLogoUrl(url) {
  return String(url || "").trim();
}

const BRAND_LOGO_PRESETS = [
  { key: "cyber-crown", label: "Cyber Crown", note: "电竞旗舰风", url: "/api/netcafe/icons/smart-cafe-cyber-crown.png" },
  { key: "neon-nexus", label: "Neon Nexus", note: "科技平台感", url: "/api/netcafe/icons/smart-cafe-neon-nexus.png" },
  { key: "titan-eye", label: "Titan Eye", note: "智能中枢感", url: "/api/netcafe/icons/smart-cafe-titan-eye.png" },
  { key: "vortex-blade", label: "Vortex Blade", note: "速度与锋芒", url: "/api/netcafe/icons/smart-cafe-vortex-blade.png" },
];
let brandLogoCatalogPromise = null;

function availableBrandLogoPresets() {
  return Array.isArray(state.brandLogoCatalog) && state.brandLogoCatalog.length
    ? state.brandLogoCatalog
    : state.brandLogoCatalogLoaded ? [] : BRAND_LOGO_PRESETS;
}

function normalizeBrandLogoCompareValue(url) {
  return normalizeBrandLogoUrl(url)
    .replace(window.location.origin, "")
    .replace(/^\.\//, "/")
    .trim()
    .toLowerCase();
}

function currentBrandLogoPresetKey(url) {
  const current = normalizeBrandLogoCompareValue(url);
  const found = availableBrandLogoPresets().find((item) => normalizeBrandLogoCompareValue(item.url) === current);
  return found ? found.key : "";
}

function renderBrandLogoPresetPicker(selectedUrl) {
  const items = availableBrandLogoPresets();
  if (!items.length) {
    return `<div class="ref-note">当前 icons 文件夹里还没有可选图片。</div>`;
  }
  const activeKey = currentBrandLogoPresetKey(selectedUrl);
  return `
    <div class="brand-logo-preset-grid">
      ${items.map((item) => `
        <button
          class="brand-logo-preset-card ${item.key === activeKey ? "active" : ""}"
          type="button"
          onclick='selectBrandLogoPreset(${JSON.stringify(item.url)})'
        >
          <span class="brand-logo-preset-thumb">
            <img src="${escapeHtml(item.url)}" alt="${escapeHtml(item.label)}">
          </span>
          <span class="brand-logo-preset-copy">
            <strong>${escapeHtml(item.label)}</strong>
            <small>${escapeHtml(item.note)}</small>
          </span>
        </button>
      `).join("")}
    </div>
  `;
}

async function loadBrandLogoCatalog(force = false) {
  if (!force && Array.isArray(state.brandLogoCatalog) && state.brandLogoCatalog.length) {
    return state.brandLogoCatalog;
  }
  if (!force && brandLogoCatalogPromise) {
    return brandLogoCatalogPromise;
  }
  brandLogoCatalogPromise = fetch(buildApiUrl("/api/netcafe/icons/manifest.json"), { cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    })
    .then((payload) => {
      const items = Array.isArray(payload && payload.icons) ? payload.icons : [];
      state.brandLogoCatalog = items
        .filter((item) => item && item.file)
        .map((item, index) => ({
          key: String(item.key || item.name || item.file || `icon-${index + 1}`).trim(),
          label: String(item.label || item.name || item.file || `Logo ${index + 1}`).trim(),
          note: String(item.note || item.file || "").trim(),
          url: buildApiUrl(`/api/netcafe/icons/${String(item.file).trim()}`),
        }));
      state.brandLogoCatalogLoaded = true;
      return state.brandLogoCatalog;
    })
    .catch(() => {
      state.brandLogoCatalog = [];
      state.brandLogoCatalogLoaded = true;
      return state.brandLogoCatalog;
    })
    .finally(() => {
      brandLogoCatalogPromise = null;
      if (isSettingsPageActive()) {
        renderSettingsPage();
      }
    });
  return brandLogoCatalogPromise;
}

function brandLogoCandidates(url) {
  const text = normalizeBrandLogoUrl(url);
  if (!text) return [];
  const candidates = [];
  const pushCandidate = (value) => {
    const candidate = String(value || "").trim();
    if (!candidate || candidates.includes(candidate)) return;
    candidates.push(candidate);
  };
  pushCandidate(text);
  if (/^\/local\/netcafe\/brand_logo\./i.test(text)) {
    const versionMatch = text.match(/[?&]v=(\d+)/i);
    const versionSuffix = versionMatch ? `?v=${versionMatch[1]}` : "";
    pushCandidate(buildApiUrl(`/api/netcafe/panel/logo/current${versionSuffix}`));
  }
  return candidates;
}


function currentRoomConfigSource(roomId = state.currentRoomId) {
  return state.config && state.config.data && state.config.data.rooms
    ? state.config.data.rooms[roomId] || null
    : null;
}

function currentGlobalSettings() {
  const raw = state.config && state.config.data ? state.config.data.global_settings : null;
  if (raw) {
    return normalizeGlobalSettings(raw);
  }
  const rooms = state.config && state.config.data && state.config.data.rooms ? Object.values(state.config.data.rooms) : [];
  const legacySource = currentRoomConfigSource() || rooms.find((item) => item && typeof item === "object") || null;
  return normalizeGlobalSettings(legacySource || {});
}

function normalizeNotificationSettings(raw) {
  const source = raw && typeof raw === "object" ? raw : {};
  return {
    wechat: {
      enabled: Boolean(source.wechat && source.wechat.enabled),
      channel_provider: "cn_im_hub_wechat",
      channel: String(source.wechat && source.wechat.channel || "wechat/user_id").trim() || "wechat/user_id",
      target: String(source.wechat && (source.wechat.target || source.wechat.recipient_id) || "").trim(),
      wechat_account_id: String(source.wechat && source.wechat.wechat_account_id || "").trim(),
      alert_scope: String(source.wechat && source.wechat.alert_scope || "offline_and_errors").trim() || "offline_and_errors",
      daily_brief_enabled: source.wechat && Object.prototype.hasOwnProperty.call(source.wechat, "daily_brief_enabled")
        ? Boolean(source.wechat.daily_brief_enabled)
        : true,
      daily_brief_time: normalizeTimeText(source.wechat && source.wechat.daily_brief_time || "23:00", "23:00"),
      offline_cooldown_minutes: Math.max(0, Number(source.wechat && source.wechat.offline_cooldown_minutes || 30) || 30),
    },
  };
}

function currentNotificationConfig() {
  return normalizeNotificationSettings(state.notificationConfig || state.config?.data?.notifications || {});
}

function currentNotificationStatus() {
  return state.notificationStatus && typeof state.notificationStatus === "object" ? state.notificationStatus : {};
}

function currentNotificationQrStatus() {
  return state.notificationQr && typeof state.notificationQr === "object" ? state.notificationQr : {};
}

function currentNotificationPreview() {
  return state.notificationPreview && typeof state.notificationPreview === "object" ? state.notificationPreview : {};
}

function storeUiSettings(settings) {
  const normalized = normalizeUiSettings(settings);
  window.localStorage.setItem(uiSettingsStorageKey(), JSON.stringify(normalized));
  return normalized;
}

function timeTextToMinutes(value) {
  const normalized = normalizeTimeText(value, "00:00");
  const parts = normalized.split(":");
  return (Number(parts[0]) * 60) + Number(parts[1]);
}

function isNightThemeTime(date, dayStartTime, nightStartTime) {
  const current = (date.getHours() * 60) + date.getMinutes();
  const dayStart = timeTextToMinutes(dayStartTime);
  const nightStart = timeTextToMinutes(nightStartTime);
  if (dayStart === nightStart) return false;
  if (dayStart < nightStart) {
    return current < dayStart || current >= nightStart;
  }
  return current >= nightStart && current < dayStart;
}

function resolveConfiguredTheme(uiSettings, date = new Date()) {
  const settings = normalizeUiSettings(uiSettings);
  if (!settings.theme.auto_by_time) {
    return settings.theme.selected;
  }
  return isNightThemeTime(date, settings.theme.day_start_time, settings.theme.night_start_time)
    ? settings.theme.night_theme
    : settings.theme.day_theme;
}

function loadThemePreference() {
  applyTheme(resolveConfiguredTheme(currentUiSettings()));
}

function applyTheme(theme, options = {}) {
  const nextTheme = normalizeThemeKey(theme);
  state.currentTheme = nextTheme;
  document.documentElement.setAttribute("data-theme", nextTheme);
  if (!options.skipStorage) {
    window.localStorage.setItem("netcafe_panel_theme", nextTheme);
  }
}

function syncConfiguredTheme() {
  const settings = currentUiSettings();
  applyTheme(resolveConfiguredTheme(settings));
  applyBrandSettings(settings.brand);
}


function updateThemeSettingsVisibility() {
  const themeAutoInput = document.getElementById("themeAutoByTime");
  if (!themeAutoInput) return;
  const autoByTime = Boolean(themeAutoInput.checked);
  document.querySelectorAll(".theme-mode-manual").forEach((node) => {
    node.classList.toggle("is-hidden", autoByTime);
  });
  document.querySelectorAll(".theme-mode-auto").forEach((node) => {
    node.classList.toggle("is-hidden", !autoByTime);
  });
  const pill = document.getElementById("themeEffectivePill");
  if (pill) {
    pill.textContent = themeLabel(resolveConfiguredTheme(collectUiSettings()));
  }
}

function handleThemeSettingsChange() {
  const nextSettings = collectUiSettings();
  storeUiSettings(nextSettings);
  syncConfiguredTheme();
  updateThemeSettingsVisibility();
}

function updateLinkageModeVisibility() {
  const modeInput = document.getElementById("linkTriggerMode");
  if (!modeInput) return;
  const mode = triggerModeValue(modeInput.value);
  const showTracker = mode === "device_tracker" || mode === "hybrid";
  const showSensor = mode === "sensor" || mode === "hybrid";
  document.querySelectorAll(".linkage-mode-tracker").forEach((node) => {
    node.classList.toggle("is-hidden", !showTracker);
  });
  document.querySelectorAll(".linkage-mode-sensor").forEach((node) => {
    node.classList.toggle("is-hidden", !showSensor);
  });
  const pill = document.getElementById("linkTriggerModePill");
  if (pill) {
    pill.textContent = mode === "hybrid" ? "混合判断" : mode === "sensor" ? "人在传感器" : "device_tracker";
  }
  updateLinkagePreviewResults();
}

function updateLinkagePreviewResults() {
  const trackerPreview = document.getElementById("deviceTrackerMatchPreview");
  if (trackerPreview) {
    const includeValue = textValue("deviceTrackerIncludeKeywords", "");
    const excludeValue = textValue("deviceTrackerExcludeKeywords", "");
    const items = filterEntityOptions(deviceTrackerCandidates(), includeValue, excludeValue);
    trackerPreview.innerHTML = renderReferenceEntityCount(
      items,
      "Tracker 匹配结果",
      "当前没有匹配到 Tracker。",
      "个 Tracker",
      "点击查看具体匹配到的 Tracker。"
    );
  }
  const sensorPreview = document.getElementById("presenceSensorMatchPreview");
  if (sensorPreview) {
    const includeValue = textValue("presenceSensorIncludeKeywords", "");
    const excludeValue = textValue("presenceSensorExcludeKeywords", "");
    const items = filterEntityOptions(presenceSensorCandidates(), includeValue, excludeValue);
    sensorPreview.innerHTML = renderReferenceEntityCount(
      items,
      "传感器匹配结果",
      "当前没有匹配到传感器。",
      "个传感器",
      "点击查看具体匹配到的传感器。"
    );
  }
}

function draftCurrentRoomEntityFilters(roomConfig) {
  const existingFilters = roomEntityFilters(roomConfig);
  return {
    ...existingFilters,
    ac_include_keywords: parseKeywordList(textValue("acIncludeKeywords", existingFilters.ac_include_keywords)),
    ac_exclude_keywords: parseKeywordList(textValue("acExcludeKeywords", existingFilters.ac_exclude_keywords)),
    light_include_keywords: parseKeywordList(textValue("lightIncludeKeywords", existingFilters.light_include_keywords)),
    light_exclude_keywords: parseKeywordList(textValue("lightExcludeKeywords", existingFilters.light_exclude_keywords)),
    fresh_air_include_keywords: parseKeywordList(textValue("freshIncludeKeywords", existingFilters.fresh_air_include_keywords)),
    fresh_air_exclude_keywords: parseKeywordList(textValue("freshExcludeKeywords", existingFilters.fresh_air_exclude_keywords)),
  };
}

function updateCurrentRoomEntityMatchSummaries() {
  const room = getRoom(state.currentRoomId);
  const roomConfig = room ? currentRoomConfig(room.room_id) : null;
  if (!room || !roomConfig) return;
  const previewConfig = {
    ...roomConfig,
    entity_filters: draftCurrentRoomEntityFilters(roomConfig),
  };
  const roomTargets = autoDetectedRoomTargets(room, previewConfig);
  const acSummary = document.getElementById("acMatchSummary");
  if (acSummary) {
    acSummary.innerHTML = renderReferenceEntityMatchTrigger(
      "空调识别结果",
      roomTargets.ac,
      "暂未识别到空调。",
      "个空调实体",
      "点击查看当前房间匹配到的空调实体。"
    );
  }
  const lightSummary = document.getElementById("lightMatchSummary");
  if (lightSummary) {
    lightSummary.innerHTML = renderReferenceEntityMatchTrigger(
      "灯光识别结果",
      roomTargets.lights,
      "暂未识别到灯光。",
      "盏灯",
      "点击查看当前房间匹配到的灯光实体。"
    );
  }
  const freshSummary = document.getElementById("freshMatchSummary");
  if (freshSummary) {
    freshSummary.innerHTML = renderReferenceEntityMatchTrigger(
      "新风识别结果",
      roomTargets.fresh,
      "暂未识别到新风。",
      "个新风实体",
      "点击查看当前房间匹配到的新风实体。"
    );
  }
  const detectedAcId = (roomTargets.ac[0] && roomTargets.ac[0].entity_id) || (roomConfig.entities && roomConfig.entities.ac) || "";
  const summerHvacMode = document.getElementById("summerHvacMode");
  if (summerHvacMode) {
    const currentValue = summerHvacMode.value || roomConfig.modes.summer.hvac_mode;
    summerHvacMode.innerHTML = selectedAcModes(detectedAcId, currentValue);
  }
  const summerFanMode = document.getElementById("summerFanMode");
  if (summerFanMode) {
    const currentValue = summerFanMode.value || roomConfig.modes.summer.fan_mode;
    summerFanMode.innerHTML = selectedAcFanModes(detectedAcId, currentValue);
  }
  const winterHvacMode = document.getElementById("winterHvacMode");
  if (winterHvacMode) {
    const currentValue = winterHvacMode.value || roomConfig.modes.winter.hvac_mode;
    winterHvacMode.innerHTML = selectedAcModes(detectedAcId, currentValue);
  }
  const winterFanMode = document.getElementById("winterFanMode");
  if (winterFanMode) {
    const currentValue = winterFanMode.value || roomConfig.modes.winter.fan_mode;
    winterFanMode.innerHTML = selectedAcFanModes(detectedAcId, currentValue);
  }
}

function sidebarCollapsedStorageKey() {
  return "netcafe_panel_sidebar_collapsed";
}

function isSidebarDesktopLayout() {
  return window.innerWidth > 900;
}

function syncSidebarCollapsedState() {
  const effectiveCollapsed = isSidebarDesktopLayout() && state.isSidebarCollapsed;
  document.body.classList.toggle("sidebar-collapsed", effectiveCollapsed);
  const toggle = document.getElementById("sidebarToggle");
  if (!toggle) return;
  toggle.hidden = !isSidebarDesktopLayout();
  toggle.disabled = !isSidebarDesktopLayout();
  const label = effectiveCollapsed ? "展开侧栏" : "收起侧栏";
  toggle.setAttribute("aria-label", label);
  toggle.setAttribute("title", label);
  toggle.setAttribute("aria-expanded", String(!effectiveCollapsed));
}

function applySidebarCollapsed(collapsed) {
  state.isSidebarCollapsed = Boolean(collapsed);
  syncSidebarCollapsedState();
}

function loadSidebarPreference() {
  const saved = String(window.localStorage.getItem(sidebarCollapsedStorageKey()) || "").trim();
  applySidebarCollapsed(saved === "1");
}

function toggleSidebar() {
  if (!isSidebarDesktopLayout()) return;
  applySidebarCollapsed(!state.isSidebarCollapsed);
  window.localStorage.setItem(sidebarCollapsedStorageKey(), state.isSidebarCollapsed ? "1" : "0");
}

function authTokenStorageKey() {
  return "netcafe_panel_auth_token";
}

function loadStoredAuthToken() {
  const token = String(window.localStorage.getItem(authTokenStorageKey()) || "").trim();
  state.auth.token = token;
  return token;
}

function storeAuthToken(token) {
  const nextToken = String(token || "").trim();
  state.auth.token = nextToken;
  if (nextToken) {
    window.localStorage.setItem(authTokenStorageKey(), nextToken);
  } else {
    window.localStorage.removeItem(authTokenStorageKey());
  }
}

function currentAuthUser() {
  return state.auth && state.auth.user ? state.auth.user : null;
}

function redirectToLogin() {
  const next = encodeURIComponent(window.location.pathname + window.location.search + window.location.hash);
  window.location.replace(`/api/netcafe/login.html?next=${next}`);
}

function selectClientTheme(theme) {
  const uiSettings = currentUiSettings();
  uiSettings.theme.selected = normalizeThemeKey(theme);
  uiSettings.theme.auto_by_time = false;
  storeUiSettings(uiSettings);
  applyTheme(uiSettings.theme.selected);
  renderSettingsPage();
  showMessage(`客户端主题已切换为 ${themeLabel(uiSettings.theme.selected)}。`, "success", true);
}

function currentLicenseStatus() {
  return state.license && state.license.data ? state.license.data : null;
}

function renderAuthGate() {
  const userChip = document.getElementById("authUserChip");
  const headerUserName = document.getElementById("headerUserName");
  const headerUserRole = document.getElementById("headerUserRole");
  const user = currentAuthUser();
  const authenticated = Boolean(state.auth.token && user);
  if (userChip) {
    userChip.classList.toggle("hidden", !authenticated);
    if (authenticated) {
      userChip.textContent = "退出";
    } else {
      userChip.textContent = "未登录";
    }
  }
  if (headerUserName) {
    headerUserName.textContent = authenticated ? (user.username || "管理员") : "管理台";
  }
  if (headerUserRole) {
    headerUserRole.textContent = "";
  }
}

async function restoreAuthSession() {
  loadStoredAuthToken();
  state.auth.user = null;
  renderAuthGate();
  if (!state.auth.token) {
    redirectToLogin();
    return false;
  }
  try {
    const result = await requestJson("/api/netcafe/panel/auth/session");
    state.auth.user = result && result.data ? result.data.user : null;
    if (result && result.data && result.data.license) {
      state.license = { success: true, data: result.data.license };
    }
    renderAuthGate();
    return Boolean(state.auth.user);
  } catch (error) {
    storeAuthToken("");
    state.auth.user = null;
    renderAuthGate();
    redirectToLogin();
    return false;
  }
}

function logoutPanelAuth() {
  storeAuthToken("");
  state.auth.user = null;
  state.overview = null;
  state.config = null;
  state.entities = null;
  state.license = null;
  state.energyHistory = { daily_kwh: null, monthly_kwh: null, source: "" };
  state.dailySummary = null;
  state.authError = "";
  state.reloadError = "";
  stopRealtimeSync();
  renderAll();
  renderAuthGate();
  redirectToLogin();
}

async function activateLicense() {
  const keyInput = document.getElementById("licenseKeyInput");
  const deviceInput = document.getElementById("licenseDeviceInput");
  const licenseKey = String(keyInput && keyInput.value || "").trim();
  const deviceId = String(deviceInput && deviceInput.value || "").trim();
  if (!licenseKey) {
    showMessage("请输入卡密。", "warning", true);
    return;
  }
  try {
    showMessage("正在激活卡密...", "info");
    const result = await requestJson("/api/netcafe/panel/license/activate", {
      method: "POST",
      body: JSON.stringify({
        license_key: licenseKey,
        device_id: deviceId,
      }),
    });
    if (result && result.data) {
      state.license = { success: true, data: result.data };
    }
    updateLicenseBadge();
    renderSettingsPage();
    showMessage((result && result.data && result.data.message) || "卡密已激活。", "success", true);
  } catch (error) {
    showMessage(error.message || "卡密激活失败。", "error");
  }
}

function loadConnectionSettings() {
  state.connection.apiBase = canUseSameOrigin() ? normalizeApiBase(window.location.origin) : "";
}

function canUseSameOrigin() {
  return window.location.protocol === "http:" || window.location.protocol === "https:";
}

function isConnectionConfigured() {
  return canUseSameOrigin();
}

function buildApiUrl(path) {
  if (/^https?:\/\//i.test(path)) return path;
  const base = state.connection.apiBase;
  if (base) return base + path;
  return path;
}

function buildRealtimeSocketUrl(path) {
  const rawUrl = buildApiUrl(path);
  if (/^wss?:\/\//i.test(rawUrl)) return rawUrl;
  if (/^https?:\/\//i.test(rawUrl)) {
    return rawUrl.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:");
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${rawUrl.startsWith("/") ? rawUrl : `/${rawUrl}`}`;
}

async function requestJson(path, options = {}) {
  if (!isConnectionConfigured()) {
    throw new Error("当前页面不在智慧网吧同源环境中，请从集成入口访问。");
  }
  const headers = { ...(options.headers || {}) };
  if (state.auth && state.auth.token) {
    headers["X-Netcafe-Auth"] = state.auth.token;
  }
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  const response = await fetch(buildApiUrl(path), {
    method: options.method || "GET",
    body: options.body,
    headers,
    credentials: "same-origin",
  });
  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }
  if (!response.ok || !data || data.success === false) {
    if (response.status === 401 && data && data.auth_required) {
      storeAuthToken("");
      state.auth.user = null;
      stopRealtimeSync();
      renderAuthGate();
      redirectToLogin();
      throw new Error(data.message || "请先登录后再访问系统。");
    }
    if (response.status === 401) {
      throw new Error("需要先登录当前管理系统后再访问此页面。");
    }
    if (response.status === 403 && data && data.license_required) {
      throw new Error(data.message || "卡密无效或自动化已暂停。");
    }
    throw new Error((data && data.message) || ("请求失败: " + response.status));
  }
  return data;
}

async function requestRawJson(path) {
  if (!isConnectionConfigured()) {
    throw new Error("当前页面不在智慧网吧同源环境中。");
  }
  if (state.historyAuthError) {
    return null;
  }
  if (state.historyAuthProbe) {
    await state.historyAuthProbe;
    if (state.historyAuthError) {
      return null;
    }
  }
  let proxyPath = path;
  if (String(path || "").startsWith("/api/history/period/")) {
    const match = String(path).match(/^\/api\/history\/period\/([^?]+)\?(.*)$/);
    if (match) {
      const startTime = decodeURIComponent(match[1] || "");
      const params = new URLSearchParams(match[2] || "");
      const entityIds = params.get("filter_entity_id") || "";
      const endTime = params.get("end_time") || "";
      proxyPath = `/api/netcafe/panel/history?start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}&entity_ids=${encodeURIComponent(entityIds)}`;
    }
  }
  const execute = async () => {
    const response = await fetch(buildApiUrl(proxyPath), {
      method: "GET",
      headers: state.auth && state.auth.token ? { "X-Netcafe-Auth": state.auth.token } : {},
      credentials: "same-origin",
    });
    if (response.status === 401 || response.status === 403) {
      state.historyAuthError = "历史数据接口当前不可用";
      return null;
    }
    if (!response.ok) {
      throw new Error("请求失败: " + response.status);
    }
    const data = await response.json();
    if (proxyPath.startsWith("/api/netcafe/panel/history")) {
      return data && data.success !== false ? data.data : null;
    }
    return data;
  };
  state.historyAuthProbe = execute();
  try {
    return await state.historyAuthProbe;
  } finally {
    state.historyAuthProbe = null;
  }
}

function showMessage(text, type = "info", autoHide = false) {
  const box = document.getElementById("messageBox");
  box.textContent = text || "";
  box.className = "banner" + (text ? " show " + type : "");
  if (text && autoHide) {
    window.clearTimeout(showMessage.timer);
    showMessage.timer = window.setTimeout(() => {
      box.className = "banner";
      box.textContent = "";
    }, 2200);
  }
}

function updateDateTime() {
  const now = new Date();
  const clock = document.getElementById("datetime");
  const dateText = document.getElementById("headerDateText");
  if (clock) {
    clock.textContent = now.toLocaleTimeString("zh-CN", { hour12: false });
  }
  if (dateText) {
    dateText.textContent = now.toLocaleDateString("zh-CN", {
      month: "numeric",
      day: "numeric",
      weekday: "short",
    });
  }
}

function updateConnectionBadge() {
  const badge = document.getElementById("connectionBadge");
  const syncText = state.syncMode === "websocket"
    ? "实时"
    : state.syncMode === "websocket-connecting"
      ? "切换中"
      : "轮询";
  if (!isConnectionConfigured()) {
    badge.className = "badge red";
    badge.textContent = `环境未就绪 · ${syncText}`;
    return;
  }
  if (!currentAuthUser()) {
    badge.className = "badge orange";
    badge.textContent = `等待登录 · ${syncText}`;
    return;
  }
  if (state.reloadError) {
    badge.className = "badge orange";
    badge.textContent = `重连中 · ${syncText}`;
    return;
  }
  if (state.authError) {
    badge.className = "badge orange";
    badge.textContent = `只读模式 · ${syncText}`;
    return;
  }
  if (state.config && state.entities) {
    badge.className = "badge green";
    badge.textContent = `已连接 · ${syncText}`;
    return;
  }
  badge.className = "badge blue";
  badge.textContent = `连接中 · ${syncText}`;
}

function updateLicenseBadge() {
  const badge = document.getElementById("licenseBadge");
  if (!currentAuthUser()) {
    badge.className = "badge";
    badge.textContent = "登录后读取卡密";
    return;
  }
  const status = state.license && state.license.data ? state.license.data : null;
  if (!status) {
    badge.className = "badge";
    badge.textContent = "卡密状态未知";
    return;
  }
  if (status.is_valid) {
    const remainingDays = getLicenseRemainingDays(status);
    if (remainingDays != null && remainingDays <= 3) {
      badge.className = "badge red";
    } else if (remainingDays != null && remainingDays <= 7) {
      badge.className = "badge orange";
    } else {
      badge.className = "badge green";
    }
    badge.textContent = String(status.message || "卡密有效").replace(/^卡密状态[:：]?\s*/,"");
  } else {
    badge.className = "badge red";
    badge.textContent = String(status.message || "卡密受限").replace(/^卡密状态[:：]?\s*/,"");
  }
}

function showLicenseBanner() {
  const banner = document.getElementById("licenseBanner");
  banner.className = "banner";
  banner.textContent = "";
}

function switchPage(page, element) {
  if (page !== "settings" && isSettingsPageActive()) {
    clearSettingsDraft();
  }
  document.querySelectorAll(".page").forEach((node) => node.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((node) => node.classList.remove("active"));
  const target = document.getElementById("page-" + page);
  if (target) target.classList.add("active");
  if (element) element.classList.add("active");
  document.body.setAttribute("data-page", page);
  const meta = pageMeta[page] || { title: page, subtitle: "" };
  document.getElementById("pageTitle").textContent = meta.title;
  const subtitle = document.getElementById("pageSubtitle");
  if (subtitle) subtitle.textContent = meta.subtitle;
}

function openPage(page) {
  switchPage(page, document.querySelector(`.nav-item[data-page="${page}"]`));
}

function handleCardKeyOpen(page, event) {
  if (!event) return;
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openPage(page);
  }
}

function handleActionKey(event, actionName, ...args) {
  if (!event) return;
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  const fn = window[actionName];
  if (typeof fn === "function") {
    fn(...args);
  }
}

function toggleDashboardPriceEditor(forceOpen) {
  state.dashboardPriceEditorOpen = typeof forceOpen === "boolean" ? forceOpen : !state.dashboardPriceEditorOpen;
  const popover = document.getElementById("dashboardEnergyPricePopover");
  if (!popover) return;
  popover.classList.toggle("show", state.dashboardPriceEditorOpen);
}

function currentRooms() {
  return state.overview && state.overview.data ? state.overview.data.rooms || [] : [];
}

function roomGroupDisplayKey(room) {
  const group = room && room.matched_group ? room.matched_group : null;
  if (!group) return "";
  const roomNumbers = Array.isArray(group.room_numbers) ? group.room_numbers.filter(Boolean) : [];
  if (roomNumbers.length <= 1) return "";
  const canonical = String(group.canonical_room_key || "").trim();
  if (canonical) return canonical;
  const display = String(group.display_name || "").trim();
  if (display) return display;
  return roomNumbers.join("-");
}

function chooseRoomRepresentative(a, b) {
  if (!a) return b;
  if (!b) return a;
  const aOccupied = roomOnlineTerminalCount(a) > 0;
  const bOccupied = roomOnlineTerminalCount(b) > 0;
  if (aOccupied !== bOccupied) return bOccupied ? b : a;
  const aOccupiedCount = roomOnlineTerminalCount(a);
  const bOccupiedCount = roomOnlineTerminalCount(b);
  if (aOccupiedCount !== bOccupiedCount) return bOccupiedCount > aOccupiedCount ? b : a;
  const aHasMapping = Boolean(a.summary && a.summary.has_mapping);
  const bHasMapping = Boolean(b.summary && b.summary.has_mapping);
  if (aHasMapping !== bHasMapping) return bHasMapping ? b : a;
  const aOnline = connectedComputers(a).length;
  const bOnline = connectedComputers(b).length;
  if (aOnline !== bOnline) return bOnline > aOnline ? b : a;
  return a;
}

function roomsForDisplay() {
  const rooms = Array.isArray(currentRooms()) ? currentRooms().filter(Boolean) : [];
  if (!rooms.length) return [];
  const merged = new Map();
  const items = [];

  for (let index = 0; index < rooms.length; index += 1) {
    const room = rooms[index];
    const key = roomGroupDisplayKey(room);
    if (!key) {
      items.push({ index, room });
      continue;
    }
    const existing = merged.get(key);
    if (!existing) {
      merged.set(key, { index, room });
      continue;
    }
    merged.set(key, {
      index: existing.index,
      room: chooseRoomRepresentative(existing.room, room),
    });
  }

  for (const value of merged.values()) {
    items.push(value);
  }

  items.sort((a, b) => a.index - b.index);
  return items.map((item) => item.room);
}

function currentEnergySummary() {
  return state.overview && state.overview.data ? state.overview.data.energy || null : null;
}

function currentResolvedEnergySummary() {
  const energy = currentEnergySummary();
  if (!energy) return null;
  const history = state.energyHistory || {};
  const aggregatedPower = currentAggregatedPowerSummary();
  const configuredRealtimePowerKw = energy.realtime_power_kw != null
    ? Number(energy.realtime_power_kw)
    : convertPowerValueToKw(
      energy.realtime_power && energy.realtime_power.state,
      energy.realtime_power && (energy.realtime_power.unit_of_measurement || (energy.realtime_power.attributes && energy.realtime_power.attributes.unit_of_measurement))
    );
  const realtimePowerKw = aggregatedPower.kw != null ? aggregatedPower.kw : configuredRealtimePowerKw;
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
  const startMonth = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
  const estimatedDailyKwh = Number.isFinite(realtimePowerKw) ? Number((realtimePowerKw * ((now.getTime() - startToday.getTime()) / 3600000)).toFixed(3)) : null;
  const estimatedMonthlyKwh = Number.isFinite(realtimePowerKw) ? Number((realtimePowerKw * ((now.getTime() - startMonth.getTime()) / 3600000)).toFixed(3)) : null;
  const dailyEnergyKwh = energy.daily_energy_kwh != null
    ? Number(energy.daily_energy_kwh)
    : (history.daily_kwh != null ? Number(history.daily_kwh) : estimatedDailyKwh);
  const monthlyEnergyKwh = energy.monthly_energy_kwh != null
    ? Number(energy.monthly_energy_kwh)
    : (history.monthly_kwh != null ? Number(history.monthly_kwh) : estimatedMonthlyKwh);
  const pricePerKwh = energy.price_per_kwh != null ? Number(energy.price_per_kwh) : 0;
  return {
    ...energy,
    aggregated_power_entities: aggregatedPower.items,
    configured_realtime_power_kw: Number.isFinite(configuredRealtimePowerKw) ? configuredRealtimePowerKw : null,
    realtime_power_kw: Number.isFinite(realtimePowerKw) ? realtimePowerKw : null,
    daily_energy_kwh_effective: Number.isFinite(dailyEnergyKwh) ? dailyEnergyKwh : null,
    monthly_energy_kwh_effective: Number.isFinite(monthlyEnergyKwh) ? monthlyEnergyKwh : null,
    daily_cost_effective: Number.isFinite(dailyEnergyKwh) ? Number((dailyEnergyKwh * pricePerKwh).toFixed(2)) : null,
    monthly_cost_effective: Number.isFinite(monthlyEnergyKwh) ? Number((monthlyEnergyKwh * pricePerKwh).toFixed(2)) : null,
    daily_source: energy.daily_energy_kwh != null ? "entity" : (history.daily_kwh != null ? "history" : (estimatedDailyKwh != null ? "estimate" : "")),
    monthly_source: energy.monthly_energy_kwh != null ? "entity" : (history.monthly_kwh != null ? "history" : (estimatedMonthlyKwh != null ? "estimate" : "")),
  };
}

function currentEnergyStatEntities(energy = currentResolvedEnergySummary()) {
  if (!energy) return [];
  const configuredEntityId = energy.realtime_power && energy.realtime_power.entity_id;
  const realtimeEntity = energy.realtime_power || null;
  const aggregatedItems = Array.isArray(energy.aggregated_power_entities) ? energy.aggregated_power_entities : [];
  const items = state.authError ? [] : aggregatedItems;
  const visibleItems = items.length
    ? items
    : (realtimeEntity ? [realtimeEntity] : []);
  return visibleItems.filter(Boolean).map((item) => ({
    ...item,
    is_bound: item.entity_id === configuredEntityId,
  }));
}

function currentDashboardConfig() {
  return state.config && state.config.data && state.config.data.dashboard ? state.config.data.dashboard : { energy: {} };
}

function formatMetricNumber(value, digits = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return number.toFixed(digits);
}

function startOfTodayIso() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
  return start.toISOString();
}

function startOfMonthIso() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
  return start.toISOString();
}

function convertPowerValueToKw(value, unit) {
  const number = Number(value);
  const normalizedUnit = String(unit || "").trim().toLowerCase();
  if (!Number.isFinite(number)) return null;
  if (normalizedUnit === "kw" || normalizedUnit === "千瓦") return number;
  if (normalizedUnit === "w" || normalizedUnit === "瓦") return number / 1000;
  return null;
}

function integratePowerHistoryKwh(historyRows, unit, startIso, endIso) {
  const rows = Array.isArray(historyRows) ? historyRows : [];
  if (!rows.length) return null;
  const startMs = new Date(startIso).getTime();
  const endMs = new Date(endIso).getTime();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) return null;

  const normalized = rows
    .map((row) => {
      const ts = new Date(row.last_changed || row.last_updated || row.lu || "").getTime();
      const kw = convertPowerValueToKw(row.state, unit);
      return Number.isFinite(ts) && kw != null ? { ts, kw } : null;
    })
    .filter(Boolean)
    .sort((a, b) => a.ts - b.ts);

  if (!normalized.length) return null;

  let energyKwh = 0;
  let previous = {
    ts: Math.max(startMs, normalized[0].ts),
    kw: normalized[0].kw,
  };

  for (let index = 1; index < normalized.length; index += 1) {
    const current = normalized[index];
    const segmentEnd = Math.min(current.ts, endMs);
    if (segmentEnd > previous.ts) {
      energyKwh += previous.kw * ((segmentEnd - previous.ts) / 3600000);
    }
    previous = {
      ts: Math.max(previous.ts, Math.min(current.ts, endMs)),
      kw: current.kw,
    };
    if (current.ts >= endMs) break;
  }

  if (endMs > previous.ts) {
    energyKwh += previous.kw * ((endMs - previous.ts) / 3600000);
  }
  return Number(energyKwh.toFixed(3));
}

function isHistoryStateOn(entityId, stateValue, mode = "") {
  const text = String(stateValue || "").trim().toLowerCase();
  if (!text || ["unknown", "unavailable", "none"].includes(text)) return false;
  if (mode === "climate") {
    return !["off"].includes(text);
  }
  if (mode === "computer") {
    return ["on", "home", "connected", "online", "present", "true"].includes(text);
  }
  const domain = String(entityId || "").split(".", 1)[0];
  if (["light", "fan", "switch", "binary_sensor", "input_boolean"].includes(domain)) {
    return text === "on";
  }
  return ["on", "home", "connected", "online", "present", "true"].includes(text);
}

function integrateOnDurationHours(historyRows, entityId, startIso, endIso, mode = "") {
  const rows = Array.isArray(historyRows) ? historyRows : [];
  if (!rows.length) return 0;
  const startMs = new Date(startIso).getTime();
  const endMs = new Date(endIso).getTime();
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) return 0;
  const normalized = rows
    .map((row) => {
      const ts = new Date(row.last_changed || row.last_updated || row.lu || "").getTime();
      return Number.isFinite(ts) ? { ts, state: row.state } : null;
    })
    .filter(Boolean)
    .sort((a, b) => a.ts - b.ts);
  if (!normalized.length) return 0;

  let totalMs = 0;
  let previous = {
    ts: Math.max(startMs, normalized[0].ts),
    on: isHistoryStateOn(entityId, normalized[0].state, mode),
  };
  for (let index = 1; index < normalized.length; index += 1) {
    const current = normalized[index];
    const segmentEnd = Math.min(current.ts, endMs);
    if (previous.on && segmentEnd > previous.ts) {
      totalMs += segmentEnd - previous.ts;
    }
    previous = {
      ts: Math.max(previous.ts, Math.min(current.ts, endMs)),
      on: isHistoryStateOn(entityId, current.state, mode),
    };
    if (current.ts >= endMs) break;
  }
  if (previous.on && endMs > previous.ts) {
    totalMs += endMs - previous.ts;
  }
  return Number((totalMs / 3600000).toFixed(2));
}

async function loadDailyUsageSummary(overviewPayload) {
  if (state.historyAuthError) {
    state.dailySummary = null;
    return;
  }
  const rooms = overviewPayload && overviewPayload.data && Array.isArray(overviewPayload.data.rooms)
    ? overviewPayload.data.rooms
    : [];
  const startIso = startOfTodayIso();
  const endIso = new Date().toISOString();

  const acIds = [];
  const lightIds = [];
  const freshIds = [];
  const computerIds = [];
  for (const room of rooms) {
    if (room && room.mapped && room.mapped.ac && room.mapped.ac.entity_id) acIds.push(room.mapped.ac.entity_id);
    if (room && room.mapped && Array.isArray(room.mapped.lights)) {
      for (const light of room.mapped.lights) {
        if (light && light.entity_id) lightIds.push(light.entity_id);
      }
    }
    if (room && room.mapped && room.mapped.fresh_air && room.mapped.fresh_air.entity_id) freshIds.push(room.mapped.fresh_air.entity_id);
    if (room && Array.isArray(room.computers)) {
      for (const computer of room.computers) {
        if (computer && computer.entity_id) computerIds.push(computer.entity_id);
      }
    }
  }

  const unique = (items) => Array.from(new Set(items.filter(Boolean)));
  const buckets = [
    { key: "ac", ids: unique(acIds), mode: "climate", label: "空调运行", color: "#2563eb" },
    { key: "light", ids: unique(lightIds), mode: "light", label: "灯光开启", color: "#dc7c1f" },
    { key: "fresh", ids: unique(freshIds), mode: "fresh", label: "新风运行", color: "#0f8f8c" },
    { key: "computer", ids: unique(computerIds), mode: "computer", label: "电脑在线", color: "#1f8f52" },
  ];

  try {
    const results = await Promise.all(buckets.map(async (bucket) => {
      if (!bucket.ids.length) return { ...bucket, hours: 0 };
      const history = await requestRawJson(`/api/history/period/${encodeURIComponent(startIso)}?filter_entity_id=${encodeURIComponent(bucket.ids.join(","))}&end_time=${encodeURIComponent(endIso)}`);
      if (!history) return { ...bucket, hours: 0 };
      const rows = Array.isArray(history) ? history : [];
      const hours = rows.reduce((sum, entityRows) => {
        const entityId = Array.isArray(entityRows) && entityRows[0] ? entityRows[0].entity_id : "";
        return sum + integrateOnDurationHours(entityRows, entityId, startIso, endIso, bucket.mode);
      }, 0);
      return { ...bucket, hours: Number(hours.toFixed(2)) };
    }));
    state.dailySummary = {
      date: startIso,
      items: results,
    };
  } catch (error) {
    state.dailySummary = null;
  }
}

async function loadComputedEnergyHistory(overviewPayload) {
  if (state.historyAuthError) {
    state.energyHistory = { daily_kwh: null, monthly_kwh: null, source: "" };
    return;
  }
  const energy = overviewPayload && overviewPayload.data ? overviewPayload.data.energy : null;
  if (!energy || !energy.realtime_power || !energy.realtime_power.entity_id) {
    state.energyHistory = { daily_kwh: null, monthly_kwh: null, source: "" };
    return;
  }
  if (energy.daily_energy_kwh != null && energy.monthly_energy_kwh != null) {
    state.energyHistory = { daily_kwh: null, monthly_kwh: null, source: "" };
    return;
  }

  const entityId = energy.realtime_power.entity_id;
  const unit = energy.realtime_power.unit_of_measurement || (energy.realtime_power.attributes && energy.realtime_power.attributes.unit_of_measurement) || "";
  const endIso = new Date().toISOString();
  const requests = [];

  if (energy.daily_energy_kwh == null) {
    requests.push(requestRawJson(`/api/history/period/${encodeURIComponent(startOfTodayIso())}?filter_entity_id=${encodeURIComponent(entityId)}&end_time=${encodeURIComponent(endIso)}`));
  } else {
    requests.push(Promise.resolve(null));
  }

  if (energy.monthly_energy_kwh == null) {
    requests.push(requestRawJson(`/api/history/period/${encodeURIComponent(startOfMonthIso())}?filter_entity_id=${encodeURIComponent(entityId)}&end_time=${encodeURIComponent(endIso)}`));
  } else {
    requests.push(Promise.resolve(null));
  }

  try {
    const [dailyHistory, monthlyHistory] = await Promise.all(requests);
    state.energyHistory = {
      daily_kwh: dailyHistory ? integratePowerHistoryKwh(Array.isArray(dailyHistory) ? dailyHistory[0] : [], unit, startOfTodayIso(), endIso) : null,
      monthly_kwh: monthlyHistory ? integratePowerHistoryKwh(Array.isArray(monthlyHistory) ? monthlyHistory[0] : [], unit, startOfMonthIso(), endIso) : null,
      source: "history",
    };
  } catch (error) {
    state.energyHistory = { daily_kwh: null, monthly_kwh: null, source: "" };
  }
}

function currentRoomGroups() {
  return state.overview && state.overview.data ? state.overview.data.groups || [] : [];
}

function currentLogs() {
  return state.overview && state.overview.data ? state.overview.data.logs || [] : [];
}

function currentTodayLogs(limit = 24) {
  const startMs = new Date(startOfTodayIso()).getTime();
  const logs = currentLogs()
    .filter((log) => {
      const ts = new Date(log && log.timestamp || "").getTime();
      return Number.isFinite(ts) && ts >= startMs;
    })
    .sort((a, b) => new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime());
  return limit == null ? logs : logs.slice(0, limit);
}

function powerSensorCandidates() {
  const POWER_NAME_HINTS = ["功率", "负载", "power", "watt", "瓦"];
  const POWER_EXCLUDE_HINTS = ["电量", "电费", "能耗", "耗电", "kwh", "wh", "度电", "energy"];
  return candidatesFor("sensor").filter((item) => {
    const unit = String(
      item && (
        item.unit_of_measurement ||
        (item.attributes && item.attributes.unit_of_measurement) ||
        (item.attributes && item.attributes.native_unit_of_measurement)
      ) || ""
    ).trim().toLowerCase();
    const nameText = `${item && item.friendly_name || ""} ${item && item.entity_id || ""}`.toLowerCase();
    const hasPowerUnit = ["w", "kw", "瓦", "千瓦"].includes(unit);
    const looksLikePowerName = POWER_NAME_HINTS.some((keyword) => nameText.includes(keyword));
    const looksLikeEnergyMeter = POWER_EXCLUDE_HINTS.some((keyword) => nameText.includes(keyword));
    const numericState = Number(item && item.state);
    if (looksLikeEnergyMeter && !hasPowerUnit) return false;
    return hasPowerUnit || (looksLikePowerName && Number.isFinite(numericState));
  });
}

function currentAggregatedPowerSummary() {
  const items = state.authError ? [] : powerSensorCandidates();
  const validItems = items
    .map((item) => {
      const unit = item.unit_of_measurement || (item.attributes && item.attributes.unit_of_measurement) || (item.attributes && item.attributes.native_unit_of_measurement) || "";
      const kw = convertPowerValueToKw(item.state, unit);
      return kw != null ? { ...item, kw } : null;
    })
    .filter(Boolean);
  if (!validItems.length) {
    return { kw: null, items: [] };
  }
  return {
    kw: Number(validItems.reduce((sum, item) => sum + item.kw, 0).toFixed(3)),
    items: validItems,
  };
}

function buildEstimatedCumulativeSeries(totalValue, points = 12) {
  const total = Number(totalValue);
  if (!Number.isFinite(total) || total <= 0) return [];
  return Array.from({ length: points }, (_, index) => {
    const progress = (index + 1) / points;
    const curve = Math.pow(progress, 1.08);
    return Number((total * curve).toFixed(3));
  });
}

function getRoom(roomId) {
  return currentRooms().find((item) => item.room_id === roomId) || null;
}

function cloneData(value) {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

function replaceRoomSnapshot(roomId, snapshot) {
  const rooms = currentRooms();
  const index = rooms.findIndex((item) => item && item.room_id === roomId);
  if (index < 0) return false;
  rooms[index] = snapshot;
  return true;
}

function applyOptimisticRoomAction(roomId, action, value) {
  const room = getRoom(roomId);
  if (!room || !room.mapped) return null;
  const snapshot = cloneData(room);
  const nextRoom = cloneData(room);
  const mapped = nextRoom.mapped || {};
  const lights = Array.isArray(mapped.lights) ? mapped.lights : [];

  if (mapped.ac) {
    if (action === "ac_turn_on") {
      mapped.ac.is_on = true;
    } else if (action === "ac_turn_off") {
      mapped.ac.is_on = false;
    } else if (action === "ac_set_temperature") {
      mapped.ac.temperature = Number(value);
    } else if (action === "ac_set_hvac_mode") {
      mapped.ac.hvac_mode = value;
      if (String(value || "").toLowerCase() === "off") {
        mapped.ac.is_on = false;
      } else {
        mapped.ac.is_on = true;
      }
    } else if (action === "ac_set_fan_mode") {
      mapped.ac.fan_mode = value;
    }
  }

  if (mapped.fresh_air) {
    if (action === "fresh_air_turn_on") {
      mapped.fresh_air.is_on = true;
    } else if (action === "fresh_air_turn_off") {
      mapped.fresh_air.is_on = false;
    } else if (action === "fresh_air_set_percentage") {
      mapped.fresh_air.percentage = Number(value);
      mapped.fresh_air.is_on = Number(value) > 0;
    } else if (action === "fresh_air_set_mode") {
      mapped.fresh_air.fan_mode = value;
      if (String(value || "").toLowerCase() !== "off") {
        mapped.fresh_air.is_on = true;
      }
    }
  }

  if (action === "light_toggle" && value && typeof value === "object") {
    const target = lights.find((item) => item && item.entity_id === value.entity_id);
    if (target) {
      target.is_on = Boolean(value.turn_on);
    }
  } else if (action === "light_apply_preset") {
    if (value === "full_on") {
      lights.forEach((item) => {
        if (item) item.is_on = true;
      });
    } else if (value === "full_off") {
      lights.forEach((item) => {
        if (item) item.is_on = false;
      });
    } else if (value === "half_on") {
      const visibleLights = lights.filter(Boolean);
      const cutoff = Math.max(1, Math.ceil(visibleLights.length / 2));
      visibleLights.forEach((item, index) => {
        item.is_on = index < cutoff;
      });
    }
  } else if (action === "light_set_brightness" && value && typeof value === "object") {
    const target = lights.find((item) => item && item.entity_id === value.entity_id);
    if (target) {
      target.is_on = true;
      target.brightness_pct = Number(value.brightness_pct);
    }
  } else if (action === "light_set_color_temperature" && value && typeof value === "object") {
    const target = lights.find((item) => item && item.entity_id === value.entity_id);
    if (target) {
      target.is_on = true;
      target.color_temp_kelvin = Number(value.kelvin);
    }
  } else if (action === "light_set_color" && value && typeof value === "object") {
    const target = lights.find((item) => item && item.entity_id === value.entity_id);
    if (target) {
      target.is_on = true;
      target.rgb_color = Array.isArray(value.rgb_color) ? [...value.rgb_color] : target.rgb_color;
      target.hex_color = value.hex || target.hex_color;
    }
  }

  if (!replaceRoomSnapshot(roomId, nextRoom)) {
    return null;
  }
  return snapshot;
}

function renderOptimisticRoomState() {
  renderAll();
  refreshOpenModalContent();
}

function scheduleActionReload() {
  window.setTimeout(() => {
    reloadAll(false).finally(() => {
      scheduleRefresh();
    });
  }, 80);
}

function roomActionLockKey(roomId, action, value) {
  return `${roomId}::${action}::${JSON.stringify(value ?? null)}`;
}

function displayRoomName(room) {
  if (!room) return "--";
  return (room.matched_group && room.matched_group.display_name) || room.display_name || room.room_name || "--";
}

function tracedFieldValue(source, candidates = [], fallback = null) {
  for (const key of candidates) {
    if (!key) continue;
    const value = source ? source[key] : undefined;
    if (value != null && value !== "" && !(typeof value === "number" && Number.isNaN(value))) {
      return { field: key, value };
    }
  }
  return { field: "", value: fallback };
}

function acCurrentDisplayValue(ac, fallback = 26) {
  return safeNumber(firstFiniteNumber(ac && ac.current_temperature, ac && ac.temperature, fallback) ?? fallback, fallback);
}

function acTargetDisplayValue(ac, fallback = 26) {
  return safeNumber(firstFiniteNumber(ac && ac.temperature, ac && ac.current_temperature, fallback) ?? fallback, fallback);
}

function acDisplaySubtitle(ac) {
  if (!ac || ac.domain !== "climate") {
    return ac ? "开关型空调实体" : "当前未绑定空调";
  }
  return `当前 ${acCurrentDisplayValue(ac, 26)}℃ · 设定 ${acTargetDisplayValue(ac, 26)}℃ · ${hvacModeLabel(ac.hvac_mode || ac.state || "off")}`;
}

function roomCoverageText(room) {
  if (!room) return "--";
  const group = room.matched_group || null;
  const roomNumbers = group && Array.isArray(group.room_numbers) ? group.room_numbers.filter(Boolean) : [];
  if (roomNumbers.length > 1) {
    return roomNumbers.join(", ");
  }
  if (roomNumbers.length === 1) {
    return roomNumbers[0];
  }
  return displayRoomName(room);
}

function roomComputerSummary(room) {
  const online = roomOnlineTerminalCount(room);
  const total = Number(room && room.computer_count || 0);
  if (!total) return "无终端在线数据";
  const labels = uniqueComputerDisplayNames(connectedComputers(room));
  if (labels.length) {
    return labels.length > 1
      ? `在线：${labels.join(" / ")}`
      : `在线：${labels[0]}`;
  }
  return online > 0 ? `${online}/${total} 台在线` : `${total} 台当前离线`;
}

function acStatusSummary(ac) {
  if (!ac) return "未绑定空调";
  if (ac.available === false || ac.exists === false) return "空调离线";
  return ac.is_on ? `运行中 · ${hvacModeLabel(ac.hvac_mode || ac.state || "on")}` : "已关闭";
}

function lightStatusSummary(room, lights) {
  const list = Array.isArray(lights) ? lights.filter(Boolean) : [];
  const total = list.length;
  const on = list.filter((item) => item.is_on).length;
  if (!total) return "未绑定灯光";
  return on > 0 ? `${on}/${total} 盏运行中` : `0/${total} 盏运行中`;
}

function freshAirStatusSummary(fresh) {
  if (!fresh) return "未绑定新风";
  if (fresh.available === false || fresh.exists === false) return "新风离线";
  return fresh.is_on ? `运行中 · ${fresh.state || "--"}` : "已关闭";
}

function acVisualState(ac) {
  if (!ac) return "state-offline";
  if (ac.available === false || ac.exists === false) return "state-offline";
  if (!ac.is_on) return "state-off";
  if (ac.hvac_mode === "heat") return "state-heat";
  if (ac.hvac_mode === "dry") return "state-dry";
  return "state-cool";
}

function lightVisualState(lights) {
  const list = Array.isArray(lights) ? lights : [];
  if (!list.length) return "state-offline";
  const active = list.filter((item) => item && item.available !== false && item.exists !== false);
  if (!active.length) return "state-offline";
  return active.some((item) => item.is_on) ? "state-on" : "state-off";
}

function freshVisualState(fresh) {
  if (!fresh) return "state-offline";
  if (fresh.available === false || fresh.exists === false) return "state-offline";
  return fresh.is_on ? "state-green" : "state-off";
}

function roomControlBadge(label, status) {
  if (status === "offline") return '<span class="badge red">离线</span>';
  if (status === "on") return '<span class="badge green">运行</span>';
  if (status === "warm") return '<span class="badge orange">运行</span>';
  if (status === "idle") return '<span class="badge blue">待机</span>';
  return `<span class="badge">${escapeHtml(label || "--")}</span>`;
}

function renderRoomDevicePanel(title, summary, stateClass, badgeHtml, stats, actions) {
  return `
    <section class="room-device-panel ${escapeHtml(stateClass)} ${stateClass !== "state-off" && stateClass !== "state-offline" ? "active" : ""}">
      <div class="room-device-panel-head">
        <div class="room-device-panel-title">
          <strong>${escapeHtml(title)}</strong>
          <span>${escapeHtml(summary)}</span>
        </div>
        ${badgeHtml || ""}
      </div>
      <div class="room-device-panel-meta">
        ${stats.map((item) => `
          <div class="room-device-panel-stat">
            <label>${escapeHtml(item.label)}</label>
            <strong>${escapeHtml(item.value)}</strong>
          </div>
        `).join("")}
      </div>
      <div class="room-device-panel-actions">${actions}</div>
    </section>
  `;
}

function renderRoomAcPanel(room, ac) {
  if (!ac) {
    return renderRoomDevicePanel(
      "空调",
      "当前未绑定空调实体",
      "state-offline",
      roomControlBadge("未绑定"),
      [
        { label: "状态", value: "未绑定" },
        { label: "模式", value: "--" },
      ],
      `<button class="btn btn-soft" type="button" disabled>未绑定</button>`
    );
  }
  const stateClass = acVisualState(ac);
  const temp = ac.domain === "climate" ? `${acCurrentDisplayValue(ac, 26)}℃` : (ac.is_on ? "ON" : "OFF");
  const modeText = hvacModeLabel(ac.hvac_mode || ac.state || (ac.is_on ? "on" : "off"));
  const badge = ac.available === false || ac.exists === false
    ? roomControlBadge("", "offline")
    : ac.is_on
      ? roomControlBadge("", stateClass === "state-heat" ? "warm" : "on")
      : roomControlBadge("", "idle");
  return renderRoomDevicePanel(
    "空调",
    acStatusSummary(ac),
    stateClass,
    badge,
    [
      { label: "当前", value: temp },
      { label: "模式", value: modeText },
    ],
    [
      compactActionButton("⏻", "开启", `performRoomAction(${JSON.stringify(room.room_id)}, "ac_turn_on")`, "cyan"),
      compactActionButton("○", "关闭", `performRoomAction(${JSON.stringify(room.room_id)}, "ac_turn_off")`, "gray"),
      compactActionButton("☀", "夏季", `performRoomAction(${JSON.stringify(room.room_id)}, "ac_apply_season", "summer", true)`, "orange"),
      compactActionButton("❄", "冬季", `performRoomAction(${JSON.stringify(room.room_id)}, "ac_apply_season", "winter", true)`, "blue"),
    ].join("")
  );
}

function renderRoomLightPanel(room, lights) {
  const total = lights.length;
  const onCount = lights.filter((item) => item && item.is_on).length;
  if (!total) {
    return renderRoomDevicePanel(
      "灯光",
      "当前未绑定灯光实体",
      "state-offline",
      roomControlBadge("未绑定"),
      [
        { label: "亮灯", value: "0 组" },
        { label: "预设", value: "--" },
      ],
      `<button class="btn btn-soft" type="button" disabled>未绑定</button>`
    );
  }
  const stateClass = lightVisualState(lights);
  const badge = lights.every((item) => item.available === false || item.exists === false)
    ? roomControlBadge("", "offline")
    : onCount > 0
      ? roomControlBadge("", "warm")
      : roomControlBadge("", "idle");
  return renderRoomDevicePanel(
    "灯光",
    lightStatusSummary(room, lights),
    stateClass,
    badge,
    [
      { label: "亮灯", value: `${onCount}/${total}` },
      { label: "建议", value: onCount > 0 ? "可调亮度" : "可一键开灯" },
    ],
    [
      compactActionButton("💡", "全开", `performRoomAction(${JSON.stringify(room.room_id)}, "light_apply_preset", "full_on")`, "orange"),
      compactActionButton("◐", "部分开启", `performRoomAction(${JSON.stringify(room.room_id)}, "light_apply_preset", "half_on")`, "blue"),
      compactActionButton("○", "全关", `performRoomAction(${JSON.stringify(room.room_id)}, "light_apply_preset", "full_off")`, "gray"),
    ].join("")
  );
}

function renderRoomFreshPanel(room, fresh) {
  if (!fresh) {
    return renderRoomDevicePanel(
      "新风",
      "当前未绑定新风实体",
      "state-offline",
      roomControlBadge("未绑定"),
      [
        { label: "状态", value: "未绑定" },
        { label: "模式", value: "--" },
      ],
      `<button class="btn btn-soft" type="button" disabled>未绑定</button>`
    );
  }
  const stateClass = freshVisualState(fresh);
  const badge = fresh.available === false || fresh.exists === false
    ? roomControlBadge("", "offline")
    : fresh.is_on
      ? roomControlBadge("", "on")
      : roomControlBadge("", "idle");
  return renderRoomDevicePanel(
    "新风",
    freshAirStatusSummary(fresh),
    stateClass,
    badge,
    [
      { label: "状态", value: fresh.is_on ? "已运行" : "已关闭" },
      { label: "模式", value: fresh.state || "--" },
    ],
    [
      compactActionButton("⏻", "开启", `performRoomAction(${JSON.stringify(room.room_id)}, "fresh_air_turn_on")`, "cyan"),
      compactActionButton("○", "关闭", `performRoomAction(${JSON.stringify(room.room_id)}, "fresh_air_turn_off")`, "gray"),
    ].join("")
  );
}

function renderRoomDeviceSwitch(isOn, handler, tone, disabled = false) {
  if (disabled) {
    return `<button class="suite-room-switch ${escapeHtml(tone)} disabled" type="button" disabled aria-label="不可用"></button>`;
  }
  return `<button class="suite-room-switch ${escapeHtml(tone)} ${isOn ? "on" : ""}" type="button" onclick='${handler}' aria-label="${isOn ? "关闭" : "开启"}"></button>`;
}

function renderRoomComputerStatusIcons(totalCount, onlineCount) {
  const total = Math.max(0, Math.min(Number(totalCount) || 0, 12));
  if (!total) {
    return `<div class="suite-room-pc-status is-empty" aria-label="未配置终端"><span class="suite-room-pc-empty">--</span></div>`;
  }
  return `
    <div class="suite-room-pc-status" aria-label="${escapeHtml(`在线 ${onlineCount}/${total}`)}">
      ${Array.from({ length: total }, (_, index) => `
        <span class="suite-room-pc-dot ${index < onlineCount ? "is-online" : "is-offline"}" title="${index < onlineCount ? "在线" : "离线"}" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="5" width="16" height="11" rx="2"></rect>
            <path d="M8 19h8"></path>
            <path d="M10 16v3"></path>
            <path d="M14 16v3"></path>
          </svg>
        </span>
      `).join("")}
      <span class="suite-room-pc-count">${onlineCount}/${total}</span>
    </div>
  `;
}

function renderRoomPreviewDevice(options) {
  const {
    label,
    icon,
    title,
    subtitle,
    headAccessory = "",
    stateClass = "",
    isOn = false,
    switchTone = "",
    switchHandler = "",
    switchDisabled = false,
  } = options;
  return `
    <div class="suite-room-device ${isOn ? "on" : ""} ${escapeHtml(stateClass)}">
      <div class="suite-room-device-head">
        <div class="suite-room-device-label">
          <span class="suite-room-device-icon">${icon}</span>
          <span>${escapeHtml(label)}</span>
        </div>
        ${headAccessory || renderRoomDeviceSwitch(isOn, switchHandler, switchTone, switchDisabled)}
      </div>
      <div class="suite-room-device-copy">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(subtitle)}</span>
      </div>
    </div>
  `;
}

function renderRoomReferenceCard(room) {
  const inventory = getMappedRoomDevices(room);
  const ac = inventory.ac;
  const lights = inventory.lights;
  const fresh = inventory.freshAir;
  const computers = roomComputers(room);
  const onlinePcCount = connectedComputers(room).length;
  const totalPcCount = Math.max(Number(room && room.computer_count || computers.length || 0), onlinePcCount);
  const onlinePcSummary = onlineComputerSummary(room, 3);
  const acStateClass = ac && ac.is_on
    ? ac.hvac_mode === "heat"
      ? "ac-heat"
      : ac.hvac_mode === "dry"
        ? "ac-dry"
        : "ac-cool"
    : "";
  return `
    <div class="card suite-room-card">
      <div class="suite-room-header">
        <div class="suite-room-title">
          <div class="suite-room-title-row">
            <span class="suite-room-mark">🏠</span>
            <div class="suite-room-name">${escapeHtml(displayRoomName(room))}</div>
          </div>
          <div class="suite-room-sub">${escapeHtml(room.entry_title)} · ${escapeHtml(roomCoverageText(room))}</div>
        </div>
        <div class="suite-room-badges">
          ${roomChip(room)}
          ${onlinePcCount ? '<span class="badge green">电脑在线</span>' : '<span class="badge blue">电脑待机</span>'}
        </div>
      </div>
      <div class="suite-room-devices">
        ${renderRoomPreviewDevice({
          label: "电脑",
          icon: "💻",
          title: onlinePcSummary || roomComputerSummary(room),
          subtitle: onlinePcCount ? `${onlinePcCount} 台在线终端` : "当前没有在线电脑",
          headAccessory: renderRoomComputerStatusIcons(totalPcCount, onlinePcCount),
          isOn: onlinePcCount > 0,
        })}
        ${renderRoomPreviewDevice({
          label: "灯光",
          icon: "💡",
          title: lightStatusSummary(room, lights),
          subtitle: lights.length ? "支持全开、部分开启、全关" : "当前未绑定灯光",
          stateClass: "light",
          isOn: lights.some((item) => item && item.is_on),
          switchTone: "light",
          switchHandler: lights.length ? `performRoomAction(${JSON.stringify(room.room_id)}, "light_apply_preset", ${JSON.stringify(lights.some((item) => item && item.is_on) ? "full_off" : "full_on")})` : "",
          switchDisabled: !lights.length,
        })}
        ${renderRoomPreviewDevice({
          label: "空调",
          icon: "❄",
          title: acStatusSummary(ac),
          subtitle: acDisplaySubtitle(ac),
          stateClass: acStateClass,
          isOn: Boolean(ac && ac.is_on),
          switchTone: "ac",
          switchHandler: ac ? `performRoomAction(${JSON.stringify(room.room_id)}, ${JSON.stringify(ac.is_on ? "ac_turn_off" : "ac_turn_on")})` : "",
          switchDisabled: !ac,
        })}
        ${renderRoomPreviewDevice({
          label: "新风",
          icon: "🌿",
          title: freshAirStatusSummary(fresh),
          subtitle: fresh ? `模式 ${fresh.state || "--"}` : "当前未绑定新风",
          stateClass: "fresh",
          isOn: Boolean(fresh && fresh.is_on),
          switchTone: "fresh",
          switchHandler: fresh ? `performRoomAction(${JSON.stringify(room.room_id)}, ${JSON.stringify(fresh.is_on ? "fresh_air_turn_off" : "fresh_air_turn_on")})` : "",
          switchDisabled: !fresh,
        })}
      </div>
      <div class="suite-room-footer">
        <button class="suite-room-detail" type="button" onclick='openRoomStatusModal(${JSON.stringify(room.room_id)})'>查看详情</button>
      </div>
    </div>
  `;
}

function renderRoomRuntimeItem(title, summary, actions, tone = "") {
  return `
    <div class="room-runtime-item${tone ? ` ${tone}` : ""}">
      <div class="room-runtime-copy">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(summary)}</span>
      </div>
      <div class="room-runtime-actions">${actions}</div>
    </div>
  `;
}

function describeAction(action, value) {
  if (action === "ac_turn_on") return "空调已开启";
  if (action === "ac_turn_off") return "空调已关闭";
  if (action === "fresh_air_turn_on") return "新风已开启";
  if (action === "fresh_air_turn_off") return "新风已关闭";
  if (action === "fresh_air_set_percentage") return `新风风量已设为 ${value}%`;
  if (action === "fresh_air_set_mode") return `新风档位已切换为 ${value}`;
  if (action === "ac_apply_season") {
    if (value === "winter") return "已切换到冬季模式";
    if (value === "custom") return "已切换到自定义模式";
    return "已切换到夏季模式";
  }
  if (action === "light_apply_preset") {
    if (value === "full_on") return "灯光全开";
    if (value === "half_on") return "灯光部分开启";
    if (value === "full_off") return "灯光全关";
  }
  if (action === "light_toggle" && value && typeof value === "object") {
    return value.turn_on ? "单灯已开启" : "单灯已关闭";
  }
  if (action === "light_set_color_temperature" && value && typeof value === "object") {
    return value.kelvin ? `色温已设为 ${value.kelvin}K` : "灯光色温已更新";
  }
  if (action === "light_set_color" && value && typeof value === "object") {
    return value.hex ? `颜色已设为 ${value.hex}` : "灯光颜色已更新";
  }
  return "动作已执行";
}

function compactActionIcon(icon, title, handler, type = "secondary") {
  return `<button class="btn btn-${type} icon-action" type="button" title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}" onclick='${handler}'>${icon}</button>`;
}

function compactActionButton(icon, label, handler, tone = "gray") {
  return `<button class="mini-action ${tone}" type="button" onclick='${handler}' title="${escapeHtml(label)}"><span>${icon}</span><span>${escapeHtml(label)}</span></button>`;
}

function capsuleToggle(isOn, onHandler, offHandler, tone = "blue") {
  const handler = isOn ? offHandler : onHandler;
  return `
    <button class="capsule-toggle ${isOn ? `on ${tone}` : ""}" type="button" onclick='${handler}' aria-label="${isOn ? "关闭" : "开启"}"></button>
    <span class="capsule-toggle-label">${isOn ? "开" : "关"}</span>
  `;
}

function openRoomDetailPage(roomId, page) {
  state.currentRoomId = roomId;
  switchPage(page || "room", document.querySelector(`.nav-item[data-page="${page || "room"}"]`));
  renderAll();
}

function closeStatusModal(event) {
  if (event && event.target && event.target.id && event.target.id !== "statusModal") return;
  const modal = document.getElementById("statusModal");
  const modalCard = document.getElementById("statusModalCard");
  const modalHead = document.getElementById("statusModalHead");
  if (modalCard) {
    modalCard.classList.remove("room-sample-modal");
    modalCard.classList.remove("light-control-modal");
  }
  if (modalHead) {
    modalHead.style.display = "";
  }
  state.modalContext = null;
  if (modal) modal.classList.remove("show");
}

function openStatusModal(title, html, options = {}) {
  const modal = document.getElementById("statusModal");
  const modalTitle = document.getElementById("statusModalTitle");
  const modalBody = document.getElementById("statusModalBody");
  const modalCard = document.getElementById("statusModalCard");
  const modalHead = document.getElementById("statusModalHead");
  if (!modal || !modalTitle || !modalBody) return;
  if (modalCard) {
    modalCard.classList.remove("room-sample-modal");
    modalCard.classList.remove("light-control-modal");
    const variants = Array.isArray(options.variant) ? options.variant : [options.variant];
    for (const variant of variants.filter(Boolean)) {
      modalCard.classList.add(String(variant));
    }
  }
  if (modalHead) {
    modalHead.style.display = options.hideHeader ? "none" : "";
  }
  modalTitle.textContent = title || "详细状态";
  modalBody.innerHTML = html || "";
  modal.classList.add("show");
}

function buildEntityMatchModalHtml(items, emptyText = "当前没有匹配结果。", description = "") {
  const list = uniqueEntityOptions(items);
  if (!list.length) {
    return `<div class="status-modal-empty">${escapeHtml(emptyText)}</div>`;
  }
  const note = description ? `${description} 共匹配 ${list.length} 个实体。` : `共匹配 ${list.length} 个实体。`;
  return `
    <div class="status-modal-section">
      <div class="status-modal-note">${escapeHtml(note)}</div>
      <div class="status-modal-list">
        ${list.map((item) => `
          <div class="status-modal-item">
            <span>${escapeHtml(entityDisplayName(item))}</span>
            <strong>${escapeHtml(item.entity_id)}</strong>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function openEntityMatchModal(title, items, emptyText = "当前没有匹配结果。", description = "") {
  openStatusModal(title || "匹配详情", buildEntityMatchModalHtml(items, emptyText, description));
}

function modalToggle(isOn, handler, tone, disabled = false) {
  if (disabled) {
    return `<button class="status-modal-toggle ${escapeHtml(tone)} disabled" type="button" disabled aria-label="不可用"></button>`;
  }
  return `<button class="status-modal-toggle ${escapeHtml(tone)} ${isOn ? "on" : ""}" type="button" onclick='${handler}' aria-label="${isOn ? "关闭" : "开启"}"></button>`;
}

function roomModalTimeText() {
  return new Date().toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function roomModalDateText() {
  return new Date().toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  });
}

function roomSampleActionButton(label, handler, tone = "white", icon = "") {
  return `
    <button class="room-sample-btn ${escapeHtml(tone)}" type="button" onclick='${handler}'>
      ${icon ? `<span class="room-sample-btn-icon">${escapeHtml(icon)}</span>` : ""}
      <span>${escapeHtml(label)}</span>
    </button>
  `;
}

function roomSampleToggle(isOn, handler, tone = "", disabled = false) {
  if (disabled) {
    return `<button class="room-sample-toggle ${escapeHtml(tone)} disabled" type="button" disabled aria-label="不可用"></button>`;
  }
  return `<button class="room-sample-toggle ${escapeHtml(tone)} ${isOn ? "on" : ""}" type="button" onclick='${handler}' aria-label="${isOn ? "关闭" : "开启"}'></button>`;
}

function roomSampleStatusDot(active) {
  return `<span class="room-sample-status-dot ${active ? "on" : ""}"></span>`;
}

function roomSampleDeviceIcon(kind) {
  if (kind === "ac") return "❄";
  if (kind === "light") return "💡";
  if (kind === "fan") return "🌀";
  if (kind === "computer") return "💻";
  return "•";
}

function roomSampleAcModeTag(roomId, ac, mode) {
  const active = String(mode) === String(ac && ac.hvac_mode || "");
  const tone = active && mode === "cool" ? "cool" : active && mode === "heat" ? "heat" : "";
  return `
    <button class="room-sample-mode-tag ${active ? `is-active ${tone}` : ""}" type="button" onclick='setAcHvacMode(${JSON.stringify(roomId)}, ${JSON.stringify(mode)})'>
      ${escapeHtml(hvacModeLabel(mode))}
    </button>
  `;
}

function roomSampleAcPresetButton(roomId, value, current) {
  return `
    <button class="room-sample-temp-preset ${Number(current) === Number(value) ? "is-active" : ""}" type="button" onclick='performRoomAction(${JSON.stringify(roomId)}, "ac_set_temperature", ${Number(value)})'>
      ${escapeHtml(String(value))}°
    </button>
  `;
}

function roomSampleFreshSpeedButton(roomId, mode, currentMode) {
  const active = String(mode || "") === String(currentMode || "");
  return `
    <button class="room-sample-speed-btn ${active ? "is-active" : ""}" type="button" onclick='performRoomAction(${JSON.stringify(roomId)}, "fresh_air_set_mode", ${JSON.stringify(mode)})'>
      <div class="room-sample-speed-icon">${escapeHtml(uiModeLabel(mode).slice(0, 1) || "•")}</div>
      <div class="room-sample-speed-name">${escapeHtml(uiModeLabel(mode))}</div>
    </button>
  `;
}

function renderRoomSampleComputerCard(room, computers, onlineComputers) {
  const labels = uniqueComputerDisplayNames(onlineComputers);
  return `
    <div class="room-sample-device-card terminal ${onlineComputers.length ? "is-active" : ""}">
      <div class="room-sample-status-bar"></div>
      <div class="room-sample-card-head">
        <div class="room-sample-card-info">
          <div class="room-sample-card-icon">${roomSampleDeviceIcon("computer")}</div>
          <div class="room-sample-card-label">
            <h3>在线终端</h3>
            <span>${escapeHtml(onlineComputers.length ? `${onlineComputers.length}/${computers.length || 0} 台在线` : "当前没有在线终端")}</span>
          </div>
        </div>
        <div class="room-sample-card-meta">${escapeHtml(`${onlineComputers.length}/${computers.length || 0}`)}</div>
      </div>
      <div class="room-sample-card-content">
        <div class="room-sample-status-row">
          <div class="room-sample-status-item">
            ${roomSampleStatusDot(onlineComputers.length > 0)}
            <span>${onlineComputers.length ? "有终端在线" : "当前无在线终端"}</span>
          </div>
          <div class="room-sample-status-side">
            <span>${roomOnlineTerminalCount(room) > 0 ? "当前有人" : "当前空闲"}</span>
          </div>
        </div>
        <div class="room-sample-terminal-grid">
          ${labels.length ? labels.map((label) => {
            const computer = onlineComputers.find((item) => computerDisplayName(item) === label) || null;
            return `
              <div class="room-sample-terminal-item is-on">
                <strong>${escapeHtml(label)}</strong>
                <span>${escapeHtml(computer && (computer.ip_address || computer.entity_id) || "--")}</span>
                <em>在线</em>
              </div>
            `;
          }).join("") : `<div class="room-sample-empty">${escapeHtml(computers.length ? "当前没有在线终端。" : "当前包厢没有识别到终端实体。")}</div>`}
        </div>
      </div>
    </div>
  `;
}

function getRoomLightEntity(roomId, entityId) {
  const room = getRoom(roomId);
  const lights = room ? getMappedRoomDevices(room).lights : [];
  const light = lights.find((item) => item && item.entity_id === entityId) || null;
  return { room, light };
}

function renderRoomSampleLightItem(roomId, light) {
  return `
    <div class="room-sample-light-item ${light && light.is_on ? "is-on" : ""}">
      <div class="room-sample-light-main">
        <div class="room-sample-light-info">
          <div class="room-sample-light-icon">${roomSampleDeviceIcon("light")}</div>
          <div class="room-sample-light-copy">
            <span class="room-sample-light-name">${escapeHtml(lightUiName(light))}</span>
            <span class="room-sample-light-meta">
              ${escapeHtml(
                light && light.available === false || light && light.exists === false
                  ? "当前离线"
                  : light && light.is_on
                    ? "已开启"
                    : "已关闭"
              )}
            </span>
          </div>
        </div>
        <div class="room-sample-light-controls">
          ${roomSampleToggle(
            Boolean(light && light.is_on),
            `performRoomAction(${JSON.stringify(roomId)}, "light_toggle", ${JSON.stringify({ entity_id: light && light.entity_id, turn_on: !(light && light.is_on) })})`,
            "light",
            !light
          )}
          <button class="room-sample-light-detail-btn" type="button" onclick='openLightControlModal(${JSON.stringify(roomId)}, ${JSON.stringify(light && light.entity_id)})'>
            调节
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderRoomSampleLightClusterButton(roomId, light) {
  const unavailable = Boolean(light && (light.available === false || light.exists === false));
  const isOn = Boolean(light && light.is_on);
  const stateClass = unavailable ? "offline" : (isOn ? "on" : "off");
  const stateText = unavailable ? "离线" : (isOn ? "已开" : "已关");
  return `
    <button
      class="room-sample-light-cluster-btn ${stateClass}"
      type="button"
      onclick='performRoomAction(${JSON.stringify(roomId)}, "light_toggle", ${JSON.stringify({ entity_id: light && light.entity_id, turn_on: !(light && light.is_on) })})'
      ${unavailable ? "disabled" : ""}
    >
      <span class="room-sample-light-cluster-name">${escapeHtml(lightUiName(light))}</span>
      <span class="room-sample-light-cluster-state">${escapeHtml(stateText)}</span>
    </button>
  `;
}

function renderRoomSampleLightCluster(roomId, lights, lightOnCount) {
  return `
    <div class="room-sample-device-card ${lightOnCount ? "is-active light" : ""}" id="roomSampleLightCard">
      <div class="room-sample-status-bar"></div>
      <div class="room-sample-card-head">
        <div class="room-sample-card-info">
          <div class="room-sample-card-icon">${roomSampleDeviceIcon("light")}</div>
          <div class="room-sample-card-label">
            <h3>灯光集合开关</h3>
            <span>${escapeHtml(lightStatusSummary(null, lights))}</span>
          </div>
        </div>
        ${roomSampleToggle(lightOnCount > 0, lights.length ? `performRoomAction(${JSON.stringify(roomId)}, "light_apply_preset", ${JSON.stringify(lightOnCount ? "full_off" : "full_on")})` : "", "light", !lights.length)}
      </div>
      <div class="room-sample-card-content light-cluster">
        <div class="room-sample-status-row">
          <div class="room-sample-status-item">
            ${roomSampleStatusDot(lightOnCount > 0)}
            <span>${lightOnCount > 0 ? "灯光运行中" : "全部待机中"}</span>
          </div>
          <div class="room-sample-status-side">
            <span>${escapeHtml(`${lightOnCount}/${lights.length || 0}`)}</span>
          </div>
        </div>
        ${lights.length ? `
          <div class="room-sample-light-scene-row">
            <button class="room-sample-light-scene-btn primary" type="button" onclick='performRoomAction(${JSON.stringify(roomId)}, "light_apply_preset", "full_on")'>全部开灯</button>
            <button class="room-sample-light-scene-btn" type="button" onclick='performRoomAction(${JSON.stringify(roomId)}, "light_apply_preset", "half_on")'>部分开启</button>
            <button class="room-sample-light-scene-btn danger" type="button" onclick='performRoomAction(${JSON.stringify(roomId)}, "light_apply_preset", "full_off")'>全部关灯</button>
          </div>
          <div class="room-sample-light-cluster-grid">
            ${lights.map((light) => renderRoomSampleLightClusterButton(roomId, light)).join("")}
          </div>
        ` : `<div class="room-sample-empty">当前包厢没有识别到灯光实体。</div>`}
      </div>
    </div>
  `;
}

function buildLightControlModalHtml(roomId, entityId) {
  const { room, light } = getRoomLightEntity(roomId, entityId);
  if (!room || !light) {
    return `<div class="status-modal-empty">未找到当前灯光实体。</div>`;
  }
  const pct = light && light.brightness_pct != null ? Math.round(Number(light.brightness_pct) || 0) : (light && light.is_on ? 100 : 0);
  const kelvin = lightColorTemperatureKelvin(light);
  const currentHex = lightCurrentColorHex(light);
  const capabilities = lightControlCapabilities(light);
  const tempRange = lightColorTemperatureRange(light);
  const tempOptions = capabilities.canColorTemp ? lightColorTemperatureOptions(light) : [];
  const colorOptions = capabilities.canColor ? lightColorPresets() : [];
  const statusText = light && light.available === false || light && light.exists === false
    ? "离线"
    : light && light.is_on
      ? "运行中"
      : "已关闭";
  const tone = light && light.available === false || light && light.exists === false
    ? "offline"
    : light && light.is_on
      ? (capabilities.canColorTemp ? lightColorTemperatureTone(kelvin) : "warm")
      : "sleep";
  return `
    <div class="apple-light-modal">
      <div class="apple-light-hero ${escapeHtml(tone)} ${light && light.is_on ? "is-on" : ""}">
        <div class="apple-light-hero-copy">
          <span class="apple-light-kicker">Light Control</span>
          <h3>${escapeHtml(lightUiName(light))}</h3>
          <p>${escapeHtml(displayRoomName(room))} · ${escapeHtml(statusText)}</p>
        </div>
        <div class="apple-light-hero-actions">
          <button
            class="apple-light-power ${light && light.is_on ? "on" : ""}"
            type="button"
            onclick='performRoomAction(${JSON.stringify(roomId)}, "light_toggle", ${JSON.stringify({ entity_id: light.entity_id, turn_on: !light.is_on })})'
            ${light && (light.available === false || light.exists === false) ? "disabled" : ""}
          >${light && light.is_on ? "关闭" : "开启"}</button>
          <button class="apple-light-close" type="button" onclick="closeStatusModal()">×</button>
        </div>
      </div>

      <div class="apple-light-panel ${light && light.is_on ? "is-on" : ""}">
        <div class="apple-light-summary-row">
          <div class="apple-light-summary-pill">
            <span>所在包厢</span>
            <strong>${escapeHtml(displayRoomName(room))}</strong>
          </div>
          <div class="apple-light-summary-pill">
            <span>当前状态</span>
            <strong>${escapeHtml(statusText)}</strong>
          </div>
          <div class="apple-light-summary-pill">
            <span>支持能力</span>
            <strong>${escapeHtml([
              capabilities.canDim ? "亮度" : "",
              capabilities.canColorTemp ? "色温" : "",
              capabilities.canColor ? "颜色" : "",
            ].filter(Boolean).join(" / ") || "开关")}</strong>
          </div>
        </div>

        ${capabilities.canDim ? `
          <div class="apple-light-control-block">
            <div class="apple-light-control-head">
              <div><h4>亮度</h4></div>
              <strong>${escapeHtml(`${pct}%`)}</strong>
            </div>
            <div class="apple-light-range-shell">
              <div class="apple-light-range-fill warm" style="width:${Math.max(0, Math.min(100, pct))}%;"></div>
              <input class="apple-light-range" type="range" min="1" max="100" value="${Math.max(1, pct || 1)}" onchange='setLightBrightness(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, this.value)'>
            </div>
          </div>
        ` : ""}

        ${capabilities.canColorTemp ? `
          <div class="apple-light-control-block">
            <div class="apple-light-control-head">
              <div><h4>色温</h4></div>
              <strong class="tone-${escapeHtml(lightColorTemperatureTone(kelvin))}">${kelvin != null ? `${escapeHtml(String(kelvin))}K` : "--"}</strong>
            </div>
            <div class="apple-light-range-shell tone-${escapeHtml(lightColorTemperatureTone(kelvin))}">
              <div class="apple-light-range-fill tone" style="width:${Math.max(0, Math.min(100, Math.round(((Number(kelvin || tempRange.min) - tempRange.min) / Math.max(tempRange.max - tempRange.min, 1)) * 100)))}%;"></div>
              <input class="apple-light-range" type="range" min="${Math.round(tempRange.min)}" max="${Math.round(tempRange.max)}" step="50" value="${Math.round(kelvin || tempRange.min)}" onchange='setLightColorTemperature(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, this.value)'>
            </div>
            <div class="apple-light-preset-row">
              ${tempOptions.map((item) => `
                <button
                  class="apple-light-preset ${kelvin != null && Math.abs(kelvin - item.kelvin) <= 220 ? "is-active" : ""}"
                  type="button"
                  onclick='setLightColorTemperature(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, ${Number(item.kelvin)})'
                >${escapeHtml(item.label)}</button>
              `).join("")}
            </div>
          </div>
        ` : ""}

        ${capabilities.canColor ? `
          <div class="apple-light-control-block">
            <div class="apple-light-control-head">
              <div><h4>颜色</h4></div>
              <strong>${escapeHtml(currentHex ? currentHex.toUpperCase() : "预设")}</strong>
            </div>
            <div class="apple-light-color-preset-row">
              ${colorOptions.map((item) => {
                const active = currentHex && normalizeHexColor(currentHex) === normalizeHexColor(item.value);
                return `
                  <button
                    class="apple-light-color-preset ${active ? "is-active" : ""}"
                    type="button"
                    style="--swatch:${escapeHtml(item.value)};"
                    onclick='setLightColor(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, ${JSON.stringify(item.value)})'
                    aria-label="${escapeHtml(item.label)}"
                    title="${escapeHtml(item.label)}"
                  ></button>
                `;
              }).join("")}
            </div>
          </div>
        ` : ""}

        ${!capabilities.canDim && !capabilities.canColorTemp && !capabilities.canColor ? `
          <div class="apple-light-inline-note">当前灯具仅支持开关控制，没有额外的亮度、色温或颜色能力。</div>
        ` : ""}
      </div>
    </div>
  `;
}

function openLightControlModal(roomId, entityId) {
  const { room, light } = getRoomLightEntity(roomId, entityId);
  if (!room || !light) {
    showMessage("未找到当前灯光实体。", "warning", true);
    return;
  }
  state.modalContext = { type: "light", roomId, entityId };
  openStatusModal(
    `${lightUiName(light)} · 详细控制`,
    buildLightControlModalHtml(roomId, entityId),
    { variant: "light-control-modal", hideHeader: true }
  );
}

async function openPowerEstimateModal() {
  const energy = currentResolvedEnergySummary();
  const configuredEntityId = energy && energy.realtime_power && energy.realtime_power.entity_id;
  const realtimeEntity = energy && energy.realtime_power ? energy.realtime_power : null;
  const aggregatedItems = energy && Array.isArray(energy.aggregated_power_entities) ? energy.aggregated_power_entities : [];
  const items = state.authError ? [] : aggregatedItems;
  const visibleItems = items.length
    ? items
    : (realtimeEntity ? [realtimeEntity] : []);
  const body = `
    <div class="status-modal-single">
      <div class="status-modal-section">
        <h4>功率实体列表</h4>
        ${energy && energy.realtime_power_kw != null ? `<div class="status-modal-note">当前汇总功率：${formatMetricNumber(energy.realtime_power_kw, 2)} kW${items.length > 1 ? `，共 ${items.length} 个实体` : ""}</div>` : ""}
        ${visibleItems.length ? `
          <div class="status-modal-list">
            ${visibleItems.map((item) => {
            const unit = item.unit_of_measurement || (item.attributes && item.attributes.unit_of_measurement);
            const currentKw = convertPowerValueToKw(item.state, item.unit_of_measurement || (item.attributes && item.attributes.unit_of_measurement));
            return `
              <div class="status-modal-item">
                <span>${escapeHtml(item.friendly_name || item.entity_id)}${item.entity_id === configuredEntityId ? " · 当前绑定" : ""}</span>
                <strong>${currentKw != null ? `${formatMetricNumber(currentKw, 2)} kW` : `${escapeHtml(String(item.state || "--"))}${unit ? ` ${escapeHtml(String(unit))}` : ""}`}</strong>
              </div>
            `;
          }).join("")}
          </div>
        ` : `<div class="status-modal-empty">当前没有可读取的功率实体。</div>`}
      </div>
      <div class="status-modal-note">${state.authError ? "当前为只读模式，无法读取完整实体清单；这里只展示首页已绑定或已返回的功率信息。" : "这里列出当前可识别的功率实体，带“当前绑定”的就是首页用来计算负载与电耗的来源。"}</div>
    </div>
  `;
  openStatusModal("当前估算负载 · 功率实体", body);
}

function drawMetricTrendChart(canvas, values, labels, accent = "#2563eb") {
  if (!canvas) return;
  const rect = canvas.parentElement.getBoundingClientRect();
  const width = Math.max(Math.round(rect.width), 320);
  const height = Math.max(Math.round(rect.height), 200);
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";
  const ctx = canvas.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);
  const rows = Array.isArray(values) ? values.map(Number).filter((item) => Number.isFinite(item)) : [];
  if (!rows.length) return;
  const pad = { top: 16, right: 16, bottom: 34, left: 44 };
  const chartWidth = width - pad.left - pad.right;
  const chartHeight = height - pad.top - pad.bottom;
  const max = Math.max(...rows, 1);
  const min = Math.min(...rows, 0);
  const range = Math.max(max - min, 0.01);
  ctx.strokeStyle = "rgba(15,23,42,.08)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = pad.top + (chartHeight / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
  }
  const coords = rows.map((value, index) => {
    const x = pad.left + (chartWidth / Math.max(rows.length - 1, 1)) * index;
    const y = pad.top + chartHeight - ((value - min) / range) * chartHeight;
    return { x, y, value };
  });
  const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartHeight);
  gradient.addColorStop(0, accent + "55");
  gradient.addColorStop(1, accent + "08");
  ctx.beginPath();
  ctx.moveTo(coords[0].x, coords[0].y);
  for (let i = 1; i < coords.length; i += 1) {
    const prev = coords[i - 1];
    const current = coords[i];
    const cpX = (prev.x + current.x) / 2;
    ctx.bezierCurveTo(cpX, prev.y, cpX, current.y, current.x, current.y);
  }
  ctx.lineTo(coords[coords.length - 1].x, pad.top + chartHeight);
  ctx.lineTo(coords[0].x, pad.top + chartHeight);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(coords[0].x, coords[0].y);
  for (let i = 1; i < coords.length; i += 1) {
    const prev = coords[i - 1];
    const current = coords[i];
    const cpX = (prev.x + current.x) / 2;
    ctx.bezierCurveTo(cpX, prev.y, cpX, current.y, current.x, current.y);
  }
  ctx.strokeStyle = accent;
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = accent;
  for (const point of coords) {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = "rgba(100,116,139,.88)";
  ctx.font = "11px Consolas, monospace";
  ctx.textAlign = "center";
  const labelItems = Array.isArray(labels) && labels.length === rows.length ? labels : rows.map((_, index) => String(index + 1));
  const step = Math.max(1, Math.ceil(labelItems.length / 6));
  coords.forEach((point, index) => {
    if (index % step !== 0 && index !== coords.length - 1) return;
    ctx.fillText(String(labelItems[index]), point.x, height - 8);
  });
}

async function openEnergyCostModal(period = "day") {
  const energy = currentResolvedEnergySummary();
  const modalTitle = period === "month" ? "月累计电费趋势" : "日累计电费趋势";
  const summaryValue = period === "month" ? energy && energy.monthly_cost_effective : energy && energy.daily_cost_effective;
  const summaryKwh = period === "month" ? energy && energy.monthly_energy_kwh_effective : energy && energy.daily_energy_kwh_effective;
  const source = period === "month" ? energy && energy.monthly_source : energy && energy.daily_source;
  openStatusModal(modalTitle, `<div class="status-modal-empty">正在生成趋势图...</div>`);
  const modalBody = document.getElementById("statusModalBody");
  if (!modalBody) return;
  const entityId = energy && energy.realtime_power && energy.realtime_power.entity_id;
  const unit = energy && energy.realtime_power && (energy.realtime_power.unit_of_measurement || (energy.realtime_power.attributes && energy.realtime_power.attributes.unit_of_measurement)) || "";
  const endIso = new Date().toISOString();
  const startIso = period === "month" ? startOfMonthIso() : startOfTodayIso();
  let values = [];
  let labels = [];
  try {
    if (entityId && !state.authError) {
      const history = await requestRawJson(`/api/history/period/${encodeURIComponent(startIso)}?filter_entity_id=${encodeURIComponent(entityId)}&end_time=${encodeURIComponent(endIso)}`);
      const rows = Array.isArray(history) ? history[0] || [] : [];
      const startMs = new Date(startIso).getTime();
      const endMs = new Date(endIso).getTime();
      const normalized = rows
        .map((row) => {
          const ts = new Date(row.last_changed || row.last_updated || row.lu || "").getTime();
          const kw = convertPowerValueToKw(row.state, unit);
          return Number.isFinite(ts) && kw != null ? { ts, kw } : null;
        })
        .filter(Boolean)
        .sort((a, b) => a.ts - b.ts);
      if (normalized.length) {
        const bucketCount = period === "month" ? Math.min(15, Math.max(new Date().getDate(), 2)) : 12;
        const bucketSize = (endMs - startMs) / bucketCount;
        let runningKwh = 0;
        let pointer = {
          ts: Math.max(startMs, normalized[0].ts),
          kw: normalized[0].kw,
        };
        let rowIndex = 1;
        for (let bucket = 1; bucket <= bucketCount; bucket += 1) {
          const bucketEnd = bucket === bucketCount ? endMs : Math.min(endMs, startMs + bucketSize * bucket);
          while (rowIndex < normalized.length && normalized[rowIndex].ts <= bucketEnd) {
            const current = normalized[rowIndex];
            const segmentEnd = Math.min(current.ts, bucketEnd);
            if (segmentEnd > pointer.ts) {
              runningKwh += pointer.kw * ((segmentEnd - pointer.ts) / 3600000);
            }
            pointer = {
              ts: Math.max(pointer.ts, Math.min(current.ts, bucketEnd)),
              kw: current.kw,
            };
            rowIndex += 1;
          }
          if (bucketEnd > pointer.ts) {
            runningKwh += pointer.kw * ((bucketEnd - pointer.ts) / 3600000);
            pointer.ts = bucketEnd;
          }
          const cost = energy && energy.price_per_kwh != null ? runningKwh * Number(energy.price_per_kwh) : runningKwh;
          values.push(Number(cost.toFixed(2)));
          const pointDate = new Date(bucketEnd);
          labels.push(period === "month"
            ? `${pointDate.getMonth() + 1}/${pointDate.getDate()}`
            : `${String(pointDate.getHours()).padStart(2, "0")}:00`);
        }
      }
    }
  } catch (error) {
  }
  if (!values.length) {
    values = buildEstimatedCumulativeSeries(summaryValue, period === "month" ? 10 : 12);
    labels = values.map((_, index) => period === "month" ? `D${index + 1}` : `T${index + 1}`);
  }
  modalBody.innerHTML = `
    <div class="status-modal-meta">
      <div class="status-modal-stat"><span>累计电费</span><strong>${summaryValue != null ? `¥ ${formatMetricNumber(summaryValue, 2)}` : "--"}</strong></div>
      <div class="status-modal-stat"><span>累计电耗</span><strong>${summaryKwh != null ? `${formatMetricNumber(summaryKwh, 2)} kWh` : "--"}</strong></div>
      <div class="status-modal-stat"><span>数据来源</span><strong>${source === "entity" ? "实体累计" : source === "history" ? "功率历史积分" : source === "estimate" ? "当前功率估算" : "未读取"}</strong></div>
    </div>
    <div class="status-modal-chart">
      <canvas id="energyCostTrendChart"></canvas>
    </div>
    ${state.authError ? `<div class="status-modal-note">当前为只读模式，未请求需要授权的历史接口，折线图使用当前累计值生成的估算趋势。</div>` : ""}
  `;
  drawMetricTrendChart(document.getElementById("energyCostTrendChart"), values, labels, period === "month" ? "#0f8f8c" : "#2563eb");
}

function roomSmartInlineToggle(isOn, handler, tone = "", disabled = false) {
  if (disabled) {
    return `<button class="room-hub-toggle ${escapeHtml(tone)} disabled" type="button" disabled aria-label="不可用"></button>`;
  }
  return `<button class="room-hub-toggle ${escapeHtml(tone)} ${isOn ? "on" : ""}" type="button" onclick='event.preventDefault(); event.stopPropagation(); ${handler}' aria-label="${isOn ? "关闭" : "开启"}'></button>`;
}

function roomHubIcon(kind) {
  const icons = {
    ac: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18M3 12h18M6.5 6.5l11 11M17.5 6.5l-11 11"/></svg>',
    light: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/></svg>',
    fresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4c1.2 0 2.3.48 3.1 1.26A4.36 4.36 0 0 1 16.36 8H12"/><path d="M20 12a4 4 0 0 1-4 4h-1.5"/><path d="M12 20a4 4 0 0 1-4-4V14.5"/><path d="M4 12a4 4 0 0 1 4-4h1.5"/></svg>',
    terminal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>',
    room: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/></svg>',
  };
  return icons[kind] || icons.room;
}

function roomSmartDetailsSummary(title, subtitle = "展开调节") {
  return `
    <summary class="room-smart-details-summary">
      <div>
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(subtitle)}</span>
      </div>
      <span class="room-smart-details-arrow">⌄</span>
    </summary>
  `;
}

function renderRoomSmartAcPanel(roomId, ac, acTargetTemp, acCurrentTemp) {
  const unavailable = Boolean(ac && (ac.available === false || ac.exists === false));
  const isClimate = Boolean(ac && ac.domain === "climate");
  const hvacMode = ac ? (ac.hvac_mode || ac.state || "off") : "off";
  const isOn = ac && ac.is_on;

  const hvacModes = isClimate
    ? Array.from(new Set((Array.isArray(ac.hvac_modes) ? ac.hvac_modes : ["cool", "heat", "auto", "dry", "fan_only"]).filter(Boolean)))
    : [];
  const fanModes = isClimate
    ? Array.from(new Set((Array.isArray(ac.fan_modes) ? ac.fan_modes : []).filter(Boolean)))
    : [];

  const activeMode = hvacModes.includes(hvacMode) ? hvacMode : (hvacModes[0] || "");
  const activeFanMode = fanModes.includes(ac && ac.fan_mode) ? ac.fan_mode : (fanModes[0] || "");

  const modeIcon = (m) => {
    if (m === "cool") return "❄️";
    if (m === "heat") return "☀️";
    if (m === "dry") return "💧";
    if (m === "fan_only") return "🌀";
    return "⚙️";
  };

  return `
    <section class="ac-card-premium ${isOn ? "is-active" : ""} ${unavailable ? "is-offline" : ""} ${isOn ? `is-${hvacMode}` : ""}" id="roomSmartAcCard">
      <div class="ac-card-header-new">
        <div class="ac-card-info-group">
          <div class="ac-card-icon-box">❄️</div>
          <div class="ac-card-title-stack">
            <h3>空调系统</h3>
            <p>${unavailable ? "设备已离线" : isOn ? `${hvacModeLabel(hvacMode)}中` : "待机状态"}</p>
          </div>
        </div>
        ${roomSmartInlineToggle(Boolean(isOn), ac ? `performRoomAction(${JSON.stringify(roomId)}, ${JSON.stringify(isOn ? "ac_turn_off" : "ac_turn_on")})` : "", "ac", !ac || unavailable)}
      </div>

      <div class="ac-card-gauge-area">
        <div class="ac-temp-main-display">
          <span class="ac-temp-label">Target</span>
          <div class="ac-temp-value-big">${acTargetTemp != null ? escapeHtml(String(acTargetTemp)) : "--"}<small style="font-size:24px; vertical-align:super; font-weight:700;">°</small></div>
          <div class="ac-temp-room-info">${acCurrentTemp != null ? `室温 ${escapeHtml(String(acCurrentTemp))}℃` : "室温检测中"}</div>
        </div>

        <div class="ac-stepper-overlay">
          <button class="ac-step-btn-new" type="button" onclick='shiftAcTemperature(${JSON.stringify(roomId)}, -1)' ${isOn && !unavailable ? "" : "disabled"}>−</button>
          <button class="ac-step-btn-new" type="button" onclick='shiftAcTemperature(${JSON.stringify(roomId)}, 1)' ${isOn && !unavailable ? "" : "disabled"}>+</button>
        </div>
      </div>

      <div class="ac-controls-bottom">
        ${isOn && hvacModes.length ? `
          <div class="ac-mode-selector-grid">
            ${hvacModes.map((m) => `
              <button class="ac-mode-btn-new ${m === activeMode ? "is-active" : ""}" type="button" onclick='setAcHvacMode(${JSON.stringify(roomId)}, ${JSON.stringify(m)})' ${unavailable ? "disabled" : ""}>
                <span class="icon">${modeIcon(m)}</span>
                <span class="label">${hvacModeLabel(m)}</span>
              </button>
            `).join("")}
          </div>
        ` : ""}

        ${isOn && isClimate ? `
          <div class="ac-settings-row">
            ${fanModes.length ? `
              <div class="ac-setting-field">
                <label>风速调节</label>
                <select class="ac-custom-select" onchange='setAcFanMode(${JSON.stringify(roomId)}, this.value)' ${unavailable ? "disabled" : ""}>
                  ${fanModes.map((m) => `<option value="${escapeHtml(m)}" ${String(m) === String(activeFanMode) ? "selected" : ""}>${escapeHtml(uiModeLabel(m))}</option>`).join("")}
                </select>
              </div>
            ` : ""}
            <div class="ac-setting-field">
              <label>智能风向</label>
              <select class="ac-custom-select" disabled><option>自动摆风</option></select>
            </div>
          </div>
        ` : ""}
      </div>
    </section>
  `;
}

function renderRoomSmartLightItem(roomId, light) {
  const capabilities = lightControlCapabilities(light);
  const hasControls = Boolean(capabilities.canDim || capabilities.canColorTemp || capabilities.canColor);
  const unavailable = Boolean(light && (light.available === false || light.exists === false));
  const isOn = Boolean(light && light.is_on);
  const pct = light && light.brightness_pct != null ? Math.round(Number(light.brightness_pct) || 0) : (isOn ? 100 : 0);
  const kelvin = lightColorTemperatureKelvin(light);
  const tempOptions = capabilities.canColorTemp ? lightColorTemperatureOptions(light) : [];
  const colorOptions = capabilities.canColor ? lightColorPresets() : [];
  const currentHex = normalizeHexColor(lightCurrentColorHex(light) || "");
  const summary = `
    <div class="room-hub-light-copy">
      <div class="room-hub-light-icon">${roomHubIcon("light")}</div>
      <div class="room-hub-light-text">
        <strong>${escapeHtml(lightUiName(light))}</strong>
        <span>${escapeHtml(
          unavailable
            ? "离线"
            : isOn
              ? (capabilities.canDim ? `亮度 ${pct}%` : "已开启")
              : "已关闭"
        )}</span>
      </div>
    </div>
    <div class="room-hub-light-actions">
      ${roomSmartInlineToggle(
        isOn,
        `performRoomAction(${JSON.stringify(roomId)}, "light_toggle", ${JSON.stringify({ entity_id: light && light.entity_id, turn_on: !isOn })})`,
        "light",
        unavailable
      )}
      ${hasControls ? `<span class="room-hub-chevron">⌄</span>` : ""}
    </div>
  `;
  if (!hasControls) {
    return `
      <div class="room-hub-light-card ${isOn ? "is-on" : ""} ${unavailable ? "is-offline" : ""}">
        <div class="room-hub-light-summary static">${summary}</div>
      </div>
    `;
  }
  return `
    <details class="room-hub-light-card ${isOn ? "is-on" : ""} ${unavailable ? "is-offline" : ""}">
      <summary class="room-hub-light-summary">
        ${summary}
      </summary>
      <div class="room-hub-light-body">
        ${capabilities.canDim ? `
          <label class="room-hub-range-block">
            <div class="room-hub-range-head">
              <span>亮度</span>
              <strong>${escapeHtml(`${pct}%`)}</strong>
            </div>
            <input type="range" min="1" max="100" value="${Math.max(1, pct || 1)}" onchange='setLightBrightness(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, this.value)' ${unavailable ? "disabled" : ""}>
          </label>
        ` : ""}
        ${capabilities.canColorTemp ? `
          <div class="room-hub-subsection">
            <div class="room-hub-range-head">
              <span>色温</span>
              <strong>${kelvin != null ? `${escapeHtml(String(kelvin))}K` : "--"}</strong>
            </div>
            <div class="room-hub-chip-row">
              ${tempOptions.map((item) => `
                <button
                  class="room-hub-chip ${kelvin != null && Math.abs(kelvin - item.kelvin) <= 220 ? "is-active" : ""}"
                  type="button"
                  onclick='setLightColorTemperature(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, ${Number(item.kelvin)})'
                  ${unavailable ? "disabled" : ""}
                >${escapeHtml(item.label)}</button>
              `).join("")}
            </div>
          </div>
        ` : ""}
        ${capabilities.canColor ? `
          <div class="room-hub-subsection">
            <div class="room-hub-range-head">
              <span>颜色</span>
              <strong>${escapeHtml((currentHex || "#ffffff").toUpperCase())}</strong>
            </div>
            <div class="room-hub-color-row">
              ${colorOptions.map((item) => `
                <button
                  class="room-hub-color-dot ${currentHex === normalizeHexColor(item.value) ? "is-active" : ""}"
                  type="button"
                  style="--swatch:${escapeHtml(item.value)};"
                  onclick='setLightColor(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, ${JSON.stringify(item.value)})'
                  title="${escapeHtml(item.label)}"
                  aria-label="${escapeHtml(item.label)}"
                  ${unavailable ? "disabled" : ""}
                ></button>
              `).join("")}
            </div>
          </div>
        ` : ""}
      </div>
    </details>
  `;
}

function renderRoomSmartLightsPanel(roomId, lights) {
  const onCount = lights.filter((item) => item && item.is_on).length;
  return `
    <section class="hub-card-premium room-hub-panel-light ${onCount ? "is-active" : ""}" id="roomSmartLightCard">
      <div class="ac-card-header-new">
        <div class="ac-card-info-group">
          <div class="ac-card-icon-box" style="${onCount ? "background:#ca8a04; color:#fff;" : ""}">💡</div>
          <div class="ac-card-title-stack">
            <h3>照明控制</h3>
            <p>${lights.length ? `${onCount}/${lights.length} 盏已开启` : "暂未检测到灯光"}</p>
          </div>
        </div>
      </div>
      <div class="ac-controls-bottom" style="padding-top:20px;">
        ${lights.length
          ? `<div class="room-hub-lights-grid">${lights.map((light) => renderRoomSmartLightItem(roomId, light)).join("")}</div>`
          : `<div class="room-hub-empty">当前包厢没有识别到灯光实体。</div>`}
      </div>
    </section>
  `;
}


function renderRoomSmartFreshPanel(roomId, fresh) {
  const unavailable = Boolean(fresh && (fresh.available === false || fresh.exists === false));
  const currentMode = fresh ? (fresh.preset_mode || fresh.state || "") : "";
  const modeText = fresh ? uiModeLabel(currentMode || "--") : "--";
  const isOn = fresh && fresh.is_on;

  return `
    <section class="fresh-card-premium ${isOn ? "is-active" : ""} ${unavailable ? "is-offline" : ""}" id="roomSmartFreshCard">
      <div class="ac-card-header-new" style="padding:0; border:none; background:transparent;">
        <div class="ac-card-info-group">
          <div class="ac-card-icon-box" style="${isOn ? "background:#22c55e; color:#fff; box-shadow:0 8px 16px -4px rgba(34,197,94,0.4);" : ""}">🌀</div>
          <div class="ac-card-title-stack">
            <h3>新风系统</h3>
            <p>${unavailable ? "设备已离线" : isOn ? "空气循环中" : "待机中"}</p>
          </div>
        </div>
        ${roomSmartInlineToggle(Boolean(isOn), fresh ? `performRoomAction(${JSON.stringify(roomId)}, ${JSON.stringify(isOn ? "fresh_air_turn_off" : "fresh_air_turn_on")})` : "", "fresh", !fresh || unavailable)}
      </div>

      <div class="room-hub-fresh-shell" style="background:#fff; border:1px solid rgba(15,23,42,0.05); padding:20px; border-radius:20px;">
        <div class="room-hub-fresh-main">
          <span class="room-hub-micro-label">Indoor Air Quality</span>
          <strong style="font-size:32px; display:block; margin:8px 0;">${isOn ? "Excellent" : "Stopped"}</strong>
          <small style="display:block; color:#64748b;">${isOn ? "包厢内空气清新，持续净化中" : "开启新风系统以改善室内空气"}</small>
        </div>
        <div class="room-hub-meta-row" style="margin-top:16px; justify-content:flex-start;">
          <span class="room-hub-meta-pill">模式: ${escapeHtml(modeText)}</span>
          <span class="room-hub-meta-pill">HEPA Filter Active</span>
        </div>
      </div>
    </section>
  `;
}




function suiteControlToggle(isOn, handler, tone = "", disabled = false) {
  if (disabled) {
    return `<button class="suite-control-switch ${escapeHtml(tone)} disabled" type="button" disabled aria-label="不可用"></button>`;
  }
  return `<button class="suite-control-switch ${escapeHtml(tone)} ${isOn ? "on" : ""}" type="button" onclick='event.preventDefault(); event.stopPropagation(); ${handler}' aria-label="${isOn ? "关闭" : "开启"}'></button>`;
}

function suiteControlDisclosure(title, subtitle = "展开调节") {
  return `
    <summary class="suite-control-disclosure-summary">
      <div class="suite-control-disclosure-copy">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(subtitle)}</span>
      </div>
      <span class="suite-control-disclosure-arrow">⌄</span>
    </summary>
  `;
}

function renderSuiteClimatePanel(roomId, ac, targetTemp, currentTemp) {
  const unavailable = Boolean(ac && (ac.available === false || ac.exists === false));
  const isClimate = Boolean(ac && ac.domain === "climate");
  const hvacMode = ac ? (ac.hvac_mode || ac.state || "off") : "off";
  const hvacModes = isClimate
    ? Array.from(new Set((Array.isArray(ac.hvac_modes) ? ac.hvac_modes : ["cool", "heat", "auto", "dry", "fan_only"]).filter(Boolean)))
    : [];
  const activeMode = hvacModes.includes(hvacMode) ? hvacMode : (hvacModes[0] || "");
  const statusText = !ac
    ? "未绑定空调"
    : unavailable
      ? "设备离线"
      : ac.is_on
        ? hvacModeLabel(hvacMode)
        : "已关闭";
  return `
    <section class="suite-control-panel climate ${ac && ac.is_on ? "is-active" : ""} ${unavailable ? "is-offline" : ""}">
      <div class="suite-control-panel-head">
        <div class="suite-control-panel-title">
          <span>Climate</span>
          <h3>空调面板</h3>
        </div>
        ${suiteControlToggle(Boolean(ac && ac.is_on), ac ? `performRoomAction(${JSON.stringify(roomId)}, ${JSON.stringify(ac.is_on ? "ac_turn_off" : "ac_turn_on")})` : "", "climate", !ac || unavailable)}
      </div>
      ${ac ? `
        <div class="suite-control-climate-core">
          <div class="suite-control-temp-stage">
            <span class="suite-control-temp-kicker">设定温度</span>
            <strong>${targetTemp != null ? `${escapeHtml(String(targetTemp))}°` : "--"}</strong>
            <span class="suite-control-temp-room">${currentTemp != null ? `室温 ${escapeHtml(String(currentTemp))}℃` : "室温 --"}</span>
          </div>
          <div class="suite-control-temp-buttons">
            <button class="suite-control-step" type="button" onclick='shiftAcTemperature(${JSON.stringify(roomId)}, -1)' ${isClimate && !unavailable ? "" : "disabled"}>-</button>
            <button class="suite-control-step" type="button" onclick='shiftAcTemperature(${JSON.stringify(roomId)}, 1)' ${isClimate && !unavailable ? "" : "disabled"}>+</button>
          </div>
        </div>
        ${isClimate ? `
          <div class="suite-control-mode-wrap">
            <label class="suite-control-field single">
              <span>模式</span>
              <select onchange='setAcHvacMode(${JSON.stringify(roomId)}, this.value)' ${unavailable ? "disabled" : ""}>
                ${hvacModes.map((mode) => `<option value="${escapeHtml(mode)}" ${String(mode) === String(activeMode) ? "selected" : ""}>${escapeHtml(hvacModeLabel(mode))}</option>`).join("")}
              </select>
            </label>
          </div>
        ` : `<div class="suite-control-note">当前空调实体只支持开关控制。</div>`}
      ` : `<div class="suite-control-empty">当前包厢没有可控制的空调实体。</div>`}
    </section>
  `;
}

function renderSuiteFreshPanel(roomId, fresh) {
  const unavailable = Boolean(fresh && (fresh.available === false || fresh.exists === false));
  const currentMode = fresh ? (fresh.preset_mode || fresh.state || "") : "";
  const modeText = fresh ? uiModeLabel(currentMode || "--") : "--";
  const statusText = !fresh
    ? "未绑定新风"
    : unavailable
      ? "设备离线"
      : fresh.is_on
        ? "运行中"
        : "已关闭";
  return `
    <section class="suite-control-panel fresh ${fresh && fresh.is_on ? "is-active" : ""} ${unavailable ? "is-offline" : ""}">
      <div class="suite-control-panel-head">
        <div class="suite-control-panel-title">
          <span>Fresh Air</span>
          <h3>新风面板</h3>
        </div>
        ${suiteControlToggle(Boolean(fresh && fresh.is_on), fresh ? `performRoomAction(${JSON.stringify(roomId)}, ${JSON.stringify(fresh.is_on ? "fresh_air_turn_off" : "fresh_air_turn_on")})` : "", "fresh", !fresh || unavailable)}
      </div>
      ${fresh ? `
        <div class="suite-control-fresh-core">
          <div class="suite-control-fresh-stage">
            <span class="suite-control-temp-kicker">当前状态</span>
            <strong>${escapeHtml(statusText)}</strong>
            <span class="suite-control-temp-room">${escapeHtml(statusText)}</span>
          </div>
        </div>
        <div class="suite-control-note">${escapeHtml(fresh.domain === "fan" && currentMode ? `当前档位：${modeText}。新风面板已改为开关控制。` : "当前新风实体只保留开关控制。")}</div>
      ` : `<div class="suite-control-empty">当前包厢没有可控制的新风实体。</div>`}
    </section>
  `;
}

function renderSuiteLightItem(roomId, light) {
  const unavailable = Boolean(light && (light.available === false || light.exists === false));
  const isOn = Boolean(light && light.is_on);
  const capabilities = lightControlCapabilities(light);
  const hasControls = Boolean(capabilities.canDim || capabilities.canColorTemp || capabilities.canColor);
  const pct = light && light.brightness_pct != null ? Math.round(Number(light.brightness_pct) || 0) : (isOn ? 100 : 0);
  const kelvin = lightColorTemperatureKelvin(light);
  const currentHex = normalizeHexColor(lightCurrentColorHex(light) || "");
  const tempOptions = capabilities.canColorTemp ? lightColorTemperatureOptions(light) : [];
  const colorOptions = capabilities.canColor ? lightColorPresets() : [];
  const summary = `
    <div class="suite-control-light-head-left">
      <div class="suite-control-light-mark ${isOn ? "is-on" : ""}"></div>
      <div class="suite-control-light-copy">
        <strong>${escapeHtml(lightUiName(light))}</strong>
        <span>${escapeHtml(unavailable ? "离线" : isOn ? (capabilities.canDim ? `亮度 ${pct}%` : "已开启") : "已关闭")}</span>
      </div>
    </div>
    <div class="suite-control-light-head-right">
      ${suiteControlToggle(
        isOn,
        `performRoomAction(${JSON.stringify(roomId)}, "light_toggle", ${JSON.stringify({ entity_id: light && light.entity_id, turn_on: !isOn })})`,
        "light",
        unavailable
      )}
      ${hasControls ? `<span class="suite-control-light-arrow">⌄</span>` : ""}
    </div>
  `;
  if (!hasControls) {
    return `
      <div class="suite-control-light-card ${isOn ? "is-on" : ""} ${unavailable ? "is-offline" : ""}">
        <div class="suite-control-light-summary static">${summary}</div>
      </div>
    `;
  }
  return `
    <details class="suite-control-light-card ${isOn ? "is-on" : ""} ${unavailable ? "is-offline" : ""}">
      <summary class="suite-control-light-summary">
        ${summary}
      </summary>
      <div class="suite-control-light-body">
        ${capabilities.canDim ? `
          <label class="suite-control-slider-block">
            <div class="suite-control-slider-head">
              <span>亮度</span>
              <strong>${escapeHtml(`${pct}%`)}</strong>
            </div>
            <input type="range" min="1" max="100" value="${Math.max(1, pct || 1)}" onchange='setLightBrightness(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, this.value)' ${unavailable ? "disabled" : ""}>
          </label>
        ` : ""}
        ${capabilities.canColorTemp ? `
          <div class="suite-control-light-section">
            <div class="suite-control-slider-head">
              <span>色温</span>
              <strong>${kelvin != null ? `${escapeHtml(String(kelvin))}K` : "--"}</strong>
            </div>
            <div class="suite-control-pill-row">
              ${tempOptions.map((item) => `
                <button
                  class="suite-control-pill ${kelvin != null && Math.abs(kelvin - item.kelvin) <= 220 ? "is-active" : ""}"
                  type="button"
                  onclick='setLightColorTemperature(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, ${Number(item.kelvin)})'
                  ${unavailable ? "disabled" : ""}
                >${escapeHtml(item.label)}</button>
              `).join("")}
            </div>
          </div>
        ` : ""}
        ${capabilities.canColor ? `
          <div class="suite-control-light-section">
            <div class="suite-control-slider-head">
              <span>颜色</span>
              <strong>${escapeHtml((currentHex || "#ffffff").toUpperCase())}</strong>
            </div>
            <div class="suite-control-color-row">
              ${colorOptions.map((item) => `
                <button
                  class="suite-control-color ${currentHex === normalizeHexColor(item.value) ? "is-active" : ""}"
                  type="button"
                  style="--swatch:${escapeHtml(item.value)};"
                  onclick='setLightColor(${JSON.stringify(roomId)}, ${JSON.stringify(light.entity_id)}, ${JSON.stringify(item.value)})'
                  title="${escapeHtml(item.label)}"
                  aria-label="${escapeHtml(item.label)}"
                  ${unavailable ? "disabled" : ""}
                ></button>
              `).join("")}
            </div>
          </div>
        ` : ""}
      </div>
    </details>
  `;
}

function renderSuiteLightsPanel(roomId, lights) {
  const onCount = lights.filter((item) => item && item.is_on).length;
  return `
    <section class="suite-control-panel lights ${onCount ? "is-active" : ""}">
      <div class="suite-control-panel-head lights-head">
        <div class="suite-control-panel-title">
          <span>Lighting</span>
          <h3>灯光控制</h3>
        </div>
        <div class="suite-control-panel-meta">${escapeHtml(lights.length ? `${onCount}/${lights.length} 开启` : "未绑定")}</div>
      </div>
      <div class="suite-control-lights-body">
        ${lights.length
          ? `<div class="suite-control-light-list">${lights.map((light) => renderSuiteLightItem(roomId, light)).join("")}</div>`
          : `<div class="suite-control-empty">当前包厢没有识别到灯光实体。</div>`}
      </div>
    </section>
  `;
}

function buildRoomStatusModalHtml(roomId) {
  const room = getRoom(roomId);
  if (!room) return `<div class="status-modal-empty">未找到当前包厢。</div>`;
  const inventory = getMappedRoomDevices(room);
  const ac = inventory.ac;
  const lights = inventory.lights;
  const fresh = inventory.freshAir;
  
  const acTargetTemp = ac && ac.domain === "climate"
    ? Number(firstFiniteNumber(ac.temperature, ac.current_temperature, 26) ?? 26)
    : null;
  const acCurrentTemp = ac && ac.domain === "climate"
    ? Number(firstFiniteNumber(ac.current_temperature, ac.temperature, 26) ?? 26)
    : null;
    
  const computers = roomComputers(room);
  const onlineComputers = connectedComputers(room);
  const connectedCount = onlineComputers.length;
  const totalComputers = Number(room && room.computer_count || computers.length || 0);
  const onlineTerminalSummary = onlineComputerSummary(room, 3);
  const onlineTerminalStat = onlineTerminalSummary || (totalComputers > 0 ? "当前无在线终端" : "未配置终端");
  const roomName = displayRoomName(room);
  
  const statCards = [
    { icon: "🖥️", tone: "blue", label: "终端", value: onlineTerminalStat, exists: true },
    { icon: "🌡️", tone: "blue", label: "当前温", value: acCurrentTemp != null ? `${acCurrentTemp}℃` : "--", exists: !!ac },
    { icon: "💡", tone: "amber", label: "灯光", value: `${lights.filter(l => l.is_on).length}/${lights.length}`, exists: lights.length > 0 },
    { icon: "🌬️", tone: "green", label: "新风", value: fresh && fresh.is_on ? "运行中" : "待机", exists: !!fresh }
  ].filter(c => c.exists);

  return `
    <div class="room-hub-modal">
      <div class="room-hub-hero">
        <div class="room-hub-hero-copy">
          <h2>${escapeHtml(roomName)}</h2>
          <p>
            <span class="status-dot ${connectedCount > 0 ? "online" : ""}"></span>
            ${connectedCount > 0 ? `${onlineTerminalSummary} 在线` : "当前空闲"}
            ${totalComputers > 0 ? ` · 共 ${totalComputers} 台终端` : ""}
          </p>
        </div>
        <button class="room-hub-close" type="button" onclick="closeStatusModal()">×</button>
      </div>

      <div class="room-hub-stats">
        ${statCards.map(item => `
          <div class="room-hub-stat ${item.tone}">
            <div class="room-hub-stat-icon">${item.icon}</div>
            <div class="room-hub-stat-copy">
              <span>${item.label}</span>
              <strong>${item.value}</strong>
            </div>
          </div>
        `).join("")}
      </div>

      <div class="room-hub-sections" style="${!ac || (!fresh && !lights.length) ? "grid-template-columns: 1fr;" : ""}">
        ${ac ? `
        <!-- Main Control: AC -->
        <div class="hub-card-unified ac-control ${ac && ac.is_on ? "is-active" : ""} ${ac ? `is-${ac.hvac_mode || "off"}` : ""}">
          <div class="hub-card-unified-head">
            <div class="hub-card-unified-title">
              <div class="icon">❄️</div>
              <h3>空调系统</h3>
            </div>
            <button class="hub-switch blue ${ac && ac.is_on ? "is-on" : ""}" 
              onclick='performRoomAction(${JSON.stringify(roomId)}, "${ac && ac.is_on ? "ac_turn_off" : "ac_turn_on"}")'></button>
          </div>
          
          <div class="ac-unified-display">
            <div class="ac-unified-temp-circle">
              <span>SET TEMP</span>
              <strong>${acTargetTemp != null ? acTargetTemp : "--"}°</strong>
              <span>${acCurrentTemp != null ? `ROOM ${acCurrentTemp}℃` : "---"}</span>
            </div>
            <div class="ac-unified-steppers">
              <button class="ac-unified-btn" onclick='shiftAcTemperature(${JSON.stringify(roomId)}, -1)' ${ac && ac.is_on ? "" : "disabled"}>−</button>
              <button class="ac-unified-btn" onclick='shiftAcTemperature(${JSON.stringify(roomId)}, 1)' ${ac && ac.is_on ? "" : "disabled"}>+</button>
            </div>
          </div>

          <div class="ac-unified-modes">
            ${(ac && ac.hvac_modes || ["cool", "heat", "fan_only", "off"]).map(m => `
              <div class="ac-mode-pill ${ac && ac.hvac_mode === m ? "is-active" : ""}" 
                onclick='setAcHvacMode(${JSON.stringify(roomId)}, ${JSON.stringify(m)})'>
                ${hvacModeLabel(m)}
              </div>
            `).join("")}
          </div>
        </div>
        ` : ""}

        ${(fresh || lights.length) ? `
        <!-- Secondary Controls: Lights & Fresh Air -->
        <div style="display: flex; flex-direction: column; gap: 20px;">
          ${fresh ? `
          <!-- Fresh Air Card -->
          <div class="hub-card-unified">
            <div class="hub-card-unified-head">
              <div class="hub-card-unified-title">
                <div class="icon">🌬️</div>
                <h3>新风系统</h3>
              </div>
              <button class="hub-switch ${fresh && fresh.is_on ? "is-on" : ""}" 
                onclick='performRoomAction(${JSON.stringify(roomId)}, "${fresh && fresh.is_on ? "fresh_air_turn_off" : "fresh_air_turn_on"}")'></button>
            </div>
            <div class="unified-device-list">
              <div class="unified-device-item ${fresh && fresh.is_on ? "is-active" : ""}">
                <div class="unified-device-info">
                  <div class="unified-device-icon">🍃</div>
                  <div class="unified-device-text">
                    <strong>循环模式</strong>
                    <span>${fresh ? uiModeLabel(fresh.preset_mode || fresh.state || "normal") : "未检测到设备"}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          ` : ""}
          ${lights.length ? `
          <!-- Lights Card -->
          <div class="hub-card-unified">
            <div class="hub-card-unified-head">
              <div class="hub-card-unified-title">
                <div class="icon">💡</div>
                <h3>灯光管理</h3>
              </div>
            </div>
            <div class="unified-device-list">
              ${lights.map(light => `
                <div class="unified-device-item ${light.is_on ? "is-active" : ""}">
                  <div class="unified-device-info">
                    <div class="unified-device-icon">💡</div>
                    <div class="unified-device-text">
                      <strong>${escapeHtml(lightUiName(light))}</strong>
                      <span>${light.is_on ? (light.brightness_pct ? `亮度 ${light.brightness_pct}%` : "已开启") : "已关闭"}</span>
                    </div>
                  </div>
                  <button class="hub-switch ${light.is_on ? "is-on" : ""}" 
                    onclick='performRoomAction(${JSON.stringify(roomId)}, "light_toggle", ${JSON.stringify({ entity_id: light.entity_id, turn_on: !light.is_on })})'></button>
                </div>
              `).join("")}
            </div>
          </div>
          ` : ""}
        </div>
        ` : ""}
      </div>
    </div>
  `;
}

function openRoomStatusModal(roomId) {
  const room = getRoom(roomId);
  state.modalContext = { type: "room", roomId };
  openStatusModal(
    room ? `${displayRoomName(room)} · 实体控制` : "实体控制",
    buildRoomStatusModalHtml(roomId),
    { variant: "room-sample", hideHeader: true }
  );
}

function refreshOpenModalContent() {
  if (!state.modalContext) return;
  if (state.modalContext.type === "room") {
    const room = getRoom(state.modalContext.roomId);
    if (!room) {
      closeStatusModal();
      return;
    }
    openStatusModal(
      `${displayRoomName(room)} · 实体控制`,
      buildRoomStatusModalHtml(state.modalContext.roomId),
      { variant: "room-sample", hideHeader: true }
    );
    return;
  }
  if (state.modalContext.type === "light") {
    const { room, light } = getRoomLightEntity(state.modalContext.roomId, state.modalContext.entityId);
    if (!room || !light) {
      closeStatusModal();
      return;
    }
    openStatusModal(
      `${lightUiName(light)} · 详细控制`,
      buildLightControlModalHtml(state.modalContext.roomId, state.modalContext.entityId),
      { variant: "light-control-modal", hideHeader: true }
    );
    return;
  }
  if (state.modalContext.type === "ac") {
    const room = getRoom(state.modalContext.roomId);
    const ac = room && getMappedRoomDevices(room).ac;
    if (!room || !ac) {
      closeStatusModal();
      return;
    }
    openStatusModal(
      `${displayRoomName(room)} · 空调控制`,
      buildAcControlModalHtml(state.modalContext.roomId)
    );
    return;
  }
  if (state.modalContext.type === "fresh") {
    const room = getRoom(state.modalContext.roomId);
    const fresh = room && getMappedRoomDevices(room).freshAir;
    if (!room || !fresh) {
      closeStatusModal();
      return;
    }
    openStatusModal(
      `${displayRoomName(room)} · 新风控制`,
      buildFreshAirControlModalHtml(state.modalContext.roomId)
    );
  }
}

function buildIssueDetailModalHtml(issueKey) {
  const summary = summarizeRooms(roomsForDisplay());
  const rooms = summary.rooms || [];
  let targetRooms = [];
  let title = "详细状态";
  if (issueKey === "offline") {
    title = "设备离线详情";
    targetRooms = rooms.filter((room) => {
      const devices = getMappedRoomDevices(room);
      return Boolean(
        (devices.ac && (devices.ac.available === false || devices.ac.exists === false)) ||
        devices.lights.some((item) => item.available === false || item.exists === false) ||
        (devices.freshAir && (devices.freshAir.available === false || devices.freshAir.exists === false))
      );
    });
  } else if (issueKey === "mapping") {
    title = "未完成映射详情";
    targetRooms = rooms.filter((room) => roomNeedsMappingAttention(room));
  } else if (issueKey === "occupied") {
    title = "当前有人包厢详情";
    targetRooms = rooms.filter((room) => roomOnlineTerminalCount(room) > 0);
  } else if (issueKey === "online_terminals") {
    title = "在线终端详情";
    targetRooms = rooms.filter((room) => connectedComputers(room).length > 0);
  }

  return {
    title,
    html: targetRooms.length ? `
      <div class="status-modal-section">
        <div class="status-modal-list">
          ${targetRooms.map((room) => `
            <div class="status-modal-item">
              <span>${escapeHtml(displayRoomName(room))}</span>
              <strong>${escapeHtml(
                issueKey === "online_terminals"
                  ? uniqueComputerDisplayNames(connectedComputers(room)).join("、")
                  : issueKey === "occupied"
                    ? roomComputerSummary(room)
                    : roomCoverageText(room)
              )}</strong>
            </div>
          `).join("")}
        </div>
      </div>
    ` : `<div class="status-modal-empty">当前没有需要处理的内容。</div>`,
  };
}

function openIssueDetailModal(issueKey) {
  const detail = buildIssueDetailModalHtml(issueKey);
  openStatusModal(detail.title, detail.html);
}

function lightSupportsBrightness(light) {
  if (!light) return false;
  const attrs = light.attributes || {};
  const colorModes = Array.isArray(light.supported_color_modes)
    ? light.supported_color_modes
    : (Array.isArray(attrs.supported_color_modes) ? attrs.supported_color_modes : []);
  if (colorModes.some((mode) => String(mode || "").toLowerCase() !== "onoff")) return true;
  const supportedFeatures = Number(light.supported_features != null ? light.supported_features : attrs.supported_features || 0);
  return Boolean(supportedFeatures & 1) || light.brightness_pct != null || attrs.brightness != null;
}

function freshAirPresetModes(fresh) {
  if (!fresh) return [];
  const attrs = fresh.attributes || {};
  const modes = Array.isArray(fresh.preset_modes)
    ? fresh.preset_modes
    : (Array.isArray(attrs.preset_modes) ? attrs.preset_modes : []);
  return modes.filter(Boolean);
}

function normalizeSceneModeToken(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, "");
}

function matchFreshAirPresetMode(fresh, targetLevel) {
  const modes = freshAirPresetModes(fresh);
  if (!modes.length) return "";
  const aliases = {
    low: ["low", "slow", "silent", "sleep", "eco", "一级", "1档", "低档", "低速", "低风"],
    medium: ["medium", "mid", "middle", "normal", "auto", "二级", "2档", "中档", "中速", "中风", "标准"],
    high: ["high", "strong", "turbo", "boost", "max", "三级", "3档", "高档", "高速", "高风", "强劲"],
  };
  const wanted = aliases[targetLevel] || [];
  const matched = modes.find((mode) => {
    const token = normalizeSceneModeToken(mode);
    return wanted.some((alias) => token.includes(normalizeSceneModeToken(alias)));
  });
  if (matched) return matched;
  if (targetLevel === "low") return modes[0];
  if (targetLevel === "high") return modes[modes.length - 1];
  return modes[Math.floor((modes.length - 1) / 2)] || modes[0];
}

async function requestPanelRoomAction(roomId, action, value, persist = false) {
  await requestJson("/api/netcafe/panel/room/action", {
    method: "POST",
    body: JSON.stringify({
      room_id: roomId,
      action,
      value,
      persist: Boolean(persist),
    }),
  });
}

async function applySceneLightsForRoom(room, brightnessPct, presetFallback = "half_on") {
  const lights = room && room.mapped && Array.isArray(room.mapped.lights) ? room.mapped.lights.filter(Boolean) : [];
  if (!lights.length) return;
  if (brightnessPct <= 0) {
    await requestPanelRoomAction(room.room_id, "light_apply_preset", "full_off");
    return;
  }
  const dimmableLights = lights.filter((light) => String(light.entity_id || "").startsWith("light.") && lightSupportsBrightness(light));
  if (presetFallback) {
    await requestPanelRoomAction(room.room_id, "light_apply_preset", presetFallback);
  }
  for (const light of dimmableLights) {
    await requestPanelRoomAction(room.room_id, "light_set_brightness", {
      entity_id: light.entity_id,
      brightness_pct: brightnessPct,
    });
  }
}

function sceneSeasonForRoom(roomId) {
  const roomConfig = currentRoomConfig(roomId);
  const season = roomConfig && roomConfig.modes ? roomConfig.modes.selected_season : "summer";
  return ["summer", "winter", "custom"].includes(season) ? season : "summer";
}

async function applySceneAcForRoom(room, options = {}) {
  const ac = room && room.mapped ? room.mapped.ac : null;
  if (!ac) return;
  if (options.power === "off") {
    await requestPanelRoomAction(room.room_id, "ac_turn_off");
    return;
  }
  if (options.power === "on" && !ac.is_on) {
    await requestPanelRoomAction(room.room_id, "ac_turn_on");
  }
  if (ac.domain !== "climate") return;
  const season = sceneSeasonForRoom(room.room_id);
  await requestPanelRoomAction(room.room_id, "ac_apply_season", season);
  const targetTemperature = options.temperature != null ? Number(options.temperature) : null;
  if (targetTemperature != null && Number.isFinite(targetTemperature)) {
    await requestPanelRoomAction(room.room_id, "ac_set_temperature", targetTemperature);
  }
}

async function applySceneFreshAirForRoom(room, options = {}) {
  const fresh = room && room.mapped ? room.mapped.fresh_air : null;
  if (!fresh) return;
  if (options.power === "off") {
    await requestPanelRoomAction(room.room_id, "fresh_air_turn_off");
    return;
  }
  await requestPanelRoomAction(room.room_id, "fresh_air_turn_on");
  const presetMode = matchFreshAirPresetMode(fresh, options.level);
  if (presetMode && String(fresh.entity_id || "").startsWith("fan.")) {
    await requestPanelRoomAction(room.room_id, "fresh_air_set_mode", presetMode);
  }
}

function dashboardSceneDefinitions() {
  return {
    internet: {
      title: "上网模式",
      success: "场景模式：上网模式已执行。",
      lightBrightness: 80,
      lightPreset: "full_on",
      ac: { power: "on", temperature: 24 },
      freshAir: { power: "on", level: "medium" },
    },
    movie: {
      title: "观影模式",
      success: "场景模式：观影模式已执行。",
      lightBrightness: 60,
      lightPreset: "half_on",
      ac: { power: "on", temperature: 23 },
      freshAir: { power: "on", level: "low" },
    },
    clean: {
      title: "清洁模式",
      success: "场景模式：清洁模式已执行。",
      lightBrightness: 100,
      lightPreset: "full_on",
      ac: { power: "off" },
      freshAir: { power: "on", level: "high" },
    },
    leave: {
      title: "闭店模式",
      success: "场景模式：闭店模式已执行。",
      lightBrightness: 0,
      lightPreset: "full_off",
      ac: { power: "off" },
      freshAir: { power: "off" },
    },
  };
}

async function applyDashboardScene(sceneKey) {
  const scene = dashboardSceneDefinitions()[sceneKey];
  const rooms = roomsForDisplay();
  if (!scene) {
    showMessage("未找到对应的场景模式。", "warning", true);
    return;
  }
  if (!rooms.length) {
    showMessage("当前没有可执行场景联动的房间。", "warning", true);
    return;
  }
  const failures = [];
  try {
    showMessage(`正在执行${scene.title}...`, "info");
    for (const room of rooms) {
      try {
        await applySceneLightsForRoom(room, scene.lightBrightness, scene.lightPreset);
        await applySceneAcForRoom(room, scene.ac);
        await applySceneFreshAirForRoom(room, scene.freshAir);
      } catch (error) {
        failures.push(`${displayRoomName(room)}：${error.message || "执行失败"}`);
      }
    }
    await reloadAll(false);
    if (failures.length) {
      showMessage(`${scene.title}部分完成，失败 ${failures.length} 间：${failures.slice(0, 2).join("；")}`, "warning", true);
      return;
    }
    showMessage(scene.success, "success", true);
  } catch (error) {
    showMessage(error.message || `${scene.title}执行失败。`, "error");
  }
}

async function runControlMode(modeKey) {
  const rooms = roomsForDisplay();
  if (!rooms.length) {
    showMessage("当前没有可执行总控模式的房间。", "warning", true);
    return;
  }
  try {
    if (modeKey === "summer") {
      await batchRoomAction("ac", "ac_apply_season", "summer", true, true);
      await batchRoomAction("light", "light_apply_preset", "half_on", false, true);
      await batchRoomAction("fresh_air", "fresh_air_turn_on", undefined, false, true);
      showMessage("总控模式：夏季模式已执行。", "success", true);
      return;
    }
    if (modeKey === "winter") {
      await batchRoomAction("ac", "ac_apply_season", "winter", true, true);
      await batchRoomAction("light", "light_apply_preset", "half_on", false, true);
      await batchRoomAction("fresh_air", "fresh_air_turn_off", undefined, false, true);
      showMessage("总控模式：冬季模式已执行。", "success", true);
      return;
    }
    if (modeKey === "patrol") {
      await batchRoomAction("light", "light_apply_preset", "full_off", false, true);
      await batchRoomAction("fresh_air", "fresh_air_turn_off", undefined, false, true);
      showMessage("总控模式：巡查模式已执行。", "success", true);
      return;
    }
    if (modeKey === "eco") {
      await batchRoomAction("light", "light_apply_preset", "half_on", false, true);
      await batchRoomAction("fresh_air", "fresh_air_turn_off", undefined, false, true);
      showMessage("总控模式：节能模式已执行。", "success", true);
      return;
    }
  } catch (error) {
    showMessage(error.message || "总控模式执行失败。", "error");
  }
}

function currentRoomConfig(roomId = state.currentRoomId) {
  const room = getRoom(roomId);
  const raw = currentRoomConfigSource(roomId);
  return raw ? normalizeRoomConfig(room, raw) : null;
}

function candidatesFor(group) {
  return state.entities && state.entities.data ? state.entities.data[group] || [] : [];
}

function candidateById(entityId) {
  for (const key of ["climate", "light", "fan", "switch", "sensor", "binary_sensor", "device_tracker"]) {
    const found = candidatesFor(key).find((item) => item.entity_id === entityId);
    if (found) return found;
  }
  return null;
}

function presenceSensorCandidates() {
  return uniqueEntityOptions([
    ...candidatesFor("binary_sensor"),
    ...candidatesFor("sensor"),
  ]);
}

function deviceTrackerCandidates() {
  return uniqueEntityOptions(candidatesFor("device_tracker"));
}

function roomMatchTokens(room) {
  const source = [
    displayRoomName(room),
    room && room.room_name,
    room && room.entry_title,
    room && room.matched_group && room.matched_group.display_name,
  ].filter(Boolean).join(" ");
  const rawTokens = source
    .toLowerCase()
    .split(/[^a-z0-9\u4e00-\u9fa5]+/)
    .filter((token) => token.length >= 2);
  const digitTokens = source.match(/\d+/g) || [];
  return Array.from(new Set([...rawTokens, ...digitTokens]));
}

function suggestEntityForRoom(room, items, currentValue = "") {
  if (currentValue) return currentValue;
  const options = uniqueEntityOptions(items);
  const tokens = roomMatchTokens(room);
  if (!tokens.length) return "";
  let best = null;
  for (const item of options) {
    const text = `${item.friendly_name || ""} ${item.entity_id || ""}`.toLowerCase();
    const score = tokens.reduce((sum, token) => sum + (text.includes(token) ? (/\d/.test(token) ? 3 : 1) : 0), 0);
    if (!best || score > best.score) {
      best = { score, entity_id: item.entity_id };
    }
  }
  return best && best.score > 0 ? best.entity_id : "";
}

function entityOwnName(entity) {
  if (!entity) return "--";
  const attrs = entity.attributes || {};
  const direct = [
    entity.entity_name,
    entity.name_by_user,
    entity.original_name,
    attrs.entity_name,
    attrs.name_by_user,
    attrs.original_name,
  ].map((item) => String(item || "").trim()).find(Boolean);
  if (direct) return direct;

  const fallback = String(entity.friendly_name || entity.name || entity.entity_id || "--").trim();
  const deviceNames = [
    entity.device_name,
    entity.device && entity.device.name_by_user,
    entity.device && entity.device.name,
    attrs.device_name,
  ].map((item) => String(item || "").trim()).filter(Boolean);
  for (const deviceName of deviceNames) {
    if (fallback.startsWith(deviceName)) {
      const cleaned = fallback.slice(deviceName.length).replace(/^[\s_\-·|/]+/, "").trim();
      if (cleaned) return cleaned;
    }
  }
  if (entity.entity_id && fallback === entity.entity_id) {
    return String(entity.entity_id).replace(/^[^.]+\./, "").replace(/_/g, " ");
  }
  return fallback;
}

function entityDisplayName(itemOrId) {
  if (!itemOrId) return "--";
  const item = typeof itemOrId === "string" ? candidateById(itemOrId) : itemOrId;
  if (item) return entityOwnName(item);
  return typeof itemOrId === "string" ? itemOrId : (itemOrId.entity_id || "--");
}

function pageFilterState(page) {
  return state.pageFilters && state.pageFilters[page] ? state.pageFilters[page] : { include: "", exclude: "" };
}

function setPageFilter(page, field, value) {
  if (!state.pageFilters[page]) {
    state.pageFilters[page] = { include: "", exclude: "" };
  }
  state.pageFilters[page][field] = String(value || "");
  renderPageByKey(page);
}

function renderPageByKey(page) {
  if (page === "room") return renderRoomPage();
  if (page === "ac") return renderAcPage();
  if (page === "light") return renderLightPage();
  if (page === "fan") return renderFanPage();
}

function matchesKeywordFilter(text, includeValue, excludeValue) {
  const source = String(text || "").toLowerCase();
  const includeKeywords = parseKeywordList(includeValue).map((item) => item.toLowerCase());
  const excludeKeywords = parseKeywordList(excludeValue).map((item) => item.toLowerCase());
  if (includeKeywords.length && !includeKeywords.some((keyword) => source.includes(keyword))) {
    return false;
  }
  if (excludeKeywords.some((keyword) => source.includes(keyword))) {
    return false;
  }
  return true;
}

function roomFilterText(room) {
  const inventory = getMappedRoomDevices(room);
  const parts = [
    displayRoomName(room),
    room && room.entry_title,
    room && room.room_name,
    room && room.matched_group && room.matched_group.display_name,
    inventory.ac && `${entityOwnName(inventory.ac)} ${inventory.ac.friendly_name || ""} ${inventory.ac.entity_id || ""}`,
    inventory.freshAir && (inventory.freshAir.friendly_name || inventory.freshAir.entity_id),
    ...(inventory.lights || []).map((item) => item && `${entityOwnName(item)} ${item.friendly_name || ""} ${item.entity_id || ""}`),
  ];
  return parts.filter(Boolean).join(" ");
}

function renderDeviceFilterBar(page, includePlaceholder, excludePlaceholder, hint = "", compact = false) {
  const filters = pageFilterState(page);
  return `
    <div class="list-filter-bar${compact ? " compact-filter" : ""}">
      ${compact ? `<span class="filter-search-icon" aria-hidden="true"></span>` : ""}
      <div class="field">
        <label>包含关键词</label>
        <input type="text" value="${escapeHtml(filters.include)}" placeholder="${escapeHtml(includePlaceholder)}" oninput='setPageFilter(${JSON.stringify(page)}, "include", this.value)'>
      </div>
      <div class="field">
        <label>排除关键词</label>
        <input type="text" value="${escapeHtml(filters.exclude)}" placeholder="${escapeHtml(excludePlaceholder)}" oninput='setPageFilter(${JSON.stringify(page)}, "exclude", this.value)'>
      </div>
      ${hint ? `<div class="list-filter-note">${escapeHtml(hint)}</div>` : ""}
    </div>
  `;
}

const LIGHT_SWITCH_INCLUDE_HINTS = ["灯带", "筒灯", "射灯", "牛眼灯", "主灯", "副灯", "壁灯", "吊灯", "吸顶灯", "灯"];
const LIGHT_SWITCH_EXCLUDE_HINTS = ["场景", "情景", "模式", "面板", "按键", "按钮", "插座", "电源", "总控", "自动化", "背光", "夜灯", "网关", "蓝牙", "无线"];

function lightCandidateText(item) {
  return `${item ? entityOwnName(item) : ""} ${item && item.friendly_name || ""} ${item && item.entity_id || ""}`.toLowerCase();
}

function parseKeywordList(value) {
  const rawItems = Array.isArray(value)
    ? value
    : String(value || "").split(/[\n,，;；]+/);
  const result = [];
  for (const item of rawItems) {
    const keyword = String(item || "").trim();
    if (keyword && !result.includes(keyword)) {
      result.push(keyword);
    }
  }
  return result;
}

function isLikelyLightSwitch(item) {
  if (!item || String(item.entity_id || "").split(".", 1)[0] !== "switch") return false;
  const text = lightCandidateText(item);
  if (LIGHT_SWITCH_EXCLUDE_HINTS.some((keyword) => text.includes(keyword))) {
    return false;
  }
  return LIGHT_SWITCH_INCLUDE_HINTS.some((keyword) => text.includes(keyword));
}

function lightCandidatePool() {
  return [
    ...candidatesFor("light"),
    ...candidatesFor("switch").filter((item) => isLikelyLightSwitch(item)),
  ];
}

function hvacModeLabel(value) {
  const labels = {
    cool: "制冷",
    heat: "制热",
    auto: "自动",
    dry: "除湿",
    fan_only: "送风",
    off: "关闭",
    unavailable: "离线",
    unknown: "未知",
  };
  return labels[value] || value || "--";
}

function circleDash(percentage, circumference) {
  const pct = Math.max(0, Math.min(1, Number(percentage) || 0));
  return Math.round(pct * circumference) + " " + circumference;
}

function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function getMappedRoomDevices(room) {
  const mapped = room && room.mapped ? room.mapped : {};
  const roomConfig = room ? currentRoomConfig(room.room_id) : null;
  const filters = roomEntityFilters(roomConfig);
  const visibleAcIds = new Set(filterEntityOptions([mapped.ac], filters.ac_include_keywords, filters.ac_exclude_keywords).map((item) => item.entity_id));
  const visibleLightIds = new Set(filterEntityOptions(mapped.lights || [], filters.light_include_keywords, filters.light_exclude_keywords).map((item) => item.entity_id));
  const visibleFreshIds = new Set(filterEntityOptions([mapped.fresh_air], filters.fresh_air_include_keywords, filters.fresh_air_exclude_keywords).map((item) => item.entity_id));
  return {
    ac: mapped.ac && visibleAcIds.has(mapped.ac.entity_id) ? mapped.ac : null,
    lights: Array.isArray(mapped.lights) ? mapped.lights.filter((item) => item && visibleLightIds.has(item.entity_id)) : [],
    freshAir: mapped.fresh_air && visibleFreshIds.has(mapped.fresh_air.entity_id) ? mapped.fresh_air : null,
    switches: Array.isArray(mapped.switches) ? mapped.switches : [],
  };
}

function hasMappedDevices(room) {
  const inventory = getMappedRoomDevices(room);
  return Boolean(inventory.ac || inventory.freshAir || inventory.lights.length || inventory.switches.length);
}

function hasVisibleRoomDevices(room) {
  const inventory = getMappedRoomDevices(room);
  return Boolean(inventory.ac || inventory.freshAir || inventory.lights.length);
}

function roomOnlineTerminalCount(room) {
  return Math.max(Number(room && room.occupied_count || 0), connectedComputers(room).length);
}

function compareRoomPriority(a, b) {
  const aOccupied = roomOnlineTerminalCount(a) > 0 ? 1 : 0;
  const bOccupied = roomOnlineTerminalCount(b) > 0 ? 1 : 0;
  if (aOccupied !== bOccupied) {
    return bOccupied - aOccupied;
  }
  const aActiveCount = roomOnlineTerminalCount(a);
  const bActiveCount = roomOnlineTerminalCount(b);
  if (aActiveCount !== bActiveCount) {
    return bActiveCount - aActiveCount;
  }
  const aName = displayRoomName(a);
  const bName = displayRoomName(b);
  const byName = aName.localeCompare(bName, "zh-CN", { numeric: true, sensitivity: "base" });
  if (byName !== 0) {
    return byName;
  }
  return String(a && a.room_id || "").localeCompare(String(b && b.room_id || ""), "zh-CN", {
    numeric: true,
    sensitivity: "base",
  });
}

function sortRoomsByPriority(rooms) {
  return [...(Array.isArray(rooms) ? rooms : [])].sort(compareRoomPriority);
}

function dashboardRoomSortValue(value) {
  return ["occupied", "number", "name", "devices"].includes(value) ? value : "occupied";
}

function roomOrderNumber(room) {
  const candidates = [
    displayRoomName(room),
    roomCoverageText(room),
    room && room.room_name,
    room && room.entry_title,
  ].filter(Boolean);
  for (const item of candidates) {
    const match = String(item).match(/\d+/);
    if (match) {
      return Number(match[0]);
    }
  }
  return Number.MAX_SAFE_INTEGER;
}

function roomActiveDeviceScore(room) {
  const inventory = getMappedRoomDevices(room);
  const onlineCount = roomOnlineTerminalCount(room);
  const lightOnCount = inventory.lights.filter((item) => item && item.is_on).length;
  return [
    onlineCount > 0 ? 4 : 0,
    inventory.ac && inventory.ac.is_on ? 3 : 0,
    inventory.freshAir && inventory.freshAir.is_on ? 2 : 0,
    lightOnCount,
    onlineCount,
  ].reduce((sum, value) => sum + Number(value || 0), 0);
}

function compareRoomsByName(a, b) {
  const aName = displayRoomName(a);
  const bName = displayRoomName(b);
  const byName = aName.localeCompare(bName, "zh-CN", { numeric: true, sensitivity: "base" });
  if (byName !== 0) {
    return byName;
  }
  return String(a && a.room_id || "").localeCompare(String(b && b.room_id || ""), "zh-CN", {
    numeric: true,
    sensitivity: "base",
  });
}

function sortDashboardRooms(rooms, sortValue = state.dashboardRoomSort) {
  const items = [...(Array.isArray(rooms) ? rooms : [])];
  const sort = dashboardRoomSortValue(sortValue);
  return items.sort((a, b) => {
    if (sort === "number") {
      const byNumber = roomOrderNumber(a) - roomOrderNumber(b);
      return byNumber !== 0 ? byNumber : compareRoomsByName(a, b);
    }
    if (sort === "name") {
      return compareRoomsByName(a, b);
    }
    if (sort === "devices") {
      const byDevices = roomActiveDeviceScore(b) - roomActiveDeviceScore(a);
      return byDevices !== 0 ? byDevices : compareRoomPriority(a, b);
    }
    return compareRoomPriority(a, b);
  });
}

function setDashboardRoomSort(value) {
  state.dashboardRoomSort = dashboardRoomSortValue(value);
  renderDashboard();
}

function summarizeRooms(rooms) {
  const visibleRooms = sortRoomsByPriority(
    Array.isArray(rooms)
      ? rooms.filter((room) => room && !room.is_public_area && room.room_id !== "public_area")
      : []
  );
  const lightEntities = visibleRooms.flatMap((room) => getMappedRoomDevices(room).lights);
  const acRooms = visibleRooms.filter((room) => getMappedRoomDevices(room).ac);
  const freshRooms = visibleRooms.filter((room) => getMappedRoomDevices(room).freshAir);
  const configuredRooms = visibleRooms.filter((room) => (room.summary && room.summary.has_mapping) || hasMappedDevices(room));
  const manualOverrideRooms = visibleRooms.filter((room) => room && room.runtime && room.runtime.ac_manual_override_until).length;
  const scheduleBlockedRooms = visibleRooms.filter((room) => room && room.runtime && room.runtime.schedule_allowed === false).length;
  return {
    rooms: visibleRooms,
    totalRooms: visibleRooms.length,
    occupiedRooms: visibleRooms.filter((room) => roomOnlineTerminalCount(room) > 0).length,
    configuredRooms: configuredRooms.length,
    unconfiguredRooms: Math.max(visibleRooms.length - configuredRooms.length, 0),
    idleRooms: visibleRooms.filter((room) => roomOnlineTerminalCount(room) <= 0).length,
    manualOverrideRooms,
    scheduleBlockedRooms,
    automationReadyRooms: Math.max(configuredRooms.length - manualOverrideRooms - scheduleBlockedRooms, 0),
    acTotal: acRooms.length,
    acOn: acRooms.filter((room) => getMappedRoomDevices(room).ac.is_on).length,
    acOffline: acRooms.filter((room) => {
      const ac = getMappedRoomDevices(room).ac;
      return ac && (ac.available === false || ac.exists === false);
    }).length,
    lightEntities,
    lightOn: lightEntities.filter((item) => item.is_on).length,
    lightOffline: lightEntities.filter((item) => item.available === false || item.exists === false).length,
    freshTotal: freshRooms.length,
    freshOn: freshRooms.filter((room) => getMappedRoomDevices(room).freshAir.is_on).length,
    freshOffline: freshRooms.filter((room) => {
      const fresh = getMappedRoomDevices(room).freshAir;
      return fresh && (fresh.available === false || fresh.exists === false);
    }).length,
    totalComputers: visibleRooms.reduce((sum, room) => sum + Number(room.computer_count || 0), 0),
    onlineComputers: visibleRooms.reduce((sum, room) => sum + roomOnlineTerminalCount(room), 0),
  };
}

function entityDisplayName(entity) {
  if (!entity) return "未绑定";
  return entityOwnName(entity) || entity.entity_id || "未绑定";
}

function renderRoomDeviceBinding(label, items, emptyText = "未绑定") {
  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  return `
    <div class="room-device-binding">
      <span>${escapeHtml(label)}</span>
      <strong>${list.length ? list.map((item) => escapeHtml(entityDisplayName(item))).join(" / ") : escapeHtml(emptyText)}</strong>
    </div>
  `;
}

function roomChip(room) {
  if (!((room.summary && room.summary.has_mapping) || hasMappedDevices(room))) {
    return '<span class="badge orange">未映射</span>';
  }
  return roomOnlineTerminalCount(room) > 0 ? '<span class="badge green">有人</span>' : '<span class="badge blue">无人</span>';
}

function statusRing(percentage, color, value, label) {
  const circumference = 251.2;
  const dash = circleDash(percentage, circumference);
  return `
    <div class="device-status-ring">
      <svg viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(17,32,51,.08)" stroke-width="8"></circle>
        <circle cx="50" cy="50" r="40" fill="none" stroke="${color}" stroke-width="8" stroke-linecap="round" stroke-dasharray="${dash}"></circle>
      </svg>
      <div class="device-status-center">
        <strong>${escapeHtml(value)}</strong>
        <span>${escapeHtml(label)}</span>
      </div>
    </div>
  `;
}

function drawLoadTrendChart(canvas, values) {
  if (!canvas) return;
  const rect = canvas.parentElement.getBoundingClientRect();
  const width = Math.max(Math.round(rect.width), 240);
  const height = Math.max(Math.round(rect.height), 120);
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";

  const ctx = canvas.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const points = (values || []).map((value) => Number(value) || 0).filter((value) => Number.isFinite(value));
  if (!points.length) return;

  const pad = { top: 10, right: 14, bottom: 20, left: 40 };
  const chartWidth = width - pad.left - pad.right;
  const chartHeight = height - pad.top - pad.bottom;
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = Math.max(max - min, 1);
  const stepX = chartWidth / Math.max(points.length - 1, 1);
  const coords = points.map((value, index) => ({
    x: pad.left + stepX * index,
    y: pad.top + chartHeight - ((value - min) / range) * chartHeight,
  }));

  ctx.strokeStyle = "rgba(15,23,42,.06)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = pad.top + (chartHeight / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillStyle = "rgba(100,116,139,.88)";
    ctx.font = "11px Consolas, monospace";
    ctx.textAlign = "right";
    ctx.fillText((max - (range / 4) * i).toFixed(1), pad.left - 6, y + 4);
  }

  const areaGradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + chartHeight);
  areaGradient.addColorStop(0, "rgba(24,144,255,.14)");
  areaGradient.addColorStop(1, "rgba(24,144,255,.02)");

  ctx.beginPath();
  ctx.moveTo(coords[0].x, coords[0].y);
  for (let i = 1; i < coords.length; i += 1) {
    const prev = coords[i - 1];
    const current = coords[i];
    const cpX = (prev.x + current.x) / 2;
    ctx.bezierCurveTo(cpX, prev.y, cpX, current.y, current.x, current.y);
  }
  ctx.lineTo(coords[coords.length - 1].x, pad.top + chartHeight);
  ctx.lineTo(coords[0].x, pad.top + chartHeight);
  ctx.closePath();
  ctx.fillStyle = areaGradient;
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(coords[0].x, coords[0].y);
  for (let i = 1; i < coords.length; i += 1) {
    const prev = coords[i - 1];
    const current = coords[i];
    const cpX = (prev.x + current.x) / 2;
    ctx.bezierCurveTo(cpX, prev.y, cpX, current.y, current.x, current.y);
  }
  ctx.strokeStyle = "#1890ff";
  ctx.lineWidth = 2;
  ctx.stroke();

  const last = coords[coords.length - 1];
  ctx.beginPath();
  ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
  ctx.fillStyle = "#1890ff";
  ctx.fill();
  ctx.beginPath();
  ctx.arc(last.x, last.y, 7, 0, Math.PI * 2);
  ctx.strokeStyle = "rgba(24,144,255,.28)";
  ctx.lineWidth = 1;
  ctx.stroke();
}

function drawDailySummaryChart(canvas, items) {
  if (!canvas) return;
  const rect = canvas.parentElement.getBoundingClientRect();
  const width = Math.max(Math.round(rect.width), 240);
  const height = Math.max(Math.round(rect.height), 160);
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";

  const ctx = canvas.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) return;
  const pad = { top: 14, right: 18, bottom: 42, left: 42 };
  const chartWidth = width - pad.left - pad.right;
  const chartHeight = height - pad.top - pad.bottom;
  const max = Math.max(...rows.map((item) => Number(item.hours) || 0), 1);
  const barWidth = Math.min(72, chartWidth / Math.max(rows.length * 1.6, 1));
  const gap = rows.length > 1 ? (chartWidth - barWidth * rows.length) / (rows.length - 1) : 0;

  ctx.strokeStyle = "rgba(15,23,42,.06)";
  ctx.lineWidth = 1;
  for (let index = 0; index <= 4; index += 1) {
    const y = pad.top + (chartHeight / 4) * index;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillStyle = "rgba(100,116,139,.88)";
    ctx.font = "11px Consolas, monospace";
    ctx.textAlign = "right";
    ctx.fillText(`${(max - (max / 4) * index).toFixed(1)}h`, pad.left - 6, y + 4);
  }

  rows.forEach((item, index) => {
    const x = pad.left + index * (barWidth + gap);
    const value = Number(item.hours) || 0;
    const barHeight = max > 0 ? (value / max) * chartHeight : 0;
    const y = pad.top + chartHeight - barHeight;
    ctx.fillStyle = item.color || "#2563eb";
    ctx.beginPath();
    ctx.roundRect(x, y, barWidth, Math.max(barHeight, 2), 14);
    ctx.fill();
    ctx.fillStyle = "rgba(15,23,42,.92)";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${value.toFixed(1)}h`, x + barWidth / 2, y - 8);
    ctx.fillStyle = "rgba(100,116,139,.92)";
    ctx.font = "12px sans-serif";
    ctx.fillText(item.label || "", x + barWidth / 2, height - 14);
  });
}

function buildEstimatedPowerSeries(rooms) {
  const baseLoad = rooms.reduce((sum, room) => {
    const ac = room.mapped && room.mapped.ac && room.mapped.ac.is_on ? 2.4 : 0;
    const lights = room.mapped && room.mapped.lights ? room.mapped.lights.filter((item) => item.is_on).length * 0.18 : 0;
    const fresh = room.mapped && room.mapped.fresh_air && room.mapped.fresh_air.is_on ? 0.6 : 0;
    const pcs = roomOnlineTerminalCount(room) * 0.35;
    return sum + ac + lights + fresh + pcs;
  }, 0);
  const roundedBase = Math.max(baseLoad, .8);
  return Array.from({ length: 12 }, (_, index) => {
    const wave = Math.sin((index / 11) * Math.PI * 1.6) * 0.42;
    const offset = ((index % 4) - 1.5) * 0.08;
    return Number(Math.max(.5, roundedBase + wave + offset).toFixed(1));
  });
}

function roomNeedsMappingAttention(room) {
  const devices = getMappedRoomDevices(room);
  const hasAc = Boolean(devices.ac);
  const hasLights = devices.lights.length > 0;
  const hasFresh = Boolean(devices.freshAir);
  if (!hasAc && !hasLights && !hasFresh) {
    return true;
  }
  if (roomOnlineTerminalCount(room) > 0) {
    return !hasAc || !hasLights;
  }
  return false;
}

function sampleRoomNames(rooms, limit = 3) {
  const items = Array.isArray(rooms) ? rooms.filter(Boolean).slice(0, limit) : [];
  if (!items.length) return "无";
  return items.map((room) => displayRoomName(room)).join("、");
}

function groupedRoomsForRoom(room) {
  if (!room) return [];
  const key = roomGroupDisplayKey(room);
  if (!key) return [room];
  return (Array.isArray(currentRooms()) ? currentRooms() : []).filter((item) => item && roomGroupDisplayKey(item) === key);
}

function roomComputers(room) {
  const rooms = groupedRoomsForRoom(room);
  const seen = new Set();
  const items = [];
  for (const current of rooms.length ? rooms : [room]) {
    const computers = Array.isArray(current && current.computers) ? current.computers : [];
    for (const computer of computers) {
      if (!computer) continue;
      const key = String(
        computer.entity_id ||
        computer.mac_address ||
        computer.ip_address ||
        `${computerDisplayName(computer)}|${computer.host_name || ""}`
      );
      if (seen.has(key)) continue;
      seen.add(key);
      items.push(computer);
    }
  }
  return items;
}

function connectedComputers(room) {
  const computers = roomComputers(room);
  return computers.filter((item) => item && (item.is_connected || item.is_online));
}

function normalizeComputerLabel(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

function isGenericComputerLabel(label) {
  const compact = normalizeComputerLabel(label).replace(/\s+/g, "");
  return /^(电脑|终端|主机|在线|离线|computer|pc)$/i.test(compact);
}

function computerDisplayName(computer) {
  const attrs = computer && computer.attributes || {};
  const entityId = String(computer && computer.entity_id || "");
  const entityTail = entityId.includes(".") ? entityId.split(".").pop() : entityId;
  const ip = String(computer && computer.ip_address || "");
  const ipTail = ip.split(".").pop();
  const candidates = [
    computer && computer.friendly_name,
    attrs && attrs.friendly_name,
    computer && computer.display_name,
    computer && computer.name,
    attrs && attrs.name,
    computer && computer.host_name,
    attrs && attrs.host_name,
    computer && computer.device_name,
    attrs && attrs.device_name,
    computer && computer.computer_name,
    attrs && attrs.computer_name,
  ];
  for (const candidate of candidates) {
    const label = normalizeComputerLabel(candidate);
    if (!label) continue;
    if (isGenericComputerLabel(label) && (ipTail || entityTail)) continue;
    return label;
  }
  if (ipTail) return `${ipTail}号电脑`;
  if (entityTail) return entityTail.replace(/[_-]+/g, " ");
  return "电脑";
}

function uniqueComputerDisplayNames(computers, limit = 0) {
  const labels = [];
  const seen = new Set();
  for (const computer of Array.isArray(computers) ? computers : []) {
    const label = computerDisplayName(computer);
    const key = label.toLowerCase();
    if (!label || seen.has(key)) continue;
    seen.add(key);
    labels.push(label);
    if (limit && labels.length >= limit) break;
  }
  return labels;
}

function onlineComputerSummary(room, limit = 3) {
  const labels = uniqueComputerDisplayNames(connectedComputers(room));
  if (!labels.length) return "";
  const visible = limit > 0 ? labels.slice(0, limit) : labels;
  return labels.length > visible.length
    ? `${visible.join("、")} 等 ${labels.length} 台`
    : visible.join("、");
}

function computerPresenceEntries(rooms, onlyOnline = true) {
  const items = [];
  for (const room of Array.isArray(rooms) ? rooms : []) {
    const computers = roomComputers(room);
    for (const computer of computers) {
      const isOnline = Boolean(computer && (computer.is_connected || computer.is_online));
      if (onlyOnline ? !isOnline : isOnline) continue;
      items.push({
        entity_id: computer && computer.entity_id || "",
        friendly_name: computerDisplayName(computer),
        display_name: computerDisplayName(computer),
        room_name: displayRoomName(room),
        ip_address: computer && computer.ip_address || "",
        state: isOnline ? "online" : "offline",
        attributes: {
          room_name: displayRoomName(room),
          ip_address: computer && computer.ip_address || "",
          host_name: computer && computer.host_name || "",
          last_probe_method: computer && computer.last_probe_method || "",
          probe_state: computer && computer.probe_state || "",
          last_seen: computer && computer.last_seen || "",
        },
      });
    }
  }
  return items;
}

function renderComputerPresenceTrigger(title, items, emptyText, detailText) {
  return renderReferenceEntityMatchTrigger(title, items, emptyText, "台终端", detailText);
}

function computerTailLabel(computer) {
  return computerDisplayName(computer);
}

function buildDashboardIssueSummary(summary) {
  const rooms = summary.rooms || [];
  const offlineRoomSet = new Map();
  for (const room of rooms) {
    const devices = getMappedRoomDevices(room);
    const hasOffline = Boolean(
      (devices.ac && (devices.ac.available === false || devices.ac.exists === false)) ||
      devices.lights.some((item) => item.available === false || item.exists === false) ||
      (devices.freshAir && (devices.freshAir.available === false || devices.freshAir.exists === false))
    );
    if (hasOffline) {
      offlineRoomSet.set(room.room_id, room);
    }
  }

  const mappingRooms = rooms.filter((room) => roomNeedsMappingAttention(room));

  return [
    {
      key: "offline",
      level: summary.acOffline + summary.lightOffline + summary.freshOffline > 0 ? "danger" : "normal",
      title: "设备离线",
      count: summary.acOffline + summary.lightOffline + summary.freshOffline,
      samples: sampleRoomNames(Array.from(offlineRoomSet.values())),
      unit: "",
    },
    {
      key: "mapping",
      level: mappingRooms.length > 0 ? "warn" : "normal",
      title: "未完成映射",
      count: mappingRooms.length,
      samples: sampleRoomNames(mappingRooms),
      unit: "",
    },
  ];
}

function renderEmptyState(title, text, actionHtml = "") {
  return `
    <div class="empty-state">
      <strong>${escapeHtml(title)}</strong>
      <div>${escapeHtml(text)}</div>
      ${actionHtml ? `<div class="button-row center stack-gap">${actionHtml}</div>` : ""}
    </div>
  `;
}

function renderPanelHeading(title, extraHtml = "") {
  return `
    <div class="energy-header">
      <div><h2 class="panel-title">${escapeHtml(title)}</h2></div>
      ${extraHtml}
    </div>
  `;
}

function renderLegendItem(tone, label, value) {
  return `<div><span class="legend-label"><span class="dot ${escapeHtml(tone)}"></span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function toneForLog(log) {
  const source = String(log && log.source || "").toLowerCase();
  const action = String(log && log.action || "").toLowerCase();
  const message = String(log && log.message || "").toLowerCase();
  if (message.includes("失败") || message.includes("离线") || action.includes("off")) return "warn";
  if (source === "automation" || message.includes("开启") || action.includes("turn_on")) return "ok";
  return "info";
}

function sourceLabel(log) {
  const source = String(log && log.source || "").toLowerCase();
  if (source === "automation") return "自动";
  if (source === "manual") return "手动";
  return source ? source : "事件";
}

function dashboardIcon(name) {
  const icons = {
    room: '<svg viewBox="0 0 24 24" fill="none"><path d="M4 10.5 12 4l8 6.5V20H4v-9.5Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M9.5 20v-5h5v5" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
    ac: '<svg viewBox="0 0 24 24" fill="none"><path d="M12 3v18M4.5 7.5 19.5 16.5M4.5 16.5 19.5 7.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    light: '<svg viewBox="0 0 24 24" fill="none"><path d="M12 4a5 5 0 0 0-3 9v2h6v-2a5 5 0 0 0-3-9Z" stroke="currentColor" stroke-width="1.8"/><path d="M9.5 18h5M10.5 21h3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    fresh: '<svg viewBox="0 0 24 24" fill="none"><path d="M12 12c0-3.5 2.2-7 5.2-7 1.4 0 2.3 1 2.3 2.3 0 3-3.5 5.2-7 5.2Zm0 0c-3.5 0-7-2.2-7-5.2C5 5.4 6 4.5 7.3 4.5c3 0 5.2 3.5 5.2 7Zm0 0c0 3.5-2.2 7-5.2 7-1.4 0-2.3-1-2.3-2.3 0-3 3.5-5.2 7-5.2Zm0 0c3.5 0 7 2.2 7 5.2 0 1.4-1 2.3-2.3 2.3-3 0-5.2-3.5-5.2-7Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/></svg>',
    pc: '<svg viewBox="0 0 24 24" fill="none"><rect x="4" y="5" width="16" height="11" rx="2.5" stroke="currentColor" stroke-width="1.8"/><path d="M9 19h6M12 16v3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    leaf: '<svg viewBox="0 0 24 24" fill="none"><path d="M19 5c-7 0-11 4.2-11 10a5 5 0 0 0 5 5c5.8 0 8-5.3 8-15h-2Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M8 16c2.2-2 4.7-3.6 8-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    alert: '<svg viewBox="0 0 24 24" fill="none"><path d="M12 4 4 18h16L12 4Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 9v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="16" r="1" fill="currentColor"/></svg>',
    energy: '<svg viewBox="0 0 24 24" fill="none"><path d="M13 3 6 13h5l-1 8 8-11h-5l0-7Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
  };
  return icons[name] || icons.room;
}

function dashboardAverageTemperature(rooms) {
  const values = (Array.isArray(rooms) ? rooms : [])
    .map((room) => {
      const ac = getMappedRoomDevices(room).ac;
      if (!ac || ac.domain !== "climate") return null;
      const value = Number(firstFiniteNumber(ac.current_temperature, ac.temperature));
      return Number.isFinite(value) ? value : null;
    })
    .filter((value) => value != null);
  if (!values.length) {
    return { raw: null, text: "--" };
  }
  const average = values.reduce((sum, value) => sum + value, 0) / values.length;
  return {
    raw: average,
    text: `${average.toFixed(1)}°C`,
  };
}

function dashboardOnlineRate(summary) {
  const total = Number(summary.acTotal || 0) + Number(summary.lightEntities.length || 0) + Number(summary.freshTotal || 0);
  const offline = Number(summary.acOffline || 0) + Number(summary.lightOffline || 0) + Number(summary.freshOffline || 0);
  if (!total) return 100;
  return Math.max(0, Math.min(100, Math.round(((total - offline) / total) * 100)));
}

function dashboardHealthSummary(summary) {
  const onlineRate = dashboardOnlineRate(summary);
  const mappingRatio = summary.totalRooms ? summary.configuredRooms / summary.totalRooms : 1;
  const occupancyRatio = summary.totalRooms ? summary.occupiedRooms / summary.totalRooms : 0;
  const score = Math.max(
    42,
    Math.min(
      99,
      Math.round(onlineRate * 0.58 + mappingRatio * 28 + (1 - Math.max(occupancyRatio - 0.9, 0)) * 14)
    )
  );
  if (score >= 90) {
    return { score, label: "优", tone: "excellent", detail: "系统运行稳定" };
  }
  if (score >= 78) {
    return { score, label: "良", tone: "good", detail: "设备状态良好" };
  }
  if (score >= 64) {
    return { score, label: "中", tone: "warn", detail: "存在待处理项" };
  }
  return { score, label: "警", tone: "danger", detail: "建议立即巡检" };
}

function renderDashboardSummaryTile(title, value, meta, tone = "", progress = 0, progressLabel = "") {
  const normalizedProgress = Math.max(0, Math.min(100, Number(progress) || 0));
  const circumference = 163.4;
  const dash = circleDash(normalizedProgress / 100, circumference);
  return `
    <div class="dashboard-summary-tile ${tone}">
      <div class="dashboard-summary-icon" aria-hidden="true">
        <svg viewBox="0 0 64 64" fill="none">
          <circle cx="32" cy="32" r="26" class="dashboard-summary-ring-track"></circle>
          <circle cx="32" cy="32" r="26" class="dashboard-summary-ring-progress" stroke-dasharray="${dash}"></circle>
        </svg>
        <div class="dashboard-summary-ring-center">
          <strong>${escapeHtml(progressLabel || `${normalizedProgress}%`)}</strong>
          <span>${escapeHtml(`${normalizedProgress}%`)}</span>
        </div>
      </div>
      <div class="dashboard-summary-copy">
        <span>${escapeHtml(title)}</span>
        <strong>${escapeHtml(value)}</strong>
        <small>${escapeHtml(meta)}</small>
      </div>
    </div>
  `;
}

function renderDashboardGauge(health) {
  const score = Math.max(0, Math.min(Number(health && health.score) || 0, 100));
  const circumference = 219.8;
  const dash = circleDash(score / 100, circumference);
  return `
    <div class="dashboard-gauge ${escapeHtml(health && health.tone || "")}">
      <svg viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="35" fill="none" stroke="rgba(89,110,143,.12)" stroke-width="8" stroke-linecap="round" stroke-dasharray="219.8 219.8"></circle>
        <circle cx="50" cy="50" r="35" fill="none" stroke="url(#dashboardGaugeGradient)" stroke-width="8" stroke-linecap="round" stroke-dasharray="${dash}"></circle>
        <defs>
          <linearGradient id="dashboardGaugeGradient" x1="18" y1="82" x2="82" y2="18" gradientUnits="userSpaceOnUse">
            <stop stop-color="#35C67B"/>
            <stop offset="0.55" stop-color="#7CC8F8"/>
            <stop offset="1" stop-color="#7A8DFF"/>
          </linearGradient>
        </defs>
      </svg>
      <div class="dashboard-gauge-center">
        <strong>${escapeHtml(health && health.label || "--")}</strong>
        <span>健康度 ${escapeHtml(String(score))}</span>
        <small>${escapeHtml(health && health.detail || "--")}</small>
      </div>
    </div>
  `;
}

function renderDashboardSuitePill(iconName, value, toneClass = "", stateClass = "") {
  return `
    <span class="dashboard-suite-pill ${escapeHtml(toneClass)} ${escapeHtml(stateClass)}">
      <span class="dashboard-suite-pill-icon" aria-hidden="true">${dashboardIcon(iconName)}</span>
      <span>${escapeHtml(value)}</span>
    </span>
  `;
}

function renderDashboardSuiteCard(room) {
  const inventory = getMappedRoomDevices(room);
  const ac = inventory.ac;
  const lights = inventory.lights;
  const fresh = inventory.freshAir;
  const lightOnCount = lights.filter((item) => item && item.is_on).length;
  const onlineCount = roomOnlineTerminalCount(room);
  const computerTotal = Number(room.computer_count || 0);
  const temperature = ac && ac.domain === "climate"
    ? `${acTargetDisplayValue(ac, 26)}°C`
    : (ac && ac.is_on ? "ON" : "--");
  const roomId = JSON.stringify(room.room_id);
  const occupancy = onlineCount > 0 ? "occupied" : "idle";
  const occupancyLabel = onlineCount > 0 ? "使用中" : "空闲";
  const acState = acVisualState(ac);
  const lightState = lightVisualState(lights);
  const freshState = freshVisualState(fresh);
  const pcState = onlineCount > 0 ? "state-online" : (computerTotal > 0 ? "state-idle" : "state-offline");
  return `
    <button class="dashboard-suite-card ${occupancy}" type="button" onclick='openRoomStatusModal(${roomId})'>
      <div class="dashboard-suite-top">
        <div class="dashboard-suite-title">${escapeHtml(displayRoomName(room))}</div>
        <span class="dashboard-suite-badge ${occupancy}">${escapeHtml(occupancyLabel)}</span>
      </div>
      <div class="dashboard-suite-visual">
        <div class="dashboard-suite-isometric ${occupancy}" aria-hidden="true"></div>
      </div>
      <div class="dashboard-suite-pills">
        ${renderDashboardSuitePill("ac", temperature, "cool", acState)}
        ${renderDashboardSuitePill("pc", `${onlineCount}/${computerTotal || Math.max(onlineCount, 1)}`, "blue", pcState)}
        ${renderDashboardSuitePill("light", lights.length ? `${lightOnCount}/${lights.length}` : "--", "amber", lightState)}
        ${renderDashboardSuitePill("fresh", fresh ? (fresh.is_on ? "开" : "关") : "--", "green", freshState)}
      </div>
    </button>
  `;
}

function showWeatherForecast() {
  if (!state.weather) {
    showMessage("天气数据尚未就绪，请稍后再试。", "info");
    return;
  }
  
  const weather = state.weather;
  const forecast = weather.forecast || [];
  const weatherText = weather.text || weather.weather || "未知";
  const city = weather.location_name || state.weatherConfig?.area_name || "未配置地区";
  const alarms = Array.isArray(weather.alarms) ? weather.alarms.filter((item) => item && (item.title || item.description)) : [];
  const indexes = weather.indexes && typeof weather.indexes === "object" ? Object.entries(weather.indexes).filter(([, value]) => value) : [];
  const updatedAt = weather.updated_at ? `${weather.updated_at} 更新` : "实时天气";
  const keypoint = weather.forecast_keypoint || weather.hourly_forecast || "";
  const minutely = weather.minutely_forecast || "";
  
  let html = `
    <div class="weather-forecast-panel">
      <div class="weather-current-main">
        <div class="weather-current-temp">
          <strong>${weather.temperature}</strong>
          <span>°C</span>
        </div>
        <div class="weather-current-desc">
          <h3>${weatherText}</h3>
          <p>${city} · ${updatedAt}</p>
        </div>
        <div class="weather-current-side">
          <div class="weather-side-pill">${weather.aqi ? `AQI ${weather.aqi}` : "AQI --"}</div>
          <div class="weather-side-pill">${weather.visibility != null ? `能见度 ${weather.visibility}` : "能见度 --"}</div>
        </div>
      </div>
      
      <div class="weather-details-grid">
        <div class="weather-detail-item">
          <label>湿度</label>
          <strong>${weather.humidity || "--"}%</strong>
        </div>
        <div class="weather-detail-item">
          <label>风向</label>
          <strong>${weather.wind_direction || "--"}</strong>
        </div>
        <div class="weather-detail-item">
          <label>风力</label>
          <strong>${weather.wind_speed || "--"}级</strong>
        </div>
        <div class="weather-detail-item">
          <label>气压</label>
          <strong>${weather.pressure || "--"}hPa</strong>
        </div>
      </div>
  `;

  if (minutely || keypoint) {
    html += `
      <div class="weather-brief-grid">
        ${minutely ? `
          <div class="weather-brief-card">
            <label>分钟级提示</label>
            <p>${minutely}</p>
          </div>
        ` : ""}
        ${keypoint ? `
          <div class="weather-brief-card">
            <label>天气概览</label>
            <p>${keypoint}</p>
          </div>
        ` : ""}
      </div>
    `;
  }

  if (alarms.length) {
    html += `
      <div class="weather-section-head">
        <h2>天气预警</h2>
      </div>
      <div class="weather-alert-list">
        ${alarms.slice(0, 4).map((item) => `
          <div class="weather-alert-item">
            <strong>${escapeHtml(item.title || "天气预警")}</strong>
            <p>${escapeHtml(item.description || "--")}</p>
          </div>
        `).join("")}
      </div>
    `;
  }
  
  if (forecast && forecast.length > 0) {
    html += `
      <div class="weather-section-head">
        <h2>近期预报</h2>
      </div>
      <div class="weather-forecast-list">
        ${forecast.map(day => `
          <div class="weather-forecast-day">
            <span class="forecast-date">${day.date}</span>
            <span class="forecast-text">${day.text}</span>
            <span class="forecast-temp">${day.low} / ${day.high}°C</span>
          </div>
        `).join("")}
      </div>
    `;
  } else {
    html += `
      <div class="status-modal-empty">暂无近期预报数据</div>
    `;
  }

  if (indexes.length) {
    html += `
      <div class="weather-section-head">
        <h2>生活指数</h2>
      </div>
      <div class="weather-index-grid">
        ${indexes.slice(0, 8).map(([name, value]) => `
          <div class="weather-index-item">
            <strong>${escapeHtml(name)}</strong>
            <p>${escapeHtml(String(value))}</p>
          </div>
        `).join("")}
      </div>
    `;
  }
  
  html += `</div>`;
  
  openStatusModal("天气详情", html);
}

function updateDashboardChrome(summary, energy, health) {
  const ambientValue = document.getElementById("headerAmbientValue");
  const ambientHumidity = document.getElementById("headerAmbientHumidity");
  const ambientWind = document.getElementById("headerAmbientWind");
  const ambientChip = document.querySelector(".top-chip-ambient");
  const ambientIcon = ambientChip ? ambientChip.querySelector(".top-chip-icon") : null;
  
  if (ambientValue) {
    if (state.weather && state.weather.temperature != null) {
      ambientValue.textContent = `${state.weather.temperature}°C`;
      
      const place = state.weather.location_name || state.weatherConfig?.area_name || "当前";
      const desc = state.weather.text || state.weather.weather || "";
      
      if (ambientHumidity) {
        ambientHumidity.textContent = place;
      }
      
      if (ambientWind) {
        ambientWind.style.display = "none";
      }

      if (ambientChip) {
        ambientChip.classList.add("weather-ready");
      }
      if (ambientIcon) {
        ambientIcon.innerHTML = weatherIconSvg(state.weather);
      }
    } else {
      const averageTemp = summary ? dashboardAverageTemperature(summary.rooms) : { raw: null, text: "--" };
      ambientValue.textContent = averageTemp.text !== "--" ? averageTemp.text : (health ? `${health.score}` : "--");
      
      if (ambientHumidity) {
        ambientHumidity.textContent = state.weatherConfig && state.weatherConfig.area_name
          ? `${state.weatherConfig.area_name} · 加载中`
          : "未配置地区";
      }
      
      if (ambientWind) {
        ambientWind.textContent = "点击配置";
        ambientWind.style.display = "";
      }

      if (ambientChip) {
        ambientChip.classList.remove("weather-ready");
      }
      if (ambientIcon) {
        ambientIcon.innerHTML = defaultWeatherIconSvg();
      }
    }
  }
}

function defaultWeatherIconSvg() {
  return `
    <svg viewBox="0 0 24 24" fill="none">
      <path d="M12 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
      <path d="M12 1.5V3M19.5 4.5 18 6M22.5 12H21M19.5 19.5 18 18M12 22.5V21M4.5 19.5 6 18M1.5 12H3M4.5 4.5 6 6M18 12h.5a2.5 2.5 0 0 1 0 5H10a3 3 0 0 1-3-3v-.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `;
}

function weatherIconSvg(weather) {
  const code = String(weather && weather.weather_code || "").trim();
  if (["00"].includes(code)) {
    return `
      <svg viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.8"/>
        <path d="M12 2.5V5M12 19v2.5M21.5 12H19M5 12H2.5M18.72 5.28l-1.77 1.77M7.05 16.95l-1.77 1.77M18.72 18.72l-1.77-1.77M7.05 7.05 5.28 5.28" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
    `;
  }
  if (["01", "02", "03"].includes(code)) {
    return `
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M8 18h8.5a3.5 3.5 0 0 0 .31-6.99A5.5 5.5 0 0 0 6.33 9.4 4 4 0 0 0 8 18Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M15.5 6.5a3 3 0 0 1 2.96 2.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
    `;
  }
  if (["04", "05", "06", "07", "08", "09", "10", "11", "12", "21", "22", "23", "24", "25"].includes(code)) {
    return `
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M7.5 15.5H17a3.5 3.5 0 0 0 .31-6.99A5 5 0 0 0 7.1 8.7 3.5 3.5 0 0 0 7.5 15.5Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M9 18.5 8 21M13 18.5 12 21M17 18.5 16 21" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
    `;
  }
  if (["13", "14", "15", "16", "17", "26", "27", "28"].includes(code)) {
    return `
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M7.5 14.5H17a3.5 3.5 0 0 0 .31-6.99A5 5 0 0 0 7.1 7.7 3.5 3.5 0 0 0 7.5 14.5Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M9.5 18h.01M12 20h.01M14.5 18h.01" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/>
      </svg>
    `;
  }
  if (["18", "32", "49", "53", "54", "55", "56", "57", "58"].includes(code)) {
    return `
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M5 10.5h14M3.5 14h12M7 17.5h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
    `;
  }
  if (["29", "30", "31"].includes(code)) {
    return `
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M4 9.5h10M8 14h12M5 18.5h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
    `;
  }
  return defaultWeatherIconSvg();
}

function setDashboardQuickControl(tab) {
  state.dashboardQuickControl = ["ac", "light", "fresh", "all"].includes(tab) ? tab : "ac";
  renderDashboard();
}

function syncDashboardTempLabel(value) {
  const label = document.getElementById("dashboardTempValue");
  if (label) {
    label.textContent = `${value}°C`;
  }
}

async function applyDashboardAcTemperature() {
  const input = document.getElementById("dashboardTempRange");
  if (!input) return;
  const target = Math.max(16, Math.min(30, Number(input.value) || 24));
  const rooms = roomsForDisplay().filter((room) => {
    const ac = getMappedRoomDevices(room).ac;
    return ac && ac.domain === "climate";
  });
  if (!rooms.length) {
    showMessage("当前没有可批量调温的 climate 空调。", "warning", true);
    return;
  }
  try {
    showMessage(`正在批量设置空调温度到 ${target}°C...`, "info");
    for (const room of rooms) {
      await requestJson("/api/netcafe/panel/room/action", {
        method: "POST",
        body: JSON.stringify({
          room_id: room.room_id,
          action: "ac_set_temperature",
          value: target,
          persist: false,
        }),
      });
    }
    showMessage(`全部空调已设置到 ${target}°C。`, "success", true);
    await reloadAll(false);
  } catch (error) {
    showMessage(error.message || "批量调温失败。", "error");
  }
}

function renderDashboardQuickPanel(summary) {
  const tab = state.dashboardQuickControl || "ac";
  const averageTemp = dashboardAverageTemperature(summary.rooms);
  const sliderValue = averageTemp.raw != null ? Math.round(averageTemp.raw) : 24;
  const tabs = [
    { key: "ac", label: "空调" },
    { key: "light", label: "灯光" },
    { key: "fresh", label: "新风" },
    { key: "all", label: "全部" },
  ];
  let title = "";
  let meta = "";
  let switchAction = "";
  let isOn = false;
  let extra = "";

  if (tab === "light") {
    title = `全部灯光 (${summary.lightEntities.length})`;
    meta = `已开启 ${summary.lightOn} 盏`;
    switchAction = `batchRoomAction("light", "light_apply_preset", ${JSON.stringify(summary.lightOn ? "full_off" : "full_on")})`;
    isOn = summary.lightOn > 0;
    extra = `
      <div class="dashboard-quick-actions">
        <button class="dashboard-quick-btn amber" type="button" onclick='batchRoomAction("light", "light_apply_preset", "full_on")'>全部全开</button>
        <button class="dashboard-quick-btn blue" type="button" onclick='batchRoomAction("light", "light_apply_preset", "half_on")'>全部部分开启</button>
        <button class="dashboard-quick-btn gray" type="button" onclick='batchRoomAction("light", "light_apply_preset", "full_off")'>全部关闭</button>
      </div>
      <div class="dashboard-quick-note">按参考图保留了设备快捷控制区，灯光支持全开、部分开启、全关三种快速预设。</div>
    `;
  } else if (tab === "fresh") {
    title = `全部新风 (${summary.freshTotal})`;
    meta = `运行中 ${summary.freshOn} 台`;
    switchAction = `batchRoomAction("fresh_air", ${JSON.stringify(summary.freshOn ? "fresh_air_turn_off" : "fresh_air_turn_on")})`;
    isOn = summary.freshOn > 0;
    extra = `
      <div class="dashboard-quick-actions">
        <button class="dashboard-quick-btn green" type="button" onclick='batchRoomAction("fresh_air", "fresh_air_turn_on")'>全部开启</button>
        <button class="dashboard-quick-btn gray" type="button" onclick='batchRoomAction("fresh_air", "fresh_air_turn_off")'>全部关闭</button>
        <button class="dashboard-quick-btn soft" type="button" onclick='openPage("fan")'>进入新风页</button>
      </div>
      <div class="dashboard-quick-note">右侧控制区样式按参考图重构，底层动作仍复用现有批量控制接口。</div>
    `;
  } else if (tab === "all") {
    title = "整店联动";
    meta = `当前有人包厢 ${summary.occupiedRooms} 间`;
    switchAction = 'runControlMode("summer")';
    isOn = summary.occupiedRooms > 0;
    extra = `
      <div class="dashboard-quick-actions">
        <button class="dashboard-quick-btn blue" type="button" onclick='applyDashboardScene("internet")'>上网模式</button>
        <button class="dashboard-quick-btn amber" type="button" onclick='applyDashboardScene("movie")'>观影模式</button>
        <button class="dashboard-quick-btn gray" type="button" onclick='applyDashboardScene("leave")'>闭店模式</button>
        <button class="dashboard-quick-btn green" type="button" onclick='runControlMode("eco")'>节能模式</button>
      </div>
      <div class="dashboard-quick-note">这里的同名按钮已和首页场景卡片保持一致，都会执行对应的灯光、空调和新风联动。</div>
    `;
  } else {
    title = `全部空调 (${summary.acTotal})`;
    meta = `运行中 ${summary.acOn} 台`;
    switchAction = `batchRoomAction("ac", ${JSON.stringify(summary.acOn ? "ac_turn_off" : "ac_turn_on")})`;
    isOn = summary.acOn > 0;
    extra = `
      <div class="dashboard-quick-actions">
        <button class="dashboard-quick-btn blue" type="button" onclick='batchRoomAction("ac", "ac_apply_season", "summer", true)'>制冷</button>
        <button class="dashboard-quick-btn amber" type="button" onclick='batchRoomAction("ac", "ac_apply_season", "winter", true)'>制热</button>
        <button class="dashboard-quick-btn soft" type="button" onclick='openPage("ac")'>精细控制</button>
      </div>
      <div class="dashboard-temp-panel">
        <div class="dashboard-temp-top">
          <span>设定温度</span>
          <strong id="dashboardTempValue">${sliderValue}°C</strong>
        </div>
        <div class="dashboard-temp-row">
          <span>16°C</span>
          <input id="dashboardTempRange" type="range" min="16" max="30" value="${sliderValue}" oninput="syncDashboardTempLabel(this.value)">
          <span>30°C</span>
        </div>
        <button class="dashboard-quick-btn primary wide" type="button" onclick="applyDashboardAcTemperature()">应用到全部空调</button>
      </div>
    `;
  }

  return `
    <div class="card dashboard-quick-card">
      ${renderPanelHeading("设备快捷控制")}
      <div class="dashboard-quick-tabs">
        ${tabs.map((item) => `
          <button class="dashboard-quick-tab ${item.key === tab ? "active" : ""}" type="button" onclick='setDashboardQuickControl(${JSON.stringify(item.key)})'>${escapeHtml(item.label)}</button>
        `).join("")}
      </div>
      <div class="dashboard-quick-head">
        <div>
          <div class="dashboard-quick-target">${escapeHtml(title)}</div>
          <div class="dashboard-quick-meta">${escapeHtml(meta)}</div>
        </div>
        <button class="dashboard-master-switch ${isOn ? "on" : ""}" type="button" onclick='${switchAction}' aria-label="主开关">
          <span></span>
        </button>
      </div>
      ${extra}
    </div>
  `;
}

function renderDashboardScenePanel() {
  const scenes = [
    { icon: "上", title: "上网模式", desc: "灯光亮度 80%，空调 24°C，新风中档", action: 'applyDashboardScene("internet")', tone: "blue" },
    { icon: "影", title: "观影模式", desc: "灯光亮度 60%，空调 23°C，新风低档", action: 'applyDashboardScene("movie")', tone: "amber" },
    { icon: "洁", title: "清洁模式", desc: "灯光全开，空调关闭，新风高档", action: 'applyDashboardScene("clean")', tone: "gray" },
    { icon: "闭", title: "闭店模式", desc: "关闭所有空调、新风、灯光设备", action: 'applyDashboardScene("leave")', tone: "green" },
  ];
  return `
    <div class="card dashboard-scene-card">
      ${renderPanelHeading("场景模式", `<button class="panel-link-btn" type="button" onclick='openPage("room")'>更多</button>`)}
      <div class="dashboard-scene-list">
        ${scenes.map((scene) => `
          <button class="dashboard-scene-item ${scene.tone}" type="button" onclick='${scene.action}'>
            <span class="dashboard-scene-icon">${escapeHtml(scene.icon)}</span>
            <span class="dashboard-scene-copy">
              <strong>${escapeHtml(scene.title)}</strong>
              <small>${escapeHtml(scene.desc)}</small>
            </span>
          </button>
        `).join("")}
      </div>
    </div>
  `;
}

function renderDashboardEnvironmentPanel(summary, health, issues, averageTemp, occupancyRate, lightRate, freshRate, onlineComputers, totalComputers) {
  const visibleIssues = (Array.isArray(issues) ? issues : []).filter((item) => Number(item.count || 0) > 0).slice(0, 3);
  return `
    <section class="card dashboard-env-card">
      ${renderPanelHeading("环境监测", `<button class="panel-link-btn" type="button" onclick='openPage("fan")'>更多</button>`)}
      <div class="dashboard-env-body">
        ${renderDashboardGauge(health)}
        <div class="dashboard-env-metrics">
          <div><span>平均温度</span><strong>${escapeHtml(averageTemp.text)}</strong></div>
          <div><span>包厢占用率</span><strong>${escapeHtml(`${occupancyRate}%`)}</strong></div>
          <div><span>灯光开启率</span><strong>${escapeHtml(`${lightRate}%`)}</strong></div>
          <div><span>新风运行率</span><strong>${escapeHtml(`${freshRate}%`)}</strong></div>
          <div><span>在线终端</span><strong>${escapeHtml(`${onlineComputers}/${totalComputers || 0}`)}</strong></div>
          <div><span>已配置房间</span><strong>${escapeHtml(`${summary.configuredRooms}/${summary.totalRooms}`)}</strong></div>
        </div>
        ${visibleIssues.length ? `
          <div class="dashboard-env-issues">
            ${visibleIssues.map((item) => `
              <button class="dashboard-env-issue ${escapeHtml(item.level === "danger" ? "danger" : item.level === "warn" ? "warn" : "info")}" type="button" onclick='openIssueDetailModal(${JSON.stringify(item.key)})'>
                <span>${escapeHtml(item.title)}</span>
                <strong>${escapeHtml(String(item.count || 0))}</strong>
              </button>
            `).join("")}
          </div>
        ` : `<div class="dashboard-env-empty">当前没有异常项，环境状态稳定。</div>`}
      </div>
    </section>
  `;
}

function renderDashboardEnergyPanel(energy, currentLoad, peakLoad, dailyEnergy, monthlyEnergy, dailyCost, monthlyCost, dailySummary) {
  const entityItems = currentEnergyStatEntities(energy);
  const priceValue = energy && energy.price_per_kwh != null ? Number(energy.price_per_kwh) : 0;
  return `
    <section class="card dashboard-energy-card">
      ${renderPanelHeading("能耗统计", `
        <div class="dashboard-energy-actions">
          <button class="panel-link-btn" type="button" onclick="openPowerEstimateModal()">统计实体</button>
          <div class="dashboard-energy-price-wrap">
            <button class="panel-link-btn" type="button" onclick="toggleDashboardPriceEditor()" aria-expanded="${state.dashboardPriceEditorOpen ? "true" : "false"}">电费设置</button>
            <div id="dashboardEnergyPricePopover" class="energy-price-quick energy-price-popover dashboard-energy-price-popover ${state.dashboardPriceEditorOpen ? "show" : ""}">
              <label for="dashboardEnergyPriceQuick">电价(元/度)</label>
              <input id="dashboardEnergyPriceQuick" type="number" min="0" step="0.01" value="${escapeHtml(String(priceValue))}">
              <button class="btn btn-primary" type="button" onclick="saveDashboardPriceQuick()">保存</button>
            </div>
          </div>
          <button class="panel-link-btn" type="button" onclick='openEnergyCostModal("month")'>电费趋势</button>
        </div>
      `)}
      <div class="dashboard-energy-body">
        <div class="dashboard-energy-highlight">
          <div class="dashboard-energy-value">${escapeHtml(dailyEnergy === "--" ? currentLoad : dailyEnergy)}</div>
          <div class="dashboard-energy-unit">${dailyEnergy === "--" ? "kW" : "kWh"}</div>
          <p>${escapeHtml(dailyEnergy === "--" ? "当前估算负载" : "今日总用电量")}</p>
          <div class="dashboard-energy-meta">
            <span>峰值 ${escapeHtml(`${peakLoad} kW`)}</span>
            <span>${escapeHtml(monthlyEnergy === "--" ? "本月电量 --" : `本月 ${monthlyEnergy} kWh`)}</span>
            <span>${escapeHtml(priceValue > 0 ? `当前电价 ¥ ${formatMetricNumber(priceValue, 2)}/度` : "当前电价未设置")}</span>
          </div>
        </div>
        <div class="dashboard-energy-chart">
          <canvas id="loadTrendChart"></canvas>
        </div>
      </div>
      <div class="dashboard-energy-stat-grid">
        <button class="dashboard-energy-stat primary" type="button" onclick='openEnergyCostModal("day")'>
          <span>今日电费估算</span>
          <strong>${escapeHtml(dailyCost === "--" ? "--" : `¥ ${dailyCost}`)}</strong>
          <small>${escapeHtml(dailyEnergy === "--" ? "等待能耗数据" : `基于 ${dailyEnergy} kWh 估算`)}</small>
        </button>
        <button class="dashboard-energy-stat" type="button" onclick='openEnergyCostModal("month")'>
          <span>本月电费估算</span>
          <strong>${escapeHtml(monthlyCost === "--" ? "--" : `¥ ${monthlyCost}`)}</strong>
          <small>${escapeHtml(monthlyEnergy === "--" ? "等待能耗数据" : `基于 ${monthlyEnergy} kWh 估算`)}</small>
        </button>
        <button class="dashboard-energy-stat" type="button" onclick="openPowerEstimateModal()">
          <span>当前统计来源</span>
          <strong>${escapeHtml(currentLoad)} kW</strong>
          <small>${escapeHtml(entityItems.length ? "点击查看实体明细" : "点击查看当前绑定实体")}</small>
        </button>
      </div>
      <div class="dashboard-section-note">保存电价后，首页会按当前电量统计自动估算日电费和月电费。</div>
    </section>
  `;
}

function renderDashboardLogPanel(logs, allLogs = logs) {
  const items = Array.isArray(logs) ? logs : [];
  const allItems = Array.isArray(allLogs) ? allLogs : items;
  const warnCount = allItems.filter((item) => toneForLog(item) === "warn").length;
  const autoCount = allItems.filter((item) => sourceLabel(item) === "自动").length;
  const manualCount = allItems.filter((item) => sourceLabel(item) === "手动").length;
  return `
    <section class="card dashboard-log-card">
      ${renderPanelHeading("运行日志", `
        <div class="dashboard-log-stats">
          <span class="dashboard-log-chip">实时流</span>
          <button class="panel-link-btn" type="button" onclick="openDashboardLogModal()">查看全部</button>
        </div>
      `)}
      <div class="dashboard-log-overview">
        <button class="dashboard-log-stat" type="button" onclick='openDashboardLogModal("all")'>
          <span>今日总数</span>
          <strong>${allItems.length}</strong>
          <small>首页 ${items.length} 条</small>
        </button>
        <button class="dashboard-log-stat warn" type="button" onclick='openDashboardLogModal("warn")'>
          <span>异常提醒</span>
          <strong>${warnCount}</strong>
          <small>优先处理</small>
        </button>
        <button class="dashboard-log-stat" type="button" onclick='openDashboardLogModal("auto")'>
          <span>自动执行</span>
          <strong>${autoCount}</strong>
          <small>联动动作</small>
        </button>
        <button class="dashboard-log-stat" type="button" onclick='openDashboardLogModal("manual")'>
          <span>手动操作</span>
          <strong>${manualCount}</strong>
          <small>人工记录</small>
        </button>
      </div>
      <div class="dashboard-log-feed dashboard-log-panel-feed">
        ${renderDashboardLogFeed(items, "日志明细")}
      </div>
    </section>
  `;
}

function openDashboardLogModal(filter = "all") {
  const logs = currentTodayLogs(null);
  const warnCount = logs.filter((item) => toneForLog(item) === "warn").length;
  const autoCount = logs.filter((item) => sourceLabel(item) === "自动").length;
  const manualCount = logs.filter((item) => sourceLabel(item) === "手动").length;
  const filteredLogs = logs.filter((item) => {
    if (filter === "warn") return toneForLog(item) === "warn";
    if (filter === "auto") return sourceLabel(item) === "自动";
    if (filter === "manual") return sourceLabel(item) === "手动";
    return true;
  });
  const titleMap = {
    all: "全部运行日志",
    warn: "异常提醒日志",
    auto: "自动执行日志",
    manual: "手动操作日志",
  };
  openStatusModal(titleMap[filter] || "全部运行日志", `
    <div class="status-modal-meta">
      <div class="status-modal-stat"><span>今日总数</span><strong>${logs.length}</strong></div>
      <div class="status-modal-stat"><span>异常提醒</span><strong>${warnCount}</strong></div>
      <div class="status-modal-stat"><span>自动执行</span><strong>${autoCount}</strong></div>
      <div class="status-modal-stat"><span>手动操作</span><strong>${manualCount}</strong></div>
    </div>
    <div class="dashboard-log-feed dashboard-log-modal-feed">
      ${renderDashboardLogFeed(filteredLogs, "全部日志", "dashboardLogModalScroll")}
    </div>
  `);
}

function renderSettingsPageHead(title, description = "", actionsHtml = "", metaHtml = "") {
  return `
    <div class="settings-page-head">
      <div>
        <h3>${escapeHtml(title)}</h3>
        ${description ? `<p>${escapeHtml(description)}</p>` : ""}
      </div>
      ${metaHtml || actionsHtml}
    </div>
  `;
}

function triggerModeLabel(value) {
  if (value === "sensor") return "人在传感器";
  if (value === "hybrid") return "混合判断";
  return "device_tracker";
}

function renderSharedLinkagePanel(roomConfig, sensorItems, trackerItems) {
  const automation = roomConfig.automation || {};
  const triggerMode = triggerModeValue(automation.trigger_mode);
  return `
    <div class="settings-linkage-shell">
      <div class="settings-linkage-title">联动判断</div>
      <div class="settings-linkage-grid compact">
        <div class="field">
          <label>模式</label>
          <select id="linkTriggerMode">
            <option value="device_tracker" ${triggerMode === "device_tracker" ? "selected" : ""}>device_tracker</option>
            <option value="sensor" ${triggerMode === "sensor" ? "selected" : ""}>人在传感器</option>
            <option value="hybrid" ${triggerMode === "hybrid" ? "selected" : ""}>混合模式</option>
          </select>
        </div>
        <div class="field">
          <label>传感器</label>
          <select id="presenceSensorEntity">${selectOptions(sensorItems, automation.presence_sensor_entity, "未选择传感器")}</select>
        </div>
        <div class="field">
          <label>Tracker</label>
          <select id="deviceTrackerEntity">${selectOptions(trackerItems, automation.device_tracker_entity, "未选择 Tracker")}</select>
        </div>
      </div>
    </div>
  `;
}

function linkageTargetCard(name, value, label, checked, description = "") {
  return `
    <label class="linkage-target-card">
      <input type="checkbox" name="${escapeHtml(name)}" value="${escapeHtml(value)}" ${checked ? "checked" : ""}>
      <div>
        <strong>${escapeHtml(label)}</strong>
        ${description ? `<span>${escapeHtml(description)}</span>` : ""}
      </div>
    </label>
  `;
}

function renderHelperNote(text, extraClass = "") {
  return `<div class="helper${extraClass ? ` ${extraClass}` : ""}">${escapeHtml(text)}</div>`;
}

function readableLightingPresetLabel(value) {
  const text = String(value || "").trim().toLowerCase();
  if (text === "full_on" || text === "fullon" || text === "full-on") return "全开";
  if (text === "half_on" || text === "halfon" || text === "half-on") return "部分开启";
  if (text === "full_off" || text === "fulloff" || text === "full-off") return "全关";
  return String(value || "").trim();
}

function formatLogMessage(log) {
  const raw = String(log && (log.message || log.action) || "").trim();
  if (!raw) return "--";
  const presetMatch = raw.match(/^已执行灯光预设\s+(.+)$/i);
  if (presetMatch) {
    return `已执行灯光：${readableLightingPresetLabel(presetMatch[1])}`;
  }
  return raw
    .replace(/已执行灯光预设\s+full[_\s-]*on/gi, "已执行灯光：全开")
    .replace(/已执行灯光预设\s+half[_\s-]*on/gi, "已执行灯光：部分开启")
    .replace(/已执行灯光预设\s+full[_\s-]*off/gi, "已执行灯光：全关");
}

function renderDashboardLogFeed(logs, title = "今日运行日志", scrollId = "dashboardLogScroll") {
  const items = Array.isArray(logs) ? logs : [];
  if (!items.length) {
    return `
      <div class="dashboard-log-empty">今天还没有运行日志。</div>
    `;
  }
  const toneForLog = (log) => {
    const source = String(log && log.source || "").toLowerCase();
    const action = String(log && log.action || "").toLowerCase();
    const message = String(log && log.message || "").toLowerCase();
    if (message.includes("失败") || message.includes("离线") || action.includes("off")) return "warn";
    if (source === "automation" || message.includes("开启") || action.includes("turn_on")) return "ok";
    return "info";
  };
  const sourceLabel = (log) => {
    const source = String(log && log.source || "").toLowerCase();
    if (source === "automation") return "自动";
    if (source === "manual") return "手动";
    return source ? source : "事件";
  };
  const describeLog = (log) => {
    const time = formatTime(log.timestamp);
    const source = sourceLabel(log);
    const room = log.room_name || "--";
    const message = formatLogMessage(log);
    return `${time} ${source} ${room} ${message}`;
  };
  return `
    <div class="dashboard-log-scroll" id="${escapeHtml(scrollId)}">
      <div class="dashboard-log-list">
        ${items.map((log) => `
          <div class="dashboard-log-item ${toneForLog(log)}" title="${escapeHtml(describeLog(log))}">
            <span class="dashboard-log-time">${escapeHtml(formatTime(log.timestamp))}</span>
            <span class="dashboard-log-source">${escapeHtml(sourceLabel(log))}</span>
            <span class="dashboard-log-room">${escapeHtml(log.room_name || "--")}</span>
            <span class="dashboard-log-text" title="${escapeHtml(formatLogMessage(log))}">${escapeHtml(formatLogMessage(log))}</span>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function ensureCurrentRoom() {
  const rooms = roomsForDisplay();
  if (!rooms.length) {
    state.currentRoomId = null;
    return;
  }
  if (!state.currentRoomId || !rooms.some((item) => item.room_id === state.currentRoomId)) {
    state.currentRoomId = rooms[0].room_id;
  }
}

function renderDashboard() {
  const root = document.getElementById("page-dashboard");
  if (!isConnectionConfigured()) {
    updateDashboardChrome(null, null, null);
    root.innerHTML = renderEmptyState(
      "请通过管理系统打开此页",
      "当前浏览器上下文不是智慧网吧的同源页面，无法直接读取本机数据。请从集成入口访问。"
    );
    return;
  }

  const rooms = roomsForDisplay();
  if (!rooms.length) {
    updateDashboardChrome(null, null, null);
    root.innerHTML = renderEmptyState("暂无包厢数据", "当前 overview 接口没有返回任何房间记录。");
    return;
  }

  const summary = summarizeRooms(rooms);
  const {
    totalRooms,
    occupiedRooms,
    configuredRooms,
    idleRooms,
    acTotal,
    acOn,
    acOffline,
    lightEntities,
    lightOn,
    lightOffline,
    freshTotal,
    freshOn,
    freshOffline,
    totalComputers,
    onlineComputers,
  } = summary;
  const energy = currentResolvedEnergySummary();
  const health = dashboardHealthSummary(summary);
  const averageTemp = dashboardAverageTemperature(summary.rooms);
  const realtimePowerKw = energy && energy.realtime_power_kw != null ? Number(energy.realtime_power_kw) : null;
  const powerSeries = realtimePowerKw != null
    ? Array.from({ length: 12 }, (_, index) => Number(Math.max(0, realtimePowerKw + Math.sin((index / 11) * Math.PI * 1.4) * Math.max(realtimePowerKw * 0.05, 0.08) + (((index % 3) - 1) * Math.max(realtimePowerKw * 0.02, 0.03))).toFixed(2)))
    : buildEstimatedPowerSeries(summary.rooms);
  const currentLoad = realtimePowerKw != null ? realtimePowerKw.toFixed(2) : powerSeries[powerSeries.length - 1].toFixed(1);
  const peakLoad = Math.max(...powerSeries).toFixed(2);
  const dailyEnergy = energy && energy.daily_energy_kwh_effective != null ? formatMetricNumber(energy.daily_energy_kwh_effective, 2) : "--";
  const monthlyEnergy = energy && energy.monthly_energy_kwh_effective != null ? formatMetricNumber(energy.monthly_energy_kwh_effective, 2) : "--";
  const dailyCost = energy && energy.daily_cost_effective != null ? formatMetricNumber(energy.daily_cost_effective, 2) : "--";
  const monthlyCost = energy && energy.monthly_cost_effective != null ? formatMetricNumber(energy.monthly_cost_effective, 2) : "--";
  const issues = buildDashboardIssueSummary(summary);
  const todayLogs = currentTodayLogs(null);
  const dashboardLogs = todayLogs.slice(0, 5);
  const dailySummary = state.dailySummary && Array.isArray(state.dailySummary.items) ? state.dailySummary.items.slice(0, 3) : [];
  const roomSort = dashboardRoomSortValue(state.dashboardRoomSort);
  const sortedDashboardRooms = sortDashboardRooms(summary.rooms, roomSort);
  const featuredRooms = sortedDashboardRooms.slice(0, 8);
  const occupancyRate = totalRooms ? Math.round((occupiedRooms / totalRooms) * 100) : 0;
  const acRate = acTotal ? Math.round((acOn / acTotal) * 100) : 0;
  const lightRate = lightEntities.length ? Math.round((lightOn / lightEntities.length) * 100) : 0;
  const freshRate = freshTotal ? Math.round((freshOn / freshTotal) * 100) : 0;
  const terminalRate = totalComputers ? Math.round((onlineComputers / totalComputers) * 100) : 0;
  const onlineTerminalItems = computerPresenceEntries(summary.rooms, true);
  const offlineTerminalItems = computerPresenceEntries(summary.rooms, false);
  updateDashboardChrome(summary, energy, health);

  root.innerHTML = `
    <div class="dashboard-home">
      <section class="card dashboard-summary-strip">
        ${renderDashboardSummaryTile("包厢总数", `${totalRooms} 间`, `使用中 ${occupiedRooms} 间`, "blue", occupancyRate, `${occupiedRooms}/${totalRooms || 0}`)}
        ${renderDashboardSummaryTile("空调设备", `${acTotal} 台`, `运行中 ${acOn} 台`, "cool", acRate, `${acOn}/${acTotal || 0}`)}
        ${renderDashboardSummaryTile("灯光设备", `${lightEntities.length} 盏`, `开启中 ${lightOn} 盏`, "amber", lightRate, `${lightOn}/${lightEntities.length || 0}`)}
        ${renderDashboardSummaryTile("新风设备", `${freshTotal} 台`, `运行中 ${freshOn} 台`, "green", freshRate, `${freshOn}/${freshTotal || 0}`)}
        ${renderDashboardSummaryTile("在线终端", `${onlineComputers} 台`, `总终端 ${totalComputers} 台`, "violet", terminalRate, `${onlineComputers}/${totalComputers || 0}`)}
        ${renderDashboardSummaryTile("运行健康", health.label, `${dashboardOnlineRate(summary)}% 在线率`, "mint", health.score, `${health.score}%`)}
      </section>

      <section class="card">
        ${renderPanelHeading("终端在线明细", `
          <div class="dashboard-panel-tools">
            <span class="chip">离线确认 ${escapeHtml(String(currentGlobalSettings().automation.offline_confirm_seconds || 45))} 秒</span>
          </div>
        `)}
        <div class="ref-setting-pair-grid">
          ${renderComputerPresenceTrigger("当前在线终端", onlineTerminalItems, "当前没有在线终端。", "点击查看当前在线终端列表。")}
          ${renderComputerPresenceTrigger("当前离线终端", offlineTerminalItems, "当前没有离线终端。", "点击查看当前离线终端列表。")}
        </div>
      </section>

      <div class="dashboard-main-grid">
        <div class="dashboard-top-grid">
          <section class="card dashboard-room-board">
            ${renderPanelHeading("包厢状态总览", `
              <div class="dashboard-panel-tools">
                <label class="dashboard-sort-wrap">
                  <span>排序</span>
                  <select class="dashboard-sort-select" onchange='setDashboardRoomSort(this.value)'>
                    <option value="occupied" ${roomSort === "occupied" ? "selected" : ""}>有人优先</option>
                    <option value="number" ${roomSort === "number" ? "selected" : ""}>包厢序号</option>
                    <option value="name" ${roomSort === "name" ? "selected" : ""}>房间名称</option>
                    <option value="devices" ${roomSort === "devices" ? "selected" : ""}>活跃设备</option>
                  </select>
                </label>
                <button class="panel-link-btn" type="button" onclick='openPage("room")'>查看全部</button>
              </div>
            `)}
            <div class="dashboard-room-grid">
              ${featuredRooms.map((room) => renderDashboardSuiteCard(room)).join("")}
            </div>
            ${summary.rooms.length > featuredRooms.length ? `<button class="dashboard-more-btn" type="button" onclick='openPage("room")'>查看更多</button>` : ""}
          </section>

          <div class="dashboard-control-stack">
            ${renderDashboardQuickPanel(summary)}
            ${renderDashboardScenePanel()}
          </div>
        </div>

        <div class="dashboard-bottom-grid">
          ${renderDashboardEnergyPanel(energy, currentLoad, peakLoad, dailyEnergy, monthlyEnergy, dailyCost, monthlyCost, dailySummary)}
          ${renderDashboardLogPanel(dashboardLogs, todayLogs)}
        </div>
      </div>
    </div>
  `;
  const loadTrendChart = document.getElementById("loadTrendChart");
  if (loadTrendChart) {
    loadTrendChart.dataset.values = JSON.stringify(powerSeries);
    drawLoadTrendChart(loadTrendChart, powerSeries);
  }
  updateDashboardLogScroll(dashboardLogs);
}

function renderRoomPage() {
  const root = document.getElementById("page-room");
  if (!isConnectionConfigured()) {
    root.innerHTML = renderEmptyState("无法读取房间数据", "请先通过管理系统同源地址打开当前页面。");
    return;
  }
  const rooms = roomsForDisplay().filter((room) => hasVisibleRoomDevices(room));
  if (!rooms.length) {
    root.innerHTML = renderEmptyState("暂无可显示的房间设备", "当前筛选逻辑下没有识别到可展示的空调、灯光或新风设备。");
    return;
  }
  const filters = pageFilterState("room");
  const filteredRooms = rooms.filter((room) => matchesKeywordFilter(roomFilterText(room), filters.include, filters.exclude));
  const summary = summarizeRooms(filteredRooms);
  const { rooms: visibleRooms, totalRooms, configuredRooms, occupiedRooms } = summary;
  const onlineTerminalItems = computerPresenceEntries(visibleRooms, true);
  const offlineTerminalItems = computerPresenceEntries(visibleRooms, false);
  root.innerHTML = `
    <div class="room-shell">
      <div class="section-title">
        <div>
          <h2>房间概览</h2>
          <p>直接查看设备运行状态，并在卡片内完成快速控制。</p>
        </div>
        <div class="section-title-tools room-title-tools">
          ${renderDeviceFilterBar("room", "包含：单人包、206、电竞", "排除：双人包、测试", "支持按房间名、覆盖范围和已绑定设备名称筛选。", true)}
          <div class="chip-list">
            <span class="chip">总房间 ${totalRooms}</span>
            <span class="chip">已映射 ${configuredRooms}</span>
            <span class="chip">当前有人 ${occupiedRooms}</span>
            <span class="chip">在线终端 ${onlineTerminalItems.length}</span>
          </div>
        </div>
      </div>
      <div class="suite-room-grid">
        ${visibleRooms.length ? visibleRooms.map((room) => renderRoomReferenceCard(room)).join("") : `<div class="card list-filter-empty">当前筛选条件下没有匹配的房间。</div>`}
      </div>
    </div>
  `;
}

function firstFiniteNumber(...values) {
  for (const value of values) {
    const num = Number(value);
    if (Number.isFinite(num)) return num;
  }
  return null;
}

function formatMetricNumber(value, digits = 0) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "--";
  if (digits > 0) {
    return num.toFixed(digits).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
  }
  return String(Math.round(num));
}

function uiModeLabel(value) {
  const raw = String(value || "").trim();
  if (!raw) return "--";
  const normalized = raw.toLowerCase();
  const alias = {
    auto: "自动",
    cool: "制冷",
    heat: "制热",
    dry: "除湿",
    fan_only: "送风",
    fan: "送风",
    off: "关闭",
    on: "开启",
    low: "低档",
    medium: "中档",
    high: "高档",
    turbo: "强力",
    swing: "扫风",
  };
  return alias[normalized] || raw.replace(/_/g, " ");
}

function roomVisualCode(room) {
  const coverage = roomCoverageText(room);
  if (coverage && coverage !== displayRoomName(room)) return coverage;
  return String(room && (room.room_id || room.entry_title || displayRoomName(room)) || "--");
}

function lightColorTemperatureKelvin(light) {
  if (!light) return null;
  const attrs = light.attributes || {};
  const kelvin = firstFiniteNumber(light.color_temp_kelvin, attrs.color_temp_kelvin);
  if (kelvin != null) return kelvin;
  const mired = firstFiniteNumber(light.color_temp, attrs.color_temp);
  if (mired != null && mired > 0) return Math.round(1000000 / mired);
  return null;
}

function lightSupportsColorTemperature(light) {
  if (!light) return false;
  const attrs = light.attributes || {};
  const colorModes = Array.isArray(light.supported_color_modes)
    ? light.supported_color_modes
    : (Array.isArray(attrs.supported_color_modes) ? attrs.supported_color_modes : []);
  if (colorModes.some((mode) => String(mode || "").toLowerCase() === "color_temp")) return true;
  if (firstFiniteNumber(light.min_color_temp_kelvin, attrs.min_color_temp_kelvin, light.max_color_temp_kelvin, attrs.max_color_temp_kelvin) != null) return true;
  if (firstFiniteNumber(light.min_mireds, attrs.min_mireds, light.max_mireds, attrs.max_mireds) != null) return true;
  return lightColorTemperatureKelvin(light) != null;
}

function lightColorTemperatureRange(light) {
  const attrs = light && light.attributes ? light.attributes : {};
  const minKelvin = firstFiniteNumber(
    light && light.min_color_temp_kelvin,
    attrs.min_color_temp_kelvin
  );
  const maxKelvin = firstFiniteNumber(
    light && light.max_color_temp_kelvin,
    attrs.max_color_temp_kelvin
  );
  const minMireds = firstFiniteNumber(light && light.min_mireds, attrs.min_mireds);
  const maxMireds = firstFiniteNumber(light && light.max_mireds, attrs.max_mireds);
  const fromMireds = minMireds != null && maxMireds != null
    ? {
        min: Math.round(1000000 / Math.max(maxMireds, 1)),
        max: Math.round(1000000 / Math.max(minMireds, 1)),
      }
    : null;
  const min = Number.isFinite(minKelvin) ? minKelvin : (fromMireds ? fromMireds.min : 2700);
  const max = Number.isFinite(maxKelvin) ? maxKelvin : (fromMireds ? fromMireds.max : 6500);
  return {
    min: Math.max(2000, Math.min(min, max)),
    max: Math.max(min, max),
  };
}

function clampColorTemperature(kelvin, light) {
  const range = lightColorTemperatureRange(light);
  return Math.max(range.min, Math.min(range.max, Math.round(Number(kelvin) || 0)));
}

function lightColorTemperatureOptions(light) {
  const range = lightColorTemperatureRange(light);
  const seeds = [
    { label: "暖黄", kelvin: 2700 },
    { label: "暖白", kelvin: 3000 },
    { label: "自然光", kelvin: 4000 },
    { label: "日光", kelvin: 5000 },
    { label: "冷白", kelvin: 6500 },
  ];
  const values = [];
  for (const item of seeds) {
    const kelvin = clampColorTemperature(item.kelvin, light);
    if (!values.some((entry) => entry.kelvin === kelvin)) {
      values.push({ label: item.label, kelvin });
    }
  }
  if (range.min < values[0].kelvin) {
    values.unshift({ label: "最暖", kelvin: range.min });
  }
  if (range.max > values[values.length - 1].kelvin) {
    values.push({ label: "最冷", kelvin: range.max });
  }
  return values;
}

function lightColorTemperatureTone(kelvin) {
  if (kelvin == null) return "neutral";
  if (kelvin >= 5600) return "cool";
  if (kelvin >= 3800) return "neutral";
  return "warm";
}

function lightSupportsColor(light) {
  if (!light) return false;
  const attrs = light.attributes || {};
  const colorModes = Array.isArray(light.supported_color_modes)
    ? light.supported_color_modes
    : (Array.isArray(attrs.supported_color_modes) ? attrs.supported_color_modes : []);
  const namedModes = ["hs", "rgb", "rgbw", "rgbww", "xy"];
  if (colorModes.some((mode) => namedModes.includes(String(mode || "").toLowerCase()))) return true;
  return Array.isArray(attrs.rgb_color) || Array.isArray(attrs.hs_color) || Array.isArray(light.rgb_color) || Array.isArray(light.hs_color);
}

function normalizeHexColor(value) {
  const raw = String(value || "").trim();
  const hex = raw.replace(/^#/, "");
  if (!/^[0-9a-f]{6}$/i.test(hex)) return null;
  return `#${hex.toLowerCase()}`;
}

function lightColorPresets() {
  return [
    { label: "暖金", value: "#f5b041" },
    { label: "珊瑚", value: "#ff7a59" },
    { label: "玫红", value: "#ec4899" },
    { label: "紫晶", value: "#8b5cf6" },
    { label: "冰蓝", value: "#60a5fa" },
    { label: "青绿", value: "#2dd4bf" },
    { label: "清白", value: "#f8fafc" },
  ];
}

function hexToRgbTriplet(hex) {
  const normalized = normalizeHexColor(hex);
  if (!normalized) return null;
  const value = normalized.slice(1);
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16),
  ];
}

function lightCurrentColorHex(light) {
  const attrs = light && light.attributes ? light.attributes : {};
  const rgb = Array.isArray(light && light.rgb_color)
    ? light.rgb_color
    : (Array.isArray(attrs.rgb_color) ? attrs.rgb_color : null);
  if (Array.isArray(rgb) && rgb.length >= 3) {
    return `#${rgb.slice(0, 3).map((item) => Math.max(0, Math.min(255, Number(item) || 0)).toString(16).padStart(2, "0")).join("")}`;
  }
  return null;
}

function lightControlCapabilities(light) {
  return {
    canDim: lightSupportsBrightness(light),
    canColorTemp: lightSupportsColorTemperature(light),
    canColor: lightSupportsColor(light),
  };
}

function lightUiName(light) {
  if (!light) return "--";
  return entityOwnName(light);
}

function lightEntitySummary(room, light) {
  const roomName = displayRoomName(room);
  const entityId = light && light.entity_id ? light.entity_id : "--";
  const type = light && light.domain ? light.domain : "light";
  return {
    roomName,
    entityId,
    type,
  };
}

function buildSparklinePlot(values, width = 320, height = 112, padding = 14) {
  const items = (values || []).map((item) => Number(item)).filter((item) => Number.isFinite(item));
  if (!items.length) {
    return { width, height, path: "", areaPath: "", lastX: padding, lastY: height / 2 };
  }
  const min = Math.min(...items);
  const max = Math.max(...items);
  const range = Math.max(max - min, 1);
  const spanX = Math.max(width - padding * 2, 1);
  const spanY = Math.max(height - padding * 2, 1);
  const points = items.map((value, index) => {
    const ratioX = items.length === 1 ? 0 : index / (items.length - 1);
    const x = padding + (ratioX * spanX);
    const y = height - padding - (((value - min) / range) * spanY);
    return { x, y };
  });
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(" ");
  const areaPath = `${path} L${points[points.length - 1].x.toFixed(2)} ${(height - padding).toFixed(2)} L${points[0].x.toFixed(2)} ${(height - padding).toFixed(2)} Z`;
  const last = points[points.length - 1];
  return { width, height, path, areaPath, lastX: last.x, lastY: last.y };
}

function syntheticClimateCurve(currentTemp, targetTemp, tone = "cool") {
  const base = firstFiniteNumber(currentTemp, targetTemp, 24) ?? 24;
  const target = firstFiniteNumber(targetTemp, currentTemp, base) ?? base;
  const drift = target - base;
  const offsets = tone === "heat"
    ? [-1.2, -1.0, -0.5, 0.2, 0.6, drift * 0.6, drift * 0.85]
    : tone === "dry"
      ? [0.7, 0.4, 0.1, -0.3, -0.2, drift * 0.25, drift * 0.5]
      : tone === "offline"
        ? [0.1, 0.1, 0, 0, 0, 0.1, 0]
        : [-0.2, -0.5, -0.8, -0.3, 0.4, drift * 0.55, drift * 0.85];
  return offsets.map((offset) => Number((base + offset).toFixed(1)));
}

function summarizeLightGroup(room) {
  const lights = getMappedRoomDevices(room).lights;
  const activeLights = lights.filter((light) => light && light.is_on);
  const dimmableLights = lights.filter((light) => lightSupportsBrightness(light));
  const brightnessValues = activeLights.map((light) => safeNumber(light.brightness_pct, 100));
  const temperatureValues = activeLights.map((light) => lightColorTemperatureKelvin(light)).filter((value) => Number.isFinite(value));
  const primaryLight = dimmableLights.find((light) => light && light.is_on) || dimmableLights[0] || lights[0] || null;
  const averageBrightness = brightnessValues.length
    ? Math.round(brightnessValues.reduce((sum, value) => sum + value, 0) / brightnessValues.length)
    : 0;
  const averageKelvin = temperatureValues.length
    ? Math.round((temperatureValues.reduce((sum, value) => sum + value, 0) / temperatureValues.length) / 50) * 50
    : 4000;
  const sceneLabel = !activeLights.length
    ? "休眠场景"
    : averageBrightness >= 80
      ? "全亮场景"
      : averageBrightness >= 45
        ? "氛围场景"
        : "柔光场景";
  const tone = !activeLights.length ? "sleep" : averageKelvin >= 4700 ? "cool" : averageBrightness >= 70 ? "gold" : "amber";
  return { lights, activeLights, dimmableLights, primaryLight, averageBrightness, averageKelvin, sceneLabel, tone };
}

function renderSampleLightPageCard(room, light) {
  const statusText = light && light.available === false || light && light.exists === false
    ? "离线"
    : light && light.is_on
      ? "已开启"
      : "已关闭";
  const statusClass = light && light.available === false || light && light.exists === false
    ? "offline"
    : light && light.is_on
      ? "on"
      : "off";
  return `
    <div
      class="card sample-light-card light-entity-card ${light && light.is_on ? "on" : ""} ${statusClass === "offline" ? "offline" : ""}"
      role="button"
      tabindex="0"
      onclick='openLightControlModal(${JSON.stringify(room.room_id)}, ${JSON.stringify(light && light.entity_id)})'
      onkeydown='if(event.key === "Enter" || event.key === " "){ event.preventDefault(); openLightControlModal(${JSON.stringify(room.room_id)}, ${JSON.stringify(light && light.entity_id)}); }'
    >
      <div class="sample-light-card-header">
        <div class="sample-light-card-name">
          <span class="sample-light-card-dot ${statusClass}"></span>
          <span>${escapeHtml(lightUiName(light))}</span>
        </div>
        <button
          class="sample-light-card-toggle ${light && light.is_on ? "on" : ""}"
          type="button"
          onclick='event.stopPropagation(); performRoomAction(${JSON.stringify(room.room_id)}, "light_toggle", ${JSON.stringify({ entity_id: light && light.entity_id, turn_on: !(light && light.is_on) })})'
          ${light && (light.available === false || light.exists === false) ? "disabled" : ""}
          aria-label="${escapeHtml(light && light.is_on ? "关闭灯光" : "开启灯光")}"
        ></button>
      </div>
      <div class="sample-light-card-body">
        <div class="sample-light-card-state">${escapeHtml(statusText)}</div>
      </div>
    </div>
  `;
}

function referenceActionButton(icon, label, handler, tone = "gray") {
  return `<button class="ref-action-btn ${escapeHtml(tone)}" type="button" onclick='${handler}'><span>${escapeHtml(icon)}</span><span>${escapeHtml(label)}</span></button>`;
}

function referenceLivePill(label, tone = "standby") {
  return `<span class="ref-live-pill ${escapeHtml(tone)}">${escapeHtml(label)}</span>`;
}

function renderReferenceMetricRing(percentage, valueText, label, color = "#3b82f6") {
  const circumference = 238.76;
  const dash = circleDash((Number(percentage) || 0) / 100, circumference);
  return `
    <div class="ref-metric-ring">
      <svg viewBox="0 0 92 92" aria-hidden="true">
        <circle cx="46" cy="46" r="38" class="ref-metric-ring-track"></circle>
        <circle cx="46" cy="46" r="38" class="ref-metric-ring-fill" style="stroke:${escapeHtml(color)};stroke-dasharray:${dash}"></circle>
      </svg>
      <div class="ref-metric-ring-center">
        <strong>${escapeHtml(valueText)}</strong>
        <span>${escapeHtml(label)}</span>
      </div>
    </div>
  `;
}

function renderReferenceAcModeButtons(roomId, ac) {
  if (!ac || ac.domain !== "climate") {
    return '<div class="ref-mode-row muted"><span class="ref-mode-note">开关型空调仅支持电源控制</span></div>';
  }
  const modes = Array.isArray(ac.hvac_modes) ? ac.hvac_modes.filter(Boolean) : [];
  if (!modes.length) {
    return '<div class="ref-mode-row muted"><span class="ref-mode-note">当前空调未提供模式列表</span></div>';
  }
  return `
    <div class="ref-mode-row">
      ${modes.map((mode) => `
        <button
          class="ref-mode-btn ${mode === ac.hvac_mode ? "active" : ""}"
          type="button"
          onclick='setAcHvacMode(${JSON.stringify(roomId)}, ${JSON.stringify(mode)})'
        >${escapeHtml(hvacModeLabel(mode))}</button>
      `).join("")}
    </div>
  `;
}

function buildAcControlModalHtml(roomId) {
  const room = getRoom(roomId);
  const ac = room && getMappedRoomDevices(room).ac;
  if (!room || !ac) {
    return `<div class="status-modal-empty">当前房间没有可控制的空调。</div>`;
  }
  const currentTemp = firstFiniteNumber(ac.current_temperature, ac.temperature) ?? 24;
  const targetTemp = firstFiniteNumber(ac.temperature, ac.current_temperature) ?? currentTemp;
  const config = currentRoomConfig(room.room_id);
  const season = config && config.modes ? config.modes.selected_season : "--";
  const seasonText = season === "summer" ? "夏季" : season === "winter" ? "冬季" : season === "custom" ? "自定义" : "--";
  const modeText = hvacModeLabel(ac.hvac_mode || ac.state || (ac.is_on ? "on" : "off"));
  const fanModeText = uiModeLabel(ac.fan_mode || "--");
  const humidityValue = firstFiniteNumber(ac.current_humidity, ac && ac.attributes && ac.attributes.current_humidity, ac.humidity, ac && ac.attributes && ac.attributes.humidity);
  const stateClass = ac.available === false || ac.exists === false
    ? "state-offline"
    : !ac.is_on
      ? "state-off"
      : ac.hvac_mode === "heat"
        ? "state-heat"
        : ac.hvac_mode === "dry"
          ? "state-dry"
          : "state-cool";
  const ringColor = stateClass === "state-heat"
    ? "#f59e0b"
    : stateClass === "state-dry"
      ? "#14b8a6"
      : stateClass === "state-offline"
        ? "#94a3b8"
        : "#3b82f6";
  const progress = ac.domain === "climate"
    ? Math.max(8, Math.min(100, Math.round((((targetTemp || 16) - 16) / 14) * 100)))
    : (ac.is_on ? 72 : 16);
  const fanOptions = ac.domain === "climate"
    ? (ac.fan_modes || []).map((mode) => `<option value="${escapeHtml(mode)}" ${mode === ac.fan_mode ? "selected" : ""}>${escapeHtml(uiModeLabel(mode))}</option>`).join("")
    : "";
  const unavailable = ac.available === false || ac.exists === false;
  return `
    <div class="ac-control-modal-page">
      <div class="ac-control-modal-summary ${escapeHtml(stateClass)}">
        <div>
          <strong>${escapeHtml(displayRoomName(room))}</strong>
          <span>${escapeHtml(entityOwnName(ac) || ac.entity_id || roomVisualCode(room))}</span>
        </div>
        ${referenceLivePill(unavailable ? "离线" : ac.is_on ? "运行中" : "已关闭", unavailable ? "offline" : ac.is_on ? "running" : "standby")}
      </div>
      <div class="ref-ac-main">
        ${renderReferenceMetricRing(
          progress,
          ac.domain === "climate" ? `${formatMetricNumber(targetTemp, 0)}°` : (ac.is_on ? "ON" : "OFF"),
          "设定温度",
          ringColor
        )}
        <div class="ref-reading-stack">
          <div class="ref-reading-main">${ac.domain === "climate" ? `${formatMetricNumber(currentTemp, 1)}°C` : (ac.is_on ? "运行中" : "已关闭")}</div>
          <div class="ref-reading-sub">当前状态 · ${escapeHtml(modeText)}</div>
          <div class="ref-info-grid">
            <div class="ref-info-item"><span>风速</span><strong>${escapeHtml(fanModeText)}</strong></div>
            <div class="ref-info-item"><span>湿度</span><strong>${humidityValue != null ? `${formatMetricNumber(humidityValue, 0)}%` : "--"}</strong></div>
            <div class="ref-info-item"><span>季节</span><strong>${escapeHtml(seasonText)}</strong></div>
            <div class="ref-info-item"><span>编号</span><strong>${escapeHtml(roomVisualCode(room))}</strong></div>
          </div>
        </div>
      </div>
      ${ac.domain === "climate" ? `
        <div class="ref-ac-temp-controls">
          <button class="ref-round-btn" type="button" onclick='shiftAcTemperature(${JSON.stringify(room.room_id)}, -1)' ${unavailable ? "disabled" : ""}>-</button>
          <div class="ref-temp-display">
            <span>目标温度</span>
            <strong>${formatMetricNumber(targetTemp, 0)}°C</strong>
          </div>
          <button class="ref-round-btn" type="button" onclick='shiftAcTemperature(${JSON.stringify(room.room_id)}, 1)' ${unavailable ? "disabled" : ""}>+</button>
        </div>
      ` : `
        <div class="ref-ac-temp-controls static">
          <div class="ref-temp-display">
            <span>控制说明</span>
            <strong>当前为空调开关型实体</strong>
          </div>
        </div>
      `}
      ${renderReferenceAcModeButtons(room.room_id, ac)}
      <div class="ref-card-footer">
        <div class="ref-select-field">
          <label>风速</label>
          ${ac.domain === "climate"
            ? `<select class="ref-select" onchange='setAcFanMode(${JSON.stringify(room.room_id)}, this.value)' ${unavailable ? "disabled" : ""}>${fanOptions || '<option value="">--</option>'}</select>`
            : `<div class="ref-static-field">${escapeHtml(fanModeText)}</div>`}
        </div>
        <div class="ref-card-actions">
          ${referenceActionButton("开", "开启", `performRoomAction(${JSON.stringify(room.room_id)}, "ac_turn_on")`, "cyan")}
          ${referenceActionButton("关", "关闭", `performRoomAction(${JSON.stringify(room.room_id)}, "ac_turn_off")`, "gray")}
          ${referenceActionButton("夏", "夏季", `performRoomAction(${JSON.stringify(room.room_id)}, "ac_apply_season", "summer", true)`, "orange")}
          ${referenceActionButton("冬", "冬季", `performRoomAction(${JSON.stringify(room.room_id)}, "ac_apply_season", "winter", true)`, "blue")}
        </div>
      </div>
    </div>
  `;
}

function openAcControlModal(roomId) {
  const room = getRoom(roomId);
  if (!room || !getMappedRoomDevices(room).ac) {
    showMessage("当前房间没有可控制的空调。", "warning", true);
    return;
  }
  state.modalContext = { type: "ac", roomId };
  openStatusModal(
    `${displayRoomName(room)} · 空调控制`,
    buildAcControlModalHtml(roomId)
  );
}

function renderReferenceFreshModeButtons(roomId, fresh) {
  const modes = freshAirPresetModes(fresh);
  if (!fresh || fresh.domain !== "fan" || !modes.length) {
    const label = fresh ? uiModeLabel(fresh.preset_mode || fresh.state || "--") : "--";
    return `<div class="ref-mode-row muted"><span class="ref-mode-note">当前模式 ${escapeHtml(label)}</span></div>`;
  }
  return `
    <div class="ref-mode-row fan">
      ${modes.map((mode) => `
        <button
          class="ref-mode-btn ${mode === fresh.preset_mode ? "active" : ""}"
          type="button"
          onclick='performRoomAction(${JSON.stringify(roomId)}, "fresh_air_set_mode", ${JSON.stringify(mode)})'
        >${escapeHtml(uiModeLabel(mode))}</button>
      `).join("")}
    </div>
  `;
}

function freshAirOperationScore(fresh) {
  if (!fresh || fresh.available === false || fresh.exists === false) return 18;
  const level = firstFiniteNumber(fresh.percentage);
  if (level != null) return Math.max(36, Math.min(96, Math.round(level)));
  const modes = freshAirPresetModes(fresh);
  const currentMode = String(fresh.preset_mode || "").trim();
  const index = currentMode ? modes.findIndex((item) => item === currentMode) : -1;
  if (index >= 0 && modes.length > 1) {
    return Math.max(40, Math.min(94, Math.round(((index + 1) / modes.length) * 100)));
  }
  return fresh.is_on ? 82 : 28;
}

function freshAirModeText(fresh) {
  if (!fresh) return "--";
  if (fresh.domain !== "fan") return fresh.is_on ? "已开启" : "已关闭";
  if (fresh.preset_mode) return uiModeLabel(fresh.preset_mode);
  if (fresh.percentage != null) return `${fresh.percentage}%`;
  return uiModeLabel(fresh.state || "--");
}

function buildFreshAirControlModalHtml(roomId) {
  const room = getRoom(roomId);
  const fresh = room && getMappedRoomDevices(room).freshAir;
  if (!room || !fresh) {
    return `<div class="status-modal-empty">当前房间没有可控制的新风。</div>`;
  }
  const unavailable = fresh.available === false || fresh.exists === false;
  const isFan = fresh.domain === "fan";
  const presetModes = freshAirPresetModes(fresh);
  const currentModeText = freshAirModeText(fresh);
  const percentage = firstFiniteNumber(fresh.percentage);
  const operationScore = freshAirOperationScore(fresh);
  const qualityLabel = operationScore >= 85 ? "优" : operationScore >= 70 ? "良" : operationScore >= 50 ? "稳" : "弱";
  const statusTone = unavailable ? "offline" : fresh.is_on ? "running" : "standby";
  const statusText = unavailable ? "离线" : fresh.is_on ? "运行中" : "已关闭";
  const config = currentRoomConfig(room.room_id);
  const defaultMode = config && config.automation && config.automation.fresh_air ? config.automation.fresh_air.fan_mode : "--";
  return `
    <div class="fresh-control-modal-page">
      <div class="fresh-control-modal-summary ${fresh.is_on ? "is-running" : ""} ${unavailable ? "state-offline" : ""}">
        <div>
          <strong>${escapeHtml(displayRoomName(room))}</strong>
          <span>${escapeHtml(entityOwnName(fresh) || fresh.entity_id || roomVisualCode(room))}</span>
        </div>
        ${referenceLivePill(statusText, statusTone)}
      </div>
      <div class="fresh-control-power-row">
        <div>
          <span>${escapeHtml(isFan ? "Fan 实体" : "Switch 实体")}</span>
          <strong>${escapeHtml(currentModeText)}</strong>
        </div>
        <div class="ref-card-actions">
          ${referenceActionButton("开", "开启", `performRoomAction(${JSON.stringify(room.room_id)}, "fresh_air_turn_on")`, "cyan")}
          ${referenceActionButton("关", "关闭", `performRoomAction(${JSON.stringify(room.room_id)}, "fresh_air_turn_off")`, "gray")}
        </div>
      </div>
      ${isFan ? `
        <div class="ref-fan-main">
          ${renderReferenceMetricRing(operationScore, qualityLabel, "运行评分", "#10b981")}
          <div class="ref-reading-stack">
            <div class="ref-reading-main">${escapeHtml(currentModeText)}</div>
            <div class="ref-reading-sub">${fresh.is_on ? "空气循环中，保持舒适" : "等待启动，准备联动"}</div>
            <div class="ref-info-grid">
              <div class="ref-info-item"><span>运行状态</span><strong>${escapeHtml(uiModeLabel(fresh.state || "--"))}</strong></div>
              <div class="ref-info-item"><span>默认档位</span><strong>${escapeHtml(uiModeLabel(defaultMode || "--"))}</strong></div>
              <div class="ref-info-item"><span>实体类型</span><strong>${escapeHtml(fresh.domain || "--")}</strong></div>
              <div class="ref-info-item"><span>最后变化</span><strong>${escapeHtml(formatTime(fresh.last_changed))}</strong></div>
            </div>
          </div>
        </div>
        ${presetModes.length ? renderReferenceFreshModeButtons(room.room_id, fresh) : ""}
        ${percentage != null ? `
          <label class="fresh-control-range">
            <div class="fresh-control-range-head">
              <span>风量</span>
              <strong>${escapeHtml(`${Math.round(percentage)}%`)}</strong>
            </div>
            <input type="range" min="0" max="100" step="1" value="${Math.max(0, Math.min(100, Math.round(percentage)))}" onchange='setFreshAirPercentage(${JSON.stringify(room.room_id)}, this.value)' ${unavailable ? "disabled" : ""}>
          </label>
        ` : ""}
        ${!presetModes.length && percentage == null ? `<div class="ref-note-box">当前 fan 实体没有提供 preset_modes 或 percentage 控制能力，只保留开关控制。</div>` : ""}
      ` : `
        <div class="ref-note-box">当前新风是 switch 开关型实体，只显示开启和关闭控制。</div>
      `}
    </div>
  `;
}

function openFreshAirControlModal(roomId) {
  const room = getRoom(roomId);
  if (!room || !getMappedRoomDevices(room).freshAir) {
    showMessage("当前房间没有可控制的新风。", "warning", true);
    return;
  }
  state.modalContext = { type: "fresh", roomId };
  openStatusModal(
    `${displayRoomName(room)} · 新风控制`,
    buildFreshAirControlModalHtml(roomId)
  );
}

function showcaseStatusRing(percentage, color, value, label) {
  const circumference = 251.2;
  const dash = circleDash((Number(percentage) || 0) / 100, circumference);
  return `
    <div class="showcase-status-ring">
      <svg viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(148,163,184,.16)" stroke-width="8"></circle>
        <circle cx="50" cy="50" r="40" fill="none" stroke="${color}" stroke-width="8" stroke-linecap="round" stroke-dasharray="${dash}"></circle>
      </svg>
      <div class="showcase-status-center">
        <strong>${escapeHtml(value)}</strong>
        <span>${escapeHtml(label)}</span>
      </div>
    </div>
  `;
}

function renderAcPage() {
  const root = document.getElementById("page-ac");
  if (!isConnectionConfigured()) {
    root.innerHTML = renderEmptyState("无法读取空调数据", "请先在配置页建立连接。");
    return;
  }
  const rooms = roomsForDisplay().filter((room) => getMappedRoomDevices(room).ac);
  if (!rooms.length) {
    root.innerHTML = renderEmptyState("暂无空调映射", "当前没有任何房间配置空调实体。");
    return;
  }
  const filters = pageFilterState("ac");
  const visibleRooms = rooms.filter((room) => {
    const ac = getMappedRoomDevices(room).ac;
    return ac && matchesKeywordFilter(`${roomFilterText(room)} ${entityOwnName(ac)} ${ac.friendly_name || ""} ${ac.entity_id || ""}`, filters.include, filters.exclude);
  });
  const onCount = visibleRooms.filter((room) => {
    const ac = getMappedRoomDevices(room).ac;
    return ac && ac.is_on;
  }).length;
  const offlineCount = visibleRooms.filter((room) => {
    const ac = getMappedRoomDevices(room).ac;
    return ac && (ac.available === false || ac.exists === false);
  }).length;
  root.innerHTML = `
    <div class="ref-device-page ref-device-page-ac">
      <div class="section-title">
        <div>
          <h2>空调总览</h2>
          <p>按房间查看空调是否运行，并直接完成开关、季节和温度调整。</p>
        </div>
        <div class="toolbar-actions">
          ${renderDeviceFilterBar("ac", "包含：单人包、挂机空调、206", "排除：双人包、测试", "支持按房间名和空调名称筛选。", true)}
          ${referenceActionButton("开", "全部开启", `batchRoomAction("ac", "ac_turn_on")`, "cyan")}
          ${referenceActionButton("关", "全部关闭", `batchRoomAction("ac", "ac_turn_off")`, "gray")}
          ${referenceActionButton("夏", "全部夏季", `batchRoomAction("ac", "ac_apply_season", "summer", true)`, "orange")}
          ${referenceActionButton("冬", "全部冬季", `batchRoomAction("ac", "ac_apply_season", "winter", true)`, "blue")}
        </div>
      </div>
      <div class="ref-ac-grid">
        ${visibleRooms.length ? visibleRooms.map((room, index) => {
          const ac = getMappedRoomDevices(room).ac;
          const currentTemp = firstFiniteNumber(ac.current_temperature, ac.temperature) ?? 24;
          const targetTemp = firstFiniteNumber(ac.temperature, ac.current_temperature) ?? currentTemp;
          const modeText = hvacModeLabel(ac.hvac_mode || ac.state || (ac.is_on ? "on" : "off"));
          const unavailable = ac.available === false || ac.exists === false;
          const stateClass = ac.available === false || ac.exists === false
            ? "state-offline"
            : !ac.is_on
              ? "state-off"
              : ac.hvac_mode === "heat"
                ? "state-heat"
                : ac.hvac_mode === "dry"
                  ? "state-dry"
                  : "state-cool";
          const statusTone = ac.available === false || ac.exists === false
            ? "offline"
            : ac.is_on
              ? "running"
              : "standby";
          const statusText = ac.available === false || ac.exists === false
            ? "离线"
            : ac.is_on
              ? "运行中"
              : "已关闭";
          const acHeaderModeText = ac.available === false || ac.exists === false
            ? "离线"
            : !ac.is_on
              ? "待机"
              : modeText;
          return `
            <div
              class="card ref-device-card ref-ac-card ref-ac-mini-card ${stateClass} ${ac.is_on ? "is-running" : ""}"
              style="--stagger:${index};"
              role="button"
              tabindex="0"
              onclick='openAcControlModal(${JSON.stringify(room.room_id)})'
              onkeydown='if(event.key === "Enter" || event.key === " "){ event.preventDefault(); openAcControlModal(${JSON.stringify(room.room_id)}); }'
            >
              <div class="ref-card-header ref-ac-card-header">
                <div>
                  <div class="ref-card-name">${escapeHtml(displayRoomName(room))}</div>
                  <div class="ref-card-sub">${escapeHtml(entityOwnName(ac) || ac.entity_id || roomVisualCode(room))}</div>
                </div>
                <div class="ref-card-header-side">
                  <span class="ref-ac-mode-badge ${escapeHtml(stateClass)}">${escapeHtml(acHeaderModeText)}</span>
                  ${referenceLivePill(statusText, statusTone)}
                </div>
              </div>
              <div class="ref-card-body ref-ac-mini-body">
                <div class="ref-ac-mini-main">
                  <div class="ref-ac-mini-current">
                    <span>当前</span>
                    <strong>${ac.domain === "climate" ? `${formatMetricNumber(currentTemp, 1)}°C` : escapeHtml(statusText)}</strong>
                  </div>
                  <button
                    class="ac-mini-power-btn ${ac.is_on ? "on" : ""}"
                    type="button"
                    onclick='event.stopPropagation(); performRoomAction(${JSON.stringify(room.room_id)}, ${JSON.stringify(ac.is_on ? "ac_turn_off" : "ac_turn_on")})'
                    ${unavailable ? "disabled" : ""}
                  >
                    <span></span>${escapeHtml(ac.is_on ? "关闭" : "开启")}
                  </button>
                </div>
                ${ac.domain === "climate" ? `
                  <div class="ref-ac-temp-controls ref-ac-mini-temp" onclick="event.stopPropagation()">
                    <button class="ref-round-btn" type="button" onclick='shiftAcTemperature(${JSON.stringify(room.room_id)}, -1)' ${unavailable ? "disabled" : ""}>-</button>
                    <div class="ref-temp-display">
                      <span>目标温度</span>
                      <strong>${formatMetricNumber(targetTemp, 0)}°C</strong>
                    </div>
                    <button class="ref-round-btn" type="button" onclick='shiftAcTemperature(${JSON.stringify(room.room_id)}, 1)' ${unavailable ? "disabled" : ""}>+</button>
                  </div>
                ` : `
                  <div class="ref-ac-temp-controls ref-ac-mini-temp static" onclick="event.stopPropagation()">
                    <div class="ref-temp-display">
                      <span>控制说明</span>
                      <strong>开关型空调</strong>
                    </div>
                  </div>
                `}
              </div>
            </div>
          `;
        }).join("") : `<div class="card list-filter-empty">当前筛选条件下没有匹配的空调。</div>`}
      </div>
    </div>
  `;
}

function renderLightPage() {
  const root = document.getElementById("page-light");
  if (!isConnectionConfigured()) {
    root.innerHTML = renderEmptyState("无法读取灯光数据", "请先在配置页建立连接。");
    return;
  }
  const rooms = roomsForDisplay().filter((room) => getMappedRoomDevices(room).lights.length);
  if (!rooms.length) {
    root.innerHTML = renderEmptyState("暂无灯光映射", "当前没有任何房间绑定灯光实体。");
    return;
  }
  const filters = pageFilterState("light");
  const lightEntries = rooms.flatMap((room) => getMappedRoomDevices(room).lights.map((light) => ({ room, light })));
  const visibleEntries = lightEntries.filter(({ room, light }) => matchesKeywordFilter(
    `${displayRoomName(room)} ${roomFilterText(room)} ${light ? entityOwnName(light) : ""} ${light && light.friendly_name || ""} ${light && light.entity_id || ""}`,
    filters.include,
    filters.exclude
  ));
  const allLights = visibleEntries.map((item) => item.light).filter(Boolean);
  const onCount = allLights.filter((light) => light && light.is_on).length;
  const offlineCount = allLights.filter((light) => light && (light.available === false || light.exists === false)).length;
  root.innerHTML = `
    <div class="ref-device-page ref-device-page-light sample-light-page">
      <div class="section-title">
        <div>
          <h2>灯光总览</h2>
          <p>按单灯展示，卡片仅保留名称、状态和开关。</p>
        </div>
        <div class="toolbar-actions">
          ${renderDeviceFilterBar("light", "包含：单人包、灯带、筒灯", "排除：双人包、过道", "支持按包厢名和灯具名称筛选。", true)}
          ${referenceActionButton("全", "全部全开", `batchRoomAction("light", "light_apply_preset", "full_on")`, "orange")}
          ${referenceActionButton("半", "全部部分开启", `batchRoomAction("light", "light_apply_preset", "half_on")`, "blue")}
          ${referenceActionButton("关", "全部全关", `batchRoomAction("light", "light_apply_preset", "full_off")`, "gray")}
        </div>
      </div>
      <div class="chip-list stack-gap">
        <span class="chip">显示灯具 ${allLights.length}/${lightEntries.length} 盏</span>
        <span class="chip">已开启 ${onCount} 盏</span>
        <span class="chip">已关闭 ${allLights.length - onCount} 盏</span>
        <span class="chip">离线 ${offlineCount} 盏</span>
      </div>
      <div class="sample-light-grid">
        ${visibleEntries.length ? visibleEntries.map(({ room, light }) => renderSampleLightPageCard(room, light)).join("") : `<div class="card list-filter-empty">当前筛选条件下没有匹配的灯具。</div>`}
      </div>
    </div>
  `;
}

function renderFanPage() {
  const root = document.getElementById("page-fan");
  if (!isConnectionConfigured()) {
    root.innerHTML = renderEmptyState("无法读取新风数据", "请先在配置页建立连接。");
    return;
  }
  const rooms = roomsForDisplay().filter((room) => getMappedRoomDevices(room).freshAir);
  if (!rooms.length) {
    root.innerHTML = renderEmptyState("暂无新风映射", "当前没有任何房间绑定新风实体。");
    return;
  }
  const filters = pageFilterState("fan");
  const visibleRooms = rooms.filter((room) => {
    const fresh = getMappedRoomDevices(room).freshAir;
    return matchesKeywordFilter(`${roomFilterText(room)} ${entityOwnName(fresh)} ${fresh.friendly_name || ""} ${fresh.entity_id || ""}`, filters.include, filters.exclude);
  });
  const onCount = visibleRooms.filter((room) => {
    const fresh = getMappedRoomDevices(room).freshAir;
    return fresh && fresh.is_on;
  }).length;
  root.innerHTML = `
    <div class="ref-device-page ref-device-page-fan">
      <div class="section-title">
        <div>
          <h2>新风控制</h2>
          <p>统一成参考图的视觉信息卡，同时保留 fan.* 档位控制和 switch.* 开关能力。</p>
        </div>
        <div class="toolbar-actions">
          ${renderDeviceFilterBar("fan", "包含：单人包、新风、206", "排除：双人包、备用", "支持按房间名和新风实体筛选。", true)}
          ${referenceActionButton("开", "全部开启", `batchRoomAction("fresh_air", "fresh_air_turn_on")`, "cyan")}
          ${referenceActionButton("关", "全部关闭", `batchRoomAction("fresh_air", "fresh_air_turn_off")`, "gray")}
        </div>
      </div>
      <div class="chip-list stack-gap">
        <span class="chip">显示 ${visibleRooms.length}/${rooms.length}</span>
        <span class="chip">运行中 ${onCount}</span>
        <span class="chip">待机 ${visibleRooms.length - onCount}</span>
      </div>
      <div class="ref-fan-grid">
        ${visibleRooms.length ? visibleRooms.map((room, index) => {
          const fresh = getMappedRoomDevices(room).freshAir;
          const currentModeText = freshAirModeText(fresh);
          const unavailable = fresh.available === false || fresh.exists === false;
          const statusTone = fresh.available === false || fresh.exists === false
            ? "offline"
            : fresh.is_on
              ? "running"
              : "standby";
          const statusText = fresh.available === false || fresh.exists === false
            ? "离线"
            : fresh.is_on
              ? "运行中"
              : "已关闭";
          return `
            <div
              class="card ref-device-card ref-fan-card ref-fan-mini-card ${fresh.is_on ? "is-running" : ""} ${unavailable ? "state-offline" : ""}"
              style="--stagger:${index};"
              role="button"
              tabindex="0"
              onclick='openFreshAirControlModal(${JSON.stringify(room.room_id)})'
              onkeydown='if(event.key === "Enter" || event.key === " "){ event.preventDefault(); openFreshAirControlModal(${JSON.stringify(room.room_id)}); }'
            >
              <div class="ref-card-header ref-fan-card-header">
                <div class="ref-fan-heading">
                  <div class="ref-fan-icon ${fresh.is_on ? "running" : ""}">
                    <span class="ref-fan-rotor">✦</span>
                  </div>
                  <div>
                    <div class="ref-card-name">${escapeHtml(displayRoomName(room))}</div>
                    <div class="ref-card-sub">${escapeHtml(entityOwnName(fresh) || fresh.entity_id || roomVisualCode(room))}</div>
                  </div>
                </div>
                <div class="ref-card-header-side">
                  ${referenceLivePill(statusText, statusTone)}
                </div>
              </div>
              <div class="ref-card-body ref-fan-mini-body">
                <div class="ref-fan-mini-main">
                  <div class="ref-fan-mini-current">
                    <span>${escapeHtml(fresh.domain === "fan" ? "当前档位" : "当前状态")}</span>
                    <strong>${escapeHtml(currentModeText)}</strong>
                  </div>
                  <button
                    class="fresh-mini-power-btn ${fresh.is_on ? "on" : ""}"
                    type="button"
                    onclick='event.stopPropagation(); performRoomAction(${JSON.stringify(room.room_id)}, ${JSON.stringify(fresh.is_on ? "fresh_air_turn_off" : "fresh_air_turn_on")})'
                    ${unavailable ? "disabled" : ""}
                  >
                    <span></span>${escapeHtml(fresh.is_on ? "关闭" : "开启")}
                  </button>
                </div>
              </div>
            </div>
          `;
        }).join("") : `<div class="card list-filter-empty">当前筛选条件下没有匹配的新风设备。</div>`}
      </div>
    </div>
  `;
}

function selectOptions(items, selectedValue, placeholder) {
  const options = [`<option value="">${escapeHtml(placeholder || "未选择")}</option>`];
  for (const item of items || []) {
    options.push(`<option value="${escapeHtml(item.entity_id)}" ${item.entity_id === selectedValue ? "selected" : ""}>${escapeHtml(entityDisplayName(item))} (${escapeHtml(item.entity_id)})</option>`);
  }
  return options.join("");
}

function selectedAcModes(entityId, selectedMode) {
  const entity = candidateById(entityId);
  const modes = entity && String(entity.entity_id || "").startsWith("climate.")
    ? (entity.attributes && entity.attributes.hvac_modes) || []
    : ["cool", "heat", "auto", "fan_only", "dry"];
  const unique = Array.from(new Set((modes || []).filter(Boolean)));
  return unique.map((mode) => `<option value="${escapeHtml(mode)}" ${mode === selectedMode ? "selected" : ""}>${escapeHtml(hvacModeLabel(mode))}</option>`).join("");
}

function selectedAcFanModes(entityId, selectedFanMode) {
  const entity = candidateById(entityId);
  const modes = entity && String(entity.entity_id || "").startsWith("climate.")
    ? (entity.attributes && entity.attributes.fan_modes) || []
    : ["auto"];
  const unique = Array.from(new Set(((modes && modes.length) ? modes : ["auto"]).filter(Boolean)));
  return unique.map((mode) => `<option value="${escapeHtml(mode)}" ${mode === selectedFanMode ? "selected" : ""}>${escapeHtml(mode)}</option>`).join("");
}

function selectedFreshModes(entityId, selectedMode) {
  const entity = candidateById(entityId);
  const modes = entity && String(entity.entity_id || "").startsWith("fan.")
    ? (entity.attributes && entity.attributes.preset_modes) || []
    : ["auto"];
  const unique = Array.from(new Set(((modes && modes.length) ? modes : ["auto"]).filter(Boolean)));
  return unique.map((mode) => `<option value="${escapeHtml(mode)}" ${mode === selectedMode ? "selected" : ""}>${escapeHtml(mode)}</option>`).join("");
}

function checkCard(name, value, label, checked) {
  return `
    <label class="check-card">
      <span>${escapeHtml(label)}</span>
      <input type="checkbox" name="${escapeHtml(name)}" value="${escapeHtml(value)}" ${checked ? "checked" : ""}>
    </label>
  `;
}

function uniqueEntityOptions(items) {
  const seen = new Set();
  const result = [];
  for (const item of items || []) {
    if (!item) continue;
    const entityId = typeof item === "string" ? item : item.entity_id;
    if (!entityId || seen.has(entityId)) continue;
    seen.add(entityId);
    const resolved = typeof item === "string" ? candidateById(entityId) : item;
    result.push({
      entity_id: entityId,
      friendly_name: resolved && resolved.friendly_name ? resolved.friendly_name : entityId,
    });
  }
  return result;
}

function filterEntityOptions(items, includeKeywords, excludeKeywords) {
  const includeList = parseKeywordList(includeKeywords).map((item) => item.toLowerCase());
  const excludeList = parseKeywordList(excludeKeywords).map((item) => item.toLowerCase());
  return uniqueEntityOptions(items).filter((item) => {
    const text = `${item.friendly_name || ""} ${item.entity_id || ""}`.toLowerCase();
    if (includeList.length && !includeList.some((keyword) => text.includes(keyword))) {
      return false;
    }
    if (excludeList.some((keyword) => text.includes(keyword))) {
      return false;
    }
    return true;
  });
}

function roomEntityFilters(roomConfig) {
  const globalSettings = currentGlobalSettings();
  if (globalSettings && globalSettings.entity_filters) {
    return globalSettings.entity_filters;
  }
  return roomConfig && roomConfig.entity_filters ? roomConfig.entity_filters : defaultRoomConfig().entity_filters;
}

function autoDetectedRoomTargets(room, roomConfig) {
  const filters = roomEntityFilters(roomConfig);
  return {
    ac: filterEntityOptions(
      roomAcOptions(room, roomConfig),
      filters.ac_include_keywords,
      filters.ac_exclude_keywords
    ),
    lights: filterEntityOptions(
      roomLightOptions(room, roomConfig),
      filters.light_include_keywords,
      filters.light_exclude_keywords
    ),
    fresh: filterEntityOptions(
      roomFreshAirOptions(room, roomConfig),
      filters.fresh_air_include_keywords,
      filters.fresh_air_exclude_keywords
    ),
  };
}

function globalEntityFiltersDraft() {
  const existing = currentGlobalSettings();
  return {
    ac_include_keywords: parseKeywordList(draftTextValue("acIncludeKeywords", existing.entity_filters.ac_include_keywords)),
    ac_exclude_keywords: parseKeywordList(draftTextValue("acExcludeKeywords", existing.entity_filters.ac_exclude_keywords)),
    light_include_keywords: parseKeywordList(draftTextValue("lightIncludeKeywords", existing.entity_filters.light_include_keywords)),
    light_exclude_keywords: parseKeywordList(draftTextValue("lightExcludeKeywords", existing.entity_filters.light_exclude_keywords)),
    fresh_air_include_keywords: parseKeywordList(draftTextValue("freshIncludeKeywords", existing.entity_filters.fresh_air_include_keywords)),
    fresh_air_exclude_keywords: parseKeywordList(draftTextValue("freshExcludeKeywords", existing.entity_filters.fresh_air_exclude_keywords)),
  };
}

function globalEntityTargets(entityFilters = currentGlobalSettings().entity_filters) {
  return {
    ac: filterEntityOptions(
      [...candidatesFor("climate"), ...candidatesFor("switch")],
      entityFilters.ac_include_keywords,
      entityFilters.ac_exclude_keywords
    ),
    lights: filterEntityOptions(
      lightCandidatePool(),
      entityFilters.light_include_keywords,
      entityFilters.light_exclude_keywords
    ),
    fresh: filterEntityOptions(
      [...candidatesFor("fan"), ...candidatesFor("switch")],
      entityFilters.fresh_air_include_keywords,
      entityFilters.fresh_air_exclude_keywords
    ),
  };
}

function automationTargetEntityFilters(globalSettings = currentGlobalSettings()) {
  const automation = globalSettings && globalSettings.automation ? globalSettings.automation : defaultGlobalSettings().automation;
  return {
    ac: {
      include: parseKeywordList(automation.ac && automation.ac.target_include_keywords),
      exclude: parseKeywordList(automation.ac && automation.ac.target_exclude_keywords),
    },
    light: {
      include: parseKeywordList(automation.light && automation.light.target_include_keywords),
      exclude: parseKeywordList(automation.light && automation.light.target_exclude_keywords),
    },
    fresh: {
      include: parseKeywordList(automation.fresh_air && automation.fresh_air.target_include_keywords),
      exclude: parseKeywordList(automation.fresh_air && automation.fresh_air.target_exclude_keywords),
    },
  };
}

function automationTargetsFromGlobalSettings(globalSettings = currentGlobalSettings()) {
  const baseTargets = globalEntityTargets(globalSettings.entity_filters);
  const targetFilters = automationTargetEntityFilters(globalSettings);
  return {
    ac: filterEntityOptions(baseTargets.ac, targetFilters.ac.include, targetFilters.ac.exclude),
    lights: filterEntityOptions(baseTargets.lights, targetFilters.light.include, targetFilters.light.exclude),
    fresh: filterEntityOptions(baseTargets.fresh, targetFilters.fresh.include, targetFilters.fresh.exclude),
  };
}

function roomAcOptions(room, roomConfig) {
  return uniqueEntityOptions([
    room && room.mapped ? room.mapped.ac : null,
    roomConfig && roomConfig.entities ? roomConfig.entities.ac : "",
  ]);
}

function roomFreshAirOptions(room, roomConfig) {
  return uniqueEntityOptions([
    room && room.mapped ? room.mapped.fresh_air : null,
    roomConfig && roomConfig.entities ? roomConfig.entities.fresh_air : "",
  ]);
}

function roomLightOptions(room, roomConfig) {
  const mappedLights = room && room.mapped && Array.isArray(room.mapped.lights) ? room.mapped.lights : [];
  const existingLights = roomConfig && roomConfig.entities && Array.isArray(roomConfig.entities.lights) ? roomConfig.entities.lights : [];
  return uniqueEntityOptions([...mappedLights, ...existingLights]);
}

function formatJsonBlock(value) {
  return escapeHtml(JSON.stringify(value ?? {}, null, 2));
}

function settingsMenuItems() {
  return [
    { key: "basic", icon: "⚙", label: "基础设置" },
    { key: "notify", icon: "💬", label: "微信通知" },
    { key: "ac", icon: "❄", label: "空调控制" },
    { key: "light", icon: "💡", label: "灯光控制" },
    { key: "fan", icon: "🌀", label: "新风控制" },
    { key: "linkage", icon: "⛓", label: "自动化联动" },
    { key: "sub", icon: "🖥", label: "副中控", requiresRoom: true },
  ];
}

function isRoomSettingsPage(page) {
  return ["sub"].includes(page);
}

function ensureValidSettingsSubPage(hasRoomConfig) {
  const available = settingsMenuItems()
    .filter((item) => hasRoomConfig || !item.requiresRoom)
    .map((item) => item.key);
  if (!available.includes(state.currentSettingsSubPage)) {
    state.currentSettingsSubPage = "basic";
  }
}

function settingsCurrentMenuLabel() {
  const item = settingsMenuItems().find((entry) => entry.key === state.currentSettingsSubPage);
  return item ? item.label : "基础设置";
}

function settingsDeviceStateLabel(entity, onText = "在线") {
  if (!entity) return "未绑定";
  if (entity.available === false || entity.exists === false) return "离线";
  if (entity.is_on === true) return onText;
  if (entity.is_on === false) return "待机";
  return "在线";
}

function renderSettingsSidebarMetric(label, value, tone = "") {
  return `
    <div class="settings-side-metric ${tone}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value))}</strong>
    </div>
  `;
}

function renderSettingsRoomSidebar(room, roomConfig, roomItems, canEdit, connectionText, refreshText) {
  const inventory = getMappedRoomDevices(room);
  const ac = inventory.ac;
  const lights = inventory.lights;
  const fresh = inventory.freshAir;
  const lightOnCount = lights.filter((item) => item && item.is_on).length;
  const totalLights = lights.length;
  const occupiedImage = roomOnlineTerminalCount(room) > 0 ? "/api/netcafe/开灯.png" : "/api/netcafe/关灯.png";
  const automationEnabled = Boolean(roomConfig && roomConfig.automation && roomConfig.automation.enabled);
  return `
    <aside class="settings-workspace-side">
      <div class="card settings-overview-card">
        <div class="settings-side-head">
          <div>
            <h3>区域选择</h3>
            <p>切换包厢后，右侧所有配置面板会同步更新。</p>
          </div>
          <span class="badge ${canEdit ? "green" : ""}">${escapeHtml(connectionText)}</span>
        </div>
        <div class="field">
          <select id="settingsRoomSelect" onchange="selectRoom(this.value)">${roomsOptions(roomItems, state.currentRoomId)}</select>
        </div>
        ${room ? `
          <div class="settings-room-meta-row">
            ${renderSettingsSidebarMetric("覆盖房间", roomCoverageText(room), "blue")}
            ${renderSettingsSidebarMetric("在线终端", `${roomOnlineTerminalCount(room)}/${Number(room.computer_count || 0)}`, "violet")}
            ${renderSettingsSidebarMetric("最近刷新", refreshText, "")}
          </div>
          <div class="settings-room-preview">
            <img src="${occupiedImage}" alt="${escapeHtml(displayRoomName(room))}">
          </div>
        ` : ""}
      </div>

      <div class="card settings-overview-card">
        <div class="settings-side-head">
          <div>
            <h3>设备状态</h3>
            <p>当前包厢的映射设备和在线状态。</p>
          </div>
        </div>
        <div class="settings-device-list">
          <div class="settings-device-row">
            <div>
              <strong>空调</strong>
              <small>${escapeHtml(acStatusSummary(ac))}</small>
            </div>
            <span class="settings-device-badge ${escapeHtml(acVisualState(ac))}">${escapeHtml(settingsDeviceStateLabel(ac, "运行中"))}</span>
          </div>
          <div class="settings-device-row">
            <div>
              <strong>灯光</strong>
              <small>${escapeHtml(lightStatusSummary(room, lights))}</small>
            </div>
            <span class="settings-device-badge ${lightOnCount > 0 ? "state-on" : totalLights ? "state-off" : "state-offline"}">${escapeHtml(totalLights ? `${lightOnCount}/${totalLights}` : "未绑定")}</span>
          </div>
          <div class="settings-device-row">
            <div>
              <strong>新风</strong>
              <small>${escapeHtml(freshAirStatusSummary(fresh))}</small>
            </div>
            <span class="settings-device-badge ${escapeHtml(freshVisualState(fresh))}">${escapeHtml(settingsDeviceStateLabel(fresh, "运行中"))}</span>
          </div>
        </div>
      </div>

      <div class="card settings-overview-card">
        <div class="settings-side-head">
          <div>
            <h3>控制模式</h3>
            <p>按参考图把全局策略收拢到侧栏，保存时统一提交。</p>
          </div>
        </div>
        <div class="settings-mode-list">
          <label class="settings-mode-option ${automationEnabled ? "active" : ""}">
            <input type="checkbox" id="automationEnabled" ${automationEnabled ? "checked" : ""}>
            <div>
              <strong>自动模式</strong>
              <span>根据环境和在线状态自动联动设备</span>
            </div>
          </label>
          <label class="settings-mode-option ${roomConfig && roomConfig.automation && roomConfig.automation.logging_enabled ? "active" : ""}">
            <input type="checkbox" id="loggingEnabled" ${roomConfig && roomConfig.automation && roomConfig.automation.logging_enabled ? "checked" : ""}>
            <div>
              <strong>记录日志</strong>
              <span>保存自动化执行日志，方便排查联动效果</span>
            </div>
          </label>
          <label class="settings-mode-option ${roomConfig && roomConfig.automation && roomConfig.automation.schedule && roomConfig.automation.schedule.enabled ? "active" : ""}">
            <input type="checkbox" id="scheduleEnabled" ${roomConfig && roomConfig.automation && roomConfig.automation.schedule && roomConfig.automation.schedule.enabled ? "checked" : ""}>
            <div>
              <strong>节能时段</strong>
              <span>仅在指定时段启用节能联动策略</span>
            </div>
          </label>
        </div>
        <div class="inline-fields">
          <div class="field">
            <label>开始时间</label>
            <input id="scheduleStartTime" type="time" value="${escapeHtml(roomConfig && roomConfig.automation && roomConfig.automation.schedule ? roomConfig.automation.schedule.start_time : "09:00")}">
          </div>
          <div class="field">
            <label>结束时间</label>
            <input id="scheduleEndTime" type="time" value="${escapeHtml(roomConfig && roomConfig.automation && roomConfig.automation.schedule ? roomConfig.automation.schedule.end_time : "23:00")}">
          </div>
        </div>
      </div>
    </aside>
  `;
}

function renderSettingsSystemSidebar(connectionText, refreshText, license, totalEntities) {
  return `
    <aside class="settings-workspace-side">
      <div class="card settings-overview-card">
        <div class="settings-side-head">
          <div>
            <h3>系统概况</h3>
            <p>当前面板连接状态和配置环境。</p>
          </div>
        </div>
        <div class="settings-side-metric-grid">
          ${renderSettingsSidebarMetric("访问模式", connectionText, "blue")}
          ${renderSettingsSidebarMetric("最近刷新", refreshText)}
          ${renderSettingsSidebarMetric("可见实体", totalEntities, "mint")}
          ${renderSettingsSidebarMetric("授权状态", license && license.status_text ? license.status_text : "--", "amber")}
        </div>
      </div>
    </aside>
  `;
}

function renderSettingsWorkspaceHero(room, canEdit) {
  const roomPage = isRoomSettingsPage(state.currentSettingsSubPage);
  const title = roomPage ? "环境配置" : settingsCurrentMenuLabel();
  const desc = roomPage
    ? `配置 ${displayRoomName(room)} 的空调、灯光、新风联动策略与场景规则。`
    : "维护连接、主题和系统级配置。";
  const meta = roomPage && room
    ? `<div class="settings-hero-breadcrumb">设备管理 <span>›</span> 环境设备 <span>›</span> ${escapeHtml(displayRoomName(room))} <span>›</span> 创建配置</div>`
    : `<div class="settings-hero-breadcrumb">系统管理 <span>›</span> ${escapeHtml(settingsCurrentMenuLabel())}</div>`;
  const actions = roomPage ? `
    <div class="button-row end">
      <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">重新读取</button>
      <button class="btn btn-primary" type="button" onclick="saveCurrentRoom()" ${canEdit ? "" : "disabled"}>保存并应用</button>
    </div>
  ` : `
    <div class="button-row end">
      <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">刷新数据</button>
    </div>
  `;
  return `
    <div class="card settings-workspace-hero">
      <div>
        ${meta}
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(desc)}</p>
      </div>
      ${actions}
    </div>
  `;
}

function renderSettingsPage() {
  const root = document.getElementById("page-settings");
  if (!root) return;
  ensureCurrentRoom();
  const rooms = currentRooms();
  const room = getRoom(state.currentRoomId);
  const config = room ? normalizeRoomConfig(room, currentRoomConfig(state.currentRoomId)) : null;
  const hasRoomConfig = Boolean(room);
  const canEdit = Boolean(state.config && state.entities && !state.authError);
  const climateItems = [...candidatesFor("climate"), ...candidatesFor("switch")];
  const freshItems = [...candidatesFor("fan"), ...candidatesFor("switch")];
  const lightItems = lightCandidatePool();
  const sensorItems = presenceSensorCandidates();
  const trackerItems = deviceTrackerCandidates();
  const uiSettings = currentUiSettings();
  ensureValidSettingsSubPage(hasRoomConfig);
  const totalEntities = ["climate", "light", "fan", "switch", "sensor"].reduce((sum, key) => sum + candidatesFor(key).length, 0);
  const license = currentLicenseStatus();
  const connectionText = !isConnectionConfigured() ? "未通过 HA 打开" : state.authError ? "只读模式" : canEdit ? "已连接" : "连接中";
  const refreshText = state.lastSuccessfulReloadAt ? formatDateTime(state.lastSuccessfulReloadAt) : "--";
  const roomConfig = config || null;
  const context = {
    rooms,
    room,
    roomConfig,
    hasRoomConfig,
    canEdit,
    climateItems,
    freshItems,
    lightItems,
    sensorItems,
    trackerItems,
    uiSettings,
    totalEntities,
    license,
    connectionText,
    refreshText,
  };

  root.innerHTML = `
    <div class="ref-settings-layout ref-settings-layout-topnav">
      <div class="ref-settings-topbar">
        <div class="ref-settings-menu">
          ${settingsMenuItems()
            .filter((item) => hasRoomConfig || !item.requiresRoom)
            .map((item) => `
              <button
                class="ref-settings-menu-btn ${state.currentSettingsSubPage === item.key ? "active" : ""}"
                type="button"
                onclick='switchSettingsSubPage(${JSON.stringify(item.key)}, this)'
              >
                <span class="ref-settings-menu-icon">${item.icon}</span>
                <span>${item.label}</span>
              </button>
            `).join("")}
        </div>
      </div>
      <section class="ref-settings-content">
        ${!isConnectionConfigured()
          ? renderEmptyState("请通过管理系统打开此页", "当前页面不在智慧网吧同源环境中，无法读取或保存任何数据。请从集成入口进入。")
          : renderReferenceSettingsContent(context)}
      </section>
    </div>
  `;
  bindSettingsDraftInputs(root);
  updateThemeSettingsVisibility();
  updateLinkageModeVisibility();
  updateGlobalEntityMatchSummaries();
}

function renderReferenceSettingsContent(context) {
  switch (state.currentSettingsSubPage) {
    case "basic":
      return renderReferenceBasicSettings(context);
    case "notify":
      return renderReferenceNotificationSettings(context);
    case "ac":
      return renderReferenceAcSettings(context);
    case "light":
      return renderReferenceLightSettings(context);
    case "fan":
      return renderReferenceFanSettings(context);
    case "linkage":
      return renderReferenceAutomationSettings(context);
    case "sub":
      return renderReferenceSubcontrolSettings(context);
    default:
      return renderReferenceBasicSettings(context);
  }
}

function renderReferenceSettingsHeader(title, description, actionsHtml = "", extraHtml = "") {
  return `
    <div class="ref-settings-header">
      <div class="ref-settings-header-left">
        <div class="sc-title">${escapeHtml(title)}</div>
        ${extraHtml ? `<div class="ref-settings-header-extra">${extraHtml}</div>` : ""}
      </div>
      ${actionsHtml ? `<div class="ref-settings-actions">${actionsHtml}</div>` : ""}
    </div>
  `;
}

function renderReferenceStatCard(label, value, tone = "") {
  return `
    <div class="ref-settings-stat ${tone}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value))}</strong>
    </div>
  `;
}

function renderReferenceSettingRow(label, description, controlHtml, extraClass = "") {
  return `
    <div class="ref-setting-row${extraClass ? ` ${extraClass}` : ""}">
      <div class="ref-setting-copy">
        <div class="ref-setting-label">${escapeHtml(label)}</div>
        ${description ? `<div class="ref-setting-desc">${escapeHtml(description)}</div>` : ""}
      </div>
      <div class="ref-setting-control">${controlHtml}</div>
    </div>
  `;
}

function renderReferenceKeywordPairRows(leftRowHtml, rightRowHtml) {
  return `
    <div class="ref-setting-pair-grid">
      ${leftRowHtml}
      ${rightRowHtml}
    </div>
  `;
}

function renderReferenceSwitch(id, checked, disabled = false, attrs = "") {
  return `
    <label class="ref-switch">
      <input id="${escapeHtml(id)}" type="checkbox" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""} ${attrs}>
      <span></span>
    </label>
  `;
}

function renderReferencePill(text, tone = "") {
  return `<span class="ref-pill${tone ? ` ${tone}` : ""}">${escapeHtml(text)}</span>`;
}

function renderReferenceChoiceCard(name, value, label, checked, description = "", type = "checkbox") {
  return `
    <label class="ref-choice-card">
      <input type="${escapeHtml(type)}" name="${escapeHtml(name)}" value="${escapeHtml(value)}" ${checked ? "checked" : ""}>
      <div>
        <strong>${escapeHtml(label)}</strong>
        ${description ? `<span>${escapeHtml(description)}</span>` : ""}
      </div>
    </label>
  `;
}

function renderReferenceFieldBlock(label, controlHtml, helper = "") {
  return `
    <div class="ref-field-block">
      <label>${escapeHtml(label)}</label>
      ${controlHtml}
      ${helper ? `<div class="ref-note">${escapeHtml(helper)}</div>` : ""}
    </div>
  `;
}

function renderReferencePageWrap(innerHtml) {
  return `<div class="ref-settings-page">${innerHtml}</div>`;
}

function themeSelectOptions(selectedValue) {
  const current = normalizeThemeKey(selectedValue);
  return [
    { value: "light", label: "日间" },
    { value: "dark", label: "暗黑" }
  ].map(opt => `<option value="${opt.value}" ${opt.value === current ? "selected" : ""}>${opt.label}</option>`).join("");
}

function renderReferenceEntityChips(items, emptyText = "当前没有匹配结果。") {
  const list = uniqueEntityOptions(items);
  if (!list.length) {
    return `<div class="ref-note">${escapeHtml(emptyText)}</div>`;
  }
  return `
    <div class="ref-settings-chip-row">
      ${list.map((item) => `
        <span class="ref-settings-chip">
          <strong>${escapeHtml(entityDisplayName(item))}</strong>
          <small>${escapeHtml(item.entity_id)}</small>
        </span>
      `).join("")}
    </div>
  `;
}

function renderReferenceEntityCount(
  items,
  title = "匹配结果",
  emptyText = "当前没有匹配结果。",
  summaryLabel = "个实体",
  detailText = "点击查看匹配详情。"
) {
  return renderReferenceEntityMatchTrigger(title, items, emptyText, summaryLabel, detailText);
}

function renderReferenceEntityMatchTrigger(title, items, emptyText = "当前没有匹配结果。", summaryLabel = "个实体", detailText = "点击查看匹配详情。") {
  const list = uniqueEntityOptions(items);
  const count = list.length;
  const summary = count ? `已匹配 ${count} ${summaryLabel}` : emptyText;
  return `
    <button
      class="ref-match-trigger${count ? "" : " is-empty"}"
      type="button"
      ${count ? `onclick='openEntityMatchModal(${JSON.stringify(title)}, ${JSON.stringify(list)}, ${JSON.stringify(emptyText)}, ${JSON.stringify(detailText)})'` : "disabled"}
    >
      <strong>${escapeHtml(summary)}</strong>
      <span>${escapeHtml(count ? detailText : "暂无可查看的匹配详情。")}</span>
    </button>
  `;
}

function renderReferenceRecognitionPreview(title, description, items, emptyText = "当前没有匹配结果。") {
  return `
    <div class="ref-settings-card">
      <div class="ref-settings-block-title">${escapeHtml(title)}</div>
      <div class="ref-preview-copy">
        <span>${escapeHtml(description)}</span>
        <strong>${escapeHtml(String(uniqueEntityOptions(items).length))} 个候选</strong>
      </div>
      <div class="ref-preview-grid">
        ${uniqueEntityOptions(items).slice(0, 8).map((item) => `
          <div class="ref-preview-card">
            <strong>${escapeHtml(entityDisplayName(item))}</strong>
            <span>${escapeHtml(item.entity_id)}</span>
          </div>
        `).join("") || `<div class="ref-preview-empty">${escapeHtml(emptyText)}</div>`}
      </div>
    </div>
  `;
}

function renderReferenceNotificationSettings(context) {
  const canEdit = Boolean(context && context.canEdit);
  const notifications = currentNotificationConfig().wechat;
  const status = currentNotificationStatus();
  const preview = currentNotificationPreview();
  const qr = currentNotificationQrStatus();
  const enabledChecked = draftCheckboxValue("notifyEnabled", notifications.enabled);
  const dailyChecked = draftCheckboxValue("notifyDailyBriefEnabled", notifications.daily_brief_enabled);
  const channel = draftTextValue("notifyChannel", notifications.channel || "wechat/user_id");
  const target = draftTextValue("notifyTarget", notifications.target || "");
  const accountId = draftTextValue("notifyWechatAccountId", notifications.wechat_account_id || "");
  const briefTime = draftTextValue("notifyDailyBriefTime", notifications.daily_brief_time || "23:00");
  const cooldown = draftTextValue("notifyOfflineCooldown", String(notifications.offline_cooldown_minutes ?? 30));
  const connectionLabel = !status.cn_im_hub_installed
    ? "未安装 cn_im_hub"
    : !status.send_service_available
      ? "发送服务不可用"
      : status.wechat_configured
        ? "微信已就绪"
        : "待补全配置";
  const qrState = String(qr.state || "").trim().toLowerCase();
  const qrImage = qr.qr_data_url || qr.qr_url || "";
  const accountsCount = Number(status.wechat_accounts_count || qr.accounts_count || 0) || 0;
  const previewText = String(preview.preview_text || "").trim();
  const qrSummary = qrState === "connected"
    ? "已连接"
    : qrImage
      ? "待扫码"
      : accountsCount
        ? "已绑定"
        : "未绑定";
  const accountSummary = status.resolved_wechat_account_id || accountId || (accountsCount ? `${accountsCount} 个已绑定账号` : "未识别");
  const targetSummary = target
    ? "已指定"
    : status.auto_match_enabled
      ? "自动匹配"
      : "未填写";
  const actions = `
    <button class="btn btn-secondary" type="button" onclick="refreshNotificationStatus()">刷新状态</button>
    <button class="btn btn-secondary" type="button" onclick="startNotificationQrSync()" ${canEdit ? "" : "disabled"}>同步二维码</button>
    <button class="btn btn-secondary" type="button" onclick="testNotificationSend()" ${canEdit ? "" : "disabled"}>发送今日摘要</button>
    <button class="btn btn-primary" type="button" onclick="saveNotificationSettings()" ${canEdit ? "" : "disabled"}>保存设置</button>
  `;
  const pills = `
    <div class="notify-header-pills">
      ${renderReferencePill(connectionLabel, status.send_service_available && status.wechat_configured ? "mint" : "amber")}
      ${renderReferencePill(targetSummary, !target && status.auto_match_enabled ? "blue" : "amber")}
      ${renderReferencePill(accountsCount ? `${accountsCount} 个微信账号` : "未绑定微信", accountsCount ? "mint" : "amber")}
      ${renderReferencePill(status.last_send_status === "success" ? "最近发送成功" : status.last_send_status === "failed" ? "最近发送失败" : "未发送", status.last_send_status === "success" ? "mint" : status.last_send_status === "failed" ? "amber" : "blue")}
    </div>
  `;
  return renderReferencePageWrap(`
    <div class="notify-page">
      ${renderReferenceSettingsHeader("微信通知", "通过 cn_im_hub 发送离线告警、异常提醒和每日日报。", actions, pills)}
      <div class="notify-layout">
        <div class="ref-settings-card notify-card notify-card-span-2">
          <div class="ref-settings-block-title">通知配置</div>
          ${renderReferenceSettingRow("启用微信通知", "设备离线和异常会走个人微信推送。", renderReferenceSwitch("notifyEnabled", enabledChecked, !canEdit, `onchange="rememberSettingDraft('notifyEnabled', this.checked)"`))}
          ${renderReferenceSettingRow("启用每日日报", "按本地时区定时推送当日汇总。", renderReferenceSwitch("notifyDailyBriefEnabled", dailyChecked, !canEdit, `onchange="rememberSettingDraft('notifyDailyBriefEnabled', this.checked)"`))}
          ${renderReferenceSettingRow("发送通道", "默认使用微信用户标识路由。", `<input id="notifyChannel" class="input" type="text" value="${escapeHtml(channel)}" ${canEdit ? "" : "disabled"} oninput="rememberSettingDraft('notifyChannel', this.value)">`)}
          ${renderReferenceSettingRow("发送目标", "可留空；留空时优先走 cn_im_hub 当前选中的微信对象自动匹配。", `<input id="notifyTarget" class="input" type="text" placeholder="可选" value="${escapeHtml(target)}" ${canEdit ? "" : "disabled"} oninput="rememberSettingDraft('notifyTarget', this.value)">`)}
          ${renderReferenceSettingRow("微信账号ID", "可选；多微信账号时可手动指定，只有一个账号时会自动匹配。", `<input id="notifyWechatAccountId" class="input" type="text" placeholder="可选" value="${escapeHtml(accountId)}" ${canEdit ? "" : "disabled"} oninput="rememberSettingDraft('notifyWechatAccountId', this.value)">`)}
          ${renderReferenceSettingRow("日报时间", "每日触发一次；同一天只会发送一份。", `<input id="notifyDailyBriefTime" class="input" type="time" value="${escapeHtml(briefTime)}" ${canEdit ? "" : "disabled"} oninput="rememberSettingDraft('notifyDailyBriefTime', this.value)">`)}
          ${renderReferenceSettingRow("离线冷却分钟", "同一设备持续离线时按冷却时间去重。", `<input id="notifyOfflineCooldown" class="input" type="number" min="0" step="1" value="${escapeHtml(cooldown)}" ${canEdit ? "" : "disabled"} oninput="rememberSettingDraft('notifyOfflineCooldown', this.value)">`)}
        </div>

        <div class="ref-settings-card notify-card">
          <div class="ref-settings-block-title">最近将发送文案预览</div>
          <div class="ref-preview-copy">
            <span>${escapeHtml(preview.title || "今日运行摘要")}</span>
            <strong>${escapeHtml(formatFriendlyDateTime(preview.occurred_at, preview.occurred_at_text || ""))}</strong>
          </div>
          <div class="notify-preview-text">${escapeHtml(previewText || "正在等待预览内容；刷新状态后会重新生成。")}</div>
        </div>

        <div class="ref-settings-card notify-card">
          <div class="ref-settings-block-title">二维码与连接</div>
          <div class="ref-preview-copy">
            <span>${escapeHtml(qr.message || (accountsCount ? "已检测到 cn_im_hub 微信账号。" : "点击上方“同步二维码”后可在这里扫码。"))}</span>
            <strong>${escapeHtml(qr.updated_at ? formatDateTime(qr.updated_at) : "--")}</strong>
          </div>
          ${qrImage ? `<div class="notify-qr-wrap"><img src="${escapeHtml(qrImage)}" alt="微信二维码" class="notify-qr-image"></div>` : ""}
          <div class="notify-card-body">
            <div class="ref-note">${escapeHtml(qrState === "connected" ? "扫码完成后，cn_im_hub 的微信账号已连接成功。" : qr.error || "二维码会在扫码确认期间自动轮询刷新状态。")}</div>
            <div class="notify-divider"></div>
            <div class="ref-note">${escapeHtml(status.last_send_error || status.resolved_wechat_account_id || status.raw_status || "当前没有更多状态详情。")}</div>
          </div>
        </div>
      </div>
    </div>
  `);
}

function renderReferenceBasicSettings(context) {
  const {
    canEdit,
    sensorItems,
    trackerItems,
    uiSettings,
  } = context;
  const config = currentGlobalSettings();
  const effectiveTheme = resolveConfiguredTheme(uiSettings);
  const autoThemeEnabled = Boolean(uiSettings.theme.auto_by_time);
  const triggerMode = triggerModeValue(config.automation.trigger_mode);
  const trackerMatches = filterEntityOptions(
    trackerItems,
    config.automation.device_tracker_include_keywords,
    config.automation.device_tracker_exclude_keywords
  );
  const sensorMatches = filterEntityOptions(
    sensorItems,
    config.automation.presence_sensor_include_keywords,
    config.automation.presence_sensor_exclude_keywords
  );
  const onlineTerminalItems = computerPresenceEntries(roomsForDisplay(), true);
  const offlineTerminalItems = computerPresenceEntries(roomsForDisplay(), false);
  const weatherConfig = state.weatherConfig || {};
  const weatherDomain = weatherConfig.domain || "weather.com.cn";
  const weatherSearchKeyword = draftTextValue("weatherSearchKeyword", weatherConfig.area_name || "");
  const weatherOptions = Array.isArray(state.weatherSearchResults) ? state.weatherSearchResults : [];
  const selectedWeatherAreaId = draftTextValue("weatherAreaId", weatherConfig.area_id || "");
  const weatherOptionsHtml = weatherOptions.length
    ? weatherOptions.map((item) => `
        <option value="${escapeHtml(item.area_id)}" ${item.area_id === selectedWeatherAreaId ? "selected" : ""}>${escapeHtml(item.label)}</option>
      `).join("")
    : `<option value="${escapeHtml(selectedWeatherAreaId || "")}" ${selectedWeatherAreaId ? "selected" : ""}>${escapeHtml(weatherConfig.area_name || "请先搜索地区")}</option>`;
  const actions = `
    <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">刷新数据</button>
    <button class="btn btn-primary" type="button" onclick="saveSystemSettings()" ${canEdit ? "" : "disabled"}>保存设置</button>
  `;
  const triggerOptions = `
    <option value="device_tracker" ${config.automation.trigger_mode === "device_tracker" ? "selected" : ""}>设备在线判断</option>
    <option value="sensor" ${config.automation.trigger_mode === "sensor" ? "selected" : ""}>人在传感器判断</option>
    <option value="hybrid" ${config.automation.trigger_mode === "hybrid" ? "selected" : ""}>混合判断</option>
  `;
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("基础设置", "集中维护品牌标识、主题策略和联动判断来源。", actions)}
    <div class="ref-settings-card">
      <div class="ref-settings-block-title">品牌自定义</div>
      ${renderReferenceSettingRow("站点名称", "侧边栏显示的品牌名称。", `<input id="brandNameInput" class="ref-input" type="text" value="${escapeHtml(uiSettings.brand.name)}" oninput="handleBrandSettingsChange()">`)}
      ${renderReferenceSettingRow("副标题", "Logo 下方显示的英文或描述文本。", `<input id="brandSubtitleInput" class="ref-input" type="text" value="${escapeHtml(uiSettings.brand.subtitle || "Netcafe")}" oninput="handleBrandSettingsChange()">`)}
      ${renderReferenceSettingRow("Logo 图片", "可直接上传到 Home Assistant 的 /config/www/netcafe，并自动回填为 /local/netcafe/... 链接。建议 1:1 透明背景 (PNG/SVG/JPG)，最大 2 MB。", `<div style=\"display:flex;gap:8px;align-items:center;flex-wrap:wrap\"><input id=\"brandLogoUrlInput\" class=\"ref-input\" type=\"text\" placeholder=\"https://... 或 /local/netcafe/brand_logo.png\" value=\"${escapeHtml(uiSettings.brand.logo_url)}\" oninput=\"handleBrandSettingsChange()\" style=\"flex:1;min-width:120px\"><button class=\"btn btn-sm\" type=\"button\" onclick=\"uploadBrandLogo()\">上传图片</button><input id=\"brandLogoFileInput\" type=\"file\" accept=\".png,.jpg,.jpeg,.gif,.svg,.webp,.ico\" style=\"display:none\" onchange=\"handleBrandLogoFileSelected(this)\"></div>`)}
      ${renderReferenceSettingRow("预设图库", "会自动读取 icons 文件夹里的图片；你以后只需要往里面放图并重新构建。", `<input id=\"brandLogoPresetInput\" type=\"hidden\" value=\"${escapeHtml(currentBrandLogoPresetKey(uiSettings.brand.logo_url))}\"><div id=\"brandLogoPresetPicker\">${renderBrandLogoPresetPicker(uiSettings.brand.logo_url)}</div>`, "align-start")}
    </div>
    <div class="ref-settings-card">
      <div class="ref-settings-block-title">天气地区</div>
      ${renderReferenceSettingRow("天气服务域名", "默认使用 weather.com.cn，一般无需修改。", `<input id="weatherDomainInput" class="ref-input" type="text" value="${escapeHtml(weatherDomain)}" placeholder="weather.com.cn">`)}
      ${renderReferenceSettingRow("搜索地区", "输入城市、区或县，前端直接搜索天气站点。", `<div style=\"display:flex;gap:8px;align-items:center;flex-wrap:wrap\"><input id=\"weatherSearchKeywordInput\" class=\"ref-input\" type=\"text\" value=\"${escapeHtml(weatherSearchKeyword)}\" placeholder=\"例如：佛山、顺德、广州\" style=\"flex:1;min-width:140px\"><button class=\"btn btn-secondary\" type=\"button\" onclick=\"searchWeatherLocations()\">搜索地区</button></div>`)}
      ${renderReferenceSettingRow("搜索结果", "选中后保存，顶部天气卡片会立即使用这里的地区。", `<div style=\"display:flex;gap:8px;align-items:center;flex-wrap:wrap\"><select id=\"weatherAreaIdSelect\" class=\"ref-input\" style=\"flex:1;min-width:180px\">${weatherOptionsHtml}</select><button class=\"btn btn-primary\" type=\"button\" onclick=\"saveWeatherSettings()\" ${canEdit ? "" : "disabled"}>保存天气地区</button></div>`, "align-start")}
      ${renderReferenceSettingRow("当前地区", "保存成功后这里会显示当前天气站点。", `<span class="ref-pill blue">${escapeHtml(weatherConfig.area_name || "未配置")}</span>`)}
    </div>
    <div class="ref-settings-card">
      <div class="ref-settings-block-title">主题策略</div>
      ${renderReferenceSettingRow("当前生效主题", "如果开启按时间切换，会根据白天/夜间配置自动切换。", `<span id="themeEffectivePill" class="ref-pill blue">${escapeHtml(themeLabel(effectiveTheme))}</span>`)}
      ${renderReferenceSettingRow("按时间自动切换", "开启后只显示自动切换相关设置，关闭后只保留手动主题。", renderReferenceSwitch("themeAutoByTime", uiSettings.theme.auto_by_time, false, 'onchange="handleThemeSettingsChange()"'), "tight")}
      ${renderReferenceSettingRow("手动主题", "关闭自动切换时，客户端直接使用这里的主题。", `<select id="clientThemeSelected" class="ref-input ref-input-sm" onchange="handleThemeSettingsChange()">${themeSelectOptions(uiSettings.theme.selected)}</select>`, `theme-mode-manual${autoThemeEnabled ? " is-hidden" : ""}`)}
      ${renderReferenceSettingRow("白天主题", "白天默认建议用日间主题。", `<select id="dayThemeSelected" class="ref-input ref-input-sm" onchange="handleThemeSettingsChange()">${themeSelectOptions(uiSettings.theme.day_theme)}</select>`, `theme-mode-auto${autoThemeEnabled ? "" : " is-hidden"}`)}
      ${renderReferenceSettingRow("白天开始时间", "早于夜间起始时间时，会按白天主题显示。", `<input id="themeDayStartTime" class="ref-input ref-input-sm" type="time" value="${escapeHtml(uiSettings.theme.day_start_time)}" onchange="handleThemeSettingsChange()">`, `theme-mode-auto${autoThemeEnabled ? "" : " is-hidden"}`)}
      ${renderReferenceSettingRow("夜间主题", "默认 18:00 后自动切到暗黑或科技主题。", `<select id="nightThemeSelected" class="ref-input ref-input-sm" onchange="handleThemeSettingsChange()">${themeSelectOptions(uiSettings.theme.night_theme)}</select>`, `theme-mode-auto${autoThemeEnabled ? "" : " is-hidden"}`)}
      ${renderReferenceSettingRow("夜间开始时间", "默认 18:00，可按你的营业时段自定义。", `<input id="themeNightStartTime" class="ref-input ref-input-sm" type="time" value="${escapeHtml(uiSettings.theme.night_start_time)}" onchange="handleThemeSettingsChange()">`, `theme-mode-auto${autoThemeEnabled ? "" : " is-hidden"}`)}
    </div>

    <div class="ref-settings-card">
      <div class="ref-settings-block-title">联动判断</div>
      ${renderReferenceSettingRow("判断模式", "决定联动在线状态优先来自 device_tracker、人在传感器还是两者混合。", `<select id="linkTriggerMode" class="ref-input" onchange="updateLinkageModeVisibility()">${triggerOptions}</select>`)}
      ${renderReferenceSettingRow("离线确认秒数", "终端连续失联达到这个秒数后，才会真正判定为离线。当前默认 45 秒，建议按现场网络稳定性调整。", `<input id="offlineConfirmSeconds" class="ref-input ref-input-sm" type="number" min="5" max="300" step="1" value="${escapeHtml(config.automation.offline_confirm_seconds)}">`)}
      ${renderReferenceSettingRow("Tracker 抓取关键词", "使用 device_tracker 模式时，按关键词自动匹配这一类 Tracker；留空则不过滤。", `<textarea id="deviceTrackerIncludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：电脑、pc、终端" oninput="updateLinkagePreviewResults()">${escapeHtml((config.automation.device_tracker_include_keywords || []).join("\n"))}</textarea>`, `align-start linkage-mode-tracker${triggerMode === "sensor" ? " is-hidden" : ""}`)}
      ${renderReferenceSettingRow("Tracker 排除关键词", "过滤访客、手机、测试或不应参与联动的 Tracker。", `<textarea id="deviceTrackerExcludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：手机、访客、测试" oninput="updateLinkagePreviewResults()">${escapeHtml((config.automation.device_tracker_exclude_keywords || []).join("\n"))}</textarea>`, `align-start linkage-mode-tracker${triggerMode === "sensor" ? " is-hidden" : ""}`)}
      ${renderReferenceSettingRow("Tracker 匹配结果", "匹配数量可直接点击查看具体命中的 Tracker。", `<div id="deviceTrackerMatchPreview">${renderReferenceEntityCount(trackerMatches, "Tracker 匹配结果", "当前没有匹配到 Tracker。", "个 Tracker", "点击查看具体匹配到的 Tracker。")}</div>`, `align-start linkage-mode-tracker${triggerMode === "sensor" ? " is-hidden" : ""}`)}
      ${renderReferenceSettingRow("传感器抓取关键词", "使用传感器模式时，按关键词自动匹配 sensor / binary_sensor；例如“人在传感器”。", `<textarea id="presenceSensorIncludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：人在传感器、occupancy、presence" oninput="updateLinkagePreviewResults()">${escapeHtml((config.automation.presence_sensor_include_keywords || []).join("\n"))}</textarea>`, `align-start linkage-mode-sensor${triggerMode === "device_tracker" ? " is-hidden" : ""}`)}
      ${renderReferenceSettingRow("传感器排除关键词", "过滤人体传感器、测试传感器或其他无关实体。", `<textarea id="presenceSensorExcludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：人体传感器、测试" oninput="updateLinkagePreviewResults()">${escapeHtml((config.automation.presence_sensor_exclude_keywords || []).join("\n"))}</textarea>`, `align-start linkage-mode-sensor${triggerMode === "device_tracker" ? " is-hidden" : ""}`)}
      ${renderReferenceSettingRow("传感器匹配结果", "匹配数量可直接点击查看具体命中的传感器。", `<div id="presenceSensorMatchPreview">${renderReferenceEntityCount(sensorMatches, "传感器匹配结果", "当前没有匹配到传感器。", "个传感器", "点击查看具体匹配到的传感器。")}</div>`, `align-start linkage-mode-sensor${triggerMode === "device_tracker" ? " is-hidden" : ""}`)}
      ${renderReferenceSettingRow("当前判断说明", "这里只定义“如何判断电脑是否有人/在线”，具体开关动作在自动化联动页中配置。", `<span id="linkTriggerModePill" class="ref-pill mint">${escapeHtml(config.automation.trigger_mode === "hybrid" ? "混合判断" : config.automation.trigger_mode === "sensor" ? "人在传感器" : "device_tracker")}</span>`)}
      ${renderReferenceSettingRow("当前在线终端", "点击查看此刻所有在线终端，便于核对联动是否命中正确电脑。", renderComputerPresenceTrigger("设置页在线终端", onlineTerminalItems, "当前没有在线终端。", "点击查看全部在线终端。"), "align-start")}
      ${renderReferenceSettingRow("当前离线终端", "点击查看此刻所有离线终端，便于排查误判或网络问题。", renderComputerPresenceTrigger("设置页离线终端", offlineTerminalItems, "当前没有离线终端。", "点击查看全部离线终端。"), "align-start")}
    </div>
  `);
}

function renderReferenceAcSettings(context) {
  const { canEdit } = context;
  const globalSettings = currentGlobalSettings();
  const entityFilters = globalSettings.entity_filters || {};
  const allTargets = globalEntityTargets(entityFilters);
  const detectedAcId = (allTargets.ac[0] && allTargets.ac[0].entity_id) || "";
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("空调控制", "这里维护全店空调识别规则和三套默认模式，包厢页与空调页会统一按这里的规则显示实体。", `
      <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">重新读取</button>
      <button class="btn btn-primary" type="button" onclick="saveSystemSettings()" ${canEdit ? "" : "disabled"}>保存并应用</button>
    `)}
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("包含关键词", "这些关键词会影响房间页和空调总览页中哪些空调会显示。", `<textarea id="acIncludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：026、单人包厢、空调" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((entityFilters.ac_include_keywords || []).join("\n"))}</textarea>`, "align-start")}
      ${renderReferenceSettingRow("排除关键词", "把测试、公共区或不应参与识别的空调排除掉。", `<textarea id="acExcludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：测试、公共区" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((entityFilters.ac_exclude_keywords || []).join("\n"))}</textarea>`, "align-start")}
      ${renderReferenceSettingRow("识别结果", "这里显示全店按当前规则筛选后的空调数量；点击可查看全部命中的实体。", `<div id="acMatchSummary">${renderReferenceEntityMatchTrigger("空调识别结果", allTargets.ac, "暂未识别到空调。", "个空调实体", "点击查看当前规则匹配到的全部空调实体。")}</div>`, "align-start")}
    </div>
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("当前模式", "保存后作为空调默认启用的全店模式来源。", `
        <select id="selectedSeason" class="ref-input ref-input-sm">
          <option value="summer" ${globalSettings.modes.selected_season === "summer" ? "selected" : ""}>夏季模式</option>
          <option value="winter" ${globalSettings.modes.selected_season === "winter" ? "selected" : ""}>冬季模式</option>
          <option value="custom" ${globalSettings.modes.selected_season === "custom" ? "selected" : ""}>自定义模式</option>
        </select>
      `)}
      ${renderReferenceSettingRow("夏季模式", "制冷模式和目标温度。", `
        <div class="ref-inline-stack">
          <label class="ref-inline-check"><input id="summerEnabled" type="checkbox" ${globalSettings.modes.summer.enabled ? "checked" : ""}><span>启用</span></label>
          <select id="summerHvacMode" class="ref-input ref-input-sm">${selectedAcModes(detectedAcId, globalSettings.modes.summer.hvac_mode)}</select>
          <select id="summerFanMode" class="ref-input ref-input-sm">${selectedAcFanModes(detectedAcId, globalSettings.modes.summer.fan_mode)}</select>
          <input id="summerTemp" class="ref-input ref-input-sm" type="number" min="16" max="32" step="1" value="${escapeHtml(globalSettings.modes.summer.temperature)}">
          <button class="btn btn-secondary" type="button" onclick="selectSeasonPreset('summer')">一键切换</button>
        </div>
      `)}
      ${renderReferenceSettingRow("冬季模式", "制热模式和目标温度。", `
        <div class="ref-inline-stack">
          <label class="ref-inline-check"><input id="winterEnabled" type="checkbox" ${globalSettings.modes.winter.enabled ? "checked" : ""}><span>启用</span></label>
          <select id="winterHvacMode" class="ref-input ref-input-sm">${selectedAcModes(detectedAcId, globalSettings.modes.winter.hvac_mode)}</select>
          <select id="winterFanMode" class="ref-input ref-input-sm">${selectedAcFanModes(detectedAcId, globalSettings.modes.winter.fan_mode)}</select>
          <input id="winterTemp" class="ref-input ref-input-sm" type="number" min="16" max="32" step="1" value="${escapeHtml(globalSettings.modes.winter.temperature)}">
          <button class="btn btn-secondary" type="button" onclick="selectSeasonPreset('winter')">一键切换</button>
        </div>
      `, "align-start")}
      ${renderReferenceSettingRow("自定义模式", "按你当前季节需要维护一套独立默认参数。", `
        <div class="ref-inline-stack">
          <label class="ref-inline-check"><input id="customEnabled" type="checkbox" ${globalSettings.modes.custom.enabled ? "checked" : ""}><span>启用</span></label>
          <select id="customHvacMode" class="ref-input ref-input-sm">${selectedAcModes(detectedAcId, globalSettings.modes.custom.hvac_mode)}</select>
          <select id="customFanMode" class="ref-input ref-input-sm">${selectedAcFanModes(detectedAcId, globalSettings.modes.custom.fan_mode)}</select>
          <input id="customTemp" class="ref-input ref-input-sm" type="number" min="16" max="32" step="1" value="${escapeHtml(globalSettings.modes.custom.temperature)}">
          <button class="btn btn-secondary" type="button" onclick="selectSeasonPreset('custom')">一键切换</button>
        </div>
      `, "align-start")}
    </div>
  `);
}

function renderReferenceLightSettings(context) {
  const { canEdit } = context;
  const entityFilters = currentGlobalSettings().entity_filters || {};
  const allTargets = globalEntityTargets(entityFilters);
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("灯光控制", "灯光页只负责全店识别规则，房间页和灯光总览页都会按这里的关键词显示实体。", `
      <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">重新读取</button>
      <button class="btn btn-primary" type="button" onclick="saveSystemSettings()" ${canEdit ? "" : "disabled"}>保存并应用</button>
    `)}
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("包含关键词", "这些关键词会影响房间页和灯光总览页里显示的灯具。", `<textarea id="lightIncludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：026、筒灯、射灯" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((entityFilters.light_include_keywords || []).join("\n"))}</textarea>`, "align-start")}
      ${renderReferenceSettingRow("排除关键词", "过滤公共区、过道或测试灯具。", `<textarea id="lightExcludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：过道、公共区" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((entityFilters.light_exclude_keywords || []).join("\n"))}</textarea>`, "align-start")}
      ${renderReferenceSettingRow("识别结果", "这里直接显示全店当前筛选到多少盏灯；点击可查看具体实体。", `<div id="lightMatchSummary">${renderReferenceEntityMatchTrigger("灯光识别结果", allTargets.lights, "暂未识别到灯光。", "盏灯", "点击查看当前规则匹配到的全部灯光实体。")}</div>`, "align-start")}
    </div>
  `);
}

function renderReferenceFanSettings(context) {
  const { canEdit } = context;
  const entityFilters = currentGlobalSettings().entity_filters || {};
  const allTargets = globalEntityTargets(entityFilters);
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("新风控制", "新风页只负责全店识别规则，房间页和新风总览页都会按这里的关键词显示实体。", `
      <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">重新读取</button>
      <button class="btn btn-primary" type="button" onclick="saveSystemSettings()" ${canEdit ? "" : "disabled"}>保存并应用</button>
    `)}
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("包含关键词", "这些关键词会影响房间页和新风总览页里显示的新风设备。", `<textarea id="freshIncludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：026、新风" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((entityFilters.fresh_air_include_keywords || []).join("\n"))}</textarea>`, "align-start")}
      ${renderReferenceSettingRow("排除关键词", "过滤测试、公共区或备用风机。", `<textarea id="freshExcludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：测试、备用" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((entityFilters.fresh_air_exclude_keywords || []).join("\n"))}</textarea>`, "align-start")}
      ${renderReferenceSettingRow("识别结果", "这里直接显示全店当前筛选到多少个新风；点击可查看具体实体。", `<div id="freshMatchSummary">${renderReferenceEntityMatchTrigger("新风识别结果", allTargets.fresh, "暂未识别到新风。", "个新风实体", "点击查看当前规则匹配到的全部新风实体。")}</div>`, "align-start")}
    </div>
  `);
}

function renderReferenceAutomationSettings(context) {
  const { canEdit } = context;
  const globalSettings = currentGlobalSettings();
  const roomTargets = automationTargetsFromGlobalSettings(globalSettings);
  const detectedFreshId = (roomTargets.fresh[0] && roomTargets.fresh[0].entity_id) || "";
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("自动化联动", "这里定义全店生效的开启联动和离线联动，所有包间都按这里的规则执行。", `
      <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">重新读取</button>
      <button class="btn btn-primary" type="button" onclick="saveSystemSettings()" ${canEdit ? "" : "disabled"}>保存并应用</button>
    `)}
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("自动化总开关", "关闭后全店自动联动动作都会停止执行。", renderReferenceSwitch("automationEnabled", globalSettings.automation.enabled), "tight")}
      ${renderReferenceSettingRow("当前判断模式", "判断来源来自基础设置页，自动化联动页只负责动作定义。", renderReferencePill(globalSettings.automation.trigger_mode === "hybrid" ? "混合判断" : globalSettings.automation.trigger_mode === "sensor" ? "人在传感器" : "device_tracker", "mint"))}
    </div>
    <div class="ref-linkage-grid">
      <div class="ref-settings-card">
        <div class="ref-settings-block-title">开启联动</div>
        ${renderReferenceKeywordPairRows(
          renderReferenceSettingRow("空调联动筛选", "在基础识别结果上，再按这里的关键词筛一次；例如只联动名字里带空调内机的实体。", `<textarea id="automationAcIncludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：空调内机、VIP" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((globalSettings.automation.ac.target_include_keywords || []).join("\n"))}</textarea>`, "align-start"),
          renderReferenceSettingRow("空调排除词", "不想参与自动化联动的空调写在这里。", `<textarea id="automationAcExcludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：测试、备用" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((globalSettings.automation.ac.target_exclude_keywords || []).join("\n"))}</textarea>`, "align-start")
        )}
        ${renderReferenceSettingRow("空调执行目标", "执行动作时会先走全店识别，再走上面的联动筛选；点击可查看具体实体。", `<div id="automationAcTargets">${renderReferenceEntityMatchTrigger("空调执行目标", roomTargets.ac, "暂未识别到空调。", "个空调实体", "点击查看当前规则会执行到的全部空调实体。")}</div>`, "align-start")}
        ${renderReferenceSettingRow("启用空调联动", "控制空调是否参与全店自动联动。", renderReferenceSwitch("acEnabled", globalSettings.automation.ac.enabled), "tight")}
        ${renderReferenceSettingRow("在线时启动空调", "联动判断为在线后，执行空调启动。", renderReferenceSwitch("acAutoOn", globalSettings.automation.ac.auto_on), "tight")}
        ${renderReferenceSettingRow("空调启动延迟", "电脑上线后延迟多久执行空调启动。", `<input id="acOnDelay" class="ref-input ref-input-sm" type="number" min="0" step="1" value="${escapeHtml(globalSettings.automation.ac.on_delay_sec)}">`)}
        ${renderReferenceSettingRow("启动采用模式", "空调自动开启时，采用当前模式、固定夏季、固定冬季或固定自定义预设。", `
          <select id="acSeasonStrategy" class="ref-input ref-input-sm">
            <option value="selected" ${globalSettings.automation.ac.season_strategy === "selected" ? "selected" : ""}>跟随当前模式</option>
            <option value="summer" ${globalSettings.automation.ac.season_strategy === "summer" ? "selected" : ""}>固定夏季模式</option>
            <option value="winter" ${globalSettings.automation.ac.season_strategy === "winter" ? "selected" : ""}>固定冬季模式</option>
            <option value="custom" ${globalSettings.automation.ac.season_strategy === "custom" ? "selected" : ""}>固定自定义模式</option>
          </select>
        `)}
        ${renderReferenceKeywordPairRows(
          renderReferenceSettingRow("灯光联动筛选", "可以只联动特定名字的灯，比如只让 name 含 灯带 的实体参与。", `<textarea id="automationLightIncludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：灯带、主灯" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((globalSettings.automation.light.target_include_keywords || []).join("\n"))}</textarea>`, "align-start"),
          renderReferenceSettingRow("灯光排除词", "这里写不想参与自动化联动的灯光关键词。", `<textarea id="automationLightExcludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：测试、过道" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((globalSettings.automation.light.target_exclude_keywords || []).join("\n"))}</textarea>`, "align-start")
        )}
        ${renderReferenceSettingRow("灯光执行目标", "执行动作时会先走全店识别，再走上面的联动筛选；点击可查看具体实体。", `<div id="automationLightTargets">${renderReferenceEntityMatchTrigger("灯光执行目标", roomTargets.lights, "暂未识别到灯光。", "盏灯", "点击查看当前规则会执行到的全部灯光实体。")}</div>`, "align-start")}
        ${renderReferenceSettingRow("启用灯光联动", "控制灯光是否参与全店自动联动。", renderReferenceSwitch("lightEnabled", globalSettings.automation.light.enabled), "tight")}
        ${renderReferenceSettingRow("在线时开灯", "联动判断为在线后，按识别到的灯光全部开启。", renderReferenceSwitch("lightAutoOn", globalSettings.automation.light.auto_on), "tight")}
        ${renderReferenceSettingRow("开灯延迟", "电脑上线后延迟多久执行开灯。", `<input id="lightOnDelay" class="ref-input ref-input-sm" type="number" min="0" step="1" value="${escapeHtml(globalSettings.automation.light.on_delay_sec)}">`)}
        ${renderReferenceKeywordPairRows(
          renderReferenceSettingRow("新风联动筛选", "只想让部分新风参与联动时，在这里写名字关键词。", `<textarea id="automationFreshIncludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：新风、排风" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((globalSettings.automation.fresh_air.target_include_keywords || []).join("\n"))}</textarea>`, "align-start"),
          renderReferenceSettingRow("新风排除词", "过滤测试机、备用机或公共区域新风。", `<textarea id="automationFreshExcludeKeywords" class="ref-input ref-textarea" placeholder="每行或逗号一个，比如：测试、备用" oninput="updateGlobalEntityMatchSummaries()">${escapeHtml((globalSettings.automation.fresh_air.target_exclude_keywords || []).join("\n"))}</textarea>`, "align-start")
        )}
        ${renderReferenceSettingRow("新风执行目标", "执行动作时会先走全店识别，再走上面的联动筛选；点击可查看具体实体。", `<div id="automationFreshTargets">${renderReferenceEntityMatchTrigger("新风执行目标", roomTargets.fresh, "暂未识别到新风。", "个新风实体", "点击查看当前规则会执行到的全部新风实体。")}</div>`, "align-start")}
        ${renderReferenceSettingRow("启用新风联动", "控制新风是否参与全店自动联动。", renderReferenceSwitch("freshEnabled", globalSettings.automation.fresh_air.enabled), "tight")}
        ${renderReferenceSettingRow("在线时启动新风", "联动判断为在线后，执行新风启动。", renderReferenceSwitch("freshAutoOn", globalSettings.automation.fresh_air.auto_on), "tight")}
        ${renderReferenceSettingRow("新风启动延迟", "电脑上线后延迟多久执行新风启动。", `<input id="freshOnDelay" class="ref-input ref-input-sm" type="number" min="0" step="1" value="${escapeHtml(globalSettings.automation.fresh_air.on_delay_sec)}">`)}
        ${renderReferenceSettingRow("启动默认档位", "新风自动启动时优先使用的 preset / fan mode。", `<select id="freshMode" class="ref-input ref-input-sm">${selectedFreshModes(detectedFreshId, globalSettings.automation.fresh_air.fan_mode)}</select>`)}
      </div>
      <div class="ref-settings-card">
        <div class="ref-settings-block-title">离线联动</div>
        ${renderReferenceSettingRow("离线时关闭空调", "联动判断为离线后，执行空调关闭。", renderReferenceSwitch("acAutoOff", globalSettings.automation.ac.auto_off), "tight")}
        ${renderReferenceSettingRow("空调关闭延迟", "电脑离线后延迟多久执行空调关闭。", `<input id="acOffDelay" class="ref-input ref-input-sm" type="number" min="0" step="1" value="${escapeHtml(globalSettings.automation.ac.off_delay_sec)}">`)}
        ${renderReferenceSettingRow("离线时关灯", "联动判断为离线后，按识别到的灯光全部关闭。", renderReferenceSwitch("lightAutoOff", globalSettings.automation.light.auto_off), "tight")}
        ${renderReferenceSettingRow("关灯延迟", "电脑离线后延迟多久执行关灯。", `<input id="lightOffDelay" class="ref-input ref-input-sm" type="number" min="0" step="1" value="${escapeHtml(globalSettings.automation.light.off_delay_sec)}">`)}
        ${renderReferenceSettingRow("离线时关闭新风", "联动判断为离线后，执行新风关闭。", renderReferenceSwitch("freshAutoOff", globalSettings.automation.fresh_air.auto_off), "tight")}
        ${renderReferenceSettingRow("新风关闭延迟", "电脑离线后延迟多久执行新风关闭。", `<input id="freshOffDelay" class="ref-input ref-input-sm" type="number" min="0" step="1" value="${escapeHtml(globalSettings.automation.fresh_air.off_delay_sec)}">`)}
      </div>
    </div>
  `);
}

function renderReferenceSubcontrolSettings(context) {
  const { room, roomConfig, hasRoomConfig, canEdit } = context;
  const globalSettings = currentGlobalSettings();
  const subcontrolTrust = globalSettings.subcontrol_trust || { enabled: false, allowed_cidrs: [], trust_proxy_headers: false };
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("副中控管理", "参考稿中的副中控页改成权限矩阵，所有开关都会同步到后端分机能力判断。", `
      <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">重新读取</button>
      <button class="btn btn-primary" type="button" onclick="saveCurrentRoomSubcontrol()" ${hasRoomConfig && canEdit ? "" : "disabled"}>保存并应用</button>
    `)}
    <div class="ref-settings-card">
      <div class="ref-settings-block-title">分机局域网免鉴权</div>
      ${renderReferenceSettingRow("启用局域网白名单", "开启后，来自指定局域网网段的分机请求可直接访问分机接口，不再强制要求 token。", renderReferenceSwitch("subcontrolTrustEnabled", subcontrolTrust.enabled), "tight")}
      ${renderReferenceSettingRow("允许的 CIDR 网段", "每行一个网段，例如 192.168.0.0/24。仅这些网段内的分机可免 token 调用分机接口。", `<textarea id="subcontrolAllowedCidrs" class="ref-input ref-textarea" placeholder="每行一个，例如：192.168.0.0/24">${escapeHtml((subcontrolTrust.allowed_cidrs || []).join("\n"))}</textarea>`, "align-start")}
      ${renderReferenceSettingRow("信任代理头", "默认关闭。只有在你确认反向代理会正确传递真实客户端 IP 时才开启。", renderReferenceSwitch("subcontrolTrustProxyHeaders", subcontrolTrust.trust_proxy_headers), "tight")}
      ${renderReferenceSettingRow("当前策略", "仅对分机 mapping / bootstrap / action / license 接口生效，不影响总控面板登录。", renderReferencePill(subcontrolTrust.enabled ? `已启用 (${(subcontrolTrust.allowed_cidrs || []).length} 个网段)` : "未启用", subcontrolTrust.enabled ? "mint" : "amber"))}
      <div class="helper">这部分是全局设置。放在副中控页里统一管理，但会同时作用于所有分机接口。</div>
    </div>
    ${hasRoomConfig && roomConfig ? `
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("启用分机控制", "关闭后分机界面会整体置灰，后端也会拒绝控制。", renderReferenceSwitch("subEnabled", roomConfig.subcontrol.enabled), "tight")}
      ${renderReferenceSettingRow("允许空调开关", "分机是否能直接开关空调。", renderReferenceSwitch("subAllowAcPower", roomConfig.subcontrol.allow_ac_power), "tight")}
      ${renderReferenceSettingRow("允许调温", "分机是否能调节空调目标温度。", renderReferenceSwitch("subAllowAcTemperature", roomConfig.subcontrol.allow_ac_temperature), "tight")}
      ${renderReferenceSettingRow("允许模式切换", "分机是否能切换制冷 / 制热 / 自动模式。", renderReferenceSwitch("subAllowAcMode", roomConfig.subcontrol.allow_ac_mode), "tight")}
      ${renderReferenceSettingRow("允许风速切换", "分机是否能切换风速档位。", renderReferenceSwitch("subAllowAcFanMode", roomConfig.subcontrol.allow_ac_fan_mode), "tight")}
      ${renderReferenceSettingRow("允许灯光控制", "分机是否能直接控制灯光。", renderReferenceSwitch("subAllowLightControl", roomConfig.subcontrol.allow_light_control), "tight")}
      ${renderReferenceSettingRow("强制季节模式", "开启后分机不能切换空调模式，只能跟随总控季节。", renderReferenceSwitch("subEnforceSeason", roomConfig.subcontrol.enforce_selected_season), "tight")}
      ${renderReferenceSettingRow("继承总控温度上下限", "沿用总控空调页面配置的温度保护范围。", renderReferenceSwitch("subInheritTemperatureLimits", roomConfig.subcontrol.inherit_temperature_limits), "tight")}
      ${renderReferenceSettingRow("启用自定义分机温度限制", "单独覆盖分机可调范围，优先级高于继承总控。", renderReferenceSwitch("subCustomTemperatureLimitsEnabled", roomConfig.subcontrol.custom_temperature_limits_enabled), "tight")}
      ${renderReferenceSettingRow("分机最低温度", "仅在启用自定义限制后生效。", `<input id="subMinTemperature" class="ref-input ref-input-sm" type="number" min="16" max="32" step="1" value="${escapeHtml(roomConfig.subcontrol.min_temperature)}">`)}
      ${renderReferenceSettingRow("分机最高温度", "仅在启用自定义限制后生效。", `<input id="subMaxTemperature" class="ref-input ref-input-sm" type="number" min="16" max="32" step="1" value="${escapeHtml(roomConfig.subcontrol.max_temperature)}">`)}
    </div>
    ` : renderEmptyState("请选择房间", "局域网免鉴权已经放到这个页面里了；如需继续设置某个包厢的分机权限，请先选择房间。")}
  `);
}

function renderReferenceAccountSettings(context) {
  const { connectionText, refreshText, license } = context;
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("账户管理", "保留卡密激活和连接检测，把原来的系统信息改成参考稿样式的设置卡片。", `
      <button class="btn btn-secondary" type="button" onclick="testConnection()">测试连接</button>
    `)}
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("当前地址", "当前面板请求的 API 基础地址。", renderReferencePill(state.connection.apiBase || "--"))}
      ${renderReferenceSettingRow("卡密", "输入完整卡密并提交到后端激活。", `<input id="licenseKeyInput" class="ref-input" type="text" placeholder="输入卡密">`)}
      ${renderReferenceSettingRow("设备 ID", "可选，不填则由后端根据环境判断。", `<input id="licenseDeviceInput" class="ref-input" type="text" placeholder="可选，不填则由后端判定">`)}
      ${renderReferenceSettingRow("当前到期时间", "激活成功后会显示后端返回的授权到期时间。", renderReferencePill(license && license.expires_at ? formatDateTime(license.expires_at) : "--", "amber"))}
      <div class="ref-setting-row">
        <div class="ref-setting-copy">
          <div class="ref-setting-label">执行操作</div>
          <div class="ref-setting-desc">激活卡密或重新测试连接状态。</div>
        </div>
        <div class="ref-setting-control ref-button-row">
          <button class="btn btn-secondary" type="button" onclick="testConnection()">测试连接</button>
          <button class="btn btn-primary" type="button" onclick="activateLicense()">激活卡密</button>
        </div>
      </div>
    </div>
  `);
}

function renderReferenceHaSettings(context) {
  const { totalEntities, refreshText } = context;
  const roomCount = currentRooms().length;
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("智慧网吧中心接入", "直接显示当前接入环境、实体数量和同步方式。")}
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("面板入口", "当前主面板页面路径。", renderReferencePill("/api/netcafe/1.html"))}
      ${renderReferenceSettingRow("同步方式", "当前页面与后端同步状态。", renderReferencePill(state.syncMode, "blue"))}
      ${renderReferenceSettingRow("已加载房间", "当前总览里可见的房间数量。", renderReferencePill(roomCount))}
      ${renderReferenceSettingRow("最近刷新", "最近一次成功刷新页面数据的时间。", renderReferencePill(refreshText || "--", "amber"))}
    </div>
    <div class="ref-settings-card">
      <div class="ref-settings-block-title">接入摘要</div>
      <pre class="code-block">${formatJsonBlock({
        room_count: roomCount,
        total_entities: totalEntities,
        sync_mode: state.syncMode,
        last_refresh_at: refreshText || null,
      })}</pre>
    </div>
  `);
}

function renderReferenceThemeSettings() {
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("客户端主题", "保留现有主题能力，但按参考稿重做成大卡片选择器。")}
    <div class="ref-theme-grid">
      <button class="ref-theme-card ${state.currentTheme === "light" ? "active" : ""}" type="button" onclick="selectClientTheme('light')">
        <div class="ref-theme-preview light"></div>
        <div class="ref-theme-name">浅色</div>
        <div class="ref-theme-desc">明亮清爽</div>
      </button>
      <button class="ref-theme-card ${state.currentTheme === "dark" ? "active" : ""}" type="button" onclick="selectClientTheme('dark')">
        <div class="ref-theme-preview dark"></div>
        <div class="ref-theme-name">深色</div>
        <div class="ref-theme-desc">护眼舒适</div>
      </button>
      <button class="ref-theme-card ${state.currentTheme === "ocean" ? "active" : ""}" type="button" onclick="selectClientTheme('ocean')">
        <div class="ref-theme-preview ocean"></div>
        <div class="ref-theme-name">海洋</div>
        <div class="ref-theme-desc">更强调设备状态和冷暖层次</div>
      </button>
    </div>
  `);
}

function renderReferenceAboutSettings(context) {
  const { license, totalEntities } = context;
  return renderReferencePageWrap(`
    ${renderReferenceSettingsHeader("关于", "保留必要的项目说明，不再显示旧版系统工作台。")}
    <div class="ref-about-card">
      <div class="ref-about-logo">智享</div>
      <div class="ref-about-name">智慧网吧管理系统</div>
      <div class="ref-about-sub">Smart Netcafe Automation Control</div>
      <div class="ref-about-ver">Build 2026.04</div>
    </div>
    <div class="ref-settings-card">
      ${renderReferenceSettingRow("当前主题", "客户端当前使用的界面主题。", renderReferencePill(state.currentTheme))}
      ${renderReferenceSettingRow("可见实体", "当前从智慧网吧读取到的实体总数。", renderReferencePill(totalEntities, "blue"))}
      ${renderReferenceSettingRow("卡密状态", "当前授权状态，来自后端 license 接口。", renderReferencePill(license ? (license.message || "已读取") : "未读取", "amber"))}
      ${renderReferenceSettingRow("同步状态", "当前页面使用的实时同步方式。", renderReferencePill(state.syncMode, "mint"))}
    </div>
  `);
}

function renderSettingsSubNav(hasRoomConfig) {
  const items = settingsMenuItems().filter((item) => hasRoomConfig || !item.requiresRoom);
  return `
    <div class="card settings-nav">
      ${items.map((item) => `
        <button class="settings-nav-btn ${state.currentSettingsSubPage === item.key ? "active" : ""}" type="button" onclick='switchSettingsSubPage(${JSON.stringify(item.key)}, this)'>
          <span class="settings-nav-icon">${item.icon}</span>
          <span class="settings-nav-label">${item.label}</span>
        </button>
      `).join("")}
    </div>
  `;
}

function renderSettingsEditor(room, config, climateItems, freshItems, lightItems, sensorItems, trackerItems, canEdit) {
  const roomItems = roomsForDisplay();
  const roomConfig = config || null;
  const acIsClimate = Boolean(roomConfig && String(roomConfig.entities.ac || "").startsWith("climate."));
  const totalEntities = ["climate", "light", "fan", "switch", "sensor"].reduce((sum, key) => sum + candidatesFor(key).length, 0);
  const license = currentLicenseStatus();
  const connectionText = !isConnectionConfigured() ? "未通过 HA 打开" : state.authError ? "只读模式" : canEdit ? "已连接" : "连接中";
  const hasRoomConfig = Boolean(room && roomConfig);
  const refreshText = state.lastSuccessfulReloadAt ? formatDateTime(state.lastSuccessfulReloadAt) : "--";
  const entityFilters = roomConfig && roomConfig.entity_filters ? roomConfig.entity_filters : {};
  const acOptions = filterEntityOptions(
    [...roomAcOptions(room, roomConfig), ...climateItems],
    entityFilters.ac_include_keywords,
    entityFilters.ac_exclude_keywords
  );
  const freshAirOptions = filterEntityOptions(
    [...roomFreshAirOptions(room, roomConfig), ...freshItems],
    entityFilters.fresh_air_include_keywords,
    entityFilters.fresh_air_exclude_keywords
  );
  const roomLightItems = filterEntityOptions(
    [...roomLightOptions(room, roomConfig), ...lightItems],
    entityFilters.light_include_keywords,
    entityFilters.light_exclude_keywords
  );
  const selectedLightIds = new Set(Array.isArray(roomConfig && roomConfig.entities && roomConfig.entities.lights) ? roomConfig.entities.lights : []);
  const fullOnLightIds = new Set(Array.isArray(roomConfig && roomConfig.lighting_presets && roomConfig.lighting_presets.full_on) ? roomConfig.lighting_presets.full_on : []);
  const fullOffLightIds = new Set(Array.isArray(roomConfig && roomConfig.lighting_presets && roomConfig.lighting_presets.full_off) ? roomConfig.lighting_presets.full_off : []);
  const acEntity = candidateById(roomConfig && roomConfig.entities ? roomConfig.entities.ac : "");
  const freshEntity = candidateById(roomConfig && roomConfig.entities ? roomConfig.entities.fresh_air : "");
  const seasonalSummary = roomConfig ? `
    <div class="season-btns">
      <button class="season-btn summer" type="button" onclick="selectSeasonPreset('summer')">
        <strong>☀ 夏季模式</strong>
        <span>当前配置: ${escapeHtml(roomConfig.modes.summer.hvac_mode || "--")} / ${escapeHtml(String(roomConfig.modes.summer.temperature || "--"))}℃ / ${escapeHtml(roomConfig.modes.summer.fan_mode || "--")}<br>点击后只更新当前表单，保存后生效。</span>
      </button>
      <button class="season-btn winter" type="button" onclick="selectSeasonPreset('winter')">
        <strong>❄ 冬季模式</strong>
        <span>当前配置: ${escapeHtml(roomConfig.modes.winter.hvac_mode || "--")} / ${escapeHtml(String(roomConfig.modes.winter.temperature || "--"))}℃ / ${escapeHtml(roomConfig.modes.winter.fan_mode || "--")}<br>点击后只更新当前表单，保存后生效。</span>
      </button>
    </div>
  ` : renderEmptyState("请选择房间", "当前没有可编辑的房间配置。");

  return `
    <div class="settings-content-shell">
      <div class="card editor-card">
        <section class="settings-subpage ${state.currentSettingsSubPage === "ac" ? "active" : ""}" data-settings-page="ac">
          ${hasRoomConfig ? `
            ${renderSettingsPageHead("空调控制", "", "", `
              <div class="chip-list">
                <span class="chip">${acIsClimate ? "climate 可调温" : "当前仅开关型"}</span>
              </div>
            `)}
            ${renderSharedLinkagePanel(roomConfig, sensorItems, trackerItems)}
            <div class="settings-page-stack">
              <section class="editor-section">
                <h4>识别结果与运行模式</h4>
                <div class="editor-stack">
                  <div class="field">
                    <label>包含关键词</label>
                    <textarea id="acIncludeKeywords" class="setting-input field-textarea" placeholder="每行或逗号一个，比如：026、单人包厢、空调">${escapeHtml((entityFilters.ac_include_keywords || []).join('\n'))}</textarea>
                  </div>
                  <div class="field">
                    <label>排除关键词</label>
                    <textarea id="acExcludeKeywords" class="setting-input field-textarea" placeholder="每行或逗号一个，比如：测试、离线">${escapeHtml((entityFilters.ac_exclude_keywords || []).join('\n'))}</textarea>
                  </div>
                  <div class="field">
                    <label>筛选后的空调候选</label>
                    <div class="check-grid">
                      ${acOptions.map((item) => checkCard("ac_select", item.entity_id, entityDisplayName(item), item.entity_id === roomConfig.entities.ac)).join("") || '<div class="helper">当前包厢没有识别到可绑定空调。</div>'}
                    </div>
                    <div class="helper">保存后按你输入的关键词重新筛选候选空调。</div>
                  </div>
                  <div class="field">
                    <label>当前季节</label>
                    <select id="selectedSeason">
                      <option value="summer" ${roomConfig.modes.selected_season === "summer" ? "selected" : ""}>夏季</option>
                      <option value="winter" ${roomConfig.modes.selected_season === "winter" ? "selected" : ""}>冬季</option>
                    </select>
                  </div>
                  <div class="editor-section">
                    <h4>夏季模式</h4>
                    <div class="editor-stack">
                      <label class="toggle-row"><span>启用夏季模式</span><input type="checkbox" id="summerEnabled" ${roomConfig.modes.summer.enabled ? "checked" : ""}></label>
                      <div class="inline-fields">
                        <div class="field">
                          <label>运行模式</label>
                          <select id="summerHvacMode">${selectedAcModes(roomConfig.entities.ac, roomConfig.modes.summer.hvac_mode)}</select>
                        </div>
                        <div class="field">
                          <label>风速</label>
                          <select id="summerFanMode">${selectedAcFanModes(roomConfig.entities.ac, roomConfig.modes.summer.fan_mode)}</select>
                        </div>
                      </div>
                      <div class="field">
                        <label>默认温度</label>
                        <input id="summerTemp" type="number" min="16" max="32" step="1" value="${escapeHtml(roomConfig.modes.summer.temperature)}" ${acIsClimate ? "" : "disabled"}>
                      </div>
                    </div>
                  </div>
                  <div class="editor-section">
                    <h4>冬季模式</h4>
                    <div class="editor-stack">
                      <label class="toggle-row"><span>启用冬季模式</span><input type="checkbox" id="winterEnabled" ${roomConfig.modes.winter.enabled ? "checked" : ""}></label>
                      <div class="inline-fields">
                        <div class="field">
                          <label>运行模式</label>
                          <select id="winterHvacMode">${selectedAcModes(roomConfig.entities.ac, roomConfig.modes.winter.hvac_mode)}</select>
                        </div>
                        <div class="field">
                          <label>风速</label>
                          <select id="winterFanMode">${selectedAcFanModes(roomConfig.entities.ac, roomConfig.modes.winter.fan_mode)}</select>
                        </div>
                      </div>
                      <div class="field">
                        <label>默认温度</label>
                        <input id="winterTemp" type="number" min="16" max="32" step="1" value="${escapeHtml(roomConfig.modes.winter.temperature)}" ${acIsClimate ? "" : "disabled"}>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
              <div class="card settings-block">
                <h4>联动动作与温控保护</h4>
                <div class="editor-stack">
                  <div class="field">
                    <label>在线时要联动的空调</label>
                    <div class="linkage-target-grid">
                      ${linkageTargetCard("ac_auto_on_target", roomConfig.entities.ac || "bound", acEntity ? entityDisplayName(acEntity) : "当前未绑定空调", roomConfig.automation.ac.auto_on, "在线后执行开启动作")}
                    </div>
                  </div>
                  <div class="field">
                    <label>离线时要联动的空调</label>
                    <div class="linkage-target-grid">
                      ${linkageTargetCard("ac_auto_off_target", roomConfig.entities.ac || "bound", acEntity ? entityDisplayName(acEntity) : "当前未绑定空调", roomConfig.automation.ac.auto_off, "离线后执行关闭动作")}
                    </div>
                  </div>
                  <div class="inline-fields">
                    <div class="field">
                      <label>开启延迟(秒)</label>
                      <input id="acOnDelay" type="number" min="0" step="1" value="${escapeHtml(roomConfig.automation.ac.on_delay_sec)}">
                    </div>
                    <div class="field">
                      <label>关闭延迟(秒)</label>
                      <input id="acOffDelay" type="number" min="0" step="1" value="${escapeHtml(roomConfig.automation.ac.off_delay_sec)}">
                    </div>
                  </div>
                  <div class="field">
                    <label>在线后使用的空调模式</label>
                    <select id="acSeasonStrategy">
                      <option value="selected" ${roomConfig.automation.ac.season_strategy === "selected" ? "selected" : ""}>跟随当前季节</option>
                      <option value="summer" ${roomConfig.automation.ac.season_strategy === "summer" ? "selected" : ""}>固定夏季模式</option>
                      <option value="winter" ${roomConfig.automation.ac.season_strategy === "winter" ? "selected" : ""}>固定冬季模式</option>
                    </select>
                  </div>
                  <label class="toggle-row"><span>允许手动覆盖自动设定</span><input type="checkbox" id="acManualOverride" ${roomConfig.automation.ac.manual_override ? "checked" : ""}></label>
                  <div class="inline-fields">
                    <div class="field">
                      <label>恢复自动设定延迟(秒)</label>
                      <input id="acRestoreDelay" type="number" min="0" step="1" value="${escapeHtml(roomConfig.automation.ac.restore_delay_sec)}">
                    </div>
                    <div class="field">
                      <label>温度限制</label>
                      <label class="toggle-row"><span>启用温度上下限</span><input type="checkbox" id="acTemperatureLimitsEnabled" ${roomConfig.automation.ac.temperature_limits_enabled ? "checked" : ""}></label>
                    </div>
                  </div>
                  <div class="inline-fields">
                    <div class="field">
                      <label>最低温度</label>
                      <input id="acMinTemperature" type="number" min="16" max="32" step="1" value="${escapeHtml(roomConfig.automation.ac.min_temperature)}" ${acIsClimate ? "" : "disabled"}>
                    </div>
                    <div class="field">
                      <label>最高温度</label>
                      <input id="acMaxTemperature" type="number" min="16" max="32" step="1" value="${escapeHtml(roomConfig.automation.ac.max_temperature)}" ${acIsClimate ? "" : "disabled"}>
                    </div>
                  </div>
                  <div class="helper">分包控制器可以继续继承这里的范围，或者在“副中控”里设置独立限制。</div>
                </div>
              </div>
              <div class="card settings-block">
                <h4>一键季节模式</h4>
                ${seasonalSummary}
              </div>
            </div>
          ` : renderEmptyState("请选择房间", "空调控制需要先选中一个已映射配置的包厢。")}
        </section>

        <section class="settings-subpage ${state.currentSettingsSubPage === "light" ? "active" : ""}" data-settings-page="light">
          ${hasRoomConfig ? `
            ${renderSettingsPageHead("灯光控制")}
            ${renderSharedLinkagePanel(roomConfig, sensorItems, trackerItems)}
            <div class="settings-page-stack">
              <section class="editor-section">
                <h4>电脑在线时开哪些灯</h4>
                <div class="editor-stack">
                  <div class="field">
                    <label>包含关键词</label>
                    <textarea id="lightIncludeKeywords" class="setting-input field-textarea" placeholder="每行或逗号一个，比如：026、筒灯、射灯">${escapeHtml((entityFilters.light_include_keywords || []).join('\n'))}</textarea>
                  </div>
                  <div class="field">
                    <label>排除关键词</label>
                    <textarea id="lightExcludeKeywords" class="setting-input field-textarea" placeholder="每行或逗号一个，比如：过道、公共区、测试">${escapeHtml((entityFilters.light_exclude_keywords || []).join('\n'))}</textarea>
                  </div>
                  <div class="field">
                    <label>筛选后的灯光候选</label>
                    <div class="check-grid">
                      ${roomLightItems.map((item) => checkCard("preset_full_on", item.entity_id, entityDisplayName(item), fullOnLightIds.has(item.entity_id) || selectedLightIds.has(item.entity_id))).join("") || '<div class="helper">当前包厢没有识别到可绑定灯光。</div>'}
                    </div>
                    <div class="helper">保存后按这些关键词筛选候选灯光，再从中勾选在线开启和离线关闭的灯。</div>
                  </div>
                </div>
              </section>
              <div class="card settings-block">
                <h4>在线/离线联动动作</h4>
                <div class="editor-stack">
                  <label class="toggle-row"><span>启用灯光自动化</span><input type="checkbox" id="lightEnabled" ${roomConfig.automation.light.enabled ? "checked" : ""}></label>
                  <div class="inline-fields">
                    <div class="field">
                      <label>在线延迟(秒)</label>
                      <input id="lightOnDelay" type="number" min="0" step="1" value="${escapeHtml(roomConfig.automation.light.on_delay_sec)}">
                    </div>
                    <div class="field">
                      <label>离线延迟(秒)</label>
                      <input id="lightOffDelay" type="number" min="0" step="1" value="${escapeHtml(roomConfig.automation.light.off_delay_sec)}">
                    </div>
                  </div>
                  <label class="toggle-row"><span>在线时执行开灯联动</span><input type="checkbox" id="lightAutoOn" ${roomConfig.automation.light.auto_on ? "checked" : ""}></label>
                  <label class="toggle-row"><span>离线时执行关灯联动</span><input type="checkbox" id="lightAutoOff" ${roomConfig.automation.light.auto_off ? "checked" : ""}></label>
                  <div class="field">
                    <label>离线时要关闭的灯光</label>
                    <div class="check-grid">
                      ${roomLightItems.map((item) => checkCard("preset_full_off", item.entity_id, entityDisplayName(item), fullOffLightIds.has(item.entity_id) || selectedLightIds.has(item.entity_id))).join("") || '<div class="helper">当前包厢没有识别到可绑定灯光。</div>'}
                    </div>
                  </div>
                  <div class="helper">可以分别定义在线开哪些灯、离线关哪些灯，例如在线开灯带，离线关筒灯和射灯。</div>
                </div>
              </div>
            </div>
          ` : renderEmptyState("请选择房间", "灯光控制需要先选中一个已映射配置的包厢。")}
        </section>

        <section class="settings-subpage ${state.currentSettingsSubPage === "fan" ? "active" : ""}" data-settings-page="fan">
          ${hasRoomConfig ? `
            ${renderSettingsPageHead("新风控制")}
            ${renderSharedLinkagePanel(roomConfig, sensorItems, trackerItems)}
            <div class="settings-page-stack">
              <section class="editor-section">
                <h4>识别结果与绑定</h4>
                <div class="editor-stack">
                  <div class="field">
                    <label>包含关键词</label>
                    <textarea id="freshIncludeKeywords" class="setting-input field-textarea" placeholder="每行或逗号一个，比如：026、新风">${escapeHtml((entityFilters.fresh_air_include_keywords || []).join('\n'))}</textarea>
                  </div>
                  <div class="field">
                    <label>排除关键词</label>
                    <textarea id="freshExcludeKeywords" class="setting-input field-textarea" placeholder="每行或逗号一个，比如：测试、备用">${escapeHtml((entityFilters.fresh_air_exclude_keywords || []).join('\n'))}</textarea>
                  </div>
                  <div class="field">
                    <label>筛选后的新风候选</label>
                    <div class="check-grid">
                      ${freshAirOptions.map((item) => checkCard("fresh_select", item.entity_id, item.friendly_name || item.entity_id, item.entity_id === roomConfig.entities.fresh_air)).join("") || '<div class="helper">当前包厢没有识别到可绑定新风。</div>'}
                    </div>
                    <div class="helper">保存后按你输入的关键词重新筛选候选新风。</div>
                  </div>
                </div>
              </section>
              <section class="editor-section">
                <h4>在线/离线联动动作</h4>
                <div class="editor-stack">
                  <label class="toggle-row"><span>启用新风自动化</span><input type="checkbox" id="freshEnabled" ${roomConfig.automation.fresh_air.enabled ? "checked" : ""}></label>
                  <div class="field">
                    <label>在线时要联动的新风</label>
                    <div class="linkage-target-grid">
                      ${linkageTargetCard("fresh_auto_on_target", roomConfig.entities.fresh_air || "bound", freshEntity ? entityDisplayName(freshEntity) : "当前未绑定新风", roomConfig.automation.fresh_air.auto_on, "在线后执行开启动作")}
                    </div>
                  </div>
                  <div class="field">
                    <label>离线时要联动的新风</label>
                    <div class="linkage-target-grid">
                      ${linkageTargetCard("fresh_auto_off_target", roomConfig.entities.fresh_air || "bound", freshEntity ? entityDisplayName(freshEntity) : "当前未绑定新风", roomConfig.automation.fresh_air.auto_off, "离线后执行关闭动作")}
                    </div>
                  </div>
                  <div class="inline-fields">
                    <div class="field">
                      <label>开启延迟(秒)</label>
                      <input id="freshOnDelay" type="number" min="0" step="1" value="${escapeHtml(roomConfig.automation.fresh_air.on_delay_sec)}">
                    </div>
                    <div class="field">
                      <label>关闭延迟(秒)</label>
                      <input id="freshOffDelay" type="number" min="0" step="1" value="${escapeHtml(roomConfig.automation.fresh_air.off_delay_sec)}">
                    </div>
                  </div>
                  <div class="field">
                    <label>默认档位</label>
                    <select id="freshMode">${selectedFreshModes(roomConfig.entities.fresh_air, roomConfig.automation.fresh_air.fan_mode)}</select>
                  </div>
                </div>
              </section>
            </div>
          ` : renderEmptyState("请选择房间", "新风控制需要先选中一个已映射配置的包厢。")}
        </section>

        <section class="settings-subpage ${state.currentSettingsSubPage === "sub" ? "active" : ""}" data-settings-page="sub">
          ${hasRoomConfig ? `
            ${renderSettingsPageHead("副中控")}
            ${renderSharedLinkagePanel(roomConfig, sensorItems, trackerItems)}
            <div class="card settings-block">
              <div class="editor-stack">
                <label class="toggle-row"><span>启用分机控制</span><input type="checkbox" id="subEnabled" ${roomConfig.subcontrol.enabled ? "checked" : ""}></label>
                <div class="inline-fields">
                  <label class="toggle-row"><span>允许空调开关</span><input type="checkbox" id="subAllowAcPower" ${roomConfig.subcontrol.allow_ac_power ? "checked" : ""}></label>
                  <label class="toggle-row"><span>允许调温</span><input type="checkbox" id="subAllowAcTemperature" ${roomConfig.subcontrol.allow_ac_temperature ? "checked" : ""}></label>
                </div>
                <div class="inline-fields">
                  <label class="toggle-row"><span>允许模式切换</span><input type="checkbox" id="subAllowAcMode" ${roomConfig.subcontrol.allow_ac_mode ? "checked" : ""}></label>
                  <label class="toggle-row"><span>允许风速切换</span><input type="checkbox" id="subAllowAcFanMode" ${roomConfig.subcontrol.allow_ac_fan_mode ? "checked" : ""}></label>
                </div>
                <div class="inline-fields">
                  <label class="toggle-row"><span>允许灯光控制</span><input type="checkbox" id="subAllowLightControl" ${roomConfig.subcontrol.allow_light_control ? "checked" : ""}></label>
                  <label class="toggle-row"><span>强制季节模式</span><input type="checkbox" id="subEnforceSeason" ${roomConfig.subcontrol.enforce_selected_season ? "checked" : ""}></label>
                </div>
                <label class="toggle-row"><span>继承温度上下限</span><input type="checkbox" id="subInheritTemperatureLimits" ${roomConfig.subcontrol.inherit_temperature_limits ? "checked" : ""}></label>
                <label class="toggle-row"><span>自定义分包温度限制</span><input type="checkbox" id="subCustomTemperatureLimitsEnabled" ${roomConfig.subcontrol.custom_temperature_limits_enabled ? "checked" : ""}></label>
                <div class="inline-fields">
                  <div class="field">
                    <label>分包最低温度</label>
                    <input id="subMinTemperature" type="number" min="16" max="32" step="1" value="${escapeHtml(roomConfig.subcontrol.min_temperature)}">
                  </div>
                  <div class="field">
                    <label>分包最高温度</label>
                    <input id="subMaxTemperature" type="number" min="16" max="32" step="1" value="${escapeHtml(roomConfig.subcontrol.max_temperature)}">
                  </div>
                </div>
                <div class="helper">分机通过专用接口读取这些策略。禁用后会在分机端置灰并显示原因，实际控制也会被后端拒绝。</div>
              </div>
            </div>
          ` : renderEmptyState("请选择房间", "副中控权限需要先选中一个已映射配置的包厢。")}
        </section>

        <section class="settings-subpage ${state.currentSettingsSubPage === "account" ? "active" : ""}" data-settings-page="account">
          ${renderSettingsPageHead("账户管理", "", `
            <div class="button-row">
              <button class="btn btn-secondary" type="button" onclick="testConnection()">测试连接</button>
            </div>
          `)}
          <div class="settings-system-grid">
            <section class="editor-section">
              <h4>连接状态</h4>
              <div class="info-list">
                <div class="info-item"><span>访问模式</span><strong>${connectionText}</strong></div>
                <div class="info-item"><span>当前地址</span><strong class="mono">${escapeHtml(state.connection.apiBase || "--")}</strong></div>
                <div class="info-item"><span>最近刷新</span><strong>${escapeHtml(refreshText)}</strong></div>
                <div class="info-item"><span>错误状态</span><strong>${escapeHtml(state.authError || state.reloadError || "--")}</strong></div>
              </div>
            </section>
            <section class="editor-section">
              <h4>卡密状态</h4>
              <div class="editor-stack">
                <div class="info-list">
                  <div class="info-item"><span>当前状态</span><strong>${escapeHtml(license ? (license.message || (license.is_valid ? "卡密有效" : "卡密受限")) : "未读取")}</strong></div>
                  <div class="info-item"><span>设备标识</span><strong class="mono">${escapeHtml(license && license.device_id ? license.device_id : "--")}</strong></div>
                  <div class="info-item"><span>到期时间</span><strong>${escapeHtml(license && license.expires_at ? formatDateTime(license.expires_at) : "--")}</strong></div>
                </div>
                <div class="field">
                  <label>卡密</label>
                  <input id="licenseKeyInput" type="text" placeholder="输入卡密">
                </div>
                <div class="field">
                  <label>设备 ID</label>
                  <input id="licenseDeviceInput" type="text" placeholder="可选，不填则由后端判定">
                </div>
                <div class="button-row">
                  <button class="btn btn-primary" type="button" onclick="activateLicense()">激活卡密</button>
                </div>
              </div>
            </section>
          </div>
          ${state.authError ? renderHelperNote("当前为只读模式。可以继续查看连接和卡密状态，但修改房间配置前需要先登录当前智慧网吧中心。", "stack-gap") : ""}
        </section>

        <section class="settings-subpage ${state.currentSettingsSubPage === "theme" ? "active" : ""}" data-settings-page="theme">
          ${renderSettingsPageHead("客户端主题")}
          <div class="theme-cards">
            <button class="theme-card ${state.currentTheme === "light" ? "active" : ""}" type="button" onclick="selectClientTheme('light')">
              <div class="theme-icon">☀</div>
              <div class="theme-name">浅色</div>
            </button>
            <button class="theme-card ${state.currentTheme === "dark" ? "active" : ""}" type="button" onclick="selectClientTheme('dark')">
              <div class="theme-icon">🌙</div>
              <div class="theme-name">深色</div>
            </button>
            <button class="theme-card ${state.currentTheme === "tech" ? "active" : ""}" type="button" onclick="selectClientTheme('tech')">
              <div class="theme-icon">🚀</div>
              <div class="theme-name">科技</div>
            </button>
            <button class="theme-card ${state.currentTheme === "apple" ? "active" : ""}" type="button" onclick="selectClientTheme('apple')">
              <div class="theme-icon"></div>
              <div class="theme-name">苹果</div>
            </button>
          </div>
        </section>

        <section class="settings-subpage ${state.currentSettingsSubPage === "about" ? "active" : ""}" data-settings-page="about">
          ${renderSettingsPageHead("关于")}
          <div class="settings-system-grid">
            <section class="editor-section">
              <h4>系统信息</h4>
              <div class="info-list">
                <div class="info-item"><span>系统名称</span><strong>智能家居控制台</strong></div>
                <div class="info-item"><span>当前连接</span><strong>${connectionText}</strong></div>
                <div class="info-item"><span>当前主题</span><strong>${escapeHtml(state.currentTheme)}</strong></div>
                <div class="info-item"><span>上次刷新</span><strong>${escapeHtml(refreshText)}</strong></div>
              </div>
            </section>
            <section class="editor-section">
              <h4>运行摘要</h4>
              <div class="info-list">
                <div class="info-item"><span>当前同步方式</span><strong>${escapeHtml(state.syncMode)}</strong></div>
                <div class="info-item"><span>已加载房间</span><strong>${roomItems.length}</strong></div>
                <div class="info-item"><span>实体总数</span><strong>${totalEntities}</strong></div>
                <div class="info-item"><span>卡密状态</span><strong>${escapeHtml(license ? (license.message || "已读取") : "未读取")}</strong></div>
              </div>
            </section>
          </div>
        </section>

        ${hasRoomConfig ? `
          <div class="button-row end stack-gap">
            <button class="btn btn-secondary" type="button" onclick="reloadAll(true)">重新读取</button>
            <button class="btn btn-primary" type="button" onclick="saveCurrentRoom()" ${canEdit ? "" : "disabled"}>保存当前包厢</button>
          </div>
        ` : ""}
      </div>
    </div>
  `;
}

function roomsOptions(items, selectedRoomId) {
  if (!items.length) {
    return '<option value="">当前没有房间</option>';
  }
  return items.map((item) => `
    <option value="${escapeHtml(item.room_id)}" ${item.room_id === selectedRoomId ? "selected" : ""}>
      ${escapeHtml(item.display_name || item.room_name)} · ${escapeHtml(item.entry_title)}
    </option>
  `).join("");
}

function readCheckedValues(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((item) => item.value);
}

function firstCheckedValue(name, fallback = "") {
  const values = readCheckedValues(name);
  return values.length ? values[0] : String(fallback || "");
}

function numberValue(id, fallback) {
  const input = document.getElementById(id);
  const value = input ? Number(input.value) : Number(fallback);
  return Number.isFinite(value) ? value : Number(fallback);
}

function checkboxValue(id, fallback = false) {
  const input = document.getElementById(id);
  return input ? Boolean(input.checked) : Boolean(fallback);
}

function textValue(id, fallback = "") {
  const input = document.getElementById(id);
  return input ? String(input.value || "") : String(fallback || "");
}

function settingsDraftValue(id, fallback) {
  return Object.prototype.hasOwnProperty.call(state.settingsDraft, id) ? state.settingsDraft[id] : fallback;
}

function rememberSettingDraft(id, value) {
  state.settingsDraft[id] = value;
}

function clearSettingsDraft() {
  state.settingsDraft = {};
}

function draftTextValue(id, fallback = "") {
  return String(settingsDraftValue(id, fallback) || "");
}

function draftCheckboxValue(id, fallback = false) {
  return Boolean(settingsDraftValue(id, fallback));
}

function draftNumberValue(id, fallback = 0) {
  const raw = settingsDraftValue(id, fallback);
  const value = Number(raw);
  const fallbackNumber = Number(fallback);
  return Number.isFinite(value) ? value : (Number.isFinite(fallbackNumber) ? fallbackNumber : 0);
}

function bindSettingsDraftInputs(root = document.getElementById("page-settings")) {
  if (!root) return;
  root.querySelectorAll("input[id], select[id], textarea[id]").forEach((node) => {
    const id = String(node.id || "").trim();
    if (!id) return;
    if (Object.prototype.hasOwnProperty.call(state.settingsDraft, id)) {
      if (node.type === "checkbox") {
        node.checked = Boolean(state.settingsDraft[id]);
      } else {
        node.value = String(state.settingsDraft[id] ?? "");
      }
    }
    const handler = () => {
      rememberSettingDraft(id, node.type === "checkbox" ? Boolean(node.checked) : String(node.value || ""));
    };
    node.addEventListener("input", handler);
    node.addEventListener("change", handler);
  });
}

function isSettingsPageActive() {
  return document.body.getAttribute("data-page") === "settings";
}

function collectUiSettings() {
  const existing = currentUiSettings();
  const next = {
    brand: {
      name: textValue("brandNameInput", existing.brand.name) || existing.brand.name,
      subtitle: textValue("brandSubtitleInput", existing.brand.subtitle) || existing.brand.subtitle,
      logo_url: textValue("brandLogoUrlInput", existing.brand.logo_url) || existing.brand.logo_url,
    },
    theme: {
      selected: textValue("clientThemeSelected", existing.theme.selected),
      auto_by_time: checkboxValue("themeAutoByTime", existing.theme.auto_by_time),
      day_theme: textValue("dayThemeSelected", existing.theme.day_theme),
      night_theme: textValue("nightThemeSelected", existing.theme.night_theme),
      day_start_time: textValue("themeDayStartTime", existing.theme.day_start_time) || existing.theme.day_start_time,
      night_start_time: textValue("themeNightStartTime", existing.theme.night_start_time) || existing.theme.night_start_time,
    },
  };
  return normalizeUiSettings(next);
}

function handleBrandSettingsChange() {
  const nextSettings = collectUiSettings();
  storeUiSettings(nextSettings);
  applyBrandSettings(nextSettings.brand);
  const presetInput = document.getElementById("brandLogoPresetInput");
  if (presetInput) {
    presetInput.value = currentBrandLogoPresetKey(nextSettings.brand.logo_url);
  }
  const presetPicker = document.getElementById("brandLogoPresetPicker");
  if (presetPicker) {
    presetPicker.innerHTML = renderBrandLogoPresetPicker(nextSettings.brand.logo_url);
  }
}

function uploadBrandLogo() {
  const fileInput = document.getElementById("brandLogoFileInput");
  if (fileInput) {
    fileInput.value = "";
    fileInput.click();
  }
}

function selectBrandLogoPreset(url) {
  const urlInput = document.getElementById("brandLogoUrlInput");
  if (!urlInput) return;
  urlInput.value = String(url || "").trim();
  handleBrandSettingsChange();
}

async function handleBrandLogoFileSelected(input) {
  const file = input.files && input.files[0];
  if (!file) return;
  if (!isConnectionConfigured()) {
    showMessage("请从集成入口访问后再上传。", "error");
    return;
  }
  if (file.size > 2 * 1024 * 1024) {
    showMessage("上传失败: 图片不能超过 2 MB。", "error");
    input.value = "";
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  showMessage("正在上传 Logo 图片到智慧网吧目录...", "info");
  try {
    const headers = {};
    if (state.auth && state.auth.token) {
      headers["X-Netcafe-Auth"] = state.auth.token;
    }
    const response = await fetch(buildApiUrl("/api/netcafe/panel/upload/logo"), {
      method: "POST",
      body: formData,
      headers,
      credentials: "same-origin",
    });
    let result = null;
    try {
      result = await response.json();
    } catch (e) {
      if (response.status === 404) {
        throw new Error("上传接口不存在 (HTTP 404)。请重载集成或重启后再试。");
      }
      if (!response.ok) {
        throw new Error("服务器返回了非 JSON 响应 (HTTP " + response.status + ")，可能需要重新登录管理系统。");
      }
      throw new Error("服务器返回了无法解析的响应。");
    }
    if (result && result.success && result.data && result.data.url) {
      const urlInput = document.getElementById("brandLogoUrlInput");
      if (urlInput) {
        urlInput.value = result.data.url;
      }
      handleBrandSettingsChange();
      showMessage("Logo 图片上传成功，已同步到中心服务器存储。", "success", true);
    } else {
      throw new Error((result && result.message) || "上传失败，请重试。");
    }
  } catch (err) {
    showMessage("上传失败: " + (err.message || "网络错误"), "error");
  } finally {
    input.value = "";
  }
}

function applyBrandSettings(brand) {
  const titleEl = document.querySelector(".sidebar-logo-text-title");
  const subEl = document.querySelector(".sidebar-logo-text-sub");
  const iconEl = document.querySelector(".sidebar-logo-icon");
  const logoCandidates = brandLogoCandidates(brand && brand.logo_url);
  if (titleEl) titleEl.textContent = brand.name || "智享空间";
  if (subEl) subEl.textContent = brand.subtitle || "Netcafe";
  if (iconEl) {
    const renderDefaultLogo = () => {
      iconEl.classList.remove("has-custom-logo");
      iconEl.innerHTML = `
        <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="7" y="7" width="50" height="50" rx="18" fill="url(#shellLogoGradient)"/>
          <rect x="16.5" y="18" width="31" height="21" rx="6.5" fill="rgba(255,255,255,.96)"/>
          <rect x="22" y="42" width="20" height="4" rx="2" fill="rgba(255,255,255,.9)"/>
          <defs>
            <linearGradient id="shellLogoGradient" x1="7" y1="7" x2="57" y2="57" gradientUnits="userSpaceOnUse">
              <stop stop-color="#3B82F6"/><stop offset="1" stop-color="#2563EB"/>
            </linearGradient>
          </defs>
        </svg>
      `;
    };

    if (!logoCandidates.length) {
      renderDefaultLogo();
      return;
    }

    const tryLoadLogo = (index = 0) => {
      if (index >= logoCandidates.length) {
        renderDefaultLogo();
        return;
      }
      const image = new Image();
      image.className = "sidebar-logo-image";
      image.alt = "";
      image.decoding = "async";
      image.referrerPolicy = "same-origin";
      image.onload = () => {
        iconEl.classList.add("has-custom-logo");
        iconEl.innerHTML = "";
        iconEl.appendChild(image);
      };
      image.onerror = () => {
        tryLoadLogo(index + 1);
      };
      image.src = logoCandidates[index];
    };

    tryLoadLogo();
  }
}

async function saveDashboardPriceQuick() {
  try {
    const dashboardConfig = currentDashboardConfig();
    const currentEnergy = dashboardConfig && dashboardConfig.energy ? dashboardConfig.energy : {};
    const price = numberValue("dashboardEnergyPriceQuick", currentEnergy.price_per_kwh != null ? currentEnergy.price_per_kwh : 0);
    showMessage("正在保存电价...", "info");
    await requestJson("/api/netcafe/panel/config/system", {
      method: "POST",
      body: JSON.stringify({
        config: {
          dashboard: {
            energy: {
              realtime_power_entity: currentEnergy.realtime_power_entity || "",
              daily_energy_entity: currentEnergy.daily_energy_entity || "",
              monthly_energy_entity: currentEnergy.monthly_energy_entity || "",
              price_per_kwh: price,
            },
          },
        },
      }),
    });
    await reloadAll(false);
    state.dashboardPriceEditorOpen = false;
    showMessage(`电价已更新为 ¥ ${formatMetricNumber(price, 2)}/度`, "success", true);
  } catch (error) {
    showMessage(error.message || "电价保存失败。", "error");
  }
}

function selectSeasonPreset(season) {
  if (!["summer", "winter", "custom"].includes(season)) return;
  const seasonSelect = document.getElementById("selectedSeason");
  if (seasonSelect) {
    seasonSelect.value = season;
  }
  const enabledId = season === "summer" ? "summerEnabled" : season === "winter" ? "winterEnabled" : "customEnabled";
  const enabled = document.getElementById(enabledId);
  if (enabled) {
    enabled.checked = true;
  }
  const label = season === "summer" ? "夏季" : season === "winter" ? "冬季" : "自定义";
  showMessage(`已切换到${label}模式，保存后生效。`, "success", true);
}

function updateGlobalEntityMatchSummaries() {
  const filters = globalEntityFiltersDraft();
  const globalSettings = currentGlobalSettings();
  const draftSettings = normalizeGlobalSettings({
    ...globalSettings,
    entity_filters: filters,
    automation: {
      ...globalSettings.automation,
      ac: {
        ...globalSettings.automation.ac,
        target_include_keywords: parseKeywordList(draftTextValue("automationAcIncludeKeywords", globalSettings.automation.ac.target_include_keywords)),
        target_exclude_keywords: parseKeywordList(draftTextValue("automationAcExcludeKeywords", globalSettings.automation.ac.target_exclude_keywords)),
      },
      light: {
        ...globalSettings.automation.light,
        target_include_keywords: parseKeywordList(draftTextValue("automationLightIncludeKeywords", globalSettings.automation.light.target_include_keywords)),
        target_exclude_keywords: parseKeywordList(draftTextValue("automationLightExcludeKeywords", globalSettings.automation.light.target_exclude_keywords)),
      },
      fresh_air: {
        ...globalSettings.automation.fresh_air,
        target_include_keywords: parseKeywordList(draftTextValue("automationFreshIncludeKeywords", globalSettings.automation.fresh_air.target_include_keywords)),
        target_exclude_keywords: parseKeywordList(draftTextValue("automationFreshExcludeKeywords", globalSettings.automation.fresh_air.target_exclude_keywords)),
      },
    },
  });
  const targets = globalEntityTargets(filters);
  const automationTargets = automationTargetsFromGlobalSettings(draftSettings);
  const detectedAcId = ((automationTargets.ac[0] && automationTargets.ac[0].entity_id) || (targets.ac[0] && targets.ac[0].entity_id) || "");
  const detectedFreshId = ((automationTargets.fresh[0] && automationTargets.fresh[0].entity_id) || (targets.fresh[0] && targets.fresh[0].entity_id) || "");
  const acSummary = document.getElementById("acMatchSummary");
  if (acSummary) {
    acSummary.innerHTML = renderReferenceEntityMatchTrigger(
      "空调识别结果",
      targets.ac,
      "暂未识别到空调。",
      "个空调实体",
      "点击查看当前规则匹配到的全部空调实体。"
    );
  }
  const lightSummary = document.getElementById("lightMatchSummary");
  if (lightSummary) {
    lightSummary.innerHTML = renderReferenceEntityMatchTrigger(
      "灯光识别结果",
      targets.lights,
      "暂未识别到灯光。",
      "盏灯",
      "点击查看当前规则匹配到的全部灯光实体。"
    );
  }
  const freshSummary = document.getElementById("freshMatchSummary");
  if (freshSummary) {
    freshSummary.innerHTML = renderReferenceEntityMatchTrigger(
      "新风识别结果",
      targets.fresh,
      "暂未识别到新风。",
      "个新风实体",
      "点击查看当前规则匹配到的全部新风实体。"
    );
  }
  const automationAcTargets = document.getElementById("automationAcTargets");
  if (automationAcTargets) {
    automationAcTargets.innerHTML = renderReferenceEntityMatchTrigger(
      "空调执行目标",
      automationTargets.ac,
      "暂未识别到空调。",
      "个空调实体",
      "点击查看当前规则会执行到的全部空调实体。"
    );
  }
  const automationLightTargets = document.getElementById("automationLightTargets");
  if (automationLightTargets) {
    automationLightTargets.innerHTML = renderReferenceEntityMatchTrigger(
      "灯光执行目标",
      automationTargets.lights,
      "暂未识别到灯光。",
      "盏灯",
      "点击查看当前规则会执行到的全部灯光实体。"
    );
  }
  const automationFreshTargets = document.getElementById("automationFreshTargets");
  if (automationFreshTargets) {
    automationFreshTargets.innerHTML = renderReferenceEntityMatchTrigger(
      "新风执行目标",
      automationTargets.fresh,
      "暂未识别到新风。",
      "个新风实体",
      "点击查看当前规则会执行到的全部新风实体。"
    );
  }
  const summerHvacMode = document.getElementById("summerHvacMode");
  if (summerHvacMode) {
    const currentValue = summerHvacMode.value || globalSettings.modes.summer.hvac_mode;
    summerHvacMode.innerHTML = selectedAcModes(detectedAcId, currentValue);
  }
  const summerFanMode = document.getElementById("summerFanMode");
  if (summerFanMode) {
    const currentValue = summerFanMode.value || globalSettings.modes.summer.fan_mode;
    summerFanMode.innerHTML = selectedAcFanModes(detectedAcId, currentValue);
  }
  const winterHvacMode = document.getElementById("winterHvacMode");
  if (winterHvacMode) {
    const currentValue = winterHvacMode.value || globalSettings.modes.winter.hvac_mode;
    winterHvacMode.innerHTML = selectedAcModes(detectedAcId, currentValue);
  }
  const winterFanMode = document.getElementById("winterFanMode");
  if (winterFanMode) {
    const currentValue = winterFanMode.value || globalSettings.modes.winter.fan_mode;
    winterFanMode.innerHTML = selectedAcFanModes(detectedAcId, currentValue);
  }
  const customHvacMode = document.getElementById("customHvacMode");
  if (customHvacMode) {
    const currentValue = customHvacMode.value || globalSettings.modes.custom.hvac_mode;
    customHvacMode.innerHTML = selectedAcModes(detectedAcId, currentValue);
  }
  const customFanMode = document.getElementById("customFanMode");
  if (customFanMode) {
    const currentValue = customFanMode.value || globalSettings.modes.custom.fan_mode;
    customFanMode.innerHTML = selectedAcFanModes(detectedAcId, currentValue);
  }
  const freshMode = document.getElementById("freshMode");
  if (freshMode) {
    const currentValue = freshMode.value || globalSettings.automation.fresh_air.fan_mode;
    freshMode.innerHTML = selectedFreshModes(detectedFreshId, currentValue);
  }
}

function collectSystemSettings() {
  const existing = currentGlobalSettings();
  return normalizeGlobalSettings({
    entity_filters: globalEntityFiltersDraft(),
    modes: {
      selected_season: draftTextValue("selectedSeason", existing.modes.selected_season),
      summer: {
        enabled: draftCheckboxValue("summerEnabled", existing.modes.summer.enabled),
        hvac_mode: draftTextValue("summerHvacMode", existing.modes.summer.hvac_mode),
        temperature: draftNumberValue("summerTemp", existing.modes.summer.temperature),
        fan_mode: draftTextValue("summerFanMode", existing.modes.summer.fan_mode),
      },
      winter: {
        enabled: draftCheckboxValue("winterEnabled", existing.modes.winter.enabled),
        hvac_mode: draftTextValue("winterHvacMode", existing.modes.winter.hvac_mode),
        temperature: draftNumberValue("winterTemp", existing.modes.winter.temperature),
        fan_mode: draftTextValue("winterFanMode", existing.modes.winter.fan_mode),
      },
      custom: {
        enabled: draftCheckboxValue("customEnabled", existing.modes.custom.enabled),
        hvac_mode: draftTextValue("customHvacMode", existing.modes.custom.hvac_mode),
        temperature: draftNumberValue("customTemp", existing.modes.custom.temperature),
        fan_mode: draftTextValue("customFanMode", existing.modes.custom.fan_mode),
      },
    },
    automation: {
      ...existing.automation,
      enabled: draftCheckboxValue("automationEnabled", existing.automation.enabled),
      trigger_mode: triggerModeValue(draftTextValue("linkTriggerMode", existing.automation.trigger_mode)),
      offline_confirm_seconds: draftNumberValue("offlineConfirmSeconds", existing.automation.offline_confirm_seconds),
      presence_sensor_entity: "",
      device_tracker_entity: "",
      presence_sensor_include_keywords: parseKeywordList(draftTextValue("presenceSensorIncludeKeywords", existing.automation.presence_sensor_include_keywords)),
      presence_sensor_exclude_keywords: parseKeywordList(draftTextValue("presenceSensorExcludeKeywords", existing.automation.presence_sensor_exclude_keywords)),
      device_tracker_include_keywords: parseKeywordList(draftTextValue("deviceTrackerIncludeKeywords", existing.automation.device_tracker_include_keywords)),
      device_tracker_exclude_keywords: parseKeywordList(draftTextValue("deviceTrackerExcludeKeywords", existing.automation.device_tracker_exclude_keywords)),
      ac: {
        ...existing.automation.ac,
        enabled: draftCheckboxValue("acEnabled", existing.automation.ac.enabled),
        auto_on: draftCheckboxValue("acAutoOn", existing.automation.ac.auto_on),
        auto_off: draftCheckboxValue("acAutoOff", existing.automation.ac.auto_off),
        on_delay_sec: draftNumberValue("acOnDelay", existing.automation.ac.on_delay_sec),
        off_delay_sec: draftNumberValue("acOffDelay", existing.automation.ac.off_delay_sec),
        target_include_keywords: parseKeywordList(draftTextValue("automationAcIncludeKeywords", existing.automation.ac.target_include_keywords)),
        target_exclude_keywords: parseKeywordList(draftTextValue("automationAcExcludeKeywords", existing.automation.ac.target_exclude_keywords)),
        season_strategy: draftTextValue("acSeasonStrategy", existing.automation.ac.season_strategy),
      },
      light: {
        ...existing.automation.light,
        enabled: draftCheckboxValue("lightEnabled", existing.automation.light.enabled),
        auto_on: draftCheckboxValue("lightAutoOn", existing.automation.light.auto_on),
        auto_off: draftCheckboxValue("lightAutoOff", existing.automation.light.auto_off),
        on_delay_sec: draftNumberValue("lightOnDelay", existing.automation.light.on_delay_sec),
        off_delay_sec: draftNumberValue("lightOffDelay", existing.automation.light.off_delay_sec),
        target_include_keywords: parseKeywordList(draftTextValue("automationLightIncludeKeywords", existing.automation.light.target_include_keywords)),
        target_exclude_keywords: parseKeywordList(draftTextValue("automationLightExcludeKeywords", existing.automation.light.target_exclude_keywords)),
        arrival_preset: "full_on",
        departure_preset: "full_off",
      },
      fresh_air: {
        ...existing.automation.fresh_air,
        enabled: draftCheckboxValue("freshEnabled", existing.automation.fresh_air.enabled),
        auto_on: draftCheckboxValue("freshAutoOn", existing.automation.fresh_air.auto_on),
        auto_off: draftCheckboxValue("freshAutoOff", existing.automation.fresh_air.auto_off),
        on_delay_sec: draftNumberValue("freshOnDelay", existing.automation.fresh_air.on_delay_sec),
        off_delay_sec: draftNumberValue("freshOffDelay", existing.automation.fresh_air.off_delay_sec),
        target_include_keywords: parseKeywordList(draftTextValue("automationFreshIncludeKeywords", existing.automation.fresh_air.target_include_keywords)),
        target_exclude_keywords: parseKeywordList(draftTextValue("automationFreshExcludeKeywords", existing.automation.fresh_air.target_exclude_keywords)),
        fan_mode: draftTextValue("freshMode", existing.automation.fresh_air.fan_mode),
      },
    },
    subcontrol_trust: {
      enabled: draftCheckboxValue("subcontrolTrustEnabled", existing.subcontrol_trust && existing.subcontrol_trust.enabled),
      allowed_cidrs: parseKeywordList(draftTextValue("subcontrolAllowedCidrs", existing.subcontrol_trust && existing.subcontrol_trust.allowed_cidrs)),
      trust_proxy_headers: draftCheckboxValue("subcontrolTrustProxyHeaders", existing.subcontrol_trust && existing.subcontrol_trust.trust_proxy_headers),
    },
  });
}

async function saveSystemSettings() {
  try {
    const uiSettings = collectUiSettings();
    const globalSettings = collectSystemSettings();
    storeUiSettings(uiSettings);
    syncConfiguredTheme();
    showMessage("正在保存全局设置...", "info");
    await requestJson("/api/netcafe/panel/config/system", {
      method: "POST",
      body: JSON.stringify({
        config: {
          ui: uiSettings,
          global_settings: globalSettings,
        },
      }),
    });
    clearSettingsDraft();
    showMessage("全局设置已保存。", "success", true);
    await reloadAll(false);
  } catch (error) {
    showMessage(error.message || "全局设置保存失败。", "error");
  }
}

function collectCurrentRoomSubcontrolConfig() {
  const room = getRoom(state.currentRoomId);
  if (!room) return null;
  const existing = normalizeRoomConfig(room, currentRoomConfigSource() || {});
  return {
    ...existing,
    subcontrol: {
      ...existing.subcontrol,
      enabled: checkboxValue("subEnabled", existing.subcontrol.enabled),
      allow_ac_power: checkboxValue("subAllowAcPower", existing.subcontrol.allow_ac_power),
      allow_ac_temperature: checkboxValue("subAllowAcTemperature", existing.subcontrol.allow_ac_temperature),
      allow_ac_mode: checkboxValue("subAllowAcMode", existing.subcontrol.allow_ac_mode),
      allow_ac_fan_mode: checkboxValue("subAllowAcFanMode", existing.subcontrol.allow_ac_fan_mode),
      allow_light_control: checkboxValue("subAllowLightControl", existing.subcontrol.allow_light_control),
      enforce_selected_season: checkboxValue("subEnforceSeason", existing.subcontrol.enforce_selected_season),
      inherit_temperature_limits: checkboxValue("subInheritTemperatureLimits", existing.subcontrol.inherit_temperature_limits),
      custom_temperature_limits_enabled: checkboxValue("subCustomTemperatureLimitsEnabled", existing.subcontrol.custom_temperature_limits_enabled),
      min_temperature: numberValue("subMinTemperature", existing.subcontrol.min_temperature),
      max_temperature: numberValue("subMaxTemperature", existing.subcontrol.max_temperature),
    },
  };
}

async function saveCurrentRoomSubcontrol() {
  try {
    const roomConfig = collectCurrentRoomSubcontrolConfig();
    if (!roomConfig) throw new Error("当前没有可保存的房间配置。");
    showMessage("正在保存副中控配置...", "info");
    await requestJson("/api/netcafe/panel/config/system", {
      method: "POST",
      body: JSON.stringify({
        config: {
          rooms: {
            [roomConfig.room_id]: roomConfig,
          },
        },
      }),
    });
    clearSettingsDraft();
    showMessage("副中控配置已保存。", "success", true);
    await reloadAll(false);
  } catch (error) {
    showMessage(error.message || "副中控配置保存失败。", "error");
  }
}

function collectCurrentRoomConfig() {
  const room = getRoom(state.currentRoomId);
  if (!room) return null;
  const existing = normalizeRoomConfig(room, currentRoomConfig());
  const entityFilters = existing.entity_filters || {};
  const nextFilters = {
    ac_include_keywords: parseKeywordList(textValue("acIncludeKeywords", entityFilters.ac_include_keywords)),
    ac_exclude_keywords: parseKeywordList(textValue("acExcludeKeywords", entityFilters.ac_exclude_keywords)),
    light_include_keywords: parseKeywordList(textValue("lightIncludeKeywords", entityFilters.light_include_keywords)),
    light_exclude_keywords: parseKeywordList(textValue("lightExcludeKeywords", entityFilters.light_exclude_keywords)),
    fresh_air_include_keywords: parseKeywordList(textValue("freshIncludeKeywords", entityFilters.fresh_air_include_keywords)),
    fresh_air_exclude_keywords: parseKeywordList(textValue("freshExcludeKeywords", entityFilters.fresh_air_exclude_keywords)),
  };
  const detectedTargets = autoDetectedRoomTargets(room, {
    ...existing,
    entity_filters: nextFilters,
  });
  const selectedLights = detectedTargets.lights.map((item) => item.entity_id);
  const fullOnLights = selectedLights;
  const fullOffLights = selectedLights;
  const preservedHalfOn = Array.isArray(existing.lighting_presets && existing.lighting_presets.half_on)
    ? existing.lighting_presets.half_on.filter((entityId) => selectedLights.includes(entityId))
    : [];
  const acAutoOn = checkboxValue("acAutoOn", existing.automation.ac.auto_on);
  const acAutoOff = checkboxValue("acAutoOff", existing.automation.ac.auto_off);
  const freshAutoOn = checkboxValue("freshAutoOn", existing.automation.fresh_air.auto_on);
  const freshAutoOff = checkboxValue("freshAutoOff", existing.automation.fresh_air.auto_off);
  const deviceTrackerIncludeKeywords = parseKeywordList(textValue("deviceTrackerIncludeKeywords", existing.automation.device_tracker_include_keywords));
  const deviceTrackerExcludeKeywords = parseKeywordList(textValue("deviceTrackerExcludeKeywords", existing.automation.device_tracker_exclude_keywords));
  const presenceSensorIncludeKeywords = parseKeywordList(textValue("presenceSensorIncludeKeywords", existing.automation.presence_sensor_include_keywords));
  const presenceSensorExcludeKeywords = parseKeywordList(textValue("presenceSensorExcludeKeywords", existing.automation.presence_sensor_exclude_keywords));
  return {
    room_id: room.room_id,
    room_name: room.room_name,
    entities: {
      ac: (detectedTargets.ac[0] && detectedTargets.ac[0].entity_id) || "",
      lights: selectedLights,
      fresh_air: (detectedTargets.fresh[0] && detectedTargets.fresh[0].entity_id) || "",
    },
    lighting_presets: {
      full_on: fullOnLights,
      half_on: preservedHalfOn,
      full_off: fullOffLights,
    },
    lighting_filters: {
      entity_keywords: [],
      half_on_keywords: [],
    },
    entity_filters: nextFilters,
    subcontrol: {
      enabled: checkboxValue("subEnabled", existing.subcontrol.enabled),
      allow_ac_power: checkboxValue("subAllowAcPower", existing.subcontrol.allow_ac_power),
      allow_ac_temperature: checkboxValue("subAllowAcTemperature", existing.subcontrol.allow_ac_temperature),
      allow_ac_mode: checkboxValue("subAllowAcMode", existing.subcontrol.allow_ac_mode),
      allow_ac_fan_mode: checkboxValue("subAllowAcFanMode", existing.subcontrol.allow_ac_fan_mode),
      allow_light_control: checkboxValue("subAllowLightControl", existing.subcontrol.allow_light_control),
      enforce_selected_season: checkboxValue("subEnforceSeason", existing.subcontrol.enforce_selected_season),
      inherit_temperature_limits: checkboxValue("subInheritTemperatureLimits", existing.subcontrol.inherit_temperature_limits),
      custom_temperature_limits_enabled: checkboxValue("subCustomTemperatureLimitsEnabled", existing.subcontrol.custom_temperature_limits_enabled),
      min_temperature: numberValue("subMinTemperature", existing.subcontrol.min_temperature),
      max_temperature: numberValue("subMaxTemperature", existing.subcontrol.max_temperature),
    },
    modes: {
      selected_season: textValue("selectedSeason", existing.modes.selected_season),
      summer: {
        enabled: checkboxValue("summerEnabled", existing.modes.summer.enabled),
        hvac_mode: textValue("summerHvacMode", existing.modes.summer.hvac_mode),
        temperature: numberValue("summerTemp", existing.modes.summer.temperature),
        fan_mode: textValue("summerFanMode", existing.modes.summer.fan_mode),
      },
      winter: {
        enabled: checkboxValue("winterEnabled", existing.modes.winter.enabled),
        hvac_mode: textValue("winterHvacMode", existing.modes.winter.hvac_mode),
        temperature: numberValue("winterTemp", existing.modes.winter.temperature),
        fan_mode: textValue("winterFanMode", existing.modes.winter.fan_mode),
      },
    },
    automation: {
      enabled: checkboxValue("automationEnabled", existing.automation.enabled),
      logging_enabled: existing.automation.logging_enabled,
      trigger_mode: triggerModeValue(textValue("linkTriggerMode", existing.automation.trigger_mode)),
      presence_sensor_entity: "",
      device_tracker_entity: "",
      presence_sensor_include_keywords: presenceSensorIncludeKeywords,
      presence_sensor_exclude_keywords: presenceSensorExcludeKeywords,
      device_tracker_include_keywords: deviceTrackerIncludeKeywords,
      device_tracker_exclude_keywords: deviceTrackerExcludeKeywords,
      schedule: existing.automation.schedule,
      ac: {
        enabled: checkboxValue("acEnabled", existing.automation.ac.enabled),
        auto_on: acAutoOn,
        auto_off: acAutoOff,
        on_delay_sec: numberValue("acOnDelay", existing.automation.ac.on_delay_sec),
        off_delay_sec: numberValue("acOffDelay", existing.automation.ac.off_delay_sec),
        manual_override: existing.automation.ac.manual_override,
        restore_delay_sec: existing.automation.ac.restore_delay_sec,
        season_strategy: textValue("acSeasonStrategy", existing.automation.ac.season_strategy),
        temperature_limits_enabled: checkboxValue("acTemperatureLimitsEnabled", existing.automation.ac.temperature_limits_enabled),
        min_temperature: numberValue("acMinTemperature", existing.automation.ac.min_temperature),
        max_temperature: numberValue("acMaxTemperature", existing.automation.ac.max_temperature),
      },
      light: {
        enabled: checkboxValue("lightEnabled", existing.automation.light.enabled),
        auto_on: checkboxValue("lightAutoOn", existing.automation.light.auto_on),
        auto_off: checkboxValue("lightAutoOff", existing.automation.light.auto_off),
        on_delay_sec: numberValue("lightOnDelay", existing.automation.light.on_delay_sec),
        off_delay_sec: numberValue("lightOffDelay", existing.automation.light.off_delay_sec),
        arrival_preset: "full_on",
        departure_preset: "full_off",
      },
      fresh_air: {
        enabled: checkboxValue("freshEnabled", existing.automation.fresh_air.enabled),
        auto_on: freshAutoOn,
        auto_off: freshAutoOff,
        on_delay_sec: numberValue("freshOnDelay", existing.automation.fresh_air.on_delay_sec),
        off_delay_sec: numberValue("freshOffDelay", existing.automation.fresh_air.off_delay_sec),
        fan_mode: textValue("freshMode", existing.automation.fresh_air.fan_mode),
      },
    },
  };
}

async function saveCurrentRoom() {
  try {
    const uiSettings = collectUiSettings();
    const roomConfig = collectCurrentRoomConfig();
    const payload = { ui: uiSettings };
    if (roomConfig) {
      payload.rooms = { [roomConfig.room_id]: roomConfig };
    }
    if (!payload.ui && !payload.rooms) throw new Error("当前没有可保存的配置。");
    storeUiSettings(uiSettings);
    syncConfiguredTheme();
    showMessage("正在保存系统设置...", "info");
    await requestJson("/api/netcafe/panel/config/system", {
      method: "POST",
      body: JSON.stringify({ config: payload }),
    });
    clearSettingsDraft();
    showMessage("系统设置已保存。", "success", true);
    await reloadAll(false);
  } catch (error) {
    showMessage(error.message || "保存失败。", "error");
  }
}

async function selectRoom(roomId) {
  state.currentRoomId = roomId;
  renderSettingsPage();
}

function switchSettingsSubPage(page, element) {
  if (isRoomSettingsPage(page) && !getRoom(state.currentRoomId)) {
    state.currentSettingsSubPage = "basic";
    renderSettingsPage();
    showMessage("当前没有可编辑的房间，已切换到基础设置页。", "warning", true);
    return;
  }
  state.currentSettingsSubPage = page;
  renderSettingsPage();
}

async function performRoomAction(roomId, action, value, persist = false) {
  const lockKey = roomActionLockKey(roomId, action, value);
  if (state.pendingRoomActionKeys.has(lockKey)) {
    return;
  }
  state.pendingRoomActionKeys.add(lockKey);
  const clientStartedAtMs = Date.now();
  const snapshot = applyOptimisticRoomAction(roomId, action, value);
  try {
    const room = getRoom(roomId);
    showMessage(`正在执行：${displayRoomName(room)} · ${describeAction(action, value)}...`, "info");
    if (snapshot) {
      renderOptimisticRoomState();
    }
    const response = await requestJson("/api/netcafe/panel/room/action", {
      method: "POST",
      body: JSON.stringify({
        room_id: roomId,
        action,
        value,
        persist: Boolean(persist),
      }),
    });
    const responseAtMs = Date.now();
    const backendTrace = response && response.trace ? response.trace : null;
    appendRealtimeActionTrace({
      trace_id: backendTrace && backendTrace.trace_id ? backendTrace.trace_id : `client-${clientStartedAtMs}-${roomId}-${action}`,
      room_id: roomId,
      room_name: displayRoomName(room),
      action,
      value,
      client_started_at_ms: clientStartedAtMs,
      client_response_at_ms: responseAtMs,
      client_api_duration_ms: safeDurationMs(responseAtMs - clientStartedAtMs),
      backend_trace: backendTrace,
      entity_ids: backendTrace && Array.isArray(backendTrace.entity_ids) ? backendTrace.entity_ids : [],
      expected_state: normalizeActionExpectedState(action, value),
      first_ws_at_ms: null,
      fulfilled_at_ms: null,
      fulfilled_entity_id: "",
      fulfilled_state: "",
    });
    const detail = response && response.data && response.data.message ? response.data.message : describeAction(action, value);
    showMessage(`${displayRoomName(room)} · ${detail}`, "success", true);
    scheduleActionReload();
  } catch (error) {
    if (snapshot) {
      replaceRoomSnapshot(roomId, snapshot);
      renderOptimisticRoomState();
    }
    showMessage(error.message || "执行失败。", "error");
  } finally {
    state.pendingRoomActionKeys.delete(lockKey);
  }
}

async function batchRoomAction(target, action, value, persist = false, quiet = false) {
  const rooms = roomsForDisplay().filter((room) => {
    const inventory = getMappedRoomDevices(room);
    if (target === "ac") return Boolean(inventory.ac);
    if (target === "light") return inventory.lights.length > 0;
    if (target === "fresh_air") return Boolean(inventory.freshAir);
    return false;
  });
  if (!rooms.length) {
    if (!quiet) showMessage("没有可执行批量动作的目标房间。", "warning", true);
    return;
  }
  const snapshots = new Map();
  try {
    if (!quiet) showMessage("正在批量执行 " + action + "...", "info");
    rooms.forEach((room) => {
      const snapshot = applyOptimisticRoomAction(room.room_id, action, value);
      if (snapshot) {
        snapshots.set(room.room_id, snapshot);
      }
    });
    if (snapshots.size) {
      renderOptimisticRoomState();
    }
    await Promise.all(rooms.map((room) => requestJson("/api/netcafe/panel/room/action", {
        method: "POST",
        body: JSON.stringify({
          room_id: room.room_id,
          action,
          value,
          persist: Boolean(persist),
        }),
      })));
    if (!quiet) showMessage(`批量执行完成 · ${describeAction(action, value)}`, "success", true);
    scheduleActionReload();
  } catch (error) {
    rooms.forEach((room) => {
      const snapshot = snapshots.get(room.room_id);
      if (snapshot) {
        replaceRoomSnapshot(room.room_id, snapshot);
      }
    });
    if (snapshots.size) {
      renderOptimisticRoomState();
    }
    if (!quiet) showMessage(error.message || "批量执行失败。", "error");
    throw error;
  }
}

async function shiftAcTemperature(roomId, delta) {
  const room = getRoom(roomId);
  const ac = room && room.mapped ? room.mapped.ac : null;
  if (!ac || ac.domain !== "climate") {
    showMessage("当前房间未绑定可调温的 climate 空调。", "warning", true);
    return;
  }
  const current = safeNumber(ac.temperature ?? ac.current_temperature, 26);
  const target = Math.max(16, Math.min(32, current + delta));
  await performRoomAction(roomId, "ac_set_temperature", target);
}

async function setAcHvacMode(roomId, value) {
  if (!value) return;
  await performRoomAction(roomId, "ac_set_hvac_mode", value);
}

async function setAcFanMode(roomId, fanMode) {
  if (!roomId || !fanMode) return;
  await performRoomAction(roomId, "ac_set_fan_mode", fanMode);
}

async function setFreshAirPercentage(roomId, percentage) {
  if (!roomId) return;
  await performRoomAction(roomId, "fresh_air_set_percentage", Number(percentage));
}

async function setLightBrightness(roomId, entityId, value) {
  if (!roomId || !entityId) return;
  await performRoomAction(roomId, "light_set_brightness", {
    entity_id: entityId,
    brightness_pct: Number(value),
  });
}

async function setLightColorTemperature(roomId, entityId, kelvin) {
  if (!roomId || !entityId || !kelvin) return;
  await performRoomAction(roomId, "light_set_color_temperature", {
    entity_id: entityId,
    kelvin: Number(kelvin),
  });
}

async function setLightColor(roomId, entityId, hex) {
  const rgb = hexToRgbTriplet(hex);
  if (!roomId || !entityId || !rgb) return;
  await performRoomAction(roomId, "light_set_color", {
    entity_id: entityId,
    hex: normalizeHexColor(hex),
    rgb_color: rgb,
  });
}

async function testConnection() {
  try {
    showMessage("正在测试连接...", "info");
    const result = await requestJson("/api/netcafe/panel/license/status");
    state.license = result;
    updateLicenseBadge();
    showLicenseBanner();
    showMessage("连接测试成功。", "success", true);
  } catch (error) {
    showMessage(error.message || "连接测试失败。", "error");
  }
}

async function updateWeather() {
  const city = state.config?.data?.settings?.city || state.config?.settings?.city || "佛山";
  try {
    const response = await requestJson(`/api/netcafe/weather?city=${encodeURIComponent(city)}`);
    const weatherData = response && typeof response === "object" && response.data && typeof response.data === "object"
      ? response.data
      : response;
    if (weatherData && weatherData.temperature != null) {
      state.weather = {
        ...weatherData,
        text: weatherData.text || weatherData.weather || "",
      };
      state.weatherConfig = {
        domain: weatherData.domain || state.weatherConfig?.domain || "weather.com.cn",
        area_id: weatherData.area_id || "",
        area_name: weatherData.location_name || "",
        area_code: weatherData.area_code || "",
        configured: Boolean(weatherData.configured),
      };
      return;
    }
    state.weather = null;
  } catch (err) {
    state.weather = null;
    console.warn("Weather fetch failed:", err);
  }
}

async function loadWeatherConfig() {
  try {
    const response = await requestJson("/api/netcafe/panel/weather/config");
    const config = response && response.data ? response.data : null;
    if (config) {
      state.weatherConfig = config;
      if (!Array.isArray(state.weatherSearchResults) || !state.weatherSearchResults.length) {
        state.weatherSearchResults = config.area_id && config.area_name
          ? [{ area_id: config.area_id, label: config.area_name }]
          : [];
      }
    }
  } catch (error) {
    console.warn("Weather config fetch failed:", error);
  }
}

async function searchWeatherLocations() {
  try {
    const keyword = textValue("weatherSearchKeywordInput", "").trim();
    const domain = textValue("weatherDomainInput", state.weatherConfig?.domain || "weather.com.cn").trim() || "weather.com.cn";
    rememberSettingDraft("weatherSearchKeyword", keyword);
    if (!keyword) {
      throw new Error("请输入城市或区县名称。");
    }
    showMessage("正在搜索天气地区...", "info");
    const response = await requestJson("/api/netcafe/panel/weather/search", {
      method: "POST",
      body: JSON.stringify({
        keyword,
        weather_domain: domain,
      }),
    });
    const items = response && response.data && Array.isArray(response.data.items) ? response.data.items : [];
    state.weatherSearchResults = items;
    if (items.length) {
      rememberSettingDraft("weatherAreaId", items[0].area_id);
      showMessage(`已找到 ${items.length} 个候选地区。`, "success", true);
    } else {
      rememberSettingDraft("weatherAreaId", "");
      showMessage("没有找到匹配的天气地区。", "warning");
    }
    renderSettingsPage();
  } catch (error) {
    showMessage(error.message || "搜索天气地区失败。", "error");
  }
}

async function saveWeatherSettings() {
  try {
    const domain = textValue("weatherDomainInput", state.weatherConfig?.domain || "weather.com.cn").trim() || "weather.com.cn";
    const areaId = textValue("weatherAreaIdSelect", draftTextValue("weatherAreaId", state.weatherConfig?.area_id || "")).trim();
    rememberSettingDraft("weatherAreaId", areaId);
    if (!areaId) {
      throw new Error("请先搜索并选择天气地区。");
    }
    showMessage("正在保存天气地区...", "info");
    const response = await requestJson("/api/netcafe/panel/weather/config", {
      method: "POST",
      body: JSON.stringify({
        area_id: areaId,
        weather_domain: domain,
      }),
    });
    state.weatherConfig = response && response.data ? response.data : state.weatherConfig;
    if (state.weatherConfig && state.weatherConfig.area_id && state.weatherConfig.area_name) {
      state.weatherSearchResults = [
        {
          area_id: state.weatherConfig.area_id,
          label: state.weatherConfig.area_name,
        },
      ];
    }
    await updateWeather();
    renderAll();
    showMessage("天气地区已保存并生效。", "success", true);
  } catch (error) {
    showMessage(error.message || "保存天气地区失败。", "error");
  }
}

async function loadNotificationStatus() {
  try {
    const response = await requestJson("/api/netcafe/panel/notifications/status");
    state.notificationStatus = response && response.data ? response.data : {};
  } catch (error) {
    console.warn("Notification status fetch failed:", error);
  }
}

async function loadNotificationPreview() {
  try {
    const response = await requestJson("/api/netcafe/panel/notifications/preview");
    state.notificationPreview = response && response.data ? response.data : {};
  } catch (error) {
    console.warn("Notification preview fetch failed:", error);
  }
}

function stopNotificationQrPolling() {
  window.clearTimeout(state.notificationQrPollTimer);
  state.notificationQrPollTimer = null;
}

function scheduleNotificationQrPolling(delay = 4000) {
  stopNotificationQrPolling();
  state.notificationQrPollTimer = window.setTimeout(() => {
    pollNotificationQrStatus();
  }, Math.max(1000, Number(delay) || 4000));
}

function syncNotificationQrPolling(status = currentNotificationQrStatus()) {
  const qrState = String(status.state || "").trim().toLowerCase();
  if (qrState === "pending_scan" || qrState === "form") {
    scheduleNotificationQrPolling(4000);
    return;
  }
  stopNotificationQrPolling();
}

async function loadNotificationQrStatus() {
  try {
    const response = await requestJson("/api/netcafe/panel/notifications/wechat/qr");
    state.notificationQr = response && response.data ? response.data : {};
    syncNotificationQrPolling(state.notificationQr);
  } catch (error) {
    console.warn("Notification qr fetch failed:", error);
  }
}

async function startNotificationQrSync() {
  try {
    showMessage("正在同步 cn_im_hub 微信二维码...", "info");
    const response = await requestJson("/api/netcafe/panel/notifications/wechat/qr", {
      method: "POST",
      body: JSON.stringify({ action: "start" }),
    });
    state.notificationQr = response && response.data ? response.data : {};
    syncNotificationQrPolling(state.notificationQr);
    renderSettingsPage();
    showMessage(
      (response && response.message) || "二维码已同步。",
      response && response.success ? "success" : "warning",
      true
    );
  } catch (error) {
    await loadNotificationQrStatus();
    renderSettingsPage();
    showMessage(error.message || "同步微信二维码失败。", "error");
  }
}

async function pollNotificationQrStatus() {
  try {
    const response = await requestJson("/api/netcafe/panel/notifications/wechat/qr", {
      method: "POST",
      body: JSON.stringify({ action: "poll" }),
    });
    state.notificationQr = response && response.data ? response.data : {};
    syncNotificationQrPolling(state.notificationQr);
    if (String(state.notificationQr.state || "").trim().toLowerCase() === "connected") {
      await loadNotificationStatus();
      renderSettingsPage();
      showMessage(state.notificationQr.message || "微信账号已连接。", "success", true);
      return;
    }
    if (response && response.success === false) {
      showMessage((response && response.message) || "微信二维码状态待确认。", "warning");
    }
    renderSettingsPage();
  } catch (error) {
    stopNotificationQrPolling();
    await loadNotificationQrStatus();
    renderSettingsPage();
    console.warn("Notification qr poll failed:", error);
  }
}

async function refreshNotificationStatus() {
  try {
    showMessage("正在刷新微信通道状态...", "info");
    await Promise.all([loadNotificationStatus(), loadNotificationQrStatus(), loadNotificationPreview()]);
    renderSettingsPage();
    showMessage("微信通道状态已刷新。", "success", true);
  } catch (error) {
    showMessage(error.message || "刷新微信通道状态失败。", "error");
  }
}

function collectNotificationSettings() {
  const current = currentNotificationConfig().wechat;
  return {
    wechat: {
      enabled: checkboxValue("notifyEnabled", current.enabled),
      channel_provider: "cn_im_hub_wechat",
      channel: textValue("notifyChannel", current.channel || "wechat/user_id").trim() || "wechat/user_id",
      target: textValue("notifyTarget", current.target).trim(),
      wechat_account_id: textValue("notifyWechatAccountId", current.wechat_account_id).trim(),
      alert_scope: "offline_and_errors",
      daily_brief_enabled: checkboxValue("notifyDailyBriefEnabled", current.daily_brief_enabled),
      daily_brief_time: normalizeTimeText(textValue("notifyDailyBriefTime", current.daily_brief_time || "23:00"), "23:00"),
      offline_cooldown_minutes: Math.max(0, numberValue("notifyOfflineCooldown", current.offline_cooldown_minutes ?? 30)),
    },
  };
}

async function saveNotificationSettings() {
  try {
    const payload = collectNotificationSettings();
    showMessage("正在保存微信通知设置...", "info");
    const response = await requestJson("/api/netcafe/panel/notifications/config", {
      method: "POST",
      body: JSON.stringify({ config: payload }),
    });
    state.notificationConfig = response && response.data ? response.data : payload;
    clearSettingsDraft();
    await Promise.all([loadNotificationStatus(), loadNotificationQrStatus(), loadNotificationPreview()]);
    renderSettingsPage();
    showMessage("微信通知设置已保存。", "success", true);
  } catch (error) {
    showMessage(error.message || "保存微信通知设置失败。", "error");
  }
}

async function testNotificationSend() {
  try {
    showMessage("正在发送今日运行摘要...", "info");
    const response = await requestJson("/api/netcafe/panel/notifications/test", {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (response && response.data) {
      state.notificationStatus = {
        ...(state.notificationStatus || {}),
        last_send_status: response.success ? "success" : "failed",
        last_send_at: response.data.sent_at || state.notificationStatus?.last_send_at || "",
        last_send_error: response.data.message || response.data.detail || response.message || "",
      };
    }
    renderSettingsPage();
    showMessage(
      (response && response.message) || "今日运行摘要已发送。",
      response && response.success ? "success" : "warning",
      true
    );
  } catch (error) {
    await Promise.all([loadNotificationStatus(), loadNotificationQrStatus(), loadNotificationPreview()]);
    renderSettingsPage();
    showMessage(error.message || "测试消息发送失败。", "error");
  }
}

async function loadPublicData() {
  if (!isConnectionConfigured()) return;
  const [overview, license] = await Promise.all([
    requestJson("/api/netcafe/panel/overview"),
    requestJson("/api/netcafe/panel/license/status").catch(() => null),
  ]);
  state.overview = overview;
  if (license) state.license = license;
}

async function loadProtectedData() {
  if (!isConnectionConfigured()) return;
  try {
    const [config, entities, weatherConfig, notificationConfig, notificationStatus, notificationPreview, notificationQr] = await Promise.all([
      requestJson("/api/netcafe/panel/config/system"),
      requestJson("/api/netcafe/panel/entities"),
      requestJson("/api/netcafe/panel/weather/config").catch(() => null),
      requestJson("/api/netcafe/panel/notifications/config").catch(() => null),
      requestJson("/api/netcafe/panel/notifications/status").catch(() => null),
      requestJson("/api/netcafe/panel/notifications/preview").catch(() => null),
      requestJson("/api/netcafe/panel/notifications/wechat/qr").catch(() => null),
    ]);
    state.config = config;
    state.entities = entities;
    state.weatherConfig = weatherConfig && weatherConfig.data ? weatherConfig.data : state.weatherConfig;
    state.notificationConfig = notificationConfig && notificationConfig.data ? notificationConfig.data : state.notificationConfig;
    state.notificationStatus = notificationStatus && notificationStatus.data ? notificationStatus.data : state.notificationStatus;
    state.notificationPreview = notificationPreview && notificationPreview.data ? notificationPreview.data : state.notificationPreview;
    state.notificationQr = notificationQr && notificationQr.data ? notificationQr.data : state.notificationQr;
    syncNotificationQrPolling(state.notificationQr);
    state.authError = "";
    loadThemePreference();
  } catch (error) {
    state.config = null;
    state.entities = null;
    state.authError = error.message || "读取受保护数据失败。";
    loadThemePreference();
  }
}

function downloadTextFile(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderAll() {
  ensureCurrentRoom();
  renderDashboard();
  renderRoomPage();
  renderAcPage();
  renderLightPage();
  renderFanPage();
  renderSettingsPage();
  updateConnectionBadge();
  updateLicenseBadge();
  showLicenseBanner();
}

function renderLiveSections() {
  ensureCurrentRoom();
  renderDashboard();
  renderRoomPage();
  renderAcPage();
  renderLightPage();
  renderFanPage();
  updateConnectionBadge();
  updateLicenseBadge();
  showLicenseBanner();
  refreshOpenModalContent();
}

function applyRealtimeEntitySnapshot(snapshot) {
  if (!snapshot || !snapshot.entity_id) return false;
  let changed = false;
  currentRooms().forEach((room) => {
    if (!room || !room.mapped) return;
    if (room.mapped.ac && room.mapped.ac.entity_id === snapshot.entity_id) {
      room.mapped.ac = cloneData(snapshot);
      changed = true;
    }
    if (room.mapped.fresh_air && room.mapped.fresh_air.entity_id === snapshot.entity_id) {
      room.mapped.fresh_air = cloneData(snapshot);
      changed = true;
    }
    if (Array.isArray(room.mapped.lights)) {
      const index = room.mapped.lights.findIndex((item) => item && item.entity_id === snapshot.entity_id);
      if (index >= 0) {
        room.mapped.lights[index] = cloneData(snapshot);
        changed = true;
      }
    }
  });
  return changed;
}

function shouldPatchRealtimeEntity(payload) {
  const domain = String(payload && payload.domain || "").trim().toLowerCase();
  return ["climate", "light", "fan", "switch"].includes(domain);
}

function stopPanelEventReconnect() {
  window.clearTimeout(state.panelEventReconnectTimer);
  state.panelEventReconnectTimer = null;
}

function stopPanelEventRefresh() {
  window.clearTimeout(state.panelEventRefreshTimer);
  state.panelEventRefreshTimer = null;
  state.panelEventRefreshDueAt = 0;
}

async function detectPanelEventsSupport() {
  if (state.panelEventsSupported != null) {
    return Boolean(state.panelEventsSupported);
  }
  if (state.panelEventsProbe) {
    return state.panelEventsProbe;
  }
  if (!state.auth.token || !isConnectionConfigured() || typeof window.WebSocket !== "function") {
    state.panelEventsSupported = false;
    state.syncMode = "polling";
    return false;
  }
  state.panelEventsSupported = true;
  state.syncMode = "websocket-connecting";
  state.panelEventsProbe = Promise.resolve(true).finally(() => {
    state.panelEventsProbe = null;
    updateConnectionBadge();
  });
  return state.panelEventsProbe;
}

function disconnectPanelEvents() {
  stopPanelEventReconnect();
  stopPanelEventRefresh();
  if (state.panelSocket) {
    try {
      state.panelSocket.close();
    } catch (error) {
    }
    state.panelSocket = null;
  }
}

function schedulePanelEventRefresh(delay = 120) {
  const wait = Math.max(0, Number(delay) || 0);
  const dueAt = Date.now() + wait;
  if (state.panelEventRefreshTimer && state.panelEventRefreshDueAt && state.panelEventRefreshDueAt <= dueAt) {
    return;
  }
  stopPanelEventRefresh();
  state.panelEventRefreshDueAt = dueAt;
  state.panelEventRefreshTimer = window.setTimeout(() => {
    state.panelEventRefreshTimer = null;
    state.panelEventRefreshDueAt = 0;
    liveRefreshCurrentState();
  }, wait);
}

function schedulePanelEventReconnect(delay = 3000) {
  stopPanelEventReconnect();
  state.panelEventReconnectTimer = window.setTimeout(() => {
    connectPanelEvents();
  }, delay);
}

async function connectPanelEvents() {
  if (state.panelSocket || !state.auth.token || !isConnectionConfigured() || typeof window.WebSocket !== "function") {
    if (typeof window.WebSocket !== "function") {
      state.panelEventsSupported = false;
      state.syncMode = "polling";
      updateConnectionBadge();
    }
    return;
  }
  state.syncMode = "websocket-connecting";
  updateConnectionBadge();
  const supported = await detectPanelEventsSupport();
  if (!supported) {
    scheduleRefresh(1000);
    return;
  }
  const url = buildRealtimeSocketUrl(`/api/netcafe/panel/ws?token=${encodeURIComponent(state.auth.token)}`);
  const socket = new window.WebSocket(url);
  state.panelSocket = socket;
  state.realtimeDebug.socketConnectCount += 1;

  socket.onopen = () => {
    stopPanelEventReconnect();
    stopRefresh();
    state.syncMode = "websocket";
    state.reloadError = "";
    state.realtimeDebug.socketOpenAtMs = Date.now();
    updateConnectionBadge();
  };

  socket.onmessage = (event) => {
    if (document.hidden || isSettingsPageActive() || autoRefreshPausedOnCurrentPage()) {
      return;
    }
    let payload = null;
    try {
      payload = event && event.data ? JSON.parse(event.data) : null;
    } catch (error) {
      payload = null;
    }
    if (!payload || payload.type === "ready" || payload.type === "pong") {
      return;
    }
    const receivedAt = Date.now();
    const serverEventAt = Number(payload.server_event_at_ms || payload.ts || 0);
    const serverEmitAt = Number(payload.server_emit_at_ms || 0);
    const serverBroadcastAt = Number(payload.server_broadcast_at_ms || 0);
    state.realtimeDebug.messageCount += 1;
    state.realtimeDebug.lastMessageAtMs = receivedAt;
    state.realtimeDebug.lastEntityId = String(payload.entity_id || "");
    state.realtimeDebug.lastDomain = String(payload.domain || "");
    state.realtimeDebug.lastServerEventAtMs = serverEventAt || 0;
    state.realtimeDebug.lastServerEmitAtMs = serverEmitAt || 0;
    state.realtimeDebug.lastServerBroadcastAtMs = serverBroadcastAt || 0;
    state.realtimeDebug.lastReceiveLatencyMs = serverEventAt ? safeDurationMs(receivedAt - serverEventAt) : null;
    state.realtimeDebug.lastBridgeDelayMs = safeDurationMs(payload.server_bridge_delay_ms);
    if (Array.isArray(state.realtimeDebug.actionTraces) && state.realtimeDebug.actionTraces.length) {
      state.realtimeDebug.actionTraces = state.realtimeDebug.actionTraces.map((trace) => {
        if (!trace || !Array.isArray(trace.entity_ids) || !trace.entity_ids.length) return trace;
        if (!trace.entity_ids.includes(String(payload.entity_id || ""))) return trace;
        const nextTrace = { ...trace };
        if (!nextTrace.first_ws_at_ms) {
          nextTrace.first_ws_at_ms = receivedAt;
        }
        if (!nextTrace.fulfilled_at_ms && eventSatisfiesActionTrace(nextTrace, payload)) {
          nextTrace.fulfilled_at_ms = receivedAt;
          nextTrace.fulfilled_entity_id = String(payload.entity_id || "");
          nextTrace.fulfilled_state = String(payload.state || payload.snapshot && payload.snapshot.state || "");
        }
        return nextTrace;
      });
    }
    const patched = payload && payload.snapshot && shouldPatchRealtimeEntity(payload)
      ? applyRealtimeEntitySnapshot(payload.snapshot)
      : false;
    if (patched) {
      const renderStart = performance.now();
      renderLiveSections();
      state.realtimeDebug.lastRenderDurationMs = safeDurationMs(performance.now() - renderStart);
      appendRealtimeDebugEvent({
        entity_id: state.realtimeDebug.lastEntityId,
        domain: state.realtimeDebug.lastDomain,
        received_at_ms: receivedAt,
        receive_latency_ms: state.realtimeDebug.lastReceiveLatencyMs,
        bridge_delay_ms: state.realtimeDebug.lastBridgeDelayMs,
        render_duration_ms: state.realtimeDebug.lastRenderDurationMs,
        patched: true,
      });
      schedulePanelEventRefresh(120);
      return;
    }
    appendRealtimeDebugEvent({
      entity_id: state.realtimeDebug.lastEntityId,
      domain: state.realtimeDebug.lastDomain,
      received_at_ms: receivedAt,
      receive_latency_ms: state.realtimeDebug.lastReceiveLatencyMs,
      bridge_delay_ms: state.realtimeDebug.lastBridgeDelayMs,
      render_duration_ms: null,
      patched: false,
    });
    schedulePanelEventRefresh(120);
  };

  socket.onerror = () => {
    if (state.panelSocket === socket) {
      state.realtimeDebug.socketErrorCount += 1;
      state.syncMode = "polling";
      updateConnectionBadge();
    }
  };

  socket.onclose = () => {
    if (state.panelSocket === socket) {
      state.realtimeDebug.socketCloseAtMs = Date.now();
      disconnectPanelEvents();
      state.syncMode = "polling";
      updateConnectionBadge();
      scheduleRefresh(1000);
      schedulePanelEventReconnect();
    }
  };
}

function redrawLoadTrendChart() {
  const canvas = document.getElementById("loadTrendChart");
  if (!canvas) return;
  try {
    const values = JSON.parse(canvas.dataset.values || "[]");
    drawLoadTrendChart(canvas, values);
  } catch (error) {
  }
}

function redrawDailySummaryChart() {
  const canvas = document.getElementById("dailySummaryChart");
  if (!canvas) return;
  drawDailySummaryChart(canvas, state.dailySummary && Array.isArray(state.dailySummary.items) ? state.dailySummary.items : []);
}

function updateDashboardLogScroll(logs) {
  const container = document.getElementById("dashboardLogScroll");
  if (!container) return;
  const items = Array.isArray(logs) ? logs : [];
  const signature = items.map((log) => `${log.timestamp || ""}|${log.room_name || ""}|${log.action || ""}|${log.message || ""}`).join("||");
  const hadSignature = Boolean(state.dashboardLogSignature);
  const changed = signature !== state.dashboardLogSignature;
  state.dashboardLogSignature = signature;
  if (!changed || !hadSignature) return;
  window.requestAnimationFrame(() => {
    container.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  });
}

async function reloadAll(showToast = true) {
  if (state.isReloading) return;
  state.isReloading = true;
  try {
    if (showToast) {
      state.historyAuthError = "";
      state.historyAuthProbe = null;
    }
    if (!state.auth.token) {
      redirectToLogin();
      return;
    }
    if (!isConnectionConfigured()) {
      state.overview = null;
      state.config = null;
      state.entities = null;
      state.energyHistory = { daily_kwh: null, monthly_kwh: null, source: "" };
      state.dailySummary = null;
      state.authError = "";
      state.reloadError = "";
      state.refreshFailureCount = 0;
      state.lastSuccessfulReloadAt = 0;
      renderAll();
      if (showToast) {
        showMessage("当前页面不在智慧网吧同源环境中，请从集成入口打开。", "warning", true);
      }
      return;
    }
    await loadPublicData();
    await loadProtectedData();
    await updateWeather();
    if (!state.authError && state.overview) {
      await loadComputedEnergyHistory(state.overview);
      await loadDailyUsageSummary(state.overview);
    } else {
      state.energyHistory = { daily_kwh: null, monthly_kwh: null, source: "" };
      state.dailySummary = null;
    }
    state.reloadError = "";
    state.refreshFailureCount = 0;
    state.lastSuccessfulReloadAt = Date.now();
    ensureCurrentRoom();
    renderAll();
    if (showToast) {
      showMessage(state.authError ? "总览已刷新，当前仍是只读模式。" : "页面数据已刷新。", state.authError ? "warning" : "success", true);
    }
  } catch (error) {
    state.reloadError = error.message || "加载失败。";
    state.energyHistory = { daily_kwh: null, monthly_kwh: null, source: "" };
    state.dailySummary = null;
    state.refreshFailureCount += 1;
    renderAll();
    if (showToast) {
      showMessage(error.message || "加载失败。", "error");
    }
  } finally {
    state.isReloading = false;
  }
}

function nextRefreshDelay() {
  if (state.panelEventsSupported === false || typeof window.WebSocket !== "function") {
    if (!state.reloadError) return 1000;
    return Math.min(5000, Math.max(1200, state.refreshFailureCount * 1000));
  }
  if (!isConnectionConfigured()) return 15000;
  if (!state.reloadError) return 15000;
  return Math.min(60000, Math.max(5000, state.refreshFailureCount * 5000));
}

function stopRefresh() {
  window.clearTimeout(state.refreshTimer);
  state.refreshTimer = null;
}

function stopRealtimeSync() {
  stopRefresh();
  disconnectPanelEvents();
}

function autoRefreshPausedOnCurrentPage() {
  const page = String(document.body.getAttribute("data-page") || "").trim().toLowerCase();
  return ["settings"].includes(page);
}

async function liveRefreshCurrentState() {
  if (state.isReloading || !isConnectionConfigured() || !state.auth.token) {
    return;
  }
  const startedAt = performance.now();
  try {
    await loadPublicData();
    renderLiveSections();
    state.reloadError = "";
    state.lastSuccessfulReloadAt = Date.now();
    state.realtimeDebug.lastRefreshDurationMs = safeDurationMs(performance.now() - startedAt);
    state.realtimeDebug.lastRefreshAtMs = Date.now();
  } catch (error) {
    state.reloadError = error.message || "轻量刷新失败。";
    state.refreshFailureCount += 1;
    state.realtimeDebug.lastRefreshDurationMs = safeDurationMs(performance.now() - startedAt);
    state.realtimeDebug.lastRefreshAtMs = Date.now();
  }
}

function scheduleRefresh(delay = nextRefreshDelay()) {
  stopRefresh();
  state.refreshTimer = window.setTimeout(() => {
    if (isSettingsPageActive() || autoRefreshPausedOnCurrentPage()) {
      scheduleRefresh();
      return;
    }
    if (isConnectionConfigured()) {
      reloadAll(false).finally(() => {
        scheduleRefresh();
      });
      return;
    }
    scheduleRefresh();
  }, delay);
}

function boot() {
  loadBrandLogoCatalog();
  loadConnectionSettings();
  loadThemePreference();
  loadStoredAuthToken();
  loadSidebarPreference();
  syncConfiguredTheme();
  renderAuthGate();
  updateDateTime();
  updateConnectionBadge();
  updateLicenseBadge();
  restoreAuthSession().finally(() => {
    if (state.auth.user) {
      reloadAll(false).finally(() => {
        scheduleRefresh();
        connectPanelEvents();
      });
    }
  });
  window.setInterval(updateDateTime, 1000);
  window.setInterval(syncConfiguredTheme, 60000);
  window.addEventListener("unhandledrejection", (event) => {
    if (!isIgnorableAsyncChannelError(event.reason)) return;
    event.preventDefault();
  });
  window.addEventListener("online", () => {
    state.reloadError = "";
    if (isSettingsPageActive() || autoRefreshPausedOnCurrentPage()) {
      scheduleRefresh(15000);
      connectPanelEvents();
      return;
    }
    reloadAll(false).finally(() => {
      scheduleRefresh(15000);
      connectPanelEvents();
    });
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && isConnectionConfigured() && !isSettingsPageActive() && !autoRefreshPausedOnCurrentPage()) {
      reloadAll(false).finally(() => {
        scheduleRefresh(15000);
        connectPanelEvents();
      });
      return;
    }
    if (document.hidden) {
      disconnectPanelEvents();
    }
  });
  window.addEventListener("resize", () => {
    window.clearTimeout(boot.resizeTimer);
    boot.resizeTimer = window.setTimeout(() => {
      syncSidebarCollapsedState();
      redrawLoadTrendChart();
      redrawDailySummaryChart();
    }, 80);
  });
}

boot();
