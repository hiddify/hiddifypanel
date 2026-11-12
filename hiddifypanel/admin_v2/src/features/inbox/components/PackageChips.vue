<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { splitData } from '@/features/inbox/format'
import type { Approval } from '@/features/inbox/api'

/** A free test package at a glance: how long, how much, and the FREE tag. */
/** `approval`: also show how it is given (in the admin's own views; the bot does not show it). */
const props = defineProps<{ days: number; usageGb: number; tag?: boolean; approval?: Approval }>()
const { t } = useI18n()
const data = computed(() => splitData(props.usageGb))
</script>

<template>
  <span class="pkg-chips">
    <span class="pkg-chip"><i class="pi pi-clock" />{{ t('inbox.free.days', { n: days }, days) }}</span>
    <span class="pkg-chip"><i class="pi pi-database" /><span dir="ltr">{{ data.amount.toLocaleString() }} {{ t(`inbox.free.unit.${data.unit}`) }}</span></span>
    <span v-if="tag" class="pkg-chip pkg-chip--free"><i class="pi pi-tag" />{{ t('inbox.free.tag') }}</span>
    <span v-if="approval" class="pkg-chip" :class="`pkg-chip--${approval}`" :title="t(`inbox.free.${approval}`)">
      <i class="pi" :class="approval === 'auto' ? 'pi-bolt' : 'pi-user-edit'" />{{ t(`inbox.free.${approval}Short`) }}
    </span>
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
/* How it is given, in the colours of the choice in the package dialog: amber waits for the admin, green is at once. */
.pkg-chip--manual {
  background: color-mix(in srgb, var(--p-amber-500) 16%, transparent);
  color: var(--p-amber-700, #b45309);
}
.pkg-chip--auto {
  background: color-mix(in srgb, var(--p-emerald-500) 16%, transparent);
  color: var(--p-emerald-700, #047857);
}
.pkg-chip--manual .pi,
.pkg-chip--auto .pi {
  color: inherit;
}
html.app-dark .pkg-chip--manual {
  color: var(--p-amber-300, #fcd34d);
}
html.app-dark .pkg-chip--auto {
  color: var(--p-emerald-300, #6ee7b7);
}
</style>
