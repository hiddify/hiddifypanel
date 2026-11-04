import type { ValidationIssue, ValidationResult } from '@/core/api/generated'

/**
 * What kind of problem a validation issue is, for a message in plain words: the panel's own fault (the check itself
 * crashed: nothing to fix in the proxy), the proxy's template, or one of its settings (its message says it already).
 */
export type IssueKind = 'internal' | 'template' | 'setting'

const INTERNAL = new Set(['validate_internal', 'unknown'])
const TEMPLATE = new Set(['jinja_error', 'client_jinja_error', 'sublink_jinja_error', 'client_render', 'server_render', 'client_yaml_parse', 'sublink_parse', 'variant_error'])

export function issueKind(issue: Pick<ValidationIssue, 'code'>): IssueKind {
  if (issue.code && INTERNAL.has(issue.code)) return 'internal'
  if (issue.code && TEMPLATE.has(issue.code)) return 'template'
  return 'setting'
}

/**
 * Build a toast detail string from validation issues (errors first). With `t`, the panel's own and template errors
 * read as their plain-words title (validation.kind.*); the panel under the editor has the rest.
 */
export function validationToastDetail(
  result: Pick<ValidationResult, 'errors' | 'warnings'> | null | undefined,
  limit = 5,
  t?: (key: string) => string,
): string {
  const issues = [...(result?.errors ?? []), ...(result?.warnings ?? [])]
  if (!issues.length) return ''
  const lines = issues.slice(0, limit).map((issue) => {
    const kind = issueKind(issue)
    return t && kind !== 'setting' ? t(`validation.kind.${kind}.title`) : formatValidationIssue(issue)
  })
  if (issues.length > limit) {
    lines.push(`… +${issues.length - limit} more`)
  }
  return lines.join(' · ')
}

export function formatValidationIssue(issue: ValidationIssue): string {
  const msg = (issue.message || '').trim()
  if (issue.code && msg && !msg.startsWith(issue.code)) {
    return `${issue.code}: ${msg}`
  }
  return msg || issue.code || 'Unknown validation error'
}
