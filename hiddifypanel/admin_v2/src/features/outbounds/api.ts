import { getHttp } from '@/core/api/client'
import type { RestartMode } from '@/shared/utils/restart-mode'

export type OutboundMode = 'warp' | 'psiphon' | 'direct' | 'socks' | 'tor' | 'block'

/** Only SOCKS has an endpoint the admin sets; Tor and Psiphon use their local port on the server. */
export const CONFIGURABLE_ENDPOINT_MODES: OutboundMode[] = ['socks']

export interface OutboundLists {
  sites: string[]
  geosites: string[]
  rule_sets: string[]
}

export interface Outbound extends OutboundLists {
  id: number
  name: string
  mode: OutboundMode
  /** Rule order, 1 = checked first. */
  position: number
  enabled: boolean
  /** The last enabled outbound: everything not routed elsewhere goes here. */
  is_default: boolean
  /** Has sites, geosites, rule-sets or domestic. */
  has_rules: boolean
  /** Routes something: enabled and (the default, or has rules). */
  active: boolean
  domestic: boolean
  host: string
  port: number | null
  username: string
  has_password: boolean
  is_builtin: boolean
  /** The admin edited the lists: upgrades keep them. */
  lists_override: boolean
  builtin_lists: OutboundLists & { domestic: boolean }
}

export interface OutboundsState {
  outbounds: Outbound[]
  /** Panel region (from the country setting), e.g. `ir`. */
  region: string
  /** What "domestic" adds for this region. */
  /** `geosites`: xray entries with prefix (`geosite:cn`, `geoip:ir`). */
  domestic: { sites: string[]; geosites: string[]; rule_sets: string[] }
  /** The WARP setting (kept in step with the WARP outbound): disable | all | custom. */
  warp_mode: string
  addable_modes: OutboundMode[]
  endpoints: Partial<Record<OutboundMode, { host?: string; port?: number }>>
  restart_mode?: RestartMode
  /** POST: the new outbound. */
  created_id?: number
}

export interface OutboundPayload extends Partial<OutboundLists> {
  name?: string
  mode?: OutboundMode
  enabled?: boolean
  domestic?: boolean
  host?: string
  port?: number | null
  username?: string
  /** Empty keeps the current password. */
  password?: string
  clear_password?: boolean
  is_default?: boolean
}

export const outboundsApi = {
  async list(): Promise<OutboundsState> {
    const { data } = await getHttp().get<OutboundsState>('outbounds/')
    return data
  },
  async create(payload: OutboundPayload): Promise<OutboundsState> {
    const { data } = await getHttp().post<OutboundsState>('outbounds/', payload)
    return data
  },
  async update(id: number, payload: OutboundPayload): Promise<OutboundsState> {
    const { data } = await getHttp().patch<OutboundsState>(`outbounds/${id}/`, payload)
    return data
  },
  async remove(id: number): Promise<OutboundsState> {
    const { data } = await getHttp().delete<OutboundsState>(`outbounds/${id}/`)
    return data
  },
  /** `ids` in the new order (first checked first; the last enabled one is the default). */
  async reorder(ids: number[]): Promise<OutboundsState> {
    const { data } = await getHttp().put<OutboundsState>('outbounds/order/', { ids })
    return data
  },
  /** Turns it on and moves it to the end. */
  async makeDefault(id: number): Promise<OutboundsState> {
    const { data } = await getHttp().post<OutboundsState>(`outbounds/${id}/default/`)
    return data
  },
  async reset(id: number): Promise<OutboundsState> {
    const { data } = await getHttp().post<OutboundsState>(`outbounds/${id}/reset/`)
    return data
  },
}

export const MODE_ICON: Record<OutboundMode, string> = {
  warp: 'pi pi-cloud',
  direct: 'pi pi-arrow-right',
  block: 'pi pi-ban',
  socks: 'pi pi-share-alt',
  tor: 'pi pi-eye-slash',
  psiphon: 'pi pi-globe',
}
