/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_API_TARGET?: string
  readonly VITE_DEV_PORT?: string
  readonly VITE_PROXY_PATH?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare global {
  interface Window {
    __API_BASE__?: string
    __ROUTER_BASE__?: string
    __LOCALE__?: string
    __PROXY_PATH__?: string
    __ADMIN_MENU__?: Array<{
      label: string
      items: Array<Record<string, unknown>>
    }>
    __ADMIN_NOTICES__?: Array<{
      severity: string
      summary: string
      detail?: string
      toast?: boolean
    }>
  }
}

export {}
