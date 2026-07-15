<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Popover from 'primevue/popover'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import InputGroup from 'primevue/inputgroup'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import {
  customProxiesApi,
  domainsApi,
  type DomainOption,
  type PanelUserOption,
} from '@/core/api/generated'
import {
  resolvePreviewParams,
  usePreviewSettings,
  type UaPreset,
} from '@/shared/composables/usePreviewSettings'

const props = withDefaults(
  defineProps<{
    requireUser?: boolean
    uaPresets?: UaPreset[]
    disabled?: boolean
  }>(),
  {
    requireUser: false,
    uaPresets: () => [],
    disabled: false,
  },
)

const emit = defineEmits<{
  preview: [params: Record<string, unknown>]
}>()

const { t } = useI18n()
const { settings } = usePreviewSettings()
const popoverRef = ref<InstanceType<typeof Popover> | null>(null)
const domains = ref<DomainOption[]>([])
const users = ref<PanelUserOption[]>([])
const optionsLoaded = ref(false)

const domainOptions = computed(() =>
  domains.value.map((d) => ({
    value: d.id,
    label: d.alias ? `${d.domain} (${d.alias})` : d.domain,
  })),
)

const userOptions = computed(() =>
  users.value.map((u) => ({
    value: u.id ?? null,
    label: u.name || u.uuid || String(u.id),
  })),
)

const uaOptions = computed(() =>
  props.uaPresets.map((ua) => ({
    value: ua.id,
    label: ua.label || ua.id,
  })),
)

async function loadOptions() {
  if (optionsLoaded.value) return
  try {
    const [domainList, userList] = await Promise.all([
      domainsApi.options(),
      customProxiesApi.listUsers().catch(() => []),
    ])
    domains.value = domainList
    users.value = userList
    if (domainList.length && settings.value.selectedDomainId == null) {
      settings.value.selectedDomainId = domainList[0].id
    }
    if (userList.length && settings.value.selectedUserId == null) {
      settings.value.selectedUserId = userList[0].id ?? null
    }
    if (!settings.value.selectedUaId && props.uaPresets.length) {
      settings.value.selectedUaId = props.uaPresets[0].id
    }
    optionsLoaded.value = true
  } catch {
    domains.value = []
    users.value = []
  }
}

function togglePopover(event: Event) {
  void loadOptions()
  popoverRef.value?.toggle(event)
}

function runPreview() {
  const params = resolvePreviewParams(settings.value, props.uaPresets, domains.value)
  emit('preview', params)
}

async function onPopoverShow() {
  await loadOptions()
}
</script>

<template>
  <span class="editor-preview-wrap">
  <InputGroup class="editor-preview-button">
    <Button
      icon="pi pi-eye"
      :label="t('editor.preview')"
      severity="secondary"
      size="small"
      :disabled="disabled"
      @click="runPreview"
    />
    <Button
      icon="pi pi-chevron-down"
      severity="secondary"
      size="small"
      :disabled="disabled"
      :aria-label="t('editor.previewParams')"
      @click="togglePopover"
    />
  </InputGroup>

  <Popover ref="popoverRef" class="editor-preview-popover" @show="onPopoverShow">
    <div class="flex flex-col gap-3 w-72 max-w-full p-1">
      <HorizontalField :label="t('proxy.exampleDomain')" input-id="preview-domain-mode">
        <div class="flex flex-col gap-2 w-full">
          <Select
            id="preview-domain-mode"
            v-model="settings.domainMode"
            :options="[
              { value: 'pick', label: t('proxy.exampleDomainPick') },
              { value: 'custom', label: t('proxy.exampleDomainCustom') },
            ]"
            option-label="label"
            option-value="value"
            class="w-full"
          />
          <Select
            v-if="settings.domainMode === 'pick'"
            v-model="settings.selectedDomainId"
            :options="domainOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('proxy.exampleDomainPick')"
            class="w-full"
          />
          <InputText
            v-else
            v-model="settings.customDomain"
            :placeholder="t('proxy.exampleDomainCustom')"
            class="w-full"
          />
        </div>
      </HorizontalField>

      <HorizontalField v-if="requireUser" :label="t('proxy.exampleUser')" input-id="preview-user-mode">
        <div class="flex flex-col gap-2 w-full">
          <Select
            id="preview-user-mode"
            v-model="settings.userMode"
            :options="[
              { value: 'sample', label: t('proxy.exampleUserSample') },
              { value: 'pick', label: t('proxy.exampleUserPick') },
            ]"
            option-label="label"
            option-value="value"
            class="w-full"
          />
          <Select
            v-if="settings.userMode === 'pick'"
            v-model="settings.selectedUserId"
            :options="userOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('proxy.exampleUserPick')"
            class="w-full"
          />
        </div>
      </HorizontalField>

      <HorizontalField :label="t('proxy.exampleUserAgent')" input-id="preview-ua-mode">
        <div class="flex flex-col gap-2 w-full">
          <Select
            id="preview-ua-mode"
            v-model="settings.uaMode"
            :options="[
              { value: 'preset', label: t('proxy.exampleUaPreset') },
              { value: 'custom', label: t('proxy.exampleUaCustom') },
            ]"
            option-label="label"
            option-value="value"
            class="w-full"
          />
          <Select
            v-if="settings.uaMode === 'preset'"
            v-model="settings.selectedUaId"
            :options="uaOptions"
            option-label="label"
            option-value="value"
            class="w-full"
          />
          <InputText
            v-else
            v-model="settings.customUa"
            :placeholder="t('proxy.exampleUaCustom')"
            class="w-full"
          />
        </div>
      </HorizontalField>

      <HorizontalField :label="t('proxy.ignoreSkip')" input-id="preview-ignore-skip" :hint="t('proxy.ignoreSkipHint')">
        <Checkbox id="preview-ignore-skip" v-model="settings.ignoreSkip" binary />
      </HorizontalField>
    </div>
  </Popover>
  </span>
</template>

<style scoped>
.editor-preview-wrap {
  display: inline-flex;
  flex: 0 0 auto;
}

.editor-preview-button :deep(.p-button) {
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
