# Preset templates

Files under `**/presets/` are **not** synced to the `proxy_template` database table.

## Purpose

Presets are composition shells used at **proxy generation time** by the template catalog builders (`inbound_builder`, `client_builder`). They stitch together smaller fragments from `protocols/`, `streams/`, `tls/`, and related folders into a full inbound or outbound block.

## Layout

```
{core}/{server|client}/presets/{name}.j2
```

Examples:

- `xray/server/presets/inbound.j2` — assembles a full xray server inbound from fragments
- `xray/client/presets/outbound_v2ray.j2` / `outbound_xhttp.j2` — xray client outbounds
- `hiddify-core/server/presets/inbound_v2ray.j2` — sing-box server inbound for vless/vmess/trojan
- `hiddify-core/client/presets/outbound_v2ray.j2` — client outbound for v2ray-compatible apps
- `clash/client/presets/outbound_general.j2` — Clash/Mihomo client proxy entry shell
- `singbox/client/presets/client_outbound.j2` — sing-box client outbound shell

## When to add a preset

Add a preset when you need a **reusable composition** referenced by `custom_proxy_presets` or builders, not a standalone editable template in the admin UI.

For admin-editable fragments, place `.j2` files outside `presets/` (e.g. `{core}/server/protocols/vless.j2`).

## Base configs vs presets vs templates

| Path pattern | Synced to DB | Table |
|---|---|---|
| `{core}/{client\|server}/base.j2` | Yes | `proxy_base_config` |
| `**/presets/**` | No | — (builder-only) |
| Other `.j2` | Yes | `proxy_template` |

New files under `proxy_templates/` are picked up automatically on the next builtin sync (`sync_all`).
