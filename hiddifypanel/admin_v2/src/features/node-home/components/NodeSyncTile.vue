<template>
  <article
    class="tile"
    :class="[`tile--${tile.state}`, { 'tile--clickable': clickable }]"
    :role="clickable ? 'button' : undefined"
    :tabindex="clickable ? 0 : undefined"
    :title="clickable ? t('nodeSync.showList') : undefined"
    @click="clickable && emit('open')"
    @keydown.enter="clickable && emit('open')"
  >
    <div class="tile__top">
      <span class="tile__icon"><i :class="tile.icon" /></span>
      <span class="tile__label">{{ t(`nodeSync.kind.${tile.kind}`) }}</span>
      <span class="tile__dot" :title="t(`nodeSync.state.${tile.state}`)" />
    </div>
    <div class="tile__count">{{ tile.count === null ? '—' : tile.count.toLocaleString(locale) }}</div>
    <div class="tile__chips">
      <span v-for="chip in tile.chips" :key="chip" class="sync-chip">{{ chip }}</span>
    </div>
    <div class="tile__last">
      <template v-if="tile.last">
        <span :title="absolute(tile.last.at)">{{ ago(tile.last.at) }}</span>
        <span class="tile__source">
          {{ t(`nodeSync.source.${tile.last.source}`) }}<template v-if="tile.last.count !== null"> · {{ tile.last.count }}</template>
        </span>
      </template>
      <span v-else class="text-muted-color">{{ t('nodeSync.never') }}</span>
    </div>
    <div v-if="tile.failure" class="tile__err" :title="String(tile.failure.detail.error ?? '')">
      <i class="pi pi-exclamation-triangle" /> {{ ago(tile.failure.at) }}: {{ tile.failure.detail.error }}
    </div>
  </article>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { SyncTile } from '@/features/node-home/sync-tiles'

defineProps<{
  tile: SyncTile
  ago: (at: number) => string
  absolute: (at: number) => string
  /** Opens the list of what the tile counts (users, admins). */
  clickable?: boolean
}>()
const emit = defineEmits<{ open: [] }>()

const { t, locale } = useI18n()
</script>

<style scoped>
.tile--clickable {
  cursor: pointer;
}
.tile--clickable:hover,
.tile--clickable:focus-visible {
  border-color: var(--p-primary-color);
  outline: none;
}
.tile {
  --tile-accent: var(--p-text-muted-color);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
  padding: 1rem;
  overflow: hidden;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-content-border-radius, 12px);
}
.tile::before {
  content: '';
  position: absolute;
  inset-inline-start: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--tile-accent);
}
.tile--fresh { --tile-accent: var(--p-green-500); }
.tile--stale { --tile-accent: var(--p-amber-500); }
.tile--error { --tile-accent: var(--p-red-500); }
.tile__top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.tile__icon {
  display: inline-grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
  color: var(--p-primary-color);
}
.tile__label {
  flex: 1;
  font-weight: 600;
}
.tile__dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 999px;
  background: var(--tile-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tile-accent) 25%, transparent);
}
.tile__count {
  font-size: 1.9rem;
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.tile__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  min-height: 1.25rem;
}
.sync-chip {
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: var(--p-content-hover-background);
  color: var(--p-text-muted-color);
  font-size: 0.72rem;
  white-space: nowrap;
}
.tile__last {
  display: flex;
  flex-direction: column;
  margin-top: auto;
  font-size: 0.8rem;
}
.tile__source {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}
.tile__err {
  overflow: hidden;
  color: var(--p-red-500);
  font-size: 0.75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 575px) {
  .tile__count {
    font-size: 1.5rem;
  }
}
</style>
