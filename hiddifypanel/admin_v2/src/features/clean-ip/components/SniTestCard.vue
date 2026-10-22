<script setup lang="ts">
/** The REALITY SNI test: a command run on a device on the operator to check; the panel records each SNI per operator. */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import Textarea from 'primevue/textarea'
import { apiErrorMessage } from '@/core/api/client'
import { cleanIpApi, type SniReport } from '../api'
import { useScanCommand } from '../composables/useScanCommand'
import CommandBox from './CommandBox.vue'
import StepHeader from './StepHeader.vue'
import { operatorLabel } from './operatorLabel'

const emit = defineEmits<{ copy: [text: string]; reports: [list: SniReport[]]; addSpares: [names: string[]] }>()
const { t } = useI18n()
const { making, command, reports, make } = useScanCommand<SniReport>((list) => emit('reports', list))

/** Shown working candidates per report: enough to pick spares from. */
const SHOWN = 40
/** Candidate names shown as chips until the list is edited. */
const PREVIEW = 5
const editing = ref(false)
const showAll = ref(false)
// The candidate names to test besides the REALITY SNIs (OONI's sites reachable in Iran by default), editable
const candidatesText = ref('')
const loadingCandidates = ref(false)
const candidatesError = ref('')
const candidates = computed(() => [...new Set(candidatesText.value.split(/[\s,;]+/).map((x) => x.trim().toLowerCase()).filter(Boolean))])

async function loadCandidates() {
  loadingCandidates.value = true
  candidatesError.value = ''
  try {
    candidatesText.value = (await cleanIpApi.sniCandidates()).join('\n')
  } catch (e) {
    candidatesError.value = apiErrorMessage(e)
  } finally {
    loadingCandidates.value = false
  }
}

onMounted(loadCandidates)
</script>

<template>
  <section class="card sni">
    <StepHeader icon="pi pi-send" :title="t('cleanIp.sniTestTitle')" :hint="t('cleanIp.sniTestHint')" />
    <p class="sni__lead">{{ t('cleanIp.sniTestLead') }}</p>
    <div class="sni__candidates" :class="{ 'sni__candidates--open': editing }">
      <div class="sni__candidates-head">
        <span class="sni__candidates-icon"><i class="pi pi-list" /></span>
        <div class="sni__candidates-text">
          <label for="sni-candidates" class="sni__candidates-title">{{ t('cleanIp.candidates') }}</label>
          <span class="sni__count">{{ t('cleanIp.candidatesCount', { count: candidates.length }) }} · {{ t('cleanIp.candidatesFrom') }}</span>
        </div>
        <Button v-tooltip.top="t('cleanIp.candidatesReload')" icon="pi pi-refresh" text rounded size="small" :aria-label="t('cleanIp.candidatesReload')" :loading="loadingCandidates" @click="loadCandidates" />
        <Button :label="editing ? t('cleanIp.rangesDone') : t('cleanIp.rangesEdit')" :icon="editing ? 'pi pi-check' : 'pi pi-pencil'" size="small" severity="secondary" text @click="editing = !editing" />
      </div>
      <Skeleton v-if="loadingCandidates && !candidatesText" height="1.6rem" border-radius="999px" />
      <div v-else-if="!editing" class="sni__chips" :class="{ 'sni__chips--all': showAll }" dir="ltr">
        <span v-for="name in showAll ? candidates : candidates.slice(0, PREVIEW)" :key="name" class="sni__chip sni__chip--plain">{{ name }}</span>
        <button v-if="candidates.length > PREVIEW" type="button" class="sni__more-btn" :aria-expanded="showAll" @click="showAll = !showAll">
          {{ showAll ? t('cleanIp.showLess') : `+${candidates.length - PREVIEW}` }}
        </button>
      </div>
      <template v-else>
        <Textarea id="sni-candidates" v-model="candidatesText" rows="8" dir="ltr" spellcheck="false" class="sni__candidates-input" fluid />
        <small class="sni__hint">{{ t('cleanIp.candidatesHint') }}</small>
      </template>
      <Message v-if="candidatesError" severity="warn" size="small" :closable="false">{{ candidatesError }}</Message>
    </div>
    <Button :label="command ? t('cleanIp.makeAgain') : t('cleanIp.makeCommand')" icon="pi pi-code" :loading="making" @click="make({ kind: 'sni', snis: candidates })" />

    <template v-if="command">
      <CommandBox :command="command" :waiting="!reports.length" @copy="emit('copy', $event)" />

      <h4 v-if="reports.length" class="sni__h">{{ t('cleanIp.received') }}</h4>
      <TransitionGroup name="sni-list" tag="div" class="sni__reports">
        <article v-for="report in [...reports].reverse()" :key="report.at" class="sni__report">
          <div class="sni__report-head">
            <b>{{ operatorLabel(t, report.short_name, report.asn) }}</b>
            <span class="sni__meta" dir="ltr">AS{{ report.asn }} · {{ report.country.toUpperCase() }}</span>
            <span class="sni__time">{{ new Date(report.at * 1000).toLocaleTimeString() }}</span>
          </div>
          <div v-if="!report.control" class="sni__blocked"><i class="pi pi-exclamation-triangle" /> {{ t('cleanIp.sniServerBlocked') }}</div>
          <template v-else>
            <div class="sni__chips">
              <span v-for="r in report.snis" :key="r.sni" class="sni__chip" :class="r.ok ? 'sni__chip--ok' : 'sni__chip--bad'">
                <i class="pi" :class="r.ok ? 'pi-check' : 'pi-times'" /> <span dir="ltr">{{ r.sni }}</span>
              </span>
            </div>
            <div v-if="report.candidates_tested" class="sni__found">
              <div class="sni__found-head">
                <span>{{ t('cleanIp.candidatesFound', { ok: report.candidates_ok?.length ?? 0, tested: report.candidates_tested }) }}</span>
                <Button
                  v-if="report.candidates_ok?.length"
                  :label="t('cleanIp.addSpares')"
                  icon="pi pi-plus"
                  size="small"
                  outlined
                  @click="emit('addSpares', report.candidates_ok ?? [])"
                />
              </div>
              <div class="sni__chips">
                <span v-for="name in (report.candidates_ok ?? []).slice(0, SHOWN)" :key="name" class="sni__chip sni__chip--ok"><span dir="ltr">{{ name }}</span></span>
                <span v-if="(report.candidates_ok?.length ?? 0) > SHOWN" class="sni__more">+{{ (report.candidates_ok?.length ?? 0) - SHOWN }}</span>
              </div>
            </div>
          </template>
        </article>
      </TransitionGroup>
    </template>
  </section>
</template>

<style scoped>
.sni {
  margin-bottom: 0;
  padding: 1.25rem;
}
.sni__lead {
  margin: -0.4rem 0 0.9rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.sni__candidates {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-hover-background);
}
.sni__candidates--open {
  background: var(--p-content-background);
}
.sni__candidates-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.sni__candidates-icon {
  inline-size: 2rem;
  block-size: 2rem;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 0.6rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.sni__candidates-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.sni__candidates-title {
  font-size: 0.88rem;
  font-weight: 600;
}
.sni__count {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
.sni__candidates-input {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
}
.sni__hint {
  color: var(--p-text-muted-color);
}
.sni__chips--all {
  max-block-size: 16rem;
  overflow: auto;
}
.sni__more-btn {
  padding: 0.1rem 0.55rem;
  border: 1px dashed var(--p-primary-color);
  border-radius: 999px;
  background: transparent;
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
}
.sni__more-btn:hover {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.sni__chip--plain {
  font-weight: 500;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.72rem;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}
.sni__found {
  margin-top: 0.75rem;
  padding-top: 0.65rem;
  border-top: 1px dashed var(--p-content-border-color);
}
.sni__found-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  font-size: 0.84rem;
}
.sni__more {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  align-self: center;
}
.sni__h {
  margin: 1.25rem 0 0.6rem;
  font-size: 0.95rem;
}
.sni__reports {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.sni__report {
  padding: 0.75rem 0.9rem;
  border-radius: 0.75rem;
  border: 1px solid var(--p-content-border-color);
}
.sni__report-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.25rem 0.75rem;
}
.sni__meta,
.sni__time {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.sni__time {
  margin-inline-start: auto;
}
.sni__blocked {
  margin-top: 0.4rem;
  font-size: 0.84rem;
  color: var(--p-orange-500);
}
.sni__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.5rem;
}
.sni__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
}
.sni__chip .pi {
  font-size: 0.65rem;
}
.sni__chip--ok {
  color: var(--p-green-600);
  background: color-mix(in srgb, var(--p-green-500) 14%, transparent);
}
.sni__chip--bad {
  color: var(--p-red-500);
  background: color-mix(in srgb, var(--p-red-400) 14%, transparent);
}
.sni-list-enter-active {
  transition: all 0.25s ease;
}
.sni-list-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
