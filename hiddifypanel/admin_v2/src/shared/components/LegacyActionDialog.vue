<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { legacyActionDialog } from '@/core/panelShell'
import { useLayout } from '@/core/layout/sakai/composables/layout'

/**
 * Classic system actions (status, logs, apply configs, update, reinstall, restart) in a
 * dialog. The page runs in an iframe: it hides its own menu there (templates/master.html)
 * and streams the action's log, and POST-only actions are submitted into the frame.
 */

const { t } = useI18n()
const { isDarkTheme } = useLayout()

const frame = ref<HTMLIFrameElement | null>(null)
const loading = ref(true)
const maximized = ref(false)
// A new name per opening, so a form submit can never target a stale frame.
const frameName = ref('')
let openCount = 0

const action = computed(() => legacyActionDialog.value)
const visible = computed({
  get: () => action.value !== null,
  set: (open: boolean) => {
    if (!open) legacyActionDialog.value = null
  },
})

function withTheme(url: string): string {
  const full = new URL(url, window.location.origin)
  // The classic UI keeps darkmode in the session; passing it keeps both UIs matched.
  full.searchParams.set('darkmode', isDarkTheme.value ? 'true' : 'false')
  return full.pathname + full.search
}

function submitInto(url: string, target: string) {
  const form = document.createElement('form')
  form.method = 'post'
  form.action = url
  form.target = target
  form.style.display = 'none'
  document.body.appendChild(form)
  form.submit()
  form.remove()
}

watch(action, async (current, previous) => {
  if (previous && previous !== current) previous.onClose?.()
  if (!current) return
  loading.value = true
  frameName.value = `legacy-action-${++openCount}`
  await nextTick() // the dialog (and its iframe) is rendered now
  if (!frame.value) return
  const url = withTheme(current.url)
  if (current.method === 'post') submitInto(url, frameName.value)
  else frame.value.src = url
})

function onLoad() {
  let location: Location | undefined
  try {
    location = frame.value?.contentWindow?.location
  } catch {
    loading.value = false // cross-origin (should not happen): nothing more to check
    return
  }
  // The first load of a fresh iframe is about:blank; wait for the real page.
  if (!location || location.href === 'about:blank') return
  loading.value = false
  // The classic page went to the new UI (e.g. after an update): show it as the whole page.
  if (/\/admin\/v2(\/|$)/.test(location.pathname)) {
    legacyActionDialog.value = null
    window.location.href = location.href
  }
}

/** The classic result page posts this when its log reaches "Finished". */
function onMessage(event: MessageEvent) {
  if (event.origin !== window.location.origin || event.source !== frame.value?.contentWindow) return
  if ((event.data as { type?: string } | null)?.type === 'hiddify-action-finished') action.value?.onFinish?.()
}
onMounted(() => window.addEventListener('message', onMessage))
onBeforeUnmount(() => window.removeEventListener('message', onMessage))

/** Only for GET pages: reloading a POST result would run the action (e.g. a reinstall) again. */
function reload() {
  const current = action.value
  if (!current || current.method !== 'get' || !frame.value) return
  loading.value = true
  frame.value.src = withTheme(current.url)
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :maximizable="true"
    :header="action?.title"
    class="legacy-action-dialog"
    :style="{ width: 'min(64rem, calc(100vw - 2rem))' }"
    :breakpoints="{ '640px': '100vw' }"
    :content-style="{ padding: 0 }"
    @maximize="maximized = true"
    @unmaximize="maximized = false"
  >
    <div class="legacy-action" :class="{ 'legacy-action--max': maximized }">
      <Transition name="legacy-action-fade">
        <div v-if="loading" class="legacy-action__loading">
          <i class="pi pi-spin pi-spinner" />
          <span>{{ t('legacy.loading') }}</span>
        </div>
      </Transition>
      <iframe
        v-if="action"
        :key="frameName"
        ref="frame"
        :name="frameName"
        class="legacy-action__frame"
        :class="{ 'legacy-action__frame--loading': loading }"
        :title="action.title"
        @load="onLoad"
      />
    </div>
    <template #footer>
      <Button v-if="action?.method === 'get'" icon="pi pi-refresh" :label="t('legacy.refresh')" severity="secondary" text @click="reload" />
      <Button :label="t('donation.close')" severity="secondary" @click="visible = false" />
    </template>
  </Dialog>
</template>

<style scoped>
.legacy-action {
  position: relative;
  height: min(70vh, 44rem);
  background: var(--p-content-background);
}
.legacy-action--max {
  height: calc(100vh - 9rem);
}
.legacy-action__frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  transition: opacity 0.25s ease;
}
.legacy-action__frame--loading {
  opacity: 0.35;
}
.legacy-action__loading {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--p-text-muted-color);
  pointer-events: none;
}
.legacy-action__loading i {
  font-size: 1.75rem;
  color: var(--p-primary-color);
}
.legacy-action-fade-enter-active,
.legacy-action-fade-leave-active {
  transition: opacity 0.2s ease;
}
.legacy-action-fade-enter-from,
.legacy-action-fade-leave-to {
  opacity: 0;
}
@media (max-width: 640px) {
  .legacy-action {
    height: calc(100dvh - 8.5rem);
  }
}
</style>
