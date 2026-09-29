import { computed, ref } from 'vue'

export interface AdminMenuItem {
  label: string
  icon?: string
  to?: string
  url?: string
  target?: string
  badge?: string
  /** `post`: the URL only accepts POST (system actions); submitted as a form after `confirm`. */
  method?: 'get' | 'post'
  confirm?: string
  items?: AdminMenuItem[]
}

/** Navigate to `url` with a POST form submit (full page load, like the classic admin's `form_post`). */
export function submitPostForm(url: string, target = '_self'): void {
  const form = document.createElement('form')
  form.method = 'post'
  form.action = url
  form.target = target
  form.style.display = 'none'
  document.body.appendChild(form)
  form.submit()
  form.remove()
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

/** Legacy system action URLs (POST-only except `status`/`viewlogs`), keyed by action; empty for non-super admins. */
export type SystemActionUrls = Partial<Record<'status' | 'viewlogs' | 'apply_configs' | 'update' | 'reinstall' | 'reset', string>>

export const systemActionUrls = ref<SystemActionUrls>(window.__ADMIN_SYSTEM_ACTIONS__ ?? {})
/** `panel_mode` hconfig: `standalone` | `parent` | `child`. */
export const panelMode = ref<string>(window.__PANEL_MODE__ ?? '')
/** A node only manages its domains/proxies/server; dashboard and users live on the parent. */
export const isChildPanel = computed(() => panelMode.value === 'child')

export interface NodeInfo {
  node_name: string
  parent_host: string
  /** The parent's dashboard for the signed-in admin ("" when unknown). */
  parent_dashboard_url: string
}

/** Set only on node (child) panels. */
export const nodeInfo = ref<NodeInfo | null>(window.__NODE_INFO__ ?? null)

/** Signed-in admin's mode: `super_admin` | `admin` | `agent`. */
export const accountMode = ref<string>(window.__ACCOUNT_MODE__ ?? '')
export const isSuperAdmin = computed(() => accountMode.value === 'super_admin')

export const legacyMenu = ref<AdminMenuGroup[]>(window.__ADMIN_MENU__ ?? [])
export const panelNotices = ref<PanelNotice[]>(window.__ADMIN_NOTICES__ ?? [])

export function applyBootstrapShell(data: {
  menu?: AdminMenuGroup[]
  notices?: PanelNotice[]
  system_actions?: SystemActionUrls
  panel_mode?: string
  node_info?: NodeInfo | null
  account_mode?: string
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
  if (data.system_actions) {
    systemActionUrls.value = data.system_actions
    window.__ADMIN_SYSTEM_ACTIONS__ = data.system_actions
  }
  if (data.panel_mode !== undefined) {
    panelMode.value = data.panel_mode
    window.__PANEL_MODE__ = data.panel_mode
  }
  if (data.node_info !== undefined) {
    nodeInfo.value = data.node_info
    window.__NODE_INFO__ = data.node_info
  }
  if (data.account_mode !== undefined) {
    accountMode.value = data.account_mode
    window.__ACCOUNT_MODE__ = data.account_mode
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
    system_actions: data.system_actions as SystemActionUrls | undefined,
    panel_mode: data.panel_mode as string | undefined,
    node_info: data.node_info as NodeInfo | null | undefined,
    account_mode: data.account_mode as string | undefined,
    locale: data.locale as string | undefined,
    panel_version: data.panel_version as string | undefined,
    panel_logo_url: data.panel_logo_url as string | undefined,
  })
}
