<script setup lang="ts">
/** Domain mode cards: emoji, name and what it is for. `fit` marks the ones detection recommends or warns about. */
import { useI18n } from 'vue-i18n'
import { KIND_META, type DomainKind } from '@/features/domains/api'

defineProps<{ kinds: DomainKind[]; fit?: Partial<Record<DomainKind, 'good' | 'ok' | 'bad'>>; compact?: boolean }>()
const model = defineModel<DomainKind>({ required: true })
const { t } = useI18n()
</script>

<template>
  <div class="kinds" :class="{ 'kinds--compact': compact }" role="radiogroup" :aria-label="t('domains.field.mode')">
    <button
      v-for="k in kinds"
      :key="k"
      type="button"
      role="radio"
      class="kind"
      :class="[{ 'kind--on': model === k }, fit?.[k] ? `kind--${fit[k]}` : '']"
      :style="{ '--kind-color': KIND_META[k].color }"
      :aria-checked="model === k"
      @click="model = k"
    >
      <span class="kind__emoji" aria-hidden="true">{{ KIND_META[k].emoji }}</span>
      <span class="kind__text">
        <span class="kind__name">
          {{ t(`domains.kind.${k}.name`) }}
          <span v-if="fit?.[k] === 'good'" class="kind__tag kind__tag--good"><i class="pi pi-sparkles" />{{ t('domains.wizard.recommended') }}</span>
          <span v-else-if="fit?.[k] === 'bad'" class="kind__tag kind__tag--bad"><i class="pi pi-exclamation-triangle" />{{ t('domains.wizard.unlikely') }}</span>
        </span>
        <span v-if="!compact" class="kind__desc">
          {{ t(`domains.kind.${k}.desc`) }}
          <a v-if="KIND_META[k].link" :href="KIND_META[k].link" target="_blank" rel="noopener" class="kind__more" @click.stop>{{ t('domains.readMore') }}<i class="pi pi-external-link" /></a>
        </span>
      </span>
      <i v-if="model === k" class="pi pi-check-circle kind__check" />
    </button>
  </div>
</template>

<style scoped>
.kinds {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15.5rem, 1fr));
  gap: 0.55rem;
}
.kinds--compact {
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
}
.kind {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding: 0.75rem 0.85rem;
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
    background 0.15s ease;
}
.kinds--compact .kind {
  align-items: center;
  padding: 0.55rem 0.7rem;
}
.kind:hover {
  border-color: color-mix(in srgb, var(--kind-color) 55%, var(--p-content-border-color));
  transform: translateY(-1px);
}
.kind:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.kind--on {
  border-color: var(--kind-color);
  box-shadow: 0 0 0 1px var(--kind-color);
  background: linear-gradient(135deg, color-mix(in srgb, var(--kind-color) 11%, transparent), transparent 75%), var(--p-content-background);
}
.kind--bad:not(.kind--on) {
  opacity: 0.62;
}
.kind__emoji {
  font-size: 1.35rem;
  line-height: 1.6rem;
}
.kinds--compact .kind__emoji {
  font-size: 1.1rem;
}
.kind__text {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}
.kind__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  font-weight: 650;
  font-size: 0.93rem;
}
.kind__desc {
  font-size: 0.78rem;
  line-height: 1.35;
  color: var(--p-text-muted-color);
}
.kind__more {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-inline-start: 0.2rem;
  color: var(--p-primary-color);
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}
.kind__more:hover {
  text-decoration: underline;
}
.kind__more i {
  font-size: 0.65rem;
}
.kind__tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0 0.45rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 600;
}
.kind__tag i {
  font-size: 0.65rem;
}
.kind__tag--good {
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 14%, transparent);
}
.kind__tag--bad {
  color: var(--p-amber-700, #b45309);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 16%, transparent);
}
.kind__check {
  position: absolute;
  top: 0.55rem;
  inset-inline-end: 0.6rem;
  color: var(--kind-color);
}
.kinds--compact .kind__check {
  display: none;
}
@media (max-width: 640px) {
  .kinds {
    grid-template-columns: minmax(0, 1fr);
  }
  .kinds--compact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
