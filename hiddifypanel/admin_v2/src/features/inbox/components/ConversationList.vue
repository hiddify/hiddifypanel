<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import SelectButton from 'primevue/selectbutton'
import PersonAvatar from '@/features/inbox/components/PersonAvatar.vue'
import { shortWhen } from '@/features/inbox/format'
import type { Conversation } from '@/features/inbox/api'

export type InboxFilter = 'all' | 'requests' | 'unread'

const props = defineProps<{ conversations: Conversation[]; selectedId: number | null }>()
defineEmits<{ select: [id: number] }>()
const filter = defineModel<InboxFilter>('filter', { required: true })

const { t, locale } = useI18n()

const count = computed<Record<InboxFilter, number>>(() => ({
  all: props.conversations.length,
  requests: props.conversations.filter((c) => c.free_status === 'pending').length,
  unread: props.conversations.filter((c) => c.unread > 0).length,
}))
const filters = computed(() =>
  (['all', 'requests', 'unread'] as const).map((value) => ({ value, label: t(`inbox.list.${value}`) + (value !== 'all' && count.value[value] ? ` ${count.value[value]}` : '') })),
)
const shown = computed(() =>
  props.conversations.filter((c) => (filter.value === 'requests' ? c.free_status === 'pending' : filter.value === 'unread' ? c.unread > 0 : true)),
)

/** The last thing that happened, as one line. */
function preview(c: Conversation): string {
  if (c.last_text === 'request' || c.last_text === 'granted' || c.last_text === 'declined') return t(`inbox.event.${c.last_text}`)
  return (c.last_sender === 'admin' ? `${t('inbox.list.you')} ` : '') + c.last_text
}
</script>

<template>
  <div class="cl">
    <div class="cl-filters">
      <SelectButton v-model="filter" :options="filters" option-label="label" option-value="value" :allow-empty="false" size="small" :aria-label="t('inbox.list.filter')" />
    </div>

    <p v-if="!shown.length" class="cl-none"><i class="pi pi-filter-slash" />{{ t('inbox.list.noMatch') }}</p>
    <ul v-else class="cl-items" role="listbox" :aria-label="t('inbox.title')">
      <li v-for="c in shown" :key="c.id">
        <button
          type="button"
          role="option"
          class="cl-item"
          :class="{ 'cl-item--on': c.id === selectedId, 'cl-item--unread': c.unread > 0 }"
          :aria-selected="c.id === selectedId"
          @click="$emit('select', c.id)"
        >
          <PersonAvatar :id="c.id" :name="c.name" />
          <span class="cl-body">
            <span class="cl-top">
              <b class="cl-name" dir="auto">{{ c.name }}</b>
              <time class="cl-time">{{ shortWhen(c.last_at, locale) }}</time>
            </span>
            <span class="cl-bottom">
              <span class="cl-preview" dir="auto">{{ preview(c) }}</span>
              <span v-if="c.free_status === 'pending'" class="cl-tag cl-tag--request"><i class="pi pi-gift" />{{ t('inbox.list.request') }}</span>
              <span v-else-if="c.free_grants" class="cl-tag cl-tag--free">{{ t('inbox.free.tag') }}</span>
              <span v-if="c.unread" class="cl-unread" :aria-label="t('inbox.list.unreadCount', { n: c.unread })">{{ c.unread > 99 ? '99+' : c.unread }}</span>
            </span>
          </span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.cl {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}
.cl-filters {
  padding: 0.75rem;
  border-bottom: 1px solid var(--surface-border);
  overflow-x: auto;
}
.cl-items {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 0.4rem;
  list-style: none;
  overflow-y: auto;
}
.cl-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.65rem 0.7rem;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--text-color);
  text-align: start;
  cursor: pointer;
  transition: background 0.12s;
}
.cl-item:hover {
  background: var(--p-content-hover-background, var(--surface-hover));
}
.cl-item--on {
  background: color-mix(in srgb, var(--primary-color) 12%, transparent);
}
.cl-body {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
  min-width: 0;
}
.cl-top,
.cl-bottom {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}
.cl-name,
.cl-preview {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cl-name {
  font-weight: 600;
}
.cl-item--unread .cl-name {
  font-weight: 800;
}
.cl-time {
  flex: none;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}
.cl-preview {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}
.cl-item--unread .cl-preview {
  color: var(--text-color);
}
.cl-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex: none;
  padding: 0.08rem 0.45rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
}
.cl-tag .pi {
  font-size: 0.65rem;
}
.cl-tag--request {
  background: color-mix(in srgb, var(--p-orange-500, #f97316) 18%, transparent);
  color: var(--p-orange-600, #ea580c);
}
.cl-tag--free {
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 16%, transparent);
  color: var(--p-green-600, #16a34a);
  letter-spacing: 0.04em;
}
.cl-unread {
  display: grid;
  place-items: center;
  flex: none;
  min-width: 1.3rem;
  height: 1.3rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  background: var(--primary-color);
  color: var(--primary-contrast-color);
  font-size: 0.7rem;
  font-weight: 700;
}
.cl-none {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  margin: 0;
  padding: 2.5rem 1rem;
  color: var(--text-color-secondary);
}
.cl-none .pi {
  font-size: 1.5rem;
}
</style>
