import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

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

declare global {
  interface Window {
    __ADMIN_MENU__?: AdminMenuGroup[]
  }
}

export function useAdminMenu() {
  const { t } = useI18n()

  const v2Groups = computed<AdminMenuGroup[]>(() => [
    {
      label: t('menu.sectionV2'),
      items: [
        { label: t('menu.dashboard'), icon: 'pi pi-fw pi-home', to: '/' },
        {
          label: t('menu.proxyEditor'),
          icon: 'pi pi-fw pi-server',
          items: [
            { label: t('menu.customProxies'), icon: 'pi pi-fw pi-share-alt', to: '/custom-proxies' },
            { label: t('menu.baseConfigs'), icon: 'pi pi-fw pi-cog', to: '/base-configs' },
            { label: t('menu.templates'), icon: 'pi pi-fw pi-file-edit', to: '/templates' },
            { label: t('menu.templateVariables'), icon: 'pi pi-fw pi-list', to: '/template-variables' },
          ],
        },
      ],
    },
  ])

  const legacyGroups = computed(() => window.__ADMIN_MENU__ ?? [])

  const menuGroups = computed(() => [...v2Groups.value, ...legacyGroups.value])

  return { menuGroups, v2Groups, legacyGroups }
}
