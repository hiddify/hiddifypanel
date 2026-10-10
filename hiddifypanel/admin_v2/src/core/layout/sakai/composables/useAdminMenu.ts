import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isAgent, isChildPanel, isSuperAdmin, legacyMenu, type AdminMenuGroup, type AdminMenuItem } from '@/core/panelShell'

export type { AdminMenuGroup, AdminMenuItem }

function framedPath(item: AdminMenuItem): string | null {
  if (!item.url || item.to || item.method === 'post' || (item.target && item.target !== '_self')) return null
  let url: URL
  try {
    url = new URL(item.url, window.location.origin)
  } catch {
    return null
  }
  if (url.origin !== window.location.origin || /\/admin\/v2(\/|$)/.test(url.pathname)) return null
  return `/legacy${url.pathname}${url.search}`
}

function framed(item: AdminMenuItem): AdminMenuItem {
  const to = framedPath(item)
  const items = item.items?.map(framed)
  if (!to) return items ? { ...item, items } : item
  const { url: _url, target: _target, ...rest } = item
  return { ...rest, to, ...(items ? { items } : {}) }
}

/** The only groups, in order. The server sends them (v2_menu.py); new-UI routes are added here. */
const GROUP_ORDER = ['manager', 'settings', 'help'] as const
type GroupId = (typeof GROUP_ORDER)[number]

export function useAdminMenu() {
  const { t } = useI18n()

  const proxyEditor = computed<AdminMenuItem>(() => ({
    label: t('menu.proxyEditor'),
    icon: 'pi pi-fw pi-server',
    items: [
      { label: t('menu.customProxies'), icon: 'pi pi-fw pi-share-alt', to: '/custom-proxies' },
      { label: t('menu.baseConfigs'), icon: 'pi pi-fw pi-cog', to: '/base-configs' },
      { label: t('menu.templates'), icon: 'pi pi-fw pi-file-edit', to: '/templates' },
      { label: t('menu.templateVariables'), icon: 'pi pi-fw pi-list', to: '/template-variables' },
    ],
  }))

  // Their own entries in Settings (not inside the proxy editor).
  const protocols = computed<AdminMenuItem>(() => ({ label: t('menu.protocols'), icon: 'pi pi-fw pi-sliders-h', to: '/protocols' }))
  const outbounds = computed<AdminMenuItem>(() => ({ label: t('menu.outbounds'), icon: 'pi pi-fw pi-directions', to: '/outbounds' }))

  const menuGroups = computed<AdminMenuGroup[]>(() => {
    // Same-origin classic pages open inside the new shell (legacy frame); external links stay as they are.
    const server = new Map(legacyMenu.value.map((group) => [group.id ?? '', group.items.map(framed)]))
    const serverItems = (id: GroupId) => server.get(id) ?? []

    const items: Record<GroupId, AdminMenuItem[]> = {
      // A node: its parent panel first, then this node's home, then the rest.
      // Otherwise: the dashboard first; tools at the end.
      manager: isChildPanel.value
        ? [...serverItems('manager'), { label: t('menu.nodeHome'), icon: 'pi pi-fw pi-server', to: '/node' }]
        : [
            { label: t('menu.dashboard'), icon: 'pi pi-fw pi-home', to: '/' },
            ...serverItems('manager'),
            { label: t('menu.utils'), icon: 'pi pi-fw pi-wrench', to: '/utils' },
            ...(isSuperAdmin.value ? [{ label: t('menu.configTester'), icon: 'pi pi-fw pi-bolt', to: '/config-tester' }] : []),
          ],
      // Domains, protocols, outbounds, settings, the proxy editor, then the rest (backup, apply, ...).
      // The proxy editor lives in Settings in every panel mode; agents don't get it.
      settings: (() => {
        const all = serverItems('settings')
        const first = (to: string) => all.find((item) => item.to === to)
        const lead = [first('/domains'), ...(isAgent.value ? [] : [protocols.value]), ...(isAgent.value || !isSuperAdmin.value ? [] : [outbounds.value]), first('/settings'), ...(isAgent.value ? [] : [proxyEditor.value])]
        const placed = new Set(lead)
        return [...lead.filter((item): item is AdminMenuItem => !!item), ...all.filter((item) => !placed.has(item))]
      })(),
      help: serverItems('help'),
    }
    return GROUP_ORDER.map((id) => ({ id, label: t(`menu.group.${id}`), items: items[id] })).filter((group) => group.items.length > 0)
  })

  return { menuGroups }
}
