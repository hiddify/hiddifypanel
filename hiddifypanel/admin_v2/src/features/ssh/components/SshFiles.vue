<template>
  <div class="sf">
    <nav class="sf-path" dir="ltr">
      <button type="button" class="sf-crumb" :title="t('ssh.home')" @click="go(home || '.')">
        <i class="pi pi-home" />
      </button>
      <template v-for="(crumb, i) in crumbs" :key="crumb.path">
        <span class="sf-sep">/</span>
        <button type="button" class="sf-crumb" :class="{ 'sf-crumb--last': i === crumbs.length - 1 }" @click="go(crumb.path)">
          {{ crumb.name }}
        </button>
      </template>
      <span class="sf-grow" />
      <Button icon="pi pi-refresh" text rounded size="small" :aria-label="t('ssh.refresh')" :loading="loading" @click="go(path)" />
      <Button icon="pi pi-plus" rounded size="small" :aria-label="t('ssh.add')" v-tooltip.bottom="t('ssh.add')" aria-haspopup="true" @click="(e) => addMenu?.toggle(e)" />
      <Menu ref="addMenu" :model="addItems" popup />
    </nav>
    <input ref="uploadInput" type="file" multiple hidden @change="onPicked($event, false)" />
    <input ref="archiveInput" type="file" hidden :accept="ARCHIVE_ACCEPT" @change="onPicked($event, true)" />

    <!-- Uploads in progress (and their outcome until dismissed) -->
    <ul v-if="uploads.length" class="sf-uploads">
      <li v-for="u in uploads" :key="u.id" class="sf-upload" :class="`sf-upload--${u.state}`">
        <i :class="uploadIcon(u)" />
        <div class="sf-upload__main">
          <div class="sf-upload__line">
            <span class="sf-name" dir="ltr">{{ u.name }}</span>
            <small v-if="u.state !== 'failed'" class="sf-muted">{{ uploadText(u) }}</small>
          </div>
          <small v-if="u.state === 'failed'" class="sf-upload__error">{{ u.message }}</small>
          <ProgressBar v-if="u.state === 'sending' || u.state === 'extracting'" :value="u.state === 'sending' ? Math.round(u.progress * 100) : undefined" :mode="u.state === 'extracting' ? 'indeterminate' : 'determinate'" :show-value="false" class="sf-upload__bar" />
        </div>
        <Button v-if="u.state === 'done' || u.state === 'failed'" icon="pi pi-times" text rounded size="small" severity="secondary" :aria-label="t('common.close')" @click="dismiss(u.id)" />
      </li>
    </ul>

    <Message v-if="error" severity="error" :closable="false" class="sf-msg">{{ error }}</Message>

    <ul class="sf-list" :class="{ 'sf-list--drop': dropping }" dir="ltr" @dragover.prevent="dropping = true" @dragleave.self="dropping = false" @drop.prevent="onDrop">
      <li v-if="dropping" class="sf-dropzone"><i class="pi pi-cloud-upload" /> {{ t('ssh.dropHere') }}</li>
      <li v-if="parent !== null">
        <button type="button" class="sf-item" @click="go(parent)"><i class="pi pi-arrow-up" /><span class="sf-name">..</span></button>
      </li>
      <li v-for="e in entries" :key="e.name">
        <button type="button" class="sf-item" @click="open(e)">
          <i :class="e.dir ? 'pi pi-folder sf-dir' : e.link ? 'pi pi-link' : 'pi pi-file'" />
          <span class="sf-name">{{ e.name }}</span>
          <small v-if="!e.dir" class="sf-size">{{ formatSize(e.size) }}</small>
          <span v-if="e.access" class="sf-perm" :class="`sf-perm--${permKind(shown(e))}`" :title="permTitle(e)"><i v-if="!permLabel(shown(e))" class="pi pi-lock" /><template v-else>{{ permLabel(shown(e)) }}</template></span>
        </button>
      </li>
      <li v-if="!loading && !entries.length && !error" class="sf-empty">
        {{ t('ssh.emptyDir') }}
      </li>
      <li v-if="truncated" class="sf-empty">{{ t('ssh.truncated') }}</li>
    </ul>

    <Dialog
      :visible="viewing"
      modal
      maximizable
      :style="{ width: '64rem', height: '80vh' }"
      :breakpoints="{ '960px': '100vw' }"
      :content-style="{
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        flex: 1,
      }"
      class="sf-viewer"
      @update:visible="(v) => !v && closeFile()"
    >
      <template #header>
        <span class="sf-title" dir="ltr"><i v-if="dirty" class="sf-dirty" :title="t('ssh.unsaved')" />{{ file?.path }}</span>
      </template>
      <ProgressBar v-if="reading" mode="indeterminate" style="height: 4px" />
      <Message v-else-if="readError" severity="error" :closable="false">{{ readError }}</Message>
      <template v-else-if="file">
        <Message v-if="file.too_large" severity="info" :closable="false">{{ t('ssh.tooLarge', { size: formatSize(file.size) }) }}</Message>
        <Message v-else-if="file.base64 !== undefined" severity="info" :closable="false">{{ t('ssh.binary', { size: formatSize(file.size) }) }}</Message>
        <FileEditor v-else-if="editing" v-model="draft" :path="file.path" class="sf-editor" @save="save" />
        <OutputView v-else :text="file.text ?? ''" class="sf-editor" />
      </template>
      <Message v-if="saveError" severity="error" :closable="false" class="mt-2">{{ saveError }}</Message>
      <template #footer>
        <Button v-if="file && !file.too_large" :label="t('ssh.download')" icon="pi pi-download" text @click="download" />
        <span class="sf-grow" />
        <Button v-if="file && archiveOf(file.path)" :label="t('ssh.extractHere')" icon="pi pi-box" text :loading="extracting" @click="extractOpen(file.path)" />
        <Button :label="t('common.close')" text @click="closeFile" />
        <Button v-if="file?.text !== undefined && !editing && file.writable" :label="t('ssh.edit')" icon="pi pi-pencil" @click="editing = true" />
        <Tag v-else-if="file?.text !== undefined && !editing" :value="t('ssh.readOnly')" icon="pi pi-lock" severity="secondary" />
        <Button v-if="file?.text !== undefined && editing" :label="t('ssh.save')" icon="pi pi-save" :loading="saving" :disabled="!dirty" @click="save" />
      </template>
    </Dialog>

    <!-- A name for a new file or folder; where an archive is unpacked -->
    <Dialog v-model:visible="ask.open" modal :header="ask.header" :style="{ width: '26rem' }" :breakpoints="{ '640px': '94vw' }">
      <form class="sf-ask" @submit.prevent="ask.submit">
        <label :for="`sf-ask-${uid}`">{{ ask.label }}</label>
        <InputText :id="`sf-ask-${uid}`" v-model="ask.value" dir="ltr" autofocus spellcheck="false" autocomplete="off" />
        <small class="sf-muted" dir="ltr">{{ ask.hint }}</small>
        <label v-if="ask.removable" class="sf-check"><Checkbox v-model="ask.remove" binary /> {{ t('ssh.removeArchive') }}</label>
        <Message v-if="ask.error" severity="error" :closable="false">{{ ask.error }}</Message>
        <div class="sf-ask__actions">
          <Button :label="t('common.cancel')" text @click="ask.open = false" />
          <Button type="submit" :label="ask.action" :loading="ask.busy" :disabled="!ask.value.trim()" />
        </div>
      </form>
    </Dialog>

    <!-- An upload whose name is taken -->
    <Dialog :visible="conflict.open" modal :closable="false" :header="t('ssh.conflictTitle')" :style="{ width: '28rem' }" :breakpoints="{ '640px': '94vw' }">
      <div class="sf-conflict">
        <i class="pi pi-copy sf-conflict__icon" />
        <p class="m-0">
          <b dir="ltr">{{ conflict.name }}</b> {{ t('ssh.conflictText') }}
        </p>
      </div>
      <template #footer>
        <div class="sf-conflict__actions">
          <Button :label="t('common.cancel')" text severity="secondary" @click="answerConflict('cancel')" />
          <Button :label="t('ssh.keepBoth')" icon="pi pi-clone" outlined @click="answerConflict('both')" />
          <Button :label="t('ssh.replaceGo')" icon="pi pi-sync" severity="danger" @click="answerConflict('replace')" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Menu from 'primevue/menu'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Tag from 'primevue/tag'
import OutputView from '@/features/ssh/components/OutputView.vue'
import FileEditor from '@/features/ssh/components/FileEditor.vue'
import { SshError, type FileContent, type FileEntry, type Listing } from '@/features/ssh/useSsh'
import { useConfirm } from 'primevue/useconfirm'

const props = defineProps<{
  list: (path: string) => Promise<Listing>
  read: (path: string) => Promise<FileContent>
  write: (path: string, content: string) => Promise<{ path: string; size: number }>
  ops: {
    create: (path: string) => Promise<{ path: string; size: number }>
    mkdir: (path: string) => Promise<{ path: string }>
    upload: (path: string, file: Blob, onProgress: (done: number) => void, overwrite?: boolean) => Promise<{ path: string; size: number }>
    extract: (path: string, dest: string, remove?: boolean) => Promise<{ path: string; dest: string }>
  }
  home: string
}>()
const { t } = useI18n()
const confirm = useConfirm()

const path = ref('')
const entries = ref<FileEntry[]>([])
const truncated = ref(false)
const loading = ref(false)
const error = ref('')
const viewing = ref(false)
const reading = ref(false)
const readError = ref('')
const file = ref<FileContent | null>(null)
const draft = ref('')
/** A file opens to read (with its colors, e.g. a log); Edit opens the editor (plain text). */
const editing = ref(false)
/** A folder's X only means "may enter it": not shown. */
function shown(e: FileEntry): string {
  return e.dir ? `${e.access!.slice(0, 2)}-` : e.access!
}

/** What the signed-in user may do, as one tag: the letters it has (RWX, RX, R…); '' when none (a lock icon). */
function permLabel(access: string): string {
  // Writing implies reading here: RW is shown as W, RWX as WX.
  const letters = (access[1] === 'w' ? access.slice(1) : access).replace(/-/g, '').toUpperCase()
  return letters
}

/** Its color: writable (green) above runnable (purple) above readable only (blue); none (grey). */
function permKind(access: string): string {
  if (access[1] === 'w') return 'w'
  if (access[2] === 'x') return 'x'
  return access[0] === 'r' ? 'r' : 'off'
}

function permTitle(e: FileEntry): string {
  const can = [access(e, 0) && t('ssh.permRead'), access(e, 1) && t('ssh.permWrite'), !e.dir && access(e, 2) && t('ssh.permExec')].filter(Boolean)
  return `${can.length ? can.join(' · ') : t('ssh.permNone')} — ${e.mode}`
}

function access(e: FileEntry, i: number): boolean {
  return !!e.access && e.access[i] !== '-'
}
const saving = ref(false)
const saveError = ref('')
const dirty = computed(() => file.value?.text !== undefined && draft.value !== file.value.text)

const crumbs = computed(() => {
  const parts = path.value.split('/').filter(Boolean)
  return parts.map((name, i) => ({
    name,
    path: '/' + parts.slice(0, i + 1).join('/'),
  }))
})
const parent = computed(() => (path.value && path.value !== '/' ? path.value.replace(/\/[^/]+\/?$/, '') || '/' : null))

function join(dir: string, name: string): string {
  return dir.endsWith('/') ? dir + name : `${dir}/${name}`
}

function formatSize(n: number | null | undefined): string {
  if (n === null || n === undefined) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`
  return `${(n / 1024 ** 3).toFixed(1)} GB`
}

async function go(target: string) {
  loading.value = true
  error.value = ''
  try {
    const listing = await props.list(target)
    path.value = listing.path
    entries.value = listing.entries
    truncated.value = listing.truncated
  } catch (e) {
    error.value = describe(e, target)
  } finally {
    loading.value = false
  }
}

async function open(entry: FileEntry) {
  const target = join(path.value, entry.name)
  if (entry.dir) return go(target)
  viewing.value = true
  reading.value = true
  readError.value = ''
  file.value = null
  editing.value = false
  saveError.value = ''
  try {
    file.value = await props.read(target)
    draft.value = file.value.text ?? ''
  } catch (e) {
    if (entry.link) return go(target) // a link to a directory
    readError.value = describe(e, target)
  } finally {
    reading.value = false
  }
}

async function save() {
  if (!file.value || !dirty.value || saving.value) return
  saving.value = true
  saveError.value = ''
  try {
    const saved = await props.write(file.value.path, draft.value)
    file.value = { ...file.value, text: draft.value, size: saved.size }
    void go(path.value) // the size in the list
  } catch (e) {
    saveError.value = describe(e, file.value?.path)
  } finally {
    saving.value = false
  }
}

function closeFile() {
  if (!dirty.value) {
    viewing.value = false
    return
  }
  confirm.require({
    header: t('ssh.unsaved'),
    message: t('ssh.discard'),
    icon: 'pi pi-exclamation-triangle',
    defaultFocus: 'reject',
    rejectProps: { label: t('ssh.keepEditing'), severity: 'secondary', outlined: true },
    acceptProps: { label: t('ssh.discardGo'), severity: 'danger' },
    accept: () => (viewing.value = false),
  })
}

function download() {
  if (!file.value) return
  const bytes = file.value.base64 !== undefined ? Uint8Array.from(atob(file.value.base64), (c) => c.charCodeAt(0)) : new TextEncoder().encode(draft.value)
  const url = URL.createObjectURL(new Blob([bytes]))
  const a = document.createElement('a')
  a.href = url
  a.download = file.value.path.split('/').pop() || 'file'
  a.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// ------------------------------------------------------------------ new files and folders, uploads, archives

const uid = Math.random().toString(36).slice(2, 8)
const addMenu = ref<InstanceType<typeof Menu> | null>(null)
const uploadInput = ref<HTMLInputElement | null>(null)
const archiveInput = ref<HTMLInputElement | null>(null)
const dropping = ref(false)
const extracting = ref(false)

const ARCHIVE = /\.(zip|tar|tar\.gz|tgz|tar\.xz|txz|tar\.bz2|tbz2|tar\.zst|gz)$/i
const ARCHIVE_ACCEPT = '.zip,.tar,.gz,.tgz,.xz,.txz,.bz2,.tbz2,.zst'
const archiveOf = (name: string) => ARCHIVE.test(name)
/** `pack.tar.gz` → `pack` (the folder it is unpacked into by default). */
const stem = (name: string) => name.replace(ARCHIVE, '') || name

const addItems = computed(() => [
  { label: t('ssh.newFile'), icon: 'pi pi-file-plus', command: () => askName('file') },
  { label: t('ssh.newFolder'), icon: 'pi pi-folder-plus', command: () => askName('folder') },
  { separator: true },
  { label: t('ssh.uploadFiles'), icon: 'pi pi-upload', command: () => uploadInput.value?.click() },
  { label: t('ssh.uploadExtract'), icon: 'pi pi-box', command: () => archiveInput.value?.click() },
])

const ask = reactive({ open: false, header: '', label: '', hint: '', action: '', value: '', error: '', busy: false, removable: false, remove: true, submit: () => {} })

function openAsk(o: { header: string; label: string; hint?: string; action: string; value?: string; removable?: boolean; run: (value: string) => Promise<void> }) {
  Object.assign(ask, { open: true, header: o.header, label: o.label, hint: o.hint ?? '', action: o.action, value: o.value ?? '', error: '', busy: false, removable: !!o.removable, remove: true })
  ask.submit = async () => {
    if (!ask.value.trim() || ask.busy) return
    ask.busy = true
    ask.error = ''
    try {
      await o.run(ask.value.trim())
      ask.open = false
    } catch (e) {
      ask.error = describe(e)
    } finally {
      ask.busy = false
    }
  }
}

function askName(kind: 'file' | 'folder') {
  openAsk({
    header: kind === 'file' ? t('ssh.newFile') : t('ssh.newFolder'),
    label: t('ssh.name'),
    hint: t('ssh.inFolder', { path: path.value }),
    action: t('ssh.create'),
    run: async (name) => {
      const target = join(path.value, name)
      if (kind === 'folder') {
        await props.ops.mkdir(target)
        await go(target)
        return
      }
      await props.ops.create(target)
      await go(path.value)
      await open({ name, dir: false, link: false, size: 0, mtime: null, mode: '', access: 'rw-' })
      editing.value = true
    },
  })
}

interface Upload {
  id: number
  name: string
  state: 'sending' | 'extracting' | 'done' | 'failed'
  progress: number
  message: string
}
const uploads = ref<Upload[]>([])
let uploadSeq = 0

function onPicked(event: Event, extract: boolean) {
  const input = event.target as HTMLInputElement
  const files = [...(input.files ?? [])]
  input.value = '' // the same file can be picked again
  if (extract && files[0]) askExtractUpload(files[0])
  else void uploadAll(files)
}

function onDrop(event: DragEvent) {
  dropping.value = false
  void uploadAll([...(event.dataTransfer?.files ?? [])])
}

async function uploadAll(files: File[]) {
  for (const file of files) await uploadOne(file)
  void go(path.value)
}

/** Sends one file into the folder shown; asks before replacing one with the same name. Its path, or null. */
async function uploadOne(file: File, dir = path.value): Promise<{ u: Upload; path: string } | null> {
  uploads.value.unshift({ id: ++uploadSeq, name: file.name, state: 'sending', progress: 0, message: '' })
  const u = uploads.value[0]!
  let target = join(dir, file.name)
  const send = (overwrite: boolean) => props.ops.upload(target, file, (d) => (u.progress = d), overwrite)
  try {
    try {
      await send(false)
    } catch (e) {
      if (!(e instanceof SshError && e.code === 'exists')) throw e
      const choice = await askConflict(file.name)
      if (choice === 'cancel') {
        dismiss(u.id)
        return null
      }
      if (choice === 'replace') await send(true)
      else {
        target = join(dir, await freeName(dir, file.name))
        u.name = target.split('/').pop()!
        await send(false)
      }
    }
    u.state = 'done'
    u.message = formatSize(file.size)
    return { u, path: target }
  } catch (e) {
    u.state = 'failed'
    u.message = describe(e, target)
    return null
  }
}

function askExtractUpload(file: File) {
  const dir = path.value
  openAsk({
    header: t('ssh.uploadExtract'),
    label: t('ssh.extractInto'),
    hint: file.name,
    action: t('ssh.uploadExtractGo'),
    value: join(dir, stem(file.name)),
    removable: true,
    run: async (dest) => {
      const remove = ask.remove
      ask.open = false // the upload shows in the list
      const sent = await uploadOne(file, dir)
      if (!sent) return
      await unpack(sent.u, sent.path, dest, remove)
    },
  })
}

function extractOpen(archive: string) {
  const dir = archive.replace(/\/[^/]*$/, '') || '/'
  const name = archive.split('/').pop() || archive
  openAsk({
    header: t('ssh.extractHere'),
    label: t('ssh.extractInto'),
    hint: name,
    action: t('ssh.extract'),
    value: join(dir, stem(name)),
    removable: true,
    run: async (dest) => {
      const remove = ask.remove
      ask.open = false
      viewing.value = false
      uploads.value.unshift({ id: ++uploadSeq, name, state: 'extracting', progress: 1, message: '' })
      await unpack(uploads.value[0]!, archive, dest, remove)
    },
  })
}

async function unpack(u: Upload, archive: string, dest: string, remove: boolean) {
  u.state = 'extracting'
  extracting.value = true
  try {
    await props.ops.extract(archive, dest, remove)
    u.state = 'done'
    u.message = t('ssh.extractedTo', { path: dest })
    await go(dest)
  } catch (e) {
    u.state = 'failed'
    u.message = describe(e, archive)
  } finally {
    extracting.value = false
  }
}

/** What went wrong, in plain words (the server's own text after it, small, for the curious). */
function describe(e: unknown, path?: string): string {
  const message = e instanceof Error ? e.message : String(e)
  const code = e instanceof SshError ? e.code : 'other'
  const name = path?.split('/').pop() || path || ''
  if (code === 'other') return message
  const detail = message.replace(/^\w+: /, '')
  const plain = t(`ssh.err.${code}`, { name, tool: detail })
  return code === 'connection' || code === 'missingTool' ? plain : `${plain} (${detail})`
}

// A name that is taken: replace it, keep both (the new one numbered) or leave it.
type ConflictChoice = 'replace' | 'both' | 'cancel'
const conflict = reactive({ open: false, name: '', resolve: (_c: ConflictChoice) => {} })

function askConflict(name: string): Promise<ConflictChoice> {
  return new Promise((resolve) => {
    Object.assign(conflict, { open: true, name, resolve })
  })
}

function answerConflict(choice: ConflictChoice) {
  conflict.open = false
  conflict.resolve(choice)
}

/** `a.conf` → `a (1).conf`, `a (2).conf`… the first one not in `dir`. */
async function freeName(dir: string, name: string): Promise<string> {
  const taken = new Set((await props.list(dir)).entries.map((e) => e.name))
  const dot = name.lastIndexOf('.') > 0 ? name.lastIndexOf('.') : name.length
  for (let i = 1; ; i++) {
    const next = `${name.slice(0, dot)} (${i})${name.slice(dot)}`
    if (!taken.has(next)) return next
  }
}

function dismiss(id: number) {
  uploads.value = uploads.value.filter((u) => u.id !== id)
}

function uploadIcon(u: Upload): string {
  return { sending: 'pi pi-cloud-upload sf-blue', extracting: 'pi pi-box sf-blue', done: 'pi pi-check-circle sf-green', failed: 'pi pi-times-circle sf-red' }[u.state]
}

function uploadText(u: Upload): string {
  if (u.state === 'sending') return `${Math.round(u.progress * 100)}%`
  if (u.state === 'extracting') return t('ssh.extracting')
  return u.message
}

onMounted(() => void go(props.home || '.'))
</script>

<style scoped>
.sf {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.sf-path {
  display: flex;
  align-items: center;
  gap: 0.1rem;
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
  overflow-x: auto;
  white-space: nowrap;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.85rem;
}
.sf-crumb {
  border: 0;
  background: none;
  color: var(--p-text-muted-color);
  padding: 0.2rem 0.3rem;
  border-radius: 6px;
  cursor: pointer;
}
.sf-crumb:hover,
.sf-crumb--last {
  color: var(--p-text-color);
}
.sf-crumb:hover {
  background: var(--p-content-hover-background);
}
.sf-sep {
  color: var(--p-text-muted-color);
}
.sf-grow {
  flex: 1;
}
.sf-msg {
  margin: 0.5rem;
}
.sf-list {
  list-style: none;
  margin: 0;
  padding: 0.25rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
.sf-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  border: 0;
  background: none;
  color: var(--p-text-color);
  text-align: left;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
}
.sf-item:hover {
  background: var(--p-content-hover-background);
}
.sf-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sf-dir {
  color: var(--p-primary-color);
}
.sf-size {
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
.sf-perm {
  flex: 0 0 auto;
  min-width: 2.1rem;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  text-align: center;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.sf-perm--r {
  color: #1f6feb;
  background: rgb(31 111 235 / 0.14);
}
.sf-perm--w {
  color: #2ea043;
  background: rgb(46 160 67 / 0.15);
}
.sf-perm--x {
  color: #8250df;
  background: rgb(130 80 223 / 0.14);
}
.sf-perm--off {
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background);
}
.sf-conflict {
  display: flex;
  gap: 0.9rem;
  align-items: flex-start;
}
.sf-conflict__icon {
  font-size: 1.6rem;
  color: var(--p-orange-500, #f59e0b);
}
.sf-conflict__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  width: 100%;
}
.sf-muted {
  color: var(--p-text-muted-color);
}
.sf-blue {
  color: var(--p-primary-color);
}
.sf-green {
  color: #2ea043;
}
.sf-red {
  color: #f47067;
}
.sf-uploads {
  list-style: none;
  margin: 0;
  padding: 0.4rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  border-bottom: 1px solid var(--p-content-border-color);
  max-height: 11rem;
  overflow-y: auto;
}
.sf-upload {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 0.6rem;
  border-radius: 10px;
  background: var(--p-content-hover-background);
  font-size: 0.85rem;
}
.sf-upload--failed {
  background: rgb(244 112 103 / 0.12);
}
.sf-upload__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.sf-upload__line {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  min-width: 0;
}
.sf-upload__line small {
  flex: 0 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}
.sf-upload__error {
  color: #d1453b;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.sf-upload__bar {
  height: 4px;
}
.sf-list--drop {
  outline: 2px dashed var(--p-primary-color);
  outline-offset: -6px;
  border-radius: 12px;
}
.sf-dropzone {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  margin-bottom: 0.25rem;
  border-radius: 10px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  font-weight: 600;
  pointer-events: none;
}
.sf-ask {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.sf-ask__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.sf-check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}
.sf-empty {
  padding: 0.75rem;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.sf-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sf-dirty {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--p-orange-500, #f59e0b);
  flex: 0 0 auto;
}
.sf-editor {
  flex: 1;
  min-height: 0;
}
.sf-text {
  margin: 0;
  max-height: 65vh;
  overflow: auto;
  padding: 0.75rem;
  border-radius: 8px;
  background: var(--p-content-hover-background);
  font-size: 0.8rem;
  line-height: 1.45;
  white-space: pre;
}
</style>
