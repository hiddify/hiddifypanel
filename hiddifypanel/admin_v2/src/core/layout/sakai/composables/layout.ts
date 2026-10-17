import { computed, reactive } from 'vue'

const STORAGE_KEY = 'admin_v2_dark'

const layoutConfig = reactive({
  menuMode: 'static' as 'static' | 'overlay',
  darkTheme: false,
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

if (typeof localStorage !== 'undefined' && localStorage.getItem(STORAGE_KEY) === '1') {
  layoutConfig.darkTheme = true
  applyDarkClass(true)
}

export function useLayout() {
  const toggleDarkMode = () => {
    layoutConfig.darkTheme = !layoutConfig.darkTheme
    applyDarkClass(layoutConfig.darkTheme)
    localStorage.setItem(STORAGE_KEY, layoutConfig.darkTheme ? '1' : '0')
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

  const isDarkTheme = computed(() => layoutConfig.darkTheme)
  const hasOpenOverlay = computed(() => layoutState.overlayMenuActive)

  return {
    layoutConfig,
    layoutState,
    isDarkTheme,
    toggleDarkMode,
    toggleMenu,
    hideMobileMenu,
    isDesktop,
    hasOpenOverlay,
  }
}
