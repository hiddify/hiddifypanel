import type { TemplateVariable } from '@/core/api/generated'

/** Insert snippet for editor — prefers dot access (hconfigs.vmess_enable). */
export function variableInsertSnippet(v: TemplateVariable): string {
  const access = v.access
  if (access.startsWith('{{')) {
    return access
  }
  if (access.startsWith('hconfigs.') || access.startsWith('user.') || access.startsWith('domain.')) {
    return `{{ ${access} }}`
  }
  if (v.category === 'loop') {
    return access
  }
  if (v.category === 'custom_proxy') {
    return access
  }
  return `{{ ${access} }}`
}
