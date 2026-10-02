import { computed, onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { panelNotices, type PanelNotice } from '@/core/panelShell'

export type PanelNoticeSeverity = PanelNotice['severity']

export type { PanelNotice }

const DISMISSED_KEY = 'hiddify.notices.dismissed'

/**
 * Stable per notice (not per position): its id, else a hash of its text. A notice whose text
 * changes (e.g. another domain) counts as new and shows again.
 */
function noticeKey(notice: PanelNotice): string {
  if (notice.id) return `id:${notice.id}`
  const text = `${notice.severity}|${notice.summary}|${notice.detail ?? ''}`
  let hash = 0
  for (let i = 0; i < text.length; i++) hash = (Math.imul(31, hash) + text.charCodeAt(i)) | 0
  return `h:${(hash >>> 0).toString(36)}`
}

function readDismissed(): Set<string> {
  try {
    const list = JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]')
    return new Set(Array.isArray(list) ? list.map(String) : [])
  } catch {
    return new Set()
  }
}

function saveDismissed(keys: Set<string>) {
  try {
    // Keep the list short: only the latest few hundred dismissals.
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([...keys].slice(-300)))
  } catch {
    /* private mode: dismissed for this visit only */
  }
}

export function usePanelNotifications() {
  const toast = useToast()
  const notices = panelNotices
  // Closed notices stay closed in this browser.
  const dismissed = ref<Set<string>>(readDismissed())
  const toasted = ref<Set<string>>(new Set())

  function dismiss(notice: PanelNotice) {
    dismissed.value = new Set(dismissed.value).add(noticeKey(notice))
    saveDismissed(dismissed.value)
  }

  const visibleNotices = computed(() => notices.value.filter((n) => !dismissed.value.has(noticeKey(n))))

  function showToasts(items: PanelNotice[] = notices.value) {
    for (const notice of items) {
      if (!notice.toast || dismissed.value.has(noticeKey(notice))) continue
      const key = noticeKey(notice)
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
