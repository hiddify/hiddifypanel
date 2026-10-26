import { getHttp } from '@/core/api/client'
import type { RestartMode } from '@/shared/utils/restart-mode'

export type DomainMode = 'direct' | 'sub_link_only' | 'cdn' | 'relay' | 'worker'
export type TlsMode = 'valid' | 'fake' | 'reality' | 'dns' | 'telegram' | 'shadowtls' | 'ssfaketls'
export type TlsStatus = 'valid' | 'self_signed' | 'expired' | 'invalid' | 'missing'

/** The mode as the page shows it (the TLS mode, valid / fake / Reality, is chosen separately). */
export type DomainKind = 'direct' | 'cdn' | 'relay' | 'worker' | 'sublink'

export interface CertJob {
  state: 'running' | 'done' | 'failed'
  started?: number
  finished?: number
  error?: string
  /** Every CA refused because of its rate limits (a self-signed certificate is used meanwhile). */
  rate_limited?: boolean
  /** The CA that issued it ('letsencrypt' / 'zerossl'). */
  ca?: string
}

export interface DomainTls {
  status: TlsStatus
  /** The domain needs a real certificate (valid TLS mode). */
  needs_valid: boolean
  issuer: string
  expires_at: string | null
  updated_at: string | null
  error: string
  /** The last certificate request from this page (kept for 10 minutes). */
  job: CertJob | null
}

export interface DomainRow {
  id: number
  domain: string
  alias: string
  mode: DomainMode
  fake_mode: TlsMode
  sort_order: number | null
  custom_proxy_ids: number[]
  /** Sub-link domains: whose configs they show. Empty = every domain. */
  show_domain_ids: number[]
  server_domain_id: number | null
  download_domain_id: number | null
  cdn_ip: string
  resolve_ip: boolean
  ech: boolean
  servernames: string
  extra_params: string
  /** Null = the default 443 / 80. */
  tls_port: number | null
  http_port: number | null
  tls: DomainTls
  /** Admin panel through this domain (none for decoy domains). */
  panel_link: string | null
}

export interface DomainProxy {
  id: number
  name: string
  slug: string
  /** sni: SNI gateway; l7: L7 gateway; ip: IP based (its own public ports). */
  kind: 'sni' | 'l7' | 'ip'
  group: string
  enabled: boolean
  reality: boolean
}

export interface DomainsMeta {
  ech_enabled: boolean
  cloudflare: boolean
  has_sublink: boolean
  default_tls_port: number
  default_http_port: number
  is_super_admin: boolean
  proxies: DomainProxy[]
  /** This server's public addresses: what a new domain's DNS record should point to. */
  server_ips?: { ip: string; version: 4 | 6; label: string }[]
}

/** Per-domain trick mode for the TLS Fragment template. */
export type TlsFragmentMode = 'on' | 'off'

export interface FragmentSettings {
  packets: string
  lengths: string[]
  delays: string[]
  maxSplit: string
}

/** ``extra_params.tricks``. */
export function tricksOf(extra: Record<string, unknown> | null | undefined): Record<string, unknown> {
  const tricks = extra?.tricks
  return tricks && typeof tricks === 'object' && !Array.isArray(tricks) ? { ...(tricks as Record<string, unknown>) } : {}
}

function asStrList(value: unknown, fallback: string[]): string[] {
  if (typeof value === 'string') {
    const parts = value
      .split(/[,;]+/)
      .map((p) => p.trim())
      .filter(Boolean)
    return parts.length ? parts : [...fallback]
  }
  if (Array.isArray(value)) {
    const parts = value.map((p) => String(p).trim()).filter(Boolean)
    return parts.length ? parts : [...fallback]
  }
  return [...fallback]
}

function buildFragmentFinalmask(frag: Record<string, unknown>): Record<string, unknown> {
  return {
    tcp: [
      {
        type: 'fragment',
        settings: {
          packets: String(frag.packets || 'tlshello').trim() || 'tlshello',
          lengths: asStrList(frag.lengths ?? frag.size, ['10-100']),
          delays: asStrList(frag.delays ?? frag.sleep, ['50-200']),
          maxSplit: String(frag.maxSplit || frag.max_split || '3-6').trim() || '3-6',
        },
      },
    ],
  }
}

/** Read TLS Fragment settings from ``tricks.finalmask.tcp`` (or legacy shapes). */
export function fragmentSettingsOf(extra: Record<string, unknown> | null | undefined): FragmentSettings | null {
  if (!extra) return null
  const tricks = tricksOf(extra)
  const fm = (tricks.finalmask ?? extra.finalmask) as Record<string, unknown> | undefined
  if (fm && typeof fm === 'object' && !Array.isArray(fm)) {
    const tcp = fm.tcp
    if (Array.isArray(tcp)) {
      for (const layer of tcp) {
        if (!layer || typeof layer !== 'object' || Array.isArray(layer)) continue
        const item = layer as Record<string, unknown>
        if (String(item.type || '').toLowerCase() !== 'fragment') continue
        const settings = item.settings && typeof item.settings === 'object' && !Array.isArray(item.settings) ? (item.settings as Record<string, unknown>) : {}
        return {
          packets: String(settings.packets || 'tlshello'),
          lengths: asStrList(settings.lengths, ['10-100']),
          delays: asStrList(settings.delays, ['50-200']),
          maxSplit: String(settings.maxSplit || settings.max_split || '3-6'),
        }
      }
    }
    if (String(fm.type || '').toLowerCase() === 'fragment') {
      const settings = fm.settings && typeof fm.settings === 'object' && !Array.isArray(fm.settings) ? (fm.settings as Record<string, unknown>) : {}
      return {
        packets: String(settings.packets || 'tlshello'),
        lengths: asStrList(settings.lengths, ['10-100']),
        delays: asStrList(settings.delays, ['50-200']),
        maxSplit: String(settings.maxSplit || settings.max_split || '3-6'),
      }
    }
  }
  const legacy = (tricks.tls_fragment ?? extra.tls_fragment) as Record<string, unknown> | undefined
  if (legacy && typeof legacy === 'object' && !Array.isArray(legacy) && (legacy.packets || legacy.lengths || legacy.size)) {
    return {
      packets: String(legacy.packets || 'tlshello'),
      lengths: asStrList(legacy.lengths ?? legacy.size, ['10-100']),
      delays: asStrList(legacy.delays ?? legacy.sleep, ['50-200']),
      maxSplit: String(legacy.maxSplit || legacy.max_split || '3-6'),
    }
  }
  return null
}

/** @deprecated use fragmentSettingsOf */
export function tlsFragmentOf(extra: Record<string, unknown> | null | undefined): Record<string, unknown> | null {
  const s = fragmentSettingsOf(extra)
  return s ? { ...s, mode: 'on' } : null
}

/** Raw FinalMask object from ``tricks.finalmask`` (or legacy top-level). */
export function finalmaskOf(extra: Record<string, unknown> | null | undefined): Record<string, unknown> | null {
  if (!extra) return null
  const tricks = tricksOf(extra)
  for (const candidate of [tricks.finalmask, extra.finalmask]) {
    if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) return { ...(candidate as Record<string, unknown>) }
  }
  return null
}

/** True when FinalMask is a single TCP fragment layer (the TLS Fragment template). */
export function isSimpleTlsFragmentFinalmask(fm: Record<string, unknown> | null | undefined): boolean {
  if (!fm) return false
  const keys = Object.keys(fm).filter((k) => fm[k] != null && !(Array.isArray(fm[k]) && !(fm[k] as unknown[]).length))
  if (keys.some((k) => k !== 'tcp')) return false
  const tcp = fm.tcp
  if (!Array.isArray(tcp) || tcp.length !== 1) return false
  const layer = tcp[0]
  if (!layer || typeof layer !== 'object' || Array.isArray(layer)) return false
  return String((layer as Record<string, unknown>).type || '').toLowerCase() === 'fragment'
}

/** Which tricks UI template is active for this domain. */
export function trickTemplateOf(extra: Record<string, unknown> | null | undefined): 'off' | 'tls_fragment' | 'custom' {
  if (!extra) return 'off'
  const tricks = tricksOf(extra)
  const named = String(tricks.template || '').toLowerCase()
  if (named === 'custom') return 'custom'
  if (named === 'tls_fragment') return 'tls_fragment'
  const fm = finalmaskOf(extra)
  if (!fm) {
    if (tricks.tls_fragment || extra.tls_fragment) return 'tls_fragment'
    return 'off'
  }
  return isSimpleTlsFragmentFinalmask(fm) ? 'tls_fragment' : 'custom'
}

/** Write / clear the TLS Fragment trick as ``tricks.finalmask`` (FinalMaskObject). */
export function setTlsFragmentInExtra(extra: Record<string, unknown>, frag: Record<string, unknown> | null): Record<string, unknown> {
  const obj: Record<string, unknown> = { ...extra }
  const tricks = tricksOf(obj)
  delete obj.finalmask
  delete obj.tls_fragment
  delete tricks.tls_fragment

  if (frag === null || String(frag.mode || '').toLowerCase() === 'off') {
    delete tricks.template
    delete tricks.finalmask
  } else {
    tricks.template = 'tls_fragment'
    tricks.finalmask = buildFragmentFinalmask(frag)
  }
  if (Object.keys(tricks).length) obj.tricks = tricks
  else delete obj.tricks
  return obj
}

/** Write a custom FinalMask object (or clear tricks). */
export function setCustomFinalmaskInExtra(extra: Record<string, unknown>, finalmask: Record<string, unknown> | null): Record<string, unknown> {
  const obj: Record<string, unknown> = { ...extra }
  const tricks = tricksOf(obj)
  delete obj.finalmask
  delete obj.tls_fragment
  delete tricks.tls_fragment

  if (!finalmask || !Object.keys(finalmask).length) {
    delete tricks.template
    delete tricks.finalmask
  } else {
    tricks.template = 'custom'
    tricks.finalmask = finalmask
  }
  if (Object.keys(tricks).length) obj.tricks = tricks
  else delete obj.tricks
  return obj
}

/** Whether ``extra_params`` has any tricks / finalmask worth opening Advanced for. */
export function hasDomainTricks(extra: Record<string, unknown> | null | undefined): boolean {
  return trickTemplateOf(extra) !== 'off'
}

/** Loaded separately, after the page: only the edit dialog (and the names of shown domains) need it. */
export interface DomainsOptions {
  /** Domains whose configs a domain can show: this panel's and its nodes' (`node` = the node's name). */
  show_options: { id: number; domain: string; alias: string; mode: DomainMode; fake_mode: TlsMode; node: string | null }[]
  /** `mode:fake_mode` → ids of the custom proxies that fit that kind of domain. */
  compatible: Record<string, number[]>
}

export interface DomainsState {
  domains: DomainRow[]
  meta: DomainsMeta
  restart_mode?: RestartMode
  warnings?: string[]
  created_id?: number
  certificate_requested?: boolean
}

export interface DomainPayload {
  domain?: string
  alias?: string
  mode?: DomainMode
  fake_mode?: TlsMode
  custom_proxy_ids?: number[]
  show_domain_ids?: number[]
  server_domain_id?: number | null
  download_domain_id?: number | null
  cdn_ip?: string
  resolve_ip?: boolean
  ech?: boolean
  servernames?: string
  extra_params?: string
  tls_port?: number | null
  http_port?: number | null
}

/** What detection guessed (same as quick setup). */
export interface DomainDetection {
  domain: string
  mode: 'direct' | 'cdn' | 'reality' | 'unresolved'
  cdn: string | null
  ips: string[]
  reason: 'server_ip' | 'cdn_range' | 'cdn_asn' | 'cdn_header' | 'external' | 'no_dns'
  reality_friendly: boolean | null
  already_added: boolean
}

export interface PortCheck {
  port: number
  kind: 'tls' | 'http'
  ok: boolean
  /** reserved: another service or proxy uses it; busy: another program listens on it; unknown: could not check. */
  code?: 'invalid' | 'reserved' | 'busy' | 'unknown'
  detail?: string
}

export const domainsApi = {
  async list(): Promise<DomainsState> {
    const { data } = await getHttp().get<DomainsState>('domains-page/')
    return data
  },
  async options(): Promise<DomainsOptions> {
    const { data } = await getHttp().get<DomainsOptions>('domains-page/options/')
    return data
  },
  async create(payload: DomainPayload): Promise<DomainsState> {
    // Saving checks DNS (and Cloudflare): give it time.
    const { data } = await getHttp().post<DomainsState>('domains-page/', payload, { timeout: 60_000 })
    return data
  },
  async update(id: number, payload: DomainPayload): Promise<DomainsState> {
    const { data } = await getHttp().patch<DomainsState>(`domains-page/${id}/`, payload, { timeout: 60_000 })
    return data
  },
  async remove(id: number): Promise<DomainsState> {
    const { data } = await getHttp().delete<DomainsState>(`domains-page/${id}/`, { timeout: 30_000 })
    return data
  },
  async reorder(ids: number[]): Promise<DomainsState> {
    const { data } = await getHttp().put<DomainsState>('domains-page/order/', { ids })
    return data
  },
  async detect(domain: string): Promise<DomainDetection> {
    const { data } = await getHttp().post<DomainDetection>('domains-page/detect/', { domain }, { timeout: 20_000 })
    return data
  },
  async certificate(id: number): Promise<DomainTls> {
    const { data } = await getHttp().get<DomainTls>(`domains-page/${id}/certificate/`)
    return data
  },
  async requestCertificate(id: number): Promise<DomainTls> {
    const { data } = await getHttp().post<DomainTls>(`domains-page/${id}/certificate/`)
    return data
  },
  async checkPort(kind: 'tls' | 'http', port: number, domainId?: number | null): Promise<PortCheck> {
    const { data } = await getHttp().get<PortCheck>('domains-page/port-check/', { params: { kind, port, domain_id: domainId ?? undefined }, timeout: 20_000 })
    return data
  },
}

export interface KindMeta {
  /** Shown in config names (the alias suggestions) */
  emoji: string
  /** The type's icon on the page (PrimeIcons) */
  icon: string
  mode: DomainMode
  /** Accent colour token. */
  color: string
  /** A guide for this mode. */
  link?: string
}

/** Modes offered when adding or editing (Cloudflare Worker is only shown for domains that already use it). */
export const KINDS: DomainKind[] = ['direct', 'cdn', 'relay', 'sublink']

export const KIND_META: Record<DomainKind, KindMeta> = {
  direct: { emoji: '➡️', icon: 'pi pi-server', mode: 'direct', color: 'var(--p-green-500, #22c55e)' },
  cdn: { emoji: '🔀', icon: 'pi pi-cloud', mode: 'cdn', color: 'var(--p-orange-500, #f97316)' },
  relay: { emoji: '♾️', icon: 'pi pi-arrow-right-arrow-left', mode: 'relay', color: 'var(--p-cyan-500, #06b6d4)', link: 'https://github.com/hiddify/hiddify-config/discussions/129' },
  worker: { emoji: '✴️', icon: 'pi pi-bolt', mode: 'worker', color: 'var(--p-amber-500, #f59e0b)' },
  sublink: { emoji: '🔗', icon: 'pi pi-link', mode: 'sub_link_only', color: 'var(--p-blue-500, #3b82f6)' },
}

export function kindOf(mode: DomainMode): DomainKind {
  return mode === 'sub_link_only' ? 'sublink' : mode
}

/** Only direct and relay domains choose their TLS mode; the others always use a real certificate. */
export function tlsModeSelectable(mode: DomainMode): boolean {
  return mode === 'direct' || mode === 'relay'
}

/** TLS modes offered (DNS only when a domain already has it). */
export const TLS_MODES: TlsMode[] = ['valid', 'fake', 'reality']

/** Fake-TLS front domains of the Telegram / ShadowTLS / SS FakeTLS servers: one each, no custom proxies or download domain. */
/** Domains that mirror a fake-TLS front setting: none any more (Telegram / ShadowTLS / SS FakeTLS are SNI proxies). */
export const FAKE_PROXY_MODES: TlsMode[] = []

export function isFakeProxyMode(mode: TlsMode): boolean {
  return FAKE_PROXY_MODES.includes(mode)
}

export const TLS_ICON: Record<TlsStatus, string> = {
  valid: 'pi pi-verified',
  self_signed: 'pi pi-exclamation-circle',
  expired: 'pi pi-clock',
  invalid: 'pi pi-times-circle',
  missing: 'pi pi-minus-circle',
}

/** What the detected setup suggests (for the add wizard). */
export function suggestedSetup(found: DomainDetection | null): { kind: DomainKind; tls: TlsMode } {
  if (!found) return { kind: 'direct', tls: 'valid' }
  if (found.domain.startsWith('*.')) return { kind: 'cdn', tls: 'valid' }
  if (found.mode === 'cdn') return { kind: 'cdn', tls: 'valid' }
  if (found.mode === 'reality') return { kind: 'direct', tls: 'reality' }
  if (found.mode === 'unresolved') return { kind: 'direct', tls: 'fake' }
  return { kind: 'direct', tls: 'valid' }
}

/** Does this mode (with this TLS mode) fit what DNS says? */
export function kindFitsDetection(kind: DomainKind, tls: TlsMode, found: DomainDetection | null): 'good' | 'ok' | 'bad' {
  if (!found) return 'ok'
  const m = found.mode
  const decoy = tlsModeSelectable(KIND_META[kind].mode) && tls !== 'valid'
  switch (kind) {
    case 'direct':
      if (decoy) return tls === 'reality' ? (m === 'reality' ? (found.reality_friendly === false ? 'ok' : 'good') : m === 'unresolved' ? 'bad' : 'ok') : 'ok'
      return m === 'direct' ? 'good' : 'bad'
    case 'sublink':
      return m === 'direct' || m === 'cdn' ? 'ok' : 'bad'
    case 'cdn':
    case 'worker':
      return m === 'cdn' ? 'good' : 'bad'
    case 'relay':
      return m === 'direct' ? 'bad' : 'ok'
  }
}

export const CERT_WAIT_SECONDS = 60
