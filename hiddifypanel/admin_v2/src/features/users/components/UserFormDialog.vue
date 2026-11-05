<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import SplitButton from 'primevue/splitbutton'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import Json5Editor from '@/shared/components/Json5Editor.vue'
import AdditionalConfigsEditor from '@/shared/components/AdditionalConfigsEditor.vue'
import { cleanConfigRows, configRowProblem } from '@/shared/utils/additional-configs'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import FormError from '@/shared/components/FormError.vue'
import { scrollToFirstInvalid } from '@/shared/utils/scroll-to-invalid'
import TagSelect from '@/features/tags/components/TagSelect.vue'
import FormSection from '@/features/users/components/package/FormSection.vue'
import PackageTimeLine, { type TimeState } from '@/features/users/components/package/PackageTimeLine.vue'
import PresetChips from '@/features/users/components/package/PresetChips.vue'
import ResetModePicker from '@/features/users/components/package/ResetModePicker.vue'
import { saveFormTags } from '@/features/tags/useTags'
import {
  UNLIMITED_DAYS,
  UNLIMITED_GB,
  usersApi,
  type AdditionalConfig,
  type UserDetail,
  type UserMode,
  type UserPayload,
  type UserRow,
  type UsersState,
} from '@/features/users/api'
import { unitLabel } from '@/shared/utils/format-metrics'
import { daysFromToday, gb, sizeText, relativeDays, shortDate } from '@/features/users/format'

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/** `user`: the one being edited (its detail is loaded); null adds a new user. */
const props = defineProps<{
  user: UserRow | null
  state: UsersState | null
  /** Show just one section (a quick edit from the list) instead of the whole form. */
  focus?: 'usage' | 'time' | null
}>()
const visible = defineModel<boolean>('visible', { required: true })
/** atEnd: a new user goes to the end of the users list (the add button's menu), not to the top. */
const emit = defineEmits<{ saved: [user: UserDetail, created: boolean, atEnd: boolean] }>()

const { t, locale } = useI18n()

const detail = ref<UserDetail | null>(null)
const loading = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)
const touched = ref(false)
const formEl = ref<HTMLFormElement | null>(null)
/** Which add was asked: the button (top of the list, also Enter in a field) or its "at end" entry. */
const addAtEnd = ref(false)
const addMenu = computed(() => [
  { label: t('users.form.add'), icon: 'pi pi-user-plus', command: () => addAt(false) },
  { label: t('users.form.addAtEnd'), icon: 'pi pi-arrow-down', command: () => addAt(true) },
])
function addAt(end: boolean) {
  addAtEnd.value = end
  formEl.value?.requestSubmit()
}
const showAdvanced = ref(false)

const name = ref('')
const comment = ref('')
const enable = ref(true)
const usageLimit = ref<number | null>(100)
const packageDays = ref<number | null>(30)
const mode = ref<UserMode>('no_reset')
const uuid = ref('')
const ownerUuid = ref<string | null>(null)
const telegramId = ref<number | null>(null)
const preferredOutbound = ref<number | null>(null)
const toast = useToast()
const tagIds = ref<number[]>([])
const initialTags = ref<number[]>([])
const configs = ref<AdditionalConfig[]>([])
const extraText = ref('{}')
const resetUsage = ref(false)
const resetDays = ref(false)

const editing = computed(() => props.user !== null)
const canOverrideOutbound = computed(() => Boolean(props.state?.capabilities?.override_preferred_outbound))
const canAddSublinks = computed(() => Boolean(props.state?.capabilities?.add_extra_sublinks))
const canModifyUserExtra = computed(() => Boolean(props.state?.capabilities?.modify_user_extra))

function randomUuid(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6]! & 0x0f) | 0x40
  b[8] = (b[8]! & 0x3f) | 0x80
  const h = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}

function fill(d: UserDetail | null) {
  name.value = d?.name ?? ''
  comment.value = d?.comment ?? ''
  enable.value = d?.enable ?? true
  usageLimit.value = d?.usage_limit_GB ?? 100
  packageDays.value = d?.package_days ?? 30
  mode.value = d?.mode ?? 'no_reset'
  uuid.value = d?.uuid ?? randomUuid()
  ownerUuid.value = d?.owner_uuid ?? props.state?.me_uuid ?? null
  telegramId.value = d?.telegram_id ?? null
  preferredOutbound.value = d?.preferred_outbound ?? null
  tagIds.value = [...(d?.tags ?? [])]
  initialTags.value = [...tagIds.value]
  configs.value = (d?.additional_configs ?? []).map((row) => [...row] as AdditionalConfig)
  extraText.value = d?.extra_params ?? '{}'
}

watch(visible, async (open) => {
  if (!open) return
  error.value = null
  touched.value = false
  busy.value = false
  showAdvanced.value = false
  resetUsage.value = false
  resetDays.value = false
  detail.value = null
  fill(null)
  if (!props.user) return
  loading.value = true
  try {
    detail.value = await usersApi.get(props.user.uuid)
    fill(detail.value)
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
})

// ---- Data section
const usedGb = computed(() => (resetUsage.value ? 0 : detail.value?.current_usage_GB ?? 0))

const nextReset = computed(() => (mode.value !== 'no_reset' && detail.value?.days_to_reset != null ? detail.value.days_to_reset : null))

// ---- Time section: started N ago / remaining / package days
const started = computed(() => (resetDays.value ? null : detail.value?.start_date ?? null))
const startedDays = computed(() => (started.value ? -daysFromToday(started.value) : null))
const remaining = computed(() => {
  const days = packageDays.value ?? 0
  return startedDays.value === null ? days : days - startedDays.value
})
const expireDate = computed(() => {
  if (!started.value) return null
  const d = new Date(`${started.value}T00:00:00`)
  d.setDate(d.getDate() + (packageDays.value ?? 0))
  return d.toISOString().slice(0, 10)
})

const unlimitedTime = computed(() => (packageDays.value ?? 0) >= UNLIMITED_DAYS)
/** pending: restart chosen (on save) · waiting: not started yet · running: started (ended when past). */
const timeState = computed<TimeState>(() => {
  if (resetDays.value) return 'pending'
  if (!started.value) return 'waiting'
  return !unlimitedTime.value && remaining.value < 0 ? 'ended' : 'running'
})

/** Dates instead of "5 weeks ago": starts from the list's choice (same browser setting). */
function listShowsDates(): boolean {
  try {
    return Boolean(JSON.parse(localStorage.getItem('hiddify.users.prefs') || '{}').showDates)
  } catch {
    return false
  }
}
const showDates = ref(listShowsDates())

// ---- Routing
const outboundOptions = computed(() => [
  { id: null as number | null, name: t('users.form.outboundAuto'), mode: '', enabled: true },
  ...(props.state?.outbounds ?? []),
])

// ---- Owner (sub-admin tree, indented)
const ownerOptions = computed(() => {
  const admins = props.state?.admins ?? []
  const depth = (uuid: string | null, seen = new Set<string>()): number => {
    const a = admins.find((x) => x.uuid === uuid)
    if (!a?.parent_uuid || seen.has(a.uuid)) return 0
    seen.add(a.uuid)
    return 1 + depth(a.parent_uuid, seen)
  }
  return admins.map((a) => ({ value: a.uuid, label: `${'  '.repeat(depth(a.uuid))}${a.uuid === props.state?.me_uuid ? t('users.form.ownerMe', { name: a.name }) : a.name}` }))
})

// ---- Additional configs
const configsInvalid = computed(() => canAddSublinks.value && configs.value.some((c) => configRowProblem(c)))

/** What is set inside the closed Advanced section, so nothing hides there unnoticed. */
const advancedSummary = computed(() => {
  const parts: string[] = []
  const ob = props.state?.outbounds.find((o) => o.id === preferredOutbound.value)
  if (ob) parts.push(t('users.form.summaryOutbound', { name: ob.name }))
  if (configs.value.length) parts.push(t('users.form.summaryConfigs', { n: configs.value.length }, configs.value.length))
  if (extraText.value.trim() && extraText.value.trim() !== '{}') parts.push(t('users.form.summaryExtra'))
  return parts.join(' · ')
})

// ---- Validation
const nameError = computed(() => touched.value && !name.value.trim())
const uuidError = computed(() => !UUID_RE.test(uuid.value.trim()))
const extraError = computed(() => {
  const text = extraText.value.trim()
  if (!text) return null
  try {
    const parsed = JSON.parse(text)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? null : t('users.form.extraNotObject')
  } catch {
    return t('users.form.extraInvalid')
  }
})

async function submit() {
  touched.value = true
  const extraBad = canModifyUserExtra.value && !!extraError.value
  if (busy.value) return
  if (!name.value.trim() || uuidError.value || extraBad || configsInvalid.value) {
    if (uuidError.value || extraBad || configsInvalid.value) showAdvanced.value = true
    void scrollToFirstInvalid(formEl.value, '.uf-error')
    return
  }
  busy.value = true
  error.value = null
  const payload: UserPayload = {
    name: name.value.trim(),
    comment: comment.value.trim(),
    enable: enable.value,
    usage_limit_GB: usageLimit.value ?? 0,
    package_days: packageDays.value ?? 0,
    mode: mode.value,
    owner_uuid: ownerUuid.value ?? undefined,
    telegram_id: telegramId.value,
    uuid: uuid.value.trim().toLowerCase(),
  }
  if (canOverrideOutbound.value) payload.preferred_outbound = preferredOutbound.value
  if (canAddSublinks.value) payload.additional_configs = cleanConfigRows(configs.value)
  if (canModifyUserExtra.value) payload.extra_params = extraText.value.trim() || '{}'
  if (resetUsage.value) payload.reset_usage = true
  if (resetDays.value) payload.reset_days = true
  try {
    const saved = props.user ? await usersApi.update(props.user.uuid, payload) : await usersApi.create(payload)
    if (await saveFormTags('user', saved.uuid, tagIds.value, initialTags.value)) saved.tags = [...tagIds.value]
    else toast.add({ severity: 'warn', summary: t('tags.saveFailed'), life: 5000 })
    emit('saved', saved, !props.user, !props.user && addAtEnd.value)
    visible.value = false
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="!busy"
    :style="{ width: 'min(48rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <template #header>
      <div class="uf-title">
        <span class="uf-title__icon"><i class="pi" :class="editing ? 'pi-user-edit' : 'pi-user-plus'" /></span>
        <div class="min-w-0">
          <div class="font-semibold text-lg uf-title__text">{{ focus === 'usage' ? t('users.form.editUsageTitle', { name: user?.name }) : focus === 'time' ? t('users.form.editTimeTitle', { name: user?.name }) : editing ? t('users.form.editTitle', { name: user?.name }) : t('users.form.addTitle') }}</div>
          <div v-if="!focus" class="text-muted-color text-sm">{{ editing ? t('users.form.editSubtitle') : t('users.form.addSubtitle') }}</div>
        </div>
        <!-- Can the user connect? -->
        <label v-if="!focus" class="uf-enable" :class="{ 'uf-enable--off': !enable }" for="uf-enable" v-tooltip.bottom="t('users.form.enableHint')">
          <span>{{ enable ? t('users.form.enabled') : t('users.form.disabled') }}</span>
          <ToggleSwitch v-model="enable" input-id="uf-enable" :disabled="busy || loading" />
        </label>
      </div>
    </template>

    <div v-if="loading" class="flex flex-col gap-3">
      <Skeleton v-for="i in 4" :key="i" height="4.5rem" border-radius="12px" />
    </div>

    <form v-else ref="formEl" class="uf" @submit.prevent="submit">
      <!-- Who -->
      <FormSection v-if="!focus" icon="pi pi-user" :title="t('users.form.who')">
        <div class="uf-grid">
          <!-- Name and Tag side by side -->
          <div class="uf-namerow uf-field--wide">
            <div class="uf-field uf-namerow__name">
              <label for="uf-name" class="font-medium">{{ t('users.form.name') }}</label>
              <InputText id="uf-name" v-model="name" maxlength="512" autofocus :invalid="nameError" :disabled="busy" :placeholder="t('users.form.namePlaceholder')" />
              <small v-if="nameError" class="uf-error">{{ t('users.form.nameRequired') }}</small>
            </div>
            <div class="uf-field uf-namerow__tag">
              <label id="uf-tag-label" class="font-medium">{{ t('tags.addTag') }}</label>
              <TagSelect v-model="tagIds" :disabled="busy" aria-labelledby="uf-tag-label" />
            </div>
          </div>
          <div class="uf-field uf-field--wide">
            <label for="uf-note" class="font-medium">{{ t('users.form.note') }} <span class="text-muted-color font-normal">({{ t('users.form.optional') }})</span></label>
            <Textarea id="uf-note" v-model="comment" rows="2" auto-resize maxlength="512" :disabled="busy" :placeholder="t('users.form.notePlaceholder')" />
          </div>
        </div>
      </FormSection>

      <!-- Data -->
      <FormSection v-if="!focus || focus === 'usage'" icon="pi pi-database" :title="t('users.form.data')">
        <!-- Used (read only, can be reset) and the limit, in one row -->
        <div class="uf-data">
          <div v-if="editing" class="uf-used" :class="{ 'uf-used--reset': resetUsage }">
            <span class="uf-used__label">{{ t('users.form.used') }}</span>
            <b class="uf-used__value" dir="ltr">{{ sizeText(usedGb, locale) }}</b>
            <button
              type="button"
              class="uf-used__reset"
              :disabled="busy || (!resetUsage && !detail?.current_usage_GB)"
              v-tooltip.top="resetUsage ? t('users.form.resetUsagePending') : t('users.form.resetUsage')"
              :aria-label="resetUsage ? t('users.form.undo') : t('users.form.resetUsage')"
              @click="resetUsage = !resetUsage"
            >
              <i class="pi" :class="resetUsage ? 'pi-undo' : 'pi-refresh'" />
              <span>{{ resetUsage ? t('users.form.undo') : t('users.form.reset') }}</span>
            </button>
          </div>
          <span v-if="editing" class="uf-data__of">{{ t('users.of') }}</span>
          <div class="uf-field uf-data__limit">
            <label for="uf-limit" class="uf-used__label">{{ t('users.form.limit') }}</label>
            <InputNumber v-model="usageLimit" input-id="uf-limit" :min="0" :max="UNLIMITED_GB" :max-fraction-digits="3" :suffix="` ${unitLabel('GB')}`" :disabled="busy" fluid />
          </div>
        </div>
        <small v-if="resetUsage" class="uf-pending"><i class="pi pi-clock" />{{ t('users.form.resetUsagePending') }}</small>
        <PresetChips v-model="usageLimit" kind="usage" :disabled="busy" />

        <ResetModePicker v-model="mode" :disabled="busy" :after="nextReset !== null ? t('users.form.nextReset', { when: relativeDays(nextReset, locale) }) : null" />
      </FormSection>

      <!-- Time: the same shape as Data (used days ↻ of package length) -->
      <FormSection v-if="!focus || focus === 'time'" icon="pi pi-calendar" :title="t('users.form.time')">
        <div class="uf-data">
          <div v-if="editing" class="uf-used" :class="{ 'uf-used--reset': resetDays }">
            <span class="uf-used__label">{{ t('users.form.used') }}</span>
            <b class="uf-used__value">{{ detail?.start_date ? t('users.form.daysCount', { n: Math.max(0, -daysFromToday(detail.start_date)) }) : t('users.form.notStarted') }}</b>
            <button
              type="button"
              class="uf-used__reset"
              :disabled="busy || (!resetDays && !detail?.start_date)"
              v-tooltip.top="resetDays ? t('users.form.undo') : t('users.form.resetDaysHint')"
              :aria-label="resetDays ? t('users.form.undo') : t('users.form.restart')"
              @click="resetDays = !resetDays"
            >
              <i class="pi" :class="resetDays ? 'pi-undo' : 'pi-replay'" />
              <span>{{ resetDays ? t('users.form.undo') : t('users.form.reset') }}</span>
            </button>
          </div>
          <span v-if="editing" class="uf-data__of">{{ t('users.of') }}</span>
          <div class="uf-field uf-data__limit">
            <label for="uf-days" class="uf-used__label">{{ t('users.form.packageLength') }}</label>
            <!-- Unlimited: a clear state instead of "10,000 days" -->
            <div v-if="unlimitedTime" class="uf-infinite">
              <span class="uf-infinite__sign">∞</span>
              <span class="flex-1">{{ t('users.form.unlimited') }}</span>
              <Button type="button" size="small" text :label="t('users.form.setDays')" :disabled="busy" @click="packageDays = 30" />
            </div>
            <InputNumber v-else v-model="packageDays" input-id="uf-days" :min="0" :max="UNLIMITED_DAYS - 1" :suffix="` ${t('users.form.daysUnit')}`" :disabled="busy" fluid />
          </div>
        </div>
        <PresetChips v-model="packageDays" kind="days" :disabled="busy" />
        <!-- One short line: relative by default, dates on request -->
        <PackageTimeLine :state="timeState">
          <template v-if="timeState === 'pending'">{{ t('users.form.restartPending') }}</template>
          <template v-else-if="timeState === 'waiting'">{{ unlimitedTime ? t('users.form.waitingUnlimited') : t('users.form.waitingText', { n: packageDays ?? 0 }) }}</template>
          <template v-else>
            {{ t('users.form.startedWhen', { when: showDates ? shortDate(started, locale) : relativeDays(-(startedDays ?? 0), locale) }) }}
            ·
            <b v-if="unlimitedTime">{{ t('users.form.neverExpires') }}</b>
            <b v-else :class="{ 'ptl__late': remaining < 0 }">{{ t(remaining < 0 ? 'users.form.endedWhen' : 'users.form.endsWhen', { when: showDates ? shortDate(expireDate, locale) : relativeDays(remaining, locale) }) }}</b>
          </template>
          <template #action>
            <Button
              v-if="timeState === 'running' || timeState === 'ended'"
              type="button"
              icon="pi pi-calendar"
              size="small"
              text
              rounded
              class="uf-when__dates"
              :severity="showDates ? undefined : 'secondary'"
              :aria-pressed="showDates"
              :aria-label="showDates ? t('users.showRelative') : t('users.showDates')"
              v-tooltip.top="showDates ? t('users.showRelative') : t('users.showDates')"
              @click="showDates = !showDates"
            />
          </template>
        </PackageTimeLine>
      </FormSection>

      <!-- Advanced -->
      <FormSection v-if="!focus" v-model:open="showAdvanced" icon="pi pi-sliders-h" :title="t('users.form.advanced')" collapsible :summary="advancedSummary">
        <div class="uf-grid">
          <div class="uf-field--wide uf-adv-blocks">
          <!-- Routing -->
          <section v-if="(state?.outbounds.length ?? 0) > 0" class="uf-sub">
            <h5 class="uf-sub__title"><i class="pi pi-directions" />{{ t('users.form.routing') }}</h5>
            <div class="uf-field">
              <label for="uf-outbound" class="font-medium">{{ t('users.form.outbound') }}</label>
              <Select v-model="preferredOutbound" :options="outboundOptions" option-label="name" option-value="id" input-id="uf-outbound" :disabled="busy || !canOverrideOutbound" class="w-full">
                <template #option="{ option }">
                  <span class="uf-opt" :class="{ 'uf-opt--off': !option.enabled }">
                    {{ option.name }}
                    <small v-if="option.mode" class="text-muted-color">{{ t(`outbounds.mode.${option.mode}`) }}</small>
                    <small v-if="!option.enabled" class="text-muted-color">· {{ t('users.form.outboundOff') }}</small>
                  </span>
                </template>
              </Select>
              <small class="text-muted-color">{{ canOverrideOutbound ? t('users.form.outboundHint') : t('users.form.outboundReadOnly') }}</small>
            </div>
          </section>

          <!-- Additional configs -->
          <section v-if="canAddSublinks || configs.length || (detail?.inherited_configs ?? 0) > 0" class="uf-sub">
            <h5 class="uf-sub__title"><i class="pi pi-paperclip" />{{ t('users.configs.title') }}<span v-if="configs.length" class="uf-count">{{ configs.length }}</span></h5>
            <p class="uf-hint">{{ t('users.configs.hint') }}</p>
            <AdditionalConfigsEditor v-model="configs" :disabled="busy || !canAddSublinks" :show-errors="touched" :inherited="detail?.inherited_configs" />
          </section>
          </div>
          <div class="uf-field uf-field--wide">
            <label for="uf-uuid" class="font-medium">UUID</label>
            <div class="flex gap-2">
              <InputText id="uf-uuid" v-model="uuid" dir="ltr" class="flex-1 min-w-0 font-mono text-sm" :invalid="uuidError" :disabled="busy" spellcheck="false" />
              <Button type="button" icon="pi pi-refresh" severity="secondary" outlined :aria-label="t('users.form.newUuid')" v-tooltip.top="t('users.form.newUuid')" :disabled="busy" @click="uuid = randomUuid()" />
            </div>
            <small :class="uuidError ? 'uf-error' : 'text-muted-color'">{{ uuidError ? t('users.form.uuidInvalid') : editing ? t('users.form.uuidEditHint') : t('users.form.uuidHint') }}</small>
          </div>
          <div class="uf-field">
            <label for="uf-owner" class="font-medium">{{ t('users.form.owner') }}</label>
            <Select v-model="ownerUuid" :options="ownerOptions" option-label="label" option-value="value" input-id="uf-owner" :disabled="busy" filter class="w-full" />
          </div>
          <div class="uf-field">
            <label for="uf-tg" class="font-medium">{{ t('users.form.telegram') }} <span class="text-muted-color font-normal">({{ t('users.form.optional') }})</span></label>
            <InputNumber v-model="telegramId" input-id="uf-tg" :use-grouping="false" :min="0" :disabled="busy" fluid />
          </div>
          <div v-if="canModifyUserExtra" class="uf-field uf-field--wide">
            <span class="font-medium">{{ t('users.form.extra') }}</span>
            <Json5Editor v-model="extraText" height="140px" />
            <small :class="extraError ? 'uf-error' : 'text-muted-color'">{{ extraError ?? t('users.form.extraHint') }}</small>
          </div>
        </div>
      </FormSection>

      <FormError :error="error" :title="t('common.saveFailed')" />

      <div class="uf-actions">
        <Button type="button" :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="visible = false" />
        <Button v-if="editing" type="submit" icon="pi pi-check" :label="t('common.save')" :loading="busy" />
        <!-- Add: on top of the users list; the menu adds it at the end instead. The button stays the form's submit (Enter). -->
        <SplitButton
          v-else
          :label="t('users.form.add')"
          :icon="busy ? 'pi pi-spin pi-spinner' : 'pi pi-user-plus'"
          :model="addMenu"
          :disabled="busy"
          :button-props="{ type: 'submit' }"
          :menu-button-props="{ 'aria-label': t('users.form.addAtEnd') }"
          @click="addAtEnd = false"
        />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.uf-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  flex: 1;
}
.uf-title__icon {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 1.1rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.uf-title__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uf {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.uf-count {
  padding: 0 0.45rem;
  border-radius: 999px;
  font-size: 0.7rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.uf-hint {
  margin: -0.4rem 0 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.uf-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
  align-items: start;
}
.uf-namerow {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}
.uf-namerow__name {
  flex: 1;
  min-width: 0;
}
.uf-namerow__tag {
  flex: none;
}
.uf-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}
.uf-field--wide {
  grid-column: 1 / -1;
}
.uf-error {
  color: var(--p-red-500, #ef4444);
}
.uf-enable {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-inline-start: auto;
  margin-inline-end: 0.5rem;
  padding: 0.25rem 0.35rem 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 10%, transparent);
  cursor: pointer;
}
.uf-enable--off {
  color: var(--p-text-muted-color);
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.1));
}
.uf-sub {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 0.85rem;
  border-radius: 12px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.05));
}
.uf-sub__title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
}
.uf-sub__title i {
  color: var(--p-primary-color);
}
.uf-adv-blocks {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Tones */
.uf-tone--ok {
  --tone: var(--p-green-500, #22c55e);
}
.uf-tone--warn {
  --tone: var(--p-amber-500, #f59e0b);
}
.uf-tone--danger {
  --tone: var(--p-red-500, #ef4444);
}
/* Used + limit in one row */
.uf-data {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1.3fr);
  align-items: end;
  gap: 0.6rem;
}
.uf-data:not(:has(.uf-used)) {
  grid-template-columns: 1fr;
}
.uf-data__of {
  padding-bottom: 0.7rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.uf-used {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  align-items: center;
  column-gap: 0.4rem;
  padding: 0.35rem 0.4rem 0.35rem 0.75rem;
  min-height: 2.6rem;
  border-radius: 10px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
}
.uf-used__label {
  grid-column: 1;
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.uf-data__limit .uf-used__label {
  margin-bottom: -0.15rem;
}
.uf-used__value {
  grid-column: 1;
  font-size: 0.95rem;
  white-space: nowrap;
  text-align: start;
}
.uf-used--reset .uf-used__value {
  text-decoration: line-through;
  color: var(--p-text-muted-color);
}
.uf-used__reset {
  grid-column: 2;
  grid-row: 1 / span 2;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  height: 1.9rem;
  padding: 0 0.7rem;
  border: 0;
  border-radius: 999px;
  color: var(--p-amber-700, #b45309);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 14%, transparent);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.uf-used__reset:not(:disabled):hover {
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 24%, transparent);
}
.uf-used__reset i {
  font-size: 0.75rem;
}
.uf-used--reset .uf-used__reset {
  color: var(--p-text-muted-color);
  background: var(--p-content-background);
}
.uf-used__reset:disabled {
  opacity: 0.4;
  cursor: default;
}
.uf-pending {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 600;
  color: var(--p-amber-700, #b45309);
}
.uf-infinite {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-height: 2.6rem;
  padding: 0.2rem 0.3rem 0.2rem 0.85rem;
  border-radius: 10px;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 35%, var(--p-content-border-color));
  background: color-mix(in srgb, var(--p-primary-color) 6%, transparent);
  font-weight: 600;
}
.uf-infinite__sign {
  font-size: 1.35rem;
  line-height: 1;
  color: var(--p-primary-color);
}
.uf-when__dates {
  flex-shrink: 0;
  width: 1.9rem !important;
  height: 1.9rem !important;
}
.uf-opt {
  display: inline-flex;
  align-items: baseline;
  gap: 0.4rem;
}
.uf-opt--off {
  opacity: 0.6;
}
.uf-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
}
.uf-actions {
  position: sticky;
  bottom: -1px;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 0 0.1rem;
  background: var(--p-dialog-background, var(--p-content-background));
}
/* Very narrow: used box above the limit, no "of" */
@media (max-width: 480px) {
  .uf-data {
    grid-template-columns: 1fr;
    gap: 0.45rem;
  }
  .uf-data__of {
    display: none;
  }
}
@media (max-width: 640px) {
  .uf-grid {
    grid-template-columns: 1fr;
  }
}
</style>
