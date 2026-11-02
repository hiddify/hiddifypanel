<script setup lang="ts">
/** Quick picks under the data limit (`usage`) or the package length (`days`); the last one is "unlimited". */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { UNLIMITED_DAYS, UNLIMITED_GB } from '@/features/users/api'
import { unitLabel } from '@/shared/utils/format-metrics'

const props = defineProps<{ kind: 'usage' | 'days'; disabled?: boolean }>()
const value = defineModel<number | null>({ required: true })
const { t } = useI18n()

type Chip = { value: number; label: string; infinite: boolean; /** hidden on phones, where one line has room for fewer */ extra: boolean }
const DAY_KEYS: [number, string][] = [
  [7, 'week'],
  [30, 'month'],
  [90, 'months3'],
  [180, 'months6'],
  [365, 'year'],
]
const chips = computed<Chip[]>(() =>
  props.kind === 'usage'
    ? [
        ...[10, 50, 100, 200, 500, 1000].map((v) => ({ value: v, label: v >= 1000 ? `${v / 1000} ${unitLabel('TB')}` : `${v} ${unitLabel('GB')}`, infinite: false, extra: v === 200 || v === 500 })),
        { value: UNLIMITED_GB, label: t('users.form.unlimited'), infinite: true, extra: false },
      ]
    : [
        ...DAY_KEYS.map(([days, key]) => ({ value: days, label: t(`users.form.period.${key}`), infinite: false, extra: key === 'week' })),
        { value: UNLIMITED_DAYS, label: t('users.form.unlimited'), infinite: true, extra: false },
      ],
)
</script>

<template>
  <div class="chips">
    <button
      v-for="c in chips"
      :key="c.value"
      type="button"
      class="chip"
      :class="{ 'chip--on': value === c.value, 'chip--extra': c.extra }"
      :aria-pressed="value === c.value"
      :aria-label="c.infinite ? c.label : undefined"
      :disabled="disabled"
      @click="value = c.value"
    >
      <svg v-if="c.infinite" class="chip__inf" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M18.6 6.62c-1.44 0-2.8.56-3.77 1.53L12 10.66 10.48 12h.01L7.8 14.39c-.64.64-1.49.99-2.4.99-1.87 0-3.39-1.51-3.39-3.38S3.53 8.62 5.4 8.62c.91 0 1.76.35 2.44 1.03l1.13 1 1.51-1.34L9.22 8.2A5.37 5.37 0 0 0 5.4 6.62C2.42 6.62 0 9.04 0 12s2.42 5.38 5.4 5.38c1.44 0 2.8-.56 3.77-1.53l2.83-2.5.01.01L13.52 12h-.01l2.69-2.39c.64-.64 1.49-.99 2.4-.99 1.87 0 3.39 1.51 3.39 3.38s-1.52 3.38-3.39 3.38c-.9 0-1.76-.35-2.44-1.03l-1.14-1.01-1.51 1.34 1.27 1.12a5.386 5.386 0 0 0 3.82 1.57c2.98 0 5.4-2.41 5.4-5.38s-2.42-5.37-5.4-5.37z" /></svg>
      <template v-else>{{ c.label }}</template>
    </button>
  </div>
</template>

<style scoped>
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.chip {
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.chip:hover:not(:disabled),
.chip--on {
  color: var(--p-primary-color);
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
}
.chip:disabled {
  opacity: 0.5;
  cursor: default;
}
.chip__inf {
  display: inline-block;
  width: 1.35em;
  height: 1em;
  vertical-align: -0.15em;
}
@media (max-width: 640px) {
  /* Room is short: fewer quick picks, all on one line */
  .chip--extra {
    display: none;
  }
  .chips {
    flex-wrap: nowrap;
  }
  .chip {
    flex: 1 1 0;
    min-width: 0;
    padding-inline: 0.3rem;
    text-align: center;
    white-space: nowrap;
  }
}
</style>
