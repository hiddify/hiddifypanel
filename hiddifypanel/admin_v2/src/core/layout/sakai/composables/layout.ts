import { computed, reactive } from 'vue'

const STORAGE_KEY = 'admin_v2_dark'
const THEME_KEY = 'admin_v2_theme'
const ACCENT_KEY = 'admin_v2_caddy_accent'

/** ``hiddify``: the panel's own look (the default). ``caddy``: the Smart Caddy glass look, light or dark. */
export type ThemeName = 'hiddify' | 'caddy'
/** Smart Caddy's colors (the swatches of the topbar's palette). */
export const CADDY_ACCENTS = ['red', 'pink', 'orange', 'yellow', 'green', 'blue', 'purple'] as const
export type CaddyAccent = (typeof CADDY_ACCENTS)[number]

const layoutConfig = reactive({
  menuMode: 'static' as 'static' | 'overlay',
  darkTheme: false,
  theme: 'hiddify' as ThemeName,
  accent: 'red' as CaddyAccent,
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

function applyTheme() {
  const caddy = layoutConfig.theme === 'caddy'
  document.documentElement.classList.toggle('theme-caddy', caddy)
  if (caddy) document.documentElement.setAttribute('data-caddy-accent', layoutConfig.accent)
  else document.documentElement.removeAttribute('data-caddy-accent')
  applyDarkClass(layoutConfig.darkTheme)
}

layoutConfig.darkTheme = readStorage(STORAGE_KEY) === '1'
layoutConfig.theme = readStorage(THEME_KEY) === 'caddy' ? 'caddy' : 'hiddify'
const savedAccent = readStorage(ACCENT_KEY) as CaddyAccent | null
if (savedAccent && CADDY_ACCENTS.includes(savedAccent)) layoutConfig.accent = savedAccent
applyTheme()

export function useLayout() {
  const toggleDarkMode = () => {
    layoutConfig.darkTheme = !layoutConfig.darkTheme
    applyTheme()
    writeStorage(STORAGE_KEY, layoutConfig.darkTheme ? '1' : '0')
  }

  /** Smart Caddy in ``accent``, or (null) the panel's own look. */
  const setCaddyAccent = (accent: CaddyAccent | null) => {
    layoutConfig.theme = accent ? 'caddy' : 'hiddify'
    if (accent) layoutConfig.accent = accent
    applyTheme()
    writeStorage(THEME_KEY, layoutConfig.theme)
    if (accent) writeStorage(ACCENT_KEY, accent)
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
    toggleMenu,
    hideMobileMenu,
    isDesktop,
    hasOpenOverlay,
  }
}
