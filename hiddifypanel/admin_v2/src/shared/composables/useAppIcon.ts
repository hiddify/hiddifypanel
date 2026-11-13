import { computed, ref } from 'vue'

/**
 * The admin app icon comes in any color (PWA Color). The panel draws it (hutils/app_icon.py); the color this browser
 * chose is kept in a cookie, so the page's app icon and manifest links are already right when the page loads next
 * time. The browser tab's icon stays the stock one.
 */
export type AppIconName = 'apple-180' | 'tile-256'
export interface AppIconInfo {
  /** The panel can draw the icon in other colors */
  enabled: boolean
  /** This browser's color (RRGGBB) */
  color: string
  /** The stock icon's color (RRGGBB): that one is a plain file */
  default: string
  cookie: string
  cookie_path: string
  /** The drawn icon's URL, with {color} and {name} to fill in */
  url: string
  /** The stock icon's files and manifest */
  stock: Record<AppIconName | 'manifest', string>
}

const HEX = /^[0-9a-f]{6}$/i
const info = ref<AppIconInfo | null>(null)
const color = ref('')

/** Take what the page (or, on the dev server, the bootstrap) says about the icon. */
export function syncAppIcon(): void {
  const data = typeof window === 'undefined' ? null : (window.__APP_ICON__ ?? null)
  info.value = data
  color.value = data && HEX.test(data.color) ? data.color.toUpperCase() : ''
}
syncAppIcon()

function setLink(selector: string, href: string, replace = false): void {
  const link = document.head.querySelector<HTMLLinkElement>(selector)
  if (!link || !href) return
  if (!replace) {
    link.href = href
    return
  }
  // A new element: browsers read a manifest link again only when it is added.
  const next = link.cloneNode() as HTMLLinkElement
  next.href = href
  link.replaceWith(next)
}

export function useAppIcon() {
  const enabled = computed(() => !!info.value?.enabled && !!color.value)
  const stockColor = computed(() => info.value?.default ?? '')

  /** The URL of the icon `name` in color `c` (the stock file for the stock color). */
  function iconUrl(name: AppIconName, c = color.value): string {
    const data = info.value
    if (!data) return ''
    return c && c !== data.default ? data.url.replace('{color}', c).replace('{name}', name) : data.stock[name]
  }

  function manifestUrl(c: string): string {
    const data = info.value
    if (!data) return ''
    const stock = data.stock.manifest
    return c && c !== data.default ? `${stock}${stock.includes('?') ? '&' : '?'}icon=${c}` : stock
  }

  /** Choose color `c` (RRGGBB): remembered for this browser, and the page's app icon and manifest links follow at once. */
  function choose(c: string): void {
    const data = info.value
    if (!data || !HEX.test(c)) return
    c = c.toUpperCase()
    color.value = c
    const stock = c === data.default
    const secure = location.protocol === 'https:' ? '; secure' : ''
    document.cookie = `${data.cookie}=${stock ? '' : c}; path=${data.cookie_path}; max-age=${stock ? 0 : 31536000}; samesite=lax${secure}`
    setLink('link[rel="apple-touch-icon"]', iconUrl('apple-180', c))
    setLink('link[rel="manifest"]', manifestUrl(c), true)
  }

  return { enabled, color, stockColor, iconUrl, choose }
}
