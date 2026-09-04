import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { legacyMenu, type AdminMenuGroup, type AdminMenuItem } from '@/core/panelShell'

export type { AdminMenuGroup, AdminMenuItem }

export function useAdminMenu() {
  const { t } = useI18n()

  const v2Groups = computed<AdminMenuGroup[]>(() => [
    {
      label: t('menu.sectionNew'),
      items: [
        { label: t('menu.dashboard'), icon: 'pi pi-fw pi-home', to: '/' },
        { label: t('menu.utils'), icon: 'pi pi-fw pi-wrench', to: '/utils' },
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

  const legacyGroups = legacyMenu

  const menuGroups = computed(() => [...v2Groups.value, ...legacyGroups.value])

  return { menuGroups, v2Groups, legacyGroups }
}
