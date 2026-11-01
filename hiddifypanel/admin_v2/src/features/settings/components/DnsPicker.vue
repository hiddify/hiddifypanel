<script setup lang="ts">
/**
 * The "DNS server" setting: a dropdown of well-known DNS servers in three groups (normal, ad blocking, ad blocking +
 * adult filter), each with its two addresses, and "Custom" for one's own. The value is the IPs separated by commas.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { DNS_GROUPS, dnsList, presetOf } from '@/features/settings/dns-presets'

const props = defineProps<{ inputId: string; invalid?: boolean }>()
const model = defineModel<string>({ required: true })
const { t } = useI18n()

const CUSTOM = '__custom__'
interface Option {
  id: string
  name: string
  ips: string[]
  color: string
}
const groups = computed(() => [
  ...DNS_GROUPS.map((g) => ({
    id: g.id,
    label: t(`settings.dns.group.${g.id}`),
    icon: g.icon,
    color: g.color,
    items: g.presets.map<Option>((p) => ({ id: p.id, name: p.name, ips: [...p.ips], color: g.color })),
  })),
  {
    id: 'custom',
    label: t('settings.dns.group.custom'),
    icon: 'pi pi-pencil',
    color: '#8b5cf6',
    items: [{ id: CUSTOM, name: t('settings.dns.custom'), ips: [], color: '#8b5cf6' }] as Option[],
  },
])
const allOptions = computed(() => groups.value.flatMap((g) => g.items))

/** Custom while the value is not one of the presets, or after "Custom" was picked */
const customPicked = ref(false)
const selectedId = computed({
  get: () => (customPicked.value ? CUSTOM : (presetOf(model.value)?.id ?? (model.value.trim() ? CUSTOM : null))),
  set: (id: string | null) => {
    if (id === CUSTOM) {
      customPicked.value = true
      return
    }
    customPicked.value = false
    const option = allOptions.value.find((o) => o.id === id)
    if (option) model.value = option.ips.join(',')
  },
})
const selected = computed(() => allOptions.value.find((o) => o.id === selectedId.value) ?? null)
const isCustom = computed(() => selectedId.value === CUSTOM)
// A value typed by hand that happens to be a preset's turns the dropdown to it
watch(model, (v) => {
  if (customPicked.value && presetOf(v) && !document.activeElement?.matches?.('.dns-picker__custom input')) customPicked.value = false
})
const groupOf = (id: string) => groups.value.find((g) => g.items.some((o) => o.id === id))
</script>

<template>
  <div class="dns-picker">
    <Select
      v-model="selectedId"
      :input-id="props.inputId"
      :options="groups"
      option-group-label="label"
      option-group-children="items"
      option-label="name"
      option-value="id"
      :invalid="invalid"
      :placeholder="t('settings.dns.placeholder')"
      class="w-full"
      panel-class="dns-picker__panel"
      scroll-height="22rem"
    >
      <template #value>
        <span v-if="selected && !isCustom" class="dns-picker__value" :title="groupOf(selected.id)?.label">
          <span class="dns-picker__dot" :style="{ background: selected.color }" />
          <b>{{ selected.name }}</b>
          <code dir="ltr">{{ dnsList(model).join(' · ') }}</code>
        </span>
        <span v-else-if="isCustom" class="dns-picker__value">
          <span class="dns-picker__dot" style="background: #8b5cf6" />
          <b>{{ t('settings.dns.custom') }}</b>
          <code v-if="dnsList(model).length" dir="ltr">{{ dnsList(model).join(' · ') }}</code>
        </span>
        <span v-else class="dns-picker__placeholder">{{ t('settings.dns.placeholder') }}</span>
      </template>
      <template #optiongroup="{ option }">
        <div class="dns-picker__group" :style="{ '--g': option.color }">
          <span class="dns-picker__group-icon"><i :class="option.icon" /></span>
          {{ option.label }}
        </div>
      </template>
      <template #option="{ option }">
        <div class="dns-picker__option" :style="{ '--g': option.color }">
          <span class="dns-picker__name">{{ option.name }}</span>
          <span v-if="option.ips.length" class="dns-picker__ips" dir="ltr">
            <code v-for="ip in option.ips" :key="ip">{{ ip }}</code>
          </span>
          <span v-else class="dns-picker__hint">{{ t('settings.dns.customHint') }}</span>
        </div>
      </template>
    </Select>
    <Transition name="dns-fade">
      <div v-if="isCustom" class="dns-picker__custom">
        <InputText
          v-model="model"
          class="w-full"
          dir="ltr"
          :invalid="invalid"
          :placeholder="t('settings.dns.customPlaceholder')"
          spellcheck="false"
          autocomplete="off"
        />
        <small>{{ t('settings.dns.customHelp') }}</small>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dns-picker {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.dns-picker__value {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
}
.dns-picker__value b {
  font-weight: 600;
}
.dns-picker__value b {
  flex: none;
}
.dns-picker__value code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.dns-picker__dot {
  flex: none;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
}
.dns-picker__placeholder {
  color: var(--p-text-muted-color);
}
.dns-picker__custom {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.dns-picker__custom small {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.dns-fade-enter-active,
.dns-fade-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.dns-fade-enter-from,
.dns-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

<style>
/* The dropdown (in <body>): each group under a coloured header, each server with its two addresses as chips */
.dns-picker__panel .p-select-option-group {
  padding: 0.55rem 0.75rem 0.3rem;
  background: transparent;
}
.dns-picker__group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--g);
}
.dns-picker__group-icon {
  display: inline-grid;
  place-items: center;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 7px;
  font-size: 0.72rem;
  background: color-mix(in srgb, var(--g) 14%, transparent);
}
.dns-picker__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
  padding-inline-start: 1.9rem;
}
.dns-picker__name {
  font-weight: 600;
}
.dns-picker__ips {
  display: inline-flex;
  gap: 0.3rem;
}
.dns-picker__ips code {
  padding: 0.05rem 0.4rem;
  border-radius: 6px;
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
  background: color-mix(in srgb, var(--g) 9%, var(--p-content-hover-background, rgba(127, 127, 127, 0.08)));
}
.dns-picker__hint {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
</style>
