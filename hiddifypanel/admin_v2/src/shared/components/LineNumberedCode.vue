<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  text: string
  highlightLine?: number
}>()

const lines = computed(() => props.text.split('\n'))
</script>

<template>
  <div class="line-numbered-code">
    <table class="line-numbered-code__table">
      <tbody>
        <tr
          v-for="(line, index) in lines"
          :key="index"
          :class="{ 'line-numbered-code__row--highlight': highlightLine === index + 1 }"
        >
          <td class="line-numbered-code__gutter">{{ index + 1 }}</td>
          <td class="line-numbered-code__line">
            <code>{{ line || ' ' }}</code>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.line-numbered-code {
  overflow: auto;
  user-select: text;
  font-size: 0.75rem;
  line-height: 1.4;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
}

.line-numbered-code__table {
  width: 100%;
  border-collapse: collapse;
}

.line-numbered-code__gutter {
  width: 2.5rem;
  min-width: 2.5rem;
  padding: 0 0.5rem;
  text-align: right;
  color: var(--text-secondary-color, #6b7280);
  user-select: none;
  vertical-align: top;
  border-right: 1px solid var(--surface-border, #e5e7eb);
}

.line-numbered-code__line {
  padding: 0 0.75rem;
  white-space: pre;
  vertical-align: top;
}

.line-numbered-code__line code {
  font-family: inherit;
  white-space: pre;
}

.line-numbered-code__row--highlight .line-numbered-code__gutter,
.line-numbered-code__row--highlight .line-numbered-code__line {
  background: color-mix(in srgb, var(--p-red-500, #ef4444) 12%, transparent);
}
</style>
