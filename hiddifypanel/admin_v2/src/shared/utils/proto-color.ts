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
