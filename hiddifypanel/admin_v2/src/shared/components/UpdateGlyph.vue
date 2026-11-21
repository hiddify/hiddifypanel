<script setup lang="ts">
/**
 * The panel update's vector icons, each alive in its own way: ``new`` an arrow rising out of a green disc with
 * sparkles, ``ok`` a check drawn into a disc, ``check`` two arrows that turn while ``spinning``, ``warn`` a triangle.
 */
/** ``tint``: the ``ok`` disc's colour (a CSS colour or var), lit from above; none: blue */
withDefaults(defineProps<{ kind: 'new' | 'ok' | 'check' | 'warn'; spinning?: boolean; size?: string; tint?: string }>(), { spinning: false, size: '1.5rem', tint: undefined })
const uid = `ug-${Math.random().toString(36).slice(2, 8)}`
</script>

<template>
  <svg class="ug" :class="[`ug--${kind}`, { 'ug--spin': spinning }]" :style="{ width: size, height: size }" viewBox="0 0 32 32" aria-hidden="true">
    <defs>
      <linearGradient :id="`${uid}-g`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#4ade80" />
        <stop offset="100%" stop-color="#16a34a" />
      </linearGradient>
      <linearGradient :id="`${uid}-b`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#60a5fa" />
        <stop offset="100%" stop-color="#2563eb" />
      </linearGradient>
      <linearGradient :id="`${uid}-w`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#fbbf24" />
        <stop offset="100%" stop-color="#f59e0b" />
      </linearGradient>
      <!-- light from above over a tinted disc -->
      <linearGradient :id="`${uid}-l`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#fff" stop-opacity="0.32" />
        <stop offset="55%" stop-color="#fff" stop-opacity="0" />
        <stop offset="100%" stop-color="#000" stop-opacity="0.12" />
      </linearGradient>
      <clipPath :id="`${uid}-c`"><circle cx="16" cy="16" r="13" /></clipPath>
    </defs>

    <!-- a new version: the arrow rises out of the disc again and again, sparkles around it -->
    <g v-if="kind === 'new'">
      <circle cx="16" cy="16" r="13" :fill="`url(#${uid}-g)`" />
      <circle cx="16" cy="16" r="13" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="0.8" />
      <g :clip-path="`url(#${uid}-c)`">
        <g class="ug__rise">
          <path d="M16 22.5V10.5M10.8 15.4 16 10.2l5.2 5.2" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
        </g>
      </g>
      <path class="ug__spark ug__spark--1" d="M27 2.5l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z" fill="#facc15" />
      <path class="ug__spark ug__spark--2" d="M3.5 22l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z" fill="#86efac" />
    </g>

    <!-- up to date: the check draws itself into the disc -->
    <g v-else-if="kind === 'ok'">
      <circle v-if="tint" cx="16" cy="16" r="13" :style="{ fill: tint }" />
      <circle cx="16" cy="16" r="13" :fill="tint ? `url(#${uid}-l)` : `url(#${uid}-b)`" />
      <path class="ug__draw" d="M10 16.4l4 4 8-8.4" fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" pathLength="1" />
    </g>

    <!-- check for updates: two arrows chasing each other round -->
    <g v-else-if="kind === 'check'" class="ug__turn">
      <path d="M25.5 13.5A10 10 0 0 0 8.2 9.6M6.5 18.5a10 10 0 0 0 17.3 3.9" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
      <path d="M8.6 4.8l-.6 5.2 5.1.8M23.4 27.2l.6-5.2-5.1-.8" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
    </g>

    <!-- could not check -->
    <g v-else>
      <path d="M16 4.5 29 27H3z" :fill="`url(#${uid}-w)`" stroke-linejoin="round" />
      <path d="M16 12.5v6.5" stroke="#fff" stroke-width="2.6" stroke-linecap="round" />
      <circle cx="16" cy="23" r="1.6" fill="#fff" />
    </g>
  </svg>
</template>

<style scoped>
.ug {
  display: block;
  flex: none;
  overflow: visible;
}
.ug__rise {
  animation: ug-rise 2.4s cubic-bezier(0.5, 0, 0.3, 1) infinite;
}
@keyframes ug-rise {
  0%,
  20% {
    transform: translateY(0);
    opacity: 1;
  }
  48% {
    transform: translateY(-16px);
    opacity: 1;
  }
  49% {
    transform: translateY(16px);
    opacity: 0;
  }
  52% {
    opacity: 1;
  }
  80%,
  100% {
    transform: translateY(0);
  }
}
.ug__spark {
  transform-box: fill-box;
  transform-origin: center;
  animation: ug-twinkle 1.8s ease-in-out infinite;
}
.ug__spark--2 {
  animation-delay: 0.9s;
}
@keyframes ug-twinkle {
  0%,
  100% {
    transform: scale(0.3) rotate(0deg);
    opacity: 0.2;
  }
  50% {
    transform: scale(1.15) rotate(45deg);
    opacity: 1;
  }
}
.ug__draw {
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: ug-draw 0.6s 0.15s cubic-bezier(0.32, 0.72, 0, 1) forwards;
}
@keyframes ug-draw {
  to {
    stroke-dashoffset: 0;
  }
}
.ug__turn {
  transform-origin: 16px 16px;
  transform-box: view-box;
  transition: transform 0.5s cubic-bezier(0.32, 0.72, 0, 1);
}
.ug--spin .ug__turn {
  animation: ug-turn 0.9s linear infinite;
}
@keyframes ug-turn {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ug__rise,
  .ug__spark,
  .ug--spin .ug__turn {
    animation: none;
  }
  .ug__draw {
    animation: none;
    stroke-dashoffset: 0;
  }
}
</style>
