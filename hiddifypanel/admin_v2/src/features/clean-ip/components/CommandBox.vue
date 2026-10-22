<script setup lang="ts">
/** A test command to copy and run on another device (Unix or Windows), then a wait for what its runs send back. */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { isSuperAdmin } from '@/core/panelShell'
import LineNumberedCode from '@/shared/components/LineNumberedCode.vue'
import type { CleanIpCommand } from '../api'

const props = defineProps<{ command: CleanIpCommand; waiting: boolean }>()
const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()

const platform = ref<'unix' | 'windows'>('unix')
const shown = computed(() => props.command.commands[platform.value])

// The script itself, exactly as the command downloads it (rendered from its base config for this command)
const scriptOpen = ref(false)
const script = ref('')
const scriptError = ref('')
const loadingScript = ref(false)

async function viewScript() {
  scriptOpen.value = true
  loadingScript.value = true
  scriptError.value = ''
  try {
    const res = await fetch(props.command.script_url, { cache: 'no-store', credentials: 'omit' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    script.value = await res.text()
  } catch (e) {
    scriptError.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingScript.value = false
  }
}
</script>

<template>
  <div class="cmd">
    <div class="cmd__platforms" role="tablist">
      <button type="button" role="tab" :aria-selected="platform === 'unix'" :class="{ on: platform === 'unix' }" @click="platform = 'unix'">
        <i class="pi pi-mobile" /> {{ t('cleanIp.platformUnix') }}
      </button>
      <button type="button" role="tab" :aria-selected="platform === 'windows'" :class="{ on: platform === 'windows' }" @click="platform = 'windows'">
        <i class="pi pi-microsoft" /> {{ t('cleanIp.platformWindows') }}
      </button>
    </div>
    <div class="cmd__code">
      <code dir="ltr">{{ shown }}</code>
      <Button icon="pi pi-copy" :label="t('common.copy')" size="small" @click="emit('copy', shown)" />
    </div>
    <p class="cmd__needs">{{ platform === 'unix' ? t('cleanIp.cmdUnix') : t('cleanIp.cmdWindows') }} · {{ t('cleanIp.cmdNote') }}</p>
    <div class="cmd__script">
      <Button :label="t('cleanIp.viewScript')" icon="pi pi-eye" size="small" text @click="viewScript" />
      <RouterLink v-if="isSuperAdmin && command.template_id" v-slot="{ href, navigate }" :to="{ name: 'base-config-edit', params: { id: command.template_id } }" custom>
        <Button as="a" :href="href" :label="t('cleanIp.editScript')" icon="pi pi-pencil" size="small" text severity="secondary" @click="navigate" />
      </RouterLink>
    </div>
  </div>

  <Dialog v-model:visible="scriptOpen" modal :header="t('cleanIp.scriptTitle')" :breakpoints="{ '960px': '95vw' }" :style="{ width: '60rem' }">
    <p class="cmd__dialog-hint">{{ t('cleanIp.scriptHint') }}</p>
    <div v-if="loadingScript" class="cmd__dialog-loading"><ProgressSpinner style="width: 2rem; height: 2rem" /></div>
    <Message v-else-if="scriptError" severity="error" :closable="false">{{ scriptError }}</Message>
    <div v-else class="cmd__code-view" dir="ltr"><LineNumberedCode :text="script" /></div>
    <template #footer>
      <RouterLink v-if="isSuperAdmin && command.template_id" v-slot="{ href, navigate }" :to="{ name: 'base-config-edit', params: { id: command.template_id } }" custom>
        <Button as="a" :href="href" :label="t('cleanIp.editScript')" icon="pi pi-pencil" severity="secondary" @click="navigate" />
      </RouterLink>
      <Button :label="t('common.copy')" icon="pi pi-copy" :disabled="!script" @click="emit('copy', script)" />
    </template>
  </Dialog>
  <div v-if="waiting" class="cmd__waiting">
    <span class="cmd__pulse" />
    {{ t('cleanIp.waiting') }}
  </div>
</template>

<style scoped>
.cmd {
  margin-top: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.75rem;
  overflow: hidden;
}
.cmd__platforms {
  display: flex;
  background: var(--p-content-hover-background);
}
.cmd__platforms button {
  flex: 1;
  padding: 0.55rem 0.75rem;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--p-text-muted-color);
  font: inherit;
  font-size: 0.85rem;
  cursor: pointer;
}
.cmd__platforms button.on {
  color: var(--p-primary-color);
  border-bottom-color: var(--p-primary-color);
  font-weight: 600;
}
.cmd__code {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.75rem;
}
.cmd__code code {
  flex: 1;
  min-width: 0;
  padding: 0.6rem 0.7rem;
  font-size: 0.78rem;
  line-height: 1.5;
  border-radius: 0.5rem;
  color: var(--p-surface-100);
  background: var(--p-surface-900);
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.cmd__needs {
  margin: 0;
  padding: 0 0.75rem 0.75rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.cmd__script {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding: 0 0.5rem 0.5rem;
}
.cmd__dialog-hint {
  margin: 0 0 0.75rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.cmd__dialog-loading {
  display: grid;
  place-items: center;
  padding: 2rem;
}
.cmd__code-view {
  max-block-size: 65vh;
  overflow: auto;
  border-radius: 0.6rem;
  border: 1px solid var(--p-content-border-color);
}
.cmd__waiting {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 1rem;
  padding: 0.85rem 1rem;
  font-size: 0.88rem;
  color: var(--p-text-muted-color);
  border: 1px dashed var(--p-content-border-color);
  border-radius: 0.75rem;
}
.cmd__pulse {
  inline-size: 0.6rem;
  block-size: 0.6rem;
  border-radius: 50%;
  background: var(--p-primary-color);
  animation: cmd-pulse 1.4s ease-in-out infinite;
}
@keyframes cmd-pulse {
  50% {
    opacity: 0.25;
    transform: scale(0.7);
  }
}
</style>
