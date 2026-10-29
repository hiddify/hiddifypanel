<template>
  <section class="ns" :class="{ 'ns--embedded': embedded }">
    <header class="ns__head">
      <div v-if="!embedded" class="min-w-0">
        <h2 class="ns__title">{{ t('nodeSync.title') }}</h2>
        <p class="ns__sub">{{ t('nodeSync.subtitle') }}</p>
      </div>
      <div class="ns__actions">
        <span v-if="data" class="ns__meta">{{ t('nodeSync.took', { ms: data.took_ms }) }}</span>
        <Button
          size="small"
          :icon="auto ? 'pi pi-pause' : 'pi pi-play'"
          :label="auto ? t('nodeSync.autoOn') : t('nodeSync.autoOff')"
          severity="secondary"
          text
          @click="auto = !auto"
        />
        <Button size="small" icon="pi pi-refresh" :loading="loading" :aria-label="t('nodeSync.refresh')" outlined @click="load" />
      </div>
    </header>

    <Message v-if="error" severity="error" :closable="false" class="mb-3">{{ error }}</Message>
    <Message v-if="data?.error" severity="warn" :closable="false" class="mb-3">{{ data.error }}</Message>

    <!-- What this node holds, and when each kind last came -->
    <div class="ns__grid">
      <template v-if="data">
        <NodeSyncTile
          v-for="tile in tiles"
          :key="tile.kind"
          :tile="tile"
          :ago="ago"
          :absolute="absolute"
          :clickable="listable(tile.kind)"
          @open="openList(tile.kind)"
        />
      </template>
      <Skeleton v-for="kind in loadingKinds" v-else :key="kind" height="10rem" border-radius="12px" />
    </div>

    <div class="ns__cols">
      <!-- Link to the parent -->
      <article class="ns__card">
        <h3 class="ns__card-title"><i class="pi pi-link" /> {{ t('nodeSync.link') }}</h3>
        <dl class="ns__dl">
          <dt>{{ t('nodeSync.websocket') }}</dt>
          <dd>
            <Tag v-if="ws" :severity="ws.connected ? 'success' : 'danger'" :value="ws.connected ? t('nodeSync.connected') : t('nodeSync.disconnected')" />
            <span v-else class="text-muted-color">{{ t('nodeSync.noWs') }}</span>
            <span v-if="ws?.transport" class="ns__mono ms-2">{{ ws.transport }}</span>
          </dd>
          <template v-if="ws?.connected && ws.connected_since">
            <dt>{{ t('nodeSync.connectedSince') }}</dt>
            <dd :title="absolute(ws.connected_since)">{{ ago(ws.connected_since) }}</dd>
          </template>
          <template v-if="ws?.host">
            <dt>{{ t('nodeSync.host') }}</dt>
            <dd class="ns__mono">{{ ws.host }}</dd>
          </template>
          <template v-if="ws?.last_batch_at">
            <dt>{{ t('nodeSync.lastBatch') }}</dt>
            <dd :title="absolute(ws.last_batch_at)">{{ ago(ws.last_batch_at) }} · {{ t('nodeSync.rows', { n: ws.rows ?? 0 }) }}</dd>
          </template>
          <template v-if="ws?.last_http_sync">
            <dt>{{ t('nodeSync.lastHttpSync') }}</dt>
            <dd :title="absolute(ws.last_http_sync)">{{ ago(ws.last_http_sync) }}</dd>
          </template>
          <template v-if="ws?.last_error">
            <dt>{{ t('nodeSync.lastError') }}</dt>
            <dd class="ns__mono ns__wrap text-red-500">{{ ws.last_error }}</dd>
          </template>
          <template v-if="data?.parent.last_users_sync">
            <dt>{{ t('nodeSync.lastUsage') }}</dt>
            <dd class="ns__mono">{{ data.parent.last_users_sync }}</dd>
          </template>
        </dl>
      </article>

      <!-- Ids, for comparing with the parent -->
      <article class="ns__card">
        <h3 class="ns__card-title"><i class="pi pi-id-card" /> {{ t('nodeSync.ids') }}</h3>
        <dl class="ns__dl">
          <dt>{{ t('nodeSync.parentUrl') }}</dt>
          <dd class="ns__mono ns__wrap">{{ data?.parent.url || '—' }}</dd>
         
          <dt>{{ t('nodeSync.cursor') }}</dt>
          <dd class="ns__mono ns__wrap">{{ cursorText }}</dd>
        </dl>
      </article>
    </div>

    <!-- Recent syncs -->
    <article class="ns__card">
      <h3 class="ns__card-title"><i class="pi pi-history" /> {{ t('nodeSync.recent') }}</h3>
      <p v-if="data && !data.log.length" class="text-muted-color m-0">{{ t('nodeSync.noLog') }}</p>
      <!-- Each sync in words; opened: what it carried, by name (the JSON behind "Technical data") -->
      <ol v-else class="ns__log">
        <SyncLogEntry
          v-for="e in data?.log ?? []"
          :key="entryKey(e)"
          :entry="e"
          :open="openRow === entryKey(e)"
          :users="data?.users"
          :admins="data?.admins"
          :ago="ago(e.at)"
          :at="absolute(e.at)"
          @toggle="openRow = openRow === entryKey(e) ? '' : entryKey(e)"
        />
      </ol>
    </article>

    <!-- The node's users / admins, as it has them -->
    <Dialog v-model:visible="listVisible" modal :header="listKind === 'users' ? t('nodeSync.usersOnNode') : t('nodeSync.adminsOnNode')" :style="{ width: 'min(44rem, 96vw)' }">
      <div class="ns__list-bar">
        <IconField class="ns__list-search">
          <InputIcon class="pi pi-search" />
          <InputText v-model="listQuery" :placeholder="t('nodeSync.search')" class="w-full" />
        </IconField>
        <SelectButton v-if="listKind === 'users'" v-model="userFilter" :options="userFilters" option-label="label" option-value="value" size="small" :allow-empty="false" />
      </div>
      <ul class="ns__list">
        <template v-if="listKind === 'users'">
          <li v-for="u in shownUsers" :key="u.uuid" class="ns__list-row">
            <Tag :severity="u.is_active ? 'success' : u.enable ? 'warn' : 'secondary'" :value="u.is_active ? t('nodeSync.active') : u.enable ? t('nodeSync.inactive') : t('nodeSync.disabled')" />
            <b class="ns__list-name">{{ u.name }}</b>
            <span class="ns__mono text-muted-color">{{ u.uuid.slice(0, 8) }}</span>
            <span v-if="u.owner" class="ns__list-extra"><i class="pi pi-sitemap" /> {{ u.owner }}</span>
          </li>
        </template>
        <template v-else>
          <li v-for="a in shownAdmins" :key="a.uuid" class="ns__list-row">
            <Tag severity="info" :value="a.mode" />
            <b class="ns__list-name">{{ a.name }}</b>
            <span class="ns__mono text-muted-color">{{ a.uuid.slice(0, 8) }}</span>
            <span v-if="a.parent" class="ns__list-extra"><i class="pi pi-sitemap" /> {{ a.parent }}</span>
          </li>
        </template>
        <li v-if="!listCount" class="text-muted-color">{{ t('nodeSync.listEmpty') }}</li>
      </ul>
      <p class="ns__list-foot text-muted-color">
        {{ t('nodeSync.listShown', { n: listCount, total: listTotal }) }}
        <template v-if="listKind === 'users' && data?.users_more"> · {{ t('nodeSync.itemsMore', { n: data.users_more }) }}</template>
      </p>
    </Dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import NodeSyncTile from '@/features/node-home/components/NodeSyncTile.vue'
import SyncLogEntry from '@/features/node-home/components/SyncLogEntry.vue'
import { SYNC_KINDS, nodeSyncApi, type FeedCursor, type NodeSyncEntry } from '@/features/node-home/api'
import { useNodeSyncStatus, type NodeSyncLoader } from '@/features/node-home/composables/useNodeSyncStatus'
import { useServerClock } from '@/features/node-home/composables/useServerClock'
import { buildTiles, type SyncTile } from '@/features/node-home/sync-tiles'

const props = withDefaults(defineProps<{ loader?: NodeSyncLoader; embedded?: boolean }>(), { loader: () => nodeSyncApi.status(), embedded: false })

const { t, locale } = useI18n()
const { data, loading, error, auto, load } = useNodeSyncStatus(props.loader)
const { ago, absolute, age } = useServerClock(computed(() => data.value?.server_time))

const loadingKinds = SYNC_KINDS

// A recent sync opened. Keyed by time + kind + source, as the log refreshes.
const openRow = ref('')
const entryKey = (e: NodeSyncEntry) => `${e.at}:${e.kind}:${e.source}`

// The node's users / admins (in the report of nodes new enough to send them).
type ListKind = 'users' | 'admins'
const listVisible = ref(false)
const listKind = ref<ListKind>('users')
const listQuery = ref('')
const userFilter = ref<'all' | 'active' | 'inactive'>('all')
const userFilters = computed(() => [
  { value: 'all', label: t('nodeSync.all') },
  { value: 'active', label: t('nodeSync.active') },
  { value: 'inactive', label: t('nodeSync.inactive') },
])
function listable(kind: string): kind is ListKind {
  return (kind === 'users' && !!data.value?.users) || (kind === 'admins' && !!data.value?.admins)
}
function openList(kind: string) {
  if (!listable(kind)) return
  listKind.value = kind
  listQuery.value = ''
  listVisible.value = true
}
const matches = (q: string, ...fields: string[]) => !q || fields.some((f) => f.toLowerCase().includes(q))
const shownUsers = computed(() => {
  const q = listQuery.value.trim().toLowerCase()
  return (data.value?.users ?? []).filter(
    (u) => (userFilter.value === 'all' || u.is_active === (userFilter.value === 'active')) && matches(q, u.name, u.uuid, u.owner),
  )
})
const shownAdmins = computed(() => {
  const q = listQuery.value.trim().toLowerCase()
  return (data.value?.admins ?? []).filter((a) => matches(q, a.name, a.uuid, a.mode, a.parent))
})
const listCount = computed(() => (listKind.value === 'users' ? shownUsers.value.length : shownAdmins.value.length))
const listTotal = computed(() => (listKind.value === 'users' ? data.value?.users?.length : data.value?.admins?.length) ?? 0)
const ws = computed(() => data.value?.websocket ?? null)

const tiles = computed<SyncTile[]>(() => {
  if (!data.value) return []
  const number = (n: number) => n.toLocaleString(locale.value)
  return buildTiles(data.value, SYNC_KINDS, age, {
    number,
    active: (n) => t('nodeSync.active', { n }),
    enabled: (n) => t('nodeSync.enabled', { n }),
    deleted: (n) => t('nodeSync.deleted', { n }),
  })
})

function cursorPart(part: FeedCursor['u']): string {
  return part ? part.join(' / ') : '—'
}

const cursorText = computed(() => {
  const cur = data.value?.parent.cursor
  return cur ? `users: ${cursorPart(cur.u)} · admins: ${cursorPart(cur.a)}` : '—'
})
</script>

<style scoped>
.ns {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}
.ns--embedded {
  margin-top: 0;
}
.ns--embedded .ns__head {
  justify-content: flex-end;
}
.ns__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem;
}
.ns__title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
}
.ns__sub {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}
.ns__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.ns__meta {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
}
.ns__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11.5rem, 1fr));
  gap: 0.75rem;
}
.ns__card {
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius, 12px);
  padding: 1rem;
  min-width: 0;
}
.ns__cols {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
  gap: 0.75rem;
}
.ns__card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  font-weight: 600;
}
.ns__dl {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 0.45rem 1rem;
  margin: 0;
  font-size: 0.85rem;
}
.ns__dl dt {
  color: var(--p-text-muted-color);
}
.ns__dl dd {
  margin: 0;
  min-width: 0;
}
.ns__mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
  direction: ltr;
  unicode-bidi: isolate;
}
.ns__wrap {
  overflow-wrap: anywhere;
}
.ns__log {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.ns__list-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.75rem;
}
.ns__list-search {
  flex: 1 1 14rem;
}
.ns__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 60vh;
  overflow: auto;
}
.ns__list-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.6rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
  font-size: 0.85rem;
}
.ns__list-name {
  overflow-wrap: anywhere;
}
.ns__list-extra {
  margin-inline-start: auto;
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}
.ns__list-foot {
  margin: 0.6rem 0 0;
  font-size: 0.8rem;
}
@media (max-width: 575px) {
  .ns__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .ns__dl {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.1rem;
  }
  .ns__dl dd {
    margin-bottom: 0.5rem;
  }
}
</style>
