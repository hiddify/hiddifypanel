<script setup lang="ts">
/**
 * The IP sheet's logo for a server whose company has no logo of its own: a rack of three servers on a network hub,
 * drawn as a vector. Their green lights blink softly, one after another, so the server looks alive.
 */
const UNITS = [4, 21, 38]
const LEDS = [15, 22, 29]
const VENTS = [36, 40.6, 45.2, 49.8]
</script>

<template>
  <svg class="srv" viewBox="0 0 64 64" role="img" aria-hidden="true">
    <!-- the links between the servers -->
    <rect class="srv__link" x="13" y="17.6" width="38" height="2.8" rx="0.6" />
    <rect class="srv__link" x="13" y="34.6" width="38" height="2.8" rx="0.6" />
    <!-- the network: a cable down to a hub, wired both ways -->
    <path class="srv__line" d="M32 51.2v4.6M14 59h12M38 59h12" />
    <rect class="srv__hub" x="26" y="55.8" width="12" height="6.4" rx="1.3" />
    <g v-for="(y, u) in UNITS" :key="y">
      <rect class="srv__unit" x="7.5" :y="y" width="49" height="13.2" rx="3.4" />
      <path class="srv__shade" :d="`M50.5 ${y + 1.6}h1.6a2.6 2.6 0 0 1 2.6 2.6v4.8a2.6 2.6 0 0 1-2.6 2.6h-1.6z`" />
      <circle
        v-for="(x, i) in LEDS"
        :key="x"
        :class="['srv__led', i === 0 ? 'srv__led--red' : 'srv__led--green']"
        :cx="x"
        :cy="y + 6.6"
        r="2.5"
        :style="i ? { animationDelay: `${(u * 2 + i) * 0.37}s` } : undefined"
      />
      <path class="srv__vent" :d="VENTS.map((x) => `M${x} ${y + 4.4}h1.8M${x} ${y + 8.8}h1.8`).join('')" />
    </g>
  </svg>
</template>

<style scoped>
.srv {
  --srv-ink: #1d1d1f;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.srv__unit {
  fill: #eaf4fd;
  stroke: var(--srv-ink);
  stroke-width: 2.2;
}
.srv__shade {
  fill: #d2e6f8;
}
.srv__link {
  fill: #4f9cf9;
  stroke: var(--srv-ink);
  stroke-width: 1.2;
}
.srv__line {
  fill: none;
  stroke: var(--srv-ink);
  stroke-width: 2.2;
  stroke-linecap: round;
}
.srv__hub {
  fill: #ffd25e;
  stroke: var(--srv-ink);
  stroke-width: 2;
}
.srv__led {
  stroke: var(--srv-ink);
  stroke-width: 1.7;
}
.srv__led--red {
  fill: #f05a5a;
}
.srv__led--green {
  fill: #9fe07b;
  animation: srv-blink 2.6s ease-in-out infinite;
}
.srv__vent {
  fill: none;
  stroke: var(--srv-ink);
  stroke-width: 2;
  stroke-linecap: round;
}
@keyframes srv-blink {
  0%,
  70%,
  100% {
    fill: #9fe07b;
  }
  80% {
    fill: #4cc63a;
  }
  88% {
    fill: #d9f7c8;
  }
}
@media (prefers-reduced-motion: reduce) {
  .srv__led--green {
    animation: none;
  }
}
</style>
