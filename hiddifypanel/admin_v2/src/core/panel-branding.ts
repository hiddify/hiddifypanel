declare global {
  interface Window {
    __PANEL_VERSION__?: string
    __PANEL_LOGO_URL__?: string
  }
}

export function getPanelVersion(): string {
  return window.__PANEL_VERSION__ ?? ''
}

export function getPanelLogoUrl(): string {
  return window.__PANEL_LOGO_URL__ ?? ''
}
