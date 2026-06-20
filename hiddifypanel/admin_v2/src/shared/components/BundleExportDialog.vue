<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'

const visible = defineModel<boolean>('visible', { default: false })

const emit = defineEmits<{
  confirm: [excludeBuiltin: boolean]
}>()

const { t } = useI18n()
const excludeBuiltin = ref(true)

watch(visible, (open) => {
  if (open) excludeBuiltin.value = true
})

function confirm() {
  emit('confirm', excludeBuiltin.value)
  visible.value = false
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="t('editor.exportBundle')" :style="{ width: 'min(28rem, 96vw)' }">
    <div class="flex items-start gap-2">
      <Checkbox v-model="excludeBuiltin" input-id="exclude-builtin" binary />
      <label for="exclude-builtin" class="cursor-pointer text-sm">{{ t('editor.excludeBuiltinTemplates') }}</label>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" text @click="visible = false" />
      <Button :label="t('proxy.export')" icon="pi pi-download" @click="confirm" />
    </template>
  </Dialog>
</template>
