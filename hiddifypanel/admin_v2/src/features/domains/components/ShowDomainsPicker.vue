<script setup lang="ts">
/**
 * Whose configs a sub-link domain shows. Nothing ticked = all domains (now and later).
 * One section per server (this one first, then its nodes); in each, decoy domains (fake TLS / Reality) first, then
 * CDN, then real-certificate ones. Searchable, with quick filters; a server or a group can be ticked at once.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import { KIND_META, kindOf, type DomainsOptions } from '@/features/domains/api'

type ShowOption = DomainsOptions['show_options'][number]
type Group = 'fake' | 'cdn' | 'direct'
type Filter = 'all' | Group | 'selected'

const props = defineProps<{ options: ShowOption[] }>()
const model = defineModel<number[]>({ required: true })
const { t } = useI18n()

const GROUP_ORDER: Group[] = ['fake', 'cdn', 'direct']
const GROUP_ICON: Record<Group, string> = { fake: 'pi pi-eye-slash', cdn: 'pi pi-cloud', direct: 'pi pi-verified' }
const TAG_ICON: Record<string, string> = { reality: 'pi pi-eye-slash', fake: 'pi pi-clone', dns: 'pi pi-database', cdn: 'pi pi-cloud', direct: 'pi pi-verified' }

function groupOf(o: ShowOption): Group {
  if (o.fake_mode !== 'valid') return 'fake'
  return o.mode === 'cdn' || o.mode === 'worker' ? 'cdn' : 'direct'
}
/** The tag on a row: its TLS mode among the decoys (Fake / Reality), its kind otherwise (Direct / Relay / CDN). */
function tagOf(o: ShowOption): string {
  return groupOf(o) === 'fake' ? t(`domains.tlsMode.${o.fake_mode}`) : t(`domains.kind.${kindOf(o.mode)}.name`)
}

/** "All domains" is off while something is ticked, or once the user turned it off. */
const choosing = ref(model.value.length > 0)
const showAll = computed({
  get: () => !model.value.length && !choosing.value,
  set: (on: boolean) => {
    choosing.value = !on
    if (on) model.value = []
  },
})

const query = ref('')
const filter = ref<Filter>('all')
const selected = computed(() => new Set(model.value))

function matches(o: ShowOption): boolean {
  if (filter.value === 'selected' ? !selected.value.has(o.id) : filter.value !== 'all' && groupOf(o) !== filter.value) return false
  const q = query.value.trim().toLowerCase()
  return !q || [o.domain, o.alias, o.node ?? '', o.download ?? ''].some((s) => s.toLowerCase().includes(q))
}

const counts = computed(() => {
  const c: Record<Filter, number> = { all: props.options.length, fake: 0, cdn: 0, direct: 0, selected: model.value.length }
  for (const o of props.options) c[groupOf(o)]++
  return c
})
const filters = computed(() => (['all', 'fake', 'cdn', 'direct', 'selected'] as Filter[]).filter((f) => f === 'all' || counts.value[f] > 0))

/** Every server with its domains (for the counts), and the groups the search and filter keep */
const servers = computed(() => {
  const byNode = new Map<string, ShowOption[]>()
  for (const o of props.options) byNode.set(o.node ?? '', [...(byNode.get(o.node ?? '') ?? []), o])
  return [...byNode.entries()]
    .sort(([a], [b]) => (a === '' ? -1 : b === '' ? 1 : a.localeCompare(b)))
    .map(([node, all]) => {
      const shown = all.filter(matches)
      return {
        node,
        all,
        shown,
        groups: GROUP_ORDER.map((g) => ({ g, items: shown.filter((o) => groupOf(o) === g).sort((a, b) => a.domain.localeCompare(b.domain)) })).filter((x) => x.items.length),
      }
    })
    .filter((s) => s.shown.length)
})
const hasNodes = computed(() => props.options.some((o) => o.node))

/** This server and nodes with something ticked start open; a search or filter opens every server it finds something in. */
const open = ref(new Set<string>(['', ...props.options.filter((o) => o.node && model.value.includes(o.id)).map((o) => o.node as string)]))
const narrowed = computed(() => !!query.value.trim() || filter.value !== 'all')
function isOpen(node: string): boolean {
  return narrowed.value || open.value.has(node)
}
function toggleOpen(node: string) {
  const s = new Set(open.value)
  if (s.has(node)) s.delete(node)
  else s.add(node)
  open.value = s
}

function ticked(items: ShowOption[]): number {
  return items.filter((o) => selected.value.has(o.id)).length
}
function toggle(id: number) {
  model.value = selected.value.has(id) ? model.value.filter((x) => x !== id) : [...model.value, id]
}
function toggleMany(items: ShowOption[]) {
  const ids = items.map((o) => o.id)
  model.value = ticked(items) === items.length ? model.value.filter((id) => !ids.includes(id)) : [...new Set([...model.value, ...ids])]
}
function clear() {
  model.value = []
  if (filter.value === 'selected') filter.value = 'all'
}
</script>

<template>
  <div class="sd">
    <label class="sd__all">
      <ToggleSwitch v-model="showAll" :disabled="!options.length" />
      <span>
        <b>{{ t('domains.show.all') }}</b>
        <small>{{ showAll ? t('domains.show.allHint') : t('domains.show.pickHint') }}</small>
      </span>
    </label>

    <p v-if="!options.length" class="sd__muted"><i class="pi pi-info-circle" />{{ t('domains.show.empty') }}</p>

    <template v-if="!showAll">
      <div class="sd__tools">
        <IconField class="sd__search">
          <InputIcon class="pi pi-search" />
          <InputText v-model="query" :placeholder="t('domains.show.search')" size="small" fluid />
          <InputIcon v-if="query" class="pi pi-times sd__clickable" role="button" :aria-label="t('domains.show.clearSearch')" @click="query = ''" />
        </IconField>
        <div class="sd__filters">
          <button v-for="f in filters" :key="f" type="button" class="sd__filter" :class="{ 'sd__filter--on': filter === f }" :aria-pressed="filter === f" @click="filter = f">
            <i v-if="f !== 'all'" :class="f === 'selected' ? 'pi pi-check' : GROUP_ICON[f]" />{{ t(`domains.show.filter.${f}`) }}
            <span class="sd__n">{{ counts[f] }}</span>
          </button>
        </div>
      </div>

      <div class="sd__status">
        <span>{{ counts.selected ? t('domains.show.selected', { n: counts.selected, total: counts.all }) : t('domains.show.noneTicked') }}</span>
        <button v-if="counts.selected" type="button" class="sd__link" @click="clear">{{ t('domains.show.clear') }}</button>
      </div>

      <div class="sd__servers">
        <section v-for="s in servers" :key="s.node" class="sd__server">
          <div v-if="hasNodes" class="sd__server-head">
            <button type="button" class="sd__fold" :aria-expanded="isOpen(s.node)" @click="toggleOpen(s.node)">
              <i class="pi sd__chev" :class="isOpen(s.node) ? 'pi-chevron-down' : 'pi-chevron-right'" />
              <span class="sd__server-icon" :class="{ 'sd__server-icon--node': s.node }"><i :class="s.node ? 'pi pi-server' : 'pi pi-home'" /></span>
              <span class="sd__server-name" :dir="s.node ? 'ltr' : undefined">{{ s.node || t('domains.show.thisServer') }}</span>
              <span class="sd__server-type">{{ s.node ? t('domains.show.node') : '' }}</span>
              <span class="sd__n" :class="{ 'sd__n--on': ticked(s.all) }">{{ ticked(s.all) }}/{{ s.all.length }}</span>
            </button>
            <Checkbox
              :model-value="ticked(s.shown) === s.shown.length"
              :indeterminate="ticked(s.shown) > 0 && ticked(s.shown) < s.shown.length"
              binary
              :aria-label="t('domains.show.tickServer')"
              @update:model-value="toggleMany(s.shown)"
            />
          </div>

          <div v-if="!hasNodes || isOpen(s.node)" class="sd__body">
            <div v-for="grp in s.groups" :key="grp.g" class="sd__group" :class="`sd__group--${grp.g}`">
              <div class="sd__group-head">
                <span class="sd__group-title"><i :class="GROUP_ICON[grp.g]" />{{ t(`domains.show.group.${grp.g}`) }}</span>
                <button v-if="grp.items.length > 1" type="button" class="sd__link" @click="toggleMany(grp.items)">
                  {{ ticked(grp.items) === grp.items.length ? t('domains.proxies.selectNone') : t('domains.proxies.selectAll') }}
                </button>
              </div>
              <label v-for="o in grp.items" :key="o.id" class="sd__row" :class="{ 'sd__row--on': selected.has(o.id) }">
                <Checkbox :model-value="selected.has(o.id)" binary @update:model-value="toggle(o.id)" />
                <span class="sd__kind" :style="{ '--kind-color': KIND_META[kindOf(o.mode)].color }" v-tooltip.top="t(`domains.kind.${kindOf(o.mode)}.name`)">
                  <i :class="KIND_META[kindOf(o.mode)].icon" />
                </span>
                <span class="sd__name">
                  <span class="sd__domain" dir="ltr">{{ o.domain || t('domains.noName') }}</span>
                  <span v-if="(o.alias && o.alias !== o.domain) || o.download" class="sd__sub">
                    <span v-if="o.alias && o.alias !== o.domain">{{ o.alias }}</span>
                    <span v-if="o.download" dir="ltr" v-tooltip.top="t('domains.field.downloadDomain')"><i class="pi pi-download" />{{ o.download }}</span>
                  </span>
                </span>
                <span class="sd__tag" :class="`sd__tag--${grp.g === 'fake' ? o.fake_mode : grp.g}`"><i :class="TAG_ICON[grp.g === 'fake' ? o.fake_mode : grp.g] ?? 'pi pi-shield'" />{{ tagOf(o) }}</span>
              </label>
            </div>
          </div>
        </section>
        <p v-if="!servers.length" class="sd__muted sd__none"><i class="pi pi-search" />{{ t('domains.show.noMatch') }}</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sd {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.sd__all {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  cursor: pointer;
}
.sd__all > span {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.sd__all b {
  font-size: 0.9rem;
  font-weight: 600;
}
.sd__all small,
.sd__muted,
.sd__status {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.sd__muted {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
}
.sd__none {
  justify-content: center;
  padding: 1rem 0;
}

.sd__tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}
.sd__search {
  flex: 1 1 14rem;
}
.sd__clickable {
  cursor: pointer;
}
.sd__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.sd__filter {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.sd__filter i {
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
}
.sd__filter--on {
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
}
.sd__filter--on i {
  color: inherit;
}
.sd__n {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}
.sd__n--on {
  color: var(--p-primary-color);
  font-weight: 600;
}

.sd__status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.sd__link {
  padding: 0.1rem 0.4rem;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
}
.sd__link:hover {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}

.sd__servers {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.sd__server {
  border: 1px solid var(--p-content-border-color);
  border-radius: 10px;
}
.sd__server-head {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.6rem 0.3rem 0.3rem;
  border-radius: 10px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
}
.sd__fold {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.25rem 0.35rem;
  border: 0;
  background: transparent;
  color: var(--p-text-color);
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.sd__chev {
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}
.sd__server-icon {
  display: grid;
  place-items: center;
  width: 1.65rem;
  height: 1.65rem;
  border-radius: 7px;
  font-size: 0.78rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 13%, transparent);
}
.sd__server-icon--node {
  color: var(--p-cyan-600, #0891b2);
  background: color-mix(in srgb, var(--p-cyan-500, #06b6d4) 13%, transparent);
}
.sd__server-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  font-size: 0.88rem;
}
.sd__server-type {
  flex: 1;
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
}
.sd__body {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.55rem;
}
.sd__server:has(.sd__server-head) .sd__body {
  border-top: 1px solid var(--p-content-border-color);
}
.sd__group {
  --g-color: var(--p-green-500, #22c55e);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding-inline-start: 0.55rem;
  border-inline-start: 3px solid color-mix(in srgb, var(--g-color) 55%, transparent);
}
.sd__group--fake {
  --g-color: var(--p-violet-500, #8b5cf6);
}
.sd__group--cdn {
  --g-color: var(--p-orange-500, #f97316);
}
.sd__group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.sd__group-title {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-text-color);
}
.sd__group-title i {
  font-size: 0.74rem;
  color: var(--g-color);
}
.sd__row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-height: 2.5rem;
  padding: 0.3rem 0.5rem;
  border-radius: 10px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.sd__row:hover {
  border-color: color-mix(in srgb, var(--p-primary-color) 45%, var(--p-content-border-color));
}
.sd__row--on {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--p-content-background));
}
.sd__kind {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.65rem;
  height: 1.65rem;
  border-radius: 7px;
  font-size: 0.78rem;
  color: var(--kind-color);
  background: color-mix(in srgb, var(--kind-color) 14%, transparent);
}
/* the name and its alias / download line start on the same side (also in RTL) */
.sd__name {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.3;
}
.sd__domain {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.83rem;
  font-weight: 600;
}
.sd__sub {
  display: flex;
  flex-wrap: wrap;
  gap: 0 0.6rem;
  max-width: 100%;
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
}
.sd__sub i {
  margin-inline-end: 0.2rem;
  font-size: 0.65rem;
}
.sd__tag {
  --t-color: var(--p-green-600, #16a34a);
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.05rem 0.5rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--t-color);
  background: color-mix(in srgb, var(--t-color) 13%, transparent);
}
.sd__tag i {
  font-size: 0.66rem;
}
.sd__tag--reality {
  --t-color: var(--p-violet-500, #8b5cf6);
}
.sd__tag--fake,
.sd__tag--dns {
  --t-color: var(--p-orange-600, #ea580c);
}
.sd__tag--cdn {
  --t-color: var(--p-orange-500, #f97316);
}

@media (max-width: 560px) {
  .sd__search {
    flex-basis: 100%;
  }
  .sd__filters {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .sd__filter {
    flex: none;
  }
  .sd__row {
    min-height: 2.6rem;
  }
}
</style>
