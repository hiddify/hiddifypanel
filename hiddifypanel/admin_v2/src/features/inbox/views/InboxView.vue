<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import { liveWatch, type LiveError } from '@/core/live/live'
import PageHeader from '@/shared/components/PageHeader.vue'
import ConversationList, { type InboxFilter } from '@/features/inbox/components/ConversationList.vue'
import ConversationThread from '@/features/inbox/components/ConversationThread.vue'
import FreeTestCard from '@/features/inbox/components/FreeTestCard.vue'
import FreeTestDialog from '@/features/inbox/components/FreeTestDialog.vue'
import BroadcastComposer from '@/features/broadcast/components/BroadcastComposer.vue'
import type { Conversation, FreeTest, Inbox } from '@/features/inbox/api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

/** Sending a message to users over the bot (it was its own page, /message: links to it open this window). */
const composing = ref(false)
const composeIds = ref<number[]>([])

function openComposer() {
  // ?compose=1&ids=1,2,3: from an old /message link, with the users chosen there as the audience.
  if (route.query.compose) {
    composeIds.value = String(route.query.ids ?? '')
      .split(',')
      .map((x) => Number(x))
      .filter((x) => Number.isInteger(x) && x > 0)
    const { compose: _c, ids: _i, ...rest } = route.query
    void router.replace({ query: rest })
  } else {
    composeIds.value = []
  }
  composing.value = true
}

const inbox = ref<Inbox | null>(null)
const loadError = ref('')
const selectedId = ref<number | null>(null)
const filter = ref<InboxFilter>('all')
const editing = ref(false)
let feed: ReturnType<typeof liveWatch> | null = null

const selected = computed(() => inbox.value?.conversations.find((c) => c.id === selectedId.value) ?? null)

function watchInbox() {
  feed?.stop()
  loadError.value = ''
  // Pushed when a message arrives or a request changes (the tables of each commit), and every half minute.
  feed = liveWatch<Inbox>('inbox/', {
    intervalMs: 30_000,
    tags: ['conversation', 'message'],
    onData: (next) => {
      inbox.value = next
      loadError.value = ''
    },
    onError: (error: LiveError) => {
      if (!inbox.value && !error.retrying) loadError.value = error.message
    },
  })
}
onMounted(() => {
  watchInbox()
  if (route.query.compose) openComposer()
})

function onChanged(conversation: Conversation) {
  if (!inbox.value) return
  inbox.value = { ...inbox.value, conversations: inbox.value.conversations.map((c) => (c.id === conversation.id ? conversation : c)) }
}
function onRemoved(id: number) {
  selectedId.value = null
  if (inbox.value) inbox.value = { ...inbox.value, conversations: inbox.value.conversations.filter((c) => c.id !== id) }
}
function onSaved(free: FreeTest) {
  if (inbox.value) inbox.value = { ...inbox.value, free }
}
</script>

<template>
  <div class="inbox-page">
    <div class="inbox-head">
      <PageHeader :title="t('inbox.title')" :subtitle="t('inbox.subtitle')" />
      <Button :label="t('broadcast.title')" icon="pi pi-send" class="inbox-head__send" :disabled="!!inbox && !inbox.bot_username" @click="openComposer" />
    </div>

    <template v-if="!inbox && !loadError">
      <Skeleton height="9rem" border-radius="18px" />
      <Skeleton height="26rem" border-radius="18px" />
    </template>
    <div v-else-if="!inbox" class="inbox-error">
      <Message severity="error" :closable="false">{{ loadError }}</Message>
      <Button :label="t('inbox.retry')" icon="pi pi-refresh" severity="secondary" outlined @click="watchInbox" />
    </div>

    <template v-else>
      <!-- No bot: nothing can arrive -->
      <section v-if="!inbox.bot_username" class="inbox-nobot">
        <span class="inbox-nobot__icon"><i class="pi pi-send" /></span>
        <div>
          <h3>{{ t('inbox.noBot.title') }}</h3>
          <p>{{ t('inbox.noBot.text') }}</p>
        </div>
        <RouterLink :to="{ path: '/settings', hash: '#cat=telegram' }" class="inbox-nobot__link">{{ t('inbox.noBot.action') }} <i class="pi pi-arrow-right" /></RouterLink>
      </section>

      <FreeTestCard v-else :free="inbox.free" @edit="editing = true" />

      <section class="inbox-panel" :class="{ 'inbox-panel--open': selected }">
        <aside class="inbox-list">
          <div v-if="!inbox.conversations.length" class="inbox-empty">
            <span class="inbox-empty__icon"><i class="pi pi-inbox" /></span>
            <h3>{{ t('inbox.list.empty.title') }}</h3>
            <p>{{ t('inbox.list.empty.text') }}</p>
          </div>
          <ConversationList v-else v-model:filter="filter" :conversations="inbox.conversations" :selected-id="selectedId" @select="selectedId = $event" />
        </aside>
        <div class="inbox-thread">
          <ConversationThread v-if="selected" :conversation="selected" :package="inbox.free.package" @back="selectedId = null" @changed="onChanged" @removed="onRemoved" />
          <div v-else class="inbox-empty">
            <span class="inbox-empty__icon"><i class="pi pi-comments" /></span>
            <h3>{{ t('inbox.thread.pick.title') }}</h3>
            <p>{{ t('inbox.thread.pick.text') }}</p>
          </div>
        </div>
      </section>

      <FreeTestDialog v-model:visible="editing" :free="inbox.free" @saved="onSaved" />
    </template>

    <!-- Send a Telegram message to users (everyone, a group, or the users chosen on the users page) -->
    <Dialog
      v-model:visible="composing"
      modal
      maximizable
      :draggable="false"
      :header="composeIds.length ? t('broadcast.dialogTitle', { n: composeIds.length }, composeIds.length) : t('broadcast.title')"
      :style="{ width: 'min(72rem, 96vw)' }"
      :breakpoints="{ '767px': '100vw' }"
      :pt="{ root: { class: 'inbox-compose-dialog' } }"
    >
      <BroadcastComposer v-if="composing" :ids="composeIds" in-dialog />
    </Dialog>
  </div>
</template>

<style scoped>
.inbox-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.inbox-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0 1rem;
}
.inbox-head > :first-child {
  flex: 1;
  min-width: 14rem;
}
.inbox-head__send {
  flex: none;
}
.inbox-error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.8rem;
}
.inbox-nobot {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1.1rem 1.25rem;
  border-radius: 18px;
  border: 1px dashed var(--surface-border);
  background: var(--surface-card);
}
.inbox-nobot > div {
  flex: 1;
  min-width: 14rem;
}
.inbox-nobot h3,
.inbox-nobot p {
  margin: 0;
}
.inbox-nobot p {
  margin-top: 0.2rem;
  color: var(--text-color-secondary);
}
.inbox-nobot__icon,
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
.inbox-nobot__link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
  color: var(--primary-color);
}
html[dir='rtl'] .inbox-nobot__link .pi {
  transform: scaleX(-1);
}
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

<style>
/* The send-message window: the whole screen on a phone */
@media (max-width: 767px) {
  .inbox-compose-dialog.p-dialog {
    width: 100vw !important;
    height: 100dvh;
    max-height: 100dvh;
    margin: 0;
    border-radius: 0;
  }
}
</style>
