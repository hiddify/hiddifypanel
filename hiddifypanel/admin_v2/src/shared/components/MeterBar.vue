<template>
  <div
    class="mbar"
    dir="ltr"
    :class="[`mbar--${tone}`, `mbar--${size}`]"
    role="meter"
    :aria-label="label"
    :aria-valuenow="used"
    :aria-valuemin="0"
    :aria-valuemax="max ?? undefined"
    :aria-valuetext="text"
  >
    <!-- Text over the empty part -->
    <span class="mbar__text" dir="ltr">{{ text }}</span>
    <!-- Same text, clipped to the filled part, in the fill's contrast color -->
    <span class="mbar__fill" :style="{ width: `${percent}%` }">
      <span class="mbar__text mbar__text--on-fill" dir="ltr">{{ text }}</span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * Glossy progress bar with its text inside (e.g. "8 / 10"): green up to 50%, yellow above, red from 80%;
 * striped when there is no limit. Used for admin limits and user usage.
 */
const props = withDefaults(defineProps<{ used: number; max: number | null | undefined; text: string; label?: string; size?: 'xs' | 'sm' | 'md' | 'lg' }>(), {
  label: undefined,
  size: 'md',
})

const tone = computed(() => {
  if (!props.max) return 'none'
  const ratio = props.used / props.max
  return ratio >= 0.8 ? 'danger' : ratio > 0.5 ? 'warn' : 'ok'
})

// A sliver stays visible once anything is used, so 1 of 1000 still shows.
const percent = computed(() => (props.max ? (props.used > 0 ? Math.max(4, Math.min(100, (props.used * 100) / props.max)) : 0) : 0))
</script>

<style scoped>
.mbar {
  --fill: linear-gradient(90deg, #34d399, #10b981 55%, #059669);
  --fill-glow: rgba(16, 185, 129, 0.45);
  --on-fill: #fff;
  /* cqw below = this bar's width, so the clipped text lines up with the one under it. */
  container-type: inline-size;
  position: relative;
  height: 1.3rem;
  border-radius: 999px;
  overflow: hidden;
  background: var(--p-content-hover-background, rgba(127, 127, 127, 0.12));
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.12);
}
.mbar--warn {
  --fill: linear-gradient(90deg, #fde047, #facc15 50%, #f59e0b);
  --fill-glow: rgba(245, 158, 11, 0.45);
  --on-fill: #422006;
}
.mbar--danger {
  --fill: linear-gradient(90deg, #fb923c, #f43f5e 55%, #e11d48);
  --fill-glow: rgba(244, 63, 94, 0.5);
}
.mbar--none {
  background: repeating-linear-gradient(
    -45deg,
    color-mix(in srgb, var(--p-primary-color) 7%, transparent) 0 6px,
    color-mix(in srgb, var(--p-primary-color) 12%, transparent) 6px 12px
  );
}
.mbar--xs {
  height: 0.95rem;
}
.mbar--xs .mbar__text {
  font-size: 0.64rem;
}
.mbar--sm {
  height: 1.15rem;
}
.mbar--lg {
  height: 1.75rem;
}
.mbar__fill {
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  overflow: hidden;
  border-radius: inherit;
  background: var(--fill);
  box-shadow: 0 0 10px -2px var(--fill-glow);
  transition: width 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}
/* Glossy top highlight */
.mbar__fill::before {
  content: '';
  position: absolute;
  inset: 0 0 50% 0;
  background: linear-gradient(rgba(255, 255, 255, 0.35), rgba(255, 255, 255, 0));
}
/* Slow sheen across the fill */
.mbar__fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, transparent 20%, rgba(255, 255, 255, 0.35) 45%, transparent 70%);
  transform: translateX(-100%);
  animation: mbar-sheen 3.2s ease-in-out infinite;
}
.mbar__text {
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  width: 100cqw;
  display: grid;
  place-items: center;
  font-size: 0.72rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
  white-space: nowrap;
  color: var(--p-text-color);
}
.mbar--lg .mbar__text {
  font-size: 0.85rem;
}
.mbar__text--on-fill {
  z-index: 1;
  color: var(--on-fill);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.18);
}
.mbar--warn .mbar__text--on-fill {
  text-shadow: none;
}
@keyframes mbar-sheen {
  0%,
  35% {
    transform: translateX(-100%);
  }
  75%,
  100% {
    transform: translateX(100%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .mbar__fill {
    transition: none;
  }
  .mbar__fill::after {
    animation: none;
    display: none;
  }
}
</style>
