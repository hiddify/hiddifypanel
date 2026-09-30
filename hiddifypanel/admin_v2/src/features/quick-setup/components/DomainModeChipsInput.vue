<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import { quickSetupApi, type DomainMode, type ModeChip } from '@/features/quick-setup/api'

const props = defineProps<{
  inputId: string
  placeholder?: string
  /** domain -> error message (from the server). */
  errors?: Record<string, string>
  invalid?: boolean
  disabled?: boolean
}>()

const model = defineModel<ModeChip[]>({ required: true })

const { t } = useI18n()
const draft = ref('')
const input = ref<HTMLInputElement | null>(null)
const menu = ref<InstanceType<typeof Menu> | null>(null)
const menuFor = ref<string | null>(null)

const MODE_META: Record<DomainMode, { icon: string }> = {
  direct: { icon: 'pi pi-bolt' },
  cdn: { icon: 'pi pi-cloud' },
  reality: { icon: 'pi pi-eye-slash' },
  relay: { icon: 'pi pi-share-alt' },
}
const MODES = Object.keys(MODE_META) as DomainMode[]

const errorList = computed(() => Object.entries(props.errors ?? {}).filter(([domain]) => model.value.some((c) => c.domain === domain)))

const menuItems = computed<MenuItem[]>(() =>
  MODES.map((mode) => ({
    label: t(`quickSetup.domains.modes.${mode}`),
    icon: MODE_META[mode].icon,
    class: `mode-item mode-item--${mode}${model.value.find((c) => c.domain === menuFor.value)?.mode === mode ? ' mode-item--active' : ''}`,
    command: () => setMode(menuFor.value, mode),
  })),
)

function normalize(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/^[a-z]+:\/\//, '')
    .replace(/[/?#].*$/, '')
    .replace(/^\[|\]$/g, '')
}

function patch(domain: string, change: Partial<ModeChip>) {
  model.value = model.value.map((c) => (c.domain === domain ? { ...c, ...change } : c))
}

async function detect(domain: string) {
  try {
    const found = await quickSetupApi.detect(domain)
    const chip = model.value.find((c) => c.domain === domain)
    if (!chip) return
    const change: Partial<ModeChip> = { detecting: false, cdn: found.cdn }
    if (found.mode === 'unresolved') change.note = 'unresolved'
    else if (found.mode === 'reality' && found.reality_friendly === false) change.note = 'not_friendly'
    // The admin's own choice wins over a late answer.
    if (!chip.touched && found.mode !== 'unresolved') change.mode = found.mode
    patch(domain, change)
  } catch {
    patch(domain, { detecting: false })
  }
}

function add(raw: string) {
  const names = raw.split(/[\s,;]+/).map(normalize).filter(Boolean)
  const added: string[] = []
  const next = [...model.value]
  for (const name of names) {
    if (next.some((c) => c.domain === name)) continue
    next.push({ domain: name, mode: 'direct', detecting: true })
    added.push(name)
  }
  if (added.length) model.value = next
  draft.value = ''
  added.forEach(detect)
}

function remove(name: string) {
  model.value = model.value.filter((c) => c.domain !== name)
  input.value?.focus()
}

function setMode(domain: string | null, mode: DomainMode) {
  if (domain) patch(domain, { mode, touched: true })
}

function openMenu(event: Event, domain: string) {
  menuFor.value = domain
  menu.value?.toggle(event)
}

function onKeydown(event: KeyboardEvent) {
  if (['Enter', ',', ' ', 'Tab'].includes(event.key) && draft.value.trim()) {
    event.preventDefault()
    add(draft.value)
  } else if (event.key === 'Backspace' && !draft.value && model.value.length) {
    remove(model.value[model.value.length - 1]!.domain)
  }
}

function onPaste(event: ClipboardEvent) {
  const text = event.clipboardData?.getData('text') ?? ''
  if (/[\s,;]/.test(text.trim())) {
    event.preventDefault()
    add(text)
  }
}

defineExpose({ add })
</script>

<template>
  <div>
    <div
      class="mchips"
      :class="{ 'mchips--invalid': invalid || errorList.length, 'mchips--disabled': disabled }"
      dir="ltr"
      @click="input?.focus()"
    >
      <TransitionGroup name="mchip">
        <span
          v-for="chip in model"
          :key="chip.domain"
          class="mchip"
          :class="[`mchip--${chip.mode}`, { 'mchip--error': errors?.[chip.domain] }]"
          :title="errors?.[chip.domain] || chip.domain"
        >
          <button
            type="button"
            class="mchip__mode"
            :disabled="disabled"
            :aria-label="t('quickSetup.domains.changeMode', { name: chip.domain })"
            v-tooltip.top="t('quickSetup.domains.changeMode', { name: chip.domain })"
            @click.stop="openMenu($event, chip.domain)"
          >
            <i :class="chip.detecting ? 'pi pi-spin pi-spinner' : MODE_META[chip.mode].icon" />
            <span>{{ chip.detecting ? t('quickSetup.domains.detecting') : t(`quickSetup.domains.modes.${chip.mode}`) }}</span>
            <i class="pi pi-chevron-down mchip__caret" />
          </button>
          <span class="mchip__name">
            <i v-if="errors?.[chip.domain]" class="pi pi-exclamation-circle" />
            {{ chip.domain }}
          </span>
          <span v-if="chip.cdn && chip.mode === 'cdn'" class="mchip__tag">{{ chip.cdn }}</span>
          <i
            v-if="chip.note && !errors?.[chip.domain]"
            class="pi pi-exclamation-triangle mchip__note"
            v-tooltip.top="t(`quickSetup.domains.notes.${chip.note}`)"
          />
          <button type="button" class="mchip__remove" :aria-label="t('quickSetup.domains.remove', { name: chip.domain })" :disabled="disabled" @click.stop="remove(chip.domain)">
            <i class="pi pi-times" />
          </button>
        </span>
      </TransitionGroup>
      <input
        :id="inputId"
        ref="input"
        v-model="draft"
        class="mchips__input"
        :placeholder="model.length ? '' : placeholder"
        :disabled="disabled"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        inputmode="url"
        @keydown="onKeydown"
        @paste="onPaste"
        @blur="draft.trim() && add(draft)"
      />
    </div>
    <Menu ref="menu" :model="menuItems" popup />
    <TransitionGroup name="mchip-error" tag="ul" class="mchips__errors">
      <li v-for="[domain, message] in errorList" :key="domain">
        <strong dir="ltr">{{ domain }}</strong>: {{ message }}
      </li>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.mchips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  min-height: 3rem;
  padding: 0.45rem 0.5rem;
  border-radius: var(--p-inputtext-border-radius, 8px);
  border: 1px solid var(--p-inputtext-border-color, var(--p-content-border-color));
  background: var(--p-inputtext-background, var(--p-content-background));
  cursor: text;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.mchips:focus-within {
  border-color: var(--p-primary-color);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--p-primary-color) 20%, transparent);
}
.mchips--invalid {
  border-color: var(--p-red-500, #ef4444);
}
.mchips--disabled {
  opacity: 0.6;
  pointer-events: none;
}
.mchip {
  --tone: var(--p-green-500, #22c55e);
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  max-width: 100%;
  padding: 0.15rem 0.25rem 0.15rem 0.15rem;
  border-radius: 999px;
  font-size: 0.85rem;
  border: 1px solid color-mix(in srgb, var(--tone) 35%, transparent);
  background: color-mix(in srgb, var(--tone) 9%, transparent);
  overflow-wrap: anywhere;
}
.mchip--cdn {
  --tone: var(--p-sky-500, #0ea5e9);
}
.mchip--reality {
  --tone: var(--p-violet-500, #8b5cf6);
}
.mchip--relay {
  --tone: var(--p-orange-500, #f97316);
}
.mchip--error {
  --tone: var(--p-red-500, #ef4444);
}
.mchip__mode {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border: 0;
  border-radius: 999px;
  font: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: #fff;
  background: var(--tone);
  cursor: pointer;
  white-space: nowrap;
  transition: filter 0.15s ease;
}
.mchip__mode:hover {
  filter: brightness(1.1);
}
.mchip__mode i {
  font-size: 0.72rem;
}
.mchip__caret {
  font-size: 0.55rem !important;
  opacity: 0.85;
}
.mchip__name {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--p-text-color);
}
.mchip--error .mchip__name {
  color: var(--p-red-600, #dc2626);
}
.mchip__tag {
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  font-size: 0.7rem;
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 16%, transparent);
}
.mchip__note {
  font-size: 0.8rem;
  color: var(--p-amber-500, #f59e0b);
}
.mchip__remove {
  display: grid;
  place-items: center;
  width: 1.35rem;
  height: 1.35rem;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.mchip__remove:hover {
  background: color-mix(in srgb, currentColor 16%, transparent);
}
.mchip__remove i {
  font-size: 0.65rem;
}
.mchips__input {
  flex: 1 1 8rem;
  min-width: 6rem;
  border: 0;
  outline: none;
  background: transparent;
  color: inherit;
  font: inherit;
  padding: 0.25rem;
}
.mchips__errors {
  margin: 0.4rem 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.82rem;
  color: var(--p-red-500, #ef4444);
}
.mchips__errors li + li {
  margin-top: 0.2rem;
}
.mchip-enter-active,
.mchip-leave-active,
.mchip-error-enter-active,
.mchip-error-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.mchip-enter-from,
.mchip-leave-to {
  opacity: 0;
  transform: scale(0.85);
}
.mchip-error-enter-from,
.mchip-error-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}
:global(.mode-item--active .p-menu-item-content) {
  background: var(--p-highlight-background, color-mix(in srgb, var(--p-primary-color) 12%, transparent));
}
:global(.mode-item--direct .p-menu-item-icon) {
  color: var(--p-green-500, #22c55e);
}
:global(.mode-item--cdn .p-menu-item-icon) {
  color: var(--p-sky-500, #0ea5e9);
}
:global(.mode-item--reality .p-menu-item-icon) {
  color: var(--p-violet-500, #8b5cf6);
}
:global(.mode-item--relay .p-menu-item-icon) {
  color: var(--p-orange-500, #f97316);
}
</style>
