<script setup lang="ts">
/** TLS mode cards: Valid TLS, Fake, Reality. `locked`: the mode always uses a real certificate (CDN, worker, subscription). */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { TLS_MODES, type TlsMode } from '@/features/domains/api'

const props = defineProps<{ locked?: boolean; fit?: Partial<Record<TlsMode, 'good' | 'bad'>> }>()
const model = defineModel<TlsMode>({ required: true })
const { t } = useI18n()

const ICON: Record<TlsMode, string> = { valid: '🔒', fake: '🎭', reality: '🔂', dns: '🧭' }
const COLOR: Record<TlsMode, string> = {
  valid: 'var(--p-green-500, #22c55e)',
  fake: 'var(--p-pink-500, #ec4899)',
  reality: 'var(--p-violet-500, #8b5cf6)',
  dns: 'var(--p-sky-500, #0ea5e9)',
}
const modes = computed<TlsMode[]>(() => (model.value === 'dns' ? [...TLS_MODES, 'dns'] : TLS_MODES))
const shown = computed<TlsMode>(() => (props.locked ? 'valid' : model.value))

function pick(m: TlsMode) {
  if (!props.locked) model.value = m
}
</script>

<template>
  <div class="tls" :class="{ 'tls--locked': locked }">
    <div class="tls__cards" role="radiogroup" :aria-label="t('domains.field.tlsMode')">
      <button
        v-for="m in modes"
        :key="m"
        type="button"
        role="radio"
        class="tls__card"
        :class="{ 'tls__card--on': shown === m, 'tls__card--bad': !locked && fit?.[m] === 'bad' }"
        :style="{ '--tls-color': COLOR[m] }"
        :aria-checked="shown === m"
        :disabled="locked && m !== 'valid'"
        @click="pick(m)"
      >
        <span class="tls__icon" aria-hidden="true">{{ ICON[m] }}</span>
        <span class="tls__name">
          {{ t(`domains.tlsMode.${m}`) }}
          <i v-if="!locked && fit?.[m] === 'good'" class="pi pi-sparkles tls__good" v-tooltip.top="t('domains.wizard.recommended')" />
        </span>
        <span class="tls__desc">{{ t(`domains.tlsMode.${m}Hint`) }}</span>
        <i v-if="shown === m" class="pi pi-check-circle tls__check" />
      </button>
    </div>
    <p v-if="locked" class="tls__lock"><i class="pi pi-lock" />{{ t('domains.tlsMode.locked') }}</p>
  </div>
</template>

<style scoped>
.tls {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.tls__cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}
.tls__card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.2rem;
  min-width: 0;
  padding: 0.7rem 0.8rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  text-align: start;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease,
    opacity 0.15s ease;
}
.tls__card:not(:disabled):hover {
  border-color: color-mix(in srgb, var(--tls-color) 55%, var(--p-content-border-color));
  transform: translateY(-1px);
}
.tls__card:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.tls__card--on {
  border-color: var(--tls-color);
  box-shadow: 0 0 0 1px var(--tls-color);
  background: linear-gradient(135deg, color-mix(in srgb, var(--tls-color) 11%, transparent), transparent 75%), var(--p-content-background);
}
.tls__card--bad:not(.tls__card--on) {
  opacity: 0.65;
}
.tls__card:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}
.tls__icon {
  font-size: 1.2rem;
  line-height: 1.5rem;
}
.tls__name {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 650;
  font-size: 0.9rem;
}
.tls__good {
  font-size: 0.75rem;
  color: var(--p-green-600, #16a34a);
}
.tls__desc {
  font-size: 0.74rem;
  line-height: 1.35;
  color: var(--p-text-muted-color);
}
.tls__check {
  position: absolute;
  top: 0.55rem;
  inset-inline-end: 0.6rem;
  color: var(--tls-color);
}
.tls__lock {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.tls__lock i {
  font-size: 0.75rem;
}
@media (max-width: 520px) {
  .tls__cards {
    grid-template-columns: minmax(0, 1fr);
  }
  .tls__card {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    column-gap: 0.6rem;
    align-items: center;
  }
  .tls__icon {
    grid-row: span 2;
  }
}
</style>
