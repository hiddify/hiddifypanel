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

/** Every operator without an address of its own (also users whose operator is not detected). */
export const OTHER = 'OTHER' satisfies OperatorCode

export interface OperatorIpRow {
  host: string
  operator: OperatorCode
}

const CODES = new Set<string>(OPERATORS.map((o) => o.code))
/** ip-format names Afranet AFN; the panel AFR. */
const ALIASES: Record<string, OperatorCode> = { AFN: 'AFR' }

export function isOperatorCode(value: string): value is OperatorCode {
  return CODES.has(value)
}

/** A token that names an operator (a code is 3 letters, like ip-format's; an unknown one counts as "OTHER"). */
function toCode(value: string): OperatorCode | null {
  const upper = value.toUpperCase()
  if (isOperatorCode(upper)) return upper
  if (ALIASES[upper]) return ALIASES[upper]
  return /^[A-Z]{3}$/.test(upper) ? OTHER : null
}

/** Rows of the text: an address, then its operator if one follows; an address alone is for every other operator. */
export function parseOperatorIps(text: string): OperatorIpRow[] {
  const tokens = text.trim().split(/[\s;,]+/).filter(Boolean)
  const rows: OperatorIpRow[] = []
  for (let i = 0; i < tokens.length; i++) {
    const next = toCode(tokens[i + 1] ?? '')
    rows.push({ host: tokens[i] ?? '', operator: next ?? OTHER })
    if (next) i++
  }
  return rows
}

/** Text of the rows with an address: a plain list when all are "OTHER", else one "address OPERATOR" pair per line. */
export function serializeOperatorIps(rows: OperatorIpRow[]): string {
  const filled = rows.filter((r) => r.host.trim())
  if (filled.every((r) => r.operator === OTHER)) return filled.map((r) => r.host.trim()).join('\n')
  return filled.map((r) => `${r.host.trim()} ${r.operator}`).join('\n')
}

/** The ircf.space address of every operator that has one (ip-format's default list). */
export function ircfDefaults(): OperatorIpRow[] {
  return OPERATORS.filter((o) => o.ircf).map((o) => ({ host: o.ircf ?? '', operator: o.code }))
}
