<template>
  <div class="bc-root" :class="{ 'bc-root--dialog': inDialog }">

    <div v-if="loading" class="bc-layout">
      <Skeleton height="30rem" border-radius="18px" />
      <Skeleton height="30rem" border-radius="18px" />
    </div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="state">
      <!-- No bot: nothing can be sent -->
      <section v-if="!state.bot" class="bc-nobot">
        <span class="bc-nobot__icon"><i class="pi pi-send" /></span>
        <div>
          <h3>{{ t('broadcast.noBot.title') }}</h3>
          <p>{{ t('broadcast.noBot.text') }}</p>
        </div>
        <RouterLink :to="{ path: '/settings', hash: '#cat=telegram' }" class="bc-nobot__link">{{ t('broadcast.noBot.action') }} <i class="pi pi-arrow-right" /></RouterLink>
      </section>

      <!-- Sending / sent -->
      <section v-if="job" class="bc-card bc-progress" :class="`bc-progress--${job.state}`" role="status" aria-live="polite">
        <div class="bc-progress__head">
          <span class="bc-progress__icon">
            <i :class="job.state === 'running' ? 'pi pi-spin pi-spinner' : job.failed && !job.sent ? 'pi pi-times-circle' : 'pi pi-check-circle'" />
          </span>
          <div class="flex-1 min-w-0">
            <h3>{{ job.state === 'running' ? t('broadcast.progress.sending') : t('broadcast.progress.done') }}</h3>
            <p>{{ t('broadcast.progress.counts', { sent: job.sent, total: job.total }) }}<template v-if="job.failed"> · {{ t('broadcast.progress.failed', { n: job.failed }) }}</template></p>
          </div>
          <Button v-if="job.state !== 'running'" :label="t('broadcast.progress.again')" icon="pi pi-pencil" severity="secondary" outlined size="small" @click="job = null" />
        </div>
        <div class="bc-progress__bar">
          <span class="bc-progress__ok" :style="{ width: pct(job.sent) }" />
          <span class="bc-progress__bad" :style="{ width: pct(job.failed) }" />
        </div>
        <details v-if="job.errors.length" class="bc-errors">
          <summary>{{ t('broadcast.progress.errors', { n: job.errors.length }) }}</summary>
          <ul>
            <li v-for="(e, i) in job.errors" :key="i"><b>{{ e.name }}</b><span dir="ltr">{{ e.error }}</span></li>
          </ul>
        </details>
      </section>

      <div v-else class="bc-layout">
        <!-- Compose -->
        <div class="bc-compose">
          <!-- 1. Who -->
          <section class="bc-card">
            <header class="bc-step"><span class="bc-step__n">1</span>{{ t('broadcast.audience.title') }}</header>
            <div class="bc-audience" role="radiogroup" :aria-label="t('broadcast.audience.title')">
              <button
                v-for="a in audiences"
                :key="a.key"
                type="button"
                role="radio"
                class="bc-aud"
                :class="{ 'bc-aud--on': audience === a.key }"
                :aria-checked="audience === a.key"
                :disabled="!state.counts[a.key]"
                @click="audience = a.key"
              >
                <i :class="a.icon" class="bc-aud__icon" />
                <span class="bc-aud__label">{{ t(`broadcast.audience.${a.key}`) }}</span>
                <span class="bc-aud__count">{{ state.counts[a.key].toLocaleString() }}</span>
              </button>
            </div>
            <p class="bc-hint"><i class="pi pi-info-circle" />{{ t('broadcast.audience.hint') }}</p>

            <!-- The users it reaches: seen before sending, and any of them left out -->
            <template v-if="audience">
              <button type="button" class="bc-who" :aria-expanded="showRecipients" @click="showRecipients = !showRecipients">
                <i class="pi pi-users" />
                <span>{{ t('broadcast.recipients.title') }}</span>
                <span class="bc-who__n">{{ checkedIds.length.toLocaleString() }} / {{ recipientList.length.toLocaleString() }}</span>
                <i class="pi bc-who__chev" :class="showRecipients ? 'pi-chevron-up' : 'pi-chevron-down'" />
              </button>
              <RecipientList v-if="showRecipients" v-model="checkedIds" :users="recipientList" :loading="recipientsLoading" />
            </template>
          </section>

          <!-- 2. What -->
          <section class="bc-card">
            <header class="bc-step">
              <span class="bc-step__n">2</span>{{ t('broadcast.message.title') }}
              <SelectButton v-model="format" :options="formats" option-label="label" option-value="value" :allow-empty="false" size="small" class="bc-format" />
            </header>

            <div v-if="format !== 'plain'" class="bc-toolbar" role="toolbar" :aria-label="t('broadcast.message.toolbar')">
              <button v-for="b in toolbar" :key="b.key" type="button" class="bc-tool" :title="t(`broadcast.tool.${b.key}`)" :aria-label="t(`broadcast.tool.${b.key}`)" @click="apply(b.key)">
                <i v-if="b.icon" :class="b.icon" /><span v-else :class="b.cls">{{ b.text }}</span>
              </button>
            </div>
            <Textarea
              ref="textEl"
              v-model="text"
              auto-resize
              rows="7"
              class="bc-text"
              :class="{ 'bc-text--mono': format === 'html' }"
              :placeholder="t(`broadcast.message.placeholder.${format}`)"
              :aria-label="t('broadcast.message.title')"
            />
            <div class="bc-meta">
              <span class="bc-help">{{ t(`broadcast.message.help.${format}`) }}</span>
              <span class="bc-len" :class="{ 'bc-len--over': overLimit }">{{ length.toLocaleString() }} / {{ limit.toLocaleString() }}</span>
            </div>
          </section>

          <!-- 3. Image and options -->
          <section class="bc-card">
            <header class="bc-step"><span class="bc-step__n">3</span>{{ t('broadcast.extra.title') }}</header>
            <div v-if="!image" class="bc-drop" :class="{ 'bc-drop--over': dragging }" tabindex="0" role="button" @click="fileEl?.click()" @keydown.enter.prevent="fileEl?.click()" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="onDrop">
              <i class="pi pi-image" />
              <span>{{ t('broadcast.extra.addImage') }}</span>
              <small>{{ t('broadcast.extra.imageHint') }}</small>
            </div>
            <div v-else class="bc-image">
              <img :src="imageUrl" alt="" />
              <div class="bc-image__info">
                <b dir="ltr">{{ image.name }}</b>
                <span>{{ size(image.size) }}</span>
              </div>
              <Button icon="pi pi-trash" severity="danger" text rounded :aria-label="t('broadcast.extra.removeImage')" @click="setImage(null)" />
            </div>
            <input ref="fileEl" type="file" :accept="IMAGE_TYPES.join(',')" hidden @change="onPick" />
            <p v-if="imageError" class="bc-error"><i class="pi pi-exclamation-triangle" />{{ imageError }}</p>

            <label class="bc-option">
              <ToggleSwitch v-model="addUsage" input-id="bc-usage" />
              <span>
                <b>{{ t('broadcast.extra.usage') }}</b>
                <small>{{ t('broadcast.extra.usageHint') }}</small>
              </span>
            </label>
          </section>
        </div>

        <!-- Preview -->
        <aside class="bc-preview" :aria-label="t('broadcast.preview.title')">
          <div class="bc-phone">
            <div class="bc-phone__bar">
              <span class="bc-phone__avatar"><i class="pi pi-send" /></span>
              <div>
                <b>{{ state.bot_username ? `@${state.bot_username}` : t('broadcast.preview.bot') }}</b>
                <small>{{ t('broadcast.preview.botLabel') }}</small>
              </div>
            </div>
            <div class="bc-phone__chat">
              <div v-if="text.trim() || imageUrl" class="bc-bubble">
                <img v-if="imageUrl" :src="imageUrl" alt="" class="bc-bubble__img" />
                <!-- eslint-disable-next-line vue/no-v-html -- the panel's own output: Telegram's tags only, everything else escaped -->
                <div v-if="previewHtml" class="bc-bubble__text" dir="auto" v-html="previewHtml" />
                <div v-if="addUsage" class="bc-bubble__usage"><i class="pi pi-chart-bar" />{{ t('broadcast.preview.usage') }}</div>
                <div v-if="addUsage" class="bc-bubble__buttons">
                  <span><IconText :text="t('broadcast.preview.buttonUsage')" /></span>
                  <span><IconText :text="t('broadcast.preview.buttonLink')" /></span>
                </div>
                <span class="bc-bubble__time">{{ now }}</span>
              </div>
              <p v-else class="bc-phone__empty"><i class="pi pi-comment" />{{ t('broadcast.preview.empty') }}</p>
            </div>
          </div>
          <p v-if="previewError" class="bc-error"><i class="pi pi-exclamation-triangle" />{{ previewError }}</p>
        </aside>
      </div>

      <!-- Send -->
      <div v-if="!job" class="bc-sendbar">
        <span class="bc-sendbar__who">
          <i class="pi pi-users" />
          <span v-if="audience">{{ t('broadcast.send.to', { n: recipients }, recipients) }}</span>
          <span v-else>{{ t('broadcast.send.choose') }}</span>
        </span>
        <Button :label="t('broadcast.send.button')" icon="pi pi-send" :disabled="!canSend" :loading="sending" class="bc-sendbar__btn" @click="confirmVisible = true" />
      </div>
    </template>

    <Dialog v-model:visible="confirmVisible" modal :draggable="false" :header="t('broadcast.confirm.title')" :style="{ width: '26rem' }" :breakpoints="{ '575px': 'calc(100vw - 2rem)' }">
      <p class="bc-confirm">{{ t('broadcast.confirm.text', { n: recipients, audience: audience ? t(`broadcast.audience.${audience}`) : '' }, recipients) }}</p>
      <template #footer>
        <Button :label="t('common.cancel')" severity="secondary" text @click="confirmVisible = false" />
        <Button :label="t('broadcast.send.button')" icon="pi pi-send" :loading="sending" @click="send" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Skeleton from 'primevue/skeleton'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { liveWatch, type Subscription } from '@/core/live/live'
import { IMAGE_TYPES, broadcastApi, type Audience, type BroadcastJob, type BroadcastState, type MessageFormat, type Recipient } from '@/features/broadcast/api'
import RecipientList from '@/features/broadcast/components/RecipientList.vue'
import IconText from '@/shared/components/IconText.vue'

/**
 * The whole "send a message" form: audience, text, image, preview and the sending's progress. The page shows it, and the
 * users page in a dialog for the users selected there (``ids``).
 */
const props = withDefaults(defineProps<{ ids?: number[]; inDialog?: boolean }>(), { ids: () => [], inDialog: false })
const emit = defineEmits<{ sent: [job: BroadcastJob] }>()

const { t } = useI18n()
const toast = useToast()

const selectedIds = computed(() => props.ids.filter((x) => Number.isInteger(x) && x > 0))

const loading = ref(true)
const loadError = ref('')
const state = ref<BroadcastState | null>(null)
const audience = ref<Audience | null>(null)
const format = ref<MessageFormat>('markdown')
const text = ref('')
const addUsage = ref(true)
const image = ref<File | null>(null)
const imageUrl = ref('')
const imageError = ref('')
const dragging = ref(false)
const previewHtml = ref('')
const previewError = ref('')
const length = ref(0)
const sending = ref(false)
const confirmVisible = ref(false)
const job = ref<BroadcastJob | null>(null)
const textEl = ref<{ $el: HTMLTextAreaElement } | null>(null)
const fileEl = ref<HTMLInputElement | null>(null)
let feed: Subscription | null = null

const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const formats = computed(() => [
  { label: t('broadcast.format.plain'), value: 'plain' },
  { label: 'Markdown', value: 'markdown' },
  { label: 'HTML', value: 'html' },
])

const audiences = computed(() => {
  const list: { key: Audience; icon: string }[] = [
    { key: 'all', icon: 'pi pi-users' },
    { key: 'active', icon: 'pi pi-bolt' },
    { key: 'expired', icon: 'pi pi-hourglass' },
    { key: 'offline_1h', icon: 'pi pi-clock' },
    { key: 'offline_1d', icon: 'pi pi-calendar' },
    { key: 'offline_1w', icon: 'pi pi-calendar-times' },
  ]
  return selectedIds.value.length ? [{ key: 'selected' as Audience, icon: 'pi pi-check-square' }, ...list] : list
})

// The users of the chosen audience, and the ones that get it (all at first; unchecked ones are left out)
const recipientList = ref<Recipient[]>([])
const checkedIds = ref<number[]>([])
const recipientsLoading = ref(false)
const showRecipients = ref(true)
const recipients = computed(() => checkedIds.value.length)
let recipientsSeq = 0

watch(audience, async (next) => {
  const seq = ++recipientsSeq
  recipientList.value = []
  checkedIds.value = []
  if (!next) return
  recipientsLoading.value = true
  try {
    const users = await broadcastApi.recipients(next, selectedIds.value)
    if (seq !== recipientsSeq) return // another audience was chosen meanwhile
    recipientList.value = users
    checkedIds.value = users.map((u) => u.id)
  } catch (err) {
    toast.add({ severity: 'error', summary: t('broadcast.recipients.failed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    if (seq === recipientsSeq) recipientsLoading.value = false
  }
})
// A photo's caption is shorter than a message: past it the photo goes first and the text after it.
const limit = computed(() => state.value?.limits.text ?? 4096)
const overLimit = computed(() => length.value > limit.value)
const canSend = computed(() => Boolean(state.value?.bot && audience.value && recipients.value && (text.value.trim() || image.value) && !overLimit.value))

// ---------------------------------------------------------------------------------------------- toolbar

type Tool = 'bold' | 'italic' | 'underline' | 'strike' | 'spoiler' | 'code' | 'pre' | 'link' | 'quote' | 'list'
const toolbar: { key: Tool; icon?: string; text?: string; cls?: string }[] = [
  { key: 'bold', text: 'B', cls: 'bc-tool__b' },
  { key: 'italic', text: 'I', cls: 'bc-tool__i' },
  { key: 'underline', text: 'U', cls: 'bc-tool__u' },
  { key: 'strike', text: 'S', cls: 'bc-tool__s' },
  { key: 'spoiler', icon: 'pi pi-eye-slash' },
  { key: 'code', icon: 'pi pi-code' },
  { key: 'pre', icon: 'pi pi-file' },
  { key: 'link', icon: 'pi pi-link' },
  { key: 'quote', icon: 'pi pi-comment' },
  { key: 'list', icon: 'pi pi-list' },
]

const MARKS: Record<'markdown' | 'html', Record<Tool, [string, string]>> = {
  markdown: {
    bold: ['**', '**'],
    italic: ['_', '_'],
    underline: ['__', '__'],
    strike: ['~~', '~~'],
    spoiler: ['||', '||'],
    code: ['`', '`'],
    pre: ['```\n', '\n```'],
    link: ['[', '](https://)'],
    quote: ['> ', ''],
    list: ['- ', ''],
  },
  html: {
    bold: ['<b>', '</b>'],
    italic: ['<i>', '</i>'],
    underline: ['<u>', '</u>'],
    strike: ['<s>', '</s>'],
    spoiler: ['<tg-spoiler>', '</tg-spoiler>'],
    code: ['<code>', '</code>'],
    pre: ['<pre>', '</pre>'],
    link: ['<a href="https://">', '</a>'],
    quote: ['<blockquote>', '</blockquote>'],
    list: ['• ', ''],
  },
}

/** Wrap the selection (or insert at the cursor) with the format's marks; the selection stays on the text. */
function apply(tool: Tool) {
  if (format.value === 'plain') return
  const el = textEl.value?.$el
  const [open, close] = MARKS[format.value][tool]
  const start = el?.selectionStart ?? text.value.length
  const end = el?.selectionEnd ?? text.value.length
  const picked = text.value.slice(start, end)
  const lineStart = tool === 'quote' || tool === 'list'
  const prefix = lineStart && start > 0 && text.value[start - 1] !== '\n' ? '\n' : ''
  text.value = text.value.slice(0, start) + prefix + open + picked + close + text.value.slice(end)
  const cursor = start + prefix.length + open.length
  requestAnimationFrame(() => {
    el?.focus()
    el?.setSelectionRange(cursor, cursor + picked.length)
  })
}

// ---------------------------------------------------------------------------------------------- image

function size(bytes: number) {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`
}

function setImage(file: File | null) {
  imageError.value = ''
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
  imageUrl.value = ''
  image.value = null
  if (!file) return
  if (!IMAGE_TYPES.includes(file.type)) {
    imageError.value = t('broadcast.extra.badType')
    return
  }
  if (state.value && file.size > state.value.limits.image_bytes) {
    imageError.value = t('broadcast.extra.tooBig')
    return
  }
  image.value = file
  imageUrl.value = URL.createObjectURL(file)
}

function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  setImage(input.files?.[0] ?? null)
  input.value = ''
}

function onDrop(e: DragEvent) {
  dragging.value = false
  setImage(e.dataTransfer?.files?.[0] ?? null)
}

// ---------------------------------------------------------------------------------------------- preview

let previewTimer: number | undefined
let previewSeq = 0
watch([text, format], () => {
  window.clearTimeout(previewTimer)
  previewTimer = window.setTimeout(refreshPreview, 250)
})

async function refreshPreview() {
  const seq = ++previewSeq
  if (!text.value.trim()) {
    previewHtml.value = ''
    length.value = 0
    return
  }
  try {
    const res = await broadcastApi.preview(text.value, format.value)
    if (seq !== previewSeq) return // a newer edit is on its way
    previewHtml.value = res.html
    length.value = res.length
    previewError.value = ''
  } catch (err) {
    previewError.value = apiErrorMessage(err)
  }
}

// ---------------------------------------------------------------------------------------------- send

function pct(n: number) {
  return job.value && job.value.total ? `${(n / job.value.total) * 100}%` : '0%'
}

async function send() {
  if (!audience.value) return
  sending.value = true
  try {
    // Everyone of the audience: by its name (who matches it when sending); some left out: exactly the checked ones
    const everyone = checkedIds.value.length === recipientList.value.length && audience.value !== 'selected'
    job.value = await broadcastApi.send({
      text: text.value,
      format: format.value,
      audience: everyone ? audience.value : 'selected',
      ids: everyone ? [] : checkedIds.value,
      addUsage: addUsage.value,
      image: image.value,
    })
    confirmVisible.value = false
    emit('sent', job.value)
    follow(job.value.id)
  } catch (err) {
    toast.add({ severity: 'error', summary: t('broadcast.send.failed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    sending.value = false
  }
}

function follow(id: string) {
  feed?.stop()
  feed = liveWatch<BroadcastJob>(`broadcast/${id}/`, {
    intervalMs: 1500,
    tags: [`broadcast:${id}`],
    onData: (next) => {
      job.value = next
      if (next.state !== 'running') feed?.stop()
    },
    pauseWhenHidden: false,
  })
}

onMounted(async () => {
  try {
    state.value = await broadcastApi.state(selectedIds.value)
    if (selectedIds.value.length && state.value.counts.selected) audience.value = 'selected'
  } catch (err) {
    loadError.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  feed?.stop()
  window.clearTimeout(previewTimer)
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
})
</script>

<style scoped>
.bc-root {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
/* In a dialog: the preview beside the form from a narrower width, the send bar at the dialog's bottom */
.bc-root--dialog .bc-layout {
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 20rem);
}
.bc-root--dialog .bc-sendbar {
  bottom: 0;
}
.bc-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 24rem);
  gap: 1rem;
  align-items: start;
}
.bc-compose {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}
.bc-card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 18px;
  padding: 1.1rem 1.15rem;
}
.bc-step {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.9rem;
  font-weight: 700;
  font-size: 1rem;
  flex-wrap: wrap;
}
.bc-step__n {
  display: grid;
  place-items: center;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-primary-color) 15%, transparent);
  color: var(--p-primary-color);
  font-size: 0.85rem;
}
.bc-format {
  margin-inline-start: auto;
}

/* audience */
.bc-audience {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
  gap: 0.6rem;
}
.bc-aud {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  padding: 0.8rem 0.85rem;
  border-radius: 14px;
  border: 1.5px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  text-align: start;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s,
    transform 0.1s;
}
.bc-aud:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--p-primary-color) 55%, transparent);
}
.bc-aud:active:not(:disabled) {
  transform: scale(0.98);
}
.bc-aud:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.bc-aud--on {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 9%, var(--p-content-background));
}
.bc-aud:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.bc-aud__icon {
  color: var(--p-primary-color);
  font-size: 1.05rem;
}
.bc-aud__label {
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1.3;
}
.bc-aud__count {
  font-size: 1.25rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.bc-who {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  margin-top: 0.9rem;
  padding: 0.55rem 0.75rem;
  border: 0;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
  color: var(--p-text-color);
  font-weight: 600;
  font-size: 0.88rem;
  cursor: pointer;
  text-align: start;
}
.bc-who:focus-visible {
  outline: 2px solid var(--p-primary-color);
}
.bc-who__n {
  margin-inline-start: auto;
  font-variant-numeric: tabular-nums;
  color: var(--p-primary-color);
}
.bc-who__chev {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.bc-hint,
.bc-help {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0.75rem 0 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

/* editor */
.bc-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding: 0.35rem;
  margin-bottom: 0.5rem;
  border-radius: 12px;
  background: var(--p-content-hover-background);
}
.bc-tool {
  display: grid;
  place-items: center;
  min-width: 2.2rem;
  height: 2.2rem;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--p-text-color);
  cursor: pointer;
  font-size: 0.95rem;
}
.bc-tool:hover,
.bc-tool:focus-visible {
  background: var(--p-content-background);
  outline: none;
  box-shadow: 0 0 0 1px var(--p-content-border-color);
}
.bc-tool__b {
  font-weight: 800;
}
.bc-tool__i {
  font-style: italic;
  font-family: serif;
}
.bc-tool__u {
  text-decoration: underline;
}
.bc-tool__s {
  text-decoration: line-through;
}
.bc-text {
  width: 100%;
  min-height: 9rem;
  font-size: 0.95rem;
  line-height: 1.6;
}
.bc-text--mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85rem;
}
.bc-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.bc-help {
  margin: 0.5rem 0 0;
}
.bc-len {
  margin-top: 0.5rem;
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.bc-len--over {
  color: var(--p-red-500, #ef4444);
  font-weight: 700;
}

/* image */
.bc-drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  padding: 1.3rem;
  border: 2px dashed var(--p-content-border-color);
  border-radius: 14px;
  color: var(--p-text-muted-color);
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.bc-drop i {
  font-size: 1.6rem;
  color: var(--p-primary-color);
}
.bc-drop span {
  font-weight: 600;
  color: var(--p-text-color);
}
.bc-drop:hover,
.bc-drop:focus-visible,
.bc-drop--over {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 6%, transparent);
  outline: none;
}
.bc-image {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
}
.bc-image img {
  width: 4rem;
  height: 4rem;
  object-fit: cover;
  border-radius: 10px;
}
.bc-image__info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
  font-size: 0.85rem;
}
.bc-image__info b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bc-image__info span {
  color: var(--p-text-muted-color);
}
.bc-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-top: 1rem;
  cursor: pointer;
}
.bc-option span {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.bc-option small {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}
.bc-error {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0.6rem 0 0;
  font-size: 0.82rem;
  color: var(--p-red-500, #ef4444);
}

/* preview: a Telegram chat */
.bc-preview {
  position: sticky;
  top: 1rem;
}
.bc-phone {
  border-radius: 26px;
  overflow: hidden;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  box-shadow: 0 20px 45px -25px color-mix(in srgb, var(--p-primary-color) 45%, transparent);
}
.bc-phone__bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.75rem 0.9rem;
  border-bottom: 1px solid var(--p-content-border-color);
}
.bc-phone__bar div {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.bc-phone__bar small {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}
.bc-phone__avatar {
  display: grid;
  place-items: center;
  width: 2.3rem;
  height: 2.3rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #2aabee, #229ed9);
  color: #fff;
}
.bc-phone__chat {
  min-height: 18rem;
  padding: 1rem 0.85rem;
  background:
    radial-gradient(circle at 20% 20%, color-mix(in srgb, #2aabee 10%, transparent), transparent 45%),
    radial-gradient(circle at 80% 70%, color-mix(in srgb, #7c3aed 9%, transparent), transparent 45%),
    var(--p-content-hover-background);
}
.bc-phone__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  margin: 5rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  text-align: center;
}
.bc-phone__empty i {
  font-size: 1.6rem;
}
.bc-bubble {
  position: relative;
  max-width: 92%;
  padding: 0.5rem 0.65rem 1.25rem;
  border-radius: 14px 14px 14px 4px;
  background: var(--p-content-background);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  animation: bc-in 0.2s ease-out;
}
.bc-bubble__img {
  display: block;
  width: calc(100% + 1.3rem);
  margin: -0.5rem -0.65rem 0.5rem;
  max-height: 16rem;
  object-fit: cover;
}
.bc-bubble__text {
  font-size: 0.9rem;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.bc-bubble__text :deep(a) {
  color: #2aabee;
}
.bc-bubble__text :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.85em;
  padding: 0.05rem 0.25rem;
  border-radius: 4px;
  background: var(--p-content-hover-background);
}
.bc-bubble__text :deep(pre) {
  margin: 0.3rem 0;
  padding: 0.5rem;
  border-radius: 8px;
  background: var(--p-content-hover-background);
  overflow-x: auto;
}
.bc-bubble__text :deep(pre code) {
  padding: 0;
  background: none;
}
.bc-bubble__text :deep(blockquote) {
  margin: 0.3rem 0;
  padding: 0.15rem 0.6rem;
  border-inline-start: 3px solid #2aabee;
  border-radius: 4px;
  background: color-mix(in srgb, #2aabee 9%, transparent);
}
.bc-bubble__text :deep(tg-spoiler),
.bc-bubble__text :deep(.tg-spoiler) {
  filter: blur(4px);
  transition: filter 0.2s;
}
.bc-bubble__text :deep(tg-spoiler:hover),
.bc-bubble__text :deep(.tg-spoiler:hover) {
  filter: none;
}
.bc-bubble__usage {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.5rem;
  padding-top: 0.45rem;
  border-top: 1px dashed var(--p-content-border-color);
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.bc-bubble__buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.3rem;
  margin-top: 0.45rem;
}
.bc-bubble__buttons span {
  padding: 0.35rem;
  border-radius: 8px;
  background: color-mix(in srgb, #2aabee 14%, transparent);
  color: #1e88c7;
  font-size: 0.75rem;
  font-weight: 600;
  text-align: center;
}
.bc-bubble__time {
  position: absolute;
  inset-inline-end: 0.55rem;
  bottom: 0.3rem;
  font-size: 0.68rem;
  color: var(--p-text-muted-color);
}

/* no bot */
.bc-nobot {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.1rem;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--p-amber-500, #f59e0b) 45%, transparent);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 9%, var(--p-content-background));
  flex-wrap: wrap;
}
.bc-nobot__icon {
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 20%, transparent);
  color: var(--p-amber-600, #d97706);
}
.bc-nobot h3 {
  margin: 0;
  font-size: 1rem;
}
.bc-nobot p {
  margin: 0.2rem 0 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.bc-nobot__link {
  margin-inline-start: auto;
  font-weight: 600;
  color: var(--p-primary-color);
  text-decoration: none;
  white-space: nowrap;
}

/* progress */
.bc-progress__head {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}
.bc-progress__head h3 {
  margin: 0;
  font-size: 1.05rem;
}
.bc-progress__head p {
  margin: 0.15rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
}
.bc-progress__icon {
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 14px;
  font-size: 1.4rem;
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
  color: var(--p-primary-color);
}
.bc-progress--done .bc-progress__icon {
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 15%, transparent);
  color: var(--p-green-600, #16a34a);
}
.bc-progress__bar {
  display: flex;
  height: 0.6rem;
  margin-top: 1rem;
  border-radius: 999px;
  overflow: hidden;
  background: var(--p-content-hover-background);
}
.bc-progress__ok {
  background: var(--p-green-500, #22c55e);
  transition: width 0.4s ease;
}
.bc-progress__bad {
  background: var(--p-red-400, #f87171);
  transition: width 0.4s ease;
}
.bc-errors {
  margin-top: 0.9rem;
  font-size: 0.85rem;
}
.bc-errors summary {
  cursor: pointer;
  color: var(--p-red-500, #ef4444);
  font-weight: 600;
}
.bc-errors ul {
  margin: 0.5rem 0 0;
  padding: 0;
  list-style: none;
  max-height: 14rem;
  overflow: auto;
}
.bc-errors li {
  display: flex;
  gap: 0.6rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
}
.bc-errors li span {
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}

/* send bar */
.bc-sendbar {
  position: sticky;
  bottom: 0.75rem;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.65rem 0.75rem 0.65rem 1rem;
  border-radius: 16px;
  border: 1px solid var(--p-content-border-color);
  background: color-mix(in srgb, var(--p-content-background) 88%, transparent);
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 30px -15px rgba(0, 0, 0, 0.35);
}
.bc-sendbar__who {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  font-weight: 600;
  font-size: 0.9rem;
}
.bc-sendbar__btn {
  margin-inline-start: auto;
}
.bc-confirm {
  margin: 0;
  line-height: 1.6;
}

@keyframes bc-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}

@media (max-width: 991px) {
  .bc-layout,
  .bc-root--dialog .bc-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .bc-preview {
    position: static;
  }
}
@media (max-width: 575px) {
  .bc-card {
    padding: 0.95rem;
    border-radius: 16px;
  }
  .bc-audience {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .bc-format {
    margin-inline-start: 0;
    width: 100%;
  }
  .bc-sendbar {
    bottom: 0.5rem;
  }
  .bc-sendbar__btn {
    flex-shrink: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .bc-bubble,
  .bc-progress__ok,
  .bc-progress__bad {
    animation: none;
    transition: none;
  }
}
</style>
