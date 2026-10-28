<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import { useToast } from 'primevue/usetoast'
import { apiErrorMessage } from '@/core/api/client'
import { nodesApi, type NodeRegisterError, type PanelNode } from '@/features/nodes/api'

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ added: [node: PanelNode | null] }>()

const { t, te } = useI18n()
const toast = useToast()

// https://host[:port]/<proxy path>/<admin uuid>/...
const LINK_RE = /^https:\/\/[^/\s:]+(?::\d+)?\/[^/\s]+\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:\/.*)?$/i

const link = ref('')
const name = ref('')
const touched = ref(false)
const busy = ref(false)
const done = ref(false)
/** A failed registration, in the panel's language: where, what happened, what to do; the technical text only goes to the clipboard. */
interface ShownError {
  side: 'node' | 'between' | 'parent' | ''
  what: string
  fix: string
  reg: string
  technical: string
}
const error = ref<ShownError | null>(null)
const SIDE_ICON: Record<string, string> = { node: 'pi pi-server', between: 'pi pi-arrows-h', parent: 'pi pi-home', '': 'pi pi-exclamation-triangle' }

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

function shownError(err: unknown): ShownError {
  const body = (err as { response?: { data?: NodeRegisterError } })?.response?.data
  const code = body?.code && te(`nodes.errors.${body.code}`) ? body.code : (err as { code?: string })?.code === 'ECONNABORTED' ? 'timeout' : ''
  const side = (['node', 'between', 'parent'].includes(String(body?.side)) ? body!.side : '') as ShownError['side']
  const message = body?.message && body.message !== body.code ? body.message : ''
  const technical = [code && `code: ${code}`, side && `side: ${side}`, body?.reg && `registration: ${body.reg}`, message || (!code ? apiErrorMessage(err) : '')].filter(Boolean).join('\n')
  if (!code) return { side, what: t('nodes.errors.unknown'), fix: t('nodes.errorFix.unknown'), reg: body?.reg ?? '', technical }
  return {
    side,
    what: t(`nodes.errors.${code}`),
    fix: te(`nodes.errorFix.${code}`) ? t(`nodes.errorFix.${code}`) : t('nodes.errorFix.unknown'),
    reg: body?.reg ?? '',
    technical,
  }
}

async function copyTechnical() {
  if (!error.value) return
  try {
    await navigator.clipboard.writeText(error.value.technical)
    toast.add({ severity: 'success', summary: t('nodes.errorCopied'), life: 4000 })
  } catch {
    toast.add({ severity: 'warn', summary: error.value.technical, life: 10000 })
  }
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
    error.value = shownError(err)
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
          <div v-if="error" class="add-node-error" role="alert">
            <div class="add-node-error__head">
              <span class="add-node-error__icon" aria-hidden="true"><i :class="SIDE_ICON[error.side]" /></span>
              <b>{{ error.side ? t(`nodes.errorSide.${error.side}`) : t('nodes.errorSide.unknown') }}</b>
            </div>
            <p class="add-node-error__what">{{ error.what }}</p>
            <div class="add-node-error__fix">
              <span class="add-node-error__label"><i class="pi pi-wrench" aria-hidden="true" />{{ t('nodes.errorFixTitle') }}</span>
              <p>{{ error.fix }}</p>
            </div>
            <div v-if="error.reg || error.technical" class="add-node-error__foot">
              <span v-if="error.reg">{{ t('nodes.errorRegShort') }} <code dir="ltr">{{ error.reg }}</code></span>
              <Button v-if="error.technical" type="button" :label="t('nodes.errorCopy')" icon="pi pi-copy" text size="small" class="add-node-error__copy" @click="copyTechnical" />
            </div>
          </div>
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
/* A failed registration: where (header), what happened, what to do, then the id and the technical details to copy */
.add-node-error {
  --err: var(--p-red-500, #ef4444);
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.85rem 0.95rem;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, var(--err) 35%, transparent);
  background: color-mix(in srgb, var(--err) 7%, var(--p-content-background));
}
.add-node-error__head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  color: color-mix(in srgb, var(--err) 85%, var(--p-text-color));
}
.add-node-error__icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 10px;
  color: #fff;
  background: var(--err);
}
.add-node-error__what {
  margin: 0;
  line-height: 1.7;
  color: var(--p-text-color);
}
.add-node-error__fix {
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.add-node-error__fix p {
  margin: 0.3rem 0 0;
  line-height: 1.7;
}
.add-node-error__label {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--p-primary-color);
}
.add-node-error__foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.add-node-error__foot code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-weight: 600;
  color: var(--p-text-color);
}
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
