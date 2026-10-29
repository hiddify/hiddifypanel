/**
 * Protocol names as the panel writes them (the server's ProxyProto values → their own spelling), e.g. "vless" →
 * "VLess", "hysteria2" → "Hysteria 2". Used wherever a protocol is shown; an unknown one is shown as it comes.
 */
export const PROTOCOL_NAMES: Record<string, string> = {
  vless: 'VLess',
  trojan: 'Trojan',
  vmess: 'VMess',
  shadowsocks: 'Shadowsocks',
  socks: 'Socks',
  v2ray: 'V2Ray',
  ssr: 'SSR',
  ssh: 'SSH',
  tuic: 'TUIC',
  hysteria: 'Hysteria',
  hysteria2: 'Hysteria 2',
  wireguard: 'WireGuard',
  naive: 'Naive',
  mieru: 'Mieru',
  anytls: 'AnyTLS',
  dnstt: 'DNSTT',
  slipstream: 'Slipstream',
  masterdns: 'MasterDNS',
  snell: 'Snell',
  telegram: 'Telegram',
}

export function protocolName(proto: string | null | undefined): string {
  if (!proto) return '—'
  return PROTOCOL_NAMES[proto.toLowerCase()] ?? proto
}

/** A share link's scheme ("ss", "hy2", "wg", "socks5", "naive+https"…) → the protocol's name; the scheme when unknown. */
const SCHEME_PROTOCOL: Record<string, string> = {
  ss: 'shadowsocks',
  hy2: 'hysteria2',
  wg: 'wireguard',
  socks5: 'socks',
  socks4: 'socks',
  'naive+https': 'naive',
  'naive+quic': 'naive',
}
export function schemeName(scheme: string): string {
  const s = scheme.toLowerCase()
  return PROTOCOL_NAMES[SCHEME_PROTOCOL[s] ?? s] ?? s
}

/**
 * Proxy categories (tags) as the panel writes them: the built-in ones by name ("down:tls_h1" → "Down:TLS_H1",
 * "node_configs" → "Node Configs"); one an admin typed is shown as written. The stored value does not change.
 */
export const CATEGORY_NAMES: Record<string, string> = {
  additional_config: 'Additional Config',
  anytls: 'AnyTLS',
  custom: 'Custom',
  dnstt: 'DNSTT',
  'down:http': 'Down:HTTP',
  'down:quic': 'Down:QUIC',
  'down:tls_h1': 'Down:TLS_H1',
  'down:tls_h2': 'Down:TLS_H2',
  faketls: 'FakeTLS',
  grpc: 'gRPC',
  http: 'HTTP',
  httpupgrade: 'HTTPUpgrade',
  hysteria: 'Hysteria',
  hysteria2: 'Hysteria 2',
  masterdns: 'MasterDNS',
  mieru: 'Mieru',
  naive: 'Naive',
  node_configs: 'Node Configs',
  quic: 'QUIC',
  reality: 'Reality',
  shadowsocks: 'Shadowsocks',
  shadowtls: 'ShadowTLS',
  slipstream: 'Slipstream',
  snell: 'Snell',
  sni: 'SNI',
  ss: 'SS',
  ssh: 'SSH',
  tcp: 'TCP',
  telegram: 'Telegram',
  telegram_faketls: 'Telegram FakeTLS',
  telegram_web: 'Telegram Web',
  tls: 'TLS',
  trojan: 'Trojan',
  tuic: 'TUIC',
  udp: 'UDP',
  'up:http': 'UP:HTTP',
  'up:quic': 'UP:QUIC',
  'up:tls_h1': 'UP:TLS H1',
  'up:tls_h2': 'UP:TLS H2',
  user_configs: 'User Configs',
  v2ray: 'V2Ray',
  vless: 'VLess',
  vmess: 'VMess',
  wireguard: 'WireGuard',
  ws: 'WS',
  xhttp: 'XHTTP',
}

export function categoryName(category: string): string {
  return CATEGORY_NAMES[category.toLowerCase()] ?? PROTOCOL_NAMES[category.toLowerCase()] ?? category
}

/** Cores as the panel writes them ("hiddify-core" → "Hiddify Core", "xray" → "XRay"); another core as it comes. */
export const CORE_NAMES: Record<string, string> = {
  clash: 'Clash',
  dns_proxy: 'DNS Proxy',
  firewall: 'Firewall',
  haproxy: 'HAProxy',
  'hiddify-core': 'Hiddify Core',
  ip_scanner: 'IP Scanner',
  'rust-rpxy-l4': 'Rust-rpxy-L4',
  singbox: 'SingBox',
  sni_scanner: 'SNI Scanner',
  sublink: 'SubLink',
  telegram: 'Telegram',
  telemt: 'Telemt',
  wireguard: 'WireGuard',
  xray: 'XRay',
}

export function coreName(core: string | null | undefined): string {
  if (!core) return ''
  return CORE_NAMES[core.toLowerCase()] ?? core
}

/** A base config's side as a name ("server" → "Server"). */
export function sideName(side: string | null | undefined): string {
  if (!side) return ''
  return side.charAt(0).toUpperCase() + side.slice(1)
}
