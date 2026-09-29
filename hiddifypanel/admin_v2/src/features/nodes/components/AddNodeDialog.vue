<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { apiErrorMessage } from '@/core/api/client'
import { nodesApi, type NodeRegisterError, type PanelNode } from '@/features/nodes/api'

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ added: [node: PanelNode | null] }>()

const { t, te } = useI18n()

// https://host[:port]/<proxy path>/<admin uuid>/...
const LINK_RE = /^https:\/\/[^/\s:]+(?::\d+)?\/[^/\s]+\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:\/.*)?$/i

const link = ref('')
const name = ref('')
const touched = ref(false)
const busy = ref(false)
const done = ref(false)
const error = ref<string | null>(null)

const trimmed = computed(() => link.value.trim())
const linkValid = computed(() => LINK_RE.test(trimmed.value))
const linkHost = computed(() => (linkValid.value ? trimmed.value.split('://', 2)[1]!.split('/', 1)[0]! : ''))
const showLinkError = computed(() => touched.value && trimmed.value.length > 0 && !linkValid.value)

watch(visible, (open) => {
  if (!open) return
  link.value = ''
  name.value = ''
  touched.value = false
  busy.value = false
  done.value = false
  error.value = null
})

function errorText(err: unknown): string {
  const body = (err as { response?: { data?: NodeRegisterError } })?.response?.data
  if (body?.code && te(`nodes.errors.${body.code}`)) {
    const text = t(`nodes.errors.${body.code}`)
    return body.message && body.message !== body.code ? `${text}\n${body.message}` : text
  }
  if ((err as { code?: string })?.code === 'ECONNABORTED') return t('nodes.errors.timeout')
  return apiErrorMessage(err)
}

async function submit() {
  touched.value = true
  if (!linkValid.value || busy.value) return
  busy.value = true
  error.value = null
  try {
    const node = await nodesApi.register(trimmed.value, name.value.trim())
    done.value = true
    emit('added', node)
    window.setTimeout(() => {
      visible.value = false
    }, 1200)
  } catch (err) {
    error.value = errorText(err)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('nodes.add.title')"
    :closable="!busy"
    :dismissable-mask="!busy"
    :style="{ width: 'min(36rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': 'calc(100vw - 1rem)' }"
  >
    <Transition name="add-node-swap" mode="out-in">
      <div v-if="done" key="done" class="add-node-done">
        <span class="add-node-done__check"><i class="pi pi-check" /></span>
        <div class="font-semibold text-lg">{{ t('nodes.add.success') }}</div>
        <div class="text-muted-color">{{ linkHost }}</div>
      </div>

      <form v-else key="form" class="flex flex-col gap-4" @submit.prevent="submit">
        <ol class="add-node-steps">
          <li><span>1</span>{{ t('nodes.add.step1') }}</li>
          <li><span>2</span>{{ t('nodes.add.step2') }}</li>
          <li><span>3</span>{{ t('nodes.add.step3') }}</li>
        </ol>

        <div class="flex flex-col gap-2">
          <label for="node-admin-link" class="font-medium">{{ t('nodes.add.linkLabel') }}</label>
          <InputText
            id="node-admin-link"
            v-model="link"
            dir="ltr"
            class="w-full font-mono text-sm"
            :invalid="showLinkError"
            :disabled="busy"
            placeholder="https://node.example.com/xxxxxxxx/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/admin/"
            autocomplete="off"
            spellcheck="false"
            @blur="touched = true"
          />
          <small v-if="showLinkError" class="add-node-hint add-node-hint--error"><i class="pi pi-exclamation-circle" />{{ t('nodes.add.linkInvalid') }}</small>
          <small v-else-if="linkValid" class="add-node-hint add-node-hint--ok"><i class="pi pi-check-circle" />{{ t('nodes.add.linkOk', { host: linkHost }) }}</small>
          <small v-else class="add-node-hint">{{ t('nodes.add.linkHint') }}</small>
        </div>

        <div class="flex flex-col gap-2">
          <label for="node-name" class="font-medium">
            {{ t('nodes.add.nameLabel') }} <span class="text-muted-color font-normal">({{ t('nodes.add.optional') }})</span>
          </label>
          <InputText id="node-name" v-model="name" class="w-full" :disabled="busy" :placeholder="linkHost || t('nodes.add.namePlaceholder')" maxlength="100" />
        </div>

        <Transition name="add-node-fade">
          <Message v-if="error" severity="error" :closable="false"><span class="whitespace-pre-line">{{ error }}</span></Message>
        </Transition>
        <Transition name="add-node-fade">
          <div v-if="busy" class="add-node-progress">
            <span class="add-node-progress__bar" />
            <span>{{ t('nodes.add.connecting') }}</span>
          </div>
        </Transition>

        <div class="flex justify-end gap-2">
          <Button type="button" :label="t('common.cancel')" severity="secondary" text :disabled="busy" @click="visible = false" />
          <Button type="submit" :label="t('nodes.add.submit')" icon="pi pi-link" :loading="busy" :disabled="!linkValid" />
        </div>
      </form>
    </Transition>
  </Dialog>
</template>

<style scoped>
.add-node-steps {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0.85rem 1rem;
  list-style: none;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-primary-color) 7%, transparent);
}
.add-node-steps li {
  display: flex;
  gap: 0.6rem;
  align-items: baseline;
  font-size: 0.9rem;
}
.add-node-steps li span {
  flex-shrink: 0;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 50%;
  display: inline-grid;
  place-items: center;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--p-primary-contrast-color, #fff);
  background: var(--p-primary-color);
}
.add-node-hint {
  display: flex;
  gap: 0.35rem;
  align-items: baseline;
  color: var(--p-text-muted-color);
}
.add-node-hint--error {
  color: var(--p-red-500, #ef4444);
}
.add-node-hint--ok {
  color: var(--p-green-500, #22c55e);
}
.add-node-progress {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.add-node-progress__bar {
  position: relative;
  height: 4px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--p-content-border-color);
}
.add-node-progress__bar::after {
  content: '';
  position: absolute;
  inset-block: 0;
  width: 35%;
  border-radius: 4px;
  background: var(--p-primary-color);
  animation: add-node-indeterminate 1.3s ease-in-out infinite;
}
.add-node-done {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem 0 1rem;
  text-align: center;
}
.add-node-done__check {
  width: 4rem;
  height: 4rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 1.75rem;
  color: #fff;
  background: var(--p-green-500, #22c55e);
  animation: add-node-pop 0.45s cubic-bezier(0.2, 1.4, 0.4, 1) both;
}
@keyframes add-node-indeterminate {
  from {
    inset-inline-start: -35%;
  }
  to {
    inset-inline-start: 100%;
  }
}
@keyframes add-node-pop {
  from {
    transform: scale(0.4);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
.add-node-fade-enter-active,
.add-node-fade-leave-active,
.add-node-swap-enter-active,
.add-node-swap-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.add-node-fade-enter-from,
.add-node-fade-leave-to {
  opacity: 0;
}
.add-node-swap-enter-from,
.add-node-swap-leave-to {
  opacity: 0;
  transform: scale(0.98);
}
@media (prefers-reduced-motion: reduce) {
  .add-node-progress__bar::after,
  .add-node-done__check {
    animation: none;
  }
}
</style>
