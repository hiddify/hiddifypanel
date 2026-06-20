import { createRouter, createWebHistory, type Router } from 'vue-router'
import AppLayout from '@/core/layout/sakai/AppLayout.vue'

const routes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/features/dashboard/views/DashboardView.vue'),
      },
      {
        path: 'custom-proxies',
        name: 'custom-proxy-list',
        component: () => import('@/features/custom-proxy/views/CustomProxyListView.vue'),
      },
      {
        path: 'custom-proxies/new',
        name: 'custom-proxy-new',
        component: () => import('@/features/custom-proxy/views/CustomProxyEditorView.vue'),
      },
      {
        path: 'custom-proxies/:id',
        name: 'custom-proxy-edit',
        component: () => import('@/features/custom-proxy/views/CustomProxyEditorView.vue'),
        props: true,
      },
      {
        path: 'templates',
        name: 'template-list',
        component: () => import('@/features/templates/views/TemplateListView.vue'),
      },
      {
        path: 'templates/new',
        name: 'template-new',
        component: () => import('@/features/templates/views/TemplateEditorView.vue'),
      },
      {
        path: 'templates/:id',
        name: 'template-edit',
        component: () => import('@/features/templates/views/TemplateEditorView.vue'),
        props: true,
      },
      {
        path: 'template-variables',
        name: 'template-variables',
        component: () => import('@/features/template-variables/views/TemplateVariablesView.vue'),
      },
      {
        path: 'base-configs',
        name: 'base-config-list',
        component: () => import('@/features/base-config/views/BaseConfigListView.vue'),
      },
      {
        path: 'base-configs/new',
        name: 'base-config-new',
        component: () => import('@/features/base-config/views/BaseConfigEditorView.vue'),
      },
      {
        path: 'base-configs/:id',
        name: 'base-config-edit',
        component: () => import('@/features/base-config/views/BaseConfigEditorView.vue'),
        props: true,
      },
    ],
  },
]

export function createAppRouter(base: string): Router {
  return createRouter({
    history: createWebHistory(base),
    routes,
  })
}

export default createAppRouter(import.meta.env.BASE_URL)
