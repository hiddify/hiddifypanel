<template>
  <div class="pwa-color">
    <!-- `center`: where the window's left edge goes, so that it opens centred under the button -->
    <span v-if="center" ref="anchor" class="pwa-color__anchor" aria-hidden="true" />
    <Button type="button" severity="secondary" outlined rounded size="small" class="pwa-color__button" aria-haspopup="dialog" :aria-expanded="shown" @click="toggle">
      <span class="pwa-color__dot" :style="{ '--swatch': `#${color}` }" aria-hidden="true" />
      <span>{{ t('pwa.colorButton') }}</span>
      <i class="pi pi-chevron-down pwa-color__caret" :class="{ 'pwa-color__caret--up': shown }" aria-hidden="true" />
    </Button>
    <!-- A small window with the ready colors and "your own color" -->
    <Popover ref="pop" :pt="{ root: { class: ['pwa-color-pop', { 'pwa-color-pop--center': center }] }, content: { class: 'pwa-color-pop__content' } }" @show="shown = true" @hide="shown = false">
      <PwaIconColors @resize="realign" />
    </Popover>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import PwaIconColors from '@/shared/components/PwaIconColors.vue'
import { useAppIcon } from '@/shared/composables/useAppIcon'

/**
 * "PWA Color": a button that opens a small window to choose the color of the admin app icon (PwaIconColors). The dot
 * on it is the color chosen now. Used in the install dialog (under the icon) and in My account (Settings).
 */
const props = defineProps<{ /** open the window centred under the button (the install dialog), not at its edge */ center?: boolean }>()
const { t } = useI18n()
const { color } = useAppIcon()
const pop = ref<InstanceType<typeof Popover> | null>(null)
const anchor = ref<HTMLElement | null>(null)
const shown = ref(false)

function toggle(event: Event) {
  pop.value?.toggle(event, props.center ? anchor.value : undefined)
}
/** The window grew or shrank (the own-color picker): put it back next to the button, on screen. */
function realign() {
  window.setTimeout(() => (pop.value as unknown as { alignOverlay?: () => void } | null)?.alignOverlay?.(), 280)
}
</script>

<style scoped>
.pwa-color {
  position: relative;
  display: inline-flex;
}
/* Half the window's width to the left of the button's middle (the window: 21rem, or the screen less a margin) */
.pwa-color__anchor {
  position: absolute;
  inset-block: 0;
  left: calc(50% - min(10.5rem, 50vw - 0.75rem));
  width: 0;
  pointer-events: none;
}
.pwa-color__button {
  gap: 0.45rem;
  padding-inline: 0.7rem 0.65rem;
  font-weight: 600;
  white-space: nowrap;
}
/* The color chosen now, as a small glass tile */
.pwa-color__dot {
  --swatch: var(--p-primary-color);
  flex: none;
  width: 1.05rem;
  height: 1.05rem;
  border-radius: 31%;
  background:
    radial-gradient(120% 80% at 28% 0%, rgb(255 255 255 / 52%) 0%, rgb(255 255 255 / 0%) 55%),
    linear-gradient(180deg, color-mix(in srgb, var(--swatch) 86%, white) 0%, var(--swatch) 46%, color-mix(in srgb, var(--swatch) 80%, black) 100%);
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / 28%),
    0 1px 2px rgb(0 0 0 / 28%);
}
.pwa-color__caret {
  font-size: 0.62rem;
  opacity: 0.7;
  transition: transform 0.2s ease;
}
.pwa-color__caret--up {
  transform: rotate(180deg);
}
@media (prefers-reduced-motion: reduce) {
  .pwa-color__caret {
    transition: none;
  }
}
</style>

<style>
/* The window itself (not scoped: PrimeVue renders it outside this component) */
.p-popover.pwa-color-pop {
  width: min(21rem, calc(100vw - 1.5rem));
  border-radius: 18px;
}
/* Centred under the button: no arrow (it would point beside the button) */
.p-popover.pwa-color-pop--center::before,
.p-popover.pwa-color-pop--center::after {
  display: none;
}
.p-popover.pwa-color-pop .pwa-color-pop__content {
  max-height: min(36rem, calc(100vh - 1.5rem));
  max-height: min(36rem, calc(100dvh - 1.5rem));
  padding: 0.9rem 0.95rem 1rem;
  overflow-y: auto;
  overscroll-behavior: contain;
}
</style>
