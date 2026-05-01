## Repo facts

Read these files before changing the HA device connection flow:

- `netcafe_automation/www/panel.html`
- `netcafe_automation/www/__init__.py`
- `netcafe_automation/config_flow.py`

## Current frontend contract

`netcafe_automation/www/panel.html` already implements the main connection flow:

- `PANEL_API.states = /api/netcafe/panel/states`
- `PANEL_API.licenseStatus = /api/netcafe/panel/license/status`
- `PANEL_API.serviceBase = /api/netcafe/panel/service`
- `getHomeAssistantAccessToken()` reads `localStorage.hassTokens`
- `authenticatedFetch()` tries bearer auth first and falls back to same-origin session on `401`
- `fetchPanelStates()` loads the full entity snapshot
- `connectStateStream()` connects to `/api/websocket`
- the socket subscribes to `state_changed`
- `callService()` posts service calls to the panel proxy
- `groupDevicesByRoomOptimized()` groups entities into rooms
- `extractComputerInfo()` and `extractIP()` derive room number and IP tail from naming rules

Important runtime assumptions already present in the page:

- opening the page with `file://` is unsupported
- `/api/netcafe/panel/*` must be mounted by the HA integration
- when real-time socket auth fails, the page falls back to polling

## Current backend contract

`netcafe_automation/www/__init__.py` exposes the bridge that the frontend depends on:

- `NetcafePanelView`
  - `GET /api/netcafe/panel`
  - returns the HTML page
- `NetcafeAutomationConfigView`
  - `GET /api/netcafe/automation`
  - returns the automation page
- `NetcafePanelStatesView`
  - `GET /api/netcafe/panel/states`
  - returns `{"success": true, "states": [state.as_dict(), ...]}`
- `NetcafePanelServiceView`
  - `POST /api/netcafe/panel/service/{domain}/{service}`
  - proxies `hass.services.async_call(...)`
- `NetcafePanelLicenseStatusView`
  - `GET /api/netcafe/panel/license/status`

Current limitation:

- the bridge returns state snapshots, not registry records
- if future work needs `device_id`, `area_id`, or `config_entry_id`, add a new backend view using public registries

## Recommended extension path

If future development needs true device-level mapping instead of entity-only mapping, add a backend view that joins:

- entity registry
- device registry
- area registry

Use public helpers, not private data keys:

```python
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

area_reg = ar.async_get(hass)
device_reg = dr.async_get(hass)
entity_reg = er.async_get(hass)
```

Then return a normalized payload such as:

```json
{
  "entity_id": "light.room101_main",
  "device_id": "abc123",
  "area_id": "room101",
  "domain": "light",
  "friendly_name": "101号包厢主灯",
  "supported_features": 0,
  "state": "on"
}
```

## Naming and grouping rules already in use

The current panel expects configurable matching rules in `APP_CONFIG.device_matching`, including:

- `exclude_keywords`
- `exclude_keywords_name_only`
- `excluded_entities`
- `light_keywords`
- `ventilator_keywords`
- `suffix_classification`
- `computer_naming.pattern`
- `computer_naming.room_group`
- `computer_naming.ip_group`

Do not hardcode room logic in multiple places. Extend the config-driven matcher first.

## Panel URL facts

`netcafe_automation/config_flow.py` advertises these URLs to users after setup:

- `/api/netcafe/automation`
- `/api/netcafe/panel`

That means future frontend work should assume the page is served by HA, not by an unrelated static server.
