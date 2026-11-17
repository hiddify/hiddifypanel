import { siHaproxy, siMysql, siRedis, siTelegram, siWireguard, type SimpleIcon } from 'simple-icons'

/**
 * What "Check Status" prints (scripts/status.sh in Hiddify-Manager), read back as data for the status details:
 *
 *   - Warp Status (usque):            (only when WARP is in use; services/warp/usque/status.sh)
 *     - Account:  <usque account info lines>
 *     - Network:  "country": "…", "city": "…", "org": "…", "query": "…"
 *   - Global IP:                       "country": "…", "city": "…", "org": "…", "query": "…"
 *   - Services Status:                 <unit>   <state>   (one per line)
 *
 * The text is the log without its colours. Anything else in it is ignored.
 */
export interface StatusPlace {
  country?: string
  city?: string
  org?: string
  /** the public address */
  query?: string
}
export interface StatusService {
  unit: string
  state: string
}
export interface StatusReport {
  ip: StatusPlace | null
  warp: { network: StatusPlace | null; account: string[] } | null
  services: StatusService[]
}

const KEY_VALUE = /"(\w+)"\s*:\s*"([^"]*)"/

export function parseStatus(text: string): StatusReport {
  const report: StatusReport = { ip: null, warp: null, services: [] }
  let section: 'none' | 'ip' | 'services' | 'warp-account' | 'warp-network' = 'none'
  let pendingUnit: string | null = null
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/\t/g, '    ')
    const trimmed = line.trim()
    if (!trimmed || /^-{8,}$/.test(trimmed)) {
      continue
    }
    if (/^- Global IP:/.test(trimmed)) {
      section = 'ip'
      report.ip ??= {}
      continue
    }
    if (/^- Services Status:/.test(trimmed)) {
      section = 'services'
      continue
    }
    if (/^- Warp Status/i.test(trimmed)) {
      report.warp ??= { network: null, account: [] }
      section = 'warp-account'
      continue
    }
    if (/^- Account:/.test(trimmed) && report.warp) {
      section = 'warp-account'
      continue
    }
    if (/^- Network:/.test(trimmed) && report.warp) {
      section = 'warp-network'
      report.warp.network ??= {}
      continue
    }
    const kv = KEY_VALUE.exec(trimmed)
    if (kv && (section === 'ip' || section === 'warp-network')) {
      const place = section === 'ip' ? report.ip! : report.warp!.network!
      place[kv[1] as keyof StatusPlace] = kv[2]
      continue
    }
    if (section === 'services') {
      // "hiddify-xray      active", or (a narrow terminal) the unit and its state on two lines
      const both = /^(\S+)\s+([a-z-]+)$/.exec(trimmed)
      if (both) {
        report.services.push({ unit: both[1]!, state: both[2]! })
        pendingUnit = null
      } else if (pendingUnit && /^[a-z-]+$/.test(trimmed)) {
        report.services.push({ unit: pendingUnit, state: trimmed })
        pendingUnit = null
      } else if (/^\S+$/.test(trimmed)) {
        pendingUnit = trimmed
      }
      continue
    }
    if (section === 'warp-account' && report.warp) report.warp.account.push(trimmed)
  }
  return report
}

/** A logo instead of a PrimeIcon (ServiceLogo.vue): a vendor's mark from Simple Icons, XRay's star, Hiddify's hexagon. */
export type ServiceLogoKind = SimpleIcon | 'xray' | 'hiddify-black' | 'hiddify-blue'

/** A unit's name for people, its logo (or icon) and colour. Units not listed keep their name. */
const SERVICES: { test: RegExp; name: string; icon: string; color: string; logo?: ServiceLogoKind }[] = [
  { test: /mysql|mariadb/, name: 'MySQL', icon: 'pi pi-database', color: '#4479a1', logo: siMysql },
  { test: /redis/, name: 'Redis', icon: 'pi pi-bolt', color: '#ff4438', logo: siRedis },
  { test: /hiddify-core|singbox/, name: 'Hiddify Core', icon: 'pi pi-box', color: '#1c1c1e', logo: 'hiddify-black' },
  { test: /xray/, name: 'XRay', icon: 'pi pi-star', color: '#1c1c1e', logo: 'xray' },
  { test: /haproxy/, name: 'HAProxy', icon: 'pi pi-sitemap', color: '#169bd6', logo: siHaproxy },
  { test: /panel/, name: 'Hiddify Panel', icon: 'pi pi-th-large', color: '#2563eb', logo: 'hiddify-blue' },
  // a reverse proxy takes the request and hands it on to the service behind it: two arrows, there and back
  { test: /rpxy/, name: 'Reverse Proxy (rpxy)', icon: 'pi pi-arrow-right-arrow-left', color: '#ff9f0a' },
  { test: /telegram/, name: 'Telegram Proxy', icon: 'pi pi-telegram', color: '#26a5e4', logo: siTelegram },
  { test: /warp|usque/, name: 'WARP', icon: 'pi pi-cloud', color: '#f48120' },
  { test: /wg-quick|wireguard/, name: 'WireGuard', icon: 'pi pi-shield', color: '#88171a', logo: siWireguard },
  { test: /nginx/, name: 'Nginx', icon: 'pi pi-server', color: '#34c759' },
  { test: /ssh/, name: 'SSH Proxy', icon: 'pi pi-key', color: '#8e8e93' },
  { test: /dns/, name: 'DNS', icon: 'pi pi-globe', color: '#64d2ff' },
]

export function serviceLook(unit: string): { name: string; icon: string; color: string; logo?: ServiceLogoKind } {
  const hit = SERVICES.find((s) => s.test.test(unit))
  return hit ? { name: hit.name, icon: hit.icon, color: hit.color, logo: hit.logo } : { name: unit.replace(/^hiddify-/, ''), icon: 'pi pi-cog', color: '#8e8e93' }
}

/** A country's ISO code from its English name (ip-api.com gives names), for its flag. */
let codes: Map<string, string> | null = null
export function countryCode(name: string | undefined): string | null {
  if (!name) return null
  if (!codes) {
    codes = new Map()
    try {
      const names = new Intl.DisplayNames(['en'], { type: 'region' })
      for (let a = 65; a <= 90; a++)
        for (let b = 65; b <= 90; b++) {
          const code = String.fromCharCode(a, b)
          const n = names.of(code)
          if (n && n !== code) codes.set(n.toLowerCase(), code)
        }
    } catch {
      /* no Intl.DisplayNames: no flag */
    }
  }
  return codes.get(name.toLowerCase()) ?? null
}
