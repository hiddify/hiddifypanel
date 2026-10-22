<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { CADDY_ACCENTS, useLayout } from './composables/layout'
import { getPanelLogoUrl, getPanelVersion } from '@/core/panel-branding'
import { isChildPanel, submitPostForm } from '@/core/panelShell'
import { getRouterBase } from '@/core/api/client'

const { t } = useI18n()
const { toggleMenu, isDarkTheme, isCaddyTheme, caddyAccent, setCaddyAccent, setHiddifyMode } = useLayout()
const themePopover = ref()

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
      <!-- Appearance: the panel's own look (light / dark) or Smart Caddy in a color, in one dialog -->
      <button
        type="button"
        class="layout-topbar-action"
        :class="{ 'layout-topbar-action--active': isCaddyTheme }"
        :aria-label="t('theme.appearance')"
        v-tooltip.bottom="t('theme.appearance')"
        @click="(e: Event) => themePopover.toggle(e)"
      >
        <i :class="['pi', isCaddyTheme ? 'pi-palette' : isDarkTheme ? 'pi-moon' : 'pi-sun']" />
      </button>
      <Popover ref="themePopover">
        <div class="theme-picker">
          <div class="theme-picker-title">{{ t('theme.hiddify') }}</div>
          <div class="theme-picker-modes">
            <button
              type="button"
              class="theme-mode"
              :class="{ 'theme-mode--on': !isCaddyTheme && !isDarkTheme }"
              @click="setHiddifyMode(false)"
            >
              <i class="pi pi-sun" />
              {{ t('theme.light') }}
            </button>
            <button
              type="button"
              class="theme-mode"
              :class="{ 'theme-mode--on': !isCaddyTheme && isDarkTheme }"
              @click="setHiddifyMode(true)"
            >
              <i class="pi pi-moon" />
              {{ t('theme.dark') }}
            </button>
          </div>
          <div class="theme-picker-title">
            {{ t('theme.caddy') }}
            <small>{{ t('theme.caddyHint') }}</small>
          </div>
          <div class="theme-picker-swatches">
            <button
              v-for="accent in CADDY_ACCENTS"
              :key="accent"
              type="button"
              class="theme-swatch"
              :class="[`theme-swatch--${accent}`, { 'theme-swatch--on': caddyAccent === accent }]"
              :aria-label="t(`theme.colors.${accent}`)"
              v-tooltip.bottom="t(`theme.colors.${accent}`)"
              @click="setCaddyAccent(accent)"
            />
          </div>
        </div>
      </Popover>
      <button type="button" class="layout-topbar-action" :aria-label="t('menu.signOut')" v-tooltip.bottom="t('menu.signOut')" @click="signOut">
        <i class="pi pi-sign-out" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.theme-picker {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 15rem;
}
.theme-picker-title {
  font-weight: 600;
}
.theme-picker-swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.theme-swatch {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  border: 2px solid transparent;
  cursor: pointer;
  box-shadow: 0 6px 14px -8px rgb(0 0 0 / 60%);
  transition: transform 0.15s;
}
.theme-swatch:hover {
  transform: translateY(-2px);
}
.theme-swatch--on {
  border-color: var(--p-text-color);
  outline: 3px solid color-mix(in srgb, var(--p-text-color) 25%, transparent);
}
.theme-swatch--red { background: linear-gradient(135deg, #ff8a6e, #f2505f); }
.theme-swatch--pink { background: linear-gradient(135deg, #f9a8d4, #d946ef); }
.theme-swatch--orange { background: linear-gradient(135deg, #fdba74, #f97316); }
.theme-swatch--yellow { background: linear-gradient(135deg, #fde68a, #eab308); }
.theme-swatch--green { background: linear-gradient(135deg, #6ee7b7, #14b8a6); }
.theme-swatch--blue { background: linear-gradient(135deg, #7dd3fc, #3b82f6); }
.theme-swatch--purple { background: linear-gradient(135deg, #c4b5fd, #7c3aed); }
.theme-picker-title small {
  display: block;
  font-weight: 400;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.theme-picker-modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.theme-mode {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: transparent;
  color: var(--p-text-color);
  cursor: pointer;
  font: inherit;
}
.theme-mode:hover {
  border-color: var(--p-primary-color);
}
.theme-mode--on {
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  font-weight: 600;
}

.layout-topbar-action--active {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
</style>
