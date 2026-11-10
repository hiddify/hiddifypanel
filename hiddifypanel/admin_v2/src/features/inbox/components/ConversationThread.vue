<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import PackageChips from '@/features/inbox/components/PackageChips.vue'
import PersonAvatar from '@/features/inbox/components/PersonAvatar.vue'
import { clock, dayLabel } from '@/features/inbox/format'
import { inboxApi, type ChatMessage, type Conversation, type FreeAction, type FreePackage, type Thread } from '@/features/inbox/api'

/** One conversation: its messages, the free test request to answer, and the box to write back. */
const props = defineProps<{
  /** From the list: shown at once, and its `last_at` tells when to ask for the messages again. */
  conversation: Conversation
  package: FreePackage
}>()
const emit = defineEmits<{ back: []; changed: [conversation: Conversation]; removed: [id: number] }>()

const { t, locale } = useI18n()
const toast = useToast()
const confirm = useConfirm()
const dangerConfirm = useDangerConfirm()

const thread = ref<Thread | null>(null)
const loading = ref(false)
const loadError = ref('')
const text = ref('')
const sending = ref(false)
const answering = ref<FreeAction | null>(null)
const scroller = ref<HTMLElement | null>(null)
const menu = ref<InstanceType<typeof Menu> | null>(null)

const conv = computed(() => thread.value?.conversation ?? props.conversation)
const MAX_TEXT = 2000

interface Row {
  message: ChatMessage
  /** Set on the first message of a day. */
  day: string | null
}
const rows = computed<Row[]>(() => {
  let last = ''
  return (thread.value?.messages ?? []).map((message) => {
    const day = new Date(message.at).toDateString()
    const first = day !== last
    last = day
    return { message, day: first ? dayLabel(message.at, locale.value) : null }
  })
})

function grantedPackage(message: ChatMessage): { days: number; usageGb: number } {
  const [days, usage] = message.text.split('|')
  return { days: Number(days) || 0, usageGb: Number(usage) || 0 }
}

async function toBottom() {
  await nextTick()
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight })
}

function show(next: Thread) {
  thread.value = next
  emit('changed', next.conversation)
  void toBottom()
}

async function load(quiet = false) {
  const id = props.conversation.id
  if (!quiet) {
    loading.value = true
    thread.value = null
  }
  loadError.value = ''
  try {
    const next = await inboxApi.thread(id)
    if (id === props.conversation.id) show(next)
  } catch (err) {
    if (!quiet) loadError.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
}

watch(() => props.conversation.id, () => void load(), { immediate: true })
// Something new arrived (the list is live): bring the messages, without a spinner.
watch(
  () => props.conversation.last_at,
  (now, before) => {
    if (before && now !== before && thread.value && now !== thread.value.conversation.last_at) void load(true)
  },
)

async function send() {
  const body = text.value.trim()
  if (!body || sending.value) return
  sending.value = true
  try {
    show(await inboxApi.send(props.conversation.id, body))
    text.value = ''
  } catch (err) {
    toast.add({ severity: 'error', summary: t('inbox.thread.sendFailed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    sending.value = false
  }
}

function onEnter(event: KeyboardEvent) {
  // Enter sends; Shift+Enter (and the phone keyboard's return while composing) makes a new line.
  if (event.shiftKey || event.isComposing) return
  event.preventDefault()
  void send()
}

const ERRORS = ['no_room', 'read_only', 'disabled', 'not_pending']
async function answer(action: FreeAction) {
  answering.value = action
  try {
    show(await inboxApi.answer(props.conversation.id, action))
    toast.add({ severity: action === 'decline' ? 'info' : 'success', summary: t(action === 'decline' ? 'inbox.thread.declined' : 'inbox.thread.approved'), life: 3500 })
  } catch (err) {
    const code = apiErrorMessage(err)
    toast.add({ severity: 'error', summary: t('inbox.thread.actionFailed'), detail: ERRORS.includes(code) ? t(`inbox.error.${code}`) : code, life: 6000 })
  } finally {
    answering.value = null
  }
}

function giveAnother() {
  confirm.require({
    header: t('inbox.thread.give'),
    message: t('inbox.thread.giveConfirm', { name: conv.value.name }),
    icon: 'pi pi-gift',
    acceptProps: { label: t('inbox.thread.give') },
    rejectProps: { label: t('common.cancel'), severity: 'secondary', text: true },
    accept: () => void answer('grant'),
  })
}

function remove() {
  dangerConfirm({
    header: t('inbox.thread.delete'),
    message: t('inbox.thread.deleteConfirm'),
    acceptLabel: t('inbox.thread.delete'),
    rejectLabel: t('common.cancel'),
    accept: async () => {
      try {
        await inboxApi.remove(props.conversation.id)
        emit('removed', props.conversation.id)
      } catch (err) {
        toast.add({ severity: 'error', summary: t('inbox.thread.actionFailed'), detail: apiErrorMessage(err), life: 6000 })
      }
    },
  })
}

const menuItems = computed(() => [
  ...(conv.value.free_status !== 'pending' && props.package.enabled ? [{ label: t('inbox.thread.give'), icon: 'pi pi-gift', command: giveAnother }] : []),
  ...(conv.value.username ? [{ label: t('inbox.free.openTelegram'), icon: 'pi pi-send', url: `https://t.me/${conv.value.username}`, target: '_blank' }] : []),
  { label: t('inbox.thread.delete'), icon: 'pi pi-trash', command: remove },
])
</script>

<template>
  <div class="th">
    <header class="th-head">
      <Button icon="pi pi-arrow-left" severity="secondary" text rounded class="th-back" :aria-label="t('inbox.thread.back')" @click="$emit('back')" />
      <PersonAvatar :id="conv.id" :name="conv.name" size="lg" />
      <div class="th-who">
        <b dir="auto">{{ conv.name }}</b>
        <span>
          <span v-if="conv.username" dir="ltr">@{{ conv.username }}</span>
          <span v-if="conv.account" class="th-account" :class="{ 'th-account--off': !conv.account.active }">
            <i class="pi pi-user" /><span dir="auto">{{ conv.account.name }}</span>
          </span>
          <span v-if="conv.free_grants" class="th-free">{{ t('inbox.free.tag') }}</span>
        </span>
      </div>
      <Button icon="pi pi-ellipsis-v" severity="secondary" text rounded :aria-label="t('inbox.thread.more')" aria-haspopup="true" @click="menu?.toggle($event)" />
      <Menu ref="menu" :model="menuItems" popup />
    </header>

    <div ref="scroller" class="th-messages">
      <div v-if="loading" class="th-center"><ProgressSpinner style="width: 2.2rem; height: 2.2rem" /></div>
      <div v-else-if="loadError" class="th-center">
        <Message severity="error" :closable="false">{{ loadError }}</Message>
        <Button :label="t('inbox.retry')" icon="pi pi-refresh" severity="secondary" outlined size="small" @click="load()" />
      </div>
      <p v-else-if="!rows.length" class="th-center th-muted"><i class="pi pi-comments" />{{ t('inbox.thread.empty') }}</p>
      <template v-for="row in rows" v-else :key="row.message.id">
        <div v-if="row.day" class="th-day"><span>{{ row.day }}</span></div>
        <div v-if="row.message.kind === 'text'" class="th-row" :class="`th-row--${row.message.sender}`">
          <div class="th-bubble">
            <p dir="auto">{{ row.message.text }}</p>
            <time>{{ clock(row.message.at, locale) }}</time>
          </div>
        </div>
        <div v-else class="th-event" :class="`th-event--${row.message.kind}`">
          <i class="pi" :class="row.message.kind === 'granted' ? 'pi-check-circle' : row.message.kind === 'declined' ? 'pi-times-circle' : 'pi-gift'" />
          <span>{{ t(`inbox.event.${row.message.kind}`) }}</span>
          <PackageChips v-if="row.message.kind === 'granted'" :days="grantedPackage(row.message).days" :usage-gb="grantedPackage(row.message).usageGb" />
          <time>{{ clock(row.message.at, locale) }}</time>
        </div>
      </template>
    </div>

    <!-- A request waiting: the one decision to make, right above the message box -->
    <section v-if="conv.free_status === 'pending'" class="th-request" role="status">
      <div class="th-request__text">
        <b><i class="pi pi-gift" /> {{ t('inbox.thread.request.title', { name: conv.name }) }}</b>
        <small>{{ conv.first_time ? t('inbox.thread.request.first') : t('inbox.thread.request.again') }}</small>
        <PackageChips :days="package.days" :usage-gb="package.usage_gb" tag />
      </div>
      <div class="th-request__actions">
        <Button :label="t('inbox.thread.decline')" icon="pi pi-times" severity="secondary" outlined :loading="answering === 'decline'" :disabled="!!answering" @click="answer('decline')" />
        <Button :label="t('inbox.thread.approve')" icon="pi pi-check" severity="success" :loading="answering === 'approve'" :disabled="!!answering" @click="answer('approve')" />
      </div>
    </section>

    <footer class="th-compose">
      <Textarea v-model="text" auto-resize rows="1" :maxlength="MAX_TEXT" :placeholder="t('inbox.thread.placeholder')" :aria-label="t('inbox.thread.placeholder')" class="th-input" dir="auto" @keydown.enter="onEnter" />
      <Button icon="pi pi-send" rounded :loading="sending" :disabled="!text.trim()" :aria-label="t('inbox.thread.send')" class="th-send" @click="send" />
    </footer>
  </div>
</template>

<style scoped>
.th {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.th-head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.65rem 0.8rem;
  border-bottom: 1px solid var(--surface-border);
}
.th-back {
  display: none;
}
html[dir='rtl'] .th-back :deep(.pi),
html[dir='rtl'] .th-send :deep(.pi) {
  transform: scaleX(-1);
}
.th-who {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  flex: 1;
  min-width: 0;
}
.th-who > b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.th-who > span {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.2rem 0.6rem;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}
.th-account {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--p-green-600, #16a34a);
}
.th-account--off {
  color: var(--text-color-secondary);
  text-decoration: line-through;
}
.th-account .pi {
  font-size: 0.7rem;
}
.th-free {
  padding: 0 0.4rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 16%, transparent);
  color: var(--p-green-600, #16a34a);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.th-messages {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
  min-height: 0;
  padding: 1rem;
  overflow-y: auto;
  background: var(--surface-ground);
}
.th-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  flex: 1;
  margin: 0;
}
.th-muted {
  color: var(--text-color-secondary);
}
.th-muted .pi {
  font-size: 1.8rem;
}
.th-day {
  display: flex;
  justify-content: center;
  margin: 0.6rem 0 0.3rem;
}
.th-day span {
  padding: 0.15rem 0.7rem;
  border-radius: 999px;
  background: var(--surface-card);
  color: var(--text-color-secondary);
  font-size: 0.72rem;
}
.th-row {
  display: flex;
}
.th-row--admin {
  justify-content: flex-end;
}
.th-bubble {
  max-width: min(34rem, 82%);
  padding: 0.5rem 0.8rem 0.35rem;
  border-radius: 16px;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-end-start-radius: 4px;
}
.th-row--admin .th-bubble {
  background: var(--primary-color);
  border-color: transparent;
  color: var(--primary-contrast-color);
  border-end-start-radius: 16px;
  border-end-end-radius: 4px;
}
.th-bubble p {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.5;
}
.th-bubble time,
.th-event time {
  display: block;
  margin-top: 0.1rem;
  font-size: 0.68rem;
  opacity: 0.65;
  text-align: end;
}
.th-event {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-self: center;
  max-width: 100%;
  margin: 0.35rem 0;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  font-size: 0.82rem;
  font-weight: 600;
}
.th-event time {
  margin: 0;
  font-weight: 400;
}
.th-event--request > .pi {
  color: var(--p-orange-500, #f97316);
}
.th-event--granted > .pi {
  color: var(--p-green-500, #22c55e);
}
.th-event--declined > .pi {
  color: var(--text-color-secondary);
}
.th-request {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.8rem;
  padding: 0.85rem 1rem;
  border-top: 1px solid color-mix(in srgb, var(--p-orange-500, #f97316) 35%, var(--surface-border));
  background: color-mix(in srgb, var(--p-orange-500, #f97316) 9%, var(--surface-card));
}
.th-request__text {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
  min-width: 14rem;
}
.th-request__text small {
  color: var(--text-color-secondary);
}
.th-request__actions {
  display: flex;
  gap: 0.5rem;
}
.th-compose {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.7rem 0.8rem;
  border-top: 1px solid var(--surface-border);
}
.th-input {
  flex: 1;
  min-width: 0;
  max-height: 9rem;
  border-radius: 18px;
  overflow-y: auto !important;
}
.th-send {
  flex: none;
}
@media (max-width: 899px) {
  .th-back {
    display: inline-flex;
  }
  .th-request__actions {
    width: 100%;
  }
  .th-request__actions :deep(.p-button) {
    flex: 1;
  }
}
</style>
