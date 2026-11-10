<script setup lang="ts">
/**
 * A coloured vector icon for an outbound's mode (Direct, Block, WARP, ...), on a soft tile of the same colour.
 * `mode` "auto" is the "Automatic" choice of the default-outbound pickers.
 */
import { computed } from 'vue'

interface ModeMark {
  color: string
  /** SVG content in a 24×24 box, drawn with the stroke (round caps and joins). */
  paths: string[]
  circles?: [number, number, number][]
  rects?: [number, number, number, number, number][]
}

const MARKS: Record<string, ModeMark> = {
  // Sparkles: chosen for you
  auto: {
    color: '#6366f1',
    paths: ['M12 3.5l1.8 4.7 4.7 1.8-4.7 1.8L12 16.5l-1.8-4.7L5.5 10l4.7-1.8z', 'M18.5 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z'],
  },
  // Straight arrow: out of the server as it is
  direct: { color: '#10b981', paths: ['M4 12h15', 'M13.5 6.5L19 12l-5.5 5.5'] },
  // No entry
  block: { color: '#ef4444', paths: ['M6.2 6.2l11.6 11.6'], circles: [[12, 12, 8.5]] },
  // Cloud (Cloudflare WARP)
  warp: { color: '#f38020', paths: ['M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z'] },
  // A proxy server in between
  socks: {
    color: '#0ea5e9',
    paths: ['M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3', 'M12 12V8'],
    rects: [[9, 2, 6, 6, 1.5], [2, 16, 6, 6, 1.5], [16, 16, 6, 6, 1.5]],
  },
  // Onion layers (Tor)
  tor: {
    color: '#7e4798',
    paths: ['M12 21c-4 0-7-2.9-7-6.8C5 10.3 9 8 12 4c3 4 7 6.3 7 10.2 0 3.9-3 6.8-7 6.8z', 'M12 21c-2 0-3.5-2.9-3.5-6.8S11 8 12 4', 'M12 21c2 0 3.5-2.9 3.5-6.8S13 8 12 4'],
  },
  // Globe: around the filtering
  psiphon: { color: '#14b8a6', paths: ['M3.5 12h17', 'M12 3.5c2.4 2.3 3.6 5.2 3.6 8.5s-1.2 6.2-3.6 8.5c-2.4-2.3-3.6-5.2-3.6-8.5s1.2-6.2 3.6-8.5z'], circles: [[12, 12, 8.5]] },
  // Chip: a hiddify-core outbound written by hand
  core_outbound: {
    color: '#8b5cf6',
    paths: ['M9 2.5v2.5M15 2.5v2.5M9 19v2.5M15 19v2.5M2.5 9H5M2.5 15H5M19 9h2.5M19 15h2.5'],
    rects: [[5, 5, 14, 14, 2.5], [9.5, 9.5, 5, 5, 1]],
  },
  // Chain link: a hiddify-core endpoint (WireGuard, ...)
  core_endpoint: {
    color: '#0891b2',
    paths: ['M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71', 'M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71'],
  },
  // Bolt: an Xray outbound
  xray_outbound: { color: '#f59e0b', paths: ['M13 2.5L4 13.5h7.5l-1 8 9-11H12z'] },
}
const FALLBACK: ModeMark = { color: '#64748b', paths: ['M4 12h15', 'M13.5 6.5L19 12l-5.5 5.5'] }

const props = withDefaults(defineProps<{ mode: string; off?: boolean; size?: string }>(), { off: false, size: '1.75rem' })
const mark = computed(() => MARKS[props.mode] ?? FALLBACK)
</script>

<template>
  <span class="ob-mode-icon" :class="{ 'ob-mode-icon--off': off }" :style="{ '--ob-c': mark.color, width: size, height: size }" aria-hidden="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path v-for="(d, i) in mark.paths" :key="`p${i}`" :d="d" />
      <circle v-for="(c, i) in mark.circles ?? []" :key="`c${i}`" :cx="c[0]" :cy="c[1]" :r="c[2]" />
      <rect v-for="(r, i) in mark.rects ?? []" :key="`r${i}`" :x="r[0]" :y="r[1]" :width="r[2]" :height="r[3]" :rx="r[4]" />
    </svg>
  </span>
</template>

<style scoped>
.ob-mode-icon {
  flex-shrink: 0;
  display: inline-grid;
  place-items: center;
  border-radius: 30%;
  color: var(--ob-c);
  background: color-mix(in srgb, var(--ob-c) 15%, transparent);
}
.ob-mode-icon svg {
  width: 62%;
  height: 62%;
}
/* A turned-off outbound keeps its shape but loses its colour. */
.ob-mode-icon--off {
  filter: grayscale(1);
  opacity: 0.6;
}
</style>
