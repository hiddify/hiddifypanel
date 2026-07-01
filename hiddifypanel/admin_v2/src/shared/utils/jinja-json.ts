import JSON5 from 'json5'

const SAMPLE_VALUES: Record<string, string> = {
  IP: '203.0.113.1',
  DOMAIN: 'example.com',
  PORT: '2080',
  PATH: '/test-path',
  TAG: 'validate-tag',
}

const SAMPLE_OBJECT_PATHS: Record<string, string> = {
  'USER.uuid': SAMPLE_VALUES.TAG,
  USER: '{"uuid":"00000000-0000-0000-0000-000000000001"}',
  'proxy.port': SAMPLE_VALUES.PORT,
  'proxy.tcp_port': SAMPLE_VALUES.PORT,
  'proxy.udp_port': SAMPLE_VALUES.PORT,
  'proxy.server': SAMPLE_VALUES.IP,
  'proxy.tag': SAMPLE_VALUES.TAG,
  'domain.server': SAMPLE_VALUES.IP,
  'user.uuid': SAMPLE_VALUES.TAG,
}

const PROXY_URI_LINE = /^\s*[a-z][a-z0-9+.-]*:\/\/\S*\s*$/gm

export function containsJinja(text: string): boolean {
  return /\{%[\s\S]*?%\}/.test(text) || /\{\{[\s\S]*?\}\}/.test(text)
}

function escapeJsonString(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
}

function sampleForKey(key: string): string | undefined {
  if (key in SAMPLE_OBJECT_PATHS) return SAMPLE_OBJECT_PATHS[key]
  return SAMPLE_VALUES[key]
}

function replaceJinjaVariables(text: string): string {
  // "{{TAG}}" — placeholder already inside JSON string quotes
  let out = text.replace(/"(\s*\{\{[\s\S]*?\}\}\s*)"/g, (_full, inner: string) => {
    const match = inner.match(/\{\{\s*([A-Za-z0-9_.]+)\s*\}\}/)
    if (match) {
      const sample = sampleForKey(match[1])
      if (sample !== undefined) return `"${escapeJsonString(sample)}"`
    }
    return '"__JINJA__"'
  })
  // Unquoted placeholders, e.g. "port": {{PORT}}
  out = out.replace(/\{\{\s*([A-Za-z0-9_.]+)\s*\}\}/g, (_, key: string) => {
    if (key === 'PORT' || key.endsWith('.port') || key.endsWith('_port')) {
      return SAMPLE_VALUES.PORT
    }
    const sample = sampleForKey(key)
    return sample !== undefined ? JSON.stringify(sample) : '"__JINJA__"'
  })
  out = out.replace(/\{\{[\s\S]*?\}\}/g, '"__JINJA__"')
  return out
}

function replaceJinjaBlocks(text: string): string {
  let out = text
  out = out.replace(
    /\{%\s*for[\s\S]*?%\}([\s\S]*?)\{%\s*endfor\s*%\}/g,
    (_, body: string) => {
      const trimmed = body.trim()
      if (!trimmed) return ''
      if (trimmed.endsWith(',')) return trimmed.slice(0, -1)
      return body
    },
  )
  out = out.replace(/\{%\s*if[\s\S]*?%\}([\s\S]*?)\{%\s*endif\s*%\}/g, '$1')
  out = out.replace(/\{%[\s\S]*?%\}/g, '')
  return out
}

export function fixDuplicateJsonCommas(text: string): string {
  let out = text.replace(/\[\s*,/g, '[').replace(/,\s*]/g, ']').replace(/,\s*}/g, '}')
  let prev: string | null = null
  while (prev !== out) {
    prev = out
    out = out.replace(/,(?:\s*,)+/g, ',')
  }
  return out
}

function trimLeadingEmptyLines(text: string): string {
  if (!text) return text
  const lines = text.split('\n')
  let start = 0
  while (start < lines.length && !lines[start].trim()) {
    start += 1
  }
  if (start === 0) return text
  const trimmed = lines.slice(start).join('\n')
  return text.endsWith('\n') && !trimmed.endsWith('\n') ? `${trimmed}\n` : trimmed
}

export function stripJinjaForJsonParse(text: string): string {
  let out = replaceJinjaBlocks(text)
  out = out.replace(PROXY_URI_LINE, '""')
  out = replaceJinjaVariables(out)
  out = fixDuplicateJsonCommas(out)
  return trimLeadingEmptyLines(out)
}

export function wrapJsonFragment(text: string): string {
  const trimmed = text.trim().replace(/,\s*$/, '')
  if (!trimmed) return '{}'
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return trimmed
  if (/\}\s*,\s*\{/.test(trimmed)) return `[\n${trimmed}\n]`
  return `{\n${trimmed}\n}`
}

function looksLikeJsonTemplate(text: string): boolean {
  const trimmed = text.trim()
  if (!trimmed) return true
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return true
  if (PROXY_URI_LINE.test(trimmed)) return false
  return containsJinja(text)
}

export function validateJinjaJson(text: string): string | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  if (!looksLikeJsonTemplate(trimmed)) return null
  try {
    const parsed = stripJinjaForJsonParse(trimmed)
    JSON5.parse(wrapJsonFragment(parsed))
    return null
  } catch (e) {
    if (containsJinja(text)) return null
    return e instanceof Error ? e.message : String(e)
  }
}

export function formatJinjaJson(text: string): string {
  const placeholders: { token: string; value: string }[] = []
  let idx = 0
  const token = () => `"__JINJA_PH_${idx++}__"`

  let processed = text.replace(/\{%[\s\S]*?%\}/g, (m) => {
    const t = token()
    placeholders.push({ token: t, value: m })
    return t
  })
  processed = processed.replace(/\{\{[\s\S]*?\}\}/g, (m) => {
    const t = token()
    placeholders.push({ token: t, value: m })
    return t
  })

  const wrapped = wrapJsonFragment(processed)
  const parsed = JSON5.parse(wrapped)
  let formatted = JSON5.stringify(parsed, null, 2)

  for (const ph of placeholders) {
    formatted = formatted.split(ph.token).join(ph.value)
    formatted = formatted.split(ph.token.replace(/"/g, '')).join(ph.value)
  }

  if (!text.trim().startsWith('{') && !text.trim().startsWith('[')) {
    formatted = formatted.replace(/^\{\n?/, '').replace(/\n?\}$/, '')
  }
  return formatted
}
