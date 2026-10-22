<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { getHttp } from '@/core/api/client'
import { SERIES } from '../composables/useChartTheme'
import DashCard from './DashCard.vue'

interface AppHealth {
  total: number
  ok: number
  failed: { name: string; error: string }[]
  error: string
}
interface HealthState {
  last: { at: number; user: string; apps: Record<string, AppHealth> } | null
  running: boolean
}

const { t, locale } = useI18n()
const state = ref<HealthState | null>(null)
const open = ref<string | null>(null)
let timer = 0

const APP_NAMES: Record<string, string> = { xray: 'Xray (v2rayN, v2rayNG, Happ…)', hiddify: 'Hiddify / sing-box' }

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
  try {
    state.value = (await getHttp().get<HealthState>('config-health/')).data
  } catch {
    state.value = null
  }
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
          <span v-if="app.error" class="health__bad">{{ app.error }}</span>
          <span v-else :class="app.failed.length ? 'health__bad' : 'health__ok'">
            {{ t('dashboard.health.working', { ok: app.ok, total: app.total }) }}
          </span>
          <i v-if="app.failed.length" class="pi" :class="open === name ? 'pi-chevron-up' : 'pi-chevron-down'" />
        </button>
        <div class="health__bar"><i :style="{ width: (app.total ? (app.ok / app.total) * 100 : 0) + '%' }" /></div>
        <ul v-if="open === name" class="health__failed">
          <li v-for="f in app.failed" :key="f.name">
            <span class="ltr">{{ f.name }}</span>
            <small class="text-muted-color ltr">{{ f.error }}</small>
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
