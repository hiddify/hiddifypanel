<script setup lang="ts">
/**
 * The IP ranges (CIDRs) to pick random IPs from; the browser scan and the full test share one list. A one-line
 * summary until edited (opened by itself when a line is not a range).
 */
import { computed, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import { CLOUDFLARE_RANGES, parseRanges } from '../api'

defineProps<{ disabled?: boolean }>()
const text = defineModel<string>({ required: true })
const { t } = useI18n()
const id = useId()

/** Ranges shown as chips in the summary. */
const PREVIEW = 3
const editing = ref(false)
const showAll = ref(false)
const parsed = computed(() => parseRanges(text.value))
const isDefault = computed(() => parsed.value.ranges.join(' ') === CLOUDFLARE_RANGES.join(' '))
const open = computed(() => editing.value || !!parsed.value.invalid.length || !parsed.value.ranges.length)

function reset() {
  text.value = CLOUDFLARE_RANGES.join('\n')
}
</script>

<template>
  <div class="rf" :class="{ 'rf--open': open }">
    <div class="rf__summary">
      <span class="rf__icon"><i class="pi pi-globe" /></span>
      <div class="rf__text">
        <label :for="id" class="rf__title">{{ t('cleanIp.ranges') }}</label>
        <span class="rf__sub">
          {{ t('cleanIp.rangesCount', { count: parsed.ranges.length }) }} ·
          {{ isDefault ? t('cleanIp.rangesCloudflare') : t('cleanIp.rangesCustom') }}
        </span>
      </div>
      <Button
        v-if="!isDefault"
        v-tooltip.top="t('cleanIp.rangesReset')"
        icon="pi pi-undo"
        text
        rounded
        size="small"
        :aria-label="t('cleanIp.rangesReset')"
        :disabled="disabled"
        @click="reset"
      />
      <Button
        :label="open ? t('cleanIp.rangesDone') : t('cleanIp.rangesEdit')"
        :icon="open ? 'pi pi-check' : 'pi pi-pencil'"
        size="small"
        severity="secondary"
        text
        :disabled="disabled || (open && (!!parsed.invalid.length || !parsed.ranges.length))"
        @click="editing = !editing"
      />
    </div>

    <div v-if="!open" class="rf__chips" dir="ltr">
      <span v-for="r in showAll ? parsed.ranges : parsed.ranges.slice(0, PREVIEW)" :key="r" class="rf__chip">{{ r }}</span>
      <button v-if="parsed.ranges.length > PREVIEW" type="button" class="rf__more" :aria-expanded="showAll" @click="showAll = !showAll">
        {{ showAll ? t('cleanIp.showLess') : `+${parsed.ranges.length - PREVIEW}` }}
      </button>
    </div>

    <template v-else>
      <Textarea
        :id="id"
        v-model="text"
        rows="6"
        dir="ltr"
        spellcheck="false"
        :disabled="disabled"
        :invalid="!!parsed.invalid.length || !parsed.ranges.length"
        class="rf__input"
        fluid
      />
      <small v-if="parsed.invalid.length" class="rf__bad">{{ t('cleanIp.rangesInvalid', { list: parsed.invalid.slice(0, 5).join(', ') }) }}</small>
      <small v-else class="rf__hint">{{ t('cleanIp.rangesHint') }}</small>
    </template>
  </div>
</template>

<style scoped>
.rf {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-hover-background);
  transition: background-color 0.15s ease;
}
.rf--open {
  background: var(--p-content-background);
}
.rf__summary {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.rf__icon {
  inline-size: 2rem;
  block-size: 2rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 0.6rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.rf__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.rf__title {
  font-size: 0.88rem;
  font-weight: 600;
}
.rf__sub {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.rf__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.rf__chip {
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.72rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}
.rf__more {
  padding: 0.1rem 0.55rem;
  border: 1px dashed var(--p-primary-color);
  border-radius: 999px;
  background: transparent;
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}
.rf__more:hover {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.rf__input {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
}
.rf__hint {
  color: var(--p-text-muted-color);
}
.rf__bad {
  color: var(--p-red-500);
}
</style>
