/** Names longer than this show their first letters and "…" (the whole name on hover); phones have less room. */
export const NAME_MAX = 20
export const PHONE_NAME_MAX = 15

/** Counted in letters, not UTF-16 units, so Persian names and emoji cut right. */
export const isLongName = (name: string, max = NAME_MAX) => Array.from(name).length > max
export const shortName = (name: string, max = NAME_MAX) => (isLongName(name, max) ? Array.from(name).slice(0, max).join('').trimEnd() + '…' : name)
