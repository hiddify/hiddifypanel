/**
 * The panel's own configs (custom proxies) seen through a test: which are down, turning them off, and Restore. The
 * restore list is shared by the health card (in the results) and the restore bar (top of the page).
 */
import { ref } from 'vue'
import { getHttp } from '@/core/api/client'
import type { RestartMode } from '@/shared/utils/restart-mode'

export type ProxyStatus = 'down' | 'partial' | 'up'

export interface ProxyHealth {
  id: number
  name: string
  enabled: boolean
  status: ProxyStatus
  tested: number
  failed: number
  failed_names: string[]
}

export interface DisabledProxy {
  id: number
  name: string
  /** unix seconds */
  at: number
  /** still off (it may have been turned on by hand since) */
  off: boolean
}

/** What Restore would turn back on. */
export const disabledProxies = ref<DisabledProxy[]>([])
/** An Apply is needed after turning proxies off or on. */
export const pendingApply = ref<RestartMode>('nothing')

export async function loadDisabled(): Promise<void> {
  disabledProxies.value = (await getHttp().get<{ disabled: DisabledProxy[] }>('config-tester/proxies/')).data.disabled
}

export async function proxyHealth(results: { name: string; ok: boolean }[]): Promise<ProxyHealth[]> {
  const { data } = await getHttp().post<{ proxies: ProxyHealth[]; disabled: DisabledProxy[] }>('config-tester/proxies/', { results })
  disabledProxies.value = data.disabled
  return data.proxies
}

export async function disableProxies(ids: number[]): Promise<void> {
  const { data } = await getHttp().post<{ disabled: DisabledProxy[]; restart_mode: RestartMode }>('config-tester/proxies/disable/', { ids })
  disabledProxies.value = data.disabled
  pendingApply.value = data.restart_mode
}

export async function restoreProxies(): Promise<DisabledProxy[]> {
  const { data } = await getHttp().post<{ restored: DisabledProxy[]; disabled: DisabledProxy[]; restart_mode: RestartMode }>('config-tester/proxies/restore/')
  disabledProxies.value = data.disabled
  if (data.restart_mode !== 'nothing') pendingApply.value = data.restart_mode
  return data.restored
}
