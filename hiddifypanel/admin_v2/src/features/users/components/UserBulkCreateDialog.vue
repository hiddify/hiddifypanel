<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import TagSelect from '@/features/tags/components/TagSelect.vue'
import FormSection from '@/features/users/components/package/FormSection.vue'
import PackageTimeLine from '@/features/users/components/package/PackageTimeLine.vue'
import PresetChips from '@/features/users/components/package/PresetChips.vue'
import ResetModePicker from '@/features/users/components/package/ResetModePicker.vue'
import { useTags } from '@/features/tags/useTags'
import { apiErrorMessage } from '@/core/api/client'
import FormError from '@/shared/components/FormError.vue'
import { scrollToFirstInvalid } from '@/shared/utils/scroll-to-invalid'
import { unitLabel } from '@/shared/utils/format-metrics'
import {
  MAX_BULK_CREATE,
  UNLIMITED_DAYS,
  UNLIMITED_GB,
  userLinkPath,
  usersApi,
  type UserDetail,
  type UserMode,
  type UserPayload,
  type UsersState,
} from '@/features/users/api'

const COUNT_PRESETS = [5, 10, 20, 50, 100]

const props = defineProps<{ state: UsersState | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ created: [users: UserDetail[]] }>()
const { load: loadTags } = useTags()

const { t } = useI18n()
const toast = useToast()

type Step = 'form' | 'done'

const step = ref<Step>('form')
const busy = ref(false)
const error = ref<string | null>(null)
const touched = ref(false)
const formEl = ref<HTMLFormElement | null>(null)

const prefix = ref('')
const count = ref<number | null>(10)
const comment = ref('')
const enable = ref(true)
const usageLimit = ref<number | null>(100)
const packageDays = ref<number | null>(30)
const mode = ref<UserMode>('no_reset')
const ownerUuid = ref<string | null>(null)
const preferredOutbound = ref<number | null>(null)
const tagIds = ref<number[]>([])
/** Closed like on the single-user form; a line says what is set inside. */
const showAdvanced = ref(false)
const unlimitedTime = computed(() => (packageDays.value ?? 0) >= UNLIMITED_DAYS)

const created = ref<UserDetail[]>([])
/** A big batch: the servers get the users after the response, for a minute or two. */
const activating = ref(false)
const domain = ref('')
const linksText = ref('')
const copied = ref(false)
let copiedTimer: number | undefined

const canOverrideOutbound = computed(() => Boolean(props.state?.capabilities?.override_preferred_outbound))
const nameError = computed(() => touched.value && !prefix.value.trim())
/** The server refused the count (e.g. an older panel with a lower maximum): the field shows it too, until it changes. */
const countRefused = ref(false)
watch(count, () => (countRefused.value = false))
const countInvalid = computed(() => {
  const n = count.value
  return touched.value && (n == null || n < 1 || n > MAX_BULK_CREATE)
})
const countError = computed(() => countRefused.value || countInvalid.value)
const previewNames = computed(() => {
  const p = prefix.value.trim() || t('users.bulkCreate.prefixPlaceholder')
  const n = Math.min(Math.max(count.value || 0, 0), MAX_BULK_CREATE)
  if (n <= 0) return []
  if (n === 1) return [p]
  const width = String(n).length
  const sample = Math.min(n, 3)
  const names = Array.from({ length: sample }, (_, i) => `${p}-${String(i + 1).padStart(width, '0')}`)
  if (n > sample) names.push('…', `${p}-${String(n).padStart(width, '0')}`)
  return names
})

const outboundOptions = computed(() => [
  { id: null as number | null, name: t('users.form.outboundAuto'), mode: '', enabled: true },
  ...(props.state?.outbounds ?? []),
])
const ownerOptions = computed(() => {
  const admins = props.state?.admins ?? []
  const depth = (uuid: string, seen = new Set<string>()): number => {
    if (seen.has(uuid)) return 0
    seen.add(uuid)
    const a = admins.find((x) => x.uuid === uuid)
    return a?.parent_uuid ? 1 + depth(a.parent_uuid, seen) : 0
  }
  return admins.map((a) => ({
    value: a.uuid,
    label: `${'  '.repeat(depth(a.uuid))}${a.uuid === props.state?.me_uuid ? t('users.form.ownerMe', { name: a.name }) : a.name}`,
  }))
})
const domains = computed(() => props.state?.link_domains ?? [])
/** What is set inside the closed Advanced section, so nothing hides there unnoticed. */
const advancedSummary = computed(() => {
  const parts: string[] = []
  if (ownerUuid.value && ownerUuid.value !== props.state?.me_uuid) {
    const owner = props.state?.admins.find((a) => a.uuid === ownerUuid.value)
    if (owner) parts.push(`${t('users.form.owner')}: ${owner.name}`)
  }
  const ob = props.state?.outbounds.find((o) => o.id === preferredOutbound.value)
  if (ob) parts.push(t('users.form.summaryOutbound', { name: ob.name }))
  return parts.join(' · ')
})
const selectedDomain = computed(() => domains.value.find((d) => d.domain === domain.value) ?? domains.value[0] ?? null)

function rebuildLinks() {
  const base = selectedDomain.value?.base ?? ''
  linksText.value = created.value.map((u) => `${base}${userLinkPath(u)}`).join('\n')
}

watch(visible, (open) => {
  if (!open) return
  step.value = 'form'
  busy.value = false
  error.value = null
  touched.value = false
  copied.value = false
  prefix.value = ''
  count.value = 10
  comment.value = ''
  enable.value = true
  usageLimit.value = 100
  packageDays.value = 30
  mode.value = 'no_reset'
  ownerUuid.value = props.state?.me_uuid ?? null
  preferredOutbound.value = null
  tagIds.value = []
  showAdvanced.value = false
  created.value = []
  activating.value = false
  linksText.value = ''
  domain.value = domains.value[0]?.domain ?? ''
})

watch(domain, () => {
  if (step.value === 'done') rebuildLinks()
})

async function submit() {
  touched.value = true
  if (busy.value) return
  if (!prefix.value.trim() || countInvalid.value) {
    void scrollToFirstInvalid(formEl.value, '.ubc-error')
    return
  }
  countRefused.value = false
  busy.value = true
  error.value = null
  const payload: UserPayload & { count: number; tag_ids?: number[] } = {
    name: prefix.value.trim(),
    count: count.value!,
    comment: comment.value.trim(),
    enable: enable.value,
    usage_limit_GB: usageLimit.value ?? 0,
    package_days: packageDays.value ?? 0,
    mode: mode.value,
    owner_uuid: ownerUuid.value ?? undefined,
  }
  if (canOverrideOutbound.value) payload.preferred_outbound = preferredOutbound.value
  // The tags go with the users, in the same request (not one request per user)
  if (tagIds.value.length) payload.tag_ids = [...tagIds.value]
  try {
    const res = await usersApi.bulkCreate(payload)
    created.value = res.users
    activating.value = Boolean(res.activating)
    if (tagIds.value.length) void loadTags(true)
    rebuildLinks()
    step.value = 'done'
    emit('created', res.users)
    toast.add({ severity: 'success', summary: t('users.bulkCreate.done', { n: res.count }, res.count), life: 4000 })
  } catch (err) {
    error.value = apiErrorMessage(err) || t('users.bulkCreate.failed')
    countRefused.value = /\bcount\b/i.test(error.value)
  } finally {
    busy.value = false
  }
}

async function copyLinks() {
  await navigator.clipboard.writeText(linksText.value)
  copied.value = true
  window.clearTimeout(copiedTimer)
  copiedTimer = window.setTimeout(() => (copied.value = false), 2000)
}

function downloadTxt() {
  const blob = new Blob([linksText.value + (linksText.value.endsWith('\n') ? '' : '\n')], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${(prefix.value.trim() || 'users').replace(/[^\p{L}\p{N}_-]+/gu, '-')}.txt`
  a.click()
  URL.revokeObjectURL(url)
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
      <div class="ubc-title">
        <span class="ubc-title__icon"><i class="pi" :class="step === 'done' ? 'pi-link' : 'pi-users'" /></span>
        <div class="min-w-0">
          <div class="font-semibold text-lg">{{ step === 'done' ? t('users.bulkCreate.linksTitle') : t('users.bulkCreate.title') }}</div>
          <div class="text-muted-color text-sm">{{ step === 'done' ? t('users.bulkCreate.linksSubtitle', { n: created.length }, created.length) : t('users.bulkCreate.subtitle') }}</div>
        </div>
        <label v-if="step === 'form'" class="ubc-enable" :class="{ 'ubc-enable--off': !enable }" for="ubc-enable" v-tooltip.bottom="t('users.form.enableHint')">
          <span>{{ enable ? t('users.form.enabled') : t('users.form.disabled') }}</span>
          <ToggleSwitch v-model="enable" input-id="ubc-enable" :disabled="busy" />
        </label>
      </div>
    </template>

    <form v-if="step === 'form'" ref="formEl" class="ubc" @submit.prevent="submit">
      <FormSection icon="pi pi-user" :title="t('users.bulkCreate.who')">
        <div class="ubc-grid">
          <div class="ubc-field ubc-field--wide">
            <label for="ubc-prefix" class="font-medium">{{ t('users.bulkCreate.prefix') }}</label>
            <InputText id="ubc-prefix" v-model="prefix" maxlength="480" autofocus :invalid="nameError" :disabled="busy" :placeholder="t('users.bulkCreate.prefixPlaceholder')" />
            <small :class="nameError ? 'ubc-error' : 'text-muted-color'">{{ nameError ? t('users.form.nameRequired') : t('users.bulkCreate.prefixHint') }}</small>
          </div>
          <div class="ubc-field">
            <label for="ubc-count" class="font-medium">{{ t('users.bulkCreate.count') }}</label>
            <InputNumber v-model="count" input-id="ubc-count" :min="1" :max="MAX_BULK_CREATE" :invalid="countError" :disabled="busy" show-buttons fluid />
            <small :class="countError ? 'ubc-error' : 'text-muted-color'">{{ t('users.bulkCreate.countHint', { max: MAX_BULK_CREATE }) }}</small>
          </div>
          <div class="ubc-field">
            <label id="ubc-tag-label" class="font-medium">{{ t('tags.addTag') }}</label>
            <TagSelect v-model="tagIds" :disabled="busy" aria-labelledby="ubc-tag-label" />
          </div>
          <div class="ubc-chips ubc-field--wide">
            <button v-for="n in COUNT_PRESETS" :key="n" type="button" class="ubc-chip" :class="{ 'ubc-chip--on': count === n }" :disabled="busy" @click="count = n">× {{ n }}</button>
          </div>
          <div v-if="previewNames.length" class="ubc-preview ubc-field--wide">
            <span class="ubc-preview__label">{{ t('users.bulkCreate.preview') }}</span>
            <span v-for="(name, i) in previewNames" :key="i" class="ubc-preview__name" dir="auto">{{ name }}</span>
          </div>
          <div class="ubc-field ubc-field--wide">
            <label for="ubc-note" class="font-medium">{{ t('users.form.note') }} <span class="text-muted-color font-normal">({{ t('users.form.optional') }})</span></label>
            <Textarea id="ubc-note" v-model="comment" rows="2" auto-resize maxlength="512" :disabled="busy" :placeholder="t('users.form.notePlaceholder')" />
          </div>
        </div>
      </FormSection>

      <FormSection icon="pi pi-database" :title="t('users.form.data')">
        <div class="ubc-field">
          <label for="ubc-limit" class="ubc-label">{{ t('users.form.limit') }}</label>
          <InputNumber v-model="usageLimit" input-id="ubc-limit" :min="0" :max="UNLIMITED_GB" :max-fraction-digits="3" :suffix="` ${unitLabel('GB')}`" :disabled="busy" fluid />
        </div>
        <PresetChips v-model="usageLimit" kind="usage" :disabled="busy" />
        <ResetModePicker v-model="mode" :disabled="busy" />
      </FormSection>

      <FormSection icon="pi pi-calendar" :title="t('users.form.time')">
        <div class="ubc-field">
          <label for="ubc-days" class="ubc-label">{{ t('users.form.packageLength') }}</label>
          <InputNumber v-model="packageDays" input-id="ubc-days" :min="0" :max="UNLIMITED_DAYS" :suffix="` ${t('users.form.daysUnit')}`" :disabled="busy" fluid />
        </div>
        <PresetChips v-model="packageDays" kind="days" :disabled="busy" />
        <!-- New users: the package starts at each one's first connection -->
        <PackageTimeLine state="waiting">{{ unlimitedTime ? t('users.form.waitingUnlimited') : t('users.form.waitingText', { n: packageDays ?? 0 }) }}</PackageTimeLine>
      </FormSection>

      <FormSection
        v-if="(state?.admins.length ?? 0) > 1 || (canOverrideOutbound && (state?.outbounds.length ?? 0) > 0)"
        v-model:open="showAdvanced"
        icon="pi pi-sliders-h"
        :title="t('users.form.advanced')"
        collapsible
        :summary="advancedSummary"
      >
        <div class="ubc-grid">
          <div v-if="(state?.admins.length ?? 0) > 1" class="ubc-field">
            <label for="ubc-owner" class="font-medium">{{ t('users.form.owner') }}</label>
            <Select v-model="ownerUuid" :options="ownerOptions" option-label="label" option-value="value" input-id="ubc-owner" :disabled="busy" filter class="w-full" />
          </div>
          <div v-if="canOverrideOutbound && (state?.outbounds.length ?? 0) > 0" class="ubc-field">
            <label for="ubc-outbound" class="font-medium">{{ t('users.form.outbound') }}</label>
            <Select v-model="preferredOutbound" :options="outboundOptions" option-label="name" option-value="id" input-id="ubc-outbound" :disabled="busy" class="w-full" />
          </div>
        </div>
      </FormSection>

      <FormError :error="error" :title="t('users.bulkCreate.failed')" />

      <div class="ubc-actions">
        <Button type="button" :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="visible = false" />
        <Button type="submit" icon="pi pi-users" :label="t('users.bulkCreate.create', { n: count || 0 }, count || 0)" :loading="busy" :disabled="countInvalid" />
      </div>
    </form>

    <div v-else class="ubc ubc--done">
      <Message v-if="activating" severity="info" :closable="false" icon="pi pi-clock">{{ t('users.bulkCreate.activating') }}</Message>
      <div v-if="domains.length > 1" class="ubc-field">
        <label for="ubc-domain" class="font-medium">{{ t('users.bulkCreate.domain') }}</label>
        <Select
          v-model="domain"
          input-id="ubc-domain"
          :options="domains"
          option-label="label"
          option-value="domain"
          class="w-full"
        />
      </div>
      <div class="ubc-field">
        <label for="ubc-links" class="font-medium">{{ t('users.bulkCreate.links') }}</label>
        <Textarea id="ubc-links" v-model="linksText" rows="12" class="ubc-links" dir="ltr" spellcheck="false" readonly />
      </div>
      <div class="ubc-actions">
        <Button type="button" icon="pi pi-download" :label="t('users.bulkCreate.download')" severity="secondary" outlined @click="downloadTxt" />
        <Button type="button" :icon="copied ? 'pi pi-check' : 'pi pi-copy'" :label="copied ? t('common.copied') : t('users.bulkCreate.copy')" @click="copyLinks" />
        <Button type="button" :label="t('common.done')" severity="secondary" text @click="visible = false" />
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.ubc-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  width: 100%;
}
.ubc-title__icon {
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
.ubc-enable {
  margin-inline-start: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 12%, transparent);
  color: var(--p-green-600, #16a34a);
  cursor: pointer;
}
.ubc-enable--off {
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 12%, transparent);
  color: var(--p-red-600, #dc2626);
}
.ubc {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
/* Field labels inside a card, as on the single-user form */
.ubc-label {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.ubc-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem 1rem;
}
.ubc-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}
.ubc-field--wide {
  grid-column: 1 / -1;
}
.ubc-error {
  color: var(--p-red-500, #ef4444);
}
.ubc-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.ubc-chip {
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  border: 1px solid var(--p-content-border-color);
  background: transparent;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}
.ubc-chip--on {
  border-color: color-mix(in srgb, var(--p-primary-color) 40%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
}
.ubc-preview {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  padding: 0.65rem 0.8rem;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-primary-color) 6%, transparent);
}
.ubc-preview__label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--p-text-muted-color);
  margin-inline-end: 0.25rem;
}
.ubc-preview__name {
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.ubc-links {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.78rem;
  line-height: 1.45;
}
.ubc-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}
@media (max-width: 640px) {
  .ubc-grid {
    grid-template-columns: 1fr;
  }
  .ubc-title {
    flex-wrap: wrap;
  }
  .ubc-enable {
    width: 100%;
    justify-content: space-between;
  }
  .ubc-actions {
    flex-direction: column-reverse;
  }
  .ubc-actions :deep(.p-button) {
    width: 100%;
  }
}
</style>
