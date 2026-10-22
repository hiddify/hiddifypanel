/**
 * "IP per operator" text of a CDN domain (CDN IP field): one `<ip or host> <OPERATOR>` pair per line, as made by
 * https://ip-format.hiddify.com/. Each user gets the address of their own operator, else an "OTHER" one
 * (hutils/network/auto_ip_selector.py). Only "OTHER" addresses are written as a plain list, without codes.
 */

/** Operators the panel detects (hutils/network/maxmind.py ASN map), then "OTHER" (auto_ip_selector.OTHER_OPERATOR). */
export const OPERATORS = [
  { code: 'MCI', ircf: 'mci.ircf.space' },
  { code: 'MTN', ircf: 'mtn.ircf.space' },
  { code: 'MKH', ircf: 'mkh.ircf.space' },
  { code: 'RTL', ircf: 'rtl.ircf.space' },
  { code: 'HWB', ircf: 'hwb.ircf.space' },
  { code: 'AST', ircf: 'ast.ircf.space' },
  { code: 'SHT', ircf: 'sht.ircf.space' },
  { code: 'PRS', ircf: 'prs.ircf.space' },
  { code: 'MBT', ircf: 'mbt.ircf.space' },
  { code: 'ASK', ircf: 'ask.ircf.space' },
  { code: 'RSP', ircf: 'rsp.ircf.space' },
  { code: 'AFR', ircf: 'afn.ircf.space' },
  { code: 'ZTL', ircf: 'ztl.ircf.space' },
  { code: 'PSM', ircf: 'psm.ircf.space' },
  { code: 'ITC', ircf: null },
  { code: 'OTHER', ircf: null },
] as const

export type OperatorCode = (typeof OPERATORS)[number]['code']
/** An operator Hiddify has no name for, by its AS number (users on that AS get its rows). */
export type AsCode = `AS${number}`
export type OperatorKey = OperatorCode | AsCode

/** Persian (۰-۹) and Arabic (٠-٩) digits as 0-9: typed on a Persian keyboard. */
export function latinDigits(value: string): string {
  return value.replace(/[۰-۹]/g, (d) => String(d.charCodeAt(0) - 0x06f0)).replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660))
}

/** "AS254" / "as 254" / "AS۲۵۴" → "AS254"; null when it is not an AS number. */
export function asCode(value: string): AsCode | null {
  const m = /^AS\s*(\d{1,10})$/i.exec(latinDigits(value.trim()))
  return m ? (`AS${Number(m[1])}` as AsCode) : null
}

/** Every operator without an address of its own (also users whose operator is not detected). */
export const OTHER = 'OTHER' satisfies OperatorCode

/**
 * Addresses and the operators they are for ("1.1.1.1,2606:4700::1111,104.16.0.0/24 AS254,MKH"); no operator: every
 * operator without its own. ``host``: the addresses as typed (comma separated); an address is an IP, a range or a name.
 */
export interface OperatorIpRow {
  host: string
  operators: OperatorKey[]
}

/** The addresses of a row's field. */
export function addressesOf(host: string): string[] {
  return host.split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean)
}

const IPV4 = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/
const HOSTNAME = /^(?=.{1,253}$)([a-z0-9*]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/i

/** An IPv4 / IPv6 address, a range of one (CIDR) or a host name. */
export function isAddress(value: string): boolean {
  const [ip, bits, extra] = value.split('/')
  if (extra !== undefined || !ip) return false
  const v6 = ip.includes(':')
  const okIp = v6 ? /^[0-9a-f:.]+$/i.test(ip) && ip.split('::').length <= 2 : IPV4.test(ip)
  if (bits !== undefined) return okIp && /^\d{1,3}$/.test(bits) && Number(bits) <= (v6 ? 128 : 32)
  return okIp || (!v6 && HOSTNAME.test(ip))
}

const CODES = new Set<string>(OPERATORS.map((o) => o.code))
/** ip-format names Afranet AFN; the panel AFR. */
const ALIASES: Record<string, OperatorCode> = { AFN: 'AFR' }

export function isOperatorCode(value: string): value is OperatorCode {
  return CODES.has(value)
}

/** A token that names an operator (a code is 3 letters, like ip-format's; an unknown one counts as "OTHER"). */
function toCode(value: string): OperatorKey | null {
  const upper = value.toUpperCase()
  if (isOperatorCode(upper)) return upper
  if (ALIASES[upper]) return ALIASES[upper]
  const as = asCode(upper)
  if (as) return as
  return /^[A-Z]{3}$/.test(upper) ? OTHER : null
}

/**
 * Rows of the text, line by line (as auto_ip_selector.parse_operator_groups reads it): on a line, a run of addresses
 * then a run of codes is one row ("1.1.1.1,2.2.2.2 MKH,AS254"; "1.1.1.1 MCI 2.2.2.2 MTN" is two). Addresses without a
 * code (or with the old "OTHER") are for every operator without its own: no operators here.
 */
export function parseOperatorIps(text: string): OperatorIpRow[] {
  const rows: OperatorIpRow[] = []
  for (const line of text.split(/\r?\n/)) {
    let hosts: string[] = []
    let codes: OperatorKey[] = []
    const flush = () => {
      if (hosts.length) rows.push({ host: hosts.join(', '), operators: codes })
      hosts = []
      codes = []
    }
    for (const token of line.trim().split(/[\s;,]+/).filter(Boolean)) {
      const code = toCode(token)
      if (code) {
        if (hosts.length && code !== OTHER && !codes.includes(code)) codes.push(code)
        continue
      }
      if (codes.length) flush() // an address after codes: the next row
      hosts.push(token)
    }
    flush()
  }
  return rows
}

/** Text of the rows with an address: "address,address CODE,CODE" per line; bare addresses for every other operator. */
export function serializeOperatorIps(rows: OperatorIpRow[]): string {
  return rows
    .map((r) => ({ hosts: addressesOf(r.host), codes: r.operators.filter((c) => c !== OTHER) }))
    .filter((r) => r.hosts.length)
    .map((r) => (r.codes.length ? `${r.hosts.join(',')} ${r.codes.join(',')}` : r.hosts.join(',')))
    .join('\n')
}

/**
 * The text with ``operators``' addresses replaced by ``ips`` (one row for all of them); an address shared with other
 * operators stays for those. No operators: the addresses for every operator without its own (the bare ones replaced).
 */
export function replaceOperatorIps(text: string, operators: OperatorKey[], ips: string[]): { text: string; kept: number } {
  const targets = operators.filter((c) => c !== OTHER)
  const rows = parseOperatorIps(text)
  const kept = targets.length
    ? rows.flatMap((r) => {
        if (!r.operators.length) return [r] // bare addresses: still for the others
        const rest = r.operators.filter((c) => !targets.includes(c))
        return rest.length ? [{ host: r.host, operators: rest }] : []
      })
    : rows.filter((r) => r.operators.length)
  const added = ips.length ? [{ host: ips.join(', '), operators: targets }] : []
  return { text: serializeOperatorIps([...added, ...kept]), kept: kept.length }
}

/** The ircf.space address of every operator that has one (ip-format's default list). */
export function ircfDefaults(): OperatorIpRow[] {
  return OPERATORS.filter((o) => o.ircf).map((o) => ({ host: o.ircf ?? '', operators: [o.code] }))
}
