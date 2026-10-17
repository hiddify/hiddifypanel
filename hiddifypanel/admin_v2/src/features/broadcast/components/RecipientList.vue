<template>
  <div class="rl">
    <div class="rl__bar">
      <IconField class="rl__search">
        <InputIcon class="pi pi-search" />
        <InputText v-model="query" :placeholder="t('broadcast.recipients.search')" size="small" :aria-label="t('broadcast.recipients.search')" />
      </IconField>
      <span class="rl__count">{{ t('broadcast.recipients.count', { n: modelValue.length, total: users.length }) }}</span>
      <Button :label="t('broadcast.recipients.all')" size="small" text @click="setAll(true)" />
      <Button :label="t('broadcast.recipients.none')" size="small" text severity="secondary" @click="setAll(false)" />
    </div>

    <div v-if="loading" class="rl__empty"><i class="pi pi-spin pi-spinner" /></div>
    <p v-else-if="!users.length" class="rl__empty">{{ t('broadcast.recipients.empty') }}</p>
    <p v-else-if="!filtered.length" class="rl__empty">{{ t('broadcast.recipients.noMatch') }}</p>
    <ul v-else class="rl__list" role="listbox" aria-multiselectable="true" :aria-label="t('broadcast.recipients.title')">
      <li v-for="u in shown" :key="u.id" role="option" :aria-selected="checked.has(u.id)">
        <label class="rl__row" :class="{ 'rl__row--off': !checked.has(u.id) }">
          <Checkbox :model-value="checked.has(u.id)" binary :input-id="`rl-${u.id}`" @update:model-value="toggle(u.id)" />
          <span class="rl__dot" :class="u.active ? 'rl__dot--on' : 'rl__dot--off'" :title="u.active ? t('broadcast.recipients.active') : t('broadcast.recipients.inactive')" />
          <!-- bdi: a Latin name in a Persian page reads right, but stays where the page's direction puts it -->
          <span class="rl__name"><bdi>{{ u.name || `#${u.id}` }}</bdi></span>
          <span class="rl__seen">{{ seen(u.last_online) }}</span>
        </label>
      </li>
    </ul>
    <Button v-if="filtered.length > shown.length" :label="t('broadcast.recipients.more', { n: filtered.length - shown.length })" size="small" text class="rl__more" @click="limit += PAGE" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import { relativeDays } from '@/features/users/format'
import type { Recipient } from '@/features/broadcast/api'

/** The users an audience reaches, to see before sending and to leave some out (or pick a few). ``v-model``: the checked ids. */
const props = defineProps<{ users: Recipient[]; loading?: boolean }>()
const modelValue = defineModel<number[]>({ required: true })

const { t, locale } = useI18n()
const PAGE = 150
const query = ref('')
const limit = ref(PAGE)

const checked = computed(() => new Set(modelValue.value))
const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? props.users.filter((u) => u.name.toLowerCase().includes(q) || u.telegram_id.includes(q)) : props.users
})
const shown = computed(() => filtered.value.slice(0, limit.value))
watch(query, () => (limit.value = PAGE))

function toggle(id: number) {
  const next = new Set(checked.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  modelValue.value = [...next]
}

/** All / none of what the search shows (all of them without a search). */
function setAll(on: boolean) {
  const next = new Set(checked.value)
  for (const u of filtered.value) {
    if (on) next.add(u.id)
    else next.delete(u.id)
  }
  modelValue.value = [...next]
}

function seen(iso: string | null): string {
  if (!iso) return t('broadcast.recipients.never')
  const days = Math.round((Date.parse(iso) - Date.now()) / 86_400_000)
  return relativeDays(days, locale.value)
}
</script>

<style scoped>
.rl {
  margin-top: 0.9rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 14px;
  overflow: hidden;
}
.rl__bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  padding: 0.5rem;
  background: var(--p-content-hover-background);
}
.rl__search {
  flex: 1 1 12rem;
}
.rl__search :deep(input) {
  width: 100%;
}
.rl__count {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.rl__list {
  max-height: 17rem;
  overflow: auto;
  margin: 0;
  padding: 0.25rem 0;
  list-style: none;
}
.rl__row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
}
.rl__row:hover {
  background: var(--p-content-hover-background);
}
.rl__row--off .rl__name {
  color: var(--p-text-muted-color);
  text-decoration: line-through;
  text-decoration-color: color-mix(in srgb, var(--p-text-muted-color) 50%, transparent);
}
.rl__dot {
  flex: 0 0 auto;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
}
.rl__dot--on {
  background: var(--p-green-500, #22c55e);
}
.rl__dot--off {
  background: var(--p-text-muted-color);
  opacity: 0.6;
}
.rl__name {
  flex: 1;
  text-align: start;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.88rem;
}
.rl__seen {
  flex: 0 0 auto;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.rl__empty {
  margin: 0;
  padding: 1.2rem;
  text-align: center;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.rl__more {
  width: 100%;
  border-radius: 0;
}
</style>
