<script setup lang="ts">
/**
 * The footer: Hiddify Manager as a wordmark; a light sweeps across it under the mouse. A click opens a small window
 * above it with Hiddify's website and channels, each in a new tab; the channel under the mouse comes alive.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { BRAND_PATHS, type BrandIcon } from '@/shared/utils/brand-icons'

const { t } = useI18n()

/** "HiddifyManager": "Hiddify" strong and "Manager" in the color; a translated name stays whole */
const name = computed(() => {
  const text = t('footer.text')
  const m = /^(Hiddify)\s*(.+)$/.exec(text)
  return m ? { first: m[1], rest: m[2] } : { first: text, rest: '' }
})

interface Link {
  key: string
  label: string
  href: string
  icon: BrandIcon | 'web'
}
const LINKS = computed<Link[]>(() => [
  { key: 'web', label: t('footer.website'), href: 'https://hiddify.com', icon: 'web' },
  { key: 'github', label: 'GitHub', href: 'https://github.com/hiddify/Hiddify-Manager', icon: 'github' },
  { key: 'x', label: 'X', href: 'https://x.com/hiddify_com', icon: 'x' },
  { key: 'telegram', label: 'Telegram', href: 'https://t.me/hiddify', icon: 'telegram' },
  { key: 'youtube', label: 'YouTube', href: 'https://youtube.com/@hiddify/videos', icon: 'youtube' },
  { key: 'instagram', label: 'Instagram', href: 'https://www.instagram.com/hiddify_com', icon: 'instagram' },
])

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)

function onOutside(e: PointerEvent) {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    open.value = false
    trigger.value?.focus()
  }
}
watch(open, (isOpen) => {
  if (isOpen) {
    document.addEventListener('pointerdown', onOutside)
    document.addEventListener('keydown', onKey)
  } else {
    document.removeEventListener('pointerdown', onOutside)
    document.removeEventListener('keydown', onKey)
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutside)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div class="layout-footer">
    <div ref="root" class="hf">
      <Transition name="hf-pop">
        <div v-if="open" id="hiddify-links" class="hf-pop" role="menu" :aria-label="t('footer.links')">
          <span class="hf-pop__title">{{ t('footer.links') }}</span>
          <div class="hf-pop__row">
            <a
              v-for="(link, i) in LINKS"
              :key="link.key"
              :href="link.href"
              target="_blank"
              rel="noopener noreferrer"
              role="menuitem"
              class="hf-link"
              :class="`hf-link--${link.key}`"
              :style="{ '--i': i }"
              :aria-label="link.label"
              v-tooltip.top="link.label"
              @click="open = false"
            >
              <span class="hf-link__tile">
                <i v-if="link.icon === 'web'" class="pi pi-globe" aria-hidden="true" />
                <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path :d="BRAND_PATHS[link.icon]" /></svg>
              </span>
            </a>
          </div>
        </div>
      </Transition>
      <button
        ref="trigger"
        type="button"
        class="hf-brand"
        :class="{ 'hf-brand--open': open }"
        :aria-expanded="open"
        aria-controls="hiddify-links"
        aria-haspopup="menu"
        @click="open = !open"
      >
        <span class="hf-brand__name"
          ><b class="hf-shine" :data-text="name.first">{{ name.first }}</b
          ><span v-if="name.rest" class="hf-brand__rest hf-shine" :data-text="name.rest">{{ name.rest }}</span></span
        >
      </button>
    </div>
  </div>
</template>

<style scoped>
.hf {
  position: relative;
  display: flex;
  justify-content: center;
}

/* The logo: a small app-icon tile and the name */
.hf-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.4rem 0.9rem;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}
.hf-brand:hover,
.hf-brand--open {
  background: var(--p-content-background);
  border-color: var(--p-content-border-color);
  box-shadow: 0 6px 18px -12px color-mix(in srgb, var(--p-primary-700) 60%, transparent);
}
.hf-brand:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.hf-brand__name {
  display: inline-flex;
  align-items: baseline;
  font-size: 1.05rem;
  letter-spacing: -0.01em;
  /* the brand reads left to right in every language */
  direction: ltr;
}
.hf-brand__name b {
  font-weight: 800;
}
.hf-brand__rest {
  font-weight: 500;
  background: linear-gradient(90deg, var(--p-primary-500), var(--p-primary-700));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
/* The light: each part's text again on top of it (data-text), filled with a bright band that sweeps from left to right
   while the mouse is on the name; not while the window is open */
.hf-shine {
  --hf-light: rgb(255 255 255 / 0.95);
  position: relative;
}
/* on the white name of the dark theme, a light in the color */
html.app-dark .hf-shine {
  --hf-light: var(--p-primary-200);
}
.hf-shine::after {
  content: attr(data-text);
  position: absolute;
  inset: 0;
  color: transparent;
  background: linear-gradient(100deg, transparent 0 32%, var(--hf-light) 50%, transparent 68% 100%) no-repeat;
  background-size: 250% 100%;
  background-position: 160% 0;
  -webkit-background-clip: text;
  background-clip: text;
  pointer-events: none;
}
.hf-brand:not(.hf-brand--open):hover .hf-shine::after,
.hf-brand:not(.hf-brand--open):focus-visible .hf-shine::after {
  animation: hf-shine 2.4s ease-in-out infinite;
}
/* "Manager" right after "Hiddify": its light starts as the first one leaves, one sweep across the whole name */
.hf-brand:not(.hf-brand--open):hover .hf-brand__rest.hf-shine::after,
.hf-brand:not(.hf-brand--open):focus-visible .hf-brand__rest.hf-shine::after {
  animation-delay: 0.42s;
}
@keyframes hf-shine {
  0% {
    background-position: 160% 0;
  }
  60%,
  100% {
    background-position: -60% 0;
  }
}
html.app-dark .hf-brand__rest {
  background-image: linear-gradient(90deg, var(--p-primary-300), var(--p-primary-400));
}

/* The small window above the logo */
.hf-pop {
  position: absolute;
  bottom: calc(100% + 0.6rem);
  left: 50%;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.55rem;
  padding: 0.7rem 0.8rem 0.8rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 20px;
  background: var(--p-overlay-popover-background, var(--p-content-background));
  box-shadow:
    0 18px 40px -16px rgb(15 23 42 / 0.35),
    0 2px 6px rgb(15 23 42 / 0.06);
  -webkit-backdrop-filter: blur(20px) saturate(1.3);
  backdrop-filter: blur(20px) saturate(1.3);
  transform: translateX(-50%);
  transform-origin: 50% 100%;
}
/* its little arrow, pointing at the logo */
.hf-pop::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  width: 0.8rem;
  height: 0.8rem;
  margin-top: -0.4rem;
  border-right: 1px solid var(--p-content-border-color);
  border-bottom: 1px solid var(--p-content-border-color);
  background: inherit;
  transform: translateX(-50%) rotate(45deg);
  -webkit-backdrop-filter: none;
  backdrop-filter: none;
}
.hf-pop__title {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.hf-pop__row {
  display: flex;
  gap: 0.55rem;
  /* the order of the links is the same in RTL */
  direction: ltr;
}

/* Each channel: a round tile in its brand color, its mark in white */
/* The link is a still hit area; only the tile inside it lifts. (When the link itself moved, a mouse on its bottom edge
   fell off it, it dropped back under the mouse, and so on: the tile jumped up and down.) */
.hf-link {
  --brand: var(--p-primary-color);
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  color: #fff;
}
.hf-link__tile {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
  background: var(--brand);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.3),
    0 6px 14px -8px var(--brand);
  pointer-events: none;
  transition:
    transform 0.2s cubic-bezier(0.2, 0.9, 0.3, 1.4),
    box-shadow 0.2s ease;
  animation: hf-link-in 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.3) backwards; /* not "both": a held end state would block the hover's lift */
  animation-delay: calc(var(--i) * 35ms);
}
.hf-link svg {
  width: 1.3rem;
  height: 1.3rem;
  fill: currentColor;
}
.hf-link .pi {
  font-size: 1.15rem;
}
.hf-link:is(:hover, :focus-visible) .hf-link__tile {
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.3),
    0 10px 20px -8px var(--brand);
}
.hf-link :is(svg, .pi) {
  transform-origin: 50% 50%;
}
/* only the channel under the mouse moves; written out per channel (scoped keyframe names are not rewritten inside a
   custom property) */
.hf-link--web:is(:hover, :focus-visible) .pi {
  animation: hf-globe 1.6s ease-in-out infinite;
}
.hf-link--github:is(:hover, :focus-visible) svg {
  animation: hf-wave 1.3s ease-in-out infinite;
}
.hf-link--x:is(:hover, :focus-visible) svg {
  animation: hf-spin 1.4s cubic-bezier(0.6, 0, 0.3, 1) infinite;
}
.hf-link--telegram:is(:hover, :focus-visible) svg {
  animation: hf-fly 1.5s ease-in-out infinite;
}
.hf-link--youtube:is(:hover, :focus-visible) svg {
  animation: hf-beat 1.1s ease-in-out infinite;
}
.hf-link--instagram:is(:hover, :focus-visible) svg {
  animation: hf-flash 1.4s ease-in-out infinite;
}
/* the globe turns */
@keyframes hf-globe {
  0% {
    transform: perspective(60px) rotateY(0);
  }
  60%,
  100% {
    transform: perspective(60px) rotateY(360deg);
  }
}
/* the cat waves */
@keyframes hf-wave {
  0%,
  60%,
  100% {
    transform: rotate(0);
  }
  15% {
    transform: rotate(-14deg) scale(1.06);
  }
  30% {
    transform: rotate(10deg) scale(1.06);
  }
  45% {
    transform: rotate(-5deg);
  }
}
/* the X turns a quarter and settles */
@keyframes hf-spin {
  0% {
    transform: rotate(0) scale(1);
  }
  40% {
    transform: rotate(90deg) scale(1.12);
  }
  60%,
  100% {
    transform: rotate(90deg) scale(1);
  }
}
/* the plane flies off up and away, and glides back in */
@keyframes hf-fly {
  0%,
  60%,
  100% {
    transform: translate(0, 0);
    opacity: 1;
  }
  22% {
    transform: translate(120%, -120%) scale(0.8);
    opacity: 0;
  }
  23% {
    transform: translate(-120%, 120%) scale(0.8);
    opacity: 0;
  }
  45% {
    transform: translate(0, 0) scale(1.08);
    opacity: 1;
  }
}
/* the play button beats */
@keyframes hf-beat {
  0%,
  50%,
  100% {
    transform: scale(1);
  }
  15% {
    transform: scale(1.2);
  }
  30% {
    transform: scale(0.94);
  }
  40% {
    transform: scale(1.1);
  }
}
/* the camera flashes */
@keyframes hf-flash {
  0%,
  55%,
  100% {
    transform: scale(1);
    filter: drop-shadow(0 0 0 rgb(255 255 255 / 0));
  }
  18% {
    transform: scale(0.86);
  }
  30% {
    transform: scale(1.14);
    filter: drop-shadow(0 0 6px rgb(255 255 255 / 0.95));
  }
}
.hf-link:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 3px;
}
.hf-link--web {
  --brand: var(--p-primary-color);
}
.hf-link--web .hf-link__tile {
  background: linear-gradient(150deg, var(--p-primary-400), var(--p-primary-700));
}
.hf-link--github {
  --brand: #24292f;
}
.hf-link--x {
  --brand: #000000;
}
.hf-link--telegram {
  --brand: #26a5e4;
}
.hf-link--youtube {
  --brand: #ff0000;
}
.hf-link--instagram {
  --brand: #dd2a7b;
}
.hf-link--instagram .hf-link__tile {
  background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285aeb 90%);
}
/* dark: the black marks get a light edge, so they do not vanish in a dark window */
html.app-dark .hf-link--github .hf-link__tile,
html.app-dark .hf-link--x .hf-link__tile {
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / 0.22),
    0 6px 14px -8px rgb(0 0 0 / 0.8);
}

.hf-pop-enter-active,
.hf-pop-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.25s cubic-bezier(0.2, 0.9, 0.3, 1.2);
}
.hf-pop-enter-from,
.hf-pop-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(6px) scale(0.92);
}
@keyframes hf-link-in {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.8);
  }
}

/* Small phones: the six channels in two rows of three */
@media (max-width: 360px) {
  .hf-pop__row {
    display: grid;
    grid-template-columns: repeat(3, auto);
  }
}
@media (prefers-reduced-motion: reduce) {
  .hf-link__tile,
  .hf-pop-enter-active,
  .hf-pop-leave-active,
  .hf-shine::after,
  .hf-link :is(svg, .pi) {
    animation: none;
    transition: none;
  }
}
</style>
