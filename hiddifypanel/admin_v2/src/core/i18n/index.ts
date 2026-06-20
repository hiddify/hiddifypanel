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

applyDocumentLocale(locale)
