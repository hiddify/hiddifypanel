import { onActivated, onDeactivated, watch, type Ref } from 'vue'

/** How one ref is written to / read from the URL hash. Plain strings, numbers, booleans and arrays need none. */
export interface HashCodec<T> {
  encode: (value: T) => string | null
  decode: (raw: string) => T
}

type Field<T = any> = Ref<T> | { ref: Ref<T>; codec: HashCodec<T> }

function defaultCodec<T>(initial: T): HashCodec<T> {
  if (Array.isArray(initial)) {
    const numeric = initial.length > 0 && typeof initial[0] === 'number'
    return {
      encode: (v) => ((v as unknown[]).length ? (v as unknown[]).map((x) => encodeURIComponent(String(x))).join(',') : null) as string | null,
      decode: (raw) => {
        const parts = raw ? raw.split(',').map(decodeURIComponent) : []
        return (numeric ? parts.map(Number).filter((n) => !Number.isNaN(n)) : parts) as T
      },
    }
  }
  if (typeof initial === 'boolean') return { encode: (v) => (v ? '1' : null), decode: (raw) => (raw === '1') as T }
  if (typeof initial === 'number') return { encode: (v) => (v === initial ? null : String(v)), decode: (raw) => (Number.isNaN(Number(raw)) ? initial : (Number(raw) as T)) }
  if (initial !== null && typeof initial === 'object') {
    return {
      encode: (v) => (JSON.stringify(v) === JSON.stringify(initial) ? null : JSON.stringify(v)),
      decode: (raw) => {
        try {
          return JSON.parse(raw) as T
        } catch {
          return initial
        }
      },
    }
  }
  // string, or null meaning "no choice": booleans picked from a list use `true`/`false` words.
  return { encode: (v) => (v === null || v === undefined || v === '' || v === initial ? null : String(v)), decode: (raw) => raw as T }
}

/** A tri-state (true / false / not chosen) flag. */
export const triStateCodec: HashCodec<boolean | null> = {
  encode: (v) => (v === null ? null : v ? '1' : '0'),
  decode: (raw) => (raw === '1' ? true : raw === '0' ? false : null),
}

/** A list of numbers (ids). */
export const numberListCodec: HashCodec<number[]> = {
  encode: (v) => (v.length ? v.join(',') : null),
  decode: (raw) => raw.split(',').map(Number).filter((n) => raw !== '' && !Number.isNaN(n)),
}

/** A number that may be unset (e.g. a sort direction). */
export const optionalNumberCodec: HashCodec<number | undefined> = {
  encode: (v) => (v === undefined || v === null ? null : String(v)),
  decode: (raw) => (Number.isNaN(Number(raw)) ? undefined : Number(raw)),
}

function readHash(): URLSearchParams {
  return new URLSearchParams(window.location.hash.replace(/^#/, ''))
}

/**
 * Keeps filters, search, sort and page in the URL hash (`#q=abc&proto=vless`), so a refresh or a shared link
 * restores the list. Keys are the names given here; a value equal to its starting value is left out.
 * The hash is only written while the view is the visible one (kept-alive views stay quiet in the background).
 */
export function useHashState(fields: Record<string, Field>): void {
  const entries = Object.entries(fields).map(([key, f]) => {
    const target: Ref = 'codec' in f ? f.ref : f
    const initial = target.value
    const codec: HashCodec<unknown> = 'codec' in f ? f.codec : defaultCodec(initial)
    return { key, target, codec }
  })

  const params = readHash()
  for (const { key, target, codec } of entries) {
    const raw = params.get(key)
    if (raw !== null) target.value = codec.decode(raw)
  }

  let active = true
  function write() {
    if (!active) return
    const next = new URLSearchParams()
    for (const { key, target, codec } of entries) {
      const raw = codec.encode(target.value)
      if (raw !== null && raw !== '') next.set(key, raw)
    }
    const hash = next.toString()
    if (hash === window.location.hash.replace(/^#/, '')) return
    const url = window.location.pathname + window.location.search + (hash ? `#${hash}` : '')
    // Keep vue-router's history state; only the hash changes.
    window.history.replaceState(window.history.state, '', url)
  }

  watch(entries.map((e) => e.target), write, { deep: true })
  onActivated(() => {
    active = true
    write()
  })
  onDeactivated(() => {
    active = false
  })
}
