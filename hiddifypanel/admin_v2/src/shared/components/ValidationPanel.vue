<template>
  <Panel v-if="result" ref="rootEl" :header="t('validation.title')" class="validation-panel mb-3">
    <Message v-if="result.ok" severity="success" :closable="false">{{ t('common.validationOk') }}</Message>
    <template v-else>
      <!-- Each error as a card: what kind of problem it is in plain words, the steps that fix it, the panel's own text -->
      <div class="vp-errors">
        <section v-for="(e, i) in result.errors" :key="'e' + i" class="vp-error" :class="`vp-error--${issueKind(e)}`">
          <header class="vp-error__head">
            <span class="vp-error__icon"><i :class="KIND_ICON[issueKind(e)]" /></span>
            <div class="min-w-0">
              <h4 class="vp-error__title">{{ issueKind(e) === 'setting' ? e.message || e.code : t(`validation.kind.${issueKind(e)}.title`) }}</h4>
              <p v-if="issueKind(e) !== 'setting'" class="vp-error__lead">{{ t(`validation.kind.${issueKind(e)}.lead`) }}</p>
            </div>
          </header>
          <template v-if="issueKind(e) !== 'setting'">
            <p class="vp-error__how">{{ t('validation.howToFix') }}</p>
            <ol class="vp-error__steps">
              <li v-for="n in 2" :key="n">{{ t(`validation.kind.${issueKind(e)}.step${n}`) }}</li>
            </ol>
          </template>
          <pre v-if="e.detail?.excerpt" class="validation-issue-detail">{{ e.detail.excerpt }}</pre>
          <details v-if="issueKind(e) !== 'setting' || e.code" class="vp-error__details" :open="issueKind(e) === 'template'">
            <summary>{{ t('validation.details') }}</summary>
            <div class="vp-error__raw">
              <Tag v-if="e.code" severity="danger" :value="e.code" class="text-xs" />
              <code dir="ltr">{{ e.message }}</code>
            </div>
          </details>
        </section>
      </div>
    </template>

    <Fieldset v-if="result.warnings?.length" :legend="t('validation.warnings')" class="mt-3 mb-0">
      <ul class="validation-issue-list">
        <li v-for="(w, i) in result.warnings" :key="'w' + i" class="validation-issue">
          <Tag v-if="w.code" severity="warn" :value="w.code" class="text-xs me-2" />
          <span class="validation-issue-message">{{ w.message }}</span>
        </li>
      </ul>
    </Fieldset>
    <Fieldset v-if="result.compiled_preview" :legend="t('validation.preview')" class="mt-3 mb-0">
      <ScrollPanel class="config-scroll-panel" :style="{ width: '100%', height: '240px' }">
        <pre class="validation-preview-pre">{{ result.compiled_preview }}</pre>
      </ScrollPanel>
    </Fieldset>
  </Panel>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Panel from 'primevue/panel'
import Message from 'primevue/message'
import { issueKind, type IssueKind } from '@/shared/utils/validation-toast'
import Fieldset from 'primevue/fieldset'
import Tag from 'primevue/tag'
import ScrollPanel from 'primevue/scrollpanel'
import type { ValidationResult } from '@/core/api/generated'

const props = defineProps<{
  result: ValidationResult | null
}>()

const { t } = useI18n()
const KIND_ICON: Record<IssueKind, string> = { internal: 'pi pi-server', template: 'pi pi-code', setting: 'pi pi-exclamation-triangle' }
const rootEl = ref<{ $el?: HTMLElement } | HTMLElement | null>(null)

function panelElement(): HTMLElement | null {
  const el = rootEl.value
  if (!el) return null
  if (el instanceof HTMLElement) return el
  return el.$el ?? null
}

async function scrollIntoView() {
  await nextTick()
  panelElement()?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

watch(
  () => props.result,
  (result) => {
    if (result && (!result.ok || result.warnings?.length)) void scrollIntoView()
  },
)

defineExpose({ scrollIntoView })
</script>

<style scoped>
.validation-issue-list {
  margin: 0;
  padding-inline-start: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.validation-issue-message {
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.875rem;
}

.validation-issue-detail {
  margin: 0.35rem 0 0;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--surface-ground);
  border-radius: var(--content-border-radius);
  max-height: 12rem;
  overflow: auto;
}

.vp-errors {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.vp-error {
  --vp-tone: var(--p-red-500, #ef4444);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.85rem 1rem 0.75rem;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--vp-tone) 24%, transparent);
  border-inline-start: 4px solid var(--vp-tone);
  background: color-mix(in srgb, var(--vp-tone) 5%, var(--p-content-background));
  font-size: 0.86rem;
}
/* The panel's own fault: amber, not the red of something to fix in the proxy */
.vp-error--internal {
  --vp-tone: var(--p-amber-500, #f59e0b);
}
.vp-error__head {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
}
.vp-error__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 10px;
  color: var(--vp-tone);
  background: color-mix(in srgb, var(--vp-tone) 14%, transparent);
}
.vp-error__title {
  margin: 0.15rem 0 0.15rem;
  font-size: 0.92rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.vp-error__lead {
  margin: 0;
  line-height: 1.55;
  color: var(--p-text-muted-color);
}
.vp-error__how {
  margin: 0.15rem 0 0;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.vp-error__steps {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: step;
}
.vp-error__steps li {
  position: relative;
  padding-inline-start: 1.85rem;
  line-height: 1.55;
  counter-increment: step;
}
.vp-error__steps li::before {
  content: counter(step);
  position: absolute;
  inset-inline-start: 0;
  top: 0.05rem;
  display: grid;
  place-items: center;
  width: 1.3rem;
  height: 1.3rem;
  border-radius: 50%;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--p-primary-contrast-color, #fff);
  background: var(--p-primary-color);
}
.vp-error__details {
  padding-top: 0.45rem;
  border-top: 1px dashed color-mix(in srgb, var(--vp-tone) 28%, transparent);
}
.vp-error__details summary {
  width: fit-content;
  cursor: pointer;
  color: var(--p-text-muted-color);
}
.vp-error__raw {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-top: 0.35rem;
}
.vp-error__raw code {
  min-width: 0;
  font-size: 0.78rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: var(--p-text-muted-color);
}

.validation-preview-pre {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.4;
  white-space: pre;
  user-select: text;
}

.config-scroll-panel :deep(.p-scrollpanel-content) {
  user-select: text;
}
</style>
