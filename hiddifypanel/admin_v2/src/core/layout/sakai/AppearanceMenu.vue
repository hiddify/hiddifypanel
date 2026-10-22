<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import { CADDY_ACCENTS, useLayout, type CaddyAccent } from './composables/layout'
import { apiErrorMessage } from '@/core/api/client'
import { adminsApi, type MyAccount } from '@/features/admins/api'
import { LANGUAGE_LOOK } from '@/shared/utils/languages'

/** Top bar: one button for the admin's language, light/dark and the theme (the panel's own, or Smart Caddy glass
 *  in a color: _theme-caddy.scss). */
const { t } = useI18n()
const toast = useToast()
const { isDarkTheme, toggleDarkMode, isCaddyTheme, caddyAccent, setCaddyAccent } = useLayout()

/** The swatch of each Smart Caddy color: the two ends of its accent gradient (as in _theme-caddy.scss). */
const SWATCH: Record<CaddyAccent, string> = {
  red: 'linear-gradient(135deg, #ff8a6e, #f2505f)',
  pink: 'linear-gradient(135deg, #f9a8d4, #d946ef)',
  orange: 'linear-gradient(135deg, #fdba74, #f97316)',
  yellow: 'linear-gradient(135deg, #fde68a, #eab308)',
  green: 'linear-gradient(135deg, #6ee7b7, #14b8a6)',
  blue: 'linear-gradient(135deg, #7dd3fc, #3b82f6)',
  purple: 'linear-gradient(135deg, #c4b5fd, #7c3aed)',
}

const panel = ref<InstanceType<typeof Popover> | null>(null)
const open = ref(false)
const me = ref<MyAccount | null>(null)
const meState = ref<'idle' | 'loading' | 'ready' | 'failed'>('idle')
const savingLang = ref(false)

async function loadMe() {
  meState.value = 'loading'
  try {
    me.value = await adminsApi.me()
    meState.value = 'ready'
  } catch {
    meState.value = 'failed'
  }
}

function toggle(event: Event) {
  panel.value?.toggle(event)
  // The languages come with "my account": asked the first time the menu opens, not on every page.
  if (meState.value === 'idle') void loadMe()
}

interface LanguageOption {
  value: string
  flag: string
  label: string
}

const languages = computed<LanguageOption[]>(() => {
  if (!me.value) return []
  const defaultName = LANGUAGE_LOOK[me.value.default_lang]?.name ?? me.value.default_lang
  return [
    { value: '', flag: '🌐', label: t('account.languageDefault', { name: defaultName }) },
    ...me.value.languages.map((value) => ({ value, flag: LANGUAGE_LOOK[value]?.flag ?? '🏳️', label: LANGUAGE_LOOK[value]?.name ?? value })),
  ]
})
/** The button shows the language in use: the admin's own, or the panel default's (flag and native name). */
const current = computed(() => {
  if (!me.value) return null
  const code = me.value.lang || me.value.default_lang
  return { flag: LANGUAGE_LOOK[code]?.flag ?? '🌐', label: LANGUAGE_LOOK[code]?.name ?? code }
})

async function pickLanguage(lang: string) {
  if (!me.value || savingLang.value || lang === me.value.lang) return
  savingLang.value = true
  try {
    await adminsApi.setMyLanguage(lang)
    // The interface language is chosen when the page loads (the server translates the menu too).
    window.location.reload()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
    savingLang.value = false
  }
}

function setDark(dark: boolean) {
  // A color theme is always dark; light/dark is the Hiddify theme's choice.
  if (!isCaddyTheme.value && dark !== isDarkTheme.value) toggleDarkMode()
}
</script>

<template>
  <button
    type="button"
    class="layout-topbar-action"
    :class="{ 'layout-topbar-action--active': open }"
    :aria-label="t('theme.menu')"
    aria-haspopup="dialog"
    :aria-expanded="open"
    @click="toggle"
  >
    <i class="pi pi-palette" />
  </button>

  <Popover ref="panel" class="appearance-popover" @show="open = true" @hide="open = false">
    <div class="appearance" role="dialog" :aria-label="t('theme.menu')">
      <!-- Language: one row; the flag opens the others (the signed-in admin's own, saved on the server) -->
      <section class="appearance__row">
        <span class="appearance__title"><i class="pi pi-language" />{{ t('account.languageTitle') }}</span>
        <Skeleton v-if="meState === 'loading' || meState === 'idle'" width="9rem" height="2.25rem" border-radius="10px" />
        <Button v-else-if="meState === 'failed'" :label="t('theme.retry')" icon="pi pi-refresh" size="small" text @click="loadMe" />
        <Select
          v-else
          :model-value="me?.lang ?? ''"
          :options="languages"
          option-label="label"
          option-value="value"
          append-to="self"
          :loading="savingLang"
          :disabled="savingLang"
          class="appearance__lang"
          :aria-label="t('account.languageTitle')"
          @update:model-value="pickLanguage"
        >
          <template #value>
            <span v-if="current" class="appearance__lang-value"><span class="appearance__flag">{{ current.flag }}</span>{{ current.label }}</span>
          </template>
          <template #option="{ option }">
            <span class="appearance__lang-value"><span class="appearance__flag">{{ option.flag }}</span>{{ option.label }}</span>
          </template>
        </Select>
      </section>

      <!-- Light / dark: this browser only; for the Hiddify theme (the color themes are always dark) -->
      <section class="appearance__section">
        <span class="appearance__title"><i :class="['pi', isDarkTheme ? 'pi-moon' : 'pi-sun']" />{{ t('theme.mode') }}</span>
        <div class="appearance__modes" role="radiogroup" :aria-label="t('theme.mode')" :aria-disabled="isCaddyTheme">
          <button type="button" role="radio" class="appearance__choice" :class="{ 'appearance__choice--active': !isDarkTheme }" :aria-checked="!isDarkTheme" :disabled="isCaddyTheme" @click="setDark(false)">
            <i class="pi pi-sun" />{{ t('theme.light') }}
          </button>
          <button type="button" role="radio" class="appearance__choice" :class="{ 'appearance__choice--active': isDarkTheme }" :aria-checked="isDarkTheme" :disabled="isCaddyTheme" @click="setDark(true)">
            <i class="pi pi-moon" />{{ t('theme.dark') }}
          </button>
        </div>
        <small v-if="isCaddyTheme" class="appearance__hint"><i class="pi pi-info-circle" /> {{ t('theme.modeLocked') }}</small>
      </section>

      <!-- Theme: the panel's own, or Smart Caddy glass in a color (light or dark as above); this browser only -->
      <section class="appearance__section">
        <span class="appearance__title"><i class="pi pi-palette" />{{ t('theme.color') }}</span>
        <button
          type="button"
          role="radio"
          class="appearance__choice appearance__default"
          :class="{ 'appearance__choice--active': caddyAccent === null }"
          :aria-checked="caddyAccent === null"
          @click="setCaddyAccent(null)"
        >
          <span class="appearance__default-dot" aria-hidden="true" />{{ t('theme.default') }}
        </button>
        <div class="appearance__swatches" role="radiogroup" :aria-label="t('theme.caddy')">
          <button
            v-for="item in CADDY_ACCENTS"
            :key="item"
            type="button"
            role="radio"
            class="appearance__swatch"
            :class="{ 'appearance__swatch--active': caddyAccent === item }"
            :style="{ '--swatch': SWATCH[item] }"
            :aria-checked="caddyAccent === item"
            :aria-label="`${t('theme.caddy')}: ${t(`theme.colors.${item}`)}`"
            v-tooltip.bottom="t(`theme.colors.${item}`)"
            @click="setCaddyAccent(item)"
          >
            <i v-if="caddyAccent === item" class="pi pi-check" />
          </button>
        </div>
        <small class="appearance__hint">{{ t('theme.glassHint') }}</small>
      </section>
    </div>
  </Popover>
</template>

<style scoped>
/* On the topbar: its own text color (the primary color would vanish on the primary-colored bar). */
.layout-topbar-action--active {
  color: var(--topbar-text, #fff);
  background: var(--topbar-hover, rgb(255 255 255 / 14%));
}
.appearance {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: min(19.5rem, calc(100vw - 2.5rem));
}
.appearance__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.appearance__section {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding-top: 1rem;
  border-top: 1px solid var(--p-content-border-color);
}
.appearance__title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.appearance__title i {
  font-size: 0.8rem;
  color: var(--p-primary-color);
}
.appearance__lang {
  min-width: 0;
  max-width: 12rem;
}
.appearance__lang-value {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.appearance__flag {
  font-size: 1.1rem;
  line-height: 1;
}
.appearance__modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}
.appearance__choice {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-width: 0;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px;
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.86rem;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}
.appearance__choice:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.appearance__choice:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--p-primary-color) 50%, var(--p-content-border-color));
  background: var(--p-content-hover-background);
}
.appearance__choice--active {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
  font-weight: 600;
}
.appearance__choice:focus-visible,
.appearance__swatch:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.appearance__default {
  justify-content: flex-start;
}
/* The panel's own look: its blue. */
.appearance__default-dot {
  width: 0.9rem;
  height: 0.9rem;
  flex-shrink: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
}
.appearance__swatches {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.5rem;
}
.appearance__swatch {
  width: 100%;
  max-width: 2.25rem;
  aspect-ratio: 1;
  justify-self: center;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: var(--swatch);
  color: #fff;
  font-size: 0.75rem;
  cursor: pointer;
  box-shadow: 0 6px 14px -8px rgb(0 0 0 / 60%);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.appearance__swatch:hover {
  transform: translateY(-2px);
}
.appearance__swatch--active {
  box-shadow:
    0 0 0 2px var(--p-content-background),
    0 0 0 4px var(--p-text-color);
}
.appearance__hint {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
@media (prefers-reduced-motion: reduce) {
  .appearance__swatch {
    transition: none;
  }
  .appearance__swatch:hover {
    transform: none;
  }
}
</style>
