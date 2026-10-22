import type { ComposerTranslation } from 'vue-i18n'

/**
 * An operator's name in the page's language; one Hiddify has no name for ("unknown") is named by its AS number when
 * known. Else its code.
 */
export function operatorLabel(t: ComposerTranslation, code: string, asn?: string): string {
  if (code === 'unknown') return asn && asn !== 'unknown' ? t('cleanIp.unknownIspAs', { asn }) : t('cleanIp.unknownIsp')
  const key = `operatorIps.name.${code}`
  const name = t(key)
  return name === key ? code : name
}
