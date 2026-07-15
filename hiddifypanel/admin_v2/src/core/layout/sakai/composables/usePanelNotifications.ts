import { computed, onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { panelNotices, type PanelNotice } from '@/core/panelShell'

export type PanelNoticeSeverity = PanelNotice['severity']

export type { PanelNotice }

function noticeKey(notice: PanelNotice, index: number): string {
  return notice.id ?? `${notice.severity}:${notice.summary.slice(0, 48)}:${index}`
}

export function usePanelNotifications() {
  const toast = useToast()
  const notices = panelNotices
  const dismissed = ref<Set<string>>(new Set())
  const toasted = ref<Set<string>>(new Set())

  function dismiss(notice: PanelNotice, index: number) {
    dismissed.value = new Set(dismissed.value).add(noticeKey(notice, index))
  }

  const visibleNotices = computed(() =>
    notices.value.filter((n, i) => !dismissed.value.has(noticeKey(n, i))),
  )

  function showToasts(items: PanelNotice[] = notices.value) {
    for (const [index, notice] of items.entries()) {
      if (!notice.toast) continue
      const key = noticeKey(notice, index)
      if (toasted.value.has(key)) continue
      toasted.value = new Set(toasted.value).add(key)
      toast.add({
        severity: notice.severity,
        summary: notice.summary.replace(/<[^>]+>/g, ''),
        detail: notice.detail?.replace(/<[^>]+>/g, ''),
        life: 8000,
      })
    }
  }

  onMounted(() => {
    showToasts()
  })

  watch(notices, (items) => {
    showToasts(items)
  })

  return { notices, visibleNotices, dismiss, showToasts }
}
