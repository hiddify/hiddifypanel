<template>
  <Panel v-if="result" :header="t('validation.title')">
    <Message v-if="result.ok" severity="success">{{ t('common.validationOk') }}</Message>
    <Message v-else severity="error">{{ t('common.validationFailed') }}</Message>

    <Fieldset v-if="result.errors?.length" :legend="t('validation.errors')">
      <ul>
        <li v-for="(e, i) in result.errors" :key="'e' + i">{{ e.message }}</li>
      </ul>
    </Fieldset>
    <Fieldset v-if="result.warnings?.length" :legend="t('validation.warnings')">
      <ul>
        <li v-for="(w, i) in result.warnings" :key="'w' + i">{{ w.message }}</li>
      </ul>
    </Fieldset>
    <Fieldset v-if="result.compiled_preview" :legend="t('validation.preview')">
      <ScrollPanel class="config-scroll-panel" :style="{ width: '100%', height: '240px' }">
        <pre class="validation-preview-pre">{{ result.compiled_preview }}</pre>
      </ScrollPanel>
    </Fieldset>
  </Panel>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Panel from 'primevue/panel'
import Message from 'primevue/message'
import Fieldset from 'primevue/fieldset'
import ScrollPanel from 'primevue/scrollpanel'
import type { ValidationResult } from '@/core/api/generated'

defineProps<{
  result: ValidationResult | null
}>()

const { t } = useI18n()
</script>

<style scoped>
.validation-preview-pre {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.4;
  white-space: pre;
  user-select: text;
}

.config-scroll-panel :deep(.p-scrollpanel-content) {
  user-select: text;
}
</style>
