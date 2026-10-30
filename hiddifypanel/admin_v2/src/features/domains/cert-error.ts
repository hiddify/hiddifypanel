/**
 * Why a certificate request failed, from the panel's ACME error ("letsencrypt: … | zerossl: …"), so the Domains page
 * can say it in plain words with the steps that fix it. The first match wins: a name no CA accepts says more than the
 * timeout the other CA reported for it.
 */
export type CertErrorKind = 'badName' | 'caa' | 'dns' | 'port80' | 'caDown' | 'other'

const RULES: [CertErrorKind, RegExp][] = [
  ['badName', /rejectedIdentifier|needs at least one dot|identifier is invalid|does not end with a public suffix|invalid identifiers/i],
  ['caa', /\bCAA\b/],
  ['dns', /no valid (A|AAAA) records|NXDOMAIN|SERVFAIL|DNS problem|could not resolve|does not resolve/i],
  ['port80', /connection refused|timeout during connect|connection reset|no route to host|network is unreachable|firewall/i],
  ['caDown', /Response \[5\d\d\]|did not finish in time|service unavailable|bad gateway|gateway time-?out/i],
]

/** How many numbered steps each kind has (domains.certError.<kind>.step1 …) */
export const CERT_ERROR_STEPS: Record<CertErrorKind, number> = { badName: 2, caa: 2, dns: 3, port80: 2, caDown: 2, other: 3 }

export function certErrorKind(error: string): CertErrorKind {
  return RULES.find(([, re]) => re.test(error))?.[0] ?? 'other'
}
