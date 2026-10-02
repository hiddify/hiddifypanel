import { createI18n, type I18nOptions } from 'vue-i18n'

type LocaleBundle = { adminV2?: Record<string, unknown> }

const localeModules = import.meta.glob<LocaleBundle>('../../../../translations.i18n/*.json', {
  eager: true,
})

const messages: Record<string, Record<string, unknown>> = {}
for (const path in localeModules) {
  const match = path.match(/\/([^/]+)\.json$/)
  if (!match) continue
  const bundle = localeModules[path] as LocaleBundle
  messages[match[1]] = bundle.adminV2 ?? {}
}

const locale = window.__LOCALE__ ?? 'en'

export const i18n = createI18n({
  legacy: false,
  locale,
  fallbackLocale: 'en',
  messages,
} as I18nOptions)

export function applyDocumentLocale(loc: string) {
  const rtl = loc === 'fa' || loc === 'ar'
  document.documentElement.lang = loc
  document.documentElement.dir = rtl ? 'rtl' : 'ltr'
}

/** PrimeVue's built-in texts (confirm buttons, empty filter results, …) in the panel language. */
export function primeVueLocale() {
  const t = i18n.global.t
  const keys = [
    'accept',
    'reject',
    'cancel',
    'clear',
    'apply',
    'choose',
    'upload',
    'emptyMessage',
    'emptyFilterMessage',
    'emptySearchMessage',
  ] as const
  return Object.fromEntries(keys.map((key) => [key, t(`primevue.${key}`)]))
}

export function setLocale(loc: string) {
  ;(i18n.global.locale as unknown as { value: string }).value = loc
  applyDocumentLocale(loc)
}

applyDocumentLocale(locale)
