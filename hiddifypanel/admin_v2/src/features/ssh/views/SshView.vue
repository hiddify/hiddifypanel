<template>
  <div class="ssh">
    <PageHeader :title="t('ssh.title')" :subtitle="t('ssh.subtitle')" />

    <nav class="ssh-tabs" role="tablist">
      <div class="ssh-tabs__scroll">
        <button v-for="tab in tabs" :key="tab.id" type="button" role="tab" class="ssh-tab" :class="{ 'ssh-tab--active': tab.id === activeId }" :aria-selected="tab.id === activeId" @click="activate(tab.id)">
          <i v-if="tab.run" :class="runIcon(tab.run)" class="ssh-tab__icon" />
          <span v-else class="ssh-tab__dot" :class="`ssh-tab__dot--${tab.phase}`" />
          <span class="ssh-tab__title" dir="ltr">{{ tab.title }}</span>
          <i v-if="tabs.length > 1 || tab.phase !== 'idle'" class="pi pi-times ssh-tab__close" :aria-label="t('ssh.closeTab')" v-tooltip.bottom="t('ssh.closeTab')" @click.stop="askClose(tab)" />
        </button>
        <Button icon="pi pi-plus" text rounded size="small" :aria-label="t('ssh.newTab')" v-tooltip.bottom="t('ssh.newTab')" :disabled="tabs.length >= MAX_TABS" @click="addTab()" />
      </div>
      <Button icon="pi pi-bolt" :label="t('ssh.commands')" text size="small" :badge="vault.commands.value.length ? String(vault.commands.value.length) : undefined" @click="commandsVisible = !commandsVisible" />
    </nav>

    <Message v-if="linkNote" severity="info" :closable="true" class="mb-2" @close="linkNote = ''">{{ linkNote }}</Message>

    <div class="ssh-main">
      <div class="ssh-panes">
        <template v-for="tab in tabs" :key="tab.id">
          <RunPane v-if="tab.run" v-show="tab.id === activeId" :run="tab.run" class="ssh-pane ssh-pane--run" @stop="stopRun(tab.run)" @open-tab="activate" />
          <SshSession
            v-else
            v-show="tab.id === activeId"
            :key="tab.id"
            :ref="(el) => setSession(tab.id, el)"
            :active="tab.id === activeId"
            :initial="tab.initial"
            class="ssh-pane"
            @title="(v) => (tab.title = v)"
            @phase="(v) => (tab.phase = v)"
            @link="(v) => onLink(tab, v)"
            @copy-link="copyLink"
          />
        </template>
      </div>
      <!-- Saved commands: run on open connections and saved ones. Beside the terminal on a wide screen (unless hidden), over it otherwise. -->
      <div v-if="!wide && commandsVisible" class="ssh-dock__mask" @click="commandsVisible = false" />
      <aside v-if="commandsVisible" class="ssh-dock" :class="{ 'ssh-dock--overlay': !wide }">
        <header class="ssh-dock__head">
          <b><i class="pi pi-bolt" /> {{ t('ssh.commands') }}</b>
          <Button icon="pi pi-times" text rounded size="small" severity="secondary" :aria-label="t('common.close')" @click="commandsVisible = false" />
        </header>
        <div class="ssh-dock__body">
          <p class="ssh-muted mt-0">{{ t('ssh.commandsHint') }}</p>

          <div class="ssh-targets">
            <div class="ssh-targets__head">
              <b>{{ t('ssh.runOnOpen') }}</b>
              <Button v-if="connected.length > 1" :label="allChosen ? t('ssh.none') : t('ssh.all')" text size="small" @click="toggleAll" />
            </div>
            <p v-if="!connected.length" class="ssh-muted m-0">
              {{ t('ssh.noConnected') }}
            </p>
            <label v-for="tab in connected" :key="tab.id" class="ssh-target">
              <Checkbox v-model="chosen" :value="tab.id" />
              <span dir="ltr">{{ tab.title }}</span>
            </label>

            <template v-if="closedSaved.length">
              <div class="ssh-targets__head mt-2">
                <b>{{ t('ssh.runOnSaved') }}</b>
                <Button :label="allSavedChosen ? t('ssh.none') : t('ssh.all')" text size="small" @click="toggleAllSaved" />
              </div>
              <label v-for="c in closedSaved" :key="c.id" class="ssh-target">
                <Checkbox v-model="chosenSaved" :value="c.id" />
                <span class="ssh-target__label">
                  <span dir="auto">{{ connectionTitle(c) }}</span>
                  <small v-if="c.name?.trim()" class="ssh-muted" dir="ltr">{{ connectionAddr(c) }}</small>
                </span>
              </label>
            </template>
          </div>

          <ul class="ssh-cmds">
            <li v-for="c in vault.commands.value" :key="c.id" class="ssh-cmd">
              <div class="ssh-cmd__text">
                <b>{{ c.builtin ? t(c.name) : c.name }} <Tag v-if="c.builtin" :value="t('ssh.builtin')" severity="secondary" class="ssh-builtin" /></b>
                <code dir="ltr">{{ c.command }}</code>
              </div>
              <div class="ssh-cmd__actions">
                <Button icon="pi pi-play" :aria-label="t('ssh.run')" v-tooltip.left="t('ssh.runOnChosen', { n: targetCount })" size="small" :disabled="!targetCount" @click="runCommand(c)" />
                <template v-if="!c.builtin">
                  <Button icon="pi pi-pencil" text rounded size="small" severity="secondary" :aria-label="t('ssh.edit')" @click="editCommand(c)" />
                  <Button icon="pi pi-trash" text rounded size="small" severity="danger" :aria-label="t('ssh.forget')" @click="vault.removeCommand(c.id)" />
                </template>
              </div>
            </li>
            <li v-if="!vault.commands.value.length" class="ssh-muted">
              {{ t('ssh.noCommands') }}
            </li>
          </ul>

          <form class="ssh-cmd-form" @submit.prevent="saveCommand">
            <b>{{ draft.id ? t('ssh.editCommand') : t('ssh.addCommand') }}</b>
            <InputText v-model="draft.name" :placeholder="t('ssh.commandName')" />
            <Textarea v-model="draft.command" rows="3" class="ssh-mono" spellcheck="false" dir="ltr" :placeholder="t('ssh.commandPlaceholder')" />
            <div class="ssh-cmd-form__actions">
              <Button v-if="draft.id" :label="t('common.cancel')" text size="small" @click="resetDraft" />
              <Button
                v-if="draft.command.trim() && targetCount"
                :label="t('ssh.runOnce')"
                icon="pi pi-play"
                text
                size="small"
                @click="
                  runCommand({
                    id: '',
                    name: draft.name || draft.command,
                    command: draft.command,
                  })
                "
              />
              <Button type="submit" :label="t('ssh.save')" icon="pi pi-save" size="small" :disabled="!draft.name.trim() || !draft.command.trim() || !vault.state.available" />
            </div>
          </form>
        </div>
      </aside>
    </div>

    <Dialog :visible="!!linkShown" modal :header="t('ssh.linkTitle')" :style="{ width: '34rem' }" :breakpoints="{ '640px': '94vw' }" @update:visible="(v) => !v && (linkShown = '')">
      <p class="mt-0 ssh-muted">{{ t('ssh.linkHint') }}</p>
      <InputText :model-value="linkShown" readonly dir="ltr" class="w-full" @focus="($event.target as HTMLInputElement).select()" />
      <template #footer>
        <Button :label="t('common.close')" @click="linkShown = ''" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * The SSH page: several connections side by side as tabs (each an `SshSession`), and saved commands run on any of the
 * connected ones. A connection's link (`?host=&port=&user=&s=`) opens it again in a tab.
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch, type ComponentPublicInstance } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import PageHeader from '@/shared/components/PageHeader.vue'
import RunPane, { type Run, type RunResult } from '@/features/ssh/components/RunPane.vue'
import SshSession from '@/features/ssh/components/SshSession.vue'
import type { ExecResult, SshPhase } from '@/features/ssh/useSsh'
import { connectionAddr, connectionTitle, openDeepLink, useVault, type ConnectTarget, type DeepLink, type VaultCommand, type VaultConnection } from '@/features/ssh/vault'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const vault = useVault()
const dangerConfirm = useDangerConfirm()

const MAX_TABS = 12

interface Tab {
  id: number
  title: string
  phase: SshPhase
  initial: ConnectTarget | null
  link: DeepLink | null
  /** A command run on several servers (this tab shows its results, not a connection). */
  run?: Run
}

type SessionApi = {
  run: (command: string) => boolean
  exec: (command: string, onData: (data: string) => void) => Promise<ExecResult>
  stopExec: () => void
  error: string
}

let seq = 0
const tabs = ref<Tab[]>([])
const activeId = ref(0)
const sessions = shallowRef(new Map<number, SessionApi>())
const linkNote = ref('')

function addTab(initial: ConnectTarget | null = null, focus = true, run?: Run): Tab {
  const tab: Tab = {
    id: ++seq,
    title: run ? run.title : t('ssh.newTab'),
    phase: 'idle',
    initial,
    link: null,
    run,
  }
  tabs.value.push(tab)
  if (focus) activeId.value = tab.id
  return tabs.value[tabs.value.length - 1]! // the reactive one
}

function activate(id: number) {
  activeId.value = id
}

/** Closing a tab that is connected (or still running a command) disconnects it: asked first. */
function askClose(tab: Tab) {
  const busy = tab.run ? tab.run.results.some((r) => r.state === 'connecting' || r.state === 'running') : tab.phase !== 'idle'
  if (!busy) return closeTab(tab.id)
  dangerConfirm({
    header: t('ssh.closeTab'),
    message: tab.run ? t('ssh.closeRunConfirm') : t('ssh.closeConfirm', { name: tab.title }),
    acceptLabel: tab.run ? t('ssh.close') : t('ssh.disconnect'),
    rejectLabel: t('common.cancel'),
    accept: () => {
      if (tab.run) stopRun(tab.run)
      closeTab(tab.id)
    },
  })
}

function closeTab(id: number) {
  const index = tabs.value.findIndex((tab) => tab.id === id)
  if (index < 0) return
  tabs.value.splice(index, 1)
  sessions.value.delete(id)
  chosen.value = chosen.value.filter((c) => c !== id)
  if (activeId.value === id) activeId.value = tabs.value[Math.max(0, index - 1)]?.id ?? 0
  if (!tabs.value.some((tab) => !tab.run)) addTab(null, !tabs.value.length)
}

function setSession(id: number, el: Element | ComponentPublicInstance | null) {
  if (el) sessions.value.set(id, el as unknown as SessionApi)
}

// ------------------------------------------------------------------ links

const active = computed(() => tabs.value.find((tab) => tab.id === activeId.value) ?? null)

function onLink(tab: Tab, link: DeepLink | null) {
  tab.link = link
  if (tab.id === activeId.value) void showLink(link)
}

/** The address shows the active connection: open it again (anywhere this admin is signed in) with it. */
async function showLink(link: DeepLink | null) {
  const query = link
    ? {
        host: link.host,
        port: String(link.port),
        user: link.user,
        ...(link.s ? { s: link.s } : {}),
      }
    : {}
  await router.replace({ query })
}

watch(activeId, () => void showLink(active.value?.link ?? null))

const linkShown = ref('')

async function copyLink() {
  const url = window.location.href
  try {
    await navigator.clipboard.writeText(url)
    toast.add({
      severity: 'success',
      summary: t('ssh.linkCopied'),
      life: 2500,
    })
  } catch {
    linkShown.value = url // the browser refused the clipboard: shown to copy by hand
  }
}

// ------------------------------------------------------------------ saved commands

/** A wide screen: the commands stay beside the terminal (shown unless the admin hid them, remembered in this browser). */
const wideQuery = window.matchMedia('(min-width: 1200px)')
const wide = ref(wideQuery.matches)
const onWide = () => (wide.value = wideQuery.matches)
onMounted(() => wideQuery.addEventListener('change', onWide))
onBeforeUnmount(() => wideQuery.removeEventListener('change', onWide))
/** Beside the connect form and the results; not beside an open terminal (the button still shows it, until the tab changes). */
const commandsAuto = computed(() => !(active.value && !active.value.run && active.value.phase === 'ready'))
const commandsOverride = ref<boolean | null>(null)
watch(() => [activeId.value, active.value?.phase], () => (commandsOverride.value = null))
const commandsVisible = computed({
  get: () => commandsOverride.value ?? (wide.value && commandsAuto.value),
  set: (v: boolean) => (commandsOverride.value = v),
})
const commandsOpen = commandsVisible
const chosen = ref<number[]>([])
const draft = reactive({ id: '', name: '', command: '' })
const connected = computed(() => tabs.value.filter((tab) => tab.phase === 'ready'))
const allChosen = computed(() => connected.value.length > 0 && connected.value.every((tab) => chosen.value.includes(tab.id)))

// The connection being looked at is chosen by default; one that is gone is not.
watch(
  () => [commandsOpen.value, connected.value.map((tab) => tab.id).join()],
  () => {
    const ids = new Set(connected.value.map((tab) => tab.id))
    chosen.value = chosen.value.filter((id) => ids.has(id))
    if (commandsOpen.value && !chosen.value.length && ids.has(activeId.value)) chosen.value = [activeId.value]
  },
)

function toggleAll() {
  chosen.value = allChosen.value ? [] : connected.value.map((tab) => tab.id)
}

// ------------------------------------------------------------------ running on many servers, with each one's result

/** Saved connections that no tab has open: they can be run on too (a tab opens for each, in the background). */
const closedSaved = computed(() => vault.connections.value.filter((c) => !tabs.value.some((tab) => tab.phase !== 'idle' && tab.title === label(c))))
const chosenSaved = ref<string[]>([])
const allSavedChosen = computed(() => closedSaved.value.length > 0 && closedSaved.value.every((c) => chosenSaved.value.includes(c.id)))
const targetCount = computed(() => chosen.value.length + chosenSaved.value.filter((id) => closedSaved.value.some((c) => c.id === id)).length)

function toggleAllSaved() {
  chosenSaved.value = allSavedChosen.value ? [] : closedSaved.value.map((c) => c.id)
}

function label(c: VaultConnection): string {
  return connectionTitle(c)
}

function runIcon(run: Run): string {
  if (run.results.some((r) => r.state === 'connecting' || r.state === 'running')) return 'pi pi-spin pi-spinner'
  return run.results.every((r) => r.state === 'ok') ? 'pi pi-check-circle ssh-ok' : 'pi pi-exclamation-circle ssh-bad'
}

const CONNECT_WAIT_MS = 60_000

/** Until the tab is connected (true), or will not be without the admin (false: refused, the key to trust, timed out). */
function connected_(tab: Tab): Promise<boolean> {
  return new Promise((resolve) => {
    const started = Date.now()
    const timer = window.setInterval(() => {
      const phase = tabs.value.find((x) => x.id === tab.id)?.phase
      if (phase === 'ready') return finish(true)
      // Idle with an error: refused (a wrong password, unreachable); idle without one: not started yet.
      const refused = phase === 'idle' && !!sessions.value.get(tab.id)?.error
      if (phase === 'closed' || phase === 'hostkey' || phase === undefined || refused || Date.now() - started > CONNECT_WAIT_MS) finish(false)
    }, 250)
    function finish(ok: boolean) {
      window.clearInterval(timer)
      resolve(ok)
    }
  })
}

function targetOf(c: VaultConnection): ConnectTarget | null {
  const base = { host: c.host, port: c.port, username: c.username }
  if (c.auth === 'password') return c.password ? { ...base, auth: 'password', password: c.password } : null
  const key = vault.keyOf(c)
  return key
    ? {
        ...base,
        auth: 'key',
        privateKey: key.privateKey,
        passphrase: key.passphrase,
        keyId: key.id,
        keyName: key.name,
      }
    : null
}

async function runOne(result: RunResult, tab: Tab, command: string) {
  if (!(await connected_(tab))) {
    result.state = 'failed'
    result.message = tab.phase === 'hostkey' ? t('ssh.needsTrust') : sessions.value.get(tab.id)?.error || t('ssh.couldNotConnect')
    return
  }
  result.state = 'running'
  const done = await sessions.value.get(tab.id)!.exec(command, (data) => (result.output += data))
  result.status = done.status
  result.message = done.message
  result.state = done.status === 0 ? 'ok' : 'failed'
}

function runCommand(c: VaultCommand) {
  const command = c.command
  const runs: { tab: Tab; title: string }[] = chosen.value
    .map((id) => tabs.value.find((tab) => tab.id === id))
    .filter((tab): tab is Tab => !!tab)
    .map((tab) => ({ tab, title: tab.title }))
  const skipped: { title: string; message: string }[] = []
  for (const conn of closedSaved.value.filter((x) => chosenSaved.value.includes(x.id))) {
    const target = targetOf(conn)
    if (!target) skipped.push({ title: label(conn), message: t('ssh.noSecret') })
    else if (tabs.value.length >= MAX_TABS - 1) skipped.push({ title: label(conn), message: t('ssh.tooManyTabs') })
    else runs.push({ tab: addTab(target, false), title: label(conn) })
  }
  chosenSaved.value = []
  const result = (key: string, tabId: number, title: string, state: RunResult['state'], message = ''): RunResult => ({
    key,
    tabId,
    title,
    state,
    status: null,
    message,
    output: '',
  })
  const tab = addTab(null, true, {
    title: c.builtin ? t(c.name) : c.name,
    command,
    results: [...runs.map(({ tab, title }) => result(`t${tab.id}`, tab.id, title, 'connecting')), ...skipped.map((s) => result(s.title, 0, s.title, 'failed', s.message))],
  })
  if (!wide.value) commandsOverride.value = null
  // Through the tab's reactive copy, so the output shows as it comes.
  for (const [i, run] of runs.entries()) void runOne(tab.run!.results[i]!, run.tab, command)
}

function stopRun(run: Run) {
  for (const r of run.results) if (r.state === 'running') sessions.value.get(r.tabId)?.stopExec()
}

function editCommand(c: VaultCommand) {
  Object.assign(draft, { id: c.id, name: c.name, command: c.command })
}

function resetDraft() {
  Object.assign(draft, { id: '', name: '', command: '' })
}

async function saveCommand() {
  await vault.saveCommand({
    id: draft.id || undefined,
    name: draft.name,
    command: draft.command,
  })
  resetDraft()
}

onMounted(async () => {
  const opened = await openDeepLink(route.query)
  if (opened && !opened.secretOk) linkNote.value = t('ssh.linkNotYours')
  addTab(opened?.target ?? null)
})
</script>

<style scoped>
.ssh {
  display: flex;
  flex-direction: column;
  /* the terminal takes the rest of the screen, on a phone too */
  height: calc(100dvh - 7rem);
  min-height: 26rem;
}
.ssh-tabs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
  margin-bottom: 0.75rem;
}
.ssh-tabs__scroll {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: thin;
}
.ssh-tab {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  max-width: 14rem;
  padding: 0.5rem 0.65rem;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--p-text-muted-color);
  cursor: pointer;
  white-space: nowrap;
  font-size: 0.88rem;
}
.ssh-tab:hover {
  color: var(--p-text-color);
}
.ssh-tab--active {
  color: var(--p-text-color);
  border-bottom-color: var(--p-primary-color);
}
.ssh-tab__title {
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.ssh-tab__dot {
  flex: 0 0 auto;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--p-content-border-color);
}
.ssh-tab__dot--ready {
  background: #3fb950;
}
.ssh-tab__dot--connecting,
.ssh-tab__dot--hostkey {
  background: #e0b453;
}
.ssh-tab__dot--closed {
  background: #f47067;
}
.ssh-tab__close {
  font-size: 0.7rem;
  padding: 0.2rem;
  border-radius: 4px;
  opacity: 0.6;
}
.ssh-tab__close:hover {
  opacity: 1;
  background: var(--p-content-hover-background);
}
.ssh-main {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0.75rem;
  position: relative;
}
.ssh-panes {
  flex: 1;
  min-width: 0;
  min-height: 0;
}
.ssh-dock {
  width: 24rem;
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
  background: var(--p-content-background);
}
.ssh-dock--overlay {
  position: fixed;
  inset-block: 0;
  inset-inline-end: 0;
  z-index: 1100;
  width: min(26rem, 100vw);
  border-radius: 0;
  box-shadow: 0 0 24px rgb(0 0 0 / 0.3);
}
.ssh-dock__mask {
  position: fixed;
  inset: 0;
  z-index: 1099;
  background: rgb(0 0 0 / 0.4);
}
.ssh-dock__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--p-content-border-color);
}
.ssh-dock__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.75rem;
}
.ssh-pane {
  height: 100%;
}
.ssh-muted {
  color: var(--p-text-muted-color);
  font-size: 0.88rem;
}
.ssh-targets {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.75rem;
  border-radius: 10px;
  background: var(--p-content-hover-background);
  margin-bottom: 1rem;
}
.ssh-targets__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ssh-target {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.88rem;
}
.ssh-target__label {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  min-width: 0;
}
.ssh-target__label > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
.ssh-target__label > small {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.72rem;
}
.ssh-cmds {
  list-style: none;
  margin: 0 0 1rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.ssh-cmd {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.7rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px;
}
.ssh-cmd__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.ssh-cmd__text code {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ssh-cmd__actions {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}
.ssh-cmd-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--p-content-border-color);
}
.ssh-cmd-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.25rem;
}
.ssh-builtin {
  font-size: 0.7rem;
  margin-inline-start: 0.25rem;
}
.ssh-summary {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
}
.ssh-results {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.ssh-result {
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px;
  overflow: hidden;
}
.ssh-result--ok {
  border-inline-start: 3px solid #3fb950;
}
.ssh-result--failed {
  border-inline-start: 3px solid #f47067;
}
.ssh-result__head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 0;
  background: none;
  color: var(--p-text-color);
  cursor: pointer;
  text-align: start;
}
.ssh-result__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.88rem;
}
.ssh-result__body {
  padding: 0 0.75rem 0.75rem;
}
.ssh-result__actions {
  display: flex;
  justify-content: flex-end;
}
.ssh-ok {
  color: #3fb950;
}
.ssh-bad {
  color: #f47067;
}
.ssh-mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.82rem;
}
@media (max-width: 767px) {
  .ssh {
    height: calc(100dvh - 5.5rem);
  }
}
</style>
