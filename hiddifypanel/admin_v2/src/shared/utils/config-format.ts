import { usesJsonTemplate } from '@/shared/utils/core-template'
import type { GeneratedSection } from '@/core/api/generated'

export type ConfigFormatView = 'json' | 'yaml'

function yamlScalar(value: string): string {
  if (
    value === ''
    || value === 'true'
    || value === 'false'
    || value === 'null'
    || /^-?\d+(?:\.\d+)?$/.test(value)
    || /[:#\n\r\t|>&*!?[\]{},]/.test(value)
    || value.startsWith(' ')
    || value.endsWith(' ')
  ) {
    return JSON.stringify(value)
  }
  return value
}

function parsedToYaml(value: unknown, indent = 0): string {
  const pad = '  '.repeat(indent)
  if (value === null || value === undefined) {
    return 'null'
  }
  if (typeof value === 'boolean' || typeof value === 'number') {
    return String(value)
  }
  if (typeof value === 'string') {
    return yamlScalar(value)
  }
  if (Array.isArray(value)) {
    if (!value.length) {
      return '[]'
    }
    return value
      .map((item) => {
        const rendered = parsedToYaml(item, indent + 1)
        if (rendered.includes('\n')) {
          return `${pad}-\n${rendered}`
        }
        return `${pad}- ${rendered}`
      })
      .join('\n')
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (!entries.length) {
      return '{}'
    }
    return entries
      .map(([key, child]) => {
        const rendered = parsedToYaml(child, indent + 1)
        if (rendered.includes('\n')) {
          return `${pad}${key}:\n${rendered}`
        }
        return `${pad}${key}: ${rendered}`
      })
      .join('\n')
  }
  return yamlScalar(String(value))
}

export function sectionSupportsFormatToggle(section: GeneratedSection | null | undefined): boolean {
  if (!section) return false
  if (section.parsed != null) return true
  const core = (section.core || '').replace(/_/g, '-')
  return usesJsonTemplate(core)
}

export function formatSectionText(
  section: GeneratedSection | null | undefined,
  view: ConfigFormatView,
  formatJson: (value: unknown) => string,
  tryPrettyJson: (text: string) => string,
): string {
  if (!section) return ''
  if (view === 'yaml') {
    const yaml = section.config_yaml || section.clash_yaml
    if (yaml) return yaml
    if (section.parsed != null) {
      return parsedToYaml(section.parsed)
    }
  }
  if (section.parsed != null) {
    return formatJson(section.parsed)
  }
  return tryPrettyJson(section.rendered || '')
}
