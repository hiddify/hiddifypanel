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
        <NodeSyncTile v-for="tile in tiles" :key="tile.kind" :tile="tile" :ago="ago" :absolute="absolute" />
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
      <ol v-else class="ns__log">
        <li v-for="(e, i) in data?.log ?? []" :key="i" class="ns__log-row" :class="{ 'ns__log-row--bad': !e.ok }">
          <i :class="e.ok ? 'pi pi-check-circle' : 'pi pi-times-circle'" />
          <span class="ns__log-kind">{{ t(`nodeSync.kind.${e.kind}`) }}</span>
          <span class="ns__chip">{{ t(`nodeSync.source.${e.source}`) }}</span>
          <span v-if="e.count !== null" class="ns__mono">{{ e.count }}</span>
          <span v-if="Object.keys(e.detail).length" class="ns__log-detail ns__mono">{{ detailText(e.detail) }}</span>
          <span class="ns__log-time" :title="absolute(e.at)">{{ ago(e.at) }}</span>
        </li>
      </ol>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import Tag from 'primevue/tag'
import NodeSyncTile from '@/features/node-home/components/NodeSyncTile.vue'
import { SYNC_KINDS, nodeSyncApi, type FeedCursor, type NodeSyncEntry } from '@/features/node-home/api'
import { useNodeSyncStatus, type NodeSyncLoader } from '@/features/node-home/composables/useNodeSyncStatus'
import { useServerClock } from '@/features/node-home/composables/useServerClock'
import { buildTiles, type SyncTile } from '@/features/node-home/sync-tiles'

const props = withDefaults(defineProps<{ loader?: NodeSyncLoader; embedded?: boolean }>(), { loader: () => nodeSyncApi.status(), embedded: false })

const { t, locale } = useI18n()
const { data, loading, error, auto, load } = useNodeSyncStatus(props.loader)
const { ago, absolute, age } = useServerClock(computed(() => data.value?.server_time))

const loadingKinds = SYNC_KINDS
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

function detailText(detail: NodeSyncEntry['detail']): string {
  return Object.entries(detail)
    .map(([k, v]) => `${k}=${v}`)
    .join(' ')
}

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
.ns__chip {
  font-size: 0.72rem;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: var(--p-content-hover-background);
  color: var(--p-text-muted-color);
  white-space: nowrap;
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
}
.ns__log-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.6rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
  font-size: 0.85rem;
}
.ns__log-row:last-child {
  border-bottom: 0;
}
.ns__log-row > .pi {
  color: var(--p-green-500);
}
.ns__log-row--bad > .pi {
  color: var(--p-red-500);
}
.ns__log-kind {
  font-weight: 600;
}
.ns__log-detail {
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}
.ns__log-time {
  margin-inline-start: auto;
  color: var(--p-text-muted-color);
  font-size: 0.78rem;
  white-space: nowrap;
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
