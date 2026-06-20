<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  text: string
}>()

const lines = computed(() => props.text.split('\n'))
</script>

<template>
  <div class="line-numbered-code">
    <table class="line-numbered-code__table">
      <tbody>
        <tr v-for="(line, index) in lines" :key="index">
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
</style>
