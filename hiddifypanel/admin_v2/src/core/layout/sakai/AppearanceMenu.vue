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
const { isDarkTheme, toggleDarkMode, caddyAccent, setCaddyAccent } = useLayout()

/** The swatch of each Smart Caddy color: the two ends of its accent gradient (as in _theme-caddy.scss). */
const SWATCH: Record<CaddyAccent, string> = {
  red: 'linear-gradient(135deg, #ff8a6e, #f2505f)',
  pink: 'linear-gradient(135deg, #f9a8d4, #d946ef)',
  orange: 'linear-gradient(135deg, #fdba74, #f97316)',
  yellow: 'linear-gradient(135deg, #fde68a, #eab308)',
  green: 'linear-gradient(135deg, #6ee7b7, #14b8a6)',
  blue: 'linear-gradient(135deg, #7dd3fc, #3b82f6)',
  purple: 'linear-gradient(135deg, #c4b5fd, #7c3aed)',
  graphite: 'linear-gradient(135deg, #9a9ba6, #3f4049)',
  spacegray: 'linear-gradient(135deg, #c3c5c9, #6c6f74)',
  brown: 'linear-gradient(135deg, #c8a07c, #6b412b)',
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
  if (dark !== isDarkTheme.value) toggleDarkMode()
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
    <i class="pi pi-sliders-h" />
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
          <!-- Chosen: only its flag (the name is in the list, the tooltip and for screen readers) -->
          <template #value>
            <span v-if="current" class="appearance__flag appearance__flag--chosen" role="img" :aria-label="current.label" :title="current.label">{{ current.flag }}</span>
          </template>
          <template #option="{ option }">
            <span class="appearance__lang-value"><span class="appearance__flag">{{ option.flag }}</span>{{ option.label }}</span>
          </template>
        </Select>
      </section>

      <!-- Light / dark: this browser only; every theme below has both -->
      <section class="appearance__section">
        <span class="appearance__title"><i :class="['pi', isDarkTheme ? 'pi-moon' : 'pi-sun']" />{{ t('theme.mode') }}</span>
        <div class="appearance__modes" role="radiogroup" :aria-label="t('theme.mode')">
          <button type="button" role="radio" class="appearance__choice" :class="{ 'appearance__choice--active': !isDarkTheme }" :aria-checked="!isDarkTheme" @click="setDark(false)">
            <i class="pi pi-sun" />{{ t('theme.light') }}
          </button>
          <button type="button" role="radio" class="appearance__choice" :class="{ 'appearance__choice--active': isDarkTheme }" :aria-checked="isDarkTheme" @click="setDark(true)">
            <i class="pi pi-moon" />{{ t('theme.dark') }}
          </button>
        </div>
      </section>

      <!-- Theme: the panel's own, or Smart Caddy glass in a color, in the light or dark chosen above; this browser only -->
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
  flex-shrink: 0;
}
.appearance__lang :deep(.p-select-label) {
  padding-inline: 0.6rem 0.2rem;
}
/* The list keeps flag and name, a little wider than the flag-only button. */
.appearance__lang :deep(.p-select-overlay) {
  min-width: 11rem;
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
.appearance__flag--chosen {
  display: block;
  font-size: 1.35rem;
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
.appearance__choice:hover {
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
  /* Ten colors: two rows of five, so each tile stays a comfortable size. */
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.5rem;
}
/* Glass tiles: the color a little translucent, a bright edge and a light sweep across the top. */
.appearance__swatch {
  position: relative;
  width: 100%;
  max-width: 2.25rem;
  aspect-ratio: 1;
  justify-self: center;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid rgb(255 255 255 / 45%);
  border-radius: 11px;
  background: transparent;
  color: #fff;
  font-size: 0.75rem;
  cursor: pointer;
  overflow: hidden;
  isolation: isolate;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 55%),
    inset 0 -6px 12px -6px rgb(0 0 0 / 25%),
    0 8px 16px -10px rgb(0 0 0 / 55%);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.appearance__swatch::before,
.appearance__swatch::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
}
.appearance__swatch::before {
  background: var(--swatch);
  opacity: 0.78;
}
.appearance__swatch::after {
  background:
    radial-gradient(120% 70% at 25% 0%, rgb(255 255 255 / 60%) 0%, rgb(255 255 255 / 0%) 55%),
    linear-gradient(160deg, rgb(255 255 255 / 25%) 0%, rgb(255 255 255 / 0%) 45%);
}
.appearance__swatch .pi {
  filter: drop-shadow(0 1px 1px rgb(0 0 0 / 45%));
}
.appearance__swatch:hover {
  transform: translateY(-2px);
}
.appearance__swatch--active {
  border-color: rgb(255 255 255 / 85%);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 70%),
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
