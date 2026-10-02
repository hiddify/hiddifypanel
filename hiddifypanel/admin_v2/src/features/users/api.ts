import { getHttp } from '@/core/api/client'
import type { ShareDomain } from '@/shared/utils/share-domain'

/** One clear state: disabled (turned off) > expired > no_data (usage used up) > active. */
export type UserStatus = 'active' | 'disabled' | 'expired' | 'no_data'
/** How often the usage resets. */
export type UserMode = 'no_reset' | 'monthly' | 'weekly' | 'daily'
export const USER_MODES: UserMode[] = ['no_reset', 'monthly', 'weekly', 'daily']

/** "Unlimited" is the highest value the server keeps (shown as ∞). */
export const UNLIMITED_GB = 1_000_000
export const UNLIMITED_DAYS = 10_000

import type { AdditionalConfig } from '@/shared/utils/additional-configs'
export { CONFIG_TARGETS, type AdditionalConfig, type ConfigKind, type ConfigTarget } from '@/shared/utils/additional-configs'

export interface UserRow {
  uuid: string
  name: string
  comment: string
  enable: boolean
  status: UserStatus
  current_usage_GB: number
  usage_limit_GB: number
  package_days: number
  remaining_days: number
  /** Null: not started, the package starts at the first connection. */
  start_date: string | null
  expire_date: string | null
  mode: UserMode
  /** Periodic modes: days until the usage resets. */
  days_to_reset: number | null
  last_reset_time: string | null
  last_online: string | null
  owner_uuid: string | null
  owner_name: string
  preferred_outbound: number | null
  /** List: how many; detail: the rows. */
  additional_configs: number
  telegram_id: number | null
  /** Ids of the tags on the user. */
  tags: number[]
}

export interface UserDetail extends Omit<UserRow, 'additional_configs'> {
  additional_configs: AdditionalConfig[]
  /** Rows the user also gets from its admin and the admins above. */
  inherited_configs: number
  /** JSON text of the other extra params. */
  extra_params: string
}

export interface UsersState {
  users: UserRow[]
  me_uuid: string
  link_domains: ShareDomain[]
  admins: { uuid: string; name: string; parent_uuid: string | null }[]
  outbounds: { id: number; name: string; mode: string; enabled: boolean }[]
  can_add: boolean
}

export interface UserPayload {
  name?: string
  comment?: string
  enable?: boolean
  usage_limit_GB?: number
  package_days?: number
  mode?: UserMode
  uuid?: string
  owner_uuid?: string
  telegram_id?: number | null
  preferred_outbound?: number | null
  additional_configs?: AdditionalConfig[]
  extra_params?: string
  reset_usage?: boolean
  reset_days?: boolean
}

export type BulkAction = 'enable' | 'disable' | 'delete' | 'reset_usage' | 'reset_days' | 'add_days' | 'add_limits'

export const usersApi = {
  async list(): Promise<UsersState> {
    const { data } = await getHttp().get<UsersState>('users/')
    return data
  },
  async get(uuid: string): Promise<UserDetail> {
    const { data } = await getHttp().get<{ user: UserDetail }>(`users/${uuid}/`)
    return data.user
  },
  async create(payload: UserPayload): Promise<UserDetail> {
    const { data } = await getHttp().post<{ user: UserDetail }>('users/', payload)
    return data.user
  },
  async update(uuid: string, payload: UserPayload): Promise<UserDetail> {
    const { data } = await getHttp().patch<{ user: UserDetail }>(`users/${uuid}/`, payload)
    return data.user
  },
  async remove(uuid: string): Promise<void> {
    await getHttp().delete(`users/${uuid}/`)
  },
  async bulk(action: BulkAction, uuids: string[], days?: number, gb?: number): Promise<number> {
    const { data } = await getHttp().post<{ count: number }>('users/bulk/', { action, uuids, days, gb })
    return data.count
  },
}

export const STATUS_ICON: Record<UserStatus, string> = {
  active: 'pi pi-check-circle',
  disabled: 'pi pi-ban',
  expired: 'pi pi-calendar-times',
  no_data: 'pi pi-database',
}

export const MODE_ICON: Record<UserMode, string> = {
  no_reset: 'pi pi-star',
  monthly: 'pi pi-calendar',
  weekly: 'pi pi-calendar-minus',
  daily: 'pi pi-sun',
}

/** The user's subscription link path on a domain: `<uuid>/#<name>`. */
export function userLinkPath(user: { uuid: string; name: string }): string {
  return `${user.uuid}/#${encodeURIComponent(user.name)}`
}
