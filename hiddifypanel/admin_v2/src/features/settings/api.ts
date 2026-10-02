import { getHttp } from '@/core/api/client'
import type { RestartMode } from '@/shared/utils/restart-mode'

export type SettingType = 'bool' | 'select' | 'text' | 'textarea' | 'html'
export type SettingValue = string | boolean

export interface SettingField {
  key: string
  label: string
  /** Sanitized HTML from the server. */
  description: string
  type: SettingType
  value: SettingValue
  apply_mode: 'nothing' | 'apply_config' | 'reinstall'
  /** Shown without "advanced" mode. */
  essential: boolean
  /** Also on the Protocols page. */
  protocol_switch: boolean
  required: boolean
  choices?: { value: string; label: string }[]
  pattern?: string
  pattern_message?: string
  maxlength?: number
}

export interface SettingCategory {
  id: string
  label: string
  description: string
  fields: SettingField[]
}

export interface SettingsSaveOut {
  categories: SettingCategory[]
  restart_mode: RestartMode
  warnings: string[]
  changed: string[]
  reload: boolean
  new_admin_path: string | null
}

/** 400/422 body: form-level messages and per-setting messages. */
export interface SettingsErrorBody {
  errors?: string[]
  field_errors?: Record<string, string[]>
}

export const settingsApi = {
  async list(): Promise<SettingCategory[]> {
    const { data } = await getHttp().get<{ categories: SettingCategory[] }>('settings/')
    return data.categories
  },
  async update(values: Record<string, SettingValue>): Promise<SettingsSaveOut> {
    const { data } = await getHttp().put<SettingsSaveOut>('settings/', { values })
    return data
  },
}
