<template>
  <section class="icon-colors">
    <div class="icon-colors__head">
      <span class="icon-colors__label">{{ t('pwa.iconColor') }}</span>
      <span class="icon-colors__code" dir="ltr">#{{ live }}</span>
    </div>

    <div class="icon-colors__grid" role="radiogroup" :aria-label="t('pwa.iconColor')">
      <button
        v-for="c in PRESETS"
        :key="c"
        type="button"
        role="radio"
        class="icon-colors__swatch"
        :class="{ 'icon-colors__swatch--on': c === live, 'icon-colors__swatch--light': isLight(c) }"
        :style="{ '--swatch': `#${c}` }"
        :aria-checked="c === live"
        :aria-label="`#${c}`"
        @click="pick(c)"
      >
        <i v-if="c === live" class="pi pi-check" />
      </button>
      <!-- Your own color: the last tile opens the picker; it takes that color once one is made -->
      <button
        type="button"
        class="icon-colors__swatch icon-colors__swatch--own"
        :class="{ 'icon-colors__swatch--on': own, 'icon-colors__swatch--made': own, 'icon-colors__swatch--light': own && isLight(live) }"
        :style="own ? { '--swatch': `#${live}` } : undefined"
        :aria-expanded="open"
        :aria-label="t('pwa.iconColorCustom')"
        @click="open = !open"
      >
        <i class="pi" :class="own ? 'pi-check' : 'pi-plus'" />
      </button>
    </div>

    <Transition name="icon-colors-own">
      <div v-if="open" class="icon-colors__own">
        <ColorPicker
          :model-value="live.toLowerCase()"
          inline
          format="hex"
          :dt="{ panel: { background: 'transparent', borderColor: 'transparent', shadow: 'none' } }"
          @update:model-value="(v: unknown) => fromPicker(String(v ?? ''))"
        />
        <div class="icon-colors__own-row">
          <label class="icon-colors__own-label" for="pwa-icon-hex">{{ t('pwa.iconColorCustom') }}</label>
          <InputGroup class="icon-colors__hex" dir="ltr">
            <InputGroupAddon>#</InputGroupAddon>
            <InputText
              id="pwa-icon-hex"
              v-model="typed"
              dir="ltr"
              maxlength="6"
              spellcheck="false"
              autocomplete="off"
              autocapitalize="characters"
              :invalid="typed.length > 0 && !HEX.test(typed)"
              @update:model-value="fromText"
              @blur="typed = live"
            />
          </InputGroup>
        </div>
      </div>
    </Transition>

    <small v-if="ios" class="icon-colors__hint">{{ t('pwa.iconColorHint') }}</small>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ColorPicker from 'primevue/colorpicker'
import InputGroup from 'primevue/inputgroup'
import InputGroupAddon from 'primevue/inputgroupaddon'
import InputText from 'primevue/inputtext'
import { useAppIcon } from '@/shared/composables/useAppIcon'
import { detectPwaPlatform } from '@/shared/composables/usePwaInstall'

/**
 * The color of the app icon (inside the "PWA Color" window): 25 ready colors (Apple's system colors, colors between
 * two of them, and dark tones), or one's own. The panel draws the icon in any color, so the choice shows at once
 * wherever the icon is on the page.
 */
const emit = defineEmits<{ /** its height changed (the own-color picker opened or closed) */ resize: [] }>()
// prettier-ignore
const PRESETS = [
  // blue (the stock icon), then around the color wheel
  '0A84FF', '00B0FC', '3CD3FE', '00C3D0', '00C8B3', '34C759', '80CD00', 'FFCC00', 'FF8D28',
  'FF6B2C', 'FF383C', 'FE007C', 'EF00AC', 'CB30E0', '9C39FF', '6155F5', '4A6AFF', '004896',
  // dark tones and neutrals: forest, plum, burgundy, brown, chocolate, graphite, black
  '007B3C', '720087', '9A0021', 'AC7F5E', '784016', '8E8E93', '15181E',
]
const HEX = /^[0-9A-F]{6}$/

const { t } = useI18n()
const { color, choose } = useAppIcon()
const ios = detectPwaPlatform() === 'ios'

/** What the controls show: the chosen color, or the one under the pointer while the picker is dragged. */
const live = ref(color.value)
const typed = ref(color.value)
const open = ref(false)
const own = computed(() => !PRESETS.includes(live.value))
watch(open, () => emit('resize'))

watch(color, (c) => {
  live.value = c
  if (document.activeElement?.id !== 'pwa-icon-hex') typed.value = c
})

/** A light color: its check mark is dark. */
function isLight(c: string): boolean {
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(c.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45
}

// The icon is drawn by the panel: while the picker is dragged, ask for it only when the pointer rests.
let timer = 0
function soon(c: string) {
  live.value = c
  window.clearTimeout(timer)
  timer = window.setTimeout(() => choose(c), 140)
}
function pick(c: string) {
  window.clearTimeout(timer)
  typed.value = c
  choose(c)
}
function fromPicker(value: string) {
  const c = value.toUpperCase()
  if (!HEX.test(c) || c === live.value) return
  typed.value = c
  soon(c)
}
function fromText(value: string | undefined) {
  const c = (value ?? '').replace(/[^0-9a-f]/gi, '').toUpperCase().slice(0, 6)
  typed.value = c
  if (HEX.test(c) && c !== live.value) soon(c)
}
onBeforeUnmount(() => window.clearTimeout(timer))
</script>

<style scoped>
.icon-colors {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  width: 100%;
  text-align: start;
}
.icon-colors__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.icon-colors__label {
  font-size: 0.86rem;
  font-weight: 600;
}
.icon-colors__code {
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
  color: var(--p-text-muted-color);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.74rem;
  letter-spacing: 0.02em;
}

/* 25 colors and "your own": three rows of nine */
.icon-colors__grid {
  display: grid;
  grid-template-columns: repeat(9, minmax(0, 1fr));
  gap: 0.55rem 0.3rem;
}
/* Each color as a small glass tile, in the shape of the icon */
.icon-colors__swatch {
  --swatch: var(--p-primary-color);
  position: relative;
  display: grid;
  place-items: center;
  justify-self: center;
  width: 100%;
  max-width: 2.15rem;
  aspect-ratio: 1;
  padding: 0;
  border: 0;
  border-radius: 31%;
  background:
    radial-gradient(120% 80% at 28% 0%, rgb(255 255 255 / 52%) 0%, rgb(255 255 255 / 0%) 55%),
    linear-gradient(180deg, color-mix(in srgb, var(--swatch) 86%, white) 0%, var(--swatch) 46%, color-mix(in srgb, var(--swatch) 80%, black) 100%);
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / 26%),
    inset 0 -5px 8px -5px rgb(0 0 0 / 32%),
    0 5px 9px -6px color-mix(in srgb, var(--swatch) 65%, black);
  color: #fff;
  font-size: 0.7rem;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease;
}
.icon-colors__swatch .pi {
  filter: drop-shadow(0 1px 1px rgb(0 0 0 / 45%));
}
.icon-colors__swatch--light {
  color: rgb(0 0 0 / 72%);
}
.icon-colors__swatch--light .pi {
  filter: none;
}
.icon-colors__swatch:hover {
  transform: translateY(-2px) scale(1.06);
}
.icon-colors__swatch:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 3px;
}
/* The chosen one: a ring in its own color (mixed with the text color, so black shows on a dark page too) */
.icon-colors__swatch--on {
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / 40%),
    0 0 0 2px var(--p-content-background),
    0 0 0 4px color-mix(in srgb, var(--swatch) 72%, var(--p-text-color));
}
/* "Your own": every color at once, until one is made */
.icon-colors__swatch--own:not(.icon-colors__swatch--made) {
  background:
    radial-gradient(120% 80% at 28% 0%, rgb(255 255 255 / 45%) 0%, rgb(255 255 255 / 0%) 55%),
    conic-gradient(from 200deg, #ff383c, #ff8d28, #ffcc00, #34c759, #00c8b3, #0a84ff, #6155f5, #cb30e0, #fe007c, #ff383c);
  box-shadow:
    inset 0 0 0 1px rgb(255 255 255 / 30%),
    0 5px 9px -6px rgb(0 0 0 / 55%);
}

/* The picker for one's own color: the color field and the hue bar, then the color's code */
.icon-colors__own {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding-top: 0.5rem;
  border-top: 1px solid color-mix(in srgb, var(--p-content-border-color) 75%, transparent);
  overflow: hidden;
}
/* PrimeVue's picker, without its dark box and with soft corners */
.icon-colors__own :deep(.p-colorpicker-panel) {
  box-shadow: none;
}
.icon-colors__own :deep(.p-colorpicker-color-selector),
.icon-colors__own :deep(.p-colorpicker-color-background) {
  border-radius: 12px;
}
.icon-colors__own :deep(.p-colorpicker-hue) {
  border-radius: 9px;
}
.icon-colors__own-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: min(100%, 17rem);
}
.icon-colors__own-label {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.icon-colors__hex {
  flex: none;
  width: 9.25rem;
}
.icon-colors__hex :deep(.p-inputtext) {
  min-width: 0;
  padding-inline: 0.6rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.92rem;
  text-transform: uppercase;
}
.icon-colors-own-enter-active,
.icon-colors-own-leave-active {
  transition:
    max-height 0.25s ease,
    opacity 0.2s ease,
    padding-top 0.25s ease;
  max-height: 17rem;
}
.icon-colors-own-enter-from,
.icon-colors-own-leave-to {
  max-height: 0;
  padding-top: 0;
  opacity: 0;
}

.icon-colors__hint {
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--p-text-muted-color);
}

@media (prefers-reduced-motion: reduce) {
  .icon-colors__swatch,
  .icon-colors-own-enter-active,
  .icon-colors-own-leave-active {
    transition: none;
  }
  .icon-colors__swatch:hover {
    transform: none;
  }
}
</style>
