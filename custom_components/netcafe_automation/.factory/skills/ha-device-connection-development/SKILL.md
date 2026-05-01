---
name: ha-device-connection-development
description: Design and implement technical plans for acquiring, connecting, grouping, and controlling Home Assistant devices in this repo's netcafe panel or related tooling. Use when Codex needs to build or extend Home Assistant device discovery, token or session auth, WebSocket state sync, HTTP proxy views, entity-to-room mapping, or service-call bridges for `panel.html`, automation pages, or future dashboards. Focus on architecture and implementation, not visual design.
---

# HA Device Connection Development

Use this skill when the task is about how to fetch Home Assistant devices, keep them connected, and control them reliably. Do not use it for styling or visual polish.

Read [references/repo-facts.md](references/repo-facts.md) before changing behavior. It captures the current contract already implemented in this repo.

## Core decisions

1. Treat `entity` as the frontend's primary unit.
   - Fetch states first.
   - Filter actionable domains such as `climate`, `light`, `switch`, `fan`, `device_tracker`, `group`, `weather`, and selected `sensor`.
   - Use `entity_id`, `state`, `attributes`, `last_changed`, and `last_updated` as the working model.
2. Prefer an integration-side HTTP bridge for snapshots and service calls.
   - Frontend should call `/api/netcafe/panel/states` and `/api/netcafe/panel/service/{domain}/{service}`.
   - Keep business rules, auth fallback, and scope control in Python rather than in raw browser code.
3. Use native HA WebSocket only for the real-time change feed.
   - Connect to `/api/websocket`.
   - Authenticate with the panel token when available.
   - Subscribe to `state_changed`.
   - Keep HTTP snapshot and polling fallback for recovery.
4. Distinguish entity discovery from registry lookup.
   - `hass.states.async_all()` is enough for dashboards and controls.
   - If the feature truly needs `device_id`, `area_id`, `config_entry_id`, or registry metadata, add a backend endpoint using HA registries. Do not try to infer those only from browser state objects.
5. Never rely on opening raw local HTML files.
   - The page must be served by Home Assistant or a same-origin bridge. `file://` cannot reach `/api/...`.

## Implementation workflow

1. Confirm access mode.
   - Preferred: the page is loaded from `/api/netcafe/panel` or `/api/netcafe/automation`.
   - Acceptable: a same-origin frontend hosted behind HA with a valid session.
   - Avoid: standalone static hosting unless you also provide explicit token handling and a safe proxy.
2. Fetch a full state snapshot first.
   - Use same-origin `fetch`.
   - If bearer auth is present and returns `401`, retry with the current HA session.
   - Validate the response shape before processing.
3. Normalize entities into app models.
   - Keep the original HA payload.
   - Derive `domain`, display name, room key, device category, and control capability.
4. Start the WebSocket stream.
   - Precheck token validity when possible.
   - `auth_required` -> send token.
   - `auth_ok` -> `subscribe_events` for `state_changed`.
   - On `auth_invalid`, heartbeat timeout, or close: switch to polling and schedule reconnect.
5. Route controls through the service bridge.
   - `POST /api/netcafe/panel/service/{domain}/{service}` with `{ entity_id, ...data }`.
   - If WebSocket is not ready, do a delayed snapshot sync after a successful control call.
6. Keep matching rules configurable.
   - Regex for room and IP extraction.
   - Include and exclude keywords.
   - Suffix-based type classification.
   - Separate public-area naming from room naming.
7. Expand only when needed.
   - Need complex query data: add a dedicated `HomeAssistantView`.
   - Need service return data: register the service with `supports_response`.
   - Need persistence: use `Store`, not private underscore APIs.

## Architecture patterns

### Pattern A: Recommended for this repo

Frontend + integration bridge + HA WebSocket.

Use when:
- the page lives inside HA
- you need safe service calls
- you want minimal token exposure
- you already have custom integration code

Flow:
1. Browser loads `/api/netcafe/panel`
2. Browser calls `/api/netcafe/panel/states`
3. Integration returns serialized `hass.states.async_all()`
4. Browser opens `/api/websocket` and subscribes to `state_changed`
5. Browser calls `/api/netcafe/panel/service/{domain}/{service}` for control

### Pattern B: Direct HA frontend

Browser calls `/api/states`, `/api/services/...`, and `/api/websocket` directly with HA token or session.

Use only when:
- there is no custom integration bridge
- you control token handling
- the page definitely runs inside HA or a trusted same-origin container

Risks:
- more auth logic in frontend
- easier to break with session or token drift
- harder to layer license rules, permissions, or domain-specific validation

## Device acquisition rules

- Classify by `domain` from `entity_id` first.
- Prefer `friendly_name` for display, never for identity.
- Use `entity_id` as the stable control key.
- Exclude telemetry-only entities from actionable lists: temperature, humidity, motion, smoke, water, status, and helper entities unless the feature explicitly needs them.
- Keep `device_tracker` separate from controllable devices; use it as presence or machine-online data.
- Use `group.*` only as a hint for grouping, not as the only source of structure.

## When to add backend endpoints

Add a new `HomeAssistantView` when:
- the frontend needs filtered or aggregated data that should not be recomputed in every browser
- the frontend needs registry data such as `device_id`, `area_id`, or `config_entry_id`
- the frontend must write files, save blueprints, or mutate HA config
- the frontend must hide secrets or enforce business rules

## Output requirements

When using this skill, produce concrete technical artifacts:
- route contract
- auth mode
- entity schema
- reconnect and fallback logic
- matching rules
- exact files to change
- residual risks if HA runtime validation was not possible

Do not spend time on visual design unless the user explicitly asks for it.
