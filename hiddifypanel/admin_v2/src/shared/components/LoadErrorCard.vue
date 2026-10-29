<script setup lang="ts">
/**
 * A page that could not load its data: what went wrong in plain words, numbered steps to fix it, Try again, and the
 * panel's own message under "Technical details" (to copy for support).
 *
 * A saved setting this panel version does not know (left by a newer or test version that ran on this server) gets its
 * name and the command that removes it; the panel's message for it is SQLAlchemy's "'<key>' is not among the defined
 * enum values. Enum name: configenum. …".
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { apiErrorMessage } from '@/core/api/client'

const props = defineProps<{ error: unknown }>()
const emit = defineEmits<{ retry: [] }>()

const { t } = useI18n()

type Kind = 'unknownSetting' | 'network' | 'auth' | 'server'

const message = computed(() => apiErrorMessage(props.error) || t('common.loadFailed'))
const status = computed(() => (props.error as { response?: { status?: number } })?.response?.status)
/** Only a setting name goes into the command shown below */
const unknownKey = computed(() => /'([a-z0-9_]+)' is not among the defined enum values\. Enum name: configenum/i.exec(message.value)?.[1] ?? '')
const kind = computed<Kind>(() => {
  if (unknownKey.value) return 'unknownSetting'
  const error = props.error as { response?: unknown; request?: unknown }
  if (error && typeof error === 'object' && 'request' in error && !error.response) return 'network'
  if (status.value === 401 || status.value === 403) return 'auth'
  return 'server'
})
const icon = computed(() => ({ unknownSetting: 'pi pi-database', network: 'pi pi-wifi', auth: 'pi pi-lock', server: 'pi pi-exclamation-triangle' })[kind.value])
const steps = computed(() => (kind.value === 'unknownSetting' ? [] : [t(`loadError.${kind.value}.step1`), t(`loadError.${kind.value}.step2`)]))

// MySQL: "key" is a reserved word, but not after "table."
const command = computed(() =>
  `mysql hiddifypanel -e "DELETE FROM str_config WHERE str_config.key='${unknownKey.value}'; DELETE FROM bool_config WHERE bool_config.key='${unknownKey.value}';"`,
)

const copied = ref<'' | 'command' | 'details'>('')
let copiedTimer: number | undefined
async function copy(what: 'command' | 'details') {
  try {
    await navigator.clipboard.writeText(what === 'command' ? command.value : message.value)
  } catch {
    return
  }
  copied.value = what
  window.clearTimeout(copiedTimer)
  copiedTimer = window.setTimeout(() => (copied.value = ''), 1600)
}
</script>

<template>
  <section class="load-error" :class="`load-error--${kind}`" role="alert">
    <header class="load-error__head">
      <span class="load-error__icon" aria-hidden="true"><i :class="icon" /></span>
      <div class="min-w-0">
        <h2 class="load-error__title">{{ t(`loadError.${kind}.title`) }}</h2>
        <p class="load-error__lead">
          <template v-if="kind === 'unknownSetting'">
            <i18n-t keypath="loadError.unknownSetting.lead" scope="global">
              <template #key><code class="load-error__key" dir="ltr">{{ unknownKey }}</code></template>
            </i18n-t>
          </template>
          <template v-else>{{ t(`loadError.${kind}.lead`) }}</template>
        </p>
      </div>
    </header>

    <h3 class="load-error__how">{{ t('loadError.howToFix') }}</h3>
    <ol class="load-error__steps">
      <template v-if="kind === 'unknownSetting'">
        <li>
          {{ t('loadError.unknownSetting.step1') }}
          <RouterLink :to="{ name: 'apply' }" class="load-error__link"><i class="pi pi-upload" />{{ t('loadError.unknownSetting.openUpdate') }}</RouterLink>
        </li>
        <li>
          {{ t('loadError.unknownSetting.step2') }}
          <RouterLink :to="{ name: 'backup' }" class="load-error__link"><i class="pi pi-download" />{{ t('loadError.unknownSetting.openBackup') }}</RouterLink>
        </li>
        <li>
          {{ t('loadError.unknownSetting.step3') }}
          <RouterLink :to="{ name: 'ssh' }" class="load-error__link"><i class="pi pi-desktop" />{{ t('loadError.unknownSetting.openTerminal') }}</RouterLink>
          <div class="load-error__cmd">
            <code dir="ltr">{{ command }}</code>
            <Button
              :icon="copied === 'command' ? 'pi pi-check' : 'pi pi-copy'"
              text
              rounded
              size="small"
              severity="secondary"
              class="load-error__cmd-copy"
              :aria-label="t('common.copy')"
              v-tooltip.top="copied === 'command' ? t('common.copied') : t('common.copy')"
              @click="copy('command')"
            />
          </div>
        </li>
        <li>{{ t('loadError.unknownSetting.step4') }}</li>
      </template>
      <li v-for="step in steps" v-else :key="step">{{ step }}</li>
    </ol>

    <div class="load-error__actions">
      <Button :label="t('loadError.retry')" icon="pi pi-refresh" size="small" @click="emit('retry')" />
    </div>

    <details class="load-error__details">
      <summary>{{ t('loadError.details') }}</summary>
      <div class="load-error__raw">
        <pre dir="ltr">{{ message }}</pre>
        <Button
          :icon="copied === 'details' ? 'pi pi-check' : 'pi pi-copy'"
          :label="copied === 'details' ? t('common.copied') : t('common.copy')"
          text
          size="small"
          severity="secondary"
          @click="copy('details')"
        />
      </div>
    </details>
  </section>
</template>

<style scoped>
.load-error {
  --le-accent: var(--p-red-500);
  position: relative;
  max-width: 46rem;
  padding: 1.25rem 1.35rem 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 16px;
  background: var(--p-content-background);
  box-shadow: 0 14px 34px -24px rgb(15 23 42 / 35%);
  overflow: hidden;
  animation: load-error-in 0.2s ease-out;
}
.load-error::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  background: linear-gradient(90deg, var(--le-accent), color-mix(in srgb, var(--le-accent) 25%, transparent));
}
.load-error--network,
.load-error--auth {
  --le-accent: var(--p-amber-500, #f59e0b);
}
.load-error__head {
  display: flex;
  align-items: flex-start;
  gap: 0.9rem;
}
.load-error__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 12px;
  color: var(--le-accent);
  background: color-mix(in srgb, var(--le-accent) 13%, transparent);
  font-size: 1.15rem;
}
.load-error__title {
  margin: 0.15rem 0 0.3rem;
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.35;
}
.load-error__lead {
  margin: 0;
  color: var(--p-text-muted-color);
  line-height: 1.6;
}
.load-error__key {
  padding: 0.05rem 0.4rem;
  border-radius: 6px;
  font-size: 0.85em;
  color: var(--p-text-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.load-error__how {
  margin: 1.1rem 0 0.55rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.load-error__steps {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: step;
}
.load-error__steps > li {
  position: relative;
  padding-inline-start: 2.1rem;
  line-height: 1.6;
  counter-increment: step;
}
.load-error__steps > li::before {
  content: counter(step);
  position: absolute;
  inset-inline-start: 0;
  top: 0.05rem;
  display: grid;
  place-items: center;
  width: 1.45rem;
  height: 1.45rem;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--p-primary-contrast-color, #fff);
  background: var(--p-primary-color);
}
.load-error__link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-inline-start: 0.35rem;
  font-weight: 600;
  color: var(--p-primary-color);
  text-decoration: none;
  white-space: nowrap;
}
.load-error__link:hover {
  text-decoration: underline;
}
.load-error__link i {
  font-size: 0.8rem;
}
.load-error__cmd {
  display: flex;
  align-items: flex-start;
  gap: 0.25rem;
  margin-top: 0.45rem;
  padding: 0.45rem 0.35rem 0.45rem 0.75rem;
  border: 1px solid rgb(148 163 184 / 18%);
  border-radius: 10px;
  background: #0f172a;
}
.load-error__cmd code {
  flex: 1 1 auto;
  min-width: 0;
  /* Whole, on as many lines as it needs: it is read before it is run */
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.55;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.78rem;
  color: #e2e8f0;
}
.load-error__cmd-copy {
  flex: none;
  color: #cbd5e1 !important;
}
.load-error__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1.1rem;
}
.load-error__details {
  margin-top: 0.9rem;
  padding-top: 0.75rem;
  border-top: 1px dashed var(--p-content-border-color);
  font-size: 0.85rem;
}
.load-error__details summary {
  cursor: pointer;
  color: var(--p-text-muted-color);
}
.load-error__raw {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.load-error__raw pre {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  padding: 0.6rem 0.75rem;
  border-radius: 8px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
}
@keyframes load-error-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .load-error {
    animation: none;
  }
}
@media (max-width: 575px) {
  .load-error {
    padding: 1rem 1rem 0.9rem;
  }
  .load-error__raw {
    flex-direction: column;
  }
}
</style>
