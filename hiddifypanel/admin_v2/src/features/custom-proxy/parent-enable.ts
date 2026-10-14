import type { CustomProxy, ParentEnableBlock } from '@/core/api/generated'
import { reactive } from 'vue'

export function blockedParentEnables(proxy: Partial<CustomProxy>): ParentEnableBlock[] {
  return proxy.blocked_by ?? []
}

export function isBlockedByParent(proxy: Partial<CustomProxy>): boolean {
  if (blockedParentEnables(proxy).length > 0) return true
  return proxy.enable === true && proxy.effective_enable === false
}

export function isEffectivelyEnabled(proxy: Partial<CustomProxy>): boolean {
  return Boolean(proxy.enable) && !isBlockedByParent(proxy)
}

export function parentEnableConflict(err: unknown): { blocked_by: ParentEnableBlock[]; settings_url?: string } | null {
  const res = (err as { response?: { status?: number; data?: Record<string, unknown> } })?.response
  if (res?.status !== 409) return null
  const body = res.data ?? {}
  const extra = (body.extra_data as Record<string, unknown> | undefined) ?? {}
  const blocked = (extra.blocked_by ?? body.blocked_by) as ParentEnableBlock[] | undefined
  if (!blocked?.length) return null
  return {
    blocked_by: blocked,
    settings_url: (extra.settings_url ?? body.settings_url) as string | undefined,
  }
}

/** One prompt at a time for the whole app; ParentEnableDialog renders it. */
export const parentEnablePrompt = reactive<{
  visible: boolean
  blocked: ParentEnableBlock[]
  settingsUrl?: string
  onEnabled?: () => void | Promise<void>
}>({ visible: false, blocked: [] })

export function useParentEnablePrompt() {
  /** Asks for the settings that block the proxy. `onEnabled` runs after they are saved here, to enable the proxy itself. */
  function promptParentEnable(blocked: ParentEnableBlock[], settingsUrl?: string, onEnabled?: () => void | Promise<void>) {
    Object.assign(parentEnablePrompt, { visible: true, blocked, settingsUrl, onEnabled })
  }

  return { promptParentEnable }
}
