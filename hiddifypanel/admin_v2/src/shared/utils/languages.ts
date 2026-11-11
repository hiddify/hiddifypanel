/** The panel languages: native names (an admin may not read the current one) with the country code of a flag. */
export const LANGUAGE_LOOK: Record<string, { flag: string; name: string }> = {
  en: { flag: 'us', name: 'English' },
  fa: { flag: 'ir', name: 'فارسی' },
  zh: { flag: 'cn', name: '中文' },
  pt: { flag: 'br', name: 'Português' },
  ru: { flag: 'ru', name: 'Русский' },
  my: { flag: 'mm', name: 'မြန်မာ' },
  ko: { flag: 'kp', name: '한국어' },
  tk: { flag: 'tm', name: 'Türkmençe' },
  be: { flag: 'by', name: 'Беларуская' },
  es: { flag: 'cu', name: 'Español' },
  am: { flag: 'et', name: 'አማርኛ' },
  ar: { flag: 'sa', name: 'العربية' },
  ur: { flag: 'pk', name: 'اردو' },
  ps: { flag: 'af', name: 'پښتو' },
  bn: { flag: 'bd', name: 'বাংলা' },
  tr: { flag: 'tr', name: 'Türkçe' },
  uz: { flag: 'uz', name: 'Oʻzbekcha' },
  az: { flag: 'az', name: 'Azərbaycanca' },
  kk: { flag: 'kz', name: 'Қазақша' },
  ky: { flag: 'kg', name: 'Кыргызча' },
  tg: { flag: 'tj', name: 'Тоҷикӣ' },
  hy: { flag: 'am', name: 'Հայերեն' },
}

/** Languages written right to left (as RTL_LANGS in models/config_enum.py). */
export const RTL_LANGUAGES = new Set(['fa', 'ar', 'ur', 'ps'])

export function isRtlLanguage(code: string): boolean {
  return RTL_LANGUAGES.has(code)
}
