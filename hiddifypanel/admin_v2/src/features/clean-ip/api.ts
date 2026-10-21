import { getHttp } from '@/core/api/client'

/** The network (ISP) this page is opened from, as the panel sees it. */
export interface CleanIpNetwork {
  ip: string
  asn: string
  org: string
  country: string
  /** Hiddify's ISP name used in the CDN IP field ("MCI", "MTN", …); "unknown" when it has none. */
  short_name: string
  short_names: string[]
  panel_country: string
  db_available: boolean
}

/** A one-day command for the full test (with upload), run on a computer / phone on the ISP to test. */
export interface CleanIpCommand {
  token: string
  expires_in: number
  script_url: string
  commands: { unix: string; windows: string }
}

/** What a run of that command sent back (saved for `short_name` when Hiddify knows the ISP). */
export interface CleanIpReport {
  at: number
  short_name: string
  asn: string
  org: string
  country: string
  tested: number
  size: number
  ips: { ip: string; ms: number; colo: string }[]
  saved: string[]
}

/** A REALITY SNI's status per ISP (from full tests run in Iran). */
export type SniStatus = Record<string, { ok: boolean; at: number }>
export interface RealityState {
  domains: { id: number; sni: string; status: SniStatus }[]
  spares: { sni: string; status: SniStatus }[]
  auto: boolean
  events: { at: number; isp: string; old: string; new: string; auto: boolean }[]
}

export const cleanIpApi = {
  async reality(): Promise<RealityState> {
    const { data } = await getHttp().get<RealityState>('clean-ip/reality/')
    return data
  },
  async saveReality(spares: string[], auto: boolean): Promise<RealityState> {
    const { data } = await getHttp().put<RealityState>('clean-ip/reality/', { spares, auto })
    return data
  },
  async switchSni(domainId: number, sni: string): Promise<RealityState> {
    // the server first tests a real REALITY connection through the site, then applies the configs
    const { data } = await getHttp().post<RealityState>(`clean-ip/reality/${domainId}/switch/`, { sni }, { timeout: 60_000 })
    return data
  },
  async network(): Promise<CleanIpNetwork> {
    const { data } = await getHttp().get<CleanIpNetwork>('clean-ip/network/')
    return data
  },
  async command(payload: { domain_id: number; size: number; per_range: number; per_isp: number }): Promise<CleanIpCommand> {
    const { data } = await getHttp().post<CleanIpCommand>('clean-ip/token/', payload)
    return data
  },
  async reports(token: string): Promise<CleanIpReport[]> {
    const { data } = await getHttp().get<{ reports: CleanIpReport[] }>(`clean-ip/token/${token}/`)
    return data.reports
  },
}

/** Cloudflare's published IPv4 ranges (https://www.cloudflare.com/ips-v4/). */
export const CLOUDFLARE_RANGES = [
  '173.245.48.0/20',
  '103.21.244.0/22',
  '103.22.200.0/22',
  '103.31.4.0/22',
  '141.101.64.0/18',
  '108.162.192.0/18',
  '190.93.240.0/20',
  '188.114.96.0/20',
  '197.234.240.0/22',
  '198.41.128.0/17',
  '162.158.0.0/15',
  '104.16.0.0/13',
  '104.24.0.0/14',
  '172.64.0.0/13',
  '131.0.72.0/22',
]

/** `count` random host addresses of a CIDR range (no network / broadcast address). */
export function randomIps(cidr: string, count: number): string[] {
  const [base, bits] = cidr.split('/')
  const prefix = Number(bits)
  const start = base.split('.').reduce((acc, part) => acc * 256 + Number(part), 0)
  const size = 2 ** (32 - prefix)
  const out = new Set<string>()
  for (let tries = 0; out.size < Math.min(count, size - 2) && tries < count * 20; tries++) {
    const n = start + 1 + Math.floor(Math.random() * (size - 2))
    out.add([24, 16, 8, 0].map((shift) => Math.floor(n / 2 ** shift) % 256).join('.'))
  }
  return [...out]
}

/**
 * Whether this browser reaches the IP over TLS, and how fast. A browser can not pick the TLS name for an IP, so the
 * answer is a TLS error: a quick error means the IP answers; no answer before the timeout means it is blocked on this
 * network (tested against a real upload test: 58 of 60 IPs got the same result).
 */
export async function probeIp(ip: string, timeoutMs: number): Promise<{ ok: boolean; ms: number }> {
  const ctl = new AbortController()
  const timer = window.setTimeout(() => ctl.abort(), timeoutMs)
  const t0 = performance.now()
  try {
    await fetch(`https://${ip}/cdn-cgi/trace?r=${Math.random().toString(36).slice(2)}`, {
      mode: 'no-cors',
      cache: 'no-store',
      credentials: 'omit',
      signal: ctl.signal,
    })
  } catch {
    // TLS error (the IP answered) or the abort (it did not)
  } finally {
    window.clearTimeout(timer)
  }
  const ms = Math.round(performance.now() - t0)
  return { ok: !ctl.signal.aborted && ms < timeoutMs, ms }
}

/**
 * The CDN IP field with this ISP's pairs replaced by `ips` and the other ISPs' pairs kept. A value without ISP names
 * (a plain IP list) can not be mixed with pairs: it is replaced (`dropped`).
 */
export function mergeCdnIp(current: string, short: string, ips: string[], known: string[]) {
  const lines = ips.map((ip) => `${ip} ${short}`)
  const tokens = (current || '').trim().split(/[\s;,]+/).filter(Boolean)
  let kept = 0
  let dropped = false
  if (tokens.length) {
    if (tokens.length % 2 === 0 && tokens.some((x) => known.includes(x))) {
      for (let i = 0; i < tokens.length; i += 2) {
        if (tokens[i + 1] !== short) {
          lines.push(`${tokens[i]} ${tokens[i + 1]}`)
          kept++
        }
      }
    } else {
      dropped = true
    }
  }
  return { text: lines.join('\n'), kept, dropped }
}
