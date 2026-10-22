<template>
  <div class="layout-wrapper" :class="containerClass">
    <AppTopbar />
    <AppSidebar />
    <div class="layout-main-container">
      <div class="layout-main">
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
  <DonationDialog />
  <LegacyActionDialog />
  <!-- Offers to install the panel as an app, once per visit, until "do not show again" -->
  <PwaInstallDialog v-model:visible="pwaVisible" />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ConfirmDialog from 'primevue/confirmdialog'
import DonationDialog from '@/shared/components/DonationDialog.vue'
import LegacyActionDialog from '@/shared/components/LegacyActionDialog.vue'
import PwaInstallDialog from '@/shared/components/PwaInstallDialog.vue'
import Toast from 'primevue/toast'
import AppFooter from './AppFooter.vue'
import AppSidebar from './AppSidebar.vue'
const pwaVisible = ref(false)
import AppTopbar from './AppTopbar.vue'
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
