<template>
  <div class="layout-wrapper" :class="containerClass">
    <AppTopbar />
    <AppSidebar />
    <div class="layout-main-container">
      <div class="layout-main">
        <PanelNotices />
        <RouterView v-slot="{ Component, route }">
          <KeepAlive :include="keptViews">
            <component :is="Component" :key="route.name as string" />
          </KeepAlive>
        </RouterView>
      </div>
      <AppFooter />
    </div>
    <div class="layout-mask animate-fadein" @click="hideMobileMenu" />
  </div>
  <Toast />
  <ConfirmDialog />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import AppFooter from './AppFooter.vue'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
import PanelNotices from './PanelNotices.vue'
import { useLayout } from './composables/layout'

const { layoutConfig, layoutState, hideMobileMenu } = useLayout()

/** Keep list filters/search when navigating to editor and back. */
const keptViews = ['CustomProxyListView']

const containerClass = computed(() => ({
  'layout-overlay': layoutConfig.menuMode === 'overlay',
  'layout-static': layoutConfig.menuMode === 'static',
  'layout-overlay-active': layoutState.overlayMenuActive,
  'layout-mobile-active': layoutState.mobileMenuActive,
  'layout-static-inactive': layoutState.staticMenuInactive,
}))
</script>
