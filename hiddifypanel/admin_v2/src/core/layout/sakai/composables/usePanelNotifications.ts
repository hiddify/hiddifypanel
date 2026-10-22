import { computed, onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { panelNotices, type PanelNotice } from '@/core/panelShell'

export type PanelNoticeSeverity = PanelNotice['severity']

export type { PanelNotice }

const DISMISSED_KEY = 'hiddify.notices.dismissed'
/** Notices already shown in the topbar's notification list: no red dot for them. */
const SEEN_KEY = 'hiddify.notices.seen'

/**
 * Stable per notice (not per position): its id, else a hash of its text. A notice whose text
 * changes (e.g. another domain) counts as new and shows again.
 */
export function noticeKey(notice: PanelNotice): string {
  if (notice.id) return `id:${notice.id}`
  const text = `${notice.severity}|${notice.summary}|${notice.detail ?? ''}`
  let hash = 0
  for (let i = 0; i < text.length; i++) hash = (Math.imul(31, hash) + text.charCodeAt(i)) | 0
  return `h:${(hash >>> 0).toString(36)}`
}

function readKeys(storageKey: string): Set<string> {
  try {
    const list = JSON.parse(localStorage.getItem(storageKey) || '[]')
    return new Set(Array.isArray(list) ? list.map(String) : [])
  } catch {
    return new Set()
  }
}

function saveKeys(storageKey: string, keys: Set<string>) {
  try {
    // Keep the list short: only the latest few hundred.
    localStorage.setItem(storageKey, JSON.stringify([...keys].slice(-300)))
  } catch {
    /* private mode: dismissed for this visit only */
  }
}

export function usePanelNotifications() {
  const toast = useToast()
  const notices = panelNotices
  // Closed notices stay closed in this browser.
  const dismissed = ref<Set<string>>(readKeys(DISMISSED_KEY))
  const seen = ref<Set<string>>(readKeys(SEEN_KEY))
  const toasted = ref<Set<string>>(new Set())

  function dismiss(notice: PanelNotice) {
    dismissed.value = new Set(dismissed.value).add(noticeKey(notice))
    saveKeys(DISMISSED_KEY, dismissed.value)
  }

  const visibleNotices = computed(() => notices.value.filter((n) => !dismissed.value.has(noticeKey(n))))
  /** Not yet seen in the notification list: they light the red dot. A notice whose text changes is new again. */
  const unseenNotices = computed(() => visibleNotices.value.filter((n) => !seen.value.has(noticeKey(n))))
  const unseenCount = computed(() => unseenNotices.value.length)

  function markAllSeen() {
    const next = new Set(seen.value)
    for (const n of visibleNotices.value) next.add(noticeKey(n))
    seen.value = next
    saveKeys(SEEN_KEY, next)
  }

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

  return { notices, visibleNotices, unseenNotices, unseenCount, dismiss, markAllSeen, showToasts }
}
