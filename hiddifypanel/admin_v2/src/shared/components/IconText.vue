<script setup lang="ts">
/** Plain text from the server with its emoji shown as icons (see emoji-icons.ts). */
import { computed } from 'vue'
import { emojiSegments, hasEmoji } from '@/shared/utils/emoji-icons'

const props = defineProps<{ text: string | null | undefined }>()
const segments = computed(() => (hasEmoji(props.text) ? emojiSegments(props.text!) : null))
</script>

<template>
  <!-- one inline box: in a flex row (a label with badges) the icons stay in the text, not spaced as items -->
  <span v-if="segments" class="icon-text">
    <template v-for="(seg, i) in segments" :key="i">
      <template v-if="'text' in seg">{{ seg.text }}</template>
      <img v-else-if="'flag' in seg" class="ui-flag ui-flag--inline" :src="seg.url" alt="" aria-hidden="true" />
      <i v-else :class="[seg.icon, 'ui-emoji-icon', seg.tone && `ui-emoji-icon--${seg.tone}`]" aria-hidden="true" />
    </template>
  </span>
  <template v-else>{{ text }}</template>
</template>
