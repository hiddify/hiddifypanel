<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import TreeSelect from 'primevue/treeselect'
import type { TreeNode } from 'primevue/treenode'
import { apiErrorMessage } from '@/core/api/client'
import AdditionalConfigsEditor from '@/shared/components/AdditionalConfigsEditor.vue'
import DefaultOutboundSelect from '@/features/admins/components/DefaultOutboundSelect.vue'
import { cleanConfigRows, configRowProblem, type AdditionalConfig } from '@/shared/utils/additional-configs'
import { unitLabel } from '@/shared/utils/format-metrics'
import { ALIAS_MIN, aliasProblem } from '@/shared/utils/password-strength'
import { adminsApi, type AdminCredentials, type AdminLimits, type AdminPayload, type AdminRow, type AdminsTree } from '@/features/admins/api'

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const DEFAULT_LIMIT = 100

/** `admin`: the one being edited; null creates a new agent. */
const props = defineProps<{ admin: AdminRow | null; tree: AdminsTree | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{
  created: [name: string, credentials: AdminCredentials]
  saved: [name: string]
  resetPassword: [admin: AdminRow]
}>()

const { t } = useI18n()

const name = ref('')
const alias = ref('')
const aliasError = computed(() => {
  const problem = aliasProblem(alias.value)
  return problem ? t(`account.aliasProblem.${problem}`, { n: ALIAS_MIN }) : null
})
const comment = ref('')
const uuid = ref('')
const canAddAdmin = ref(false)
const parent = ref<Record<string, boolean>>({})
const limits = ref<{ max_users: number | null; max_active_users: number | null; max_online_users: number | null; max_total_usage_GB: number | null }>({
  max_users: DEFAULT_LIMIT,
  max_active_users: DEFAULT_LIMIT,
  max_online_users: null,
  max_total_usage_GB: null,
})
const showAdvanced = ref(false)
const touched = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)

const editing = computed(() => props.admin !== null)
const targetIsSuper = computed(() => props.admin?.mode === 'super_admin')
/** The signed-in admin's own limits cap what it can give (null: super admin, no cap). */
const myLimits = computed<AdminLimits | null>(() => props.tree?.my_limits ?? null)
const canGrantSubAdmins = computed(() => props.tree?.can_create ?? false)

function randomUuid(): string {
  // Non-secure contexts (plain http) have no randomUUID.
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6]! & 0x0f) | 0x40
  bytes[8] = (bytes[8]! & 0x3f) | 0x80
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

/** Admins that can hold sub-admins, as a tree; the edited admin and its branch are left out (no cycles). */
const parentOptions = computed<TreeNode[]>(() => {
  const rows = props.tree?.admins ?? []
  const excluded = new Set<string>()
  if (props.admin) {
    const stack = [props.admin.uuid]
    while (stack.length) {
      const id = stack.pop()!
      excluded.add(id)
      rows.filter((row) => row.parent_uuid === id).forEach((row) => stack.push(row.uuid))
    }
  }
  const build = (parentUuid: string | null): TreeNode[] =>
    rows
      .filter((row) => row.parent_uuid === parentUuid && !excluded.has(row.uuid))
      .map((row) => {
        const children = build(row.uuid)
        const eligible = row.is_me || row.mode === 'super_admin' || row.can_add_admin
        return {
          key: row.uuid,
          label: row.is_me ? `${row.name} (${t('admins.you')})` : row.name,
          icon: row.mode === 'super_admin' ? 'pi pi-crown' : 'pi pi-user',
          selectable: eligible,
          styleClass: eligible ? undefined : 'admin-form__node--muted',
          children,
        }
      })
      // Keep ineligible admins only as a path to eligible ones below them.
      .filter((node) => node.selectable || (node.children?.length ?? 0) > 0)
  return build(null)
})

const parentName = computed(() => {
  const key = Object.keys(parent.value)[0]
  const row = props.tree?.admins.find((a) => a.uuid === key)
  return row ? (row.is_me ? t('admins.you') : row.name) : ''
})

const expandedParents = computed(() => Object.fromEntries((props.tree?.admins ?? []).map((row) => [row.uuid, true])))

watch(visible, (open) => {
  if (!open) return
  const admin = props.admin
  touched.value = false
  busy.value = false
  error.value = null
  showAdvanced.value = false
  name.value = admin?.name ?? ''
  alias.value = admin?.alias ?? ''
  comment.value = admin?.comment ?? ''
  uuid.value = admin?.uuid ?? randomUuid()
  configs.value = (admin?.additional_configs ?? []).map((row) => [...row] as AdditionalConfig)
  defaultOutbound.value = admin?.default_outbound ?? null
  canAddAdmin.value = admin?.can_add_admin ?? false
  parent.value = { [admin?.parent_uuid ?? props.tree?.me_uuid ?? '']: true }
  const mine = myLimits.value
  limits.value = admin?.limits
    ? { ...admin.limits }
    : {
        max_users: Math.min(DEFAULT_LIMIT, mine?.max_users ?? DEFAULT_LIMIT),
        max_active_users: Math.min(DEFAULT_LIMIT, mine?.max_active_users ?? DEFAULT_LIMIT),
        // Under a limited admin a sub-admin starts with the parent's own cap (it can not be unlimited).
        max_online_users: mine?.max_online_users ?? null,
        max_total_usage_GB: mine?.max_total_usage_GB ?? null,
      }
})

const nameError = computed(() => touched.value && !name.value.trim())
const uuidError = computed(() => !editing.value && !UUID_RE.test(uuid.value.trim()))

const limitFields = computed(() =>
  (
    [
      { key: 'max_online_users', icon: 'pi pi-wifi', optional: true, suffix: '' },
      { key: 'max_active_users', icon: 'pi pi-bolt', optional: false, suffix: '' },
      { key: 'max_users', icon: 'pi pi-users', optional: false, suffix: '' },
      { key: 'max_total_usage_GB', icon: 'pi pi-arrow-right-arrow-left', optional: true, suffix: ` ${unitLabel('GB')}` },
    ] as const
  ).map((field) => {
    const mine = myLimits.value?.[field.key] ?? null
    const value = limits.value[field.key]
    const tooHigh = mine !== null && (value === null ? field.optional : value > mine)
    const missing = !field.optional && value === null
    return { ...field, mine, invalid: tooHigh || missing }
  }),
)
const configs = ref<AdditionalConfig[]>([])
const defaultOutbound = ref<number | null>(null)

const limitsInvalid = computed(() => !targetIsSuper.value && limitFields.value.some((field) => field.invalid))

async function submit() {
  touched.value = true
  const configsInvalid = configs.value.some((c) => configRowProblem(c))
  if (configsInvalid) showAdvanced.value = true
  if (!name.value.trim() || uuidError.value || limitsInvalid.value || configsInvalid || aliasError.value || busy.value) return
  busy.value = true
  error.value = null
  const payload: AdminPayload = {
    name: name.value.trim(),
    comment: comment.value.trim(),
    can_add_admin: canAddAdmin.value,
    parent_uuid: Object.keys(parent.value)[0] || undefined,
    additional_configs: cleanConfigRows(configs.value),
    default_outbound: defaultOutbound.value,
  }
  if (!targetIsSuper.value) payload.alias = alias.value.trim().toLowerCase()
  if (!targetIsSuper.value) {
    payload.max_users = limits.value.max_users ?? DEFAULT_LIMIT
    payload.max_active_users = limits.value.max_active_users ?? DEFAULT_LIMIT
    payload.max_online_users = limits.value.max_online_users ?? 0
    payload.max_total_usage_GB = limits.value.max_total_usage_GB ?? 0
  }
  try {
    if (props.admin) {
      await adminsApi.update(props.admin.uuid, payload)
      emit('saved', payload.name!)
    } else {
      const res = await adminsApi.create({ ...payload, uuid: uuid.value.trim().toLowerCase() })
      emit('created', res.name, { password: res.password, admin_link: res.admin_link })
    }
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
    :style="{ width: 'min(40rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
    :pt="{ content: { class: 'admin-form__content' } }"
  >
    <template #header>
      <div class="admin-form__title">
        <span class="admin-form__title-icon"><i class="pi" :class="editing ? 'pi-user-edit' : 'pi-user-plus'" /></span>
        <div class="min-w-0">
          <div class="font-semibold text-lg">{{ editing ? t('admins.form.editTitle', { name: admin?.name }) : t('admins.form.createTitle') }}</div>
          <div class="text-muted-color text-sm">{{ editing ? t('admins.form.editSubtitle') : t('admins.form.createSubtitle') }}</div>
        </div>
      </div>
    </template>

    <form class="admin-form" @submit.prevent="submit">
      <!-- Who -->
      <section class="admin-form__section">
        <div class="admin-form__field">
          <label for="admin-name" class="font-medium">{{ t('admins.form.name') }}</label>
          <InputText id="admin-name" v-model="name" autofocus maxlength="512" :invalid="nameError" :disabled="busy" :placeholder="t('admins.form.namePlaceholder')" />
          <small v-if="nameError" class="admin-form__error">{{ t('admins.form.nameRequired') }}</small>
        </div>
        <!-- Optional sign-in username (never for super admins) -->
        <div v-if="!targetIsSuper" class="admin-form__field">
          <label for="admin-alias" class="font-medium">
            {{ t('admins.form.alias') }} <span class="text-muted-color font-normal">({{ t('admins.form.optional') }})</span>
          </label>
          <InputText
            id="admin-alias"
            v-model="alias"
            dir="ltr"
            autocomplete="off"
            autocapitalize="none"
            spellcheck="false"
            maxlength="64"
            :invalid="!!aliasError"
            :disabled="busy"
            :placeholder="t('account.aliasPlaceholder')"
          />
          <small :class="aliasError ? 'admin-form__error' : 'text-muted-color'">{{ aliasError ?? t('admins.form.aliasHint') }}</small>
        </div>
        <div class="admin-form__field">
          <label for="admin-note" class="font-medium">
            {{ t('admins.form.note') }} <span class="text-muted-color font-normal">({{ t('admins.form.optional') }})</span>
          </label>
          <Textarea id="admin-note" v-model="comment" rows="2" auto-resize maxlength="512" :disabled="busy" :placeholder="t('admins.form.notePlaceholder')" />
        </div>
      </section>

      <!-- Permission -->
      <section v-if="canGrantSubAdmins || canAddAdmin" class="admin-form__section">
        <label class="admin-form__switch" for="admin-can-add">
          <span class="admin-form__switch-text">
            <span class="font-medium">{{ t('admins.form.canAddAdmin') }}</span>
            <small class="text-muted-color">{{ t('admins.form.canAddAdminHint') }}</small>
          </span>
          <ToggleSwitch v-model="canAddAdmin" input-id="admin-can-add" :disabled="busy || !canGrantSubAdmins" />
        </label>
      </section>

      <!-- Limits -->
      <section class="admin-form__section">
        <h4 class="admin-form__heading"><i class="pi pi-gauge" />{{ t('admins.form.limits') }}</h4>
        <Message v-if="targetIsSuper" severity="info" :closable="false" size="small">{{ t('admins.form.superNoLimits') }}</Message>
        <template v-else>
          <p class="admin-form__hint">{{ t('admins.form.limitsHint') }}</p>
          <div class="admin-form__limits">
            <div v-for="field in limitFields" :key="field.key" class="admin-form__field">
              <label :for="`admin-${field.key}`" class="admin-form__limit-label"><i :class="field.icon" />{{ t(`admins.limit.${field.key}`) }}</label>
              <InputNumber
                v-model="limits[field.key]"
                :input-id="`admin-${field.key}`"
                :min="0"
                :max="field.mine ?? undefined"
                :max-fraction-digits="field.key === 'max_total_usage_GB' ? 2 : 0"
                :suffix="field.suffix"
                :placeholder="field.optional ? t('admins.form.noLimit') : ''"
                :invalid="field.invalid"
                :disabled="busy"
                show-buttons
                button-layout="horizontal"
                fluid
              >
                <template #incrementicon><span class="pi pi-plus" /></template>
                <template #decrementicon><span class="pi pi-minus" /></template>
              </InputNumber>
              <small v-if="field.mine !== null" class="text-muted-color" :class="{ 'admin-form__error': field.invalid }">{{ t('admins.form.upTo', { max: field.mine }) }}</small>
              <small v-else-if="field.optional" class="text-muted-color">{{ t('admins.form.emptyNoLimit') }}</small>
            </div>
          </div>
        </template>
      </section>

      <!-- Advanced: where the admin sits in the tree, and its UUID -->
      <section class="admin-form__section">
        <button type="button" class="admin-form__toggle" :aria-expanded="showAdvanced" @click="showAdvanced = !showAdvanced">
          <i class="pi pi-sliders-h" />
          <span class="flex-1">{{ t('admins.form.advanced') }}</span>
          <span v-if="!showAdvanced && parentName" class="admin-form__toggle-hint">
            {{ t('admins.form.advancedHint', { name: parentName }) }}<template v-if="configs.length"> · {{ t('admins.form.configsCount', { n: configs.length }, configs.length) }}</template>
          </span>
          <i class="pi pi-angle-down admin-form__caret" :class="{ 'admin-form__caret--open': showAdvanced }" />
        </button>
        <div v-if="showAdvanced" class="admin-form__field">
          <label for="admin-parent" class="font-medium">{{ t('admins.form.parent') }}</label>
          <TreeSelect
            v-model="parent"
            input-id="admin-parent"
            :options="parentOptions"
            :expanded-keys="expandedParents"
            selection-mode="single"
            filter
            filter-mode="lenient"
            :disabled="busy"
            class="w-full"
          />
          <small class="text-muted-color">{{ t('admins.form.parentHint') }}</small>
        </div>
        <div v-if="showAdvanced && !editing" class="admin-form__field">
          <label for="admin-uuid" class="font-medium">UUID</label>
          <div class="flex gap-2">
            <InputText id="admin-uuid" v-model="uuid" dir="ltr" class="flex-1 min-w-0 font-mono text-sm" :invalid="uuidError" :disabled="busy" spellcheck="false" />
            <Button type="button" icon="pi pi-refresh" severity="secondary" outlined :aria-label="t('admins.form.newUuid')" v-tooltip.top="t('admins.form.newUuid')" @click="uuid = randomUuid()" />
          </div>
          <small :class="uuidError ? 'admin-form__error' : 'text-muted-color'">{{ uuidError ? t('admins.form.uuidInvalid') : t('admins.form.uuidHint') }}</small>
        </div>
        <!-- Where this admin's users (and its sub-admins' users) leave through, unless they choose -->
        <div v-if="showAdvanced && (tree?.outbounds.length ?? 0) > 0" class="admin-form__field">
          <label for="admin-outbound" class="admin-form__limit-label"><i class="pi pi-directions" />{{ t('admins.form.outbound') }}</label>
          <DefaultOutboundSelect v-model="defaultOutbound" :outbounds="tree?.outbounds ?? []" :inherited="admin?.inherited_outbound ?? null" :disabled="busy" input-id="admin-outbound" />
          <small class="text-muted-color">{{ t('admins.form.outboundHint') }}</small>
        </div>
        <!-- Configs every user of this admin (and of its sub-admins) gets -->
        <div v-if="showAdvanced" class="admin-form__field">
          <span class="admin-form__limit-label"><i class="pi pi-paperclip" />{{ t('admins.form.configs') }}<span v-if="configs.length" class="admin-form__count">{{ configs.length }}</span></span>
          <small class="text-muted-color">{{ t('admins.form.configsHint') }}</small>
          <AdditionalConfigsEditor v-model="configs" :disabled="busy" :show-errors="touched" />
        </div>
      </section>

      <Message v-if="!editing" severity="secondary" :closable="false" size="small" icon="pi pi-key">{{ t('admins.form.passwordInfo') }}</Message>
      <Message v-if="error" severity="error" :closable="false"><span class="whitespace-pre-line">{{ error }}</span></Message>

      <div class="admin-form__actions">
        <Button
          v-if="admin"
          type="button"
          icon="pi pi-key"
          :label="t('admins.resetPassword')"
          severity="warn"
          outlined
          :disabled="busy"
          class="admin-form__reset"
          @click="emit('resetPassword', admin)"
        />
        <Button type="button" :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="visible = false" />
        <Button type="submit" :icon="editing ? 'pi pi-check' : 'pi pi-user-plus'" :label="editing ? t('common.save') : t('admins.form.create')" :loading="busy" :disabled="limitsInvalid || uuidError" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.admin-form__title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.admin-form__title-icon {
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
.admin-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.admin-form__section {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}
.admin-form__section + .admin-form__section {
  padding-top: 1.25rem;
  border-top: 1px solid var(--p-content-border-color);
}
.admin-form__heading {
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
.admin-form__heading i {
  color: var(--p-primary-color);
}
.admin-form__hint {
  margin: -0.4rem 0 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.admin-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}
.admin-form__error {
  color: var(--p-red-500, #ef4444);
}
.admin-form__limits {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}
.admin-form__limit-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 500;
  font-size: 0.9rem;
}
.admin-form__limit-label i {
  font-size: 0.8rem;
  color: var(--p-primary-color);
}
.admin-form__limits :deep(.p-inputnumber-input) {
  text-align: center;
}
.admin-form__switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0.9rem;
  border-radius: 12px;
  border: 1px solid var(--p-content-border-color);
  cursor: pointer;
}
.admin-form__switch-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.admin-form__toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: 0;
  border-radius: 10px;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.88rem;
  text-align: start;
  cursor: pointer;
}
.admin-form__count {
  padding: 0 0.45rem;
  border-radius: 999px;
  font-size: 0.7rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
}
.admin-form__toggle-hint {
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8rem;
}
.admin-form__toggle:hover {
  color: var(--p-primary-color);
}
.admin-form__caret {
  transition: transform 0.25s ease;
}
.admin-form__caret--open {
  transform: rotate(180deg);
}
.admin-form__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}
.admin-form__reset {
  margin-inline-end: auto;
}
:global(.admin-form__node--muted .p-tree-node-label) {
  opacity: 0.55;
}
@media (max-width: 640px) {
  .admin-form__limits {
    grid-template-columns: 1fr;
  }
  .admin-form__reset {
    width: 100%;
  }
}
</style>
