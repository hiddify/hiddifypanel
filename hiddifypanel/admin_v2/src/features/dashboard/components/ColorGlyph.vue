<script setup lang="ts">
/**
 * Small colour icons of the dashboard's node rows, drawn as vectors (sharp at any size): "info", a light-blue circle
 * with a white i, and "pencil", a real yellow pencil (eraser, metal band, wood and graphite tip).
 */
import { useId } from 'vue'

defineProps<{ name: 'info' | 'pencil' }>()
const id = useId()
</script>

<template>
  <svg v-if="name === 'info'" class="glyph" viewBox="0 0 24 24" aria-hidden="true">
    <defs>
      <linearGradient :id="`${id}-blue`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#7cc8ff" />
        <stop offset="1" stop-color="#3d9dfa" />
      </linearGradient>
    </defs>
    <circle cx="12" cy="12" r="10" :fill="`url(#${id}-blue)`" />
    <circle cx="12" cy="12" r="9.6" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="0.8" />
    <circle cx="12" cy="7.3" r="1.45" fill="#fff" />
    <rect x="10.85" y="10" width="2.3" height="7.4" rx="1.15" fill="#fff" />
  </svg>

  <svg v-else class="glyph" viewBox="0 0 24 24" aria-hidden="true">
    <!-- drawn lying down, tip to the left, then turned so the tip points down-left as a writing pencil does. Its weight
         (band and eraser) sits up-right of its box's centre, so it is moved down-left to line up optically with a
         round icon beside it -->
    <g transform="translate(-0.8 0.6) rotate(-45 12 12)">
      <!-- sharpened wood and the graphite point -->
      <path d="M1.6 12 7 8.9v6.2Z" fill="#f3c98f" />
      <path d="M1.6 12 3.9 10.7v2.6Z" fill="#3a3a3c" />
      <!-- the yellow body: three faces of the hexagon, light on top, shade below -->
      <rect x="7" y="8.9" width="11" height="2.1" fill="#ffe066" />
      <rect x="7" y="11" width="11" height="2" fill="#ffcc00" />
      <rect x="7" y="13" width="11" height="2.1" fill="#e9a600" />
      <!-- the metal band, its ridges -->
      <rect x="18" y="8.9" width="2.2" height="6.2" fill="#c7c7cc" />
      <path d="M18.75 8.9v6.2M19.45 8.9v6.2" stroke="#9a9aa0" stroke-width="0.35" />
      <!-- the pink eraser -->
      <path d="M20.2 8.9h1.3a1.4 1.4 0 0 1 1.4 1.4v3.4a1.4 1.4 0 0 1-1.4 1.4h-1.3Z" fill="#ff8fa3" />
      <!-- a thin outline holds it together -->
      <path d="M7 8.9 1.6 12 7 15.1" fill="none" stroke="#000" stroke-opacity="0.18" stroke-width="0.4" stroke-linejoin="round" />
      <rect x="7" y="8.9" width="15.9" height="6.2" rx="0.6" fill="none" stroke="#000" stroke-opacity="0.18" stroke-width="0.4" />
    </g>
  </svg>
</template>

<style scoped>
.glyph {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
  filter: drop-shadow(0 0.5px 0.6px rgb(0 0 0 / 0.18));
}
</style>
