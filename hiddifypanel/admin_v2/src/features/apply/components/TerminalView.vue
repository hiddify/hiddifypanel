<script setup lang="ts">
/** A log like a console: colours, follow the end, copy. `spans` are appended by the owner. */
import { nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import type { AnsiSpan } from '@/shared/utils/ansi'

const props = defineProps<{ spans: AnsiSpan[]; height?: string; empty?: string }>()
const { t } = useI18n()
const toast = useToast()

const box = ref<HTMLElement | null>(null)
const follow = ref(true)
const wrap = ref(true)

function atEnd(): boolean {
  const el = box.value
  return !el || el.scrollTop + el.clientHeight >= el.scrollHeight - 40
}
function onScroll() {
  follow.value = atEnd()
}
function toEnd() {
  const el = box.value
  if (el) el.scrollTop = el.scrollHeight
  follow.value = true
}

watch(
  () => props.spans.length,
  async () => {
    if (!follow.value) return
    await nextTick()
    toEnd()
  },
)

async function copy() {
  try {
    await navigator.clipboard.writeText(props.spans.map((s) => s.text).join(''))
    toast.add({ severity: 'success', summary: t('apply.log.copied'), life: 1800 })
  } catch {
    /* clipboard blocked */
  }
}
defineExpose({ toEnd })
</script>

<template>
  <div class="term">
    <div class="term__bar">
      <span class="term__dots" aria-hidden="true"><i /><i /><i /></span>
      <span class="term__title">{{ t('apply.log.terminal') }}</span>
      <Button :icon="wrap ? 'pi pi-align-left' : 'pi pi-arrows-h'" text rounded size="small" severity="secondary" :aria-label="t('apply.log.wrap')" v-tooltip.top="t('apply.log.wrap')" @click="wrap = !wrap" />
      <Button icon="pi pi-copy" text rounded size="small" severity="secondary" :aria-label="t('common.copy')" v-tooltip.top="t('common.copy')" :disabled="!spans.length" @click="copy" />
    </div>
    <div ref="box" class="term__body" :style="{ height: height ?? '24rem' }" @scroll.passive="onScroll">
      <pre dir="ltr" :class="{ 'term__pre--nowrap': !wrap }"><template v-if="spans.length"><span v-for="(s, i) in spans" :key="i" :class="s.cls">{{ s.text }}</span></template><span v-else class="term__empty">{{ empty ?? t('apply.log.empty') }}</span></pre>
    </div>
    <Transition name="term-jump">
      <button v-if="!follow" type="button" class="term__jump" @click="toEnd"><i class="pi pi-arrow-down" />{{ t('apply.log.follow') }}</button>
    </Transition>
  </div>
</template>

<style scoped>
.term {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  background: #0d1117;
  border: 1px solid #1f2733;
  color: #d6dde6;
}
.term__bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.5rem 0.25rem 0.85rem;
  background: #161b22;
  border-bottom: 1px solid #1f2733;
}
.term__dots {
  display: inline-flex;
  gap: 0.3rem;
}
.term__dots i {
  width: 0.62rem;
  height: 0.62rem;
  border-radius: 50%;
  background: #ff5f56;
}
.term__dots i:nth-child(2) {
  background: #ffbd2e;
}
.term__dots i:nth-child(3) {
  background: #27c93f;
}
.term__title {
  flex: 1;
  margin-inline-start: 0.4rem;
  font-size: 0.74rem;
  letter-spacing: 0.04em;
  color: #7d8896;
}
.term__body {
  overflow: auto;
  padding: 0.7rem 0.85rem;
}
.term__body pre {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.76rem;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  text-align: start;
}
.term__body .term__pre--nowrap {
  white-space: pre;
  overflow-wrap: normal;
}
.term__empty {
  color: #6b7686;
}
.term__body :deep(.bold) {
  font-weight: 700;
}
.term__body :deep(.fg-red) { color: #ff6b6b; }
.term__body :deep(.fg-green) { color: #4ade80; }
.term__body :deep(.fg-yellow) { color: #facc15; }
.term__body :deep(.fg-blue) { color: #60a5fa; }
.term__body :deep(.fg-magenta) { color: #e879f9; }
.term__body :deep(.fg-cyan) { color: #22d3ee; }
.term__body :deep(.fg-white) { color: #f1f5f9; }
.term__body :deep(.fg-black) { color: #64748b; }
.term__body :deep(.fg-bright-red) { color: #ff8787; }
.term__body :deep(.fg-bright-green) { color: #86efac; }
.term__body :deep(.fg-bright-yellow) { color: #fde047; }
.term__body :deep(.fg-bright-blue) { color: #93c5fd; }
.term__body :deep(.fg-bright-magenta) { color: #f0abfc; }
.term__body :deep(.fg-bright-cyan) { color: #67e8f9; }
.term__body :deep(.fg-bright-white) { color: #fff; }
.term__body :deep(.fg-bright-black) { color: #94a3b8; }
.term__jump {
  position: absolute;
  inset-inline-end: 1rem;
  bottom: 0.9rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.75rem;
  border: 0;
  border-radius: 999px;
  font: inherit;
  font-size: 0.76rem;
  font-weight: 600;
  color: #0d1117;
  background: #58a6ff;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}
.term-jump-enter-active,
.term-jump-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}
.term-jump-enter-from,
.term-jump-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
