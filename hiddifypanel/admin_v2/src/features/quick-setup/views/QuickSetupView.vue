<template>
  <div class="qs" :class="{ 'qs--rtl': rtl }">
    <div class="qs__bg" aria-hidden="true" />

    <header class="qs__top">
      <div class="qs__brand">
        <img v-if="logoUrl" :src="logoUrl" alt="" class="qs__logo" />
        <div>
          <div class="qs__title">{{ t('quickSetup.title') }}</div>
          <div class="qs__subtitle">{{ t('quickSetup.subtitle') }}</div>
        </div>
      </div>
      <Button :label="t('quickSetup.skip')" text severity="secondary" size="small" icon="pi pi-times" @click="skip" />
    </header>

    <!-- Stepper -->
    <nav class="qs-stepper" :aria-label="t('quickSetup.title')">
      <div class="qs-stepper__track"><div class="qs-stepper__fill" :style="{ width: `${progress}%` }" /></div>
      <ol ref="stepList" class="qs-stepper__list">
        <li
          v-for="(step, i) in steps"
          :key="step.id"
          class="qs-stepper__item"
          :class="{ 'qs-stepper__item--done': i < current, 'qs-stepper__item--now': i === current }"
        >
          <button type="button" class="qs-stepper__dot" :disabled="i > furthest || busy" :aria-current="i === current ? 'step' : undefined" @click="goTo(i)">
            <i v-if="i < current" class="pi pi-check" />
            <i v-else :class="step.icon" />
          </button>
          <span class="qs-stepper__label">{{ step.title }}</span>
        </li>
      </ol>
      <div class="qs-stepper__mobile">
        <span class="qs-stepper__count">{{ t('quickSetup.stepOf', { n: current + 1, total: steps.length }) }}</span>
        <span class="qs-stepper__mobile-title">{{ steps[current]?.title }}</span>
      </div>
    </nav>

    <main class="qs-card">
      <div v-if="loading" class="qs-card__loading">
        <Skeleton height="1.5rem" width="40%" class="mb-3" />
        <Skeleton height="6rem" class="mb-3" />
        <Skeleton height="6rem" />
      </div>
      <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>
      <template v-else-if="state">
        <div class="qs-card__head">
          <span class="qs-card__icon"><i :class="steps[current]?.icon" /></span>
          <div class="min-w-0">
            <h2 class="qs-card__title">{{ steps[current]?.title }}</h2>
            <p class="qs-card__lead">{{ steps[current]?.lead }}</p>
          </div>
        </div>

        <Transition :name="direction" mode="out-in">
          <div :key="steps[current]?.id" class="qs-card__body">
            <StepLanguage v-if="steps[current]?.id === 'language'" ref="stepRef" :state="state" @error="showError" />
            <StepPassword v-else-if="steps[current]?.id === 'password'" ref="stepRef" @error="showError" />
            <StepDomains v-else-if="steps[current]?.id === 'domains'" ref="stepRef" :state="state" @error="showError" @saved="state = $event" />
            <ProtocolsView v-else-if="steps[current]?.id === 'protocols'" ref="stepRef" embedded />
            <div v-else-if="steps[current]?.id === 'nodes'" class="flex flex-col gap-4">
              <div class="qs-callout">
                <i class="pi pi-sitemap" />
                <span>{{ t('quickSetup.nodes.question') }}</span>
              </div>
              <NodesView embedded />
            </div>
            <StepFinish v-else-if="steps[current]?.id === 'finish'" :state="state" />
          </div>
        </Transition>
      </template>
    </main>

    <footer v-if="state" class="qs-nav">
      <Button :label="t('quickSetup.back')" icon="pi pi-arrow-left" severity="secondary" text :disabled="current === 0 || busy" class="qs-nav__back" @click="back" />
      <span class="qs-nav__spacer" />
      <Button
        v-if="steps[current]?.id === 'nodes'"
        :label="t('quickSetup.nodes.skip')"
        severity="secondary"
        outlined
        :disabled="busy"
        @click="next(true)"
      />
      <Button
        v-if="steps[current]?.id !== 'finish'"
        :label="t('quickSetup.next')"
        icon="pi pi-arrow-right"
        icon-pos="right"
        :loading="busy"
        @click="next()"
      />
      <Button v-else :label="t('quickSetup.finish.button')" icon="pi pi-check" :loading="busy" class="qs-nav__finish" @click="finish" />
    </footer>

    <Toast />
    <ConfirmDialog />
    <LegacyActionDialog />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import Toast from 'primevue/toast'
import LegacyActionDialog from '@/shared/components/LegacyActionDialog.vue'
import { apiErrorMessage } from '@/core/api/client'
import { needsQuickSetup, openLegacyAction } from '@/core/panelShell'
import { QUICK_SETUP_SKIPPED_KEY } from '@/router'
import ProtocolsView from '@/features/protocols/views/ProtocolsView.vue'
import NodesView from '@/features/nodes/views/NodesView.vue'
import StepDomains from '@/features/quick-setup/components/StepDomains.vue'
import StepFinish from '@/features/quick-setup/components/StepFinish.vue'
import StepLanguage from '@/features/quick-setup/components/StepLanguage.vue'
import StepPassword from '@/features/quick-setup/components/StepPassword.vue'
import { quickSetupApi, type QuickSetupState } from '@/features/quick-setup/api'

type StepId = 'language' | 'password' | 'domains' | 'protocols' | 'nodes' | 'finish'
interface StepRef {
  submit?: () => Promise<boolean>
  save?: () => Promise<boolean>
}

const { t, locale } = useI18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()

const state = ref<QuickSetupState | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const busy = ref(false)
const current = ref(0)
const furthest = ref(0)
const direction = ref<'qs-forward' | 'qs-backward'>('qs-forward')
const stepRef = ref<StepRef | null>(null)
const stepList = ref<HTMLOListElement | null>(null)

/** Mobile: the step strip slides so the current step is centered (only the strip scrolls). */
function centerCurrentStep(smooth = true) {
  const list = stepList.value
  const item = list?.children[current.value] as HTMLElement | undefined
  if (!list || !item || list.scrollWidth <= list.clientWidth) return
  // Scroll by the on-screen distance between the two centers: same in LTR and RTL.
  const itemBox = item.getBoundingClientRect()
  const listBox = list.getBoundingClientRect()
  const delta = itemBox.left + itemBox.width / 2 - (listBox.left + listBox.width / 2)
  list.scrollBy({ left: delta, behavior: smooth ? 'smooth' : 'auto' })
}
const logoUrl = window.__PANEL_LOGO_URL__ || ''
const rtl = computed(() => locale.value === 'fa' || locale.value === 'ar')

const STEP_ICONS: Record<StepId, string> = {
  language: 'pi pi-language',
  password: 'pi pi-lock',
  domains: 'pi pi-link',
  protocols: 'pi pi-sliders-h',
  nodes: 'pi pi-sitemap',
  finish: 'pi pi-flag',
}

const steps = computed(() => {
  const ids: StepId[] = ['language', 'password', 'domains', 'protocols', ...(state.value?.is_node ? [] : (['nodes'] as StepId[])), 'finish']
  return ids.map((id) => ({ id, icon: STEP_ICONS[id], title: t(`quickSetup.steps.${id}.title`), lead: t(`quickSetup.steps.${id}.lead`) }))
})
const progress = computed(() => (steps.value.length > 1 ? (current.value / (steps.value.length - 1)) * 100 : 0))

function showError(message: string) {
  toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: message, life: 7000 })
}

function syncUrl() {
  void router.replace({ query: { ...route.query, step: String(current.value + 1) } })
}

function goTo(index: number) {
  if (index === current.value || index > furthest.value || busy.value) return
  direction.value = index > current.value ? 'qs-forward' : 'qs-backward'
  current.value = index
  syncUrl()
}

function back() {
  goTo(current.value - 1)
}

async function next(skipSave = false) {
  if (busy.value) return
  busy.value = true
  try {
    const step = stepRef.value
    const ok = skipSave ? true : step?.submit ? await step.submit() : step?.save ? await step.save() : true
    if (!ok) return
    direction.value = 'qs-forward'
    current.value = Math.min(current.value + 1, steps.value.length - 1)
    furthest.value = Math.max(furthest.value, current.value)
    syncUrl()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } finally {
    busy.value = false
  }
}

async function finish() {
  busy.value = true
  try {
    const { reinstall_url } = await quickSetupApi.finish()
    needsQuickSetup.value = false
    // The reinstall applies the new domains; its page shows the live log and the new admin links.
    openLegacyAction({ title: t('quickSetup.finish.running'), url: reinstall_url, method: 'post' })
  } catch (err) {
    showError(apiErrorMessage(err))
  } finally {
    busy.value = false
  }
}

function skip() {
  try {
    sessionStorage.setItem(QUICK_SETUP_SKIPPED_KEY, '1')
  } catch {
    // storage blocked: the dashboard may bring the setup back
  }
  void router.push({ path: '/' })
}

watch(current, () => nextTick(() => centerCurrentStep()))

watch(
  () => steps.value.length,
  (count) => {
    if (current.value > count - 1) current.value = count - 1
  },
)

onMounted(async () => {
  try {
    state.value = await quickSetupApi.state()
    const fromUrl = Number(route.query.step) - 1
    if (Number.isInteger(fromUrl) && fromUrl > 0) {
      // e.g. after the language step reloads the page in the new language
      current.value = Math.min(fromUrl, steps.value.length - 1)
      furthest.value = current.value
    }
  } catch (err) {
    loadError.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
  await nextTick()
  centerCurrentStep(false)
})
</script>

<style>
/* Shared by the step components (they render inside .qs). */
.qs {
  --qs-accent: var(--p-primary-color);
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.25rem 1rem 6.5rem;
  color: var(--p-text-color);
  background: var(--p-surface-50, #f8fafc);
}
.app-dark .qs {
  background: var(--p-surface-950, #0b1120);
}
.qs__bg {
  position: absolute;
  inset: 0 0 auto 0;
  height: 22rem;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(60rem 18rem at 15% -10%, color-mix(in srgb, var(--qs-accent) 22%, transparent), transparent 70%),
    radial-gradient(40rem 16rem at 90% -20%, color-mix(in srgb, #ec4899 14%, transparent), transparent 70%);
}
.qs > *:not(.qs__bg) {
  position: relative;
  z-index: 1;
  width: min(100%, 52rem);
}
.qs__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.qs__brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.qs__logo {
  width: 2.6rem;
  height: 2.6rem;
  object-fit: contain;
  border-radius: 12px;
  padding: 0.3rem;
  background: var(--qs-accent);
}
.qs__title {
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.2;
}
.qs__subtitle {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

/* Stepper */
.qs-stepper {
  position: relative;
  margin-bottom: 1.25rem;
}
.qs-stepper__track {
  position: absolute;
  inset-inline: 1.3rem;
  top: 1.3rem;
  height: 3px;
  border-radius: 3px;
  background: var(--p-content-border-color);
  overflow: hidden;
}
.qs-stepper__fill {
  height: 100%;
  background: linear-gradient(90deg, var(--qs-accent), color-mix(in srgb, var(--qs-accent) 60%, #ec4899));
  transition: width 0.45s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.qs--rtl .qs-stepper__fill {
  margin-inline-start: auto;
}
.qs-stepper__list {
  position: relative;
  display: flex;
  justify-content: space-between;
  margin: 0;
  padding: 0;
  list-style: none;
}
.qs-stepper__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.45rem;
  width: 5.5rem;
  text-align: center;
}
.qs-stepper__dot {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  border: 2px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: var(--p-text-muted-color);
  cursor: pointer;
  transition:
    transform 0.2s ease,
    background-color 0.25s ease,
    border-color 0.25s ease,
    color 0.25s ease,
    box-shadow 0.25s ease;
}
.qs-stepper__dot:disabled {
  cursor: default;
}
.qs-stepper__item--done .qs-stepper__dot {
  border-color: var(--qs-accent);
  background: var(--qs-accent);
  color: var(--p-primary-contrast-color, #fff);
}
.qs-stepper__item--now .qs-stepper__dot {
  border-color: var(--qs-accent);
  color: var(--qs-accent);
  transform: scale(1.08);
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--qs-accent) 18%, transparent);
}
.qs-stepper__label {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  line-height: 1.25;
}
.qs-stepper__item--now .qs-stepper__label {
  color: var(--p-text-color);
  font-weight: 600;
}
.qs-stepper__mobile {
  display: none;
}

/* Card */
.qs-card {
  padding: 1.5rem;
  border-radius: 20px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  box-shadow: 0 20px 45px -30px rgba(15, 23, 42, 0.45);
  overflow: hidden;
}
.qs-card__head {
  display: flex;
  align-items: flex-start;
  gap: 0.9rem;
  margin-bottom: 1.4rem;
}
.qs-card__icon {
  width: 2.8rem;
  height: 2.8rem;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 14px;
  font-size: 1.2rem;
  color: var(--qs-accent);
  background: color-mix(in srgb, var(--qs-accent) 13%, transparent);
}
.qs-card__title {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 700;
}
.qs-card__lead {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color);
}

/* Footer nav */
.qs-nav {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 1.1rem;
}
.qs-nav__spacer {
  flex: 1;
}

/* Step building blocks */
.qs-label {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
  font-weight: 600;
}
.qs-label i {
  color: var(--qs-accent);
}
.qs-hint {
  display: block;
  margin: 0;
  font-size: 0.83rem;
  line-height: 1.5;
  color: var(--p-text-muted-color);
}
.qs-error {
  color: var(--p-red-500, #ef4444);
}
.qs-ok {
  color: var(--p-green-600, #16a34a);
}
.qs-required {
  color: var(--p-red-500, #ef4444);
}
.qs-optional {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.qs-narrow {
  max-width: 28rem;
}
.qs-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 10.5rem), 1fr));
  gap: 0.6rem;
  margin-top: 0.75rem;
}
.qs-option {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.8rem 0.9rem;
  border-radius: 14px;
  border: 1.5px solid var(--p-content-border-color);
  background: var(--p-content-background);
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease,
    box-shadow 0.18s ease;
}
.qs-option:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--qs-accent) 45%, var(--p-content-border-color));
}
.qs-option--on {
  border-color: var(--qs-accent);
  background: color-mix(in srgb, var(--qs-accent) 8%, var(--p-content-background));
  box-shadow: 0 6px 18px -12px var(--qs-accent);
}
.qs-option__flag {
  font-size: 1.5rem;
  line-height: 1;
}
.qs-option__name {
  flex: 1;
  font-weight: 600;
}
.qs-option__check {
  color: var(--qs-accent);
  animation: qs-pop 0.3s cubic-bezier(0.2, 1.4, 0.4, 1) both;
}
.qs-callout,
.qs-warning {
  display: flex;
  gap: 0.7rem;
  align-items: flex-start;
  padding: 0.8rem 1rem;
  border-radius: 14px;
  font-size: 0.9rem;
  line-height: 1.55;
  background: color-mix(in srgb, var(--qs-accent) 8%, transparent);
}
.qs-callout i {
  margin-top: 0.2rem;
  color: var(--qs-accent);
}
.qs-warning {
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 10%, transparent);
}
.qs-warning i {
  margin-top: 0.2rem;
  color: var(--p-amber-600, #d97706);
}
.qs-warning ul {
  margin: 0;
  padding-inline-start: 1rem;
}
.qs-ips {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1rem;
  border-radius: 16px;
  border: 1px dashed color-mix(in srgb, var(--qs-accent) 40%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--qs-accent) 4%, transparent);
}
.qs-ips__intro {
  display: flex;
  gap: 0.75rem;
}
.qs-ips__intro > i {
  margin-top: 0.2rem;
  color: var(--qs-accent);
}
.qs-steps-list {
  margin: 0.35rem 0 0;
  padding-inline-start: 1.1rem;
  font-size: 0.87rem;
  color: var(--p-text-muted-color);
}
.qs-ips__list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 16rem), 1fr));
  gap: 0.5rem;
}
.qs-ip {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 0.4rem 0.45rem 0.8rem;
  border-radius: 12px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.qs-ip__type {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--qs-accent);
}
.qs-ip__type small {
  font-weight: 500;
  color: var(--p-text-muted-color);
}
.qs-ip__value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.9rem;
  text-align: start;
}
.qs-switch-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.85rem 1rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  cursor: pointer;
}
.qs-switch-row__icon {
  width: 2.2rem;
  height: 2.2rem;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: var(--p-red-500, #ef4444);
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 10%, transparent);
}
.qs-finish-hero {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 1rem;
  border-radius: 16px;
  background: linear-gradient(120deg, color-mix(in srgb, var(--qs-accent) 14%, transparent), color-mix(in srgb, #22c55e 12%, transparent));
}
.qs-finish-hero__icon {
  width: 3rem;
  height: 3rem;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 1.25rem;
  color: #fff;
  background: var(--p-green-500, #22c55e);
  animation: qs-pop 0.5s cubic-bezier(0.2, 1.4, 0.4, 1) both;
}
.qs-summary {
  margin: 0;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  overflow: hidden;
}
.qs-summary__row {
  display: grid;
  grid-template-columns: minmax(8rem, 14rem) 1fr;
  gap: 0.75rem;
  padding: 0.7rem 1rem;
}
.qs-summary__row + .qs-summary__row {
  border-top: 1px solid var(--p-content-border-color);
}
.qs-summary__row dt {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  color: var(--p-text-muted-color);
  font-size: 0.88rem;
}
.qs-summary__row dt i {
  color: var(--qs-accent);
}
.qs-summary__row dd {
  margin: 0;
  font-weight: 600;
  overflow-wrap: anywhere;
  text-align: start;
}
.qs-docs {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.9rem 1rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  color: inherit;
  text-decoration: none;
  transition:
    border-color 0.18s ease,
    transform 0.18s ease;
}
.qs-docs:hover {
  border-color: var(--qs-accent);
  transform: translateY(-1px);
}
.qs-docs > i:first-child {
  font-size: 1.2rem;
  color: var(--qs-accent);
}

/* Step transitions (mirrored in RTL) */
.qs-forward-enter-active,
.qs-forward-leave-active,
.qs-backward-enter-active,
.qs-backward-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.qs-forward-enter-from,
.qs-backward-leave-to {
  opacity: 0;
  transform: translateX(28px);
}
.qs-forward-leave-to,
.qs-backward-enter-from {
  opacity: 0;
  transform: translateX(-28px);
}
.qs--rtl .qs-forward-enter-from,
.qs--rtl .qs-backward-leave-to {
  transform: translateX(-28px);
}
.qs--rtl .qs-forward-leave-to,
.qs--rtl .qs-backward-enter-from {
  transform: translateX(28px);
}
@keyframes qs-pop {
  from {
    transform: scale(0.4);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

/* Mobile */
@media (max-width: 720px) {
  .qs {
    padding: 0.9rem 0.75rem 6.5rem;
  }
  .qs__subtitle {
    display: none;
  }
  .qs-stepper__track {
    position: static;
    margin-bottom: 0.6rem;
  }
  .qs-stepper__mobile {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    margin-bottom: 0.55rem;
  }
  /* The steps as a sliding strip; the current one is kept centered (centerCurrentStep). */
  .qs-stepper__list {
    order: 3;
    justify-content: flex-start;
    gap: 0.25rem;
    margin: 0 -0.75rem;
    padding: 0.35rem 0.75rem 0.25rem;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scroll-snap-type: x proximity;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    mask-image: linear-gradient(90deg, transparent 0, #000 1.25rem, #000 calc(100% - 1.25rem), transparent 100%);
  }
  .qs-stepper__list::-webkit-scrollbar {
    display: none;
  }
  .qs-stepper {
    display: flex;
    flex-direction: column;
  }
  .qs-stepper__item {
    position: relative;
    flex: 0 0 4.6rem;
    width: 4.6rem;
    scroll-snap-align: center;
  }
  /* connector to the next step (the full-width track is the progress bar above) */
  .qs-stepper__item:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 1.05rem;
    inset-inline-start: calc(50% + 1.25rem);
    width: calc(100% - 2.5rem + 0.25rem);
    height: 2px;
    border-radius: 2px;
    background: var(--p-content-border-color);
    transition: background-color 0.3s ease;
  }
  .qs-stepper__item--done:not(:last-child)::after {
    background: var(--qs-accent);
  }
  .qs-stepper__dot {
    width: 2.2rem;
    height: 2.2rem;
    font-size: 0.85rem;
  }
  .qs-stepper__item--now .qs-stepper__dot {
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--qs-accent) 18%, transparent);
  }
  .qs-stepper__label {
    font-size: 0.72rem;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .qs-stepper__count {
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--qs-accent);
  }
  .qs-stepper__mobile-title {
    font-weight: 600;
  }
  .qs-card {
    padding: 1.1rem;
    border-radius: 16px;
  }
  .qs-card__head {
    display: none;
  }
  .qs-nav {
    position: fixed;
    inset-inline: 0;
    bottom: 0;
    z-index: 20;
    width: 100% !important;
    margin: 0;
    padding: 0.7rem 0.9rem calc(0.7rem + env(safe-area-inset-bottom));
    background: var(--p-content-background);
    border-top: 1px solid var(--p-content-border-color);
    box-shadow: 0 -10px 24px -18px rgba(15, 23, 42, 0.5);
  }
  .qs-summary__row {
    grid-template-columns: 1fr;
    gap: 0.2rem;
  }
}
@media (prefers-reduced-motion: reduce) {
  .qs-forward-enter-active,
  .qs-forward-leave-active,
  .qs-backward-enter-active,
  .qs-backward-leave-active,
  .qs-stepper__fill,
  .qs-stepper__dot {
    transition: none;
  }
  .qs-option__check,
  .qs-finish-hero__icon {
    animation: none;
  }
}
</style>
