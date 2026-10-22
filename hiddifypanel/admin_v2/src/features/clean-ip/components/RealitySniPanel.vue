<script setup lang="ts">
/** REALITY SNIs: an overview, where each is filtered (from the SNI tests), the test, the spares and auto switch, the history. */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { apiErrorMessage } from '@/core/api/client'
import { cleanIpApi, type RealityState, type SniStatus } from '../api'
import SniTestCard from './SniTestCard.vue'
import StepHeader from './StepHeader.vue'

const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()
const toast = useToast()

/** The server keeps at most this many spares (clean_ip_api MAX_SPARES). */
const MAX_SPARES = 300
const HOSTNAME = /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/

const reality = ref<RealityState | null>(null)
const error = ref('')
const spares = ref<string[]>([])
const newSpare = ref('')
const autoSwitch = ref(false)
const switchTo = ref<Record<number, string>>({})
const switching = ref<number | null>(null)
const saving = ref(false)

type Health = 'ok' | 'bad' | 'none'

function entries(status: SniStatus) {
  return Object.entries(status).map(([isp, st]) => ({ isp, ok: st.ok }))
}
function health(status: SniStatus): Health {
  const list = entries(status)
  if (!list.length) return 'none'
  return list.every((s) => s.ok) ? 'ok' : 'bad'
}
function filteredOn(status: SniStatus): number {
  return entries(status).filter((s) => !s.ok).length
}

const spareStatus = computed(() => new Map((reality.value?.spares ?? []).map((s) => [s.sni, s.status])))
const spareOptions = computed(() => (reality.value?.spares ?? []).map((s) => ({ sni: s.sni, health: health(s.status) })))
const overview = computed(() => {
  const domains = reality.value?.domains ?? []
  return {
    total: domains.length,
    ok: domains.filter((d) => health(d.status) === 'ok').length,
    bad: domains.filter((d) => health(d.status) === 'bad').length,
  }
})
/** What is typed or pasted: one name or a list (lines, spaces or commas). */
const typedNames = computed(() => [...new Set(newSpare.value.split(/[\s,;]+/).map((x) => x.trim().toLowerCase().replace(/\.$/, '')).filter(Boolean))])
const typedValid = computed(() => typedNames.value.filter((n) => HOSTNAME.test(n)))
const typedInvalid = computed(() => typedNames.value.filter((n) => !HOSTNAME.test(n)))
const dirty = computed(
  () => !!reality.value && (autoSwitch.value !== reality.value.auto || spares.value.join('\n') !== reality.value.spares.map((s) => s.sni).join('\n')),
)

function show(state: RealityState) {
  reality.value = state
  spares.value = state.spares.map((s) => s.sni)
  autoSwitch.value = state.auto
}

async function load() {
  error.value = ''
  try {
    show(await cleanIpApi.reality())
  } catch (e) {
    error.value = apiErrorMessage(e)
  }
}

async function saveSettings() {
  saving.value = true
  try {
    show(await cleanIpApi.saveReality(spares.value, autoSwitch.value))
    toast.add({ severity: 'success', summary: t('cleanIp.settingsSaved'), life: 2500 })
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 5000 })
  } finally {
    saving.value = false
  }
}

/** Adds every valid name typed or pasted; the invalid ones stay in the box to fix. */
function addSpare() {
  if (!typedValid.value.length) return
  const before = spares.value.length
  const merged = [...new Set([...spares.value, ...typedValid.value])]
  spares.value = merged.slice(0, MAX_SPARES)
  const added = spares.value.length - before
  if (merged.length > MAX_SPARES) toast.add({ severity: 'warn', summary: t('cleanIp.sparesFull', { max: MAX_SPARES }), life: 5000 })
  else if (typedValid.value.length > 1) toast.add({ severity: 'info', summary: t('cleanIp.sparesAdded', { count: added }), life: 2500 })
  newSpare.value = typedInvalid.value.join('\n')
}

/** Enter adds, Shift+Enter is a new line (for a list typed by hand). */
function onAddKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    addSpare()
  }
}
function removeSpare(name: string) {
  spares.value = spares.value.filter((s) => s !== name)
}

/** Working candidates from a test become spares (saved at once, with the other settings as they are on screen). */
async function addSpares(names: string[]) {
  spares.value = [...new Set([...spares.value, ...names])].slice(0, MAX_SPARES)
  await saveSettings()
}

async function doSwitch(domainId: number) {
  const sni = (switchTo.value[domainId] || '').trim()
  if (!sni) return
  switching.value = domainId
  try {
    show(await cleanIpApi.switchSni(domainId, sni))
    switchTo.value[domainId] = ''
    toast.add({ severity: 'success', summary: t('cleanIp.switched', { sni }), life: 5000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: apiErrorMessage(e), life: 6000 })
  } finally {
    switching.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="rs">
    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
      <Button :label="t('cleanIp.retry')" size="small" text @click="load" />
    </Message>

    <template v-else-if="!reality">
      <Skeleton height="5.5rem" border-radius="1rem" />
      <Skeleton height="10rem" border-radius="1rem" />
    </template>

    <template v-else>
      <!-- at a glance -->
      <section class="rs__overview">
        <div class="rs__tile">
          <i class="pi pi-shield" />
          <b>{{ overview.total }}</b>
          <span>{{ t('cleanIp.ovSnis') }}</span>
        </div>
        <div class="rs__tile rs__tile--ok">
          <i class="pi pi-check-circle" />
          <b>{{ overview.ok }}</b>
          <span>{{ t('cleanIp.ovHealthy') }}</span>
        </div>
        <div class="rs__tile" :class="{ 'rs__tile--bad': overview.bad }">
          <i class="pi pi-ban" />
          <b>{{ overview.bad }}</b>
          <span>{{ t('cleanIp.ovFiltered') }}</span>
        </div>
        <div class="rs__tile">
          <i class="pi pi-box" />
          <b>{{ reality.spares.length }}</b>
          <span>{{ t('cleanIp.ovSpares') }}</span>
        </div>
        <div class="rs__tile" :class="{ 'rs__tile--ok': reality.auto }">
          <i class="pi pi-bolt" />
          <b>{{ reality.auto ? t('cleanIp.on') : t('cleanIp.off') }}</b>
          <span>{{ t('cleanIp.ovAuto') }}</span>
        </div>
      </section>

      <section class="card rs__card">
        <StepHeader icon="pi pi-shield" :title="t('cleanIp.realityTitle')" :hint="t('cleanIp.realityHint')" />

        <div v-if="!reality.domains.length" class="rs__empty">
          <i class="pi pi-shield" />
          <span>{{ t('cleanIp.noReality') }}</span>
        </div>

        <div class="rs__domains">
          <article v-for="d in reality.domains" :key="d.id" class="rs__domain" :class="`rs__domain--${health(d.status)}`">
            <div class="rs__domain-head">
              <b class="rs__sni" dir="ltr">{{ d.sni }}</b>
              <span class="rs__state">
                <i class="pi" :class="{ ok: 'pi-check-circle', bad: 'pi-exclamation-circle', none: 'pi-question-circle' }[health(d.status)]" />
                {{
                  health(d.status) === 'ok'
                    ? t('cleanIp.stateOk')
                    : health(d.status) === 'bad'
                      ? t('cleanIp.stateBad', { count: filteredOn(d.status) })
                      : t('cleanIp.stateNone')
                }}
              </span>
            </div>
            <div v-if="entries(d.status).length" class="rs__chips">
              <span v-for="s in entries(d.status)" :key="s.isp" class="rs__chip" :class="s.ok ? 'rs__chip--ok' : 'rs__chip--bad'">
                <i class="pi" :class="s.ok ? 'pi-check' : 'pi-times'" /> {{ s.isp }}
              </span>
            </div>
            <p v-else class="rs__untested">{{ t('cleanIp.notTested') }}</p>
            <div class="rs__switch">
              <Select v-model="switchTo[d.id]" :options="spareOptions" option-label="sni" option-value="sni" editable :placeholder="t('cleanIp.newSni')" class="rs__select">
                <template #option="{ option }">
                  <span class="rs__opt">
                    <span class="rs__dot" :class="`rs__dot--${option.health}`" />
                    <span dir="ltr">{{ option.sni }}</span>
                  </span>
                </template>
              </Select>
              <Button :label="t('cleanIp.switch')" icon="pi pi-sync" :loading="switching === d.id" :disabled="!switchTo[d.id]" @click="doSwitch(d.id)" />
            </div>
          </article>
        </div>
      </section>

      <!-- a run's results change the SNIs' status (and may switch one): load them again -->
      <SniTestCard @copy="emit('copy', $event)" @reports="load" @add-spares="addSpares" />

      <section class="card rs__card">
        <StepHeader icon="pi pi-box" :title="t('cleanIp.sparesTitle')" :hint="t('cleanIp.sparesHint')" />

        <div class="rs__spares">
          <span v-for="name in spares" :key="name" class="rs__spare">
            <span class="rs__dot" :class="`rs__dot--${health(spareStatus.get(name) ?? {})}`" />
            <span dir="ltr">{{ name }}</span>
            <button type="button" class="rs__spare-x" :aria-label="t('operatorIps.remove')" @click="removeSpare(name)"><i class="pi pi-times" /></button>
          </span>
          <span v-if="!spares.length" class="rs__untested">{{ t('cleanIp.noSpares') }}</span>
        </div>
        <form class="rs__add" @submit.prevent="addSpare">
          <!-- empty: the page's direction and font, so the hint reads well; typed names: left to right, monospace -->
          <Textarea
            v-model="newSpare"
            rows="1"
            auto-resize
            :dir="newSpare ? 'ltr' : undefined"
            spellcheck="false"
            :placeholder="t('cleanIp.sparesPlaceholder')"
            :invalid="!!typedInvalid.length"
            class="rs__add-input"
            :class="{ 'rs__add-input--filled': !!newSpare }"
            @keydown="onAddKey"
          />
          <Button
            type="submit"
            :label="typedValid.length > 1 ? t('cleanIp.addCount', { count: typedValid.length }) : t('operatorIps.add')"
            icon="pi pi-plus"
            severity="secondary"
            :disabled="!typedValid.length"
          />
        </form>
        <small v-if="typedInvalid.length" class="rs__add-bad">{{ t('cleanIp.sparesInvalid', { list: typedInvalid.slice(0, 5).join(', ') }) }}</small>
        <small v-else class="rs__add-hint">{{ t('cleanIp.sparesPasteHint', { count: spares.length, max: MAX_SPARES }) }}</small>

        <label class="rs__auto" :class="{ 'rs__auto--on': autoSwitch }">
          <span class="rs__auto-icon"><i class="pi pi-bolt" /></span>
          <span class="rs__auto-text">
            <b>{{ t('cleanIp.autoTitle') }}</b>
            <small>{{ t('cleanIp.auto') }}</small>
          </span>
          <ToggleSwitch v-model="autoSwitch" />
        </label>

        <Transition name="rs-fade">
          <div v-if="dirty" class="rs__savebar">
            <span><i class="pi pi-circle-fill" /> {{ t('cleanIp.unsaved') }}</span>
            <Button :label="t('cleanIp.saveSettings')" icon="pi pi-save" :loading="saving" @click="saveSettings" />
          </div>
        </Transition>
      </section>

      <section v-if="reality.events.length" class="card rs__card">
        <StepHeader icon="pi pi-history" :title="t('cleanIp.history')" />
        <ol class="rs__timeline">
          <li v-for="e in reality.events" :key="e.at">
            <span class="rs__tl-dot" :class="{ 'rs__tl-dot--auto': e.auto }"><i class="pi" :class="e.auto ? 'pi-bolt' : 'pi-user'" /></span>
            <div>
              <div class="rs__tl-main">
                <bdi dir="ltr">{{ e.old }} <span class="rs__tl-arrow">→</span> <b>{{ e.new }}</b></bdi>
              </div>
              <div class="rs__tl-meta">{{ e.auto ? t('cleanIp.byAuto', { isp: e.isp }) : t('cleanIp.byAdmin') }} · {{ new Date(e.at * 1000).toLocaleString() }}</div>
            </div>
          </li>
        </ol>
      </section>
    </template>
  </div>
</template>

<style scoped>
.rs {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.rs__card {
  margin-bottom: 0;
  padding: 1.25rem;
}

/* overview */
.rs__overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr));
  gap: 0.75rem;
}
.rs__tile {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 0.65rem;
  align-items: center;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.rs__tile .pi {
  grid-row: span 2;
  inline-size: 2.2rem;
  block-size: 2.2rem;
  display: grid;
  place-items: center;
  border-radius: 0.7rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.rs__tile b {
  font-size: 1.3rem;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.rs__tile span {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.rs__tile--ok .pi {
  color: var(--p-green-500);
  background: color-mix(in srgb, var(--p-green-500) 14%, transparent);
}
.rs__tile--bad {
  border-color: color-mix(in srgb, var(--p-red-400) 50%, var(--p-content-border-color));
}
.rs__tile--bad .pi {
  color: var(--p-red-500);
  background: color-mix(in srgb, var(--p-red-400) 14%, transparent);
}

/* REALITY domains */
.rs__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.75rem 1rem;
  color: var(--p-text-muted-color);
  border: 1px dashed var(--p-content-border-color);
  border-radius: 0.75rem;
}
.rs__empty .pi {
  font-size: 1.5rem;
}
.rs__domains {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 21rem), 1fr));
  gap: 0.75rem;
}
.rs__domain {
  --rs-tone: var(--p-text-muted-color);
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 1rem;
  border-radius: 0.9rem;
  border: 1px solid var(--p-content-border-color);
  background: linear-gradient(180deg, color-mix(in srgb, var(--rs-tone) 7%, var(--p-content-background)), var(--p-content-background) 70%);
}
.rs__domain--ok {
  --rs-tone: var(--p-green-500);
}
.rs__domain--bad {
  --rs-tone: var(--p-red-400);
  border-color: color-mix(in srgb, var(--p-red-400) 45%, var(--p-content-border-color));
}
.rs__domain-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
}
.rs__sni {
  font-size: 1.05rem;
  overflow-wrap: anywhere;
}
.rs__state {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--rs-tone);
  background: color-mix(in srgb, var(--rs-tone) 14%, transparent);
}
.rs__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.rs__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.rs__chip .pi {
  font-size: 0.65rem;
}
.rs__chip--ok {
  color: var(--p-green-600);
  background: color-mix(in srgb, var(--p-green-500) 14%, transparent);
}
.rs__chip--bad {
  color: var(--p-red-500);
  background: color-mix(in srgb, var(--p-red-400) 14%, transparent);
}
.rs__untested {
  margin: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.rs__switch {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.rs__select {
  flex: 1 1 12rem;
  min-width: 0;
}
.rs__opt {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.rs__dot {
  inline-size: 0.5rem;
  block-size: 0.5rem;
  flex: none;
  border-radius: 50%;
  background: var(--p-text-muted-color);
}
.rs__dot--ok {
  background: var(--p-green-500);
}
.rs__dot--bad {
  background: var(--p-red-400);
}

/* spares */
.rs__spares {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
}
.rs__spare {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding-block: 0.25rem;
  padding-inline: 0.65rem 0.3rem;
  border-radius: 999px;
  font-size: 0.84rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-hover-background);
}
.rs__spare-x {
  inline-size: 1.4rem;
  block-size: 1.4rem;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--p-text-muted-color);
  cursor: pointer;
}
.rs__spare-x:hover {
  color: var(--p-red-500);
  background: color-mix(in srgb, var(--p-red-400) 14%, transparent);
}
.rs__spare-x .pi {
  font-size: 0.65rem;
}
.rs__add {
  display: flex;
  gap: 0.5rem;
}
.rs__add {
  align-items: flex-start;
}
.rs__add-input {
  flex: 1;
  min-width: 0;
  max-block-size: 12rem;
}
.rs__add-input--filled {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85rem;
}
.rs__add-hint,
.rs__add-bad {
  display: block;
  margin-top: 0.35rem;
  color: var(--p-text-muted-color);
}
.rs__add-bad {
  color: var(--p-red-500);
}
.rs__spares {
  max-block-size: 14rem;
  overflow: auto;
}
.rs__auto {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  padding: 0.75rem 0.9rem;
  border-radius: 0.8rem;
  border: 1px solid var(--p-content-border-color);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}
.rs__auto--on {
  border-color: color-mix(in srgb, var(--p-orange-400) 55%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-orange-400) 7%, var(--p-content-background));
}
.rs__auto-icon {
  inline-size: 2rem;
  block-size: 2rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 0.6rem;
  color: var(--p-orange-500);
  background: color-mix(in srgb, var(--p-orange-400) 16%, transparent);
}
.rs__auto-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.rs__auto-text small {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.rs__savebar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.6rem 0.75rem;
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--p-primary-color) 7%, var(--p-content-background));
  font-size: 0.85rem;
}
.rs__savebar .pi-circle-fill {
  font-size: 0.5rem;
  color: var(--p-orange-500);
  vertical-align: middle;
}
.rs-fade-enter-active,
.rs-fade-leave-active {
  transition: opacity 0.2s ease;
}
.rs-fade-enter-from,
.rs-fade-leave-to {
  opacity: 0;
}

/* history */
.rs__timeline {
  list-style: none;
  margin: 0;
  padding: 0;
}
.rs__timeline li {
  position: relative;
  display: flex;
  gap: 0.75rem;
  padding-bottom: 0.9rem;
}
.rs__timeline li:not(:last-child)::before {
  content: '';
  position: absolute;
  inset-inline-start: 0.85rem;
  inset-block: 1.8rem 0;
  border-inline-start: 2px solid var(--p-content-border-color);
}
.rs__tl-dot {
  inline-size: 1.75rem;
  block-size: 1.75rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 0.75rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.rs__tl-dot--auto {
  color: var(--p-orange-500);
  background: color-mix(in srgb, var(--p-orange-500) 14%, transparent);
}
.rs__tl-main {
  font-size: 0.9rem;
  overflow-wrap: anywhere;
}
.rs__tl-arrow {
  margin-inline: 0.2rem;
  color: var(--p-text-muted-color);
}
.rs__tl-meta {
  margin-top: 0.15rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
</style>
