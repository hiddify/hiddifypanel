import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { isChildPanel, isSuperAdmin, panelNotices, type PanelNotice } from '@/core/panelShell'
import { configHealthProblems, loadConfigHealth, problemKind } from '@/shared/composables/useConfigHealth'

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

const escapeHtml = (text: string) => text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)
/** Config health is looked at again this often (it runs every 6 hours, or on "Check now" from the dashboard) */
const HEALTH_REFRESH_MS = 10 * 60_000

export function usePanelNotifications() {
  const toast = useToast()
  const { t } = useI18n()

  /** Config health problems as notices: where it fails and what to look at (the dashboard card has the details). */
  const healthNotices = computed<PanelNotice[]>(() =>
    configHealthProblems.value.map(({ name, label, app, host }) => {
      const head = `<b>${escapeHtml(t('dashboard.health.title'))} · ${escapeHtml(label)}</b><br>`
      const where = t('dashboard.health.notice.where')
      if (app.error) {
        const kind = problemKind(app)
        return {
          id: `config-health:${name}:${kind}:${host}`,
          severity: 'error',
          summary: head + escapeHtml(t(`dashboard.health.problem.${kind}.title`, { host: host || '—' })),
          detail: `${escapeHtml(t(`dashboard.health.problem.${kind}.hint`, { host: host || '—' }))} ${escapeHtml(where)}`,
        }
      }
      // not the list's length: the panel keeps only the first 60 failed configs
      const failed = Math.max(app.total - app.ok, app.failed.length)
      return {
        // the number in the id: more (or fewer) failing configs is news again
        id: `config-health:${name}:failed:${failed}`,
        severity: 'warn',
        summary: head + escapeHtml(t('dashboard.health.notice.failed', { n: failed, total: app.total })),
        detail: escapeHtml(where),
      }
    }),
  )
  // Errors first: a config that does not work matters more than the panel's advice
  const notices = computed(() => [...healthNotices.value.filter((n) => n.severity === 'error'), ...panelNotices.value, ...healthNotices.value.filter((n) => n.severity !== 'error')])
  let healthTimer = 0
  function refreshHealth() {
    void loadConfigHealth()
    healthTimer = window.setTimeout(refreshHealth, HEALTH_REFRESH_MS)
  }
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
    // Config health is the super admin's (the API is theirs), and a node's configs are tested by its parent panel
    if (isSuperAdmin.value && !isChildPanel.value) refreshHealth()
  })
  onBeforeUnmount(() => window.clearTimeout(healthTimer))

  watch(notices, (items) => {
    showToasts(items)
  })

  return { notices, visibleNotices, unseenNotices, unseenCount, dismiss, markAllSeen, showToasts }
}
