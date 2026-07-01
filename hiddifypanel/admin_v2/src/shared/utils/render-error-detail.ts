import type { GeneratedSection, RenderErrorDetail, ValidationIssue } from '@/core/api/generated'

function parseErrorLocation(message: string): { line: number | null; column: number | null } {
  const lineMatch = message.match(/<string>:(\d+)/)
  const colMatch = message.match(/column (\d+)/)
  return {
    line: lineMatch ? Number(lineMatch[1]) : null,
    column: colMatch ? Number(colMatch[1]) : null,
  }
}

function errorFromIssueMessage(issue: ValidationIssue): string {
  const colon = issue.message.indexOf(': ')
  return colon >= 0 ? issue.message.slice(colon + 2) : issue.message
}

function buildFallbackDetail(
  error: string,
  section?: GeneratedSection | null,
  label?: string | null,
): RenderErrorDetail {
  const { line, column } = parseErrorLocation(error)
  const phase = line ? 'json5' : 'jinja'
  const source = phase === 'json5'
    ? (section?.rendered || '')
    : (section?.error_detail?.template_source || section?.error_detail?.source || section?.rendered || '')
  return {
    message: error,
    source,
    phase,
    line,
    column,
    label: label || section?.label || section?.core || null,
  }
}

export function detailFromIssue(
  issue: ValidationIssue,
  section?: GeneratedSection | null,
): RenderErrorDetail | null {
  const extracted = errorFromIssueMessage(issue)
  const detail = issue.detail ?? null
  if (detail && detail.message === extracted) {
    return detail
  }
  if (detail && section?.error_detail && section.error_detail.message === extracted) {
    return section.error_detail
  }
  if (extracted) {
    return buildFallbackDetail(extracted, section, detail?.label)
  }
  return detail
}

export function detailFromSection(section: GeneratedSection | null | undefined): RenderErrorDetail | null {
  if (!section?.error) return null
  const detail = section.error_detail
  if (detail && detail.message === section.error) {
    return detail
  }
  return buildFallbackDetail(section.error, section)
}

export function hasRenderableErrorDetail(detail: RenderErrorDetail | null | undefined): boolean {
  if (!detail) return false
  return Boolean(
    detail.source
    || detail.excerpt
    || detail.template_source
    || detail.template_excerpt
    || detail.message,
  )
}
