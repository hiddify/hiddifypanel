<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Skeleton from 'primevue/skeleton'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import Json5Editor from '@/shared/components/Json5Editor.vue'
import { apiErrorMessage } from '@/core/api/client'
import {
  CONFIG_TARGETS,
  MODE_ICON,
  UNLIMITED_DAYS,
  UNLIMITED_GB,
  USER_MODES,
  usersApi,
  type AdditionalConfig,
  type ConfigKind,
  type UserDetail,
  type UserMode,
  type UserPayload,
  type UserRow,
  type UsersState,
} from '@/features/users/api'
import { daysFromToday, gb, relativeDays, shortDate } from '@/features/users/format'

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
/** Quick picks; the last one is "unlimited" (the highest value the server keeps). */
const LIMIT_PRESETS = [10, 50, 100, 200, 500, 1000, UNLIMITED_GB]
const DAY_PRESETS = [
  { days: 7, key: 'week' },
  { days: 30, key: 'month' },
  { days: 90, key: 'months3' },
  { days: 180, key: 'months6' },
  { days: 365, key: 'year' },
  { days: UNLIMITED_DAYS, key: 'unlimited' },
] as const

/** `user`: the one being edited (its detail is loaded); null adds a new user. */
const props = defineProps<{ user: UserRow | null; state: UsersState | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ saved: [user: UserDetail, created: boolean] }>()

const { t, locale } = useI18n()

const detail = ref<UserDetail | null>(null)
const loading = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)
const touched = ref(false)
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
const configs = ref<AdditionalConfig[]>([])
const extraText = ref('{}')
const resetUsage = ref(false)
const resetDays = ref(false)

const editing = computed(() => props.user !== null)

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

const modeOptions = computed(() => USER_MODES.map((m) => ({ value: m, label: t(`users.mode.${m}`), icon: MODE_ICON[m] })))
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
const timeState = computed<'pending' | 'waiting' | 'running' | 'ended'>(() => {
  if (resetDays.value) return 'pending'
  if (!started.value) return 'waiting'
  return !unlimitedTime.value && remaining.value < 0 ? 'ended' : 'running'
})
const TIME_ICON = { pending: 'pi pi-replay', waiting: 'pi pi-hourglass', running: 'pi pi-calendar', ended: 'pi pi-calendar-times' } as const

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
const kindOptions = computed(() => (['offline', 'subscription'] as ConfigKind[]).map((k) => ({ value: k, label: t(`users.configs.kind.${k}`) })))
const targetOptions = computed(() => CONFIG_TARGETS.map((x) => ({ value: x, label: t(`users.configs.target.${x}`) })))
function addConfig(kind: ConfigKind) {
  configs.value.push([kind, 'auto', ''])
}
function removeConfig(i: number) {
  configs.value.splice(i, 1)
}
function configProblem(row: AdditionalConfig): string | null {
  if (!touched.value) return null
  if (!row[2].trim()) return t('users.configs.empty')
  if (row[0] === 'subscription' && !/^https?:\/\//i.test(row[2].trim())) return t('users.configs.badUrl')
  return null
}

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
  if (!name.value.trim() || uuidError.value || extraError.value || configs.value.some((c) => configProblem(c)) || busy.value) {
    if (uuidError.value || extraError.value || configs.value.some((c) => configProblem(c))) showAdvanced.value = true
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
    preferred_outbound: preferredOutbound.value,
    additional_configs: configs.value.map(([k, target, v]) => [k, target, v.trim()] as AdditionalConfig),
    extra_params: extraText.value.trim() || '{}',
    uuid: uuid.value.trim().toLowerCase(),
  }
  if (resetUsage.value) payload.reset_usage = true
  if (resetDays.value) payload.reset_days = true
  try {
    const saved = props.user ? await usersApi.update(props.user.uuid, payload) : await usersApi.create(payload)
    emit('saved', saved, !props.user)
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
          <div class="font-semibold text-lg uf-title__text">{{ editing ? t('users.form.editTitle', { name: user?.name }) : t('users.form.addTitle') }}</div>
          <div class="text-muted-color text-sm">{{ editing ? t('users.form.editSubtitle') : t('users.form.addSubtitle') }}</div>
        </div>
        <!-- Can the user connect? -->
        <label class="uf-enable" :class="{ 'uf-enable--off': !enable }" for="uf-enable" v-tooltip.bottom="t('users.form.enableHint')">
          <span>{{ enable ? t('users.form.enabled') : t('users.form.disabled') }}</span>
          <ToggleSwitch v-model="enable" input-id="uf-enable" :disabled="busy || loading" />
        </label>
      </div>
    </template>

    <div v-if="loading" class="flex flex-col gap-3">
      <Skeleton v-for="i in 4" :key="i" height="4.5rem" border-radius="12px" />
    </div>

    <form v-else class="uf" @submit.prevent="submit">
      <!-- Who -->
      <section class="uf-sec">
        <h4 class="uf-sec__title"><i class="pi pi-user" />{{ t('users.form.who') }}</h4>
        <div class="uf-grid">
          <div class="uf-field uf-field--wide">
            <label for="uf-name" class="font-medium">{{ t('users.form.name') }}</label>
            <InputText id="uf-name" v-model="name" maxlength="512" autofocus :invalid="nameError" :disabled="busy" :placeholder="t('users.form.namePlaceholder')" />
            <small v-if="nameError" class="uf-error">{{ t('users.form.nameRequired') }}</small>
          </div>
          <div class="uf-field uf-field--wide">
            <label for="uf-note" class="font-medium">{{ t('users.form.note') }} <span class="text-muted-color font-normal">({{ t('users.form.optional') }})</span></label>
            <Textarea id="uf-note" v-model="comment" rows="2" auto-resize maxlength="512" :disabled="busy" :placeholder="t('users.form.notePlaceholder')" />
          </div>
        </div>
      </section>

      <!-- Data -->
      <section class="uf-sec">
        <h4 class="uf-sec__title"><i class="pi pi-database" />{{ t('users.form.data') }}</h4>
        <!-- Used (read only, can be reset) and the limit, in one row -->
        <div class="uf-data">
          <div v-if="editing" class="uf-used" :class="{ 'uf-used--reset': resetUsage }">
            <span class="uf-used__label">{{ t('users.form.used') }}</span>
            <b class="uf-used__value" dir="ltr">{{ gb(usedGb, locale) }} GB</b>
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
            <InputNumber v-model="usageLimit" input-id="uf-limit" :min="0" :max="UNLIMITED_GB" :max-fraction-digits="3" suffix=" GB" :disabled="busy" fluid />
          </div>
        </div>
        <small v-if="resetUsage" class="uf-pending"><i class="pi pi-clock" />{{ t('users.form.resetUsagePending') }}</small>
        <div class="uf-chips">
          <button
            v-for="v in LIMIT_PRESETS"
            :key="v"
            type="button"
            class="uf-chip"
            :class="{ 'uf-chip--on': usageLimit === v, 'uf-chip--extra': v === 200 || v === 500 }"
            @click="usageLimit = v"
          >
            {{ v === UNLIMITED_GB ? '♾️' : v >= 1000 ? `${v / 1000} TB` : `${v} GB` }}
          </button>
        </div>

        <div class="uf-field">
          <span class="font-medium">{{ t('users.form.mode') }}</span>
          <div class="uf-modes" role="radiogroup" :aria-label="t('users.form.mode')">
            <button
              v-for="m in modeOptions"
              :key="m.value"
              type="button"
              role="radio"
              class="uf-mode"
              :class="{ 'uf-mode--on': mode === m.value }"
              :aria-checked="mode === m.value"
              :disabled="busy"
              @click="mode = m.value"
            >
              <i :class="m.icon" /><span>{{ m.label }}</span>
            </button>
          </div>
          <small class="text-muted-color">
            {{ t(`users.modeHint.${mode}`) }}
            <template v-if="nextReset !== null"> · {{ t('users.form.nextReset', { when: relativeDays(nextReset, locale) }) }}</template>
          </small>
        </div>
      </section>

      <!-- Time: the same shape as Data (used days ↻ of package length) -->
      <section class="uf-sec">
        <h4 class="uf-sec__title"><i class="pi pi-calendar" />{{ t('users.form.time') }}</h4>
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
        <div class="uf-chips">
          <button
            v-for="p in DAY_PRESETS"
            :key="p.days"
            type="button"
            class="uf-chip"
            :class="{ 'uf-chip--on': packageDays === p.days, 'uf-chip--extra': p.key === 'week' }"
            @click="packageDays = p.days"
          >
            {{ p.key === 'unlimited' ? '♾️' : t(`users.form.period.${p.key}`) }}
          </button>
        </div>
        <!-- One short line: relative by default, dates on request -->
        <div class="uf-when" :class="`uf-when--${timeState}`">
          <i :class="TIME_ICON[timeState]" />
          <span class="uf-when__text">
            <template v-if="timeState === 'pending'">{{ t('users.form.restartPending') }}</template>
            <template v-else-if="timeState === 'waiting'">{{ unlimitedTime ? t('users.form.waitingUnlimited') : t('users.form.waitingText', { n: packageDays ?? 0 }) }}</template>
            <template v-else>
              {{ t('users.form.startedWhen', { when: showDates ? shortDate(started, locale) : relativeDays(-(startedDays ?? 0), locale) }) }}
              ·
              <b v-if="unlimitedTime">{{ t('users.form.neverExpires') }}</b>
              <b v-else :class="{ 'uf-when__late': remaining < 0 }">{{ t(remaining < 0 ? 'users.form.endedWhen' : 'users.form.endsWhen', { when: showDates ? shortDate(expireDate, locale) : relativeDays(remaining, locale) }) }}</b>
            </template>
          </span>
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
        </div>
      </section>

      <!-- Advanced -->
      <section class="uf-sec">
        <button type="button" class="uf-toggle" :aria-expanded="showAdvanced" @click="showAdvanced = !showAdvanced">
          <i class="pi pi-sliders-h" />
          <span class="flex-1">{{ t('users.form.advanced') }}</span>
          <i class="pi pi-angle-down uf-toggle__caret" :class="{ 'uf-toggle__caret--open': showAdvanced }" />
        </button>
        <p v-if="!showAdvanced && advancedSummary" class="uf-adv-summary">{{ advancedSummary }}</p>
        <div v-if="showAdvanced" class="uf-grid">
          <div class="uf-field--wide uf-adv-blocks">
          <!-- Routing -->
          <section class="uf-sub">
            <h5 class="uf-sub__title"><i class="pi pi-directions" />{{ t('users.form.routing') }}</h5>
            <div class="uf-field">
              <label for="uf-outbound" class="font-medium">{{ t('users.form.outbound') }}</label>
              <Select v-model="preferredOutbound" :options="outboundOptions" option-label="name" option-value="id" input-id="uf-outbound" :disabled="busy" class="w-full">
                <template #option="{ option }">
                  <span class="uf-opt" :class="{ 'uf-opt--off': !option.enabled }">
                    {{ option.name }}
                    <small v-if="option.mode" class="text-muted-color">{{ t(`outbounds.mode.${option.mode}`) }}</small>
                    <small v-if="!option.enabled" class="text-muted-color">· {{ t('users.form.outboundOff') }}</small>
                  </span>
                </template>
              </Select>
              <small class="text-muted-color">{{ t('users.form.outboundHint') }}</small>
            </div>
          </section>

          <!-- Additional configs -->
          <section class="uf-sub">
            <h5 class="uf-sub__title"><i class="pi pi-clone" />{{ t('users.configs.title') }}<span v-if="configs.length" class="uf-count">{{ configs.length }}</span></h5>
            <p class="uf-hint">{{ t('users.configs.hint') }}</p>
            <TransitionGroup name="uf-row" tag="div" class="uf-configs">
              <div v-for="(row, i) in configs" :key="i" class="uf-config">
                <div class="uf-config__head">
                  <SelectButton v-model="row[0]" :options="kindOptions" option-label="label" option-value="value" :allow-empty="false" size="small" :disabled="busy" />
                  <Select v-model="row[1]" :options="targetOptions" option-label="label" option-value="value" size="small" :disabled="busy" class="uf-config__target" />
                  <Button type="button" icon="pi pi-trash" text rounded severity="danger" size="small" :aria-label="t('common.delete')" :disabled="busy" @click="removeConfig(i)" />
                </div>
                <InputText v-if="row[0] === 'subscription'" v-model="row[2]" dir="ltr" class="w-full font-mono text-sm" :placeholder="t('users.configs.urlPlaceholder')" :invalid="!!configProblem(row)" :disabled="busy" />
                <Textarea v-else v-model="row[2]" dir="ltr" rows="3" class="w-full uf-mono" :placeholder="t('users.configs.offlinePlaceholder')" :invalid="!!configProblem(row)" :disabled="busy" />
                <small v-if="configProblem(row)" class="uf-error">{{ configProblem(row) }}</small>
              </div>
            </TransitionGroup>
            <div class="flex flex-wrap gap-2">
              <Button type="button" icon="pi pi-link" :label="t('users.configs.addSubscription')" size="small" severity="secondary" outlined :disabled="busy" @click="addConfig('subscription')" />
              <Button type="button" icon="pi pi-file" :label="t('users.configs.addOffline')" size="small" severity="secondary" outlined :disabled="busy" @click="addConfig('offline')" />
            </div>
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
          <div class="uf-field uf-field--wide">
            <span class="font-medium">{{ t('users.form.extra') }}</span>
            <Json5Editor v-model="extraText" height="140px" />
            <small :class="extraError ? 'uf-error' : 'text-muted-color'">{{ extraError ?? t('users.form.extraHint') }}</small>
          </div>
        </div>
      </section>

      <Message v-if="error" severity="error" :closable="false"><span class="whitespace-pre-line">{{ error }}</span></Message>

      <div class="uf-actions">
        <Button type="button" :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="visible = false" />
        <Button type="submit" :icon="editing ? 'pi pi-check' : 'pi pi-user-plus'" :label="editing ? t('common.save') : t('users.form.add')" :loading="busy" />
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
.uf-sec {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem;
  border-radius: 14px;
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}
.uf-sec__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.uf-sec__title i {
  color: var(--p-primary-color);
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
.uf-adv-summary {
  margin: -0.35rem 0 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.uf-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.uf-chip {
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.78rem;
  cursor: pointer;
}
.uf-chip:hover,
.uf-chip--on {
  color: var(--p-primary-color);
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
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
/* Reset period: 4 equal buttons, 2×2 on phones */
.uf-modes {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.35rem;
  padding: 0.25rem;
  border-radius: 12px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
}
.uf-mode {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-width: 0;
  padding: 0.45rem 0.4rem;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.84rem;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    box-shadow 0.15s ease;
}
.uf-mode span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uf-mode i {
  font-size: 0.8rem;
}
.uf-mode--on {
  color: var(--p-primary-color);
  font-weight: 600;
  background: var(--p-content-background);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
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
.uf-when {
  --tone: var(--p-green-600, #16a34a);
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 1.9rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
}
.uf-when > i {
  font-size: 0.8rem;
  color: var(--tone);
}
.uf-when--waiting {
  --tone: var(--p-sky-500, #0ea5e9);
}
.uf-when--pending {
  --tone: var(--p-amber-600, #d97706);
  color: var(--tone);
  font-weight: 600;
}
.uf-when--ended {
  --tone: var(--p-red-500, #ef4444);
}
.uf-when__text {
  flex: 1;
  min-width: 0;
}
.uf-when__text b {
  color: var(--p-text-color);
}
.uf-when__text .uf-when__late {
  color: var(--p-red-500, #ef4444);
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
.uf-configs {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.uf-config {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.65rem;
  border-radius: 12px;
  border: 1px dashed var(--p-content-border-color);
}
.uf-config__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.uf-config__target {
  min-width: 9rem;
  flex: 1;
}
.uf-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
}
.uf-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0;
  border: 0;
  background: none;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: start;
  cursor: pointer;
}
.uf-toggle:hover {
  color: var(--p-primary-color);
}
.uf-toggle__caret {
  transition: transform 0.25s ease;
}
.uf-toggle__caret--open {
  transform: rotate(180deg);
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
.uf-row-enter-active,
.uf-row-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.uf-row-enter-from,
.uf-row-leave-to {
  opacity: 0;
  transform: translateY(-4px);
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
  /* Room is short: fewer quick picks, all on one line */
  .uf-chip--extra {
    display: none;
  }
  .uf-chips {
    flex-wrap: nowrap;
  }
  .uf-chip {
    flex: 1 1 0;
    min-width: 0;
    padding-inline: 0.3rem;
    text-align: center;
    white-space: nowrap;
  }
  .uf-modes {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .uf-sec {
    padding: 0.85rem;
  }

}
</style>
