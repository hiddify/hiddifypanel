import { getHttp } from '@/core/api/client'

export type ApplyMode = 'nothing' | 'apply_config' | 'reinstall'

export interface ProtocolSwitch {
  key: string
  label: string
  /** Sanitized HTML from the server (links, line breaks, emphasis). */
  description: string
  category: string
  enabled: boolean
  apply_mode: ApplyMode
}

export interface ProtocolSwitchesOut {
  items: ProtocolSwitch[]
  restart_mode: ApplyMode
}

export const protocolsApi = {
  async list(): Promise<ProtocolSwitchesOut> {
    const { data } = await getHttp().get<ProtocolSwitchesOut>('protocols/')
    return data
  },
  async update(values: Record<string, boolean>): Promise<ProtocolSwitchesOut> {
    const { data } = await getHttp().put<ProtocolSwitchesOut>('protocols/', { values })
    return data
  },
}
