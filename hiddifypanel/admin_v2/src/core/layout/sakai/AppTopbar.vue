<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLayout } from './composables/layout'
import { getPanelLogoUrl, getPanelVersion } from '@/core/panel-branding'

const { t } = useI18n()
const { toggleMenu, toggleDarkMode, isDarkTheme } = useLayout()

const panelVersion = computed(() => getPanelVersion())
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
      <button type="button" class="layout-topbar-action" :aria-label="t('theme.dark')" @click="toggleDarkMode">
        <i :class="['pi', isDarkTheme ? 'pi-sun' : 'pi-moon']" />
      </button>
    </div>
  </div>
</template>
