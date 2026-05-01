const HVAC_MODE_LABELS = {
    off: "关闭",
    cool: "制冷",
    heat: "制热",
    fan_only: "送风",
    dry: "除湿",
    auto: "自动",
    heat_cool: "自动",
};

const FAN_MODE_LABELS = {
    auto: "自动",
    low: "低速",
    medium: "中速",
    mid: "中速",
    middle: "中速",
    high: "高速",
    turbo: "强力",
    quiet: "静音",
    silent: "静音",
};

const appState = {
    bootstrap: null,
    isConnected: false,
    refreshInterval: null,
    tempChangeTimer: null,
    pendingTemperature: null,
    licenseStatus: {
        isValid: false,
        message: "正在读取总控授权状态",
        expireDate: null,
        daysRemaining: -1,
    },
};

const tempDisplay = document.getElementById("temperature");
const tempDisplayContainer = document.querySelector(".temp-display");
const powerBtn = document.getElementById("power-btn");
const tempUpBtn = document.getElementById("temp-up");
const tempDownBtn = document.getElementById("temp-down");
const modeSelect = document.getElementById("mode-select");
const fanSelect = document.getElementById("fan-select");
const swingSelect = document.getElementById("swing-select");
const connectionStatus = document.getElementById("connection-status");
const roomNameEl = document.getElementById("room-name");
const roomNameLightEl = document.getElementById("room-name-light");
const currentTemp = document.getElementById("current-temp");
const lightCountEl = document.getElementById("light-count");
const lightsContainer = document.getElementById("lights-container");
const policySummary = document.getElementById("policy-summary");
const acReason = document.getElementById("ac-reason");
const lightReason = document.getElementById("light-reason");
const closeBtn = document.getElementById("close-btn");
const licensePanel = document.getElementById("license-panel");
const licenseMessage = document.getElementById("license-message");
const swingGroup = document.querySelector(".swing-group");
const tempRow = document.querySelector(".temp-row");
const controlsRow = document.querySelector(".controls-row");

function setStatus(text, color = "#4FC3F7") {
    connectionStatus.textContent = text;
    connectionStatus.style.color = color;
}

function setReasonBox(element, text) {
    if (!element) return;
    if (text) {
        element.textContent = text;
        element.classList.remove("hidden");
    } else {
        element.textContent = "";
        element.classList.add("hidden");
    }
}

function stopAutoRefreshes() {
    if (appState.refreshInterval) {
        clearInterval(appState.refreshInterval);
        appState.refreshInterval = null;
    }
    if (appState.tempChangeTimer) {
        clearTimeout(appState.tempChangeTimer);
        appState.tempChangeTimer = null;
    }
}

function normalizeLicenseStatus(raw) {
    const status = raw && typeof raw === "object" ? raw : {};
    const expireDate = status.expireDate || status.expire_date || null;
    const daysRemaining = Number.isFinite(Number(status.daysRemaining))
        ? Number(status.daysRemaining)
        : (Number.isFinite(Number(status.days_remaining)) ? Number(status.days_remaining) : -1);
    return {
        isValid: Boolean(status.isValid ?? status.is_valid),
        message: String(status.message || "未激活卡密"),
        expireDate,
        daysRemaining,
        key: status.key || "",
    };
}

function isLicenseUsable() {
    return Boolean(appState.licenseStatus && appState.licenseStatus.isValid);
}

function currentBootstrap() {
    return appState.bootstrap || null;
}

function currentAc() {
    return currentBootstrap() ? currentBootstrap().ac || null : null;
}

function currentLights() {
    return currentBootstrap() ? currentBootstrap().lights || [] : [];
}

function getCapability(name) {
    const caps = currentBootstrap() && currentBootstrap().ui_caps ? currentBootstrap().ui_caps : {};
    return caps[name] || { enabled: false, reason: "当前未连接总控" };
}

function getEffectiveLimits() {
    const limits = currentBootstrap() && currentBootstrap().effective_limits ? currentBootstrap().effective_limits : {};
    return {
        min: Number.isFinite(Number(limits.ac_temperature_min)) ? Number(limits.ac_temperature_min) : 16,
        max: Number.isFinite(Number(limits.ac_temperature_max)) ? Number(limits.ac_temperature_max) : 32,
    };
}

function getAllowedControls() {
    const controls = currentBootstrap() && currentBootstrap().allowed_controls ? currentBootstrap().allowed_controls : {};
    return {
        hvacModes: Array.isArray(controls.hvac_modes) ? controls.hvac_modes : [],
        fanModes: Array.isArray(controls.fan_modes) ? controls.fan_modes : [],
    };
}

function uniqueValues(values = []) {
    return Array.from(new Set(
        (values || []).map((value) => String(value || "").trim()).filter(Boolean)
    ));
}

function formatOptionLabel(value, labelMap = {}) {
    const key = String(value || "");
    return labelMap[key] || labelMap[key.toLowerCase()] || key;
}

function renderSelectOptions(selectEl, values, currentValue, labelMap, unsupportedLabel) {
    const options = uniqueValues(values);
    selectEl.innerHTML = "";

    if (!options.length) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = unsupportedLabel;
        selectEl.appendChild(option);
        selectEl.value = "";
        return;
    }

    options.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = formatOptionLabel(value, labelMap);
        selectEl.appendChild(option);
    });

    selectEl.value = options.includes(currentValue) ? currentValue : options[0];
}

function clampTemperature(value) {
    const { min, max } = getEffectiveLimits();
    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) {
        return min;
    }
    return Math.min(max, Math.max(min, numericValue));
}

function translateHttpStatus(status, detail = "") {
    const suffix = detail ? `（${detail}）` : "";
    switch (Number(status)) {
    case 400:
        return `请求参数不正确${suffix}`;
    case 401:
        return "当前分机未被主机允许访问，请先在总控中启用分机局域网白名单";
    case 403:
        return detail || "当前分机未被主机允许访问，请检查白名单设置";
    case 404:
        return detail || "当前分机 IP 未在主机当前 CSV 中分配";
    case 409:
        return detail || "当前分机识别到多个房间，请检查主机映射";
    case 502:
        return `主机已连接，但 Home Assistant 网关返回 502，请检查主机上的反向代理或 HA 服务状态${suffix}`;
    case 503:
        return `Home Assistant 服务暂时不可用，请稍后重试或检查主机服务状态${suffix}`;
    case 504:
        return `主机连接超时，通常是主机上的 Home Assistant 或代理响应过慢${suffix}`;
    default:
        return "";
    }
}

function formatRequestErrorMessage(error, fallback = "请求失败") {
    const text = String(error?.message || "").trim();
    const status = Number(error?.status || 0);
    const lower = text.toLowerCase();
    const httpMessage = translateHttpStatus(status, text && !/^http\s+\d+$/i.test(text) ? text : "");

    if (httpMessage) {
        return httpMessage;
    }
    if (!text) {
        return fallback;
    }
    if (text.includes("当前分机 IP") || text.includes("白名单")) {
        return text;
    }
    if (text.includes("未在主机当前 CSV 中分配")) {
        return text;
    }
    if (text.includes("运行时尚未就绪")) {
        return "主机已识别到本机 IP，但对应包厢运行时尚未就绪";
    }
    if (lower.includes("failed to fetch") || lower.includes("fetch failed")) {
        return "无法连接到主机，请检查主机 IP、端口 8123 和网络连通性";
    }
    if (lower.includes("econnrefused") || lower.includes("connection refused")) {
        return "主机拒绝连接，请确认主机 IP 正确且 Home Assistant 正在监听 8123 端口";
    }
    if (lower.includes("timed out") || lower.includes("timeout")) {
        return "连接主机超时，请检查网络是否通畅，或主机负载是否过高";
    }
    if (lower.includes("getaddrinfo") || lower.includes("enotfound") || lower.includes("dns")) {
        return "无法解析主机地址，请检查主机配置是否正确";
    }
    if (/^http\s+\d+$/i.test(text)) {
        return `主机接口返回异常：${text}`;
    }
    return text;
}

async function requestJson(path, method = "GET", data = null) {
    const response = await fetch(path, {
        method,
        headers: {
            "Content-Type": "application/json",
        },
        body: data == null ? undefined : JSON.stringify(data),
    });
    const rawText = await response.text();
    let parsed = null;

    if (rawText) {
        try {
            parsed = JSON.parse(rawText);
        } catch (_error) {
            parsed = rawText;
        }
    }

    if (!response.ok || !parsed || parsed.success === false) {
        const detail = typeof parsed === "string"
            ? parsed.trim()
            : parsed?.message || parsed?.error || `HTTP ${response.status}`;
        const error = new Error(detail);
        error.status = response.status;
        error.authRequired = Boolean(parsed && typeof parsed === "object" && parsed.auth_required);
        error.lanTrustRequired = Boolean(parsed && typeof parsed === "object" && parsed.lan_trust_required);
        error.clientIp = parsed && typeof parsed === "object" ? String(parsed.client_ip || "").trim() : "";
        throw error;
    }

    return parsed.data !== undefined ? parsed.data : parsed;
}

function enableAcControls(enabled, isClimate) {
    powerBtn.disabled = !enabled;
    tempUpBtn.disabled = !enabled || !isClimate;
    tempDownBtn.disabled = !enabled || !isClimate;
    modeSelect.disabled = !enabled || !isClimate;
    fanSelect.disabled = !enabled || !isClimate;
    swingSelect.disabled = true;
}

function renderDisconnectedState(message) {
    roomNameEl.textContent = "等待主机连接...";
    roomNameLightEl.textContent = roomNameEl.textContent;
    currentTemp.textContent = "--°C";
    tempDisplay.textContent = "--";
    policySummary.innerHTML = "";
    lightsContainer.innerHTML = `<div class="light-error">${message || "未连接总控"}</div>`;
    lightCountEl.textContent = "未连接";
    setReasonBox(acReason, message || "未连接总控");
    setReasonBox(lightReason, message || "未连接总控");
    enableAcControls(false, false);
}

function buildPolicyTags(bootstrap) {
    const tags = [];
    const subcontrol = bootstrap?.policy?.subcontrol || {};
    const automation = bootstrap?.policy?.automation || {};
    const limits = bootstrap?.effective_limits || {};

    if (subcontrol.enforce_selected_season) {
        tags.push(`${automation?.enabled ? "总控" : "季节"}锁定`);
    }
    if (subcontrol.inherit_temperature_limits) {
        tags.push(`温度 ${limits.ac_temperature_min ?? 16}-${limits.ac_temperature_max ?? 32}℃`);
    }
    if (automation?.schedule?.enabled) {
        if (bootstrap?.policy?.runtime?.schedule_allowed === false) {
            tags.push("当前时段外");
        } else {
            tags.push(`时段 ${automation.schedule.start_time}-${automation.schedule.end_time}`);
        }
    }
    if (bootstrap?.policy?.runtime?.ac_manual_override_until) {
        tags.push(`不允许超过 ${limits.ac_temperature_max ?? 32}℃`);
    }
    return tags;
}

function renderPolicySummary(bootstrap) {
    const tags = buildPolicyTags(bootstrap);
    policySummary.innerHTML = tags.map((tag) => `<span class="policy-tag">${tag}</span>`).join("");
}

function acReasonsSummary() {
    const reasons = [
        getCapability("ac_power").reason,
        getCapability("ac_temperature").reason,
        getCapability("ac_mode").reason,
        getCapability("ac_fan_mode").reason,
    ].filter(Boolean);
    return Array.from(new Set(reasons)).join("；");
}

function renderAcPanel() {
    const bootstrap = currentBootstrap();
    const ac = currentAc();

    swingGroup.style.display = "none";
    swingSelect.disabled = true;

    if (!bootstrap || !ac) {
        currentTemp.textContent = "--°C";
        tempDisplay.textContent = "--";
        tempRow.style.display = "";
        setReasonBox(acReason, bootstrap ? "当前房间未绑定空调" : "未连接总控");
        enableAcControls(false, false);
        return;
    }

    const isClimate = ac.domain === "climate";
    const isPowerOn = Boolean(ac.is_on);
    const effectiveTemperature = clampTemperature(ac.temperature ?? appState.pendingTemperature ?? getEffectiveLimits().min);
    appState.pendingTemperature = effectiveTemperature;

    currentTemp.textContent = isClimate
        ? `${ac.current_temperature != null ? ac.current_temperature : "--"}°C`
        : (isPowerOn ? "设备已开启" : "设备已关闭");
    tempDisplay.textContent = isClimate ? effectiveTemperature : (isPowerOn ? "ON" : "OFF");

    tempDisplayContainer.classList.remove("mode-cool", "mode-heat", "mode-fan_only", "mode-dry");
    if (isClimate && isPowerOn) {
        tempDisplayContainer.classList.add(`mode-${ac.hvac_mode || ac.state}`);
    }

    powerBtn.textContent = isPowerOn ? "关闭" : "开启";
    powerBtn.classList.toggle("off", !isPowerOn);

    if (!isClimate) {
        tempRow.style.display = "none";
        modeSelect.style.display = "none";
        fanSelect.style.display = "none";
        controlsRow.style.justifyContent = "center";
        powerBtn.disabled = !getCapability("ac_power").enabled || !isLicenseUsable() || !appState.isConnected;
        setReasonBox(acReason, getCapability("ac_power").reason || "");
        return;
    }

    tempRow.style.display = "";
    modeSelect.style.display = "";
    fanSelect.style.display = "";
    controlsRow.style.justifyContent = "";

    renderSelectOptions(
        modeSelect,
        getAllowedControls().hvacModes.length ? getAllowedControls().hvacModes : (ac.hvac_modes || [ac.hvac_mode || ac.state || "off"]),
        ac.hvac_mode || ac.state || "off",
        HVAC_MODE_LABELS,
        "不支持模式"
    );
    renderSelectOptions(
        fanSelect,
        getAllowedControls().fanModes.length ? getAllowedControls().fanModes : (ac.fan_modes || []),
        ac.fan_mode || "",
        FAN_MODE_LABELS,
        "不支持风速"
    );

    const canPower = appState.isConnected && isLicenseUsable() && getCapability("ac_power").enabled;
    const canTemp = appState.isConnected && isLicenseUsable() && isPowerOn && getCapability("ac_temperature").enabled;
    const canMode = appState.isConnected && isLicenseUsable() && getCapability("ac_mode").enabled;
    const canFan = appState.isConnected && isLicenseUsable() && getCapability("ac_fan_mode").enabled;
    const limits = getEffectiveLimits();

    powerBtn.disabled = !canPower;
    tempUpBtn.disabled = !canTemp || effectiveTemperature >= limits.max;
    tempDownBtn.disabled = !canTemp || effectiveTemperature <= limits.min;
    modeSelect.disabled = !canMode;
    fanSelect.disabled = !canFan;

    setReasonBox(acReason, acReasonsSummary());
}

function renderLightsPanel() {
    const bootstrap = currentBootstrap();
    const lights = currentLights();
    roomNameLightEl.textContent = bootstrap?.room_name || roomNameEl.textContent;

    if (!bootstrap) {
        lightCountEl.textContent = "未连接";
        lightsContainer.innerHTML = '<div class="light-error">未连接总控</div>';
        setReasonBox(lightReason, "未连接总控");
        return;
    }

    if (!lights.length) {
        lightCountEl.textContent = "未绑定灯光";
        lightsContainer.innerHTML = '<div class="light-empty">当前房间未绑定灯光设备</div>';
        setReasonBox(lightReason, getCapability("light_control").reason || "");
        return;
    }

    const lightCap = getCapability("light_control");
    lightCountEl.textContent = `共 ${lights.length} 个设备`;
    setReasonBox(lightReason, lightCap.reason || "");

    lightsContainer.innerHTML = lights.map((light) => {
        const friendlyName = light.friendly_name || light.entity_id;
        const isOn = Boolean(light.is_on);
        return `
            <div class="light-item">
                <span class="light-name">${friendlyName}</span>
                <button class="light-toggle ${isOn ? "on" : ""}" data-entity-id="${light.entity_id}" data-turn-on="${isOn ? "0" : "1"}" ${lightCap.enabled ? "" : "disabled"}></button>
            </div>
        `;
    }).join("");

    lightsContainer.querySelectorAll(".light-toggle").forEach((button) => {
        button.addEventListener("click", async () => {
            const entityId = button.dataset.entityId;
            const turnOn = button.dataset.turnOn === "1";
            await performSubcontrolAction("light_toggle", { entity_id: entityId, turn_on: turnOn });
        });
    });
}

function renderBootstrap() {
    const bootstrap = currentBootstrap();
    if (!bootstrap) {
        renderDisconnectedState("未连接总控");
        return;
    }

    roomNameEl.textContent = bootstrap.room_name || `未匹配 (${bootstrap.local_ip || "--"})`;
    roomNameLightEl.textContent = roomNameEl.textContent;
    renderPolicySummary(bootstrap);
    renderAcPanel();
    renderLightsPanel();

    const dominantReason = Array.from(new Set(Object.values(bootstrap.ui_reasons || {}).filter(Boolean)))[0] || "";
    if (dominantReason) {
        setStatus(`已连接 · ${dominantReason}`, "#f6c85f");
    } else {
        setStatus("已连接总控", "#10b981");
    }
}

function applyLicenseState() {
    if (isLicenseUsable()) {
        licensePanel.classList.add("hidden");
        return;
    }

    stopAutoRefreshes();
    licensePanel.classList.remove("hidden");
    const message = appState.licenseStatus.message || "授权状态由 netcafe_automation 总控决定";
    licenseMessage.textContent = message;

    if (appState.bootstrap) {
        renderBootstrap();
    } else {
        appState.isConnected = false;
        renderDisconnectedState(message);
    }
    setStatus(message, "#ff6b6b");
}

async function loadBootstrap(showError = true, options = {}) {
    const force = Boolean(options.force);
    if (!force && !isLicenseUsable()) {
        applyLicenseState();
        return;
    }

    try {
        const bootstrap = await requestJson("/api/netcafe/subcontrol/bootstrap");
        appState.bootstrap = bootstrap;
        appState.isConnected = true;
        if (bootstrap && bootstrap.license) {
            appState.licenseStatus = normalizeLicenseStatus(bootstrap.license);
        }
        renderBootstrap();
        applyLicenseState();
    } catch (error) {
        const message = formatRequestErrorMessage(error, "读取总控状态失败");
        appState.bootstrap = null;
        appState.isConnected = false;
        renderDisconnectedState(message);
        setStatus(message, "#ffb74d");
        if (showError) {
            console.error("读取 bootstrap 失败:", error);
        }
    }
}

function startAutoRefresh() {
    stopAutoRefreshes();
    appState.refreshInterval = setInterval(() => {
        if (isLicenseUsable()) {
            loadBootstrap(false);
        }
    }, 10000);
}

async function performSubcontrolAction(action, value = null) {
    const bootstrap = currentBootstrap();
    if (!bootstrap || !bootstrap.room_id) return;
    if (!isLicenseUsable()) return;

    try {
        await requestJson("/api/netcafe/subcontrol/action", "POST", {
            room_id: bootstrap.room_id,
            action,
            value,
        });
        await loadBootstrap(false);
    } catch (error) {
        const message = formatRequestErrorMessage(error, "控制失败");
        setStatus(message, "#ffb74d");
        setReasonBox(acReason, action.startsWith("light_") ? acReason.textContent : message);
        if (action.startsWith("light_")) {
            setReasonBox(lightReason, message);
        }
    }
}

powerBtn.addEventListener("click", async () => {
    const ac = currentAc();
    if (!ac) return;
    await performSubcontrolAction(ac.is_on ? "ac_turn_off" : "ac_turn_on");
});

tempUpBtn.addEventListener("click", () => {
    const ac = currentAc();
    if (!ac || !ac.is_on) return;
    const nextTemp = clampTemperature((appState.pendingTemperature ?? ac.temperature ?? getEffectiveLimits().min) + 1);
    appState.pendingTemperature = nextTemp;
    tempDisplay.textContent = nextTemp;
    if (appState.tempChangeTimer) clearTimeout(appState.tempChangeTimer);
    appState.tempChangeTimer = setTimeout(() => performSubcontrolAction("ac_set_temperature", nextTemp), 500);
});

tempDownBtn.addEventListener("click", () => {
    const ac = currentAc();
    if (!ac || !ac.is_on) return;
    const nextTemp = clampTemperature((appState.pendingTemperature ?? ac.temperature ?? getEffectiveLimits().min) - 1);
    appState.pendingTemperature = nextTemp;
    tempDisplay.textContent = nextTemp;
    if (appState.tempChangeTimer) clearTimeout(appState.tempChangeTimer);
    appState.tempChangeTimer = setTimeout(() => performSubcontrolAction("ac_set_temperature", nextTemp), 500);
});

modeSelect.addEventListener("change", (event) => {
    if (!event.target.value) return;
    performSubcontrolAction("ac_set_hvac_mode", event.target.value);
});

fanSelect.addEventListener("change", (event) => {
    if (!event.target.value) return;
    performSubcontrolAction("ac_set_fan_mode", event.target.value);
});

swingSelect.addEventListener("change", () => {
    setReasonBox(acReason, "当前分机版本暂不支持摆风控制");
});

closeBtn.addEventListener("click", () => {
    window.close();
});

document.querySelectorAll(".tab-btn").forEach((button) => {
    button.addEventListener("click", () => {
        const targetTab = button.dataset.tab;
        document.querySelectorAll(".tab-btn").forEach((tabButton) => tabButton.classList.remove("active"));
        button.classList.add("active");
        document.querySelectorAll(".tab-content").forEach((content) => {
            content.classList.toggle("active", content.id === `${targetTab}-panel`);
        });
    });
});

(async function init() {
    await loadBootstrap(false, { force: true });
    if (isLicenseUsable()) {
        startAutoRefresh();
    }
})();
