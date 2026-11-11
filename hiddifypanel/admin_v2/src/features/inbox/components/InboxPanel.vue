<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import ConversationList, { type InboxFilter } from '@/features/inbox/components/ConversationList.vue'
import ConversationThread from '@/features/inbox/components/ConversationThread.vue'
import type { Conversation, FreePackage } from '@/features/inbox/api'

/** A list of conversations beside the one that is open (on a phone: one pane at a time). `packageOf`: the package a
 *  conversation asked for, shown in its request. */
const props = defineProps<{ conversations: Conversation[]; selectedId: number | null; packageOf: (conversation: Conversation) => FreePackage }>()
const emit = defineEmits<{ select: [id: number | null]; changed: [conversation: Conversation]; removed: [id: number] }>()

const { t } = useI18n()
const filter = ref<InboxFilter>('all')
const selected = computed(() => props.conversations.find((c) => c.id === props.selectedId) ?? null)
</script>

<template>
  <section class="inbox-panel" :class="{ 'inbox-panel--open': selected }">
    <aside class="inbox-list">
      <div v-if="!conversations.length" class="inbox-empty">
        <span class="inbox-empty__icon"><i class="pi pi-inbox" /></span>
        <h3>{{ t('inbox.list.empty.title') }}</h3>
        <p>{{ t('inbox.list.empty.text') }}</p>
      </div>
      <ConversationList v-else v-model:filter="filter" :conversations="conversations" :selected-id="selectedId" @select="emit('select', $event)" />
    </aside>
    <div class="inbox-thread">
      <ConversationThread
        v-if="selected"
        :conversation="selected"
        :package="packageOf(selected)"
        @back="emit('select', null)"
        @changed="emit('changed', $event)"
        @removed="emit('removed', $event)"
      />
      <div v-else class="inbox-empty">
        <span class="inbox-empty__icon"><i class="pi pi-comments" /></span>
        <h3>{{ t('inbox.thread.pick.title') }}</h3>
        <p>{{ t('inbox.thread.pick.text') }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.inbox-panel {
  display: grid;
  grid-template-columns: minmax(17rem, 22rem) minmax(0, 1fr);
  height: clamp(26rem, calc(100dvh - 24rem), 46rem);
  border-radius: 18px;
  border: 1px solid var(--surface-border);
  background: var(--surface-card);
  overflow: hidden;
}
.inbox-list {
  min-height: 0;
  border-inline-end: 1px solid var(--surface-border);
}
.inbox-thread {
  min-width: 0;
  min-height: 0;
}
.inbox-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  height: 100%;
  padding: 2rem 1.5rem;
  text-align: center;
}
.inbox-empty__icon {
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  flex: none;
  border-radius: 50%;
  background: color-mix(in srgb, var(--primary-color) 12%, transparent);
  color: var(--primary-color);
  font-size: 1.25rem;
}
.inbox-empty h3 {
  margin: 0.4rem 0 0;
  font-size: 1.05rem;
}
.inbox-empty p {
  max-width: 24rem;
  margin: 0;
  color: var(--text-color-secondary);
  line-height: 1.5;
}
/* A phone shows one pane at a time: the list, then the conversation over it. */
@media (max-width: 899px) {
  .inbox-panel {
    grid-template-columns: minmax(0, 1fr);
    height: clamp(24rem, calc(100dvh - 12rem), 46rem);
  }
  .inbox-list {
    border-inline-end: 0;
  }
  .inbox-thread,
  .inbox-panel--open .inbox-list {
    display: none;
  }
  .inbox-panel--open .inbox-thread {
    display: block;
  }
}
</style>
