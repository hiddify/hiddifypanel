import { computed, ref } from 'vue'

/**
 * The admin app icon comes in any color (App Color). The panel draws it (hutils/app_icon.py). The browser tab's icon
 * stays the stock one.
 *
 * Until the admin picks a color by hand, the icon follows the panel's theme: it takes the ready color closest to the
 * theme's color (an orange theme gives the orange icon), and the page's app icon and manifest links follow, so the
 * app installed from the browser gets that color too. A color picked by hand is kept in a cookie and wins from then on.
 */
export type AppIconName = 'apple-180' | 'tile-256'
export interface AppIconInfo {
  /** The panel can draw the icon in other colors */
  enabled: boolean
  /** This browser's color (RRGGBB) */
  color: string
  /** The color was picked by hand (the cookie is set): the theme no longer decides it */
  chosen?: boolean
  /** The stock icon's color (RRGGBB): that one is a plain file */
  default: string
  cookie: string
  cookie_path: string
  /** The drawn icon's URL, with {color} and {name} to fill in */
  url: string
  /** The stock icon's files and manifest */
  stock: Record<AppIconName | 'manifest', string>
}

// prettier-ignore
/** The ready colors (the App Color window): Apple's system colors, colors between two of them, and dark tones. */
export const ICON_PRESETS = [
  // blue (the stock icon), then around the color wheel
  '0A84FF', '00B0FC', '3CD3FE', '00C3D0', '00C8B3', '34C759', '80CD00', 'FFCC00', 'FF8D28',
  'FF6B2C', 'FF383C', 'FE007C', 'EF00AC', 'CB30E0', '9C39FF', '6155F5', '4A6AFF', '004896',
  // dark tones and neutrals: forest, plum, burgundy, brown, chocolate, graphite, black
  '007B3C', '720087', '9A0021', 'AC7F5E', '784016', '8E8E93', '15181E',
]

const HEX = /^[0-9a-f]{6}$/i
const info = ref<AppIconInfo | null>(null)
/** The color picked by hand, or '' while the theme decides */
const chosen = ref('')
/** The ready color closest to the theme's color */
const themed = ref('')

// --- the ready color closest to a color: OKLCH, with a difference of hue counting double (a coral red is red) ---
type Lch = [number, number, number]
function toLch(hex: string): Lch {
  const lin = (v: number) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
  const [r, g, b] = [0, 2, 4].map((i) => lin(parseInt(hex.slice(i, i + 2), 16) / 255))
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
  const a = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s
  const bb = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, Math.hypot(a, bb), Math.atan2(bb, a)]
}
function distance([L1, C1, h1]: Lch, [L2, C2, h2]: Lch): number {
  const dh = 2 * Math.sqrt(C1 * C2) * Math.sin((h1 - h2) / 2)
  return (L1 - L2) ** 2 + (C1 - C2) ** 2 + (2 * dh) ** 2
}
export function closestPreset(hex: string): string {
  const target = toLch(hex)
  return ICON_PRESETS.reduce((best, p) => (distance(target, toLch(p)) < distance(target, toLch(best)) ? p : best))
}

/** The theme's color as RRGGBB: its primary 500 (the same in light and dark mode), as the browser resolves it. */
function themeColor(): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue('--p-primary-500').trim()
  if (!value) return ''
  const probe = document.createElement('span')
  probe.style.color = value
  probe.style.display = 'none'
  document.body.appendChild(probe)
  const rgb = getComputedStyle(probe).color.match(/[\d.]+/g)?.slice(0, 3).map(Number)
  probe.remove()
  return rgb && rgb.length === 3 ? rgb.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase() : ''
}

function setLink(selector: string, href: string, replace = false): void {
  const link = document.head.querySelector<HTMLLinkElement>(selector)
  if (!link || !href || link.getAttribute('href') === href) return
  if (!replace) {
    link.href = href
    return
  }
  // A new element: browsers read a manifest link again only when it is added.
  const next = link.cloneNode() as HTMLLinkElement
  next.href = href
  link.replaceWith(next)
}

function iconUrlOf(data: AppIconInfo, name: AppIconName, c: string): string {
  return c && c !== data.default ? data.url.replace('{color}', c).replace('{name}', name) : data.stock[name]
}
function manifestUrlOf(data: AppIconInfo, c: string): string {
  const stock = data.stock.manifest
  return c && c !== data.default ? `${stock}${stock.includes('?') ? '&' : '?'}icon=${c}` : stock
}
/** The page's app icon and manifest links in color `c`: what a phone or browser installs. */
function applyLinks(c: string): void {
  const data = info.value
  if (!data?.enabled || !c) return
  setLink('link[rel="apple-touch-icon"]', iconUrlOf(data, 'apple-180', c))
  setLink('link[rel="manifest"]', manifestUrlOf(data, c), true)
}

/** The theme changed (or the page started): without a color picked by hand, the icon follows it. */
function followTheme(): void {
  if (!info.value?.enabled || typeof document === 'undefined' || !document.body) return
  const theme = themeColor()
  themed.value = theme ? closestPreset(theme) : ''
  if (!chosen.value) applyLinks(themed.value || info.value.default)
}

let watching = false
function watchTheme(): void {
  if (watching || typeof window === 'undefined') return
  watching = true
  // The theme is classes and an attribute on <html> (layout.ts): read the color again when they change.
  let frame = 0
  new MutationObserver(() => {
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(followTheme)
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-caddy-accent', 'style'] })
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', followTheme, { once: true })
}

/** Take what the page (or, on the dev server, the bootstrap) says about the icon. */
export function syncAppIcon(): void {
  const data = typeof window === 'undefined' ? null : (window.__APP_ICON__ ?? null)
  info.value = data
  chosen.value = data?.chosen && HEX.test(data.color) ? data.color.toUpperCase() : ''
  if (data?.enabled) {
    watchTheme()
    followTheme()
  }
}
syncAppIcon()

export function useAppIcon() {
  /** The icon's color now: the one picked by hand, else the theme's closest one, else the stock one */
  const color = computed(() => chosen.value || themed.value || (info.value && HEX.test(info.value.color) ? info.value.color.toUpperCase() : ''))
  const enabled = computed(() => !!info.value?.enabled && !!color.value)
  const stockColor = computed(() => info.value?.default ?? '')

  /** The URL of the icon `name` in color `c` (the stock file for the stock color). */
  function iconUrl(name: AppIconName, c = color.value): string {
    return info.value ? iconUrlOf(info.value, name, c) : ''
  }

  /** Pick color `c` (RRGGBB) by hand: remembered for this browser (also the stock blue), and the links follow at once. */
  function choose(c: string): void {
    const data = info.value
    if (!data || !HEX.test(c)) return
    c = c.toUpperCase()
    chosen.value = c
    const secure = location.protocol === 'https:' ? '; secure' : ''
    document.cookie = `${data.cookie}=${c}; path=${data.cookie_path}; max-age=31536000; samesite=lax${secure}`
    applyLinks(c)
  }

  return { enabled, color, stockColor, iconUrl, choose }
}
