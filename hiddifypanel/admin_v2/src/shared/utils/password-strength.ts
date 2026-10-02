/** Same rules as the server (hiddifypanel/admin_credentials.py): admins can not set a weak password. */

export const MIN_PASSWORD = 10
export type PasswordRule = 'length' | 'lower' | 'upper' | 'digit' | 'common' | 'name'

const COMMON = new Set([
  'password', 'password1', 'passw0rd', '123456789', '1234567890', '12345678', 'qwerty123', 'qwertyuiop',
  'iloveyou', 'admin123', 'administrator', 'letmein123', 'welcome123', 'abc123456', 'hiddify', 'hiddify123',
]) // prettier-ignore

/** Each rule and whether the password meets it. `avoid`: the admin's name, alias, UUID. */
export function passwordRules(password: string, avoid: (string | null | undefined)[] = []): { rule: PasswordRule; ok: boolean }[] {
  const pw = password || ''
  const lowered = pw.toLowerCase()
  const containsName = avoid.some((w) => !!w && w.length >= 4 && lowered.includes(w.toLowerCase()))
  return [
    { rule: 'length', ok: pw.length >= MIN_PASSWORD },
    { rule: 'lower', ok: /[a-z]/.test(pw) },
    { rule: 'upper', ok: /[A-Z]/.test(pw) },
    { rule: 'digit', ok: /\d/.test(pw) },
    { rule: 'common', ok: !!pw && !COMMON.has(lowered) && new Set(pw).size >= 5 },
    { rule: 'name', ok: !!pw && !containsName },
  ]
}

export function isStrongPassword(password: string, avoid: (string | null | undefined)[] = []): boolean {
  return passwordRules(password, avoid).every((r) => r.ok)
}

/** A strong random password (letters and digits, no look-alikes). */
export function generatePassword(length = 16): string {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
  for (;;) {
    const bytes = crypto.getRandomValues(new Uint32Array(length))
    const pw = Array.from(bytes, (n) => alphabet[n % alphabet.length]).join('')
    if (isStrongPassword(pw)) return pw
  }
}

/** Alias (sign-in username) rules, as on the server: 6–64 of a-z 0-9 . _ - , not UUID-shaped. */
export const ALIAS_MIN = 6
export function aliasProblem(alias: string): 'too_short' | 'bad_chars' | 'looks_like_uuid' | null {
  const a = alias.trim().toLowerCase()
  if (!a) return null
  if (a.length < ALIAS_MIN) return 'too_short'
  if (!/^[a-z0-9][a-z0-9._-]{0,63}$/.test(a)) return 'bad_chars'
  if (/^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$/.test(a)) return 'looks_like_uuid'
  return null
}
