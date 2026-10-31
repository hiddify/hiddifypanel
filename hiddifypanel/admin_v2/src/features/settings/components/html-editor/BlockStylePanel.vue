<script setup lang="ts">
/**
 * Full mode's "Block style": the look of the block the caret is in (or of an element picked in the path bar), as
 * inline styles: background (colour or gradient), text colour, spacing, corners, border, shadow, width, line height.
 */
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Slider from 'primevue/slider'

const props = defineProps<{ target: HTMLElement | null }>()
const emit = defineEmits<{ change: []; parent: [] }>()

const { t } = useI18n()

type Background = 'none' | 'color' | 'gradient'
const SHADOWS: Record<string, string> = {
  none: '',
  soft: '0 4px 14px -6px rgba(15, 23, 42, 0.25)',
  strong: '0 12px 32px -10px rgba(15, 23, 42, 0.45)',
  glow: '0 0 0 4px rgba(69, 95, 233, 0.18)',
}
const LINE_HEIGHTS = ['', '1', '1.25', '1.5', '1.75', '2']

const s = reactive({
  background: 'none' as Background,
  color1: '#4f46e5',
  color2: '#06b6d4',
  angle: 135,
  textColor: '',
  padding: 0,
  margin: 0,
  radius: 0,
  borderWidth: 0,
  borderColor: '#dee2e6',
  borderStyle: 'solid',
  shadow: 'none',
  fullWidth: false,
  lineHeight: '',
})

function px(value: string): number {
  const n = parseFloat(value)
  return Number.isFinite(n) ? Math.round(n) : 0
}
/** "rgb(1, 2, 3)" → "#010203" for the colour inputs */
function hex(color: string, fallback: string): string {
  const m = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (m) return `#${[m[1], m[2], m[3]].map((v) => Number(v).toString(16).padStart(2, '0')).join('')}`
  return /^#[0-9a-f]{6}$/i.test(color) ? color : fallback
}

function read(el: HTMLElement) {
  const st = el.style
  const image = st.backgroundImage || (st.background.includes('gradient') ? st.background : '')
  const grad = image.match(/linear-gradient\(\s*(\d+)deg\s*,\s*(#[0-9a-f]{3,8}|rgba?\([^)]*\))\s*,\s*(#[0-9a-f]{3,8}|rgba?\([^)]*\))/i)
  if (grad) {
    s.background = 'gradient'
    s.angle = Number(grad[1])
    s.color1 = hex(grad[2], s.color1)
    s.color2 = hex(grad[3], s.color2)
  } else if (st.backgroundColor) {
    s.background = 'color'
    s.color1 = hex(st.backgroundColor, s.color1)
  } else s.background = 'none'
  s.textColor = st.color ? hex(st.color, '#212529') : ''
  s.padding = px(st.paddingTop || st.padding)
  s.margin = px(st.marginBottom)
  s.radius = px(st.borderTopLeftRadius || st.borderRadius)
  s.borderWidth = px(st.borderTopWidth || st.borderWidth)
  s.borderColor = hex(st.borderTopColor || st.borderColor, '#dee2e6')
  s.borderStyle = st.borderTopStyle || st.borderStyle || 'solid'
  s.shadow = Object.entries(SHADOWS).find(([, v]) => v && st.boxShadow.replace(/\s+/g, '') === v.replace(/\s+/g, ''))?.[0] ?? (st.boxShadow ? 'custom' : 'none')
  s.fullWidth = st.width === '100%'
  s.lineHeight = st.lineHeight
}

watch(
  () => props.target,
  (el) => el && read(el),
  { immediate: true },
)

function write() {
  const el = props.target
  if (!el) return
  const st = el.style
  st.removeProperty('background')
  st.removeProperty('background-image')
  st.removeProperty('background-color')
  if (s.background === 'color') st.backgroundColor = s.color1
  if (s.background === 'gradient') st.background = `linear-gradient(${s.angle}deg, ${s.color1}, ${s.color2})`
  if (s.textColor) st.color = s.textColor
  else st.removeProperty('color')
  if (s.padding) st.padding = `${s.padding}px`
  else st.removeProperty('padding')
  st.marginBottom = s.margin ? `${s.margin}px` : ''
  if (s.radius) st.borderRadius = `${s.radius}px`
  else st.removeProperty('border-radius')
  if (s.borderWidth) st.border = `${s.borderWidth}px ${s.borderStyle} ${s.borderColor}`
  else st.removeProperty('border')
  if (s.shadow !== 'custom') {
    if (SHADOWS[s.shadow]) st.boxShadow = SHADOWS[s.shadow]
    else st.removeProperty('box-shadow')
  }
  st.width = s.fullWidth ? '100%' : ''
  if (s.fullWidth && el.ownerDocument.defaultView?.getComputedStyle(el).display === 'inline') st.display = 'inline-block'
  st.lineHeight = s.lineHeight
  if (!el.getAttribute('style')?.trim()) el.removeAttribute('style')
  emit('change')
}

function reset() {
  props.target?.removeAttribute('style')
  props.target?.removeAttribute('align')
  if (props.target) read(props.target)
  emit('change')
}
</script>

<template>
  <div class="bsp">
    <div v-if="!target" class="bsp__empty"><i class="pi pi-info-circle" />{{ t('settings.htmlEditor.style.noTarget') }}</div>
    <template v-else>
      <div class="bsp__head">
        <code class="bsp__tag" dir="ltr">&lt;{{ target.tagName.toLowerCase() }}&gt;</code>
        <button type="button" class="bsp__link" @mousedown.prevent @click="emit('parent')"><i class="pi pi-arrow-up" />{{ t('settings.htmlEditor.style.parent') }}</button>
      </div>

      <div class="bsp__field">
        <span class="bsp__label">{{ t('settings.htmlEditor.style.background') }}</span>
        <div class="bsp__seg">
          <button v-for="b in ['none', 'color', 'gradient'] as const" :key="b" type="button" :class="{ on: s.background === b }" @mousedown.prevent @click="(s.background = b), write()">
            {{ t(`settings.htmlEditor.style.${b}`) }}
          </button>
        </div>
      </div>
      <div v-if="s.background !== 'none'" class="bsp__row">
        <input v-model="s.color1" type="color" class="bsp__color" :aria-label="t('settings.htmlEditor.style.color')" @input="write" />
        <template v-if="s.background === 'gradient'">
          <input v-model="s.color2" type="color" class="bsp__color" :aria-label="t('settings.htmlEditor.style.color')" @input="write" />
          <span class="bsp__preview" :style="{ background: `linear-gradient(${s.angle}deg, ${s.color1}, ${s.color2})` }" />
        </template>
      </div>
      <div v-if="s.background === 'gradient'" class="bsp__field">
        <span class="bsp__label">{{ t('settings.htmlEditor.style.angle') }} <b dir="ltr">{{ s.angle }}°</b></span>
        <Slider v-model="s.angle" :min="0" :max="360" :step="15" @update:model-value="write" />
      </div>

      <div class="bsp__row bsp__row--between">
        <span class="bsp__label">{{ t('settings.htmlEditor.style.textColor') }}</span>
        <span class="bsp__row">
          <input :value="s.textColor || '#212529'" type="color" class="bsp__color" :aria-label="t('settings.htmlEditor.style.textColor')" @input="(s.textColor = ($event.target as HTMLInputElement).value), write()" />
          <button v-if="s.textColor" type="button" class="bsp__link" @mousedown.prevent @click="(s.textColor = ''), write()">{{ t('settings.htmlEditor.style.none') }}</button>
        </span>
      </div>

      <div v-for="f in (['padding', 'margin', 'radius'] as const)" :key="f" class="bsp__field">
        <span class="bsp__label">{{ t(`settings.htmlEditor.style.${f}`) }} <b dir="ltr">{{ s[f] }}px</b></span>
        <Slider v-model="s[f]" :min="0" :max="f === 'radius' ? 32 : 40" @update:model-value="write" />
      </div>

      <div class="bsp__field">
        <span class="bsp__label">{{ t('settings.htmlEditor.style.border') }} <b dir="ltr">{{ s.borderWidth }}px</b></span>
        <div class="bsp__row">
          <Slider v-model="s.borderWidth" :min="0" :max="6" class="flex-1" @update:model-value="write" />
          <input v-model="s.borderColor" type="color" class="bsp__color" :aria-label="t('settings.htmlEditor.style.border')" @input="write" />
          <select v-model="s.borderStyle" class="bsp__select" @change="write">
            <option v-for="b in ['solid', 'dashed', 'dotted']" :key="b" :value="b">{{ t(`settings.htmlEditor.style.${b}`) }}</option>
          </select>
        </div>
      </div>

      <div class="bsp__field">
        <span class="bsp__label">{{ t('settings.htmlEditor.style.shadow') }}</span>
        <div class="bsp__seg">
          <button v-for="sh in ['none', 'soft', 'strong', 'glow'] as const" :key="sh" type="button" :class="{ on: s.shadow === sh }" @mousedown.prevent @click="(s.shadow = sh), write()">
            {{ t(`settings.htmlEditor.style.shadow_${sh}`) }}
          </button>
        </div>
      </div>

      <div class="bsp__row bsp__row--between">
        <label class="bsp__check"><input v-model="s.fullWidth" type="checkbox" @change="write" />{{ t('settings.htmlEditor.style.fullWidth') }}</label>
        <label class="bsp__row">
          <span class="bsp__label">{{ t('settings.htmlEditor.tools.lineHeight') }}</span>
          <select v-model="s.lineHeight" class="bsp__select" @change="write">
            <option v-for="h in LINE_HEIGHTS" :key="h" :value="h">{{ h || '—' }}</option>
          </select>
        </label>
      </div>

      <Button :label="t('settings.htmlEditor.style.reset')" icon="pi pi-replay" severity="secondary" text size="small" class="self-start" @click="reset" />
    </template>
  </div>
</template>

<style scoped>
.bsp {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 17rem;
  font-size: 0.8rem;
}
.bsp__empty {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  color: var(--p-text-muted-color);
}
.bsp__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.bsp__tag {
  padding: 0.1rem 0.45rem;
  border-radius: 6px;
  font-size: 0.75rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.bsp__link {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0;
  border: 0;
  font: inherit;
  font-size: 0.75rem;
  color: var(--p-primary-color);
  background: none;
  cursor: pointer;
}
.bsp__link i {
  font-size: 0.65rem;
}
.bsp__field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.bsp__label {
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.bsp__label b {
  color: var(--p-text-color);
  font-weight: 600;
}
.bsp__row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.bsp__row--between {
  justify-content: space-between;
}
.bsp__seg {
  display: flex;
  padding: 2px;
  gap: 2px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
}
.bsp__seg button {
  flex: 1;
  padding: 0.3rem 0.4rem;
  border: 0;
  border-radius: 6px;
  font: inherit;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  background: transparent;
  cursor: pointer;
}
.bsp__seg button.on {
  color: var(--p-primary-color);
  background: var(--p-content-background);
  box-shadow: 0 1px 2px rgb(15 23 42 / 12%);
}
.bsp__color {
  width: 2rem;
  height: 1.75rem;
  padding: 0;
  border: 1px solid var(--p-content-border-color);
  border-radius: 6px;
  background: none;
  cursor: pointer;
}
.bsp__preview {
  flex: 1;
  height: 1.75rem;
  border-radius: 6px;
}
.bsp__select {
  padding: 0.2rem 0.3rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 6px;
  font: inherit;
  color: var(--p-text-color);
  background: var(--p-content-background);
}
.bsp__check {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
}
</style>
