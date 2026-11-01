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
    <!-- Phones and tablets: a small tab at the middle of the screen's edge opens the menu, rides with it as it slides in,
         and closes it again -->
    <button
      type="button"
      class="menu-tab"
      :class="{ 'menu-tab--open': layoutState.mobileMenuActive }"
      :aria-label="layoutState.mobileMenuActive ? t('menu.close') : t('menu.open')"
      :aria-expanded="layoutState.mobileMenuActive"
      @click="toggleMenu"
    >
      <i class="pi pi-chevron-right" />
    </button>
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
import { useI18n } from 'vue-i18n'
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

const { layoutConfig, layoutState, hideMobileMenu, toggleMenu } = useLayout()
const { t } = useI18n()

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

<style scoped>
/* The mobile menu's tab: only below the desktop layout (the sidebar slides in there); on the screen's start edge, at
   half height, and at the sidebar's edge while it is open, sliding with it */
.menu-tab {
  display: none;
}
@media (max-width: 991px) {
  .menu-tab {
    position: fixed;
    top: 50%;
    inset-inline-start: 0;
    z-index: 1000;
    display: grid;
    place-items: center;
    width: 1.4rem;
    height: 3.6rem;
    margin-top: -1.8rem;
    padding: 0;
    border: 1px solid var(--p-content-border-color);
    border-inline-start: 0;
    border-start-end-radius: 12px;
    border-end-end-radius: 12px;
    color: var(--p-primary-color);
    background: var(--p-content-background);
    box-shadow: 2px 0 10px -4px rgb(15 23 42 / 30%);
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition:
      inset-inline-start 0.4s cubic-bezier(0.05, 0.74, 0.2, 0.99),
      background-color 0.2s ease,
      width 0.2s ease;
  }
  html.theme-caddy .menu-tab {
    background: var(--p-surface-0);
  }
  html.theme-caddy.app-dark .menu-tab {
    background: var(--p-surface-900);
  }
  .menu-tab:active {
    width: 1.6rem;
  }
  .menu-tab i {
    font-size: 0.75rem;
    transition: transform 0.4s cubic-bezier(0.05, 0.74, 0.2, 0.99);
  }
  /* The arrow points the way the menu will go: inwards (towards the page) when closed, back when open */
  html[dir='rtl'] .menu-tab i {
    transform: scaleX(-1);
  }
  .menu-tab--open {
    inset-inline-start: min(20rem, 100vw - 1.4rem);
  }
  .menu-tab--open i {
    transform: rotate(180deg);
  }
  html[dir='rtl'] .menu-tab--open i {
    transform: scaleX(-1) rotate(180deg);
  }
}
</style>
