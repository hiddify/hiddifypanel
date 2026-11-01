<script setup lang="ts">
/**
 * The user page as this admin's users see it: brand title, support link and text, language, a custom page.
 * An empty field: what the admins above (or the panel's settings) give, shown as its placeholder.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { apiErrorMessage } from '@/core/api/client'
import { LANGUAGE_LOOK } from '@/shared/utils/languages'
import { adminsApi, type OverrideInfo, type OverrideKey, type OverrideSettings } from '@/features/admins/api'
import FlagIcon from '@/shared/components/FlagIcon.vue'

const props = defineProps<{ info: OverrideInfo; languages: string[] }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ saved: [info: OverrideInfo] }>()
const { t } = useI18n()
const toast = useToast()

const KEYS: OverrideKey[] = ['branding_title', 'branding_site', 'branding_freetext', 'lang', 'user_page_url']
const URL_KEYS: OverrideKey[] = ['branding_site', 'user_page_url']
const URL_RE = /^https?:\/\/[^\s/]+\.[^\s/]+(\/\S*)?$/i

const form = ref<Record<OverrideKey, string>>(fill(props.info.override_settings))
const showAdvanced = ref(false)
const saving = ref(false)
function fill(values: OverrideSettings): Record<OverrideKey, string> {
  return Object.fromEntries(KEYS.map((k) => [k, values[k] ?? ''])) as Record<OverrideKey, string>
}
watch(visible, (open) => {
  if (!open) return
  form.value = fill(props.info.override_settings)
  showAdvanced.value = !!form.value.user_page_url
})

function compact(values: Record<OverrideKey, string>): OverrideSettings {
  return Object.fromEntries(KEYS.map((k) => [k, values[k].trim()]).filter(([, v]) => v))
}
const cleaned = computed(() => compact(form.value))
const dirty = computed(() => JSON.stringify(cleaned.value) !== JSON.stringify(compact(fill(props.info.override_settings))))
const badUrl = (k: OverrideKey) => !!form.value[k].trim() && !URL_RE.test(form.value[k].trim())
const invalid = computed(() => URL_KEYS.some(badUrl))

const langOptions = computed(() => [
  { value: '', label: t('account.userPage.inherit', { value: look(props.info.override_defaults.lang) }) },
  ...props.languages.map((code) => ({ value: code, label: look(code) })),
])
/** The flag of a language; the inherited one ("") has the panel default's */
const flagOf = (code: string) => LANGUAGE_LOOK[code || props.info.override_defaults.lang || '']?.flag ?? ''
function look(code: string | undefined): string {
  const l = code ? LANGUAGE_LOOK[code] : undefined
  return l ? l.name : code || '—'
}
function placeholder(k: OverrideKey): string {
  const inherited = props.info.override_defaults[k]
  return inherited ? t('account.userPage.inherit', { value: inherited.length > 60 ? `${inherited.slice(0, 59)}…` : inherited }) : t('account.userPage.empty')
}

async function save() {
  if (invalid.value || saving.value) return
  saving.value = true
  try {
    emit('saved', await adminsApi.saveMyOverrides(cleaned.value))
    visible.value = false
    toast.add({ severity: 'success', summary: t('account.userPage.saved'), life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :draggable="false" :header="t('account.userPage.title')" :style="{ width: 'min(40rem, calc(100vw - 1.5rem))' }" :breakpoints="{ '640px': '100vw' }">
    <form class="upf" @submit.prevent="save">
      <p class="upf__intro">{{ t('account.userPage.intro') }}</p>

      <div class="upf__field">
        <label for="upf-title" class="font-medium">{{ t('account.userPage.brandTitle') }}</label>
        <InputText id="upf-title" v-model="form.branding_title" maxlength="200" :placeholder="placeholder('branding_title')" :disabled="saving" fluid />
        <small class="upf__hint">{{ t('account.userPage.brandTitleHint') }}</small>
      </div>

      <div class="upf__field">
        <label for="upf-site" class="font-medium">{{ t('account.userPage.supportLink') }}</label>
        <InputText id="upf-site" v-model="form.branding_site" dir="ltr" inputmode="url" :placeholder="placeholder('branding_site')" :invalid="badUrl('branding_site')" :disabled="saving" fluid />
        <small v-if="badUrl('branding_site')" class="upf__error">{{ t('account.userPage.badUrl') }}</small>
        <small v-else class="upf__hint">{{ t('account.userPage.supportLinkHint') }}</small>
      </div>

      <div class="upf__field">
        <label for="upf-text" class="font-medium">{{ t('account.userPage.supportText') }}</label>
        <Textarea id="upf-text" v-model="form.branding_freetext" rows="3" auto-resize :placeholder="placeholder('branding_freetext')" :disabled="saving" fluid />
        <small class="upf__hint">{{ t('account.userPage.supportTextHint') }}</small>
      </div>

      <div class="upf__field">
        <label for="upf-lang" class="font-medium">{{ t('account.userPage.lang') }}</label>
        <Select v-model="form.lang" input-id="upf-lang" :options="langOptions" option-label="label" option-value="value" :disabled="saving" fluid>
          <template #value="{ value }"><span class="upf__lang"><FlagIcon :code="flagOf(value)" />{{ langOptions.find((o) => o.value === value)?.label }}</span></template>
          <template #option="{ option }"><span class="upf__lang"><FlagIcon :code="flagOf(option.value)" />{{ option.label }}</span></template>
        </Select>
        <small class="upf__hint">{{ t('account.userPage.langHint') }}</small>
      </div>

      <Button type="button" text size="small" :icon="showAdvanced ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" :label="t('account.userPage.advanced')" class="self-start" @click="showAdvanced = !showAdvanced" />
      <div v-if="showAdvanced" class="upf__field">
        <label for="upf-page" class="font-medium">{{ t('account.userPage.customPage') }}</label>
        <InputText id="upf-page" v-model="form.user_page_url" dir="ltr" inputmode="url" :placeholder="placeholder('user_page_url')" :invalid="badUrl('user_page_url')" :disabled="saving" fluid />
        <small v-if="badUrl('user_page_url')" class="upf__error">{{ t('account.userPage.badUrl') }}</small>
        <small v-else class="upf__hint">{{ t('account.userPage.customPageHint') }}</small>
      </div>
    </form>
    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" text @click="visible = false" />
      <Button icon="pi pi-check" :label="t('account.save')" :loading="saving" :disabled="!dirty || invalid" @click="save" />
    </template>
  </Dialog>
</template>

<style scoped>
.upf {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.upf__intro {
  margin: 0;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}
.upf__field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.upf__hint {
  color: var(--p-text-muted-color);
}
.upf__error {
  color: var(--p-red-500);
}
.upf__lang {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
</style>
