/**
 * Opens a Telegram link: the app first (tg://, it needs no web access), and the t.me page when no app takes it.
 *
 * A tg:// link alone does nothing in a browser with no Telegram app registered for it; t.me alone needs the web page,
 * which is filtered in some countries even where the app works. When the app opens, the browser loses focus, so the
 * t.me page is only opened while the panel still has it.
 */
export function openTelegram(webUrl: string): void {
  const app = tgUrl(webUrl)
  if (!app) {
    window.open(webUrl, '_blank', 'noopener')
    return
  }
  let left = false
  const onLeave = () => (left = true)
  window.addEventListener('blur', onLeave, { once: true })
  document.addEventListener('visibilitychange', onLeave, { once: true })
  window.location.href = app
  window.setTimeout(() => {
    window.removeEventListener('blur', onLeave)
    document.removeEventListener('visibilitychange', onLeave)
    if (!left && document.visibilityState === 'visible') window.open(webUrl, '_blank', 'noopener')
  }, 1500)
}

/** https://t.me/<name>?start=<x> → tg://resolve?domain=<name>&start=<x>; null for other links. */
export function tgUrl(webUrl: string): string | null {
  let url: URL
  try {
    url = new URL(webUrl)
  } catch {
    return null
  }
  if (url.hostname !== 't.me' && url.hostname !== 'telegram.me') return null
  const name = url.pathname.replace(/^\/+|\/+$/g, '')
  if (!name || name.includes('/')) return null
  const query = new URLSearchParams({ domain: name })
  const start = url.searchParams.get('start')
  if (start) query.set('start', start)
  return `tg://resolve?${query.toString()}`
}
