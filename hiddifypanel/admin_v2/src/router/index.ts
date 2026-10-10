import { createRouter, createWebHistory, type Router } from 'vue-router'
import AppLayout from '@/core/layout/sakai/AppLayout.vue'
import { isAgent, isChildPanel, isSuperAdmin, needsQuickSetup } from '@/core/panelShell'

export const QUICK_SETUP_SKIPPED_KEY = 'hiddify.quickSetup.skipped'

/** Proxy editor pages: not for agents. */
const notForAgents = () => (isAgent.value ? { name: 'dashboard' } : true)

const routes = [
  {
    // First-run onboarding: full screen, outside the shell (no sidebar).
    path: '/quick-setup',
    name: 'quick-setup',
    component: () => import('@/features/quick-setup/views/QuickSetupView.vue'),
    beforeEnter: () => (isSuperAdmin.value ? true : { path: '/' }),
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/features/dashboard/views/DashboardView.vue'),
        // A node's dashboard lives on the parent panel; it only gets a basic home page.
        beforeEnter: () => (isChildPanel.value ? { name: 'node-home' } : true),
      },
      {
        path: 'node',
        name: 'node-home',
        component: () => import('@/features/node-home/views/NodeHomeView.vue'),
      },
      {
        // Classic admin pages the new UI has not replaced yet, framed inside the new shell.
        path: 'legacy/:path(.*)',
        name: 'legacy',
        component: () => import('@/features/legacy/views/LegacyFrameView.vue'),
      },
      {
        path: 'nodes',
        name: 'nodes',
        component: () => import('@/features/nodes/views/NodesView.vue'),
        // Super admins of a parent/standalone panel only; a node's nodes are managed on its parent.
        beforeEnter: () => (isChildPanel.value ? { name: 'node-home' } : isSuperAdmin.value ? true : { name: 'dashboard' }),
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('@/features/users/views/UsersView.vue'),
        // Users are managed on the parent panel.
        beforeEnter: () => (isChildPanel.value ? { name: 'node-home' } : true),
      },
      {
        path: 'admins',
        name: 'admins',
        component: () => import('@/features/admins/views/AdminsView.vue'),
        // Admins are managed on the parent panel.
        beforeEnter: () => (isChildPanel.value ? { name: 'node-home' } : true),
      },
      {
        path: 'account',
        name: 'my-account',
        component: () => import('@/features/admins/views/MyAccountView.vue'),
        beforeEnter: () => (isChildPanel.value ? { name: 'node-home' } : true),
      },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('@/features/settings/views/SettingsView.vue'),
      },
      {
        path: 'protocols',
        name: 'protocols',
        component: () => import('@/features/protocols/views/ProtocolsView.vue'),
        beforeEnter: notForAgents,
      },
      {
        path: 'domains',
        name: 'domains',
        component: () => import('@/features/domains/views/DomainsView.vue'),
        // Super admins and admins (like the classic Domains page); agents do not manage domains.
        beforeEnter: notForAgents,
      },
      {
        path: 'backup',
        name: 'backup',
        component: () => import('@/features/backup/views/BackupView.vue'),
        // The whole panel's data: super admins only.
        beforeEnter: () => (isSuperAdmin.value ? true : { name: 'dashboard' }),
      },
      {
        path: 'outbounds',
        name: 'outbounds',
        component: () => import('@/features/outbounds/views/OutboundsView.vue'),
        // Server routing: super admins only.
        beforeEnter: () => (isSuperAdmin.value ? true : { name: 'dashboard' }),
      },
      {
        path: 'custom-proxies',
        name: 'custom-proxy-list',
        component: () => import('@/features/custom-proxy/views/CustomProxyListView.vue'),
        meta: { keepAlive: true },
        beforeEnter: notForAgents,
      },
      {
        path: 'custom-proxies/new',
        name: 'custom-proxy-new',
        component: () => import('@/features/custom-proxy/views/CustomProxyEditorView.vue'),
        beforeEnter: notForAgents,
      },
      {
        path: 'custom-proxies/:id',
        name: 'custom-proxy-edit',
        component: () => import('@/features/custom-proxy/views/CustomProxyEditorView.vue'),
        props: true,
        beforeEnter: notForAgents,
      },
      {
        path: 'templates',
        name: 'template-list',
        component: () => import('@/features/templates/views/TemplateListView.vue'),
        beforeEnter: notForAgents,
      },
      {
        path: 'templates/new',
        name: 'template-new',
        component: () => import('@/features/templates/views/TemplateEditorView.vue'),
        beforeEnter: notForAgents,
      },
      {
        path: 'templates/:id',
        name: 'template-edit',
        component: () => import('@/features/templates/views/TemplateEditorView.vue'),
        props: true,
        beforeEnter: notForAgents,
      },
      {
        path: 'template-variables',
        name: 'template-variables',
        component: () => import('@/features/template-variables/views/TemplateVariablesView.vue'),
        beforeEnter: notForAgents,
      },
      {
        path: 'utils',
        name: 'utils',
        component: () => import('@/features/utils/views/UtilsView.vue'),
      },
      {
        path: 'config-tester',
        name: 'config-tester',
        component: () => import('@/features/config-tester/views/ConfigTesterView.vue'),
        // Runs cores on the server: super admins only.
        beforeEnter: () => (isSuperAdmin.value ? true : { name: 'dashboard' }),
      },
      {
        path: 'apply',
        name: 'apply',
        component: () => import('@/features/apply/views/ApplyView.vue'),
        // Server actions: super admins only.
        beforeEnter: () => (isSuperAdmin.value ? true : { name: 'dashboard' }),
      },
      // The old Actions page lives on the Apply page now.
      { path: 'actions', redirect: { name: 'apply' } },
      {
        path: 'base-configs',
        name: 'base-config-list',
        component: () => import('@/features/base-config/views/BaseConfigListView.vue'),
        beforeEnter: notForAgents,
      },
      {
        path: 'base-configs/new',
        name: 'base-config-new',
        component: () => import('@/features/base-config/views/BaseConfigEditorView.vue'),
        beforeEnter: notForAgents,
      },
      {
        path: 'base-configs/:id',
        name: 'base-config-edit',
        component: () => import('@/features/base-config/views/BaseConfigEditorView.vue'),
        props: true,
        beforeEnter: notForAgents,
      },
    ],
  },
]

function quickSetupSkipped(): boolean {
  try {
    return sessionStorage.getItem(QUICK_SETUP_SKIPPED_KEY) === '1'
  } catch {
    return false
  }
}

export function createAppRouter(base: string): Router {
  const router = createRouter({
    history: createWebHistory(base),
    routes,
  })
  // A panel that still needs its first setup opens the quick setup instead of the dashboard.
  router.beforeEach((to) => {
    if (to.name === 'dashboard' && needsQuickSetup.value && isSuperAdmin.value && !quickSetupSkipped()) {
      return { name: 'quick-setup' }
    }
    return true
  })
  return router
}

export default createAppRouter(import.meta.env.BASE_URL)
