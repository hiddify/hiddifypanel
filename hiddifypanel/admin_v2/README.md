# Hiddify Admin V2

Vue 3 + PrimeVue dashboard for custom proxy management.

## Paths

- Source: `hiddify-panel/src/hiddifypanel/admin_v2/`
- Production build output: `hiddify-panel/src/hiddifypanel/static/admin-v2/`
- Flask shell: `/<proxy_path>/admin_v2/` (proxy_path is random per installation)

## proxy_path (no fixed value)

`proxy_path_admin` is generated randomly per panel. The UI never hardcodes it.

| Mode | How API base is resolved |
|------|--------------------------|
| **Production** (Flask shell) | Relative `../api/v2/admin/` — works with any proxy_path |
| **Vite dev** | `GET /__admin_v2_bootstrap` → returns `{ proxy_path, api_base }` |
| **Dev override** | URL query `?proxy_path=YOUR_PATH` or `?pp=YOUR_PATH` |
| **Cached** | `sessionStorage` after first successful bootstrap |

## Development

1. Start Flask panel (port `9000` by default).
2. Run Vite:

```bash
cd hiddify-panel/src/hiddifypanel/admin_v2
bash scripts/dev.sh
```

3. Open http://127.0.0.1:5173/ — proxy_path is fetched automatically from the running panel.

Optional: copy your proxy_path from the admin URL and open  
`http://127.0.0.1:5173/?proxy_path=YOUR_RANDOM_PATH`

## VS Code / Cursor

- **Admin V2: Vite Dev** — frontend (uses `scripts/dev.sh`, no npm in PATH required)
- **Admin V2 (Flask + Vite)** — panel + hot reload UI

## Production build

Translations live only in `hiddifypanel/translations.i18n/` (Admin V2 uses the `adminV2` section at build time).

```bash
./build.sh
```
