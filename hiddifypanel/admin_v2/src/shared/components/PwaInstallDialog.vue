<template>
  <Dialog
    v-model:visible="visible"
    modal
    :show-header="false"
    :dismissable-mask="true"
    :position="narrow ? 'bottom' : 'center'"
    :draggable="false"
    :style="{ width: 'min(25rem, 100vw)' }"
    :pt="{ root: { class: ['pwa-dialog', { 'pwa-dialog--sheet': narrow }] }, content: { class: 'pwa-dialog__content' } }"
  >
    <div class="pwa">
      <button type="button" class="pwa__close" :aria-label="t('pwa.later')" @click="close"><i class="pi pi-times" /></button>

      <!-- The app as it will look on the home screen -->
      <div class="pwa__hero">
        <div class="pwa__app">
          <img v-if="icon" :src="icon" alt="" class="pwa__icon" />
          <i v-else class="pi pi-mobile pwa__icon pwa__icon--fallback" />
        </div>
        <h2 class="pwa__title">{{ t('pwa.title') }}</h2>
        <p class="pwa__text">{{ t('pwa.text') }}</p>
      </div>

      <ul class="pwa__perks">
        <li><span class="pwa__perk-icon"><i class="pi pi-bolt" /></span>{{ t('pwa.perkFast') }}</li>
        <li><span class="pwa__perk-icon"><i class="pi pi-window-maximize" /></span>{{ t('pwa.perkWindow') }}</li>
        <li><span class="pwa__perk-icon"><i class="pi pi-sync" /></span>{{ t('pwa.perkFresh') }}</li>
      </ul>

      <!-- No install dialog from the browser: how to add it by hand -->
      <ol v-if="iosManual || !canPrompt" class="pwa__steps">
        <template v-if="iosManual">
          <li><span class="pwa__step-n">1</span>{{ t('pwa.iosShare') }} <i class="pi pi-upload pwa__step-icon" /></li>
          <li><span class="pwa__step-n">2</span>{{ t('pwa.iosAdd') }} <i class="pi pi-plus-circle pwa__step-icon" /></li>
        </template>
        <template v-else>
          <li><span class="pwa__step-n">1</span>{{ t('pwa.menuOpen') }} <i class="pi pi-ellipsis-v pwa__step-icon" /></li>
          <li><span class="pwa__step-n">2</span>{{ t('pwa.menuInstall') }} <i class="pi pi-download pwa__step-icon" /></li>
        </template>
      </ol>

      <div class="pwa__actions">
        <Button v-if="canPrompt" icon="pi pi-download" :label="t('pwa.install')" size="large" class="pwa__install" :loading="busy" @click="doInstall" />
        <Button :label="canPrompt ? t('pwa.later') : t('pwa.gotIt')" severity="secondary" text class="pwa__later" @click="close" />
      </div>

      <label class="pwa__never">
        <Checkbox v-model="never" binary input-id="pwa-never" />
        <span>{{ t('pwa.never') }}</span>
      </label>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import { usePwaInstall } from '@/shared/composables/usePwaInstall'

/** `manual`: opened from a button (always shows); otherwise it offers itself once per visit, unless the user said never. */
const props = defineProps<{ manual?: boolean }>()
const visible = defineModel<boolean>('visible', { default: false })

const { t } = useI18n()
const { available, canPrompt, iosManual, dismissed, install, dismissForever } = usePwaInstall()
const never = ref(false)
const busy = ref(false)
const icon = ref('')

// Phones: a sheet from the bottom.
const narrowQuery = window.matchMedia('(max-width: 575px)')
const narrow = ref(narrowQuery.matches)
const onNarrow = (e: MediaQueryListEvent) => (narrow.value = e.matches)

/** The app icon the page declares (production template, or added from the bootstrap in dev). */
function readIcon() {
  icon.value = document.head.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"]')?.href || window.__PANEL_LOGO_URL__ || ''
}

const SESSION_KEY = 'hiddify.pwaInstall.offered'
function offeredThisVisit(): boolean {
  try {
    return sessionStorage.getItem(SESSION_KEY) === '1'
  } catch {
    return false
  }
}

function offer() {
  if (props.manual || visible.value || dismissed.value || offeredThisVisit() || !available.value) return
  readIcon()
  visible.value = true
  try {
    sessionStorage.setItem(SESSION_KEY, '1')
  } catch {
    /* ignore */
  }
}

onMounted(() => {
  narrowQuery.addEventListener('change', onNarrow)
  window.setTimeout(offer, 1500) // the browser's install event can come a little after the page
})
onBeforeUnmount(() => narrowQuery.removeEventListener('change', onNarrow))
watch(available, (ok) => ok && window.setTimeout(offer, 500))
watch(visible, (open) => open && readIcon())

function close() {
  if (never.value) dismissForever()
  visible.value = false
}

async function doInstall() {
  if (never.value) dismissForever()
  busy.value = true
  try {
    await install()
    visible.value = false
  } catch {
    /* the browser refused: the menu steps show instead (canPrompt is now false) */
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.pwa {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.pwa__close {
  position: absolute;
  top: 0.25rem;
  inset-inline-end: 0.25rem;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-content-background) 70%, transparent);
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.pwa__close:hover,
.pwa__close:focus-visible {
  color: var(--p-text-color);
  outline: 2px solid var(--p-primary-color);
}

.pwa__hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.4rem;
  margin: -1.25rem -1.25rem 0;
  padding: 1.75rem 1.5rem 1.25rem;
  background: radial-gradient(120% 90% at 50% 0%, color-mix(in srgb, var(--p-primary-color) 22%, transparent), transparent 70%);
}
.pwa__app {
  display: grid;
  place-items: center;
  width: 5rem;
  height: 5rem;
  margin-bottom: 0.4rem;
  border-radius: 1.4rem;
  background: var(--p-content-background);
  box-shadow:
    0 10px 30px -8px color-mix(in srgb, var(--p-primary-color) 55%, transparent),
    0 0 0 1px var(--p-content-border-color);
  animation: pwa-pop 0.45s cubic-bezier(0.2, 0.9, 0.3, 1.3) both;
}
.pwa__icon {
  width: 4.1rem;
  height: 4.1rem;
  border-radius: 1.1rem;
  object-fit: contain;
}
.pwa__icon--fallback {
  display: grid;
  place-items: center;
  font-size: 2.2rem;
  color: var(--p-primary-color);
}
.pwa__title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 700;
}
.pwa__text {
  margin: 0;
  max-width: 20rem;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  line-height: 1.6;
}

.pwa__perks {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.pwa__perks li {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.9rem;
}
.pwa__perk-icon {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 10px;
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
}

.pwa__steps {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin: 0;
  padding: 0.75rem;
  list-style: none;
  border-radius: 12px;
  background: var(--p-content-hover-background);
}
.pwa__steps li {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.88rem;
}
.pwa__step-n {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font-size: 0.75rem;
  font-weight: 700;
}
.pwa__step-icon {
  margin-inline-start: auto;
  color: var(--p-text-muted-color);
}

.pwa__actions {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.pwa__install,
.pwa__later {
  width: 100%;
}
.pwa__never {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: -0.25rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
  cursor: pointer;
}

@keyframes pwa-pop {
  from {
    transform: scale(0.7) translateY(6px);
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pwa__app {
    animation: none;
  }
}
</style>

<style>
/* The dialog itself (not scoped: PrimeVue renders it outside this component) */
.pwa-dialog .pwa-dialog__content {
  padding: 1.25rem;
  overflow: hidden;
  border-radius: inherit;
}
.pwa-dialog {
  border-radius: 22px;
  overflow: hidden;
}
/* Phones: a sheet from the bottom, round only on top */
.pwa-dialog.pwa-dialog--sheet {
  margin: 0;
  border-radius: 22px 22px 0 0;
  max-height: 92vh;
}
.pwa-dialog.pwa-dialog--sheet .pwa-dialog__content {
  overflow: auto;
  padding-bottom: calc(1.25rem + env(safe-area-inset-bottom));
}
</style>
