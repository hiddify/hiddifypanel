import type { ValidationIssue, ValidationResult } from '@/core/api/generated'

/** Build a toast detail string from validation issues (errors first). */
export function validationToastDetail(
  result: Pick<ValidationResult, 'errors' | 'warnings'> | null | undefined,
  limit = 5,
): string {
  const issues = [...(result?.errors ?? []), ...(result?.warnings ?? [])]
  if (!issues.length) return ''
  const lines = issues.slice(0, limit).map(formatValidationIssue)
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
