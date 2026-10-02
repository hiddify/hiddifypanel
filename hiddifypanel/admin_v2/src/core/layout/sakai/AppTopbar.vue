<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLayout } from './composables/layout'
import { getPanelLogoUrl, getPanelVersion } from '@/core/panel-branding'
import { isChildPanel, submitPostForm } from '@/core/panelShell'
import { getRouterBase } from '@/core/api/client'

const { t } = useI18n()
const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout()

const panelVersion = computed(() => getPanelVersion())

/** Ends the session on the server (POST only), then the sign-in page opens. */
function signOut() {
  // After signing in again: back to this page.
  const here = window.location.pathname + window.location.search + window.location.hash
  submitPostForm(`${getRouterBase().replace(/admin\/v2\/?$/, '')}logout/?next=${encodeURIComponent(here)}`)
}
const panelLogoUrl = computed(() => getPanelLogoUrl())
</script>

<template>
  <div class="layout-topbar">
    <div class="layout-topbar-logo-container">
      <button type="button" class="layout-menu-button layout-topbar-action" @click="toggleMenu">
        <i class="pi pi-bars" />
      </button>
      <router-link to="/" class="layout-topbar-logo">
        <img
          v-if="panelLogoUrl"
          :src="panelLogoUrl"
          alt="Hiddify"
          class="layout-topbar-logo-image"
        />
        <i v-else class="pi pi-shield" />
        <span class="layout-topbar-logo-text">
          <span class="layout-topbar-title">{{ t('appTitle') }}</span>
          <span v-if="panelVersion" class="layout-topbar-version ltr">{{ panelVersion }}</span>
        </span>
      </router-link>
    </div>
    <div class="layout-topbar-actions">
      <!-- My account: limits and password (a node's admins are managed on its parent) -->
      <router-link
        v-if="!isChildPanel"
        to="/account"
        class="layout-topbar-action"
        active-class="layout-topbar-action--active"
        :aria-label="t('menu.myAccount')"
        v-tooltip.bottom="t('menu.myAccount')"
      >
        <i class="pi pi-user" />
      </router-link>
      <button type="button" class="layout-topbar-action" :aria-label="t('theme.dark')" @click="toggleDarkMode">
        <i :class="['pi', isDarkTheme ? 'pi-sun' : 'pi-moon']" />
      </button>
      <button type="button" class="layout-topbar-action" :aria-label="t('menu.signOut')" v-tooltip.bottom="t('menu.signOut')" @click="signOut">
        <i class="pi pi-sign-out" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.layout-topbar-action--active {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
</style>
