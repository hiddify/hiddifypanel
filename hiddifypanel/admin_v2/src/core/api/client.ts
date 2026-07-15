import axios, { type AxiosInstance } from 'axios'
import { applyBootstrapResponse, legacyMenu } from '@/core/panelShell'

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

function resolveProxyPathForBootstrap(): string | null {
  return (
    devProxyPath() ||
    normalizeProxyPath(window.__PROXY_PATH__) ||
    normalizeProxyPath(sessionStorage.getItem(STORAGE_KEY))
  )
}

function bootstrapPath(): string {
  const proxyPath = resolveProxyPathForBootstrap()
  return proxyPath ? `/${proxyPath}/__admin_v2_bootstrap` : BOOTSTRAP_PATH
}

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

function proxyPathFromBaseUrl(): string | null {
  const match = import.meta.env.BASE_URL.match(/^\/([^/]+)\/admin\/v2\/?$/)
  return match ? match[1] : null
}

function devProxyPath(): string | null {
  return (
    normalizeProxyPath(window.__PROXY_PATH__) ||
    proxyPathFromQuery() ||
    normalizeProxyPath(sessionStorage.getItem(STORAGE_KEY)) ||
    proxyPathFromBaseUrl() ||
    normalizeProxyPath(import.meta.env.VITE_PROXY_PATH)
  )
}

function bootstrapFromProxyPath(proxyPath: string) {
  return {
    apiBase: apiBaseFromProxyPath(proxyPath),
    routerBase: routerBaseFromProxyPath(proxyPath),
  }
}

async function tryFetchBootstrapExtras(): Promise<boolean> {
  try {
    const res = await fetch(bootstrapPath(), { credentials: 'include' })
    if (!res.ok) return false
    const boot = await res.json()
    applyBootstrapResponse(boot)
    return true
  } catch {
    return false
  }
}

function applyBootstrapPayload(boot: Awaited<ReturnType<typeof fetchBootstrap>>) {
  applyBootstrapResponse(boot)
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
  const res = await fetch(bootstrapPath(), { credentials: 'include' })
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
  let result: { apiBase: string; routerBase: string }

  if (import.meta.env.VITE_API_BASE) {
    const pp =
      devProxyPath() ||
      normalizeProxyPath(window.__PROXY_PATH__ || sessionStorage.getItem(STORAGE_KEY))
    result = {
      apiBase: import.meta.env.VITE_API_BASE,
      routerBase: pp ? routerBaseFromProxyPath(pp) : import.meta.env.BASE_URL,
    }
  } else if (!import.meta.env.DEV) {
    result = {
      apiBase: window.__API_BASE__ ?? '../api/v2/admin/',
      routerBase: window.__ROUTER_BASE__ ?? import.meta.env.BASE_URL,
    }
  } else {
    const proxyPath = devProxyPath()
    if (proxyPath) {
      rememberProxyPath(proxyPath, routerBaseFromProxyPath(proxyPath))
      result = bootstrapFromProxyPath(proxyPath)
    } else {
      const boot = await fetchBootstrap()
      rememberProxyPath(boot.proxy_path, boot.router_base || routerBaseFromProxyPath(boot.proxy_path))
      applyBootstrapPayload(boot)
      return {
        apiBase: boot.api_base || apiBaseFromProxyPath(boot.proxy_path),
        routerBase: boot.router_base || routerBaseFromProxyPath(boot.proxy_path),
      }
    }
  }

  if (import.meta.env.DEV && !legacyMenuHasItems()) {
    await tryFetchBootstrapExtras()
  }

  return result
}

function legacyMenuHasItems(): boolean {
  return legacyMenu.value.length > 0
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
