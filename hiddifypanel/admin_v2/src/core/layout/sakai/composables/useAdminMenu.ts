import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isChildPanel, legacyMenu, type AdminMenuGroup, type AdminMenuItem } from '@/core/panelShell'

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

export function useAdminMenu() {
  const { t } = useI18n()

  const v2Groups = computed<AdminMenuGroup[]>(() => [
    {
      label: t('menu.sectionNew'),
      items: [
        // Nodes have no dashboard of their own (it is on the parent) and only keep the proxy editor.
        ...(isChildPanel.value
          ? [{ label: t('menu.nodeHome'), icon: 'pi pi-fw pi-home', to: '/node' }]
          : [
              { label: t('menu.dashboard'), icon: 'pi pi-fw pi-home', to: '/' },
              { label: t('menu.utils'), icon: 'pi pi-fw pi-wrench', to: '/utils' },
            ]),
        {
          label: t('menu.proxyEditor'),
          icon: 'pi pi-fw pi-server',
          items: [
            { label: t('menu.protocols'), icon: 'pi pi-fw pi-sliders-h', to: '/protocols' },
            { label: t('menu.customProxies'), icon: 'pi pi-fw pi-share-alt', to: '/custom-proxies' },
            { label: t('menu.baseConfigs'), icon: 'pi pi-fw pi-cog', to: '/base-configs' },
            { label: t('menu.templates'), icon: 'pi pi-fw pi-file-edit', to: '/templates' },
            { label: t('menu.templateVariables'), icon: 'pi pi-fw pi-list', to: '/template-variables' },
          ],
        },
      ],
    },
  ])

  // Same-origin classic pages open inside the new shell (legacy frame); external links stay as they are.
  const legacyGroups = computed<AdminMenuGroup[]>(() => legacyMenu.value.map((group) => ({ ...group, items: group.items.map(framed) })))

  const menuGroups = computed(() => [...v2Groups.value, ...legacyGroups.value])

  return { menuGroups, v2Groups, legacyGroups }
}
