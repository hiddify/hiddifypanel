/**
 * The DNS servers offered for the "DNS server" setting (General), in three groups. The setting keeps the chosen IPs
 * separated by commas ("1.1.1.1,1.0.0.1"): the server uses them for its own DNS and its cores.
 */
export interface DnsPreset {
  /** Unique in the list (a provider can be in more than one group) */
  id: string
  name: string
  ips: [string, string]
}

export interface DnsGroup {
  id: 'normal' | 'adblock' | 'family'
  icon: string
  color: string
  presets: DnsPreset[]
}

export const DNS_GROUPS: DnsGroup[] = [
  {
    id: 'normal',
    icon: 'pi pi-globe',
    color: '#0ea5e9',
    presets: [
      { id: 'cloudflare', name: 'Cloudflare', ips: ['1.1.1.1', '1.0.0.1'] },
      { id: 'google', name: 'Google', ips: ['8.8.8.8', '8.8.4.4'] },
      { id: 'quad9', name: 'Quad9', ips: ['9.9.9.9', '149.112.112.112'] },
      { id: 'opendns', name: 'OpenDNS', ips: ['208.67.222.222', '208.67.220.220'] },
      { id: 'controld', name: 'Control D', ips: ['76.76.2.0', '76.76.10.0'] },
    ],
  },
  {
    id: 'adblock',
    icon: 'pi pi-ban',
    color: '#f97316',
    presets: [
      { id: 'adguard', name: 'AdGuard DNS', ips: ['94.140.14.14', '94.140.15.15'] },
      { id: 'controld-ads', name: 'Control D', ips: ['76.76.2.2', '76.76.10.2'] },
      { id: 'comodo', name: 'Comodo Secure DNS', ips: ['8.26.56.26', '8.20.247.20'] },
    ],
  },
  {
    id: 'family',
    icon: 'pi pi-shield',
    color: '#22c55e',
    presets: [
      { id: 'adguard-family', name: 'AdGuard Family', ips: ['94.140.14.15', '94.140.15.16'] },
      { id: 'controld-family', name: 'Control D', ips: ['76.76.2.4', '76.76.10.4'] },
    ],
  },
]

/** "1.1.1.1, 1.0.0.1" → ["1.1.1.1", "1.0.0.1"] */
export function dnsList(value: string): string[] {
  return value
    .split(/[\s,;]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

/** The preset the value is made of (both IPs in either order, or only one of them, like the old default "1.1.1.1") */
export function presetOf(value: string): DnsPreset | null {
  const ips = dnsList(value)
  if (!ips.length) return null
  for (const g of DNS_GROUPS) for (const p of g.presets) if (ips.every((ip) => p.ips.includes(ip))) return p
  return null
}

const IPV4 = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/
const IPV6 = /^[0-9a-f:]+$/i

/** One to four IP addresses (IPv4 or IPv6) */
export function isDnsValue(value: string): boolean {
  const list = dnsList(value)
  return list.length > 0 && list.length <= 4 && list.every((ip) => IPV4.test(ip) || (ip.includes(':') && IPV6.test(ip)))
}
