<script setup lang="ts">
/** The IP full test, with a real upload: a command run on a device on the operator to test (a browser can not upload to an IP). */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import type { DomainRow } from '@/features/domains/api'
import type { IpReport } from '../api'
import type { ScanResult } from '../composables/useIpScan'
import { useScanCommand } from '../composables/useScanCommand'
import CommandBox from './CommandBox.vue'
import RangesField from './RangesField.vue'
import StepHeader from './StepHeader.vue'
import { operatorLabel } from './operatorLabel'

const props = defineProps<{ domains: DomainRow[]; perIsp: number; ranges: string[] }>()
/** The scan's range list: editing it here changes step 1's too. */
const rangesText = defineModel<string>('rangesText', { required: true })
const emit = defineEmits<{ copy: [text: string]; reports: [list: IpReport[]]; use: [results: ScanResult[], tested: number] }>()
const domainId = defineModel<number | null>('domainId', { required: true })
const { t } = useI18n()

/** Best IPs shown per report. */
const TOP = 5
const uploadKb = ref(5)
const perRange = ref(8)
const { making, command, reports, make } = useScanCommand<IpReport>((list) => emit('reports', list))

const cdnDomains = computed(() => props.domains.filter((d) => d.mode === 'cdn' || d.mode === 'worker'))

function makeCommand() {
  if (domainId.value) make({ kind: 'ip', domain_id: domainId.value, size: uploadKb.value * 1000, per_range: perRange.value, per_isp: props.perIsp, ranges: props.ranges })
}
</script>

<template>
  <section class="card step">
    <StepHeader icon="pi pi-upload" :title="t('cleanIp.fullTitle')" :hint="t('cleanIp.fullHint')" />
    <p class="full__lead">{{ t('cleanIp.fullLead') }}</p>

    <div class="full__fields">
      <label class="full__field full__field--wide">
        <span>{{ t('cleanIp.domain') }}</span>
        <Select v-model="domainId" :options="cdnDomains" option-label="domain" option-value="id" :disabled="!cdnDomains.length" fluid />
      </label>
      <label class="full__field">
        <span>{{ t('cleanIp.uploadSize') }}</span>
        <InputNumber v-model="uploadKb" :min="1" :max="64" show-buttons suffix=" KB" fluid />
      </label>
      <label class="full__field">
        <span>{{ t('cleanIp.perRange') }}</span>
        <InputNumber v-model="perRange" :min="1" :max="64" show-buttons fluid />
      </label>
    </div>
    <RangesField v-model="rangesText" class="full__ranges" />
    <Button :label="command ? t('cleanIp.makeAgain') : t('cleanIp.makeCommand')" icon="pi pi-code" class="full__make" :loading="making" :disabled="!domainId || !ranges.length" @click="makeCommand" />

    <template v-if="command">
      <CommandBox :command="command" :waiting="!reports.length" @copy="emit('copy', $event)" />

      <h4 v-if="reports.length" class="full__h">{{ t('cleanIp.received') }}</h4>
      <TransitionGroup name="full-list" tag="div" class="full__reports">
        <article v-for="report in [...reports].reverse()" :key="report.at" class="full__report">
          <div class="full__report-head">
            <b>{{ operatorLabel(t, report.short_name, report.asn) }}</b>
            <span class="full__meta" dir="ltr">AS{{ report.asn }} · {{ report.country.toUpperCase() }}</span>
            <span class="full__time">{{ new Date(report.at * 1000).toLocaleTimeString() }}</span>
          </div>
          <div class="full__report-line">{{ t('cleanIp.reportLine', { tested: report.tested, found: report.ips.length, kb: Math.round(report.size / 1000) }) }}</div>
          <ul v-if="report.ips.length" class="full__ips-list">
            <li v-for="r in report.ips.slice(0, TOP)" :key="r.ip">
              <span dir="ltr" class="full__ips">{{ r.ip }}</span>
              <span class="full__ms">{{ r.ms }} ms</span>
              <span class="full__loss" :class="{ 'full__loss--bad': (r.loss ?? 0) > 0 }">{{ t('cleanIp.loss', { pct: r.loss ?? 0 }) }}</span>
              <span v-if="r.colo" class="full__colo">{{ r.colo }}</span>
            </li>
          </ul>
          <div v-if="report.saved.length" class="full__saved">
            <i class="pi pi-check-circle" /> {{ t('cleanIp.reportSaved', { count: report.saved.length, isp: report.short_name }) }}
            <span dir="ltr" class="full__ips">{{ report.saved.join(', ') }}</span>
          </div>
          <div v-else-if="report.ips.length" class="full__unsaved">
            <span>{{ t('cleanIp.reportNotSaved') }}</span>
            <Button :label="t('cleanIp.useThese')" icon="pi pi-arrow-up" size="small" text @click="emit('use', report.ips.map((r) => ({ ip: r.ip, ms: r.ms })), report.tested)" />
          </div>
        </article>
      </TransitionGroup>
    </template>
  </section>
</template>

<style scoped>
.step {
  margin-bottom: 0;
  padding: 1.25rem;
}
.full__lead {
  margin: -0.4rem 0 0.9rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.full__fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
}
.full__field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
  min-width: 0;
}
.full__field--wide {
  grid-column: 1 / -1;
}
.full__ranges {
  margin-top: 0.75rem;
}
.full__make {
  margin-top: 1rem;
}
.full__h {
  margin: 1.25rem 0 0.6rem;
  font-size: 0.95rem;
}
.full__reports {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.full__report {
  padding: 0.75rem 0.9rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
}
.full__report-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.25rem 0.75rem;
}
.full__meta,
.full__time {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.full__time {
  margin-inline-start: auto;
}
.full__report-line {
  margin-top: 0.25rem;
  font-size: 0.84rem;
}
.full__saved {
  margin-top: 0.35rem;
  font-size: 0.82rem;
  color: var(--p-green-500);
}
.full__ips {
  font-family: var(--font-mono, ui-monospace, monospace);
  overflow-wrap: anywhere;
}
.full__ips-list {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.full__ips-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.75rem;
  font-size: 0.82rem;
}
.full__ms {
  color: var(--p-green-500);
  font-variant-numeric: tabular-nums;
}
.full__loss {
  padding: 0 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--p-green-600);
  background: color-mix(in srgb, var(--p-green-500) 14%, transparent);
}
.full__loss--bad {
  color: var(--p-orange-600);
  background: color-mix(in srgb, var(--p-orange-400) 18%, transparent);
}
.full__colo {
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
}
.full__unsaved {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
  margin-top: 0.35rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.full-list-enter-active {
  transition: all 0.25s ease;
}
.full-list-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
