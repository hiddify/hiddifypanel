<script setup lang="ts">
/**
 * A country's flag (SVG), e.g. a node's location or a language; nothing when the code is unknown.
 * `waving`: the flag waves in a soft wind (a node's location on the dashboard and the Nodes page): it is cut into thin
 * strips that rise and fall one after another, more the further they are from the pole, with a light that follows
 * the wave.
 */
import { computed } from 'vue'
import { flagUrl } from '@/shared/utils/flags'

const props = defineProps<{ code: string | null | undefined; label?: string; waving?: boolean }>()
const url = computed(() => flagUrl(props.code))
const STRIPS = 12
</script>

<template>
  <span
    v-if="url && waving"
    class="ui-flag ui-flag--waving"
    role="img"
    :aria-label="label || undefined"
    :title="label"
    :aria-hidden="label ? undefined : 'true'"
    :style="{ '--flag-url': `url(${url})`, '--n': STRIPS }"
  >
    <span v-for="i in STRIPS" :key="i" class="ui-flag__strip" :style="{ '--i': i - 1 }" />
  </span>
  <img v-else-if="url" class="ui-flag" :src="url" :alt="label ?? ''" :title="label" :aria-hidden="label ? undefined : 'true'" />
</template>

<style scoped>
.ui-flag--waving {
  display: inline-flex;
  /* the pole is on the left whatever the page's direction, and the strips must stay in the flag's order */
  direction: ltr;
  overflow: visible;
  border-radius: 0;
  box-shadow: none;
  /* the thin outline of a still flag, drawn around the moving strips */
  filter: drop-shadow(0 0 0.5px color-mix(in srgb, var(--p-text-color) 35%, transparent));
}
.ui-flag__strip {
  /* how far this strip moves: nothing at the pole, the most at the far end */
  --amp: calc(var(--i) / (var(--n) - 1) * 0.085em);
  flex: 1 0 0;
  height: 100%;
  margin-right: -0.35px; /* no hairline gaps between the strips */
  background-image: var(--flag-url);
  background-repeat: no-repeat;
  background-size: calc(var(--n) * 100%) 100%;
  background-position: calc(var(--i) * 100% / (var(--n) - 1)) 0;
  animation: ui-flag-wave 2.8s ease-in-out infinite;
  /* each strip a little behind the one before it: the wave runs from the pole to the end */
  animation-delay: calc((var(--i) - var(--n)) * 0.14s);
  will-change: transform;
}
.ui-flag__strip:first-child {
  border-top-left-radius: 2px;
  border-bottom-left-radius: 2px;
}
.ui-flag__strip:last-child {
  margin-right: 0;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
}
@keyframes ui-flag-wave {
  0%,
  100% {
    transform: translateY(calc(var(--amp) * -1));
    filter: brightness(1.06);
  }
  50% {
    transform: translateY(var(--amp));
    filter: brightness(0.9);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ui-flag__strip {
    animation: none;
  }
}
</style>
