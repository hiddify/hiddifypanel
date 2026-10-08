<script setup lang="ts">
/**
 * Apply configs / reinstall / update as a dialog over the page you are on (settings, domains...): asks first when
 * the action is disruptive, then shows the live run, so there is no trip to the Apply page.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import { apiErrorMessage } from '@/core/api/client'
import { ACTION_META, applyApi, type ApplyAction, type StartedRun } from '@/features/apply/api'
import RunPanel from '@/features/apply/components/RunPanel.vue'

const props = defineProps<{ action: ApplyAction | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ finished: [action: ApplyAction, ok: boolean] }>()

const { t } = useI18n()

type Stage = 'confirm' | 'starting' | 'running' | 'error'
const stage = ref<Stage>('confirm')
const run = ref<StartedRun | null>(null)
const error = ref<string | null>(null)
const finished = ref(false)

const meta = computed(() => (props.action ? ACTION_META[props.action] : null))

async function start() {
  if (!props.action) return
  stage.value = 'starting'
  error.value = null
  try {
    run.value = await applyApi.start(props.action)
    finished.value = false
    stage.value = 'running'
  } catch (err) {
    error.value = apiErrorMessage(err)
    stage.value = 'error'
  }
}

watch(visible, (open) => {
  if (!open || !props.action) return
  run.value = null
  error.value = null
  finished.value = false
  // The harmless ones just run; the disruptive ones ask first
  if (ACTION_META[props.action].confirm) stage.value = 'confirm'
  else void start()
})

function onFinished(ok: boolean) {
  finished.value = true
  if (props.action) emit('finished', props.action, ok)
}

function close() {
  visible.value = false
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :draggable="false"
    :closable="stage !== 'starting'"
    :header="action ? t(`apply.action.${action}.title`) : ''"
    :style="{ width: 'min(56rem, calc(100vw - 1.5rem))' }"
    :breakpoints="{ '640px': '100vw' }"
  >
    <template v-if="action && meta">
      <div v-if="stage === 'confirm'" class="ard-confirm">
        <span class="ard-confirm__icon" :style="{ '--c': meta.color }"><i :class="meta.icon" /></span>
        <p>{{ t(`apply.action.${action}.confirm`) }}</p>
      </div>
      <div v-else-if="stage === 'starting'" class="ard-confirm">
        <span class="ard-confirm__icon" :style="{ '--c': meta.color }"><i class="pi pi-spin pi-cog" /></span>
        <p>{{ t('apply.run.starting') }}</p>
      </div>
      <Message v-else-if="stage === 'error'" severity="warn" :closable="false">
        <b>{{ t('apply.notStarted') }}</b>
        <div>{{ error }}</div>
      </Message>
      <RunPanel v-else-if="run" :key="run.started" :action="run.action" :file="run.log" :started="run.started" :sources="run" @finished="onFinished" @close="close" />
    </template>

    <template #footer>
      <template v-if="stage === 'confirm' && action">
        <Button :label="t('common.cancel')" severity="secondary" text @click="close" />
        <Button :label="t(`apply.action.${action}.button`)" :icon="meta?.icon" :severity="meta?.danger ? 'danger' : undefined" @click="start" />
      </template>
      <Button v-else-if="stage === 'error'" :label="t('donation.close')" severity="secondary" @click="close" />
      <Button v-else-if="stage === 'running'" :label="finished ? t('donation.close') : t('apply.run.hide')" severity="secondary" :text="!finished" @click="close" />
    </template>
  </Dialog>
</template>

<style scoped>
.ard-confirm {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.ard-confirm p {
  margin: 0;
  line-height: 1.6;
}
.ard-confirm__icon {
  flex: none;
  width: 3rem;
  height: 3rem;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 1.3rem;
  color: var(--c);
  background: color-mix(in srgb, var(--c) 14%, transparent);
}
</style>
