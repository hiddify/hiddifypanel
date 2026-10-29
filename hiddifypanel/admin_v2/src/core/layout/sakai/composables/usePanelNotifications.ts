import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { hasCapability, isChildPanel, isSuperAdmin, panelNotices, type PanelNotice } from '@/core/panelShell'
import { domainProblems, domainSaveWarnings, loadDomainProblems } from '@/shared/composables/useDomainNotices'
import { configHealthProblems, loadConfigHealth, problemKind } from '@/shared/composables/useConfigHealth'
import { loadNodeProblems, nodeProblems } from '@/shared/composables/useNodeNotices'

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
  const { t, te } = useI18n()

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
  /** The Domains page's problems: certificates that do not work, and the warnings of the last saves. */
  const domainNotices = computed<PanelNotice[]>(() => {
    const head = (name: string) => `<b>${escapeHtml(t('domains.notice.title', { domain: name }))}</b><br>`
    const out: PanelNotice[] = domainProblems.value.map((p) => ({
      // the domain, the kind and the message in the id: a new failure is news again
      id: `domains:${p.id}:${p.kind}:${p.error.slice(0, 40)}`,
      severity: ['failed', 'expired', 'invalid'].includes(p.kind) ? 'error' : 'warn',
      summary: head(p.domain) + escapeHtml(t(`domains.notice.${p.kind}`)),
      detail: [p.error, t('domains.notice.where')].filter(Boolean).map(escapeHtml).join('<br>'),
    }))
    for (const w of domainSaveWarnings.value) {
      out.push({ severity: 'warn', summary: `<b>${escapeHtml(t('domains.notice.saved'))}</b><br>${escapeHtml(w.text).replace(/\n/g, '<br>')}` })
    }
    return out
  })
  /** Nodes this panel cannot reach: which one, why, and what to do (the Nodes page has the details). */
  const nodeNotices = computed<PanelNotice[]>(() =>
    nodeProblems.value.map((p) => {
      const code = te(`nodes.contact.${p.code}.title`) ? p.code : 'unknown'
      return {
        // the node and the reason in the id: another reason is news again
        id: `nodes:${p.id}:${code}`,
        severity: 'error',
        summary: `<b>${escapeHtml(t('nodes.notice.title', { name: p.name }))}</b><br>${escapeHtml(t(`nodes.contact.${code}.title`))}`,
        detail: `${escapeHtml(t(`nodes.contact.${code}.fix`))}<br>${escapeHtml(t('nodes.notice.where'))}`,
      }
    }),
  )
  const extra = computed(() => [...healthNotices.value, ...domainNotices.value, ...nodeNotices.value])
  // Errors first: a config or a certificate that does not work matters more than the panel's advice
  const notices = computed(() => [...extra.value.filter((n) => n.severity === 'error'), ...panelNotices.value, ...extra.value.filter((n) => n.severity !== 'error')])
  let healthTimer = 0
  function refreshHealth() {
    // Config health is the super admin's, and a node's configs are tested by its parent panel; every admin has Domains
    if (isSuperAdmin.value && !isChildPanel.value) {
      void loadConfigHealth()
      void loadNodeProblems()
    }
    if (hasCapability('modify_domains')) void loadDomainProblems()
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
    refreshHealth()
  })
  onBeforeUnmount(() => window.clearTimeout(healthTimer))

  watch(notices, (items) => {
    showToasts(items)
  })

  return { notices, visibleNotices, unseenNotices, unseenCount, dismiss, markAllSeen, showToasts }
}
