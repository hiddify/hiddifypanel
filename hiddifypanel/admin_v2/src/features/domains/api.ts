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
  ipv4: string[]
  ipv6: string[]
  ech_enabled: boolean
  cloudflare: boolean
  has_sublink: boolean
  default_tls_port: number
  default_http_port: number
  is_super_admin: boolean
  proxies: DomainProxy[]
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
  emoji: string
  mode: DomainMode
  /** Accent colour token. */
  color: string
  /** A guide for this mode. */
  link?: string
}

/** Modes offered when adding or editing (Cloudflare Worker is only shown for domains that already use it). */
export const KINDS: DomainKind[] = ['direct', 'cdn', 'relay', 'sublink']

export const KIND_META: Record<DomainKind, KindMeta> = {
  direct: { emoji: '➡️', mode: 'direct', color: 'var(--p-green-500, #22c55e)' },
  cdn: { emoji: '🔀', mode: 'cdn', color: 'var(--p-orange-500, #f97316)' },
  relay: { emoji: '♾️', mode: 'relay', color: 'var(--p-cyan-500, #06b6d4)', link: 'https://github.com/hiddify/hiddify-config/discussions/129' },
  worker: { emoji: '✴️', mode: 'worker', color: 'var(--p-amber-500, #f59e0b)' },
  sublink: { emoji: '🔗', mode: 'sub_link_only', color: 'var(--p-blue-500, #3b82f6)' },
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
export const FAKE_PROXY_MODES: TlsMode[] = ['telegram', 'shadowtls', 'ssfaketls']

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
