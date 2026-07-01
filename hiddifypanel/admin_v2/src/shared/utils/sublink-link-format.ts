export type SublinkFormatKind = 'uri' | 'raw' | 'base64'

export interface UriLinkFormat {
  protocol: string
  user: string
  password: string
  host: string
  port: string
  path: string
  fragment: string
  query_params: Record<string, string>
}

export interface Base64LinkFormat {
  protocol: string
  content: string
}

export interface LinkFormatOptions {
  format: SublinkFormatKind
  uri_format: UriLinkFormat
  base64_format: Base64LinkFormat
}

export const URI_FRAGMENT_INCLUDE = "{%- include 'hiddify-core/client/tag' -%}"

/** Exact Jinja link line for URI format (uri object must be in render context). */
export const URI_LINK_TEMPLATE =
  '{{uri.protocol}}://{{ uri.user }}:{{ uri.password }}@{{ uri.host }}:{{ uri.port }}/{{ uri.path }}?{{ uri.query_params|urlencoded }}#{{ uri.fragment |urlencoded }}'

/** Exact Jinja link line for base64 format. */
export const BASE64_LINK_TEMPLATE = '{{ uri.protocol }}://{{ uri.content|trim|b64encode }}'

export const DEFAULT_URI_FORMAT: UriLinkFormat = {
  protocol: 'vless',
  user: '{{ user.uuid }}',
  password: '',
  host: '{{ proxy.server }}',
  port: '{{ proxy.port }}',
  path: '/',
  fragment: URI_FRAGMENT_INCLUDE,
  query_params: {
    encryption: 'none',
    type: 'tcp',
    security: 'tls',
  },
}

export const DEFAULT_BASE64_CONTENT = `{
  "v": "2",
  "ps": "{%- include 'hiddify-core/client/tag' -%}",
  "add": "{{ proxy.server }}",
  "port": "{{ proxy.port }}",
  "id": "{{ user.uuid }}",
  "aid": "0",
  "net": "tcp",
  "type": "none",
  "host": "",
  "path": "{{ proxy.path }}",
  "tls": "tls"
}`

export const DEFAULT_BASE64_FORMAT: Base64LinkFormat = {
  protocol: 'vmess',
  content: DEFAULT_BASE64_CONTENT,
}

export function defaultLinkFormatOptions(): LinkFormatOptions {
  return {
    format: 'uri',
    uri_format: { ...DEFAULT_URI_FORMAT, query_params: { ...DEFAULT_URI_FORMAT.query_params } },
    base64_format: { ...DEFAULT_BASE64_FORMAT },
  }
}

function migrateLegacyOptions(
  raw: Partial<LinkFormatOptions> & {
    raw_format?: string
    vless_format?: Partial<UriLinkFormat & { tag?: string; fragment?: string; pass?: string }>
    vmess_format?: Partial<Base64LinkFormat>
    base64_format?: Partial<Base64LinkFormat>
  },
): Partial<LinkFormatOptions> {
  const migrated = { ...raw }
  const fmt = migrated.format as string | undefined
  if (fmt === 'vless') {
    migrated.format = 'uri'
  }
  if (fmt === 'vmess') {
    migrated.format = 'base64'
  }
  if (!migrated.uri_format && migrated.vless_format) {
    const legacy = migrated.vless_format
    migrated.uri_format = {
      protocol: legacy.protocol ?? DEFAULT_URI_FORMAT.protocol,
      user: legacy.user ?? DEFAULT_URI_FORMAT.user,
      password: legacy.password ?? legacy.pass ?? DEFAULT_URI_FORMAT.password,
      host: legacy.host ?? DEFAULT_URI_FORMAT.host,
      port: legacy.port ?? DEFAULT_URI_FORMAT.port,
      path: legacy.path ?? DEFAULT_URI_FORMAT.path,
      fragment: legacy.fragment ?? legacy.tag ?? DEFAULT_URI_FORMAT.fragment,
      query_params: legacy.query_params ?? { ...DEFAULT_URI_FORMAT.query_params },
    }
  }
  if (!migrated.base64_format && migrated.vmess_format) {
    migrated.base64_format = { ...migrated.vmess_format }
  }
  if (migrated.uri_format) {
    const uri = migrated.uri_format as UriLinkFormat & { tag?: string; pass?: string }
    if (uri.tag && !uri.fragment) {
      uri.fragment = uri.tag
      delete uri.tag
    }
    if (uri.pass && !uri.password) {
      uri.password = uri.pass
      delete uri.pass
    }
    if (uri.fragment?.includes("{% include 'hiddify-core/client/tag' %}")) {
      uri.fragment = uri.fragment.replace(
        /\{%\s*include\s+['"]hiddify-core\/client\/tag['"]\s*%\}/g,
        URI_FRAGMENT_INCLUDE,
      )
    }
  }
  if (migrated.base64_format?.content?.includes("{% set _ps %}")) {
    migrated.base64_format.content = DEFAULT_BASE64_CONTENT
  }
  return migrated
}

export function composeLinkTemplate(options: LinkFormatOptions): string | null {
  if (options.format === 'raw') return null
  if (options.format === 'base64') return BASE64_LINK_TEMPLATE
  return URI_LINK_TEMPLATE
}

export function normalizeLinkFormatOptions(
  raw?: Partial<LinkFormatOptions> & {
    raw_format?: string
    vless_format?: Partial<UriLinkFormat>
    vmess_format?: Partial<Base64LinkFormat>
  } | null,
): LinkFormatOptions {
  const base = defaultLinkFormatOptions()
  if (!raw) return base
  const input = migrateLegacyOptions(raw)
  const format = input.format
  if (format === 'uri' || format === 'raw' || format === 'base64') {
    base.format = format
  }
  base.uri_format = { ...base.uri_format, ...(input.uri_format ?? {}) }
  base.base64_format = { ...base.base64_format, ...(input.base64_format ?? {}) }
  if (input.uri_format?.query_params) {
    base.uri_format.query_params = { ...base.uri_format.query_params, ...input.uri_format.query_params }
  }
  return base
}

export function isLinkFormatOptions(value: unknown): value is LinkFormatOptions {
  if (!value || typeof value !== 'object') return false
  const fmt = (value as LinkFormatOptions).format
  return fmt === 'uri' || fmt === 'raw' || fmt === 'base64'
}

export function initSublinkLinkOptions(cc: { link_format_options?: LinkFormatOptions | null }): LinkFormatOptions {
  if (!isLinkFormatOptions(cc.link_format_options)) {
    cc.link_format_options = normalizeLinkFormatOptions(cc.link_format_options as Partial<LinkFormatOptions> | null)
  }
  return cc.link_format_options
}

export function ensureSublinkLinkOptions(cc: { link_format_options?: LinkFormatOptions | null }): LinkFormatOptions {
  return initSublinkLinkOptions(cc)
}

export function applyLinkFormatToTemplate(cc: {
  link_format_options?: LinkFormatOptions | null
  outbounds_template?: string
}): void {
  const opts = initSublinkLinkOptions(cc)
  const tpl = composeLinkTemplate(opts)
  if (tpl !== null) {
    cc.outbounds_template = tpl
  }
}

export function formatBase64ContentIfJson(content: string): string {
  const trimmed = content.trim()
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
    return content
  }
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2)
  } catch {
    return content
  }
}

/** @deprecated */
export const formatVmessContentIfJson = formatBase64ContentIfJson

export const sublinkFormatOptions = [
  { value: 'uri', labelKey: 'proxy.sublinkFormatUri' },
  { value: 'raw', labelKey: 'proxy.sublinkFormatRawLink' },
  { value: 'base64', labelKey: 'proxy.sublinkFormatBase64' },
] as const
