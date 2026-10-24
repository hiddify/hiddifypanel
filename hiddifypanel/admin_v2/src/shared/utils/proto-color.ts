/** One recognisable color per proxy protocol, so a long list can be scanned by color. */
const PROTO_COLORS: Record<string, string> = {
  vless: '#2563eb',
  vmess: '#7c3aed',
  trojan: '#e11d48',
  shadowsocks: '#0d9488',
  ss: '#0d9488',
  hysteria: '#ea580c',
  hysteria2: '#f59e0b',
  tuic: '#db2777',
  wireguard: '#16a34a',
  wg: '#16a34a',
  ssh: '#475569',
  socks: '#0891b2',
  http: '#0ea5e9',
  mieru: '#84cc16',
  naive: '#a855f7',
  anytls: '#ef4444',
}

/** Stable color for any protocol name; unknown ones get a hue from their name. */
export function protoColor(proto: string | null | undefined): string {
  const key = String(proto ?? '').toLowerCase()
  if (PROTO_COLORS[key]) return PROTO_COLORS[key]
  let hash = 0
  for (const ch of key) hash = (hash * 31 + ch.charCodeAt(0)) % 360
  return `hsl(${hash} 65% 48%)`
}

/** Tag style: tinted background, readable text in light and dark themes. */
export function protoTagStyle(proto: string | null | undefined): Record<string, string> {
  const c = protoColor(proto)
  return {
    background: `color-mix(in srgb, ${c} 16%, transparent)`,
    color: `color-mix(in srgb, ${c} 82%, var(--p-text-color))`,
    border: `1px solid color-mix(in srgb, ${c} 38%, transparent)`,
  }
}

/**
 * Proxy categories: one named after a protocol (vless, ss, http, telegram…) has that protocol's color, as in the
 * Protocol column; the others have their own, each different from the protocols' and from one another's.
 */
const CATEGORY_COLORS: Record<string, string> = {
  additional_config: '#3f6212',
  custom: '#854d0e',
  'down:http': '#9f1239',
  'down:quic': '#0369a1',
  'down:tls_h1': '#86198f',
  'down:tls_h2': '#3730a3',
  faketls: '#065f46',
  grpc: '#78716c',
  httpupgrade: '#10b981',
  node_configs: '#b45309',
  quic: '#3b82f6',
  reality: '#65a30d',
  shadowtls: '#44403c',
  sni: '#d97706',
  tcp: '#15803d',
  telegram_faketls: '#991b1b',
  telegram_web: '#6b21a8',
  tls: '#eab308',
  udp: '#4d7c0f',
  'up:http': '#ca8a04',
  'up:quic': '#d946ef',
  'up:tls_h1': '#166534',
  'up:tls_h2': '#059669',
  user_configs: '#155e75',
  ws: '#14b8a6',
  xhttp: '#22c55e',
}

export function categoryColor(category: string | null | undefined): string {
  const key = String(category ?? '').toLowerCase()
  return CATEGORY_COLORS[key] ?? protoColor(key)
}

export function categoryTagStyle(category: string | null | undefined): Record<string, string> {
  const c = categoryColor(category)
  return {
    background: `color-mix(in srgb, ${c} 16%, transparent)`,
    color: `color-mix(in srgb, ${c} 82%, var(--p-text-color))`,
    border: `1px solid color-mix(in srgb, ${c} 38%, transparent)`,
  }
}
