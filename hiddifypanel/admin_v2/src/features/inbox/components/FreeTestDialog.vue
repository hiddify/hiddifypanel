<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { isSuperAdmin } from '@/core/panelShell'
import NumberStepper from '@/shared/components/NumberStepper.vue'
import PackageChips from '@/features/inbox/components/PackageChips.vue'
import { splitData } from '@/features/inbox/format'
import { inboxApi, type Approval, type FreeTest } from '@/features/inbox/api'

/** Define the free test: on or off, how long, how much data, and whether each request needs the admin. */
const props = defineProps<{ free: FreeTest }>()
const emit = defineEmits<{ saved: [free: FreeTest] }>()
const visible = defineModel<boolean>('visible', { required: true })

const { t } = useI18n()
const toast = useToast()

type Unit = 'mb' | 'gb'
const enabled = ref(false)
const days = ref<number | null>(7)
const amount = ref<number | null>(500)
const unit = ref<Unit>('mb')
const approval = ref<Approval>('manual')
const busy = ref(false)

const units = computed(() => (['mb', 'gb'] as const).map((value) => ({ value, label: t(`inbox.free.unit.${value}`) })))
const approvals: { value: Approval; icon: string }[] = [
  { value: 'manual', icon: 'pi pi-user-edit' },
  { value: 'auto', icon: 'pi pi-bolt' },
]

watch(visible, (shown) => {
  if (!shown) return
  const pkg = props.free.package
  const data = splitData(pkg.usage_gb)
  // Opening the dialog of a package that is off is the way to turn it on.
  enabled.value = true
  days.value = pkg.days
  amount.value = data.amount
  unit.value = data.unit
  approval.value = pkg.approval
})

const usageGb = computed(() => {
  const value = amount.value ?? 0
  return unit.value === 'mb' ? Math.round((value / 1024) * 1000) / 1000 : value
})
const limits = computed(() => props.free.limits)
const valid = computed(
  () => !!days.value && days.value >= 1 && days.value <= limits.value.max_days && usageGb.value >= limits.value.min_usage_gb && usageGb.value <= limits.value.max_usage_gb,
)

async function save(inherit = false) {
  busy.value = true
  try {
    const saved = await inboxApi.savePackage(inherit ? null : { enabled: enabled.value, days: days.value ?? 7, usage_gb: usageGb.value, approval: approval.value })
    toast.add({ severity: 'success', summary: t('inbox.dialog.saved'), life: 2500 })
    emit('saved', saved)
    visible.value = false
  } catch (err) {
    toast.add({ severity: 'error', summary: t('inbox.dialog.saveFailed'), detail: apiErrorMessage(err), life: 5000 })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :draggable="false" :header="t('inbox.dialog.title')" :style="{ width: '32rem' }" :breakpoints="{ '575px': 'calc(100vw - 1.5rem)' }">
    <div class="ftd">
      <label class="ftd-switch" for="ftd-enabled">
        <span>
          <b>{{ t('inbox.dialog.enabled') }}</b>
          <small>{{ t('inbox.dialog.enabledHint') }}</small>
        </span>
        <ToggleSwitch v-model="enabled" input-id="ftd-enabled" :disabled="busy" />
      </label>

      <fieldset class="ftd-fields" :disabled="!enabled || busy">
        <div class="ftd-grid">
          <div class="ftd-field">
            <div class="ftd-head">
              <label for="ftd-days">{{ t('inbox.dialog.days') }}</label>
            </div>
            <NumberStepper v-model="days" input-id="ftd-days" :min="1" :max="limits.max_days" :suffix="t('inbox.dialog.daysUnit')" :disabled="!enabled || busy" />
          </div>
          <div class="ftd-field">
            <!-- The unit is a small segmented control beside the label, so both steppers keep the same width -->
            <div class="ftd-head">
              <label for="ftd-data">{{ t('inbox.dialog.data') }}</label>
              <SelectButton
                v-model="unit"
                class="ftd-unit"
                size="small"
                :options="units"
                option-label="label"
                option-value="value"
                :allow-empty="false"
                :disabled="!enabled || busy"
                :aria-label="t('inbox.dialog.data')"
              />
            </div>
            <NumberStepper v-model="amount" input-id="ftd-data" :min="1" :max="unit === 'mb' ? 1023 : limits.max_usage_gb" :step="unit === 'mb' ? 50 : 1" :disabled="!enabled || busy" />
          </div>
        </div>

        <div class="ftd-field">
          <span class="ftd-label">{{ t('inbox.dialog.approval') }}</span>
          <div class="ftd-modes" role="radiogroup" :aria-label="t('inbox.dialog.approval')">
            <button
              v-for="mode in approvals"
              :key="mode.value"
              type="button"
              role="radio"
              class="ftd-mode"
              :class="{ 'ftd-mode--on': approval === mode.value }"
              :aria-checked="approval === mode.value"
              @click="approval = mode.value"
            >
              <i :class="mode.icon" />
              <span>
                <b>{{ t(`inbox.free.${mode.value}`) }}</b>
                <small>{{ t(`inbox.free.${mode.value}Hint`) }}</small>
              </span>
            </button>
          </div>
        </div>

        <div class="ftd-preview">
          <span class="ftd-label">{{ t('inbox.dialog.preview') }}</span>
          <div class="ftd-bubble">
            <!-- A red satin ribbon across the box's top end corner with a bow on it; the tails sway, the loops breathe -->
            <span class="ftd-wrap" aria-hidden="true">
              <svg class="ftd-bow" viewBox="0 0 100 80">
                <defs>
                  <linearGradient id="ftd-band" gradientUnits="userSpaceOnUse" x1="52" y1="40" x2="60" y2="30">
                    <stop offset="0" stop-color="#991b1b" />
                    <stop offset=".35" stop-color="#dc2626" />
                    <stop offset=".6" stop-color="#f87171" />
                    <stop offset="1" stop-color="#b91c1c" />
                  </linearGradient>
                  <linearGradient id="ftd-satin" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0" stop-color="#fca5a5" />
                    <stop offset=".45" stop-color="#ef4444" />
                    <stop offset="1" stop-color="#991b1b" />
                  </linearGradient>
                  <linearGradient id="ftd-tail" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0" stop-color="#b91c1c" />
                    <stop offset=".5" stop-color="#f87171" />
                    <stop offset="1" stop-color="#991b1b" />
                  </linearGradient>
                </defs>
                <line x1="2" y1="-11" x2="114" y2="79" stroke="url(#ftd-band)" stroke-width="12" />
                <g class="ftd-tail ftd-tail--a">
                  <path d="M54 35 C48 45 44 55 36 68 L42 66 L44 72 C50 58 55 46 57.5 36 Z" fill="url(#ftd-tail)" />
                </g>
                <g class="ftd-tail ftd-tail--b">
                  <path d="M58 36 C60 47 58 58 62 72 L66 67 L71 70 C65 57 63 46 60.5 35 Z" fill="url(#ftd-tail)" />
                </g>
                <g class="ftd-loops">
                  <path d="M56 33 C46 18 30 14 27 22 C24 31 40 38 56 33 Z" fill="url(#ftd-satin)" />
                  <path d="M56 33 C47 26 37 23 32 24.5 C38 30 48 33 56 33 Z" fill="#7f1d1d" fill-opacity=".45" />
                  <path d="M56 33 C70 36 86 44 82 53 C78 61 63 47 56 33 Z" fill="url(#ftd-satin)" />
                  <path d="M56 33 C66 40 75 47 78 51.5 C70 48 62 41 56 33 Z" fill="#7f1d1d" fill-opacity=".4" />
                  <path d="M30 20 C34 16.5 41 18 46 22" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="1.2" stroke-linecap="round" />
                  <path d="M66 39 C73 41 79 45 80.5 49" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.1" stroke-linecap="round" />
                </g>
                <g transform="rotate(-40 56 33)">
                  <rect x="48.5" y="24.5" width="15" height="17" rx="5.5" fill="url(#ftd-satin)" stroke="#991b1b" stroke-width=".9" />
                  <path d="M52 26 C50.5 30 50.5 36 52 40" fill="none" stroke="#7f1d1d" stroke-opacity=".45" stroke-width="1.1" stroke-linecap="round" />
                  <path d="M60 26 C61.5 30 61.5 36 60 40" fill="none" stroke="#7f1d1d" stroke-opacity=".45" stroke-width="1.1" stroke-linecap="round" />
                  <path d="M55 27 C54.2 31 54.2 35 55 39" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="1.3" stroke-linecap="round" />
                </g>
              </svg>
            </span>
            <b><i class="pi pi-gift ftd-gift" aria-hidden="true" /> {{ t('inbox.free.title') }}</b>
            <PackageChips :days="days ?? 0" :usage-gb="usageGb" tag />
          </div>
        </div>
      </fieldset>
    </div>

    <template #footer>
      <Button v-if="free.own && !isSuperAdmin" :label="t('inbox.dialog.inherit')" icon="pi pi-sitemap" severity="secondary" text :disabled="busy" class="ftd-inherit" @click="save(true)" />
      <Button :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="visible = false" />
      <Button :label="t('inbox.dialog.save')" icon="pi pi-check" :loading="busy" :disabled="enabled && !valid" @click="save()" />
    </template>
  </Dialog>
</template>

<style scoped>
.ftd {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}
.ftd-switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 14px;
  background: var(--surface-ground);
  cursor: pointer;
}
.ftd-switch span,
.ftd-mode span {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.ftd small {
  color: var(--text-color-secondary);
  font-weight: 400;
  line-height: 1.4;
}
.ftd-fields {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  margin: 0;
  padding: 0;
  border: 0;
  min-width: 0;
  container: ftd-fields / inline-size;
  transition: opacity 0.15s;
}
.ftd-fields:disabled {
  opacity: 0.5;
}
/* Days and data side by side only when both fit; on a phone they stack, so the data stepper keeps its width. */
.ftd-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
@container ftd-fields (min-width: 28rem) {
  .ftd-grid {
    grid-template-columns: 1fr 1fr;
  }
}
.ftd-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}
.ftd-field label,
.ftd-label {
  font-size: 0.85rem;
  font-weight: 600;
}
/* Same height on both columns, so the two steppers line up whether or not the head holds the unit picker. */
.ftd-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  min-height: 1.9rem;
}
/* An iOS-style segmented control: a tinted track, the chosen segment a raised white pill. */
.ftd-unit {
  padding: 2px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
}
.ftd-unit :deep(.p-togglebutton) {
  min-width: 2.6rem;
  padding: 0.15rem 0.6rem;
  border: 0;
  border-radius: 7px;
  background: transparent;
  font-size: 0.78rem;
  font-weight: 600;
}
.ftd-unit :deep(.p-togglebutton-content) {
  padding: 0;
  background: transparent;
  box-shadow: none;
}
.ftd-unit :deep(.p-togglebutton-checked) {
  background: var(--p-content-background);
  box-shadow:
    0 1px 3px rgb(0 0 0 / 0.12),
    0 0 0 0.5px rgb(0 0 0 / 0.04);
}
/* Dark: the chosen segment is lighter than the track, as on iOS. */
html.app-dark .ftd-unit :deep(.p-togglebutton-checked) {
  background: color-mix(in srgb, var(--ftd-unit-color) 26%, var(--p-content-background));
}
/* Each unit has its own soft colour (MB blue, GB violet): faint when off, a light tint of it when chosen. */
.ftd-unit :deep(.p-togglebutton:nth-child(1)) {
  --ftd-unit-color: var(--p-blue-500);
}
.ftd-unit :deep(.p-togglebutton:nth-child(2)) {
  --ftd-unit-color: var(--p-violet-500);
}
.ftd-unit :deep(.p-togglebutton) {
  color: color-mix(in srgb, var(--ftd-unit-color) 65%, var(--p-text-muted-color));
}
.ftd-unit :deep(.p-togglebutton:not(.p-togglebutton-checked):hover) {
  background: color-mix(in srgb, var(--ftd-unit-color) 8%, transparent);
}
.ftd-unit :deep(.p-togglebutton.p-togglebutton-checked) {
  color: var(--ftd-unit-color);
  background: color-mix(in srgb, var(--ftd-unit-color) 14%, var(--p-content-background));
}
.ftd-modes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 0.6rem;
}
.ftd-mode {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding: 0.8rem 0.9rem;
  border: 1.5px solid var(--surface-border);
  border-radius: 14px;
  background: var(--surface-card);
  color: var(--text-color);
  text-align: start;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.ftd-mode > .pi {
  margin-top: 0.15rem;
  color: var(--text-color-secondary);
}
.ftd-mode--on {
  border-color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 8%, var(--surface-card));
}
.ftd-mode--on > .pi {
  color: var(--primary-color);
}
.ftd-preview {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
/* The preview is a gift box: a soft warm box with a red satin ribbon and bow across its top end corner. */
.ftd-bubble {
  --ftd-gift-color: var(--p-red-500);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  align-self: flex-start;
  max-width: 100%;
  padding: 0.8rem 5.6rem 0.8rem 1rem;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--ftd-gift-color) 25%, var(--surface-border));
  background: linear-gradient(135deg, color-mix(in srgb, var(--ftd-gift-color) 5%, var(--p-content-background)), color-mix(in srgb, var(--p-amber-400) 7%, var(--p-content-background)));
  box-shadow: 0 8px 20px -12px color-mix(in srgb, var(--ftd-gift-color) 55%, transparent);
}
html[dir='rtl'] .ftd-bubble {
  padding: 0.8rem 1rem 0.8rem 5.6rem;
}
/* The ribbon layer: clipped to the box's rounded corners. The ribbon crosses the top end corner at 45 degrees. */
.ftd-wrap {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
}
.ftd-bow {
  position: absolute;
  /* nudged toward the corner: the box clips what passes its edges */
  top: -0.55rem;
  inset-inline-end: -0.45rem;
  width: 6.5rem;
  height: 5.2rem;
  filter: drop-shadow(0 2px 2px rgb(127 29 29 / 0.25));
}
html[dir='rtl'] .ftd-bow {
  transform: scaleX(-1);
}
/* Each tail swings from the knot, softly and out of step with the other, like satin in a light breeze. */
.ftd-tail,
.ftd-loops {
  transform-box: view-box;
  transform-origin: 56px 33px;
}
.ftd-tail {
  animation: ftd-tail-sway 3.2s ease-in-out infinite;
}
.ftd-tail--b {
  animation-duration: 3.8s;
  animation-delay: -1.4s;
}
.ftd-loops {
  animation: ftd-loops-breathe 3.6s ease-in-out infinite;
}
@keyframes ftd-tail-sway {
  0%,
  100% {
    transform: rotate(-5deg) skewX(2deg);
  }
  50% {
    transform: rotate(6deg) skewX(-3deg);
  }
}
@keyframes ftd-loops-breathe {
  0%,
  100% {
    transform: scale(1) rotate(0);
  }
  50% {
    transform: scale(1.05) rotate(-2deg);
  }
}
/* The box's content stays above the ribbon. */
.ftd-bubble > b,
.ftd-bubble > :not(.ftd-wrap) {
  position: relative;
}
/* A lively gift icon: its colour, a soft glow and a little shake every few seconds. */
.ftd-gift {
  display: inline-block;
  color: var(--ftd-gift-color);
  filter: drop-shadow(0 0 6px color-mix(in srgb, var(--ftd-gift-color) 45%, transparent));
  transform-origin: 50% 80%;
  animation: ftd-gift-wiggle 3.2s ease-in-out infinite;
}
@keyframes ftd-gift-wiggle {
  0%,
  72%,
  100% {
    transform: rotate(0) scale(1);
  }
  78% {
    transform: rotate(-14deg) scale(1.12);
  }
  84% {
    transform: rotate(11deg) scale(1.12);
  }
  90% {
    transform: rotate(-6deg) scale(1.05);
  }
  95% {
    transform: rotate(3deg) scale(1);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ftd-gift,
  .ftd-tail,
  .ftd-loops {
    animation: none;
  }
}
.ftd-inherit {
  margin-inline-end: auto;
}
</style>
