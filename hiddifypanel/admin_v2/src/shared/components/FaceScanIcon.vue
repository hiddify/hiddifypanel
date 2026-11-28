<template>
  <!-- A face being scanned, alive: the frame's corners breathe, a light line sweeps over the face, the eyes blink.
       Drawn in currentColor on a 64-unit grid (frame 6–58), so it is sharp at any size. -->
  <span class="fsi" aria-hidden="true">
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="4.3" stroke-linecap="round" stroke-linejoin="round">
      <defs>
        <linearGradient :id="`${id}-line`" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stop-color="currentColor" stop-opacity="0" />
          <stop offset="0.5" stop-color="currentColor" stop-opacity="1" />
          <stop offset="1" stop-color="currentColor" stop-opacity="0" />
        </linearGradient>
        <linearGradient :id="`${id}-trail`" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stop-color="currentColor" stop-opacity="0" />
          <stop offset="1" stop-color="currentColor" stop-opacity="0.22" />
        </linearGradient>
        <clipPath :id="`${id}-inside`">
          <rect x="8" y="8" width="48" height="48" rx="6" />
        </clipPath>
      </defs>

      <g class="fsi__corner fsi__corner--tl"><path d="M6 20V12a6 6 0 0 1 6-6h8" /></g>
      <g class="fsi__corner fsi__corner--tr"><path d="M44 6h8a6 6 0 0 1 6 6v8" /></g>
      <g class="fsi__corner fsi__corner--br"><path d="M58 44v8a6 6 0 0 1-6 6h-8" /></g>
      <g class="fsi__corner fsi__corner--bl"><path d="M20 58h-8a6 6 0 0 1-6-6v-8" /></g>

      <g class="fsi__face">
        <path class="fsi__eye" d="M21 23.5v6" />
        <path class="fsi__eye" d="M43 23.5v6" />
        <path d="M32 23.5v12.9a2 2 0 0 1-2 2h-1.5" />
        <path class="fsi__smile" d="M23.5 41.6q8.5 5.4 17 0" />
      </g>

      <g :clip-path="`url(#${id}-inside)`" stroke="none">
        <g class="fsi__scan">
          <rect x="8" y="-10" width="48" height="10" :fill="`url(#${id}-trail)`" />
          <rect x="8" y="-1.25" width="48" height="2.5" rx="1.25" :fill="`url(#${id}-line)`" />
        </g>
      </g>
    </svg>
  </span>
</template>

<script setup lang="ts">
import { useId } from 'vue'

const id = `fsi-${useId()}`
</script>

<style scoped>
.fsi {
  display: inline-grid;
  place-items: center;
  width: 1em;
  height: 1em;
}
.fsi svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}
.fsi__corner,
.fsi__eye,
.fsi__scan,
.fsi__smile {
  transform-box: fill-box;
  transform-origin: center;
}
.fsi__corner {
  animation: fsi-breathe 2.8s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
.fsi__corner--tl {
  --dx: -1.6px;
  --dy: -1.6px;
}
.fsi__corner--tr {
  --dx: 1.6px;
  --dy: -1.6px;
}
.fsi__corner--br {
  --dx: 1.6px;
  --dy: 1.6px;
}
.fsi__corner--bl {
  --dx: -1.6px;
  --dy: 1.6px;
}
.fsi__eye {
  animation: fsi-blink 4.2s ease-in-out infinite;
}
.fsi__smile {
  animation: fsi-smile 2.8s ease-in-out infinite;
}
/* The light line: down over the face with its trail behind it, then again from the top */
.fsi__scan {
  transform-box: view-box;
  transform-origin: 0 0;
  animation: fsi-scan 2.8s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}

@keyframes fsi-breathe {
  0%,
  100% {
    translate: 0 0;
  }
  50% {
    translate: var(--dx) var(--dy);
  }
}
@keyframes fsi-blink {
  0%,
  88%,
  96%,
  100% {
    scale: 1 1;
  }
  92% {
    scale: 1 0.15;
  }
}
@keyframes fsi-smile {
  0%,
  100% {
    scale: 1;
  }
  50% {
    scale: 1.06 1.12;
  }
}
@keyframes fsi-scan {
  0% {
    translate: 0 8px;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  72% {
    translate: 0 56px;
    opacity: 1;
  }
  82%,
  100% {
    translate: 0 56px;
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .fsi * {
    animation: none !important;
  }
  .fsi__scan {
    display: none;
  }
}
</style>
