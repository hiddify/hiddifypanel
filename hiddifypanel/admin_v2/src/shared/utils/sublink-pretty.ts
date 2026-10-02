import { decodeUtf8Base64, encodeUtf8Base64, safeDecodeUriComponent, tryDecodeUtf8Base64 } from './text-codecs'

export interface QueryParam {
  key: string
  value: string
}

export interface PrettyUriLink {
  kind: 'uri'
  protocol: string
  server: string
  port: string
  user: string
  password: string
  path: string
  fragment: string
  method: string
  params: QueryParam[]
  extra: string
}

export interface PrettyVmessLink {
  kind: 'vmess'
  protocol: 'vmess'
  json: string
}

export interface PrettyParseError {
  kind: 'error'
  error: string
  raw: string
}

export type PrettyLink = PrettyUriLink | PrettyVmessLink | PrettyParseError

const URI_SCHEME = /^[a-z][a-z0-9+.-]*:\/\//i
const PASSWORD_PROTOS = new Set(['trojan', 'hysteria', 'hysteria2', 'hy2', 'tuic', 'anytls', 'ss', 'shadowsocks'])

export function isPrettyParseError(link: PrettyLink): link is PrettyParseError {
  return link.kind === 'error'
}

export function isPrettyVmessLink(link: PrettyLink): link is PrettyVmessLink {
  return link.kind === 'vmess'
}

export function isPrettyUriLink(link: PrettyLink): link is PrettyUriLink {
  return link.kind === 'uri'
}

function looksLikeJson(text: string): boolean {
  const trimmed = text.trim()
  return (trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))
}

function prettyJsonOrRaw(text: string): string {
  const trimmed = text.trim()
  if (!looksLikeJson(trimmed)) return text
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2)
  } catch {
    return text
  }
}

function decodeExtra(raw: string): string {
  let value = safeDecodeUriComponent(raw)
  if (!looksLikeJson(value.trim())) {
    const again = safeDecodeUriComponent(value)
    if (looksLikeJson(again.trim())) value = again
  }
  return prettyJsonOrRaw(value)
}

function encodeExtra(text: string): string | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  try {
    return encodeURIComponent(JSON.stringify(JSON.parse(trimmed)))
  } catch {
    return encodeURIComponent(trimmed)
  }
}

function stringifyQuery(params: QueryParam[], extra: string): string {
  const parts: string[] = []
  let extraText = extra
  for (const param of params) {
    const key = param.key.trim()
    if (!key) continue
    if (key === 'extra') {
      if (!extraText.trim()) extraText = param.value
      continue
    }
    parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(param.value)}`)
  }
  const encodedExtra = encodeExtra(extraText)
  if (encodedExtra != null) {
    parts.push(`extra=${encodedExtra}`)
  }
  return parts.join('&')
}

function splitFragment(text: string): { body: string; fragment: string } {
  const hash = text.indexOf('#')
  if (hash < 0) return { body: text, fragment: '' }
  return { body: text.slice(0, hash), fragment: safeDecodeUriComponent(text.slice(hash + 1)) }
}

function splitUserinfo(hostport: string): { userinfo?: string; hostport: string } {
  const at = hostport.lastIndexOf('@')
  if (at < 0) return { hostport }
  return { userinfo: hostport.slice(0, at), hostport: hostport.slice(at + 1) }
}

function parseHostPortPath(value: string): { server: string; port: string; path: string } {
  let rest = value
  if (rest.startsWith('[')) {
    const close = rest.indexOf(']')
    if (close < 0) return { server: rest, port: '', path: '' }
    const server = rest.slice(1, close)
    rest = rest.slice(close + 1)
    let port = ''
    let path = ''
    if (rest.startsWith(':')) {
      const slash = rest.indexOf('/')
      port = slash >= 0 ? rest.slice(1, slash) : rest.slice(1)
      if (slash >= 0) path = rest.slice(slash)
    } else if (rest.startsWith('/')) {
      path = rest
    }
    return { server, port, path }
  }
  const slash = rest.indexOf('/')
  const authority = slash >= 0 ? rest.slice(0, slash) : rest
  const path = slash >= 0 ? rest.slice(slash) : ''
  const colon = authority.lastIndexOf(':')
  if (colon >= 0) {
    return { server: authority.slice(0, colon), port: authority.slice(colon + 1), path }
  }
  return { server: authority, port: '', path }
}

function parseUserPassword(userinfo: string, protocol: string): { user: string; password: string } {
  const decoded = safeDecodeUriComponent(userinfo)
  const colon = decoded.indexOf(':')
  if (colon >= 0) {
    return { user: decoded.slice(0, colon), password: decoded.slice(colon + 1) }
  }
  if (PASSWORD_PROTOS.has(protocol)) return { user: '', password: decoded }
  return { user: decoded, password: '' }
}

function decodeSsAuth(user: string, password: string): { user: string; password: string; method: string } {
  const blob = user && password ? `${user}:${password}` : user || password
  if (!blob) return { user: '', password: '', method: '' }
  const decoded = tryDecodeUtf8Base64(blob) ?? blob
  const colon = decoded.indexOf(':')
  if (colon > 0 && /^[a-z0-9+-]+$/i.test(decoded.slice(0, colon))) {
    return { user: '', password: decoded.slice(colon + 1), method: decoded.slice(0, colon) }
  }
  return parseUserPassword(blob, 'ss')
}

function parseQuery(search: string): { params: QueryParam[]; extra: string } {
  const params: QueryParam[] = []
  let extra = ''
  if (!search) return { params, extra }
  for (const part of search.split('&')) {
    if (!part) continue
    const eq = part.indexOf('=')
    const key = safeDecodeUriComponent(eq >= 0 ? part.slice(0, eq) : part)
    if (!key) continue
    const value = eq >= 0 ? safeDecodeUriComponent(part.slice(eq + 1)) : ''
    if (key === 'extra') extra = decodeExtra(value)
    else params.push({ key, value })
  }
  return { params, extra }
}

function parseVmess(rest: string): PrettyVmessLink {
  const { body } = splitFragment(rest)
  const json = decodeUtf8Base64(body)
  const parsed = JSON.parse(json) as unknown
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('vmess payload is not an object')
  }
  return { kind: 'vmess', protocol: 'vmess', json: JSON.stringify(parsed, null, 2) }
}

function parseUriLink(protocol: string, rest: string): PrettyUriLink {
  const { body, fragment } = splitFragment(rest)
  const qmark = body.indexOf('?')
  const beforeQuery = qmark >= 0 ? body.slice(0, qmark) : body
  const { params, extra } = parseQuery(qmark >= 0 ? body.slice(qmark + 1) : '')
  const { userinfo, hostport } = splitUserinfo(beforeQuery)
  const { server, port, path } = parseHostPortPath(hostport)
  let user = ''
  let password = ''
  let method = ''
  if (userinfo) {
    if (protocol === 'ss') {
      const parsed = parseUserPassword(userinfo, 'ss')
      const auth = decodeSsAuth(parsed.user, parsed.password)
      user = auth.user
      password = auth.password
      method = auth.method
    } else {
      const parsed = parseUserPassword(userinfo, protocol)
      user = parsed.user
      password = parsed.password
    }
  }
  return {
    kind: 'uri',
    protocol,
    server,
    port,
    user,
    password,
    path,
    fragment,
    method,
    params,
    extra,
  }
}

export function parseShareLink(line: string): PrettyLink {
  const raw = line.trim()
  const match = raw.match(URI_SCHEME)
  if (!match) return { kind: 'error', error: 'Not a share link', raw }
  const protocol = match[0].slice(0, -3).toLowerCase()
  const rest = raw.slice(match[0].length)
  try {
    if (protocol === 'vmess') return parseVmess(rest)
    if (protocol === 'ss' && !rest.includes('@')) {
      const { body, fragment } = splitFragment(rest)
      const decoded = decodeUtf8Base64(body)
      if (decoded.includes('@')) {
        const nested = parseUriLink('ss', fragment ? `${decoded}#${encodeURIComponent(fragment)}` : decoded)
        return nested
      }
    }
    return parseUriLink(protocol, rest)
  } catch (err) {
    return { kind: 'error', error: err instanceof Error ? err.message : String(err), raw }
  }
}

export function unwrapSubscriptionText(text: string): { text: string; unwrapped: boolean } {
  const trimmed = text.trim()
  if (!trimmed) return { text, unwrapped: false }
  if (URI_SCHEME.test(trimmed) || trimmed.includes('\n')) return { text, unwrapped: false }
  const decoded = tryDecodeUtf8Base64(trimmed)
  if (!decoded) return { text, unwrapped: false }
  const lines = decoded.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  if (lines.some((line) => URI_SCHEME.test(line))) return { text: decoded.replace(/\r\n/g, '\n'), unwrapped: true }
  return { text, unwrapped: false }
}

export function parseSublinks(text: string): PrettyLink[] {
  const { text: source } = unwrapSubscriptionText(text)
  const links: PrettyLink[] = []
  for (const line of source.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('//')) continue
    links.push(parseShareLink(trimmed))
  }
  return links
}

function stringifyVmess(link: PrettyVmessLink): string {
  const parsed = JSON.parse(link.json || '{}') as unknown
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('vmess JSON must be an object')
  }
  return `vmess://${encodeUtf8Base64(JSON.stringify(parsed))}`
}

function stringifyUri(link: PrettyUriLink): string {
  let userinfo = ''
  if (link.protocol === 'ss' && link.method) {
    userinfo = encodeUtf8Base64(`${link.method}:${link.password}`)
  } else if (link.user && link.password) {
    userinfo = `${encodeURIComponent(link.user)}:${encodeURIComponent(link.password)}`
  } else if (link.user) {
    userinfo = encodeURIComponent(link.user)
  } else if (link.password) {
    userinfo = encodeURIComponent(link.password)
  }
  const host = link.server.includes(':') && !link.server.startsWith('[') ? `[${link.server}]` : link.server
  const port = link.port ? `:${link.port}` : ''
  const path = link.path && link.path !== '/' ? (link.path.startsWith('/') ? link.path : `/${link.path}`) : ''
  const query = stringifyQuery(link.params, link.extra)
  const fragment = link.fragment ? `#${encodeURIComponent(link.fragment)}` : ''
  const auth = userinfo ? `${userinfo}@` : ''
  return `${link.protocol}://${auth}${host}${port}${path}${query ? `?${query}` : ''}${fragment}`
}

export function stringifyShareLink(link: PrettyLink): string {
  if (isPrettyParseError(link)) return link.raw
  if (isPrettyVmessLink(link)) return stringifyVmess(link)
  return stringifyUri(link)
}

export function stringifySublinks(links: PrettyLink[]): string {
  return links.map((item) => stringifyShareLink(item)).join('\n')
}

export function linkTitle(link: PrettyLink, index: number): string {
  if (isPrettyParseError(link)) return `Link ${index + 1}: ${link.error}`
  if (isPrettyVmessLink(link)) {
    try {
      const config = JSON.parse(link.json) as { ps?: string; add?: string }
      return `${link.protocol} ${config.ps || config.add || index + 1}`
    } catch {
      return `vmess ${index + 1}`
    }
  }
  return [link.protocol, link.server, link.fragment].filter(Boolean).join(' ') || `Link ${index + 1}`
}

export function tryStringifySublinks(links: PrettyLink[]): { text: string; error: string | null } {
  try {
    return { text: stringifySublinks(links), error: null }
  } catch (err) {
    return { text: '', error: err instanceof Error ? err.message : String(err) }
  }
}
