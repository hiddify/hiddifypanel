<template>
  <div class="sess">
    <!-- Connect -->
    <section v-if="phase === 'idle' || phase === 'connecting' || phase === 'hostkey'" class="sess-connect">
      <form class="sess-card" @submit.prevent="connect">
        <Select
          v-if="vault.connections.value.length"
          :model-value="null"
          :options="vault.connections.value"
          :option-label="connectionLabel"
          filter
          :filter-fields="['host', 'username']"
          :placeholder="t('ssh.savedPick', { n: vault.connections.value.length })"
          class="sess-saved"
          :disabled="phase === 'connecting'"
          @update:model-value="(c) => c && useSaved(c, true)"
        >
          <template #option="{ option }">
            <div class="sess-saved__opt">
              <i :class="option.auth === 'key' ? 'pi pi-key' : 'pi pi-lock'" />
              <span class="sess-saved__name" dir="ltr">{{ connectionLabel(option) }}</span>
              <small class="sess-muted">{{ ago(option.lastUsed) }}</small>
              <Button icon="pi pi-pencil" text rounded size="small" severity="secondary" :aria-label="t('ssh.edit')" @click.stop="useSaved(option, false)" />
              <Button icon="pi pi-trash" text rounded size="small" severity="danger" :aria-label="t('ssh.forget')" @click.stop="vault.removeConnection(option.id)" />
            </div>
          </template>
        </Select>

        <div class="sess-row">
          <div class="sess-field sess-field--grow">
            <label :for="`h-${uid}`">{{ t('ssh.host') }}</label>
            <InputText :id="`h-${uid}`" v-model.trim="form.host" placeholder="203.0.113.10" autocomplete="off" autocapitalize="off" spellcheck="false" dir="ltr" required />
          </div>
          <div class="sess-field sess-field--port">
            <label :for="`p-${uid}`">{{ t('ssh.port') }}</label>
            <InputNumber v-model="form.port" :input-id="`p-${uid}`" :min="1" :max="65535" :use-grouping="false" />
          </div>
        </div>
        <div class="sess-field">
          <label :for="`u-${uid}`">{{ t('ssh.username') }}</label>
          <InputText :id="`u-${uid}`" v-model.trim="form.username" placeholder="root" autocomplete="off" autocapitalize="off" spellcheck="false" dir="ltr" required />
        </div>

        <SelectButton v-model="authKind" :options="authOptions" option-label="label" option-value="value" :allow-empty="false" class="sess-auth" />

        <div v-if="authKind === 'password'" class="sess-field">
          <label :for="`pw-${uid}`">{{ t('ssh.password') }}</label>
          <Password v-model="form.password" :input-id="`pw-${uid}`" :feedback="false" toggle-mask fluid autocomplete="off" />
        </div>
        <template v-else>
          <div class="sess-field">
            <label>{{ t('ssh.privateKey') }}</label>
            <Select v-model="keyChoice" :options="keyOptions" option-label="label" option-value="value" filter :filter-fields="['label']" class="w-full">
              <template #option="{ option }">
                <div class="sess-saved__opt">
                  <i :class="option.value === NEW_KEY ? 'pi pi-plus' : 'pi pi-key'" />
                  <span class="sess-saved__name">{{ option.label }}</span>
                  <Button v-if="option.value !== NEW_KEY" icon="pi pi-trash" text rounded size="small" severity="danger" :aria-label="t('ssh.forget')" @click.stop="forgetKey(option.value)" />
                </div>
              </template>
            </Select>
          </div>
          <template v-if="keyChoice === NEW_KEY">
            <div class="sess-field">
              <div class="sess-label-row">
                <label :for="`k-${uid}`">{{ t('ssh.keyText') }}</label>
                <Button :label="t('ssh.chooseFile')" icon="pi pi-upload" text size="small" @click="keyFile?.click()" />
                <input ref="keyFile" type="file" class="hidden" @change="loadKey" />
              </div>
              <Textarea :id="`k-${uid}`" v-model="form.privateKey" rows="4" class="sess-mono" spellcheck="false" placeholder="-----BEGIN OPENSSH PRIVATE KEY-----" dir="ltr" />
            </div>
            <div class="sess-row">
              <div class="sess-field sess-field--grow">
                <label :for="`kn-${uid}`">{{ t('ssh.keyName') }}</label>
                <InputText :id="`kn-${uid}`" v-model.trim="form.keyName" :placeholder="t('ssh.keyNamePlaceholder')" />
              </div>
              <div class="sess-field sess-field--grow">
                <label :for="`pp-${uid}`">{{ t('ssh.passphrase') }}</label>
                <Password v-model="form.passphrase" :input-id="`pp-${uid}`" :feedback="false" toggle-mask fluid autocomplete="off" :placeholder="t('ssh.optional')" />
              </div>
            </div>
          </template>
        </template>

        <label class="sess-save" :class="{ 'sess-save--off': !vault.state.available }">
          <Checkbox v-model="saveIt" binary :disabled="!vault.state.available" />
          <span
            >{{ t('ssh.saveIt') }}<small v-if="!vault.state.available">{{ t('ssh.cannotSave') }}</small></span
          >
        </label>

        <Message v-if="vault.state.error" severity="warn" :closable="false">{{ t('ssh.savedUnreadable') }}</Message>
        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
        <Button type="submit" :label="t('ssh.connect')" icon="pi pi-sign-in" :loading="phase === 'connecting'" :disabled="!canConnect" class="w-full" />
        <p class="sess-note">
          <i class="pi pi-shield" />
          {{ t(saveIt && vault.state.available ? 'ssh.noteSaved' : 'ssh.note') }}
        </p>
      </form>
    </section>

    <!-- Terminal -->
    <section v-show="phase === 'ready' || phase === 'closed'" class="sess-live">
      <header class="sess-bar">
        <span class="sess-dot" :class="phase === 'ready' ? 'sess-dot--on' : 'sess-dot--off'" />
        <b class="sess-target" dir="ltr">{{ title }}</b>
        <Tag v-if="protocol" :value="protocol" severity="secondary" />
        <span class="sess-grow" />
        <Button v-if="linkToken" icon="pi pi-link" :label="narrow ? undefined : t('ssh.copyLink')" text size="small" v-tooltip.bottom="t('ssh.copyLinkHint')" @click="emit('copy-link')" />
        <Button v-if="filesAvailable" :icon="filesOpen ? 'pi pi-folder-open' : 'pi pi-folder'" :label="narrow ? undefined : t('ssh.files')" text size="small" @click="toggleFiles" />
        <Button v-if="phase === 'closed'" icon="pi pi-refresh" :label="narrow ? undefined : t('ssh.reconnect')" text size="small" @click="reconnect" />
        <Button icon="pi pi-power-off" :label="narrow ? undefined : t('ssh.disconnect')" text size="small" severity="danger" @click="disconnect" />
      </header>

      <Message v-if="phase === 'closed'" severity="warn" :closable="false">
        {{ exitStatus !== null ? t('ssh.exited', { status: exitStatus }) : error || t('ssh.closed') }}
      </Message>

      <!-- A phone: the terminal or the files, the whole width each -->
      <div v-if="narrow && filesAvailable" class="sess-switch" role="tablist">
        <button type="button" role="tab" :class="{ 'sess-switch--on': !filesOpen }" :aria-selected="!filesOpen" @click="filesOpen = false"><i class="pi pi-desktop" /> {{ t('ssh.terminal') }}</button>
        <button type="button" role="tab" :class="{ 'sess-switch--on': filesOpen }" :aria-selected="filesOpen" @click="filesOpen = true"><i class="pi pi-folder" /> {{ t('ssh.files') }}</button>
      </div>

      <div class="sess-body" :class="{ 'sess-body--files': filesOpen && !narrow }" :style="filesOpen && !narrow ? { '--files-width': `${filesWidth}px` } : undefined">
        <div v-show="!(narrow && filesOpen)" ref="terminalBox" class="sess-terminal" />

        <!-- The keys a phone keyboard lacks, over the terminal: a tap sends one, holding an arrow repeats it -->
        <div v-if="touch && padShown && phase === 'ready' && !(narrow && filesOpen)" class="pad" role="toolbar" :aria-label="t('ssh.keyPad')">
          <div class="pad__top">
            <button type="button" class="pad__key" @pointerdown.prevent="hold(ESC)" @pointerup="release" @pointerleave="release" @pointercancel="release">Esc</button>
            <button type="button" class="pad__key" @pointerdown.prevent="hold(TAB)" @pointerup="release" @pointerleave="release" @pointercancel="release">Tab</button>
            <button type="button" class="pad__key pad__key--stop" @pointerdown.prevent="hold(CTRL_C)" @pointerup="release" @pointerleave="release" @pointercancel="release">Ctrl+C</button>
          </div>
          <div class="pad__dpad">
            <button
              v-for="a in ARROWS"
              :key="a.area"
              type="button"
              class="pad__key pad__arrow"
              :style="{ gridArea: a.area }"
              :aria-label="a.area"
              @pointerdown.prevent="hold(a.key, true)"
              @pointerup="release"
              @pointerleave="release"
              @pointercancel="release"
            >
              <i :class="`pi pi-chevron-${a.area}`" />
            </button>
            <span class="pad__hub" />
          </div>
          <button type="button" class="pad__close" :aria-label="t('common.close')" @pointerdown.prevent @click="padShown = false"><i class="pi pi-times" /></button>
        </div>
        <div
          v-if="filesOpen && !narrow"
          class="sess-split"
          role="separator"
          aria-orientation="vertical"
          :aria-label="t('ssh.resize')"
          tabindex="0"
          @pointerdown="startResize"
          @dblclick="filesWidth = FILES_DEFAULT"
          @keydown.left.prevent="filesWidth = clampWidth(filesWidth + 24)"
          @keydown.right.prevent="filesWidth = clampWidth(filesWidth - 24)"
        />
        <aside v-if="filesOpen" class="sess-files">
          <SshFiles :list="list" :read="read" :write="write" :ops="{ create, mkdir, upload, extract }" :home="home" />
        </aside>
      </div>

      <div v-if="touch && !(narrow && filesOpen)" class="sess-keys" role="toolbar" :aria-label="t('ssh.keys')">
        <button
          type="button"
          class="sess-key sess-key--pad"
          :class="{ 'sess-key--on': padShown }"
          :aria-pressed="padShown"
          :aria-label="t('ssh.keyPad')"
          @pointerdown.prevent
          @click="padShown = !padShown"
        >
          <i class="pi pi-th-large" />
        </button>
        <button
          v-for="k in KEYS"
          :key="k.label"
          type="button"
          class="sess-key"
          :class="{ 'sess-key--on': k.ctrl && ctrlArmed, 'sess-key--stop': k.stop }"
          @pointerdown.prevent
          @click="pressKey(k)"
        >
          {{ k.label }}
        </button>
      </div>

    </section>

    <Dialog :visible="phase === 'hostkey' && active" modal :closable="false" :header="hostKey?.changed ? t('ssh.keyChanged') : t('ssh.newHost')" :style="{ width: '32rem' }" :breakpoints="{ '640px': '94vw' }">
      <Message v-if="hostKey?.changed" severity="error" :closable="false" class="mb-3">{{ t('ssh.keyChangedHint') }}</Message>
      <p class="mt-0">{{ t('ssh.trustHint', { host: form.host }) }}</p>
      <div class="sess-fingerprint" dir="ltr">
        <small>{{ hostKey?.algorithm }}</small>
        <code>{{ hostKey?.fingerprint }}</code>
      </div>
      <template #footer>
        <Button :label="t('common.cancel')" text @click="cancel" />
        <Button :label="t('ssh.trust')" icon="pi pi-check" :severity="hostKey?.changed ? 'danger' : undefined" @click="trustAndConnect" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * One SSH connection (a tab of the SSH page): the connect form (saved connections and keys from the vault), then the
 * terminal, its files and the keys a phone keyboard lacks. The page runs saved commands in it through `run`.
 */
import { usePref } from '@/features/ssh/prefs'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import SshFiles from '@/features/ssh/components/SshFiles.vue'
import { lastTarget, useSsh, type SshPhase } from '@/features/ssh/useSsh'
import { useVault, type ConnectTarget, type DeepLink, type VaultConnection } from '@/features/ssh/vault'

const props = defineProps<{
  active: boolean
  initial?: ConnectTarget | null
}>()
/** `initial` without its secret (a link of another admin, or without one): the form is filled, the admin signs in. */
const emit = defineEmits<{
  title: [title: string]
  phase: [phase: SshPhase]
  link: [link: DeepLink | null]
  'copy-link': []
}>()

const { t, locale } = useI18n()
const vault = useVault()
const uid = Math.random().toString(36).slice(2, 8)
const NEW_KEY = '__new__'

const last = lastTarget()
const form = reactive({
  host: last.host ?? '',
  port: last.port ?? 22,
  username: last.username ?? 'root',
  password: '',
  privateKey: '',
  passphrase: '',
  keyName: '',
})
const authKind = ref<'password' | 'key'>('password')
const authOptions = computed(() => [
  { label: t('ssh.byPassword'), value: 'password' },
  { label: t('ssh.byKey'), value: 'key' },
])
/** The saved key to use, or NEW_KEY to paste one (named, saved with the connection). Default: the key used last. */
const keyChoice = ref<string>(NEW_KEY)
const keyOptions = computed(() => [...vault.keys.value.map((k) => ({ label: k.name, value: k.id })), { label: t('ssh.newKey'), value: NEW_KEY }])
const keyFile = ref<HTMLInputElement | null>(null)
const terminalBox = ref<HTMLElement | null>(null)
const filesOpen = ref(false)
/** Files beside the terminal on a wide screen, unless the admin hid them (remembered in this browser). */
const filesShown = usePref('files', true)

// The files panel's width: dragged at its edge (double-click: back to the default), kept in this browser.
const FILES_DEFAULT = 320
const FILES_KEY = 'hiddify.ssh.pref.filesWidth'
function clampWidth(w: number): number {
  return Math.round(Math.min(Math.max(w, 220), Math.max(260, window.innerWidth * 0.7)))
}
function storedWidth(): number {
  try {
    return clampWidth(Number(localStorage.getItem(FILES_KEY)) || FILES_DEFAULT)
  } catch {
    return FILES_DEFAULT
  }
}
const filesWidth = ref(storedWidth())
watch(filesWidth, (w) => {
  try {
    localStorage.setItem(FILES_KEY, String(w))
  } catch {
    /* not kept */
  }
  void nextTick(refit)
})

function startResize(down: PointerEvent) {
  const handle = down.currentTarget as HTMLElement
  handle.setPointerCapture(down.pointerId)
  const startX = down.clientX
  const startWidth = filesWidth.value
  const rtl = getComputedStyle(handle).direction === 'rtl'
  document.body.style.userSelect = 'none'
  const move = (e: PointerEvent) => {
    const dx = e.clientX - startX
    filesWidth.value = clampWidth(startWidth + (rtl ? dx : -dx))
  }
  const up = () => {
    handle.removeEventListener('pointermove', move)
    document.body.style.userSelect = ''
  }
  handle.addEventListener('pointermove', move)
  handle.addEventListener('pointerup', up, { once: true })
  handle.addEventListener('pointercancel', up, { once: true })
}

function toggleFiles() {
  filesOpen.value = !filesOpen.value
  if (!narrow.value) filesShown.value = filesOpen.value
}
const narrow = ref(false)
const touch = ref(false)
const ctrlArmed = ref(false)
const saveIt = ref(true)
const linkToken = ref('')
/** What the connect in progress used: saved (and sealed into a link) once it is ready. */
let attempt: ConnectTarget | null = null

let term: Terminal | null = null
let fit: FitAddon | null = null
let observer: ResizeObserver | null = null
let resizeTimer: number | undefined

const {
  phase,
  error,
  hostKey,
  protocol,
  home,
  filesAvailable,
  exitStatus,
  connect: open,
  trustAndConnect,
  cancel,
  disconnect: close,
  input,
  resize,
  list,
  read,
  write,
  create,
  mkdir,
  upload,
  extract,
  exec,
  stopExec,
} = useSsh((data) => term?.write(data))

const title = computed(() => (form.host ? `${form.username}@${form.host}${form.port !== 22 ? `:${form.port}` : ''}` : t('ssh.newTab')))
const canConnect = computed(() => {
  if (!form.host || !form.username) return false
  if (authKind.value === 'password') return !!form.password
  return keyChoice.value !== NEW_KEY || !!form.privateKey.trim()
})

watch(title, (v) => emit('title', v), { immediate: true })
watch(phase, (v) => emit('phase', v), { immediate: true })
// The last saved key is the default (once the vault is read).
watch(
  () => vault.lastKey.value?.id,
  (id) => {
    if (id && keyChoice.value === NEW_KEY && !form.privateKey) keyChoice.value = id
  },
  { immediate: true },
)

function connectionLabel(c: VaultConnection): string {
  return `${c.username}@${c.host}${c.port !== 22 ? `:${c.port}` : ''}`
}

function ago(when: number): string {
  const minutes = Math.round((when - Date.now()) / 60_000)
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  if (Math.abs(minutes) < 60) return rtf.format(minutes, 'minute')
  if (Math.abs(minutes) < 60 * 24) return rtf.format(Math.round(minutes / 60), 'hour')
  return rtf.format(Math.round(minutes / 1440), 'day')
}

function useSaved(c: VaultConnection, connectNow: boolean) {
  Object.assign(form, {
    host: c.host,
    port: c.port,
    username: c.username,
    password: c.password ?? '',
    privateKey: '',
    passphrase: '',
    keyName: '',
  })
  authKind.value = c.auth
  if (c.auth === 'key') keyChoice.value = vault.keyOf(c)?.id ?? NEW_KEY
  saveIt.value = true
  if (connectNow && canConnect.value) void connect()
}

/** A connection with its secret (a deep link): the key in it is matched to a saved one when there is one. */
function useTarget(target: ConnectTarget) {
  Object.assign(form, {
    host: target.host,
    port: target.port,
    username: target.username,
    password: target.password ?? '',
    privateKey: target.privateKey ?? '',
    passphrase: target.passphrase ?? '',
    keyName: target.keyName ?? '',
  })
  authKind.value = target.auth
  const saved = target.privateKey ? vault.keys.value.find((k) => k.privateKey.trim() === target.privateKey!.trim()) : undefined
  keyChoice.value = saved?.id ?? NEW_KEY
  void connect()
}

async function forgetKey(id: string) {
  await vault.removeKey(id)
  if (keyChoice.value === id) keyChoice.value = vault.lastKey.value?.id ?? NEW_KEY
}

async function loadKey(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  form.privateKey = await file.text()
  if (!form.keyName) form.keyName = file.name
}

/** What to connect with: the password, the chosen saved key, or the pasted one. */
function target(): ConnectTarget {
  const base = {
    host: form.host,
    port: form.port || 22,
    username: form.username,
  }
  if (authKind.value === 'password') return { ...base, auth: 'password', password: form.password }
  const saved = vault.keys.value.find((k) => k.id === keyChoice.value)
  if (saved)
    return {
      ...base,
      auth: 'key',
      privateKey: saved.privateKey,
      passphrase: saved.passphrase,
      keyId: saved.id,
      keyName: saved.name,
    }
  return {
    ...base,
    auth: 'key',
    privateKey: form.privateKey,
    passphrase: form.passphrase || undefined,
    keyName: form.keyName || `${form.username}@${form.host}`,
  }
}

async function connect() {
  attempt = target()
  await nextTick()
  ensureTerminal()
  term?.reset()
  refit()
  await open(attempt, term?.cols ?? 80, term?.rows ?? 24)
}

/** It worked: kept (with its key, named) and sealed into a link for this admin. */
async function remember(done: ConnectTarget) {
  const cipher = vault.cipher()
  // Server, port and user in the clear; only the secret is sealed (this admin's key).
  const secret = cipher
    ? await cipher.seal({
        auth: done.auth,
        password: done.password,
        privateKey: done.privateKey,
        passphrase: done.passphrase,
        keyName: done.keyName,
      })
    : ''
  linkToken.value = secret || '-'
  emit('link', {
    host: done.host,
    port: done.port,
    user: done.username,
    s: secret,
  })
  if (!saveIt.value || !vault.state.available) return
  let keyId = done.keyId
  if (done.auth === 'key') {
    if (keyId) await vault.useKey(keyId)
    else if (done.privateKey) keyId = keyChoice.value = await vault.saveKey(done.keyName ?? '', done.privateKey, done.passphrase)
  }
  await vault.saveConnection({
    host: done.host,
    port: done.port,
    username: done.username,
    auth: done.auth,
    password: done.auth === 'password' ? done.password : undefined,
    keyId,
  })
}

function reconnect() {
  close()
  void connect()
}

function disconnect() {
  close()
  filesOpen.value = false
  linkToken.value = ''
  emit('link', null)
}

/** Types a command into the terminal (the page's saved commands). */
function run(command: string): boolean {
  if (phase.value !== 'ready') return false
  input(command.endsWith('\n') ? command : `${command}\n`)
  return true
}

defineExpose({ run, exec, stopExec, phase, title, error, linkToken })

// ------------------------------------------------------------------ the terminal

/** Dark in both themes (what programs expect), the 16 ANSI colors legible on it. */
const THEME = {
  background: '#0f1419',
  foreground: '#d7dce2',
  cursor: '#f0b44c',
  selectionBackground: '#33415580',
  black: '#1c2128',
  red: '#f47067',
  green: '#8ddb8c',
  yellow: '#e0b453',
  blue: '#6cb6ff',
  magenta: '#dcbdfb',
  cyan: '#56d4dd',
  white: '#adbac7',
  brightBlack: '#636e7b',
  brightRed: '#ff938a',
  brightGreen: '#b4f1b4',
  brightYellow: '#f0ce6b',
  brightBlue: '#96d0ff',
  brightMagenta: '#eedcff',
  brightCyan: '#86e6ec',
  brightWhite: '#e6edf3',
}

function ensureTerminal() {
  if (term || !terminalBox.value) return
  term = new Terminal({
    cursorBlink: true,
    fontFamily: '"JetBrains Mono", "Cascadia Code", "Fira Code", Menlo, Consolas, "Liberation Mono", monospace',
    fontSize: narrow.value ? 13 : 14,
    scrollback: 5000,
    theme: THEME,
  })
  fit = new FitAddon()
  term.loadAddon(fit)
  term.loadAddon(new WebLinksAddon())
  term.open(terminalBox.value)
  term.onData((data) => input(applyCtrl(data)))
  observer = new ResizeObserver(() => refit())
  observer.observe(terminalBox.value)
  refit()
}

function refit() {
  if (!fit || !term || !props.active) return
  try {
    fit.fit()
  } catch {
    return // not laid out yet
  }
  window.clearTimeout(resizeTimer)
  resizeTimer = window.setTimeout(() => term && resize(term.cols, term.rows), 120)
}

interface Key {
  label: string
  send?: string
  ctrl?: boolean
  /** Stops the running program (Ctrl+C): shown apart. */
  stop?: boolean
}
const ESC: Key = { label: 'Esc', send: '\x1b' }
const TAB: Key = { label: 'Tab', send: '\t' }
const CTRL_C: Key = { label: '^C', send: '\x03', stop: true }
const ARROWS = [
  { area: 'up', key: { label: '↑', send: '\x1b[A' } },
  { area: 'left', key: { label: '←', send: '\x1b[D' } },
  { area: 'right', key: { label: '→', send: '\x1b[C' } },
  { area: 'down', key: { label: '↓', send: '\x1b[B' } },
]
const KEYS: Key[] = [
  CTRL_C,
  { label: 'Esc', send: '\x1b' },
  { label: 'Tab', send: '\t' },
  { label: 'Ctrl', ctrl: true },
  { label: '↑', send: '\x1b[A' },
  { label: '↓', send: '\x1b[B' },
  { label: '←', send: '\x1b[D' },
  { label: '→', send: '\x1b[C' },
  { label: '|', send: '|' },
  { label: '~', send: '~' },
  { label: '/', send: '/' },
  { label: '-', send: '-' },
]

/** With Ctrl armed, the next letter is its control character (Ctrl+C is \x03). */
function applyCtrl(data: string): string {
  if (!ctrlArmed.value || data.length !== 1) return data
  ctrlArmed.value = false
  const code = data.toUpperCase().charCodeAt(0)
  return code >= 64 && code <= 95 ? String.fromCharCode(code - 64) : data
}

/** The pad over the terminal (a phone): shown or not, remembered in this browser. */
const padShown = usePref('pad', true)
let repeatDelay = 0
let repeatTimer = 0

/** A key of the pad pressed: sent now and, for an arrow held down, again and again until it is let go. */
function hold(key: Key, repeat = false) {
  release()
  if (navigator.vibrate) navigator.vibrate(8)
  if (key.send) input(key.send)
  if (!repeat) return
  repeatDelay = window.setTimeout(() => {
    repeatTimer = window.setInterval(() => key.send && input(key.send), 70)
  }, 380)
}

function release() {
  window.clearTimeout(repeatDelay)
  window.clearInterval(repeatTimer)
}

function pressKey(key: Key) {
  if (key.ctrl) ctrlArmed.value = !ctrlArmed.value
  else if (key.send) input(key.send)
  term?.focus()
}

const narrowQuery = window.matchMedia('(max-width: 767px)')
const touchQuery = window.matchMedia('(pointer: coarse)')
function onLayout() {
  narrow.value = narrowQuery.matches
  touch.value = touchQuery.matches
  if (term) term.options.fontSize = narrow.value ? 13 : 14
  void nextTick(refit)
}

watch(phase, async (now) => {
  if (now === 'ready') {
    if (attempt) void remember(attempt)
    if (!narrow.value && filesShown.value && filesAvailable.value) filesOpen.value = true
    await nextTick()
    ensureTerminal()
    refit()
    if (props.active) term?.focus()
  }
})
watch(filesOpen, () => void nextTick(refit))
watch(
  () => props.active,
  async (active) => {
    if (!active) return
    await nextTick()
    refit()
    term?.focus()
  },
)

onMounted(async () => {
  onLayout()
  narrowQuery.addEventListener('change', onLayout)
  touchQuery.addEventListener('change', onLayout)
  if (props.initial) {
    await vault.loaded()
    if (props.initial.password || props.initial.privateKey) useTarget(props.initial)
    else
      Object.assign(form, {
        host: props.initial.host,
        port: props.initial.port,
        username: props.initial.username,
      })
  }
})
onBeforeUnmount(() => {
  narrowQuery.removeEventListener('change', onLayout)
  touchQuery.removeEventListener('change', onLayout)
  observer?.disconnect()
  window.clearTimeout(resizeTimer)
  close()
  term?.dispose()
})
</script>

<style scoped>
.sess {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.sess-connect {
  display: flex;
  justify-content: center;
  overflow-y: auto;
  padding: 0.25rem;
}
.sess-card {
  width: 100%;
  max-width: 30rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 16px;
  background: var(--p-content-background);
}
.sess-saved {
  width: 100%;
}
.sess-saved__opt {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-width: 0;
}
.sess-saved__opt i {
  color: var(--p-primary-color);
}
.sess-saved__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.88rem;
}
.sess-muted {
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.sess-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.sess-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.sess-field label {
  font-weight: 500;
  font-size: 0.9rem;
}
.sess-field--grow {
  flex: 1;
  min-width: 10rem;
}
.sess-field--port {
  width: 6.5rem;
}
.sess-field--port :deep(input) {
  width: 100%;
}
.sess-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sess-auth {
  display: flex;
}
.sess-auth :deep(.p-togglebutton) {
  flex: 1;
}
.sess-mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.8rem;
}
.sess-save {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  cursor: pointer;
  font-size: 0.92rem;
}
.sess-save small {
  display: block;
  color: var(--p-text-muted-color);
}
.sess-save--off {
  cursor: default;
  opacity: 0.7;
}
.sess-note {
  margin: 0;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
  display: flex;
  gap: 0.4rem;
  align-items: baseline;
}
.sess-live {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  min-height: 0;
}
.sess-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.sess-dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
}
.sess-dot--on {
  background: #3fb950;
  box-shadow: 0 0 0 3px #3fb95033;
}
.sess-dot--off {
  background: #8b949e;
}
.sess-target {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.sess-grow {
  flex: 1;
}
.sess-body {
  position: relative;
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
}
.sess-body--files {
  grid-template-columns: minmax(0, 1fr) 10px var(--files-width, 20rem);
  gap: 0;
}
.sess-split {
  cursor: col-resize;
  position: relative;
  touch-action: none;
  outline: none;
}
.sess-split::after {
  content: '';
  position: absolute;
  inset-block: 35%;
  inset-inline-start: 3px;
  width: 4px;
  border-radius: 4px;
  background: var(--p-content-border-color);
  transition: background 0.15s, inset 0.15s;
}
.sess-split:hover::after,
.sess-split:focus-visible::after {
  background: var(--p-primary-color);
  inset-block: 0;
}
.sess-terminal {
  min-height: 0;
  min-width: 0;
  border-radius: 12px;
  padding: 0.5rem;
  background: #0f1419;
  overflow: hidden;
}
.sess-switch {
  display: flex;
  gap: 0.25rem;
  padding: 0.2rem;
  border-radius: 10px;
  background: var(--p-content-hover-background);
}
.sess-switch button {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.45rem;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
  cursor: pointer;
}
.sess-switch .sess-switch--on {
  background: var(--p-content-background);
  color: var(--p-text-color);
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.15);
}
.sess-files {
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
}
.sess-keys {
  display: flex;
  gap: 0.35rem;
  overflow-x: auto;
  padding-bottom: 0.25rem;
  scrollbar-width: none;
}
.sess-key {
  flex: 0 0 auto;
  min-width: 2.6rem;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.9rem;
}
.sess-key--stop {
  color: #f47067;
  border-color: rgb(244 112 103 / 0.5);
  font-weight: 700;
}
.sess-key--pad {
  min-width: 2.4rem;
}
.pad {
  position: absolute;
  inset-inline-end: 0.6rem;
  bottom: 0.6rem;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.55rem;
  padding: 0.7rem 0.7rem 0.75rem;
  border-radius: 20px;
  background: rgb(22 27 34 / 0.72);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgb(255 255 255 / 0.1);
  box-shadow: 0 10px 30px rgb(0 0 0 / 0.45);
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
}
.pad__top {
  display: flex;
  gap: 0.4rem;
}
.pad__key {
  display: grid;
  place-items: center;
  min-width: 3rem;
  height: 2.6rem;
  padding: 0 0.6rem;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 12px;
  background: rgb(255 255 255 / 0.08);
  color: #e6edf3;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.06s, background 0.12s;
  -webkit-tap-highlight-color: transparent;
}
.pad__key:active {
  transform: scale(0.92);
  background: rgb(255 255 255 / 0.22);
}
.pad__key--stop {
  color: #ff8b82;
  border-color: rgb(244 112 103 / 0.45);
  background: rgb(244 112 103 / 0.16);
}
.pad__key--stop:active {
  background: rgb(244 112 103 / 0.35);
}
.pad__dpad {
  position: relative;
  display: grid;
  grid-template-areas:
    '. up .'
    'left hub right'
    '. down .';
  grid-template-columns: repeat(3, 2.9rem);
  grid-template-rows: repeat(3, 2.9rem);
  gap: 0.2rem;
}
.pad__arrow {
  min-width: 0;
  height: auto;
  padding: 0;
  border-radius: 14px;
  font-size: 1rem;
}
.pad__hub {
  grid-area: hub;
  align-self: center;
  justify-self: center;
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.18);
}
.pad__close {
  position: absolute;
  top: -0.55rem;
  inset-inline-end: -0.55rem;
  width: 1.6rem;
  height: 1.6rem;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgb(255 255 255 / 0.18);
  background: #2d333b;
  color: #c9d1d9;
  font-size: 0.65rem;
  cursor: pointer;
}
.sess-key--on {
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  border-color: var(--p-primary-color);
}
.sess-fingerprint {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  border-radius: 8px;
  background: var(--p-content-hover-background);
}
.sess-fingerprint code {
  word-break: break-all;
  font-size: 0.9rem;
}
.sess-fingerprint small {
  color: var(--p-text-muted-color);
}
@media (max-width: 767px) {
  .sess-card {
    padding: 1rem;
  }
  .sess-terminal {
    padding: 0.25rem;
    border-radius: 8px;
  }
}
</style>
