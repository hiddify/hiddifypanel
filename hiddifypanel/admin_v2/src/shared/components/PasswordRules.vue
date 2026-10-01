<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { MIN_PASSWORD, passwordRules } from '@/shared/utils/password-strength'

/** Live checklist of what a strong password needs. */
const props = defineProps<{ password: string; avoid?: (string | null | undefined)[] }>()
const { t } = useI18n()
const rules = computed(() => passwordRules(props.password, props.avoid ?? []))
</script>

<template>
  <ul class="pw-rules" :aria-label="t('passwordRules.label')">
    <li v-for="r in rules" :key="r.rule" :class="{ 'pw-rules__ok': r.ok }">
      <i class="pi" :class="r.ok ? 'pi-check-circle' : 'pi-circle'" />{{ t(`passwordRules.${r.rule}`, { n: MIN_PASSWORD }) }}
    </li>
  </ul>
</template>

<style scoped>
.pw-rules {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: 0.25rem 0.9rem;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.pw-rules li {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  transition: color 0.15s ease;
}
.pw-rules i {
  font-size: 0.75rem;
}
.pw-rules__ok {
  color: var(--p-green-600, #16a34a);
}
</style>
