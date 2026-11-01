<script setup lang="ts">
/** A country's flag (SVG), e.g. a node's location or a language; nothing when the code is unknown. */
import { computed } from 'vue'
import { flagUrl } from '@/shared/utils/flags'

const props = defineProps<{ code: string | null | undefined; label?: string }>()
const url = computed(() => flagUrl(props.code))
</script>

<template>
  <img v-if="url" class="ui-flag" :src="url" :alt="label ?? ''" :title="label" :aria-hidden="label ? undefined : 'true'" />
</template>
