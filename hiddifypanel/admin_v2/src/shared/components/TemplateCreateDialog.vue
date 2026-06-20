<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import HorizontalField from '@/shared/components/HorizontalField.vue'
import TemplatedEditor from '@/shared/components/TemplatedEditor.vue'
import { proxyTemplatesApi, type ProxyTemplate } from '@/core/api/generated'
import { buildTemplateSlug } from '@/shared/utils/template-slug'
import { usesJsonTemplate } from '@/shared/utils/core-template'

const props = defineProps<{
  visible: boolean
  core: string
  category: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  created: [template: ProxyTemplate]
}>()

const { t } = useI18n()
const toast = useToast()

const description = ref('')
const content = ref('')
const saving = ref(false)

watch(
  () => props.visible,
  (open) => {
    if (!open) return
    description.value = ''
    content.value = usesJsonTemplate(props.core)
      ? props.category === 'server_inbound'
        ? '{\n  \n}'
        : '[]'
      : ''
  },
)

function close() {
  emit('update:visible', false)
}

async function save() {
  const trimmed = description.value.trim()
  if (!trimmed) return
  saving.value = true
  try {
    const slug = buildTemplateSlug(props.core, props.category, trimmed)
    const created = await proxyTemplatesApi.create({
      name: trimmed,
      slug,
      core: props.core,
      category: props.category,
      description: trimmed,
      content: content.value,
    })
    toast.add({ severity: 'success', summary: t('common.saved'), life: 3000 })
    emit('created', created)
    close()
  } catch {
    toast.add({ severity: 'error', summary: t('common.loadFailed'), life: 4000 })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :header="t('template.new')"
    class="w-full max-w-2xl"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="flex flex-col gap-3">
      <HorizontalField :label="t('template.description')" input-id="new-tpl-desc">
        <InputText id="new-tpl-desc" v-model="description" class="w-full" />
      </HorizontalField>
      <HorizontalField :label="t('template.content')">
        <TemplatedEditor
          v-model="content"
          :variant="usesJsonTemplate(core) ? 'json' : 'plain'"
          :height="usesJsonTemplate(core) ? '280px' : undefined"
          :rows="12"
          :core="core"
          :category="category"
          :show-include="false"
        />
      </HorizontalField>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" text @click="close" />
      <Button icon="pi pi-save" :label="t('common.save')" :loading="saving" :disabled="!description.trim()" @click="save" />
    </template>
  </Dialog>
</template>
