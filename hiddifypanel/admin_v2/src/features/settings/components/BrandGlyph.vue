<script setup lang="ts">
/**
 * Vector logos of the proxy cores, for their select options (option-icons.ts `brand`): XRay's four-pointed star
 * (Project X's logo, redrawn from its geometry: four quarters split by a thin cross, each turned 90°) and Hiddify's
 * hexagon with the Hiddify mark (the app icon's shapes).
 */
import { useId } from 'vue'

defineProps<{ name: 'xray' | 'hiddify' }>()
const id = useId()

const XRAY = 'M11.26 0 11.26 11.26 2.37 11.26 8.42 8.42ZM24 11.26 12.74 11.26 12.74 2.37 15.58 8.42ZM12.74 24 12.74 12.74 21.63 12.74 15.58 15.58ZM0 12.74 11.26 12.74 11.26 21.63 8.42 15.58Z'
/** Hiddify's hexagon (rounded corners) and mark, on a 1024 grid as in the app icon */
const HEX =
  'M970.14,310.98 L970.14,713.02 A109.95,109.95 0 0 1 915.16,808.25 L566.98,1009.27 A109.95,109.95 0 0 1 457.02,1009.27 L108.84,808.25 A109.95,109.95 0 0 1 53.86,713.02 L53.86,310.98 A109.95,109.95 0 0 1 108.84,215.75 L457.02,14.73 A109.95,109.95 0 0 1 566.98,14.73 L915.16,215.75 A109.95,109.95 0 0 1 970.14,310.98 Z'
</script>

<template>
  <svg v-if="name === 'xray'" class="ui-brand ui-brand--xray" viewBox="0 0 24 24" aria-hidden="true">
    <path :d="XRAY" fill="currentColor" />
  </svg>
  <svg v-else class="ui-brand" viewBox="0 0 1024 1024" aria-hidden="true">
    <defs>
      <linearGradient :id="`${id}-hex`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#5b9dff" />
        <stop offset="1" stop-color="#2563eb" />
      </linearGradient>
    </defs>
    <path :d="HEX" :fill="`url(#${id}-hex)`" />
    <g transform="translate(68.7,32.4) scale(1.385)" fill="#fff" stroke="#fff" stroke-width="12" stroke-linejoin="round">
      <path d="M158,372 L234,328 L234,416 L283,416 L283,292 L356,249 L356,467 L283,467 L283,424 L234,424 L234,467 L158,467 Z" />
      <path d="M407,226 L482,181 L482,254 L407,254 Z" />
      <rect x="407" y="286" width="75" height="181" />
    </g>
  </svg>
</template>
