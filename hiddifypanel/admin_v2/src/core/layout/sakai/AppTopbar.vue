<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLayout } from './composables/layout'
import AppearanceMenu from './AppearanceMenu.vue'
import NotificationsMenu from './NotificationsMenu.vue'
import { getPanelLogoUrl, getPanelVersion } from '@/core/panel-branding'
import { isChildPanel, submitPostForm } from '@/core/panelShell'
import { getRouterBase } from '@/core/api/client'

const { t } = useI18n()
const { toggleMenu } = useLayout()

const panelVersion = computed(() => getPanelVersion())

/** Ends the session on the server (POST only), then the sign-in page opens. */
function signOut() {
  // After signing in again: back to this page.
  const here = window.location.pathname + window.location.search + window.location.hash
  submitPostForm(`${getRouterBase().replace(/admin\/v2\/?$/, '')}logout/?next=${encodeURIComponent(here)}`)
}
const panelLogoUrl = computed(() => getPanelLogoUrl())

/** The panel's name only when it fits whole: where it would end in "…" (a narrow phone), only the logo stays. */
const topbarEl = ref<HTMLElement | null>(null)
const logoTextEl = ref<HTMLElement | null>(null)
const titleEl = ref<HTMLElement | null>(null)
function fitName() {
  const box = logoTextEl.value
  const title = titleEl.value
  if (!box || !title) return
  // measured with the name shown, in the same frame (nothing is painted in between)
  box.classList.remove('layout-topbar-logo-text--hidden')
  box.classList.toggle('layout-topbar-logo-text--hidden', title.scrollWidth > title.clientWidth + 1)
}
let resizeObserver: ResizeObserver | null = null
onMounted(() => {
  fitName()
  resizeObserver = new ResizeObserver(fitName)
  if (topbarEl.value) resizeObserver.observe(topbarEl.value)
})
onBeforeUnmount(() => resizeObserver?.disconnect())
watch(() => t('appTitle'), () => nextTick(fitName))
</script>

<template>
  <div ref="topbarEl" class="layout-topbar">
    <div class="layout-topbar-logo-container">
      <button type="button" class="layout-menu-button layout-topbar-action" @click="toggleMenu">
        <i class="pi pi-bars" />
      </button>
      <router-link to="/" class="layout-topbar-logo" :aria-label="t('appTitle')">
        <img
          v-if="panelLogoUrl"
          :src="panelLogoUrl"
          alt="Hiddify"
          class="layout-topbar-logo-image"
        />
        <i v-else class="pi pi-shield" />
        <span ref="logoTextEl" class="layout-topbar-logo-text">
          <span ref="titleEl" class="layout-topbar-title">{{ t('appTitle') }}</span>
          <span v-if="panelVersion" class="layout-topbar-version ltr">{{ panelVersion }}</span>
        </span>
      </router-link>
    </div>
    <div class="layout-topbar-actions">
      <!-- The panel's notices (only while there are some) -->
      <NotificationsMenu />
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
      <!-- Language, light/dark and the theme (Hiddify or Smart Caddy glass in a color) -->
      <AppearanceMenu />
      <button type="button" class="layout-topbar-action" :aria-label="t('menu.signOut')" v-tooltip.bottom="t('menu.signOut')" @click="signOut">
        <i class="pi pi-sign-out" />
      </button>
    </div>
  </div>
</template>

<style scoped>
/* On the topbar: its own text color (the primary color would vanish on the primary-colored bar), as the
   notifications and appearance buttons do when open. */
.layout-topbar-action--active {
  color: var(--topbar-text, #fff);
  background: var(--topbar-hover, rgb(255 255 255 / 14%));
}
</style>
