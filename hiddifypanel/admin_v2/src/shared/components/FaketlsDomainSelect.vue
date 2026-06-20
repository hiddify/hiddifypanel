<template>
  <div class="flex flex-row gap-2 items-start w-full">
    <MultiSelect
      v-model="selected"
      :options="domainOptions"
      option-label="label"
      option-value="value"
      :placeholder="t('proxy.faketlsDomains')"
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
      :allowed-modes="['special']"
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
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const { t } = useI18n()
const specialDomains = ref<string[]>([])
const showDialog = ref(false)

const selected = computed({
  get: () => props.modelValue ?? [],
  set: (v) => emit('update:modelValue', v),
})

const domainOptions = computed(() =>
  specialDomains.value.map((d) => ({ label: d, value: d })),
)

async function load() {
  const rows = await domainsApi.options({ modes: ['special'] })
  specialDomains.value = rows.map((d) => d.domain).filter(Boolean) as string[]
  const allowed = new Set(specialDomains.value)
  const filtered = (props.modelValue ?? []).filter((d) => allowed.has(d))
  if (filtered.length !== (props.modelValue ?? []).length) {
    emit('update:modelValue', filtered)
  }
}

async function onDomainCreated(created: DomainOption) {
  await load()
  if (created.domain && !props.modelValue?.includes(created.domain)) {
    emit('update:modelValue', [...(props.modelValue ?? []), created.domain])
  }
}

onMounted(load)
watch(() => props.modelValue, load)
</script>
