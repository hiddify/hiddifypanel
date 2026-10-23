import { computed, ref } from 'vue'
import { getHttp } from '@/core/api/client'

/**
 * Config health (the dashboard card and the topbar's notifications): the panel's last test of every config of its own
 * subscription. One state for both, so "Check now" on the card also updates the bell.
 */
export interface AppHealth {
  total: number
  ok: number
  failed: { name: string; error: string }[]
  error: string
  /** Why the subscription could not be tested (certificate, timeout, dns, unreachable, http, empty, core, other) */
  error_kind?: string
}
export interface HealthState {
  last: { at: number; user: string; host?: string; apps: Record<string, AppHealth> } | null
  running: boolean
}

export const CONFIG_HEALTH_APPS: Record<string, string> = { xray: 'Xray (v2rayN, v2rayNG, Happ…)', hiddify: 'Hiddify / sing-box' }

export const configHealth = ref<HealthState | null>(null)

export async function loadConfigHealth(): Promise<HealthState | null> {
  try {
    configHealth.value = (await getHttp().get<HealthState>('config-health/')).data
  } catch {
    configHealth.value = null
  }
  return configHealth.value
}

const KNOWN_KINDS = ['certificate', 'timeout', 'dns', 'unreachable', 'http', 'empty', 'core']

/** The i18n key part (`dashboard.health.problem.<kind>`) for an app whose subscription could not be tested. */
export function problemKind(app: AppHealth): string {
  const kind = app.error_kind ?? ''
  if (KNOWN_KINDS.includes(kind)) return kind
  // Results kept from before the kinds existed: the same reading of the message
  if (/certificate|SSL/i.test(app.error)) return 'certificate'
  return 'other'
}

/** One failed config's curl message, in words (`dashboard.health.reason.<kind>`); '' when it is not a known one. */
export function configReason(error: string): string {
  if (/SOCKS\d? connection to/i.test(error)) return 'noExit'
  if (/timed out/i.test(error)) return 'timeout'
  if (/TLS|SSL/i.test(error)) return 'tls'
  if (/reset by peer|Broken pipe|Empty reply/i.test(error)) return 'closed'
  if (/refused/i.test(error)) return 'refused'
  return ''
}

/** The apps with something to tell: their subscription could not be tested, or some configs fail. */
export const configHealthProblems = computed(() => {
  const last = configHealth.value?.last
  if (!last) return []
  return Object.entries(last.apps)
    .filter(([, app]) => app.error || app.failed.length)
    .map(([name, app]) => ({ name, label: CONFIG_HEALTH_APPS[name] ?? name, app, host: last.host ?? '' }))
})
