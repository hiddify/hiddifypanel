<script setup lang="ts">
/** Step 1: scan random Cloudflare IPs from this browser, fastest first. */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import ProgressBar from 'primevue/progressbar'
import type { IpScan } from '../composables/useIpScan'
import RangesField from './RangesField.vue'
import StepHeader from './StepHeader.vue'

/** ``bare``: inside the IP flow's step (no card, no title; the settings folded). ``show``: rows shown until "all". */
const props = defineProps<{ scan: IpScan; bare?: boolean; show?: number }>()
const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()

/** Shown rows: enough to pick from, without slowing a phone down. */
const SHOWN = 100
const optionsOpen = ref(false)

const showAll = ref(false)
const limit = computed(() => (props.show && !showAll.value ? props.show : SHOWN))
const rows = computed(() => props.scan.passed.value.slice(0, limit.value))
const hidden = computed(() => Math.min(props.scan.passed.value.length, SHOWN) - rows.value.length)
const slowest = computed(() => Math.max(...rows.value.map((r) => r.ms), 1))

function speed(ms: number): 'fast' | 'ok' | 'slow' {
  if (ms < 300) return 'fast'
  return ms < 800 ? 'ok' : 'slow'
}
</script>

<template>
  <component :is="bare ? 'div' : 'section'" :class="bare ? 'scan--bare' : 'card step'">
    <StepHeader v-if="!bare" :number="1" :title="t('cleanIp.scan')" :hint="t('cleanIp.howItWorks')" />

    <button v-if="bare" type="button" class="scan__opts-toggle" :aria-expanded="optionsOpen" @click="optionsOpen = !optionsOpen">
      <i class="pi pi-sliders-h" />
      <span>{{ t('cleanIp.scanSettings') }}</span>
      <small>{{ t('cleanIp.scanSettingsSummary', { ranges: scan.ranges.value.length, count: scan.estimate.value, sec: scan.timeoutSec.value }) }}</small>
      <i class="pi pi-chevron-down scan__opts-chevron" :class="{ 'scan__opts-chevron--open': optionsOpen }" />
    </button>
    <div v-show="!bare || optionsOpen" class="scan__opts">
    <RangesField v-model="scan.rangesText.value" :disabled="scan.running.value" class="scan__ranges" />

    <div class="scan__settings">
      <label class="scan__field">
        <span>{{ t('cleanIp.perRange') }}</span>
        <InputNumber v-model="scan.perRange.value" :min="1" :max="64" show-buttons :disabled="scan.running.value" fluid />
      </label>
      <label class="scan__field">
        <span>{{ t('cleanIp.timeout') }}</span>
        <InputNumber v-model="scan.timeoutSec.value" :min="1" :max="15" show-buttons suffix=" s" :disabled="scan.running.value" fluid />
      </label>
    </div>
    <p class="scan__estimate">{{ t('cleanIp.estimate', { count: scan.estimate.value, ranges: scan.ranges.value.length }) }}</p>
    </div>

    <Button
      v-if="!scan.running.value"
      :label="scan.total.value ? t('cleanIp.scanAgain') : t('cleanIp.start')"
      icon="pi pi-play"
      size="large"
      class="scan__go"
      :disabled="!scan.ranges.value.length"
      @click="scan.start()"
    />
    <Button v-else :label="t('cleanIp.stop')" icon="pi pi-stop" size="large" severity="secondary" class="scan__go" :loading="scan.stopping.value" @click="scan.stop()" />

    <template v-if="scan.total.value">
      <ProgressBar :value="scan.progress.value" :show-value="false" class="scan__bar" :class="{ 'scan__bar--live': scan.running.value }" />
      <div class="scan__stats">
        <div class="scan__stat">
          <b>{{ scan.done.value }}<small>/{{ scan.total.value }}</small></b>
          <span>{{ t('cleanIp.statTested') }}</span>
        </div>
        <div class="scan__stat scan__stat--ok">
          <b>{{ scan.passed.value.length }}</b>
          <span>{{ t('cleanIp.statWorking') }}</span>
        </div>
        <div class="scan__stat">
          <b>{{ scan.passed.value[0]?.ms ?? '–' }}<small v-if="scan.passed.value.length"> ms</small></b>
          <span>{{ t('cleanIp.statBest') }}</span>
        </div>
      </div>
    </template>

    <div v-if="rows.length" class="scan__results">
      <div class="scan__results-head">
        <span>{{ t('cleanIp.ip') }}</span>
        <Button :label="t('cleanIp.copyAll')" icon="pi pi-copy" text size="small" @click="emit('copy', scan.passed.value.map((r) => r.ip).join('\n'))" />
      </div>
      <ul class="scan__list">
        <li v-for="(row, index) in rows" :key="row.ip" class="scan__row">
          <span class="scan__rank">{{ index + 1 }}</span>
          <span class="scan__ip ltr">{{ row.ip }}</span>
          <span class="scan__lat" :class="`scan__lat--${speed(row.ms)}`">
            <span class="scan__lat-bar"><span :style="{ inlineSize: `${Math.max(6, (row.ms / slowest) * 100)}%` }" /></span>
            <span class="scan__ms">{{ row.ms }} ms</span>
          </span>
          <Button icon="pi pi-copy" text rounded size="small" :aria-label="t('common.copy')" @click="emit('copy', row.ip)" />
        </li>
      </ul>
      <button v-if="hidden > 0 || (showAll && props.show)" type="button" class="scan__more" :aria-expanded="showAll" @click="showAll = !showAll">
        <i class="pi" :class="showAll ? 'pi-chevron-up' : 'pi-chevron-down'" />
        {{ showAll ? t('cleanIp.showLess') : t('cleanIp.showAllResults', { count: scan.passed.value.length }) }}
      </button>
    </div>
    <div v-else class="scan__empty">
      <i class="pi" :class="scan.running.value ? 'pi-spin pi-spinner' : scan.total.value ? 'pi-ban' : 'pi-search'" />
      <span>{{ scan.total.value ? (scan.running.value ? t('cleanIp.scanning') : t('cleanIp.noneFound')) : t('cleanIp.notYet') }}</span>
    </div>
  </component>
</template>

<style scoped>
.step {
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  padding: 1.25rem;
}
.scan__ranges {
  margin-bottom: 0.9rem;
}
.scan__opts-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  inline-size: 100%;
  margin-bottom: 0.75rem;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.65rem;
  background: var(--p-content-hover-background);
  color: inherit;
  font: inherit;
  font-size: 0.85rem;
  text-align: start;
  cursor: pointer;
}
.scan__opts-toggle small {
  flex: 1;
  min-width: 0;
  color: var(--p-text-muted-color);
}
.scan__opts-chevron {
  font-size: 0.75rem;
  transition: transform 0.2s ease;
}
.scan__opts-chevron--open {
  transform: rotate(180deg);
}
.scan--bare .scan__opts {
  margin-bottom: 0.75rem;
}
.scan__settings {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
  gap: 0.75rem;
}
.scan__field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
  min-width: 0;
}
.scan__estimate {
  margin: 0.5rem 0 0.9rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.scan__go {
  inline-size: 100%;
}
.scan__bar {
  block-size: 6px;
  margin-top: 1rem;
}
.scan__bar--live :deep(.p-progressbar-value) {
  background-image: linear-gradient(90deg, var(--p-primary-color), color-mix(in srgb, var(--p-primary-color) 55%, white), var(--p-primary-color));
  background-size: 200% 100%;
  animation: scan-shine 1.4s linear infinite;
}
@keyframes scan-shine {
  to {
    background-position: -200% 0;
  }
}
.scan__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.scan__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem;
  border-radius: 0.75rem;
  background: var(--p-content-hover-background);
}
.scan__stat b {
  font-size: 1.2rem;
  font-variant-numeric: tabular-nums;
}
.scan__stat small {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
}
.scan__stat span {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.scan__stat--ok b {
  color: var(--p-green-500);
}
.scan__results {
  margin-top: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
  overflow: hidden;
}
.scan__results-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.25rem 0.5rem 0.25rem 0.85rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background);
}
.scan__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-block-size: 24rem;
  overflow: auto;
}
.scan__more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  inline-size: 100%;
  padding: 0.5rem;
  border: 0;
  border-top: 1px solid var(--p-content-border-color);
  background: var(--p-content-hover-background);
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.scan__more .pi {
  font-size: 0.7rem;
}
.scan__row {
  display: grid;
  grid-template-columns: 1.75rem minmax(0, 1fr) minmax(6.5rem, 9rem) auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.2rem 0.5rem 0.2rem 0.85rem;
  border-top: 1px solid var(--p-content-border-color);
}
.scan__rank {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
.scan__ip {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.88rem;
  overflow-wrap: anywhere;
}
.scan__lat {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.scan__lat-bar {
  flex: 1;
  block-size: 4px;
  border-radius: 999px;
  background: var(--p-content-border-color);
  overflow: hidden;
}
.scan__lat-bar > span {
  display: block;
  block-size: 100%;
  border-radius: inherit;
  background: currentColor;
}
.scan__ms {
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.scan__lat--fast {
  color: var(--p-green-500);
}
.scan__lat--ok {
  color: var(--p-amber-500);
}
.scan__lat--slow {
  color: var(--p-red-400);
}
.scan__empty {
  flex: 1;
  justify-content: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 1.75rem 1rem;
  text-align: center;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  border: 1px dashed var(--p-content-border-color);
  border-radius: 0.75rem;
}
.scan__empty .pi {
  font-size: 1.5rem;
}
.ltr {
  direction: ltr;
  unicode-bidi: isolate;
}
</style>
