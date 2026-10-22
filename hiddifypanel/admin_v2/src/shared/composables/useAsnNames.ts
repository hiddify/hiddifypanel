import { reactive } from 'vue'
import { getHttp } from '@/core/api/client'

/** AS number → company (GeoLite2-ASN on the panel), shared by every operator list on the page; "" when unknown. */
const names = reactive(new Map<number, string>())
const pending = new Set<number>()
let timer = 0

async function fetchPending() {
  const numbers = [...pending].slice(0, 50)
  numbers.forEach((n) => pending.delete(n))
  if (!numbers.length) return
  try {
    const { data } = await getHttp().get<{ names: Record<string, string> }>('clean-ip/asn-names/', { params: { asn: numbers.join(',') }, timeout: 30_000 })
    for (const n of numbers) names.set(n, data.names[String(n)] ?? '')
  } catch {
    // no name shown; asked again on the next request for it
  }
  if (pending.size) void fetchPending()
}

/** The company of "AS254"-style codes, fetched once each (batched, a moment after the last request). */
export function useAsnNames() {
  function request(codes: Iterable<string>) {
    for (const code of codes) {
      const n = Number(/^AS(\d+)$/.exec(code)?.[1])
      if (n && !names.has(n)) pending.add(n)
    }
    if (!pending.size) return
    window.clearTimeout(timer)
    timer = window.setTimeout(fetchPending, 300)
  }
  /** The company of an AS code, "" while unknown or not found. */
  function nameOf(code: string): string {
    const n = Number(/^AS(\d+)$/.exec(code)?.[1])
    return n ? (names.get(n) ?? '') : ''
  }
  return { request, nameOf }
}
