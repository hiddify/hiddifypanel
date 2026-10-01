<script setup lang="ts">
/**
 * Custom proxies for a domain. Nothing picked = automatic: every proxy that fits this domain (SNI proxies
 * only when picked). The rule: one SNI gateway proxy, or L7 proxies, never both; IP-based ones go with either.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { DomainProxy } from '@/features/domains/api'

const props = defineProps<{ proxies: DomainProxy[]; compatibleIds: number[]; reality: boolean }>()
const model = defineModel<number[]>({ required: true })
/** "Choose" is kept open while nothing is ticked yet. */
const choosing = defineModel<boolean>('choosing', { default: false })
const { t } = useI18n()

const byId = computed(() => new Map(props.proxies.map((p) => [p.id, p])))
const compatible = computed(() => {
  const ids = new Set(props.compatibleIds)
  return props.proxies.filter((p) => ids.has(p.id) || model.value.includes(p.id))
})
type Kind = DomainProxy['kind']
const GROUPS: { kind: Kind; icon: string }[] = [
  { kind: 'sni', icon: 'pi pi-directions' },
  { kind: 'ip', icon: 'pi pi-server' },
  { kind: 'l7', icon: 'pi pi-sitemap' },
]
const groups = computed(() =>
  GROUPS.map((g) => ({ ...g, items: compatible.value.filter((p) => p.kind === g.kind && !(props.reality && g.kind === 'sni')) })).filter((g) => g.items.length),
)

const mode = computed<'auto' | 'pick'>(() => (model.value.length || choosing.value ? 'pick' : 'auto'))
const picked = computed(() => model.value.map((id) => byId.value.get(id)).filter(Boolean) as DomainProxy[])
const hasSni = computed(() => picked.value.some((p) => p.kind === 'sni'))
const hasL7 = computed(() => picked.value.some((p) => p.kind === 'l7'))

function setMode(m: 'auto' | 'pick') {
  choosing.value = m === 'pick'
  if (m === 'auto') model.value = []
}

function toggle(p: DomainProxy) {
  const on = model.value.includes(p.id)
  let ids = model.value.filter((id) => id !== p.id)
  if (!on) {
    // One SNI proxy at most, and never together with L7 ones.
    if (p.kind === 'sni') ids = ids.filter((id) => byId.value.get(id)?.kind === 'ip')
    if (p.kind === 'l7') ids = ids.filter((id) => byId.value.get(id)?.kind !== 'sni')
    ids.push(p.id)
  }
  model.value = ids
  choosing.value = true
}

function allOn(items: DomainProxy[]): boolean {
  return items.every((p) => model.value.includes(p.id))
}

/** Tick (or untick) a whole group; ticking L7 ones drops the SNI proxy. */
function toggleAll(items: DomainProxy[]) {
  const ids = items.map((p) => p.id)
  if (allOn(items)) {
    model.value = model.value.filter((id) => !ids.includes(id))
  } else {
    let keep = model.value.filter((id) => !ids.includes(id))
    if (items.some((p) => p.kind === 'l7')) keep = keep.filter((id) => byId.value.get(id)?.kind !== 'sni')
    model.value = [...keep, ...ids]
  }
  choosing.value = true
}

function blocked(p: DomainProxy): boolean {
  return !model.value.includes(p.id) && ((p.kind === 'l7' && hasSni.value) || (p.kind === 'sni' && hasL7.value))
}
</script>

<template>
  <div class="pp">
    <div class="pp__choices" role="radiogroup">
      <button type="button" role="radio" class="pp__choice" :class="{ 'pp__choice--on': mode === 'auto' }" :aria-checked="mode === 'auto'" @click="setMode('auto')">
        <i class="pi pi-sparkles" />
        <span class="pp__choice-text">
          <b>{{ t('domains.proxies.auto') }}</b>
          <small>{{ t('domains.proxies.autoHint') }}</small>
        </span>
      </button>
      <button
        type="button"
        role="radio"
        class="pp__choice"
        :class="{ 'pp__choice--on': mode === 'pick' }"
        :aria-checked="mode === 'pick'"
        :disabled="!groups.length"
        @click="setMode('pick')"
      >
        <i class="pi pi-list-check" />
        <span class="pp__choice-text">
          <b>{{ t('domains.proxies.pick') }}</b>
          <small>{{ t('domains.proxies.pickHint') }}</small>
        </span>
      </button>
    </div>

    <div v-if="mode === 'pick'" class="pp__groups">
      <div v-for="g in groups" :key="g.kind" class="pp__group">
        <div class="pp__group-head">
          <span class="pp__group-title"><i :class="g.icon" />{{ t(`domains.proxies.group.${g.kind}`) }}<small v-if="g.kind === 'sni'">{{ t('domains.proxies.sniOne') }}</small></span>
          <button v-if="g.kind !== 'sni' && g.items.length > 1" type="button" class="pp__all" @click="toggleAll(g.items)">
            {{ allOn(g.items) ? t('domains.proxies.selectNone') : t('domains.proxies.selectAll') }}
          </button>
        </div>
        <div class="pp__list">
          <button
            v-for="p in g.items"
            :key="p.id"
            type="button"
            :role="g.kind === 'sni' ? 'radio' : 'checkbox'"
            class="pp__item"
            :class="{ 'pp__item--on': model.includes(p.id), 'pp__item--off': !p.enabled, 'pp__item--blocked': blocked(p) }"
            :aria-checked="model.includes(p.id)"
            v-tooltip.top="blocked(p) ? t('domains.proxies.rule') : undefined"
            @click="toggle(p)"
          >
            <i class="pi" :class="g.kind === 'sni' ? (model.includes(p.id) ? 'pi-circle-fill' : 'pi-circle') : model.includes(p.id) ? 'pi-check-square' : 'pi-stop'" />
            <span class="pp__name">{{ p.name }}</span>
            <span v-if="!p.enabled" class="pp__tag pp__tag--off">{{ t('domains.proxies.off') }}</span>
          </button>
        </div>
      </div>
      <p v-if="!model.length" class="pp__note"><i class="pi pi-info-circle" />{{ t('domains.proxies.noneTicked') }}</p>
    </div>
    <p v-if="!props.reality && groups.some((g) => g.kind === 'sni')" class="pp__rule"><i class="pi pi-shield" />{{ t('domains.proxies.rule') }}</p>
    <p v-if="!groups.length" class="pp__note"><i class="pi pi-info-circle" />{{ t('domains.proxies.noneFit') }}</p>
  </div>
</template>

<style scoped>
.pp {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.pp__choices {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
}
.pp__choice {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.6rem 0.7rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  text-align: start;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}
.pp__choice > i {
  margin-top: 0.15rem;
  color: var(--p-text-muted-color);
}
.pp__choice--on {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--p-content-background));
}
.pp__choice--on > i {
  color: var(--p-primary-color);
}
.pp__choice-text {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}
.pp__choice-text b {
  font-size: 0.86rem;
  font-weight: 600;
}
.pp__choice-text small {
  font-size: 0.74rem;
  color: var(--p-text-muted-color);
  line-height: 1.3;
}
.pp__choice:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.pp__groups {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 0.75rem 0.85rem;
  border-radius: 12px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.06));
}
.pp__group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.pp__group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.pp__all {
  padding: 0.1rem 0.5rem;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
}
.pp__all:hover {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.pp__group-title {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.pp__group-title i {
  font-size: 0.75rem;
}
.pp__group-title small {
  font-weight: 400;
}
.pp__item--blocked {
  opacity: 0.45;
}
.pp__list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.pp__item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  max-width: 100%;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-color);
  font: inherit;
  font-size: 0.84rem;
  cursor: pointer;
}
.pp__item i {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.pp__item--on {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, var(--p-content-background));
}
.pp__item--on i {
  color: var(--p-primary-color);
}
.pp__item--off .pp__name {
  opacity: 0.6;
}
.pp__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pp__tag {
  padding: 0 0.4rem;
  border-radius: 999px;
  font-size: 0.66rem;
  font-weight: 600;
  color: var(--p-violet-600, #7c3aed);
  background: color-mix(in srgb, var(--p-violet-500, #8b5cf6) 14%, transparent);
}
.pp__tag--off {
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
}
.pp__note,
.pp__rule {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  margin: 0;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.pp__note i,
.pp__rule i {
  margin-top: 0.1rem;
  font-size: 0.8rem;
}
.pp-fade-enter-active {
  transition: opacity 0.2s ease;
}
.pp-fade-enter-from {
  opacity: 0;
}
</style>
