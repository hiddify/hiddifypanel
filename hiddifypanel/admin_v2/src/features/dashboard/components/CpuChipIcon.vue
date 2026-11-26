<template>
  <!-- A processor seen from above: the dark package with its pin-1 mark, the silver heat spreader with its side lugs
       and tabs, and the maker's logo printed in the middle (no product-line name). A metal gleam passes over it now and
       then. Vector on a 64-unit grid, so it is sharp at any size. -->
  <svg class="cci" viewBox="0 0 64 64" role="img" :aria-label="logo?.title ?? 'CPU'">
    <defs>
      <linearGradient :id="`${id}-pkg`" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#2b6f76" />
        <stop offset="1" stop-color="#103d43" />
      </linearGradient>
      <linearGradient :id="`${id}-ihs`" x1="0" y1="0" x2="0.35" y2="1">
        <stop offset="0" stop-color="#fbfbfc" />
        <stop offset="0.55" stop-color="#eceef1" />
        <stop offset="1" stop-color="#d9dce1" />
      </linearGradient>
      <linearGradient :id="`${id}-gleam`" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#fff" stop-opacity="0" />
        <stop offset="0.5" stop-color="#fff" stop-opacity="0.85" />
        <stop offset="1" stop-color="#fff" stop-opacity="0" />
      </linearGradient>
      <clipPath :id="`${id}-clip`"><path :d="IHS" /></clipPath>
    </defs>

    <!-- the package (substrate) and its pin-1 mark -->
    <rect x="3" y="3" width="58" height="58" rx="4.5" :fill="`url(#${id}-pkg)`" />
    <rect x="3.5" y="3.5" width="57" height="57" rx="4" fill="none" stroke="#fff" stroke-opacity="0.12" stroke-width="1" />
    <path d="M5.5 58.5v-4.2l4.2 4.2z" fill="#d6b25e" />

    <!-- the heat spreader: a soft shadow under it, then the metal -->
    <path :d="IHS" fill="#000" fill-opacity="0.28" transform="translate(0 1.1)" />
    <path :d="IHS" :fill="`url(#${id}-ihs)`" />
    <path :d="IHS" fill="none" stroke="#000" stroke-opacity="0.1" stroke-width="0.6" />
    <!-- the package showing through the spreader's tabs, top and bottom -->
    <rect x="23" y="8" width="7" height="2.6" rx="0.6" :fill="`url(#${id}-pkg)`" />
    <rect x="34" y="8" width="7" height="2.6" rx="0.6" :fill="`url(#${id}-pkg)`" />
    <rect x="23" y="53.4" width="7" height="2.6" rx="0.6" :fill="`url(#${id}-pkg)`" />
    <rect x="34" y="53.4" width="7" height="2.6" rx="0.6" :fill="`url(#${id}-pkg)`" />

    <!-- the maker's logo, printed on the metal -->
    <svg v-if="logo" x="19" y="19" width="26" height="26" viewBox="0 0 24 24" overflow="visible">
      <path :d="logo.path" fill="#4a4b50" />
    </svg>

    <!-- the gleam crossing the metal -->
    <g :clip-path="`url(#${id}-clip)`">
      <rect class="cci__gleam" x="-14" y="-10" width="14" height="84" :fill="`url(#${id}-gleam)`" transform="rotate(20 32 32)" />
    </g>
  </svg>
</template>

<script setup lang="ts">
import { useId } from 'vue'
import type { SimpleIcon } from 'simple-icons'

defineProps<{ logo: SimpleIcon | null }>()

const id = `cci-${useId()}`
/** The heat spreader: a rounded square, a little wider in its middle (the side lugs) */
const IHS =
  'M12.5 8h39a2.5 2.5 0 0 1 2.5 2.5V19h1.5a1 1 0 0 1 1 1v24a1 1 0 0 1-1 1H54v8.5a2.5 2.5 0 0 1-2.5 2.5h-39a2.5 2.5 0 0 1-2.5-2.5V45H8.5a1 1 0 0 1-1-1V20a1 1 0 0 1 1-1H10v-8.5A2.5 2.5 0 0 1 12.5 8z'
</script>

<style scoped>
.cci {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
  filter: drop-shadow(0 6px 10px rgb(0 0 0 / 0.28));
}
.cci__gleam {
  transform-box: view-box;
  animation: cci-gleam 4.5s ease-in-out infinite;
}
@keyframes cci-gleam {
  0%,
  55% {
    translate: 0 0;
    opacity: 0;
  }
  60% {
    opacity: 1;
  }
  85% {
    translate: 80px 0;
    opacity: 1;
  }
  90%,
  100% {
    translate: 80px 0;
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .cci__gleam {
    animation: none;
    opacity: 0;
  }
}
</style>
