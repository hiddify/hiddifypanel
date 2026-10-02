import type { CustomProxy, ParentEnableBlock } from '@/core/api/generated'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'

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

export function useParentEnablePrompt() {
  const confirm = useConfirm()
  const { t } = useI18n()

  function promptParentEnable(blocked: ParentEnableBlock[], settingsUrl?: string) {
    const names = blocked.map((item) => item.label).join(', ')
    confirm.require({
      message: t('proxy.needGlobalEnable', { names }),
      header: t('proxy.cannotEnable'),
      icon: 'pi pi-exclamation-triangle',
      rejectProps: { label: t('common.cancel'), severity: 'secondary', outlined: true },
      acceptProps: { label: t('proxy.goToSettings') },
      accept: () => {
        if (settingsUrl) window.open(settingsUrl, '_blank', 'noopener,noreferrer')
      },
    })
  }

  return { promptParentEnable }
}
