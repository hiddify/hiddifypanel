<script setup lang="ts">
/**
 * A country's flag (SVG), e.g. a node's location or a language; nothing when the code is unknown.
 * `waving`: the flag waves in the wind like cloth (a node's location on the dashboard and the Nodes page). It is drawn
 * as vector inside an SVG: thin strips of the flag, each skewed along the wave so that they join into one smooth
 * surface, with light and shade that follow the folds (shared/utils/flag-wind.ts). Sharp at any size.
 */
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { flagUrl } from '@/shared/utils/flags'
import { FLAG_H, FLAG_W, blow, lift, windAllowed } from '@/shared/utils/flag-wind'

const props = defineProps<{ code: string | null | undefined; label?: string; waving?: boolean }>()
const url = computed(() => flagUrl(props.code))

const STRIPS = 32
const SW = FLAG_W / STRIPS
const uid = `flag-${useId()}`
const root = ref<SVGSVGElement | null>(null)
const groups: SVGGElement[] = []
const shades: SVGRectElement[] = []

/** The top and bottom edge of a strip (and the pole / flying end), a hairline that keeps light flags visible */
function edge(i: number): string {
  const x0 = i * SW
  const x1 = x0 + SW
  let d = `M${x0} 0.5H${x1}M${x0} ${FLAG_H - 0.5}H${x1}`
  if (i === 0) d += `M0.5 0V${FLAG_H}`
  if (i === STRIPS - 1) d += `M${FLAG_W - 0.5} 0V${FLAG_H}`
  return d
}

function draw(t: number) {
  for (let i = 0; i < STRIPS; i++) {
    const x0 = i * SW
    const y0 = lift(x0, t)
    const y1 = lift(x0 + SW, t)
    const slope = (y1 - y0) / SW
    groups[i]?.setAttribute('transform', `matrix(1 ${slope.toFixed(4)} 0 1 0 ${(y0 - slope * x0).toFixed(3)})`)
    // a fold that faces up catches the light, one that faces down is in shade
    const shade = shades[i]
    if (shade) {
      shade.setAttribute('fill', slope < 0 ? '#fff' : '#000')
      shade.setAttribute('fill-opacity', Math.min(slope < 0 ? 0.3 : 0.34, Math.abs(slope) * 1.9).toFixed(3))
    }
  }
}

let stop: (() => void) | null = null
let seen: IntersectionObserver | null = null
function setup() {
  teardown()
  if (!props.waving || !root.value || !windAllowed()) return
  draw(0)
  seen = new IntersectionObserver(([entry]) => {
    if (entry?.isIntersecting) stop ??= blow(draw)
    else {
      stop?.()
      stop = null
    }
  })
  seen.observe(root.value)
}
function teardown() {
  stop?.()
  stop = null
  seen?.disconnect()
  seen = null
}
onMounted(setup)
watch(() => [props.waving, url.value], () => requestAnimationFrame(setup))
onBeforeUnmount(teardown)
</script>

<template>
  <svg
    v-if="url && waving"
    ref="root"
    class="ui-flag ui-flag--waving"
    :viewBox="`0 0 ${FLAG_W} ${FLAG_H}`"
    preserveAspectRatio="none"
    role="img"
    :aria-label="label || undefined"
    :aria-hidden="label ? undefined : 'true'"
  >
    <title v-if="label">{{ label }}</title>
    <defs>
      <image :id="`${uid}-img`" :href="url" x="0" y="0" :width="FLAG_W" :height="FLAG_H" preserveAspectRatio="xMidYMid slice" />
      <!-- a hair wider than the strip, so no seam shows between neighbours -->
      <clipPath v-for="i in STRIPS" :id="`${uid}-c${i}`" :key="i">
        <rect :x="(i - 1) * SW - 0.4" y="-1" :width="SW + 0.8" :height="FLAG_H + 2" />
      </clipPath>
    </defs>
    <g v-for="i in STRIPS" :key="i" :ref="(el) => (groups[i - 1] = el as SVGGElement)">
      <use :href="`#${uid}-img`" :clip-path="`url(#${uid}-c${i})`" />
      <rect :ref="(el) => (shades[i - 1] = el as SVGRectElement)" :x="(i - 1) * SW" y="0" :width="SW" :height="FLAG_H" fill="#000" fill-opacity="0" />
      <path :d="edge(i - 1)" fill="none" stroke="rgb(0 0 0 / 0.16)" stroke-width="1" vector-effect="non-scaling-stroke" />
    </g>
  </svg>
  <img v-else-if="url" class="ui-flag" :src="url" :alt="label ?? ''" :title="label" :aria-hidden="label ? undefined : 'true'" />
</template>

<style scoped>
.ui-flag--waving {
  overflow: visible;
  border-radius: 0;
  box-shadow: none;
}
</style>
