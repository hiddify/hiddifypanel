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
            <label for="ftd-days">{{ t('inbox.dialog.days') }}</label>
            <NumberStepper v-model="days" input-id="ftd-days" :min="1" :max="limits.max_days" :suffix="t('inbox.dialog.daysUnit')" :disabled="!enabled || busy" />
          </div>
          <div class="ftd-field">
            <label for="ftd-data">{{ t('inbox.dialog.data') }}</label>
            <div class="ftd-data">
              <NumberStepper v-model="amount" input-id="ftd-data" :min="1" :max="unit === 'mb' ? 1023 : limits.max_usage_gb" :step="unit === 'mb' ? 50 : 1" :disabled="!enabled || busy" />
              <SelectButton v-model="unit" :options="units" option-label="label" option-value="value" :allow-empty="false" :disabled="!enabled || busy" :aria-label="t('inbox.dialog.data')" />
            </div>
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
            <b><i class="pi pi-gift" /> {{ t('inbox.free.title') }}</b>
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
    grid-template-columns: 1fr 1.3fr;
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
.ftd-data {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
/* On a very narrow screen the unit picker wraps under the stepper instead of squeezing it. */
.ftd-data > :first-child {
  flex: 1 1 8rem;
  min-width: 0;
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
.ftd-bubble {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  align-self: flex-start;
  max-width: 100%;
  padding: 0.8rem 1rem;
  border-radius: 16px;
  border-end-start-radius: 4px;
  background: var(--surface-ground);
  border: 1px solid var(--surface-border);
}
.ftd-inherit {
  margin-inline-end: auto;
}
</style>
