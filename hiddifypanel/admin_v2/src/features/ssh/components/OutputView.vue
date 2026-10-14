<template>
  <div ref="box" class="out" />
</template>

<script setup lang="ts">
/** A command's output as a terminal shows it (ANSI colors, progress lines), read-only; follows `text` as it grows. */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

const props = defineProps<{ text: string }>()
const box = ref<HTMLElement | null>(null)
let term: Terminal | null = null
let fit: FitAddon | null = null
let written = 0
let observer: ResizeObserver | null = null

function flush() {
  if (!term || props.text.length <= written) return
  term.write(props.text.slice(written))
  written = props.text.length
}

onMounted(() => {
  if (!box.value) return
  term = new Terminal({
    disableStdin: true,
    cursorBlink: false,
    convertEol: true,
    fontSize: 12,
    scrollback: 10000,
    fontFamily: '"JetBrains Mono", "Cascadia Code", Menlo, Consolas, monospace',
    theme: { background: '#0f1419', foreground: '#d7dce2', cursor: '#0f1419' },
  })
  fit = new FitAddon()
  term.loadAddon(fit)
  term.open(box.value)
  observer = new ResizeObserver(() => {
    try {
      fit?.fit()
    } catch {
      /* not laid out yet */
    }
  })
  observer.observe(box.value)
  flush()
})

watch(() => props.text, flush)

onBeforeUnmount(() => {
  observer?.disconnect()
  term?.dispose()
})
</script>

<style scoped>
.out {
  height: 100%;
  min-height: 12rem;
  border-radius: 8px;
  padding: 0.35rem;
  background: #0f1419;
  overflow: hidden;
}
</style>
