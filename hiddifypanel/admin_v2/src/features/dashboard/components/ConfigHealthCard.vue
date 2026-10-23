<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { getHttp } from '@/core/api/client'
import { CONFIG_HEALTH_APPS as APP_NAMES, configHealth as state, configReason, loadConfigHealth, problemKind } from '@/shared/composables/useConfigHealth'
import { SERIES } from '../composables/useChartTheme'
import DashCard from './DashCard.vue'

const { t, locale } = useI18n()
const open = ref<string | null>(null)
/** Apps whose technical message is shown (under the explanation) */
const details = ref<Set<string>>(new Set())
let timer = 0

function toggleDetails(name: string) {
  const next = new Set(details.value)
  if (!next.delete(name)) next.add(name)
  details.value = next
}

const apps = computed(() => Object.entries(state.value?.last?.apps ?? {}))
const allOk = computed(() => apps.value.length > 0 && apps.value.every(([, a]) => !a.failed.length && !a.error))
const ago = computed(() => {
  const at = state.value?.last?.at
  if (!at) return ''
  const minutes = Math.max(0, Math.round((Date.now() / 1000 - at) / 60))
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  return minutes < 60 ? rtf.format(-minutes, 'minute') : rtf.format(-Math.round(minutes / 60), 'hour')
})

async function load() {
  await loadConfigHealth()
  window.clearTimeout(timer)
  // While a check runs, look again every 10 s; otherwise once a minute (the time-ago label)
  timer = window.setTimeout(load, state.value?.running ? 10_000 : 60_000)
}

async function checkNow() {
  await getHttp().post('config-health/')
  if (state.value) state.value.running = true
  window.clearTimeout(timer)
  timer = window.setTimeout(load, 5_000)
}

onMounted(load)
onBeforeUnmount(() => window.clearTimeout(timer))
</script>

<template>
  <DashCard
    :title="t('dashboard.health.title')"
    :subtitle="state?.last ? t('dashboard.health.checked', { ago }) : t('dashboard.health.subtitle')"
    icon="pi pi-check-circle"
    :accent="allOk ? SERIES.online : SERIES.upload"
    padded
  >
    <template #actions>
      <Button
        :label="state?.running ? t('dashboard.health.running') : t('dashboard.health.checkNow')"
        :icon="state?.running ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'"
        size="small"
        severity="secondary"
        :disabled="state?.running"
        @click="checkNow"
      />
    </template>

    <p v-if="!state?.last" class="text-muted-color text-sm m-0">{{ state?.running ? t('dashboard.health.firstRun') : t('dashboard.health.never') }}</p>
    <div v-else class="health">
      <div v-for="[name, app] in apps" :key="name" class="health__app">
        <button type="button" class="health__row" :disabled="!app.failed.length" @click="open = open === name ? null : name">
          <span class="health__name">{{ APP_NAMES[name] ?? name }}</span>
          <span v-if="app.error" class="health__bad">{{ t('dashboard.health.notTested') }}</span>
          <span v-else :class="app.failed.length ? 'health__bad' : 'health__ok'">
            {{ t('dashboard.health.working', { ok: app.ok, total: app.total }) }}
          </span>
          <i v-if="app.failed.length" class="pi" :class="open === name ? 'pi-chevron-up' : 'pi-chevron-down'" />
        </button>
        <div class="health__bar"><i :style="{ width: (app.total ? (app.ok / app.total) * 100 : 0) + '%' }" /></div>
        <!-- The subscription could not be tested: what it means and where to look, the raw message on demand -->
        <div v-if="app.error" class="health__problem" role="alert">
          <i class="pi pi-exclamation-triangle health__problem-icon" aria-hidden="true" />
          <div class="health__problem-body">
            <strong>{{ t(`dashboard.health.problem.${problemKind(app)}.title`, { host: state.last.host || '—' }) }}</strong>
            <p>{{ t(`dashboard.health.problem.${problemKind(app)}.hint`, { host: state.last.host || '—' }) }}</p>
            <button type="button" class="health__more" :aria-expanded="details.has(name)" @click="toggleDetails(name)">
              <i class="pi" :class="details.has(name) ? 'pi-chevron-up' : 'pi-chevron-down'" />{{ t('dashboard.health.technical') }}
            </button>
            <code v-if="details.has(name)" class="health__raw ltr">{{ app.error }}</code>
          </div>
        </div>
        <ul v-if="open === name" class="health__failed">
          <li v-for="f in app.failed" :key="f.name">
            <span class="ltr health__cfg">{{ f.name }}</span>
            <span v-if="configReason(f.error)" class="health__reason">{{ t(`dashboard.health.reason.${configReason(f.error)}`) }}</span>
            <small class="text-muted-color ltr health__wrap">{{ f.error }}</small>
          </li>
        </ul>
      </div>
      <p class="text-muted-color text-xs m-0">{{ t('dashboard.health.note', { user: state.last.user }) }}</p>
    </div>
  </DashCard>
</template>

<style scoped>
.health {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.health__row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
  text-align: start;
}
.health__row:disabled {
  cursor: default;
}
.health__name {
  flex: 1;
  font-weight: 600;
  min-width: 0;
  overflow-wrap: anywhere;
}
.health__app {
  min-width: 0;
}
.health__problem {
  display: flex;
  gap: 0.65rem;
  margin-top: 0.65rem;
  padding: 0.75rem 0.85rem;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--p-orange-500) 35%, transparent);
  background: color-mix(in srgb, var(--p-orange-500) 9%, transparent);
  min-width: 0;
}
.health__problem-icon {
  flex: none;
  margin-top: 0.15rem;
  color: var(--p-orange-500);
}
.health__problem-body {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
  font-size: 0.9rem;
}
.health__problem-body p {
  margin: 0;
  line-height: 1.55;
  color: var(--p-text-muted-color);
}
.health__more {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.health__raw {
  display: block;
  max-height: 10rem;
  overflow: auto;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  background: color-mix(in srgb, var(--p-text-color) 6%, transparent);
  font-size: 0.78rem;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.health__cfg {
  font-weight: 600;
}
.health__reason {
  color: var(--p-orange-500);
  font-size: 0.82rem;
}
.health__wrap {
  overflow-wrap: anywhere;
}
.health__ok {
  color: var(--p-green-500);
  font-weight: 600;
}
.health__bad {
  color: var(--p-orange-500);
  font-weight: 600;
}
.health__bar {
  height: 6px;
  margin-top: 0.4rem;
  border-radius: 6px;
  background: color-mix(in srgb, var(--p-text-color) 10%, transparent);
  overflow: hidden;
}
.health__bar > i {
  display: block;
  height: 100%;
  background: var(--p-green-500);
  border-radius: inherit;
}
.health__failed {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  max-height: 16rem;
  overflow: auto;
  font-size: 0.85rem;
}
.health__failed li {
  display: flex;
  flex-direction: column;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
}
.ltr {
  direction: ltr;
  unicode-bidi: isolate;
  text-align: start;
}
</style>
