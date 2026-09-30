import { getHttp } from '@/core/api/client'

export interface QuickSetupState {
  needs_setup: boolean
  /** This panel is a node of a parent (the "add nodes" step is skipped). */
  is_node: boolean
  admin_lang: string
  country: string
  languages: string[]
  countries: string[]
  ipv4: string
  ipv6: string
  /** Proxy domains with how each is used. */
  entries: DomainEntry[]
  /** Domains that only serve subscription links. */
  sublink_domains: string[]
  block_iran_sites: boolean
  decoy_domain: string
  /** Set after saving domains: non-blocking notes (e.g. a REALITY site without TLS 1.3 + h2). */
  warnings?: string[]
}

export type DomainMode = 'direct' | 'cdn' | 'reality' | 'relay'

export interface DomainEntry {
  domain: string
  mode: DomainMode
}

/** What the server guessed for a domain. `unresolved`: no DNS record (or an IP that is not this server). */
export interface DomainDetection {
  domain: string
  mode: DomainMode | 'unresolved'
  /** CDN provider name when mode is `cdn`, e.g. "Cloudflare". */
  cdn: string | null
  ips: string[]
  reason: 'server_ip' | 'cdn_range' | 'cdn_asn' | 'cdn_header' | 'external' | 'no_dns'
  reality_friendly: boolean | null
}

export interface DomainsInput {
  entries: DomainEntry[]
  sublink_domains: string[]
  block_iran_sites: boolean
  decoy_domain: string
}

/** 422 body of the domains step: an error per domain name. */
export interface DomainsErrorBody {
  errors?: string[]
  field_errors?: {
    entries?: Record<string, string>
    sublink_domains?: Record<string, string>
    /** No direct domain was given. */
    required?: boolean
    decoy_domain?: string | null
  }
}

export const quickSetupApi = {
  async state(): Promise<QuickSetupState> {
    const { data } = await getHttp().get<QuickSetupState>('quick-setup/')
    return data
  },
  async language(adminLang: string, country: string): Promise<{ reload: boolean }> {
    const { data } = await getHttp().put<{ reload: boolean }>('quick-setup/language/', { admin_lang: adminLang, country })
    return data
  },
  async password(password: string): Promise<void> {
    await getHttp().put('quick-setup/password/', { password })
  },
  async detect(domain: string): Promise<DomainDetection> {
    // DNS + an HTTPS probe of the domain.
    const { data } = await getHttp().post<DomainDetection>('quick-setup/detect/', { domain }, { timeout: 20_000 })
    return data
  },
  async domains(input: DomainsInput): Promise<QuickSetupState> {
    // Each domain is resolved on the server; allow for slow DNS.
    const { data } = await getHttp().put<QuickSetupState>('quick-setup/domains/', input, { timeout: 60_000 })
    return data
  },
  async finish(): Promise<{ reinstall_url: string }> {
    const { data } = await getHttp().post<{ reinstall_url: string }>('quick-setup/finish/')
    return data
  },
}

/** A domain with its mode; `cdn`/`note` come from detection, `touched` once the admin picked the mode. */
export interface ModeChip {
  domain: string
  mode: DomainMode
  cdn?: string | null
  detecting?: boolean
  touched?: boolean
  note?: 'unresolved' | 'not_friendly' | null
}
