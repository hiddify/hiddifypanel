<template>
  <div class="flex flex-row gap-2 items-start w-full">
    <MultiSelect
      v-model="selected"
      :options="options"
      option-label="label"
      option-value="value"
      :placeholder="placeholder"
      filter
      display="chip"
      class="flex-1 min-w-0"
    />
    <Button
      type="button"
      icon="pi pi-plus"
      :aria-label="t('domain.addTitle')"
      class="shrink-0"
      @click="showDialog = true"
    />
    <AddDomainDialog
      v-model:visible="showDialog"
      :allowed-modes="dialogModes"
      @created="onDomainCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import MultiSelect from 'primevue/multiselect'
import Button from 'primevue/button'
import AddDomainDialog from '@/shared/components/AddDomainDialog.vue'
import { domainsApi, type DomainOption } from '@/core/api/generated'

const props = defineProps<{
  modelValue: number[]
  /** Filter domains by proxy domain_modes (direct, cdn, relay, fake, special, reality). */
  domainModes?: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number[]]
}>()

const { t } = useI18n()
const domainList = ref<DomainOption[]>([])
const showDialog = ref(false)

const dialogModes = computed(() =>
  props.domainModes?.length ? props.domainModes : undefined,
)

const selected = computed({
  get: () => props.modelValue ?? [],
  set: (v) => emit('update:modelValue', v),
})

const options = computed(() =>
  domainList.value.map((d) => ({
    label: d.alias ? `${d.domain} (${d.alias}) [${d.mode}]` : `${d.domain} [${d.mode}]`,
    value: d.id,
  })),
)

const placeholder = computed(() => t('proxy.domainIds'))

async function load() {
  domainList.value = await domainsApi.options({
    modes: props.domainModes?.length ? props.domainModes : undefined,
  })
  const allowed = new Set(domainList.value.map((d) => d.id))
  const filtered = (props.modelValue ?? []).filter((id) => allowed.has(id))
  if (filtered.length !== (props.modelValue ?? []).length) {
    emit('update:modelValue', filtered)
  }
}

async function onDomainCreated(created: DomainOption) {
  await load()
  const ids = [...(props.modelValue ?? []), created.id]
  emit('update:modelValue', ids)
}

onMounted(load)
watch(() => props.domainModes?.join(','), load)
</script>
