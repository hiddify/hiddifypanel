<script setup lang="ts">
/**
 * Hiddify Manager's hexagon logo (the app icon's inverted look): a white glass tile inside a ring, with the logo on
 * it. The ring and the logo take ``color`` (the theme's colour by default), so the logo matches every theme and
 * every colour; the glass is the same picture in all of them.
 */
import glass from '@/assets/images/hiddify-hexagon-glass.png'

withDefaults(defineProps<{ color?: string }>(), { color: 'var(--p-primary-color)' })
const clip = `hexclip-${Math.random().toString(36).slice(2, 8)}`
const HEX =
  'M970.14,310.98 L970.14,713.02 A109.95,109.95 0 0 1 915.16,808.25 L566.98,1009.27 A109.95,109.95 0 0 1 457.02,1009.27 L108.84,808.25 A109.95,109.95 0 0 1 53.86,713.02 L53.86,310.98 A109.95,109.95 0 0 1 108.84,215.75 L457.02,14.73 A109.95,109.95 0 0 1 566.98,14.73 L915.16,215.75 A109.95,109.95 0 0 1 970.14,310.98 Z'
</script>

<template>
  <svg class="hiddify-logo" viewBox="0 0 1024 1024" role="img" aria-label="Hiddify" :style="{ color }">
    <defs>
      <clipPath :id="clip"><path :d="HEX" /></clipPath>
    </defs>
    <!-- the ring: the hexagon in the colour; the white glass tile sits inside it -->
    <path :d="HEX" fill="currentColor" />
    <g transform="translate(512,512) scale(0.927) translate(-512,-512)">
      <image :href="glass" width="1024" height="1024" :clip-path="`url(#${clip})`" />
    </g>
    <g transform="translate(68.7,32.4) scale(1.385)" fill="currentColor" stroke="currentColor" stroke-width="12" stroke-linejoin="round">
      <path d="M158,372 L234,328 L234,416 L283,416 L283,292 L356,249 L356,467 L283,467 L283,424 L234,424 L234,467 L158,467 Z" />
      <path d="M407,226 L482,181 L482,254 L407,254 Z" />
      <rect x="407" y="286" width="75" height="181" />
    </g>
  </svg>
</template>

<style scoped>
.hiddify-logo {
  display: block;
  flex: none;
  aspect-ratio: 1;
}
</style>
