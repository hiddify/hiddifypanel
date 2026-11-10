<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { splitData } from '@/features/inbox/format'

/** A free test package at a glance: how long, how much, and the FREE tag. */
const props = defineProps<{ days: number; usageGb: number; tag?: boolean }>()
const { t } = useI18n()
const data = computed(() => splitData(props.usageGb))
</script>

<template>
  <span class="pkg-chips">
    <span class="pkg-chip"><i class="pi pi-clock" />{{ t('inbox.free.days', { n: days }, days) }}</span>
    <span class="pkg-chip"><i class="pi pi-database" /><span dir="ltr">{{ data.amount.toLocaleString() }} {{ t(`inbox.free.unit.${data.unit}`) }}</span></span>
    <span v-if="tag" class="pkg-chip pkg-chip--free"><i class="pi pi-tag" />{{ t('inbox.free.tag') }}</span>
  </span>
</template>

<style scoped>
.pkg-chips {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.pkg-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  background: var(--p-content-hover-background, var(--surface-hover));
  color: var(--text-color);
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
}
.pkg-chip .pi {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}
.pkg-chip--free {
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 16%, transparent);
  color: var(--p-green-600, #16a34a);
  letter-spacing: 0.04em;
}
.pkg-chip--free .pi {
  color: inherit;
}
</style>
