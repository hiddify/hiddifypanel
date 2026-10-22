<template>
  <Dialog
    v-model:visible="visible"
    modal
    :show-header="false"
    :dismissable-mask="true"
    :position="narrow ? 'bottom' : 'center'"
    :draggable="false"
    :style="{ width: 'min(27rem, 100vw)' }"
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

      <!-- How to install, animated for this device (Safari on iPhone, Chrome on Android or a computer) -->
      <PwaInstallGuide />

      <label class="pwa__never">
        <Checkbox v-model="never" binary input-id="pwa-never" />
        <span>{{ t('pwa.never') }}</span>
      </label>

      <div class="pwa__actions">
        <Button :label="t('pwa.gotIt')" icon="pi pi-check" size="large" class="pwa__got" autofocus @click="close" />
        <!-- The browser can install it right away: one click instead of the steps -->
        <Button v-if="canPrompt" icon="pi pi-download" :label="t('pwa.installNow')" severity="secondary" outlined class="pwa__install" :loading="busy" @click="doInstall" />
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import { usePwaInstall } from '@/shared/composables/usePwaInstall'
import PwaInstallGuide from '@/shared/components/PwaInstallGuide.vue'

/**
 * `manual`: opened from a button (always shows). Otherwise it offers itself on the dashboard (a node: its home), each
 * time the panel is opened (once per page load), unless the panel already runs as the app or the user said never.
 */
const props = defineProps<{ manual?: boolean }>()
const visible = defineModel<boolean>('visible', { default: false })

const { t } = useI18n()
const { installed, canPrompt, dismissed, install, dismissForever } = usePwaInstall()
const route = useRoute()
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

/** Offered once per page load (module state): coming back to the dashboard in the same visit does not repeat it. */
let offeredThisLoad = false
const HOME_ROUTES = ['dashboard', 'node-home']

function offer() {
  if (props.manual || visible.value || offeredThisLoad || dismissed.value || installed.value) return
  if (!HOME_ROUTES.includes(String(route.name ?? ''))) return
  offeredThisLoad = true
  readIcon()
  visible.value = true
}

onMounted(() => {
  narrowQuery.addEventListener('change', onNarrow)
  window.setTimeout(offer, 1200) // after the page has drawn (the browser's install event can come a little later too)
})
onBeforeUnmount(() => narrowQuery.removeEventListener('change', onNarrow))
// Opened on another page first: the guide waits for the dashboard.
watch(() => route.name, () => window.setTimeout(offer, 600))
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



.pwa__actions {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.pwa__got,
.pwa__install {
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
