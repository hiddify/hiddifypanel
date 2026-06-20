const JSON_TEMPLATE_CORES = new Set(['xray', 'singbox', 'hiddify-core', 'hiddify_core', 'clash'])

export function usesJsonTemplate(core?: string | null): boolean {
  const normalized = (core ?? '').replace(/_/g, '-')
  return JSON_TEMPLATE_CORES.has(normalized) || JSON_TEMPLATE_CORES.has(core ?? '')
}

export const SUBLINK_CORE = 'sublink'

export function isSublinkCore(core?: string | null): boolean {
  return (core ?? '') === SUBLINK_CORE
}
