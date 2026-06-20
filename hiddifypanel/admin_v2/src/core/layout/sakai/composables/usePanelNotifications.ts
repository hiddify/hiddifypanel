import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'

export type PanelNoticeSeverity = 'success' | 'info' | 'warn' | 'error'

export interface PanelNotice {
  severity: PanelNoticeSeverity
  summary: string
  detail?: string
  toast?: boolean
  id?: string
}

declare global {
  interface Window {
    __ADMIN_NOTICES__?: PanelNotice[]
  }
}

function noticeKey(notice: PanelNotice, index: number): string {
  return notice.id ?? `${notice.severity}:${notice.summary.slice(0, 48)}:${index}`
}

export function usePanelNotifications() {
  const toast = useToast()
  const notices = ref<PanelNotice[]>([])
  const dismissed = ref<Set<string>>(new Set())

  function loadNotices() {
    notices.value = [...(window.__ADMIN_NOTICES__ ?? [])]
  }

  function dismiss(notice: PanelNotice, index: number) {
    dismissed.value = new Set(dismissed.value).add(noticeKey(notice, index))
  }

  const visibleNotices = computed(() =>
    notices.value.filter((n, i) => !dismissed.value.has(noticeKey(n, i))),
  )

  function showToasts() {
    for (const notice of notices.value) {
      if (!notice.toast) continue
      toast.add({
        severity: notice.severity,
        summary: notice.summary.replace(/<[^>]+>/g, ''),
        detail: notice.detail?.replace(/<[^>]+>/g, ''),
        life: 8000,
      })
    }
  }

  onMounted(() => {
    loadNotices()
    showToasts()
  })

  return { notices, visibleNotices, dismiss, showToasts, loadNotices }
}
