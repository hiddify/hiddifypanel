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
import FreeTestCard from '@/features/inbox/components/FreeTestCard.vue'
import FreeTestDialog from '@/features/inbox/components/FreeTestDialog.vue'
import BroadcastComposer from '@/features/broadcast/components/BroadcastComposer.vue'
import InboxPanel from '@/features/inbox/components/InboxPanel.vue'
import PackageDrawer from '@/features/inbox/components/PackageDrawer.vue'
import type { Conversation, FreePackage, FreeTest, Inbox } from '@/features/inbox/api'

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
const editing = ref(false)
/** The package the dialog edits; null: a new one. */
const target = ref<FreePackage | null>(null)
let feed: ReturnType<typeof liveWatch> | null = null

/** The admin's own packages, the default one first; else the one in effect (a parent's, or the defaults). */
const packages = computed<FreePackage[]>(() => {
  const free = inbox.value?.free
  if (!free) return []
  if (!free.packages.length) return [free.package]
  return [...free.packages].sort((a, b) => Number(b.id === free.default_id) - Number(a.id === free.default_id))
})
const defaultId = computed(() => (inbox.value?.free.packages.length ? inbox.value.free.default_id : packages.value[0]?.id) ?? '')
/** Several packages: each gets its own card, with its conversations in a drawer under it. */
const multi = computed(() => packages.value.length > 1)
const canAdd = computed(() => {
  const free = inbox.value?.free
  return !!free && free.can_edit && free.packages.length > 0 && free.packages.length < free.max_packages
})

/** A conversation goes with the package it asked for, while it exists; else with the default one. */
function groupOf(conversation: Conversation): string {
  const id = conversation.package_id
  return id && packages.value.some((p) => p.id === id) ? id : defaultId.value
}
const groups = computed(() => {
  const by = new Map<string, Conversation[]>()
  for (const c of inbox.value?.conversations ?? []) by.set(groupOf(c), [...(by.get(groupOf(c)) ?? []), c])
  return by
})
function conversationsOf(pkg: FreePackage): Conversation[] {
  return groups.value.get(pkg.id ?? '') ?? []
}
function needsAttention(list: Conversation[]): boolean {
  return list.some((c) => c.unread > 0 || c.free_status === 'pending')
}
function packageOf(conversation: Conversation): FreePackage {
  return packages.value.find((p) => p.id === groupOf(conversation)) ?? inbox.value!.free.package
}

function openEdit(pkg: FreePackage) {
  const free = inbox.value!.free
  // A package of the admin's own, or the parent's one to start its own from; with no packages left, a new one.
  target.value = free.packages.some((p) => p.id === pkg.id) || !free.own ? pkg : null
  editing.value = true
}
function openAdd() {
  target.value = null
  editing.value = true
}

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

      <template v-else>
        <!-- One package: its card, then every conversation -->
        <template v-if="!multi">
          <FreeTestCard :free="inbox.free" :pkg="packages[0]" :is-default="true" :multi="false" @edit="openEdit" @saved="onSaved" />
          <button v-if="canAdd" type="button" class="inbox-add" @click="openAdd"><i class="pi pi-plus" />{{ t('inbox.free.add') }}</button>
        </template>
        <!-- Several: each card with its own conversations in a drawer under it -->
        <div v-else class="inbox-groups">
          <div v-for="pkg in packages" :key="pkg.id" class="inbox-group">
            <FreeTestCard :free="inbox.free" :pkg="pkg" :is-default="pkg.id === defaultId" :multi="true" @edit="openEdit" @saved="onSaved" />
            <PackageDrawer :count="conversationsOf(pkg).length" :attention="needsAttention(conversationsOf(pkg))">
              <InboxPanel
                :conversations="conversationsOf(pkg)"
                :selected-id="selectedId"
                :package-of="packageOf"
                @select="selectedId = $event"
                @changed="onChanged"
                @removed="onRemoved"
              />
            </PackageDrawer>
          </div>
          <button v-if="canAdd" type="button" class="inbox-add" @click="openAdd"><i class="pi pi-plus" />{{ t('inbox.free.add') }}</button>
        </div>
      </template>

      <InboxPanel
        v-if="!multi || !inbox.bot_username"
        :conversations="inbox.conversations"
        :selected-id="selectedId"
        :package-of="packageOf"
        @select="selectedId = $event"
        @changed="onChanged"
        @removed="onRemoved"
      />

      <FreeTestDialog v-model:visible="editing" :free="inbox.free" :target="target" @saved="onSaved" />
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
.inbox-nobot__icon {
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
.inbox-groups {
  display: flex;
  flex-direction: column;
  gap: 1.4rem;
}
.inbox-group {
  display: flex;
  flex-direction: column;
}
.inbox-add {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.85rem;
  border: 1.5px dashed color-mix(in srgb, var(--p-text-color) 24%, transparent);
  border-radius: 18px;
  background: color-mix(in srgb, var(--p-content-background) 45%, transparent);
  color: var(--text-color-secondary);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s;
}
.inbox-add:hover,
.inbox-add:focus-visible {
  border-color: var(--primary-color);
  color: var(--primary-color);
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
