import axios, { type AxiosInstance } from 'axios'

declare global {
  interface Window {
    __API_BASE__?: string
    __ROUTER_BASE__?: string
    __LOCALE__?: string
    __PROXY_PATH__?: string
    __PANEL_VERSION__?: string
    __PANEL_LOGO_URL__?: string
  }
}

const BOOTSTRAP_PATH = '/__admin_v2_bootstrap'
const STORAGE_KEY = 'hiddify_admin_proxy_path'

function normalizeProxyPath(value: string | null | undefined): string | null {
  if (!value) return null
  const trimmed = value.replace(/^\/+|\/+$/g, '')
  return trimmed || null
}

function apiBaseFromProxyPath(proxyPath: string): string {
  return `/${proxyPath}/api/v2/admin/`
}

function routerBaseFromProxyPath(proxyPath: string): string {
  return `/${proxyPath}/admin/v2/`
}

function proxyPathFromQuery(): string | null {
  const params = new URLSearchParams(window.location.search)
  return normalizeProxyPath(params.get('proxy_path') || params.get('pp'))
}

async function fetchBootstrap(): Promise<{
  proxy_path: string
  api_base: string
  router_base: string
  locale?: string
  panel_version?: string
  panel_logo_url?: string
  menu?: unknown[]
  notices?: unknown[]
}> {
  const res = await fetch(BOOTSTRAP_PATH, { credentials: 'include' })
  if (!res.ok) {
    throw new Error(
      'Could not resolve proxy_path. Start the Flask panel and open Admin V2 from the panel, or use ?proxy_path=YOUR_PATH in the URL.',
    )
  }
  return res.json()
}

function rememberProxyPath(proxyPath: string, routerBase?: string) {
  sessionStorage.setItem(STORAGE_KEY, proxyPath)
  window.__PROXY_PATH__ = proxyPath
  if (routerBase) {
    window.__ROUTER_BASE__ = routerBase
  }
}

async function resolveBootstrap(): Promise<{ apiBase: string; routerBase: string }> {
  if (import.meta.env.VITE_API_BASE) {
    const pp = normalizeProxyPath(window.__PROXY_PATH__ || sessionStorage.getItem(STORAGE_KEY))
    return {
      apiBase: import.meta.env.VITE_API_BASE,
      routerBase: pp ? routerBaseFromProxyPath(pp) : import.meta.env.BASE_URL,
    }
  }

  if (!import.meta.env.DEV) {
    return {
      apiBase: window.__API_BASE__ ?? '../api/v2/admin/',
      routerBase: window.__ROUTER_BASE__ ?? import.meta.env.BASE_URL,
    }
  }

  const fromWindow = normalizeProxyPath(window.__PROXY_PATH__)
  if (fromWindow) {
    rememberProxyPath(fromWindow, routerBaseFromProxyPath(fromWindow))
    return {
      apiBase: apiBaseFromProxyPath(fromWindow),
      routerBase: routerBaseFromProxyPath(fromWindow),
    }
  }

  const fromQuery = proxyPathFromQuery()
  if (fromQuery) {
    rememberProxyPath(fromQuery, routerBaseFromProxyPath(fromQuery))
    return {
      apiBase: apiBaseFromProxyPath(fromQuery),
      routerBase: routerBaseFromProxyPath(fromQuery),
    }
  }

  const cached = normalizeProxyPath(sessionStorage.getItem(STORAGE_KEY))
  if (cached) {
    rememberProxyPath(cached, routerBaseFromProxyPath(cached))
    return {
      apiBase: apiBaseFromProxyPath(cached),
      routerBase: routerBaseFromProxyPath(cached),
    }
  }

  const boot = await fetchBootstrap()
  rememberProxyPath(boot.proxy_path, boot.router_base || routerBaseFromProxyPath(boot.proxy_path))
  if (boot.menu) {
    window.__ADMIN_MENU__ = boot.menu as Window['__ADMIN_MENU__']
  }
  if (boot.notices) {
    window.__ADMIN_NOTICES__ = boot.notices as Window['__ADMIN_NOTICES__']
  }
  if (boot.panel_version) {
    window.__PANEL_VERSION__ = boot.panel_version
  }
  if (boot.panel_logo_url) {
    window.__PANEL_LOGO_URL__ = boot.panel_logo_url
  }
  return {
    apiBase: boot.api_base || apiBaseFromProxyPath(boot.proxy_path),
    routerBase: boot.router_base || routerBaseFromProxyPath(boot.proxy_path),
  }
}

let httpClient: AxiosInstance | null = null
let apiBaseValue = ''
let routerBaseValue = ''

export async function initApiClient(): Promise<void> {
  const { apiBase, routerBase } = await resolveBootstrap()
  apiBaseValue = apiBase
  routerBaseValue = routerBase
  window.__ROUTER_BASE__ = routerBase
  httpClient = axios.create({
    baseURL: apiBaseValue,
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
  })
  httpClient.interceptors.response.use(
    (response) => response,
    (error) => {
      const status = error?.response?.status
      if (status === 401 || status === 403) {
        console.error('Admin V2 API auth failed — log in via the panel first, then reload this page.')
      }
      return Promise.reject(error)
    },
  )
}

export function getHttp(): AxiosInstance {
  if (!httpClient) {
    throw new Error('API client not initialized. Call initApiClient() first.')
  }
  return httpClient
}

export function getApiBase(): string {
  return apiBaseValue
}

export function getRouterBase(): string {
  return routerBaseValue || window.__ROUTER_BASE__ || import.meta.env.BASE_URL
}
