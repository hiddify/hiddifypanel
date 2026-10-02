<template>
  <div class="bk-page">
    <PageHeader :title="t('backup.title')" :subtitle="t('backup.subtitle')" />

    <div v-if="loading" class="bk-grid">
      <Skeleton height="17rem" border-radius="18px" />
      <Skeleton height="17rem" border-radius="18px" />
    </div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="state">
      <div class="bk-grid">
        <!-- Download -->
        <section class="bk-card bk-card--save">
          <header class="bk-card__head">
            <span class="bk-card__icon"><i class="pi pi-download" /></span>
            <div>
              <h3 class="bk-card__title">{{ t('backup.save.title') }}</h3>
              <p class="bk-card__sub">{{ t('backup.save.sub') }}</p>
            </div>
          </header>

          <div class="bk-counts">
            <div v-for="c in counts" :key="c.key" class="bk-count">
              <i :class="c.icon" />
              <b>{{ c.n.toLocaleString() }}</b>
              <span>{{ t(`backup.count.${c.key}`) }}</span>
            </div>
          </div>

          <p class="bk-secret"><i class="pi pi-lock" />{{ t('backup.save.secret') }}</p>

          <div class="bk-card__actions">
            <Button :label="t('backup.save.download')" icon="pi pi-download" :loading="downloading" class="bk-main-btn" @click="download" />
            <Button :label="t('backup.save.onServer')" icon="pi pi-server" severity="secondary" outlined :loading="creating" @click="createOnServer" />
          </div>
        </section>

        <!-- Restore -->
        <RestoreCard v-model:source="restoreSource" />
      </div>

      <!-- Automatic backups on the server -->
      <section ref="historyEl" class="bk-card bk-history">
        <header class="bk-card__head">
          <span class="bk-card__icon bk-card__icon--auto"><i class="pi pi-clock" /></span>
          <div class="flex-1 min-w-0">
            <h3 class="bk-card__title">{{ t('backup.auto.title') }}</h3>
            <p class="bk-card__sub">{{ t('backup.auto.sub') }}</p>
          </div>
          <span v-if="state.files.length" class="bk-history__count">{{ state.files.length }}</span>
        </header>

        <!-- Telegram delivery -->
        <div v-if="state.telegram.bot" class="bk-tg" :class="{ 'bk-tg--on': state.telegram.connected }">
          <i class="pi pi-send" />
          <span>{{ state.telegram.connected ? t('backup.auto.telegramOn') : t('backup.auto.telegramOff') }}</span>
          <RouterLink v-if="!state.telegram.connected" to="/account" class="bk-tg__link">{{ t('backup.auto.connect') }}</RouterLink>
        </div>

        <p v-if="!state.files.length" class="bk-empty"><i class="pi pi-inbox" />{{ t('backup.auto.empty') }}</p>
        <TransitionGroup v-else name="bk-row" tag="ul" class="bk-files">
          <li v-for="(f, i) in shownFiles" :key="f.name" class="bk-file" :class="{ 'bk-file--new': f.name === justCreated, 'bk-file--latest': i === 0 }">
            <span class="bk-file__icon"><i class="pi pi-file" /></span>
            <div class="bk-file__body">
              <b>{{ when(f.created) }}</b>
              <small>{{ new Date(f.created).toLocaleString() }} · {{ formatSize(f.size) }}</small>
            </div>
            <span v-if="i === 0" class="bk-file__tag">{{ t('backup.auto.latest') }}</span>
            <div class="bk-file__actions">
              <Button icon="pi pi-download" text rounded size="small" :aria-label="t('backup.auto.download')" v-tooltip.top="t('backup.auto.download')" @click="downloadFile(f)" />
              <Button icon="pi pi-replay" text rounded size="small" severity="secondary" :aria-label="t('backup.auto.restore')" v-tooltip.top="t('backup.auto.restore')" @click="restoreFrom(f)" />
              <Button icon="pi pi-trash" text rounded size="small" severity="danger" :aria-label="t('common.delete')" v-tooltip.top="t('common.delete')" @click="confirmDelete(f)" />
            </div>
          </li>
        </TransitionGroup>
        <Button
          v-if="state.files.length > PAGE"
          :label="showAll ? t('backup.auto.showLess') : t('backup.auto.showAll', { n: state.files.length })"
          :icon="showAll ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          text
          size="small"
          class="self-center"
          @click="showAll = !showAll"
        />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import PageHeader from '@/shared/components/PageHeader.vue'
import { useDangerConfirm } from '@/shared/composables/useDangerConfirm'
import { apiErrorMessage } from '@/core/api/client'
import RestoreCard from '@/features/backup/components/RestoreCard.vue'
import { backupApi, formatSize, type BackupFile, type BackupState, type RestoreSource } from '@/features/backup/api'

const PAGE = 5
const { t, locale } = useI18n()
const toast = useToast()
const dangerConfirm = useDangerConfirm()

const state = ref<BackupState | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const downloading = ref(false)
const creating = ref(false)
const justCreated = ref<string | null>(null)
const showAll = ref(false)
const restoreSource = ref<RestoreSource | null>(null)
const historyEl = ref<HTMLElement | null>(null)

const counts = computed(() => {
  const c = state.value?.current
  if (!c) return []
  return [
    { key: 'users', icon: 'pi pi-users', n: c.users },
    { key: 'admins', icon: 'pi pi-user-edit', n: c.admins },
    { key: 'domains', icon: 'pi pi-globe', n: c.domains },
    { key: 'custom_proxies', icon: 'pi pi-sitemap', n: c.custom_proxies },
    { key: 'nodes', icon: 'pi pi-server', n: c.nodes },
  ].filter((x) => x.n > 0 || x.key === 'users')
})
const shownFiles = computed(() => (showAll.value ? state.value?.files ?? [] : (state.value?.files ?? []).slice(0, PAGE)))

/** "3 hours ago", "yesterday". */
function when(iso: string): string {
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  const [unit, size] = units.find(([, s]) => Math.abs(seconds) >= s) ?? ['minute', 60]
  return rtf.format(Math.round(seconds / size), unit)
}

async function load() {
  loading.value = true
  loadError.value = null
  try {
    state.value = await backupApi.state()
  } catch (err) {
    loadError.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}

async function download() {
  downloading.value = true
  try {
    await backupApi.download()
    toast.add({ severity: 'success', summary: t('backup.save.downloaded'), life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: t('backup.save.failed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    downloading.value = false
  }
}

async function createOnServer() {
  creating.value = true
  try {
    state.value = await backupApi.createOnServer()
    justCreated.value = state.value.created ?? null
    window.setTimeout(() => (justCreated.value = null), 2500)
    toast.add({ severity: 'success', summary: t('backup.save.created'), life: 3000 })
    await nextTick()
    historyEl.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  } catch (err) {
    toast.add({ severity: 'error', summary: t('backup.save.failed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    creating.value = false
  }
}

async function downloadFile(f: BackupFile) {
  try {
    await backupApi.downloadFile(f.name)
  } catch (err) {
    toast.add({ severity: 'error', summary: t('backup.save.failed'), detail: apiErrorMessage(err), life: 6000 })
  }
}

function restoreFrom(f: BackupFile) {
  restoreSource.value = { kind: 'server', name: f.name, size: f.size }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function confirmDelete(f: BackupFile) {
  dangerConfirm({
    header: t('backup.auto.deleteTitle'),
    message: t('backup.auto.deleteMessage', { when: new Date(f.created).toLocaleString() }),
    acceptLabel: t('common.delete'),
    accept: async () => {
      try {
        state.value = await backupApi.removeFile(f.name)
        if (restoreSource.value?.kind === 'server' && restoreSource.value.name === f.name) restoreSource.value = null
      } catch (err) {
        toast.add({ severity: 'error', summary: t('backup.auto.deleteFailed'), detail: apiErrorMessage(err), life: 6000 })
      }
    },
  })
}

onMounted(load)
</script>

<style scoped>
.bk-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
  align-items: start;
  margin-bottom: 1.25rem;
}
.bk-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 18px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  animation: bk-in 0.4s ease both;
}
.bk-card--save {
  background:
    radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--p-primary-color) 12%, transparent), transparent 55%),
    var(--p-content-background);
}
.bk-card__head {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.bk-card__icon {
  flex-shrink: 0;
  width: 2.7rem;
  height: 2.7rem;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.bk-card__icon--auto {
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 14%, transparent);
}
.bk-card__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
}
.bk-card__sub {
  margin: 0.15rem 0 0;
  font-size: 0.84rem;
  color: var(--p-text-muted-color);
}
.bk-counts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(7.2rem, 1fr));
  gap: 0.45rem;
}
.bk-count {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 0.55rem;
  align-items: center;
  padding: 0.6rem 0.7rem;
  border-radius: 13px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
}
.bk-count i {
  grid-row: span 2;
  font-size: 1rem;
  color: var(--p-primary-color);
}
.bk-count b {
  font-size: 1.1rem;
  font-variant-numeric: tabular-nums;
}
.bk-count span {
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
}
.bk-secret {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.8rem;
  color: var(--p-amber-700, #b45309);
}
.bk-secret i {
  margin-top: 0.15rem;
  font-size: 0.8rem;
}
.bk-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.bk-main-btn {
  flex: 1 1 auto;
}
.bk-history__count {
  padding: 0.1rem 0.6rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.bk-tg {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.85rem;
  border-radius: 12px;
  font-size: 0.84rem;
  color: #1d8cc4;
  background: color-mix(in srgb, #229ed9 10%, transparent);
}
.bk-tg--on {
  color: var(--p-green-700, #15803d);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 10%, transparent);
}
.bk-tg__link {
  margin-inline-start: auto;
  font-weight: 600;
  color: inherit;
}
.bk-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin: 0;
  padding: 1.5rem 0;
  color: var(--p-text-muted-color);
}
.bk-files {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}
.bk-file {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.65rem 0.4rem;
  border-radius: 12px;
  transition: background 0.2s ease;
}
.bk-file + .bk-file {
  border-top: 1px solid var(--p-content-border-color);
}
.bk-file:hover {
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.05));
}
.bk-file--new {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.bk-file__icon {
  flex-shrink: 0;
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.bk-file--latest .bk-file__icon {
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 13%, transparent);
}
.bk-file__body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}
.bk-file__body b {
  font-size: 0.9rem;
}
.bk-file__body small {
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bk-file__tag {
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 13%, transparent);
}
.bk-file__actions {
  display: flex;
}
@keyframes bk-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.bk-row-move {
  transition: transform 0.3s ease;
}
.bk-row-enter-active,
.bk-row-leave-active {
  transition: opacity 0.25s ease;
}
.bk-row-enter-from,
.bk-row-leave-to {
  opacity: 0;
}
@media (max-width: 900px) {
  .bk-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 640px) {
  .bk-card {
    padding: 1rem;
  }
  .bk-card__actions .p-button {
    width: 100%;
  }
  .bk-file__tag {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .bk-card {
    animation: none;
  }
}
</style>
