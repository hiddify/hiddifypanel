<script setup lang="ts">
/**
 * A country's flag (SVG), e.g. a node's location or a language; nothing when the code is unknown.
 * `waving`: the flag waves in the wind like cloth (a node's location on the dashboard and the Nodes page). It is drawn
 * as vector inside an SVG: 48 thin strips of the flag, each skewed along the wave so that they join into one smooth
 * surface, one soft gradient of light and shade along the folds and one hairline around the cloth (shared/utils/flag-wind.ts). Sharp at any size.
 */
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { flagUrl } from '@/shared/utils/flags'
import { FLAG_H, FLAG_W, blow, lift, windAllowed } from '@/shared/utils/flag-wind'

const props = defineProps<{
  code: string | null | undefined
  label?: string
  waving?: boolean
}>()
const url = computed(() => flagUrl(props.code))

const STRIPS = 48
const SW = FLAG_W / STRIPS
/** Light and shade: one gradient across the whole cloth, so it is soft, never in bands */
const STOPS = 25
const uid = `flag-${useId()}`
const root = ref<SVGSVGElement | null>(null)
const groups: SVGGElement[] = []
const stops: SVGStopElement[] = []
const outline = ref<SVGPathElement | null>(null)
const lifts = new Float64Array(STRIPS + 1)

function draw(t: number) {
  for (let i = 0; i <= STRIPS; i++) lifts[i] = lift(i * SW, t)
  // each strip skewed so its edges sit on the wave: neighbours share their edges, one smooth surface
  for (let i = 0; i < STRIPS; i++) {
    const x0 = i * SW
    const slope = (lifts[i + 1]! - lifts[i]!) / SW
    groups[i]?.setAttribute('transform', `matrix(1 ${slope.toFixed(5)} 0 1 0 ${(lifts[i]! - slope * x0).toFixed(4)})`)
  }
  // a fold that faces up catches the light, one that faces down is in shade
  for (let j = 0; j < STOPS; j++) {
    const x = (j / (STOPS - 1)) * FLAG_W
    const slope = (lift(Math.min(FLAG_W, x + 2), t) - lift(Math.max(0, x - 2), t)) / 4
    const stop = stops[j]
    if (!stop) continue
    stop.setAttribute('stop-color', slope < 0 ? '#fff' : '#000')
    stop.setAttribute('stop-opacity', Math.min(slope < 0 ? 0.26 : 0.3, Math.abs(slope) * 1.6).toFixed(3))
  }
  // the hairline around the cloth: one path along the wave, so it never breaks at the strips
  if (outline.value) {
    let top = `M0 ${lifts[0]!.toFixed(3)}`
    let bottom = ''
    for (let i = 1; i <= STRIPS; i++) top += `L${(i * SW).toFixed(3)} ${lifts[i]!.toFixed(3)}`
    for (let i = STRIPS; i >= 0; i--) bottom += `L${(i * SW).toFixed(3)} ${(FLAG_H + lifts[i]!).toFixed(3)}`
    outline.value.setAttribute('d', `${top}${bottom}Z`)
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
watch(
  () => [props.waving, url.value],
  () => requestAnimationFrame(setup),
)
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
      <linearGradient :id="`${uid}-light`" gradientUnits="userSpaceOnUse" x1="0" y1="0" :x2="FLAG_W" y2="0">
        <stop v-for="j in STOPS" :key="j" :ref="(el) => (stops[j - 1] = el as SVGStopElement)" :offset="(j - 1) / (STOPS - 1)" stop-color="#000" stop-opacity="0" />
      </linearGradient>
      <!-- a hair wider than the strip, so no seam shows between neighbours -->
      <clipPath v-for="i in STRIPS" :id="`${uid}-c${i}`" :key="i">
        <rect :x="(i - 1) * SW - 0.5" y="-1" :width="SW + 1" :height="FLAG_H + 2" />
      </clipPath>
    </defs>
    <g v-for="i in STRIPS" :key="i" :ref="(el) => (groups[i - 1] = el as SVGGElement)" :clip-path="`url(#${uid}-c${i})`">
      <use :href="`#${uid}-img`" />
      <rect x="0" y="0" :width="FLAG_W" :height="FLAG_H" :fill="`url(#${uid}-light)`" />
    </g>
    <path ref="outline" :d="`M0 0H${FLAG_W}V${FLAG_H}H0Z`" fill="none" stroke="rgb(0 0 0 / 0.14)" stroke-width="0.75" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
  </svg>
  <img v-else-if="url" class="ui-flag" :src="url" :alt="label ?? ''" :title="label" :aria-hidden="label ? undefined : 'true'" />
</template>

<style scoped>
.ui-flag--waving {
  overflow: visible;
  border-radius: 0;
  box-shadow: none;
  shape-rendering: geometricPrecision;
  image-rendering: optimizeQuality;
}
</style>
