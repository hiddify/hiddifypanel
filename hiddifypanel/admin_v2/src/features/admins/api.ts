import { getHttp } from '@/core/api/client'
import type { AdditionalConfig } from '@/shared/utils/additional-configs'

export type AdminMode = 'super_admin' | 'admin' | 'agent'

/** Limits of one admin; they count its users and all its sub-admins' users. Null fields: no limit. */
export interface AdminLimits {
  max_users: number
  max_active_users: number
  max_online_users: number | null
  /** Traffic all these users may use together. */
  max_total_usage_GB: number | null
}

/** Users of an admin and its sub-admins. Online = seen in the last 24 hours. */
export interface AdminStats {
  total: number
  active: number
  online: number
  usage_GB: number
}

/** A domain an admin link can use; the link is `${base}${uuid}/`. */
export interface LinkDomain {
  domain: string
  label: string
  /** `current`: the address this panel is open on. */
  kind: 'current' | 'direct' | 'cdn' | 'auto'
  base: string
}

export interface AdminRow {
  uuid: string
  name: string
  comment: string
  mode: AdminMode
  can_add_admin: boolean
  /** Null for the tree root (the signed-in admin). */
  parent_uuid: string | null
  parent_name: string | null
  is_me: boolean
  has_password: boolean
  /** Sign-in username instead of the UUID ("" when not set). */
  alias: string
  admin_link: string
  /** Null for a super admin: no limits. */
  limits: AdminLimits | null
  stats: AdminStats
  sub_admins: number
  /** Added to the subscription of every user of this admin and its sub-admins. */
  additional_configs: AdditionalConfig[]
  can_edit: boolean
  can_delete: boolean
}

export interface AdminsTree {
  me_uuid: string
  can_create: boolean
  my_limits: AdminLimits | null
  link_domains: LinkDomain[]
  admins: AdminRow[]
}

export interface AdminPayload {
  name?: string
  comment?: string
  uuid?: string
  can_add_admin?: boolean
  parent_uuid?: string
  max_users?: number
  max_active_users?: number
  /** 0 or null: no limit. */
  max_online_users?: number | null
  max_total_usage_GB?: number | null
  additional_configs?: AdditionalConfig[]
  /** "" clears it. */
  alias?: string
}

export interface AdminCredentials {
  password: string
  /** With an alias: the sign-in page (no UUID); else the UUID link. */
  admin_link: string
  alias?: string
}

export interface MyAccount {
  uuid: string
  name: string
  mode: AdminMode
  can_add_admin: boolean
  parent_name: string | null
  has_password: boolean
  /** Strong enough for an alias (and required for any new password). */
  strong_password: boolean
  alias: string
  /** False for super admins: they sign in with their link only. */
  can_alias: boolean
  /** With an alias: the sign-in page; else the UUID link. */
  login_link: string
  admin_link: string
  limits: AdminLimits | null
  stats: AdminStats
  sub_admins: number
  /** Mine: for all my users and my sub-admins' users. */
  additional_configs: AdditionalConfig[]
  /** From the admins above me: my users get them too. */
  inherited_configs: number
}

export const adminsApi = {
  async tree(): Promise<AdminsTree> {
    const { data } = await getHttp().get<AdminsTree>('admins/')
    return data
  },
  async create(payload: AdminPayload): Promise<AdminCredentials & { uuid: string; name: string }> {
    const { data } = await getHttp().post<AdminCredentials & { uuid: string; name: string }>('admins/', payload)
    return data
  },
  async update(uuid: string, payload: AdminPayload): Promise<void> {
    await getHttp().patch(`admins/${uuid}/`, payload)
  },
  async remove(uuid: string): Promise<void> {
    await getHttp().delete(`admins/${uuid}/`)
  },
  async resetPassword(uuid: string): Promise<AdminCredentials> {
    const { data } = await getHttp().post<AdminCredentials>(`admins/${uuid}/reset-password/`)
    return data
  },
  async me(): Promise<MyAccount> {
    const { data } = await getHttp().get<MyAccount>('admins/me/')
    return data
  },
  async setMyAlias(alias: string): Promise<{ alias: string; login_link: string }> {
    const { data } = await getHttp().put<{ alias: string; login_link: string }>('admins/me/alias/', { alias })
    return data
  },
  async saveMyConfigs(rows: AdditionalConfig[]): Promise<AdditionalConfig[]> {
    const { data } = await getHttp().put<{ additional_configs: AdditionalConfig[] }>('admins/me/additional-configs/', { additional_configs: rows })
    return data.additional_configs
  },
  async changeMyPassword(currentPassword: string, newPassword: string): Promise<void> {
    await getHttp().put('admins/me/password/', { current_password: currentPassword, new_password: newPassword })
  },
}

export type MeterTone = 'ok' | 'warn' | 'danger' | 'none'

/** Color of a meter: green up to 50% of the limit, yellow above it, red from 80%; `none` without a limit. */
export function meterTone(used: number, max: number | null | undefined): MeterTone {
  if (!max) return 'none'
  const ratio = used / max
  return ratio >= 0.8 ? 'danger' : ratio > 0.5 ? 'warn' : 'ok'
}
