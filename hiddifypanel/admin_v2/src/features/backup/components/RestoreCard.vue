<script setup lang="ts">
/**
 * Restore: drop (or pick) a backup file, or take one of the server's backups (`source`), see what it holds,
 * choose the parts, then restore. The restore and the reinstall run in the action dialog with their log.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import ToggleSwitch from 'primevue/toggleswitch'
import { apiErrorMessage } from '@/core/api/client'
import { openLegacyAction } from '@/core/panelShell'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { backupApi, formatSize, type BackupSummary, type RestoreOptions, type RestoreSource } from '@/features/backup/api'

const source = defineModel<RestoreSource | null>('source', { required: true })
const { t } = useI18n()
const dangerConfirm = useDangerConfirm()

const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const reading = ref(false)
const summary = ref<BackupSummary | null>(null)
const error = ref<string | null>(null)
const busy = ref(false)
const showAdvanced = ref(false)
const options = ref<RestoreOptions>({ settings: true, users: true, domains: true, replace_owner_admin: false })

const PARTS = [
  { key: 'settings', icon: 'pi pi-cog' },
  { key: 'users', icon: 'pi pi-users' },
  { key: 'domains', icon: 'pi pi-globe' },
] as const

const anyPart = computed(() => options.value.settings || options.value.users || options.value.domains)

const counts = computed(() => {
  const s = summary.value
  if (!s) return []
  return [
    { key: 'users', icon: 'pi pi-users', n: s.users },
    { key: 'admins', icon: 'pi pi-user-edit', n: s.admins },
    { key: 'domains', icon: 'pi pi-globe', n: s.domains },
    { key: 'custom_proxies', icon: 'pi pi-sitemap', n: s.custom_proxies },
    { key: 'nodes', icon: 'pi pi-server', n: s.nodes },
    { key: 'settings', icon: 'pi pi-cog', n: s.settings },
  ].filter((c) => c.n > 0 || c.key === 'users')
})

// A new source: check it with the server.
watch(
  source,
  async (src) => {
    summary.value = null
    error.value = null
    if (!src) return
    reading.value = true
    try {
      summary.value = await backupApi.summary(src)
    } catch (err) {
      error.value = apiErrorMessage(err) || t('backup.restore.unreadable')
    } finally {
      reading.value = false
    }
  },
  { immediate: true },
)

async function takeFile(file: File | undefined) {
  if (!file) return
  error.value = null
  if (!/\.json$/i.test(file.name) && file.type !== 'application/json') {
    error.value = t('backup.restore.notJson')
    return
  }
  try {
    const data = JSON.parse(await file.text())
    source.value = { kind: 'upload', name: file.name, size: file.size, data }
  } catch {
    error.value = t('backup.restore.unreadable')
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false
  void takeFile(e.dataTransfer?.files?.[0])
}
function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  void takeFile(input.files?.[0])
  input.value = ''
}

function clear() {
  source.value = null
}

function start() {
  if (!source.value || !anyPart.value) return
  const parts = PARTS.filter((p) => options.value[p.key]).map((p) => t(`backup.restore.part.${p.key}`))
  dangerConfirm({
    header: t('backup.restore.confirmTitle'),
    message: t('backup.restore.confirmMessage', { parts: parts.join(document.documentElement.dir === 'rtl' ? '، ' : ', ') }),
    acceptLabel: t('backup.restore.run'),
    accept: () => void run(),
  })
}

async function run() {
  if (!source.value) return
  busy.value = true
  error.value = null
  try {
    const { run_url } = await backupApi.prepare(source.value, options.value)
    openLegacyAction({ title: t('backup.restore.running'), url: run_url, method: 'post' })
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="rc">
    <header class="rc__head">
      <span class="rc__icon"><i class="pi pi-history" /></span>
      <div>
        <h3 class="rc__title">{{ t('backup.restore.title') }}</h3>
        <p class="rc__sub">{{ t('backup.restore.sub') }}</p>
      </div>
    </header>

    <!-- 1. Choose a backup -->
    <input ref="fileInput" type="file" accept=".json,application/json" hidden @change="onPick" />
    <button
      v-if="!source"
      type="button"
      class="rc__drop"
      :class="{ 'rc__drop--over': dragging }"
      @click="fileInput?.click()"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <span class="rc__drop-icon"><i class="pi pi-cloud-upload" /></span>
      <b>{{ t('backup.restore.drop') }}</b>
      <small>{{ t('backup.restore.dropHint') }}</small>
    </button>

    <!-- 2. What it holds -->
    <div v-else class="rc__file">
      <div class="rc__file-head">
        <i class="pi" :class="source.kind === 'server' ? 'pi-server' : 'pi-file'" />
        <div class="rc__file-name">
          <b dir="ltr">{{ source.name }}</b>
          <small>{{ source.kind === 'server' ? t('backup.restore.fromServer') : t('backup.restore.fromFile') }} · {{ formatSize(source.size) }}</small>
        </div>
        <Button icon="pi pi-times" text rounded size="small" severity="secondary" :aria-label="t('backup.restore.change')" v-tooltip.top="t('backup.restore.change')" :disabled="busy" @click="clear" />
      </div>

      <div v-if="reading" class="rc__counts">
        <Skeleton v-for="i in 4" :key="i" height="3.2rem" border-radius="12px" />
      </div>
      <template v-else-if="summary">
        <div class="rc__counts">
          <div v-for="c in counts" :key="c.key" class="rc__count">
            <i :class="c.icon" />
            <b>{{ c.n.toLocaleString() }}</b>
            <span>{{ t(`backup.count.${c.key}`) }}</span>
          </div>
        </div>
        <p v-if="summary.domain_names.length" class="rc__domains" dir="ltr">{{ summary.domain_names.join(' · ') }}<template v-if="summary.domains > summary.domain_names.length"> …</template></p>
      </template>
    </div>

    <Message v-if="error" severity="error" :closable="false" size="small">{{ error }}</Message>

    <!-- 3. What to restore -->
    <template v-if="summary">
      <div class="rc__parts">
        <label v-for="p in PARTS" :key="p.key" class="rc__part" :class="{ 'rc__part--on': options[p.key] }">
          <span class="rc__part-icon"><i :class="p.icon" /></span>
          <span class="rc__part-text">
            <b>{{ t(`backup.restore.part.${p.key}`) }}</b>
            <small>{{ t(`backup.restore.part.${p.key}Hint`) }}</small>
          </span>
          <ToggleSwitch v-model="options[p.key]" :disabled="busy" />
        </label>
      </div>

      <button type="button" class="rc__adv" :aria-expanded="showAdvanced" @click="showAdvanced = !showAdvanced">
        <i class="pi pi-sliders-h" />{{ t('backup.restore.advanced') }}<i class="pi rc__chev" :class="showAdvanced ? 'pi-chevron-up' : 'pi-chevron-down'" />
      </button>
      <label v-if="showAdvanced" class="rc__part rc__part--plain">
        <span class="rc__part-icon"><i class="pi pi-id-card" /></span>
        <span class="rc__part-text">
          <b>{{ t('backup.restore.replaceOwner') }}</b>
          <small>{{ t('backup.restore.replaceOwnerHint') }}</small>
        </span>
        <ToggleSwitch v-model="options.replace_owner_admin" :disabled="busy" />
      </label>

      <Message v-if="summary.admin_path_changes && options.settings" severity="warn" :closable="false" size="small" icon="pi pi-link">{{ t('backup.restore.pathChanges') }}</Message>
      <Message severity="secondary" :closable="false" size="small" icon="pi pi-info-circle">{{ t('backup.restore.whatHappens') }}</Message>

      <div class="rc__actions">
        <Button :label="t('backup.restore.run')" icon="pi pi-replay" severity="danger" :loading="busy" :disabled="!anyPart" @click="start" />
      </div>
    </template>
  </section>
</template>

<style scoped>
.rc {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 18px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.rc__head {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.rc__icon {
  flex-shrink: 0;
  width: 2.7rem;
  height: 2.7rem;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: var(--p-amber-600, #d97706);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 15%, transparent);
}
.rc__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
}
.rc__sub {
  margin: 0.15rem 0 0;
  font-size: 0.84rem;
  color: var(--p-text-muted-color);
}
.rc__drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 2rem 1rem;
  border-radius: 16px;
  border: 2px dashed var(--p-content-border-color);
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.rc__drop:hover,
.rc__drop--over {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 6%, transparent);
}
.rc__drop-icon {
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  margin-bottom: 0.3rem;
  font-size: 1.35rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.rc__drop--over .rc__drop-icon {
  animation: rc-bounce 0.6s ease infinite alternate;
}
.rc__drop small {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}
.rc__file {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.85rem;
  border-radius: 14px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
}
.rc__file-head {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;
}
.rc__file-head > i {
  font-size: 1.2rem;
  color: var(--p-primary-color);
}
.rc__file-name {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.rc__file-name b {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.86rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
.rc__file-name small {
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
}
.rc__counts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(7.2rem, 1fr));
  gap: 0.45rem;
}
.rc__count {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 0.5rem;
  align-items: center;
  padding: 0.5rem 0.65rem;
  border-radius: 12px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.rc__count i {
  grid-row: span 2;
  color: var(--p-primary-color);
}
.rc__count b {
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
}
.rc__count span {
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
}
.rc__domains {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
.rc__parts {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.rc__part {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.8rem;
  border-radius: 13px;
  border: 1px solid var(--p-content-border-color);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.rc__part--on {
  border-color: color-mix(in srgb, var(--p-primary-color) 45%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-primary-color) 5%, transparent);
}
.rc__part-icon {
  flex-shrink: 0;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.rc__part--on .rc__part-icon {
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 13%, transparent);
}
.rc__part-text {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  flex: 1;
  min-width: 0;
}
.rc__part-text b {
  font-size: 0.9rem;
}
.rc__part-text small {
  font-size: 0.76rem;
  line-height: 1.35;
  color: var(--p-text-muted-color);
}
.rc__adv {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  align-self: flex-start;
  padding: 0.2rem 0.1rem;
  border: 0;
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
}
.rc__adv:hover {
  color: var(--p-primary-color);
}
.rc__chev {
  font-size: 0.7rem;
}
.rc__actions {
  display: flex;
  justify-content: flex-end;
}
@keyframes rc-bounce {
  to {
    transform: translateY(-4px);
  }
}
@media (max-width: 640px) {
  .rc {
    padding: 1rem;
  }
  .rc__actions .p-button {
    width: 100%;
  }
}
@media (prefers-reduced-motion: reduce) {
  .rc__drop--over .rc__drop-icon {
    animation: none;
  }
}
</style>
