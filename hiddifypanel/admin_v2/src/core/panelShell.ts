import { ref } from 'vue'

export interface AdminMenuItem {
  label: string
  icon?: string
  to?: string
  url?: string
  target?: string
  badge?: string
  items?: AdminMenuItem[]
}

export interface AdminMenuGroup {
  label: string
  items: AdminMenuItem[]
}

export interface PanelNotice {
  severity: 'success' | 'info' | 'warn' | 'error'
  summary: string
  detail?: string
  toast?: boolean
  id?: string
}

export const legacyMenu = ref<AdminMenuGroup[]>(window.__ADMIN_MENU__ ?? [])
export const panelNotices = ref<PanelNotice[]>(window.__ADMIN_NOTICES__ ?? [])

export function applyBootstrapShell(data: {
  menu?: AdminMenuGroup[]
  notices?: PanelNotice[]
  locale?: string
  panel_version?: string
  panel_logo_url?: string
}) {
  if (data.menu?.length) {
    legacyMenu.value = data.menu
    window.__ADMIN_MENU__ = data.menu
  }
  if (data.notices) {
    panelNotices.value = data.notices
    window.__ADMIN_NOTICES__ = data.notices
  }
  if (data.locale) {
    window.__LOCALE__ = data.locale
  }
  if (data.panel_version) {
    window.__PANEL_VERSION__ = data.panel_version
  }
  if (data.panel_logo_url) {
    window.__PANEL_LOGO_URL__ = data.panel_logo_url
  }
}

export function applyBootstrapResponse(data: Record<string, unknown>) {
  applyBootstrapShell({
    menu: data.menu as AdminMenuGroup[] | undefined,
    notices: data.notices as PanelNotice[] | undefined,
    locale: data.locale as string | undefined,
    panel_version: data.panel_version as string | undefined,
    panel_logo_url: data.panel_logo_url as string | undefined,
  })
}
