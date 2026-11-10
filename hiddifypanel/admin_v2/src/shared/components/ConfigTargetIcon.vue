<script setup lang="ts">
/**
 * A vector mark for an additional config's app format (Auto, Share links, Xray, Hiddify / sing-box, Clash),
 * in the format's colour on a soft tile of the same colour.
 */
import { computed } from 'vue'
import type { ConfigTarget } from '@/shared/utils/additional-configs'

const props = defineProps<{ target: ConfigTarget }>()

/** Brand / theme colour of each format. */
const COLORS: Record<ConfigTarget, string> = {
  auto: '#6366f1',
  sublink: '#0ea5e9',
  xray: '#0f172a',
  'hiddify-core': '#455fe9',
  clash: '#f59e0b',
}

const color = computed(() => COLORS[props.target] ?? '#64748b')
</script>

<template>
  <span class="cti" :class="`cti--${target}`" :style="{ '--cti-color': color }" aria-hidden="true">
    <!-- Auto: stacked layers, every format at once -->
    <svg v-if="target === 'auto'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 3.2 21 8l-9 4.8L3 8z" fill="currentColor" fill-opacity=".18" />
      <path d="M3 12.2l9 4.8 9-4.8" />
      <path d="M3 16.3l9 4.8 9-4.8" />
    </svg>

    <!-- Share links: a chain link -->
    <svg v-else-if="target === 'sublink'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M10 13.5a4.5 4.5 0 0 0 6.6.4l2.9-2.9a4.6 4.6 0 0 0-6.5-6.5l-1.6 1.6" />
      <path d="M14 10.5a4.5 4.5 0 0 0-6.6-.4l-2.9 2.9a4.6 4.6 0 0 0 6.5 6.5l1.6-1.6" />
    </svg>

    <!-- Xray (Project X): the official four-pointed star, split by a thin cross -->
    <svg v-else-if="target === 'xray'" viewBox="0 0 24 24" fill="currentColor">
      <path d="M11.45 .6V11.45H.6L8.7 8.7zM12.55 .6V11.45H23.4L15.3 8.7zM11.45 23.4V12.55H.6L8.7 15.3zM12.55 23.4V12.55H23.4L15.3 15.3z" />
    </svg>

    <!-- Hiddify: the official logo -->
    <svg v-else-if="target === 'hiddify-core'" viewBox="0 0 1080 1080" fill="currentColor">
      <g transform="translate(0,1080) scale(0.1,-0.1)">
        <path
          d="M10433 9999c-49-15-2353-1401-2392-1439-18-18-43-54-55-79-21-45-21-56-21-606l0-560 27-51c15-29 46-68 69-88 83-70 2-67 1334-64l1200 3 48 25c57 29 102 76 131 139 21 46 21 46 21 1281 0 1232 0 1235-21 1280-48 104-131 161-244 166-36 2-80-1-97-7z"
        />
        <path
          d="M6455 7722c-67-24-2363-1402-2396-1439-15-15-37-48-50-73l-24-45-5-1845-5-1845-30-53c-32-59-66-91-129-125-40-21-52-22-387-25-330-3-348-2-402 18-63 24-125 79-159 142l-23 43-5 1250-5 1250-30 53c-32 58-67 92-126 122-51 26-133 35-189 20-56-15-2350-1388-2402-1438-20-19-47-58-60-86l-23-51 0-1545 0-1545 23-50c28-61 62-98 122-133l45-27 1225 0 1225 0 41 22c22 12 57 40 78 63 73 81 70 58 76 620 5 493 6 506 27 545 29 54 87 110 142 137 45 23 52 23 401 23 354 0 355 0 404-24 58-29 108-77 138-134 23-42 23-47 28-547l5-505 24-45c30-58 76-106 126-133l40-22 1225 0 1225 0 46 27c54 32 102 83 127 136 16 35 17 227 17 3552l0 3515-21 46c-60 129-213 197-339 151z"
        />
        <path
          d="M8125 6506c-66-30-131-104-150-169-13-44-15-403-15-2927 0-2524 2-2883 15-2927 18-60 80-135 139-166l41-22 1204-3c1346-3 1258-7 1344 68 25 23 54 62 68 92l24 53 0 2900c0 2821-1 2901-19 2949-23 60-76 120-130 149l-41 22-1215 2-1215 3-50-24z"
        />
      </g>
    </svg>

    <!-- Clash: the cat head -->
    <svg v-else viewBox="0 0 24 24" fill="currentColor">
      <path
        d="M4.3 3.4c.5-.3 1.1-.2 1.6.2l3.2 2.7a10.7 10.7 0 0 1 5.8 0l3.2-2.7c.5-.4 1.1-.5 1.6-.2 .5 .3 .8 .8 .8 1.4v6.3c.6 1 1 2.2 1 3.4 0 4.3-4.1 7.1-9.5 7.1S2.5 18.8 2.5 14.5c0-1.2.4-2.4 1-3.4V4.8c0-.6.3-1.1.8-1.4z"
      />
      <ellipse cx="8.6" cy="13.6" rx="1.35" ry="1.6" fill="#fff" />
      <ellipse cx="15.4" cy="13.6" rx="1.35" ry="1.6" fill="#fff" />
      <path d="M11 16.6h2l-1 1.1z" fill="#fff" />
    </svg>
  </span>
</template>

<style scoped>
.cti {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.45rem;
  color: var(--cti-color);
  background: color-mix(in srgb, var(--cti-color) 13%, transparent);
}
.cti svg {
  width: 1rem;
  height: 1rem;
}
/* Xray's mark is near-black: keep it readable in the dark theme */
html.app-dark .cti--xray {
  color: #e2e8f0;
  background: color-mix(in srgb, #e2e8f0 14%, transparent);
}
</style>
