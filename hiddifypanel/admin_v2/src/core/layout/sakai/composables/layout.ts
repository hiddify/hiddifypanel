import { computed, reactive } from 'vue'

const STORAGE_KEY = 'admin_v2_dark'
const THEME_KEY = 'admin_v2_theme'
const ACCENT_KEY = 'admin_v2_caddy_accent'
const GLASS_KEY = 'admin_v2_glass'

/** ``hiddify``: the panel's own look (the default). ``caddy``: the Smart Caddy glass look, light or dark.
 *  ``liquid``: Liquid Glass, an iOS-like design (_theme-liquid.scss), light or dark, with a glass strength. */
export type ThemeName = 'hiddify' | 'caddy' | 'liquid'
export const THEMES: readonly ThemeName[] = ['hiddify', 'caddy', 'liquid']
/** Liquid Glass's strength (0 nearly solid … 100 the most glass) when none was chosen */
export const DEFAULT_GLASS = 60
/** Smart Caddy's colors (the swatches of the topbar's palette). */
export const CADDY_ACCENTS = ['red', 'pink', 'orange', 'yellow', 'green', 'blue', 'purple', 'graphite', 'spacegray', 'brown'] as const
export type CaddyAccent = (typeof CADDY_ACCENTS)[number]

const layoutConfig = reactive({
  menuMode: 'static' as 'static' | 'overlay',
  darkTheme: false,
  theme: 'hiddify' as ThemeName,
  accent: 'red' as CaddyAccent,
  /** Liquid Glass: how much glass, 0…100 (its surfaces' see-through, blur, edges and depth follow it) */
  glass: DEFAULT_GLASS,
})

const layoutState = reactive({
  staticMenuInactive: false,
  overlayMenuActive: false,
  mobileMenuActive: false,
  menuHoverActive: false,
  activePath: null as string | null,
})

// Match `_responsive.scss` (min-width: 992px); avoid innerWidth which can drift after mobile zoom-out.
const desktopMq = typeof window !== 'undefined' ? window.matchMedia('(min-width: 992px)') : null

function isDesktop() {
  return desktopMq?.matches ?? false
}

function applyDarkClass(enabled: boolean) {
  document.documentElement.classList.toggle('app-dark', enabled)
  document.documentElement.classList.toggle('p-dark', enabled)
}

function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* private window: the choice lasts until the page closes */
  }
}

function applyGlass() {
  // one variable for the whole theme: every Liquid Glass surface derives its look from it (_theme-liquid.scss)
  document.documentElement.style.setProperty('--lg-strength', String(layoutConfig.glass / 100))
}

function applyTheme() {
  const root = document.documentElement
  const theme = layoutConfig.theme
  root.classList.toggle('theme-caddy', theme === 'caddy')
  root.classList.toggle('theme-liquid', theme === 'liquid')
  // the two glass themes: their cards are see-through, so some floating parts take a solid surface (theme-glass)
  root.classList.toggle('theme-glass', theme !== 'hiddify')
  // both take one of the colors (the palettes in _theme-caddy.scss)
  if (theme !== 'hiddify') root.setAttribute('data-caddy-accent', layoutConfig.accent)
  else root.removeAttribute('data-caddy-accent')
  applyDarkClass(layoutConfig.darkTheme)
  applyGlass()
}

/** A change of theme, mode or color cross-fades (where the browser can, and motion is welcome) instead of jumping */
function smoothly(change: () => void) {
  const doc = document as Document & { startViewTransition?: (cb: () => void) => unknown }
  const calm = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (doc.startViewTransition && !calm) doc.startViewTransition(change)
  else change()
}

layoutConfig.darkTheme = readStorage(STORAGE_KEY) === '1'
const savedTheme = readStorage(THEME_KEY) as ThemeName | null
layoutConfig.theme = savedTheme && THEMES.includes(savedTheme) ? savedTheme : 'hiddify'
const savedAccent = readStorage(ACCENT_KEY) as CaddyAccent | null
if (savedAccent && CADDY_ACCENTS.includes(savedAccent)) layoutConfig.accent = savedAccent
const savedGlass = Number(readStorage(GLASS_KEY))
if (readStorage(GLASS_KEY) !== null && Number.isFinite(savedGlass)) layoutConfig.glass = Math.min(100, Math.max(0, savedGlass))
applyTheme()

export function useLayout() {
  const toggleDarkMode = () => {
    layoutConfig.darkTheme = !layoutConfig.darkTheme
    smoothly(applyTheme)
    writeStorage(STORAGE_KEY, layoutConfig.darkTheme ? '1' : '0')
  }

  /** Smart Caddy in ``accent``, or (null) the panel's own look. */
  const setCaddyAccent = (accent: CaddyAccent | null) => {
    layoutConfig.theme = accent ? 'caddy' : 'hiddify'
    if (accent) layoutConfig.accent = accent
    smoothly(applyTheme)
    writeStorage(THEME_KEY, layoutConfig.theme)
    if (accent) writeStorage(ACCENT_KEY, accent)
  }

  /** The theme (its color stays: Smart Caddy and Liquid Glass share the colors) */
  const setTheme = (theme: ThemeName) => {
    if (theme === layoutConfig.theme) return
    layoutConfig.theme = theme
    smoothly(applyTheme)
    writeStorage(THEME_KEY, theme)
  }

  /** The color of the glass themes; Liquid Glass's background waves follow it (registered colors in _theme-liquid.scss) */
  const setAccent = (accent: CaddyAccent) => {
    layoutConfig.accent = accent
    applyTheme()
    writeStorage(ACCENT_KEY, accent)
  }

  /** Liquid Glass's strength, live while the slider moves */
  const setGlass = (value: number) => {
    layoutConfig.glass = Math.min(100, Math.max(0, Math.round(value)))
    applyGlass()
    writeStorage(GLASS_KEY, String(layoutConfig.glass))
  }

  const toggleMenu = () => {
    if (isDesktop()) {
      if (layoutConfig.menuMode === 'static') {
        layoutState.staticMenuInactive = !layoutState.staticMenuInactive
      } else {
        layoutState.overlayMenuActive = !layoutState.overlayMenuActive
      }
    } else {
      layoutState.mobileMenuActive = !layoutState.mobileMenuActive
    }
  }

  const hideMobileMenu = () => {
    layoutState.mobileMenuActive = false
  }

  const isCaddyTheme = computed(() => layoutConfig.theme === 'caddy')
  const themeName = computed(() => layoutConfig.theme)
  const glass = computed(() => layoutConfig.glass)
  const caddyAccent = computed(() => (layoutConfig.theme === 'caddy' ? layoutConfig.accent : null))
  const isDarkTheme = computed(() => layoutConfig.darkTheme)
  const hasOpenOverlay = computed(() => layoutState.overlayMenuActive)

  return {
    layoutConfig,
    layoutState,
    isDarkTheme,
    toggleDarkMode,
    isCaddyTheme,
    caddyAccent,
    setCaddyAccent,
    themeName,
    setTheme,
    setAccent,
    glass,
    setGlass,
    toggleMenu,
    hideMobileMenu,
    isDesktop,
    hasOpenOverlay,
  }
}
