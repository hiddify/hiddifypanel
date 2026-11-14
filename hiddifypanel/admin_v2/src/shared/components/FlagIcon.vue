<script setup lang="ts">
/**
 * A country's flag (SVG), e.g. a node's location or a language; nothing when the code is unknown.
 * `waving`: the flag flies like cloth in the wind (a node's location on the dashboard and the Nodes page): it falls
 * away from the pole, flaps at its flying end and is pulled flat by a gust once a loop (shared/utils/flag-wind.ts).
 * It is drawn inside an SVG as thin strips of the flag, each placed on the cloth's shape; the strips overlap, so no
 * seam shows, with one soft gradient of light and shade over them and one dark outline around the cloth. The
 * outline is vector and the flag's picture is oversampled, so nothing looks jagged, also zoomed in a little.
 */
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { flagBitmap, flagUrl } from '@/shared/utils/flags'
import { FLAG_H, FLAG_W, blow, column, windAllowed, type Column } from '@/shared/utils/flag-wind'

const props = defineProps<{ code: string | null | undefined; label?: string; waving?: boolean }>()
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
/** The oversampled picture of the flag, once it is drawn (the SVG itself until then) */
const picture = ref('')
const cols: Column[] = Array.from({ length: STRIPS + 1 }, () => ({ x: 0, top: 0, bottom: 0, shade: 0 }))
const light: Column = { x: 0, top: 0, bottom: 0, shade: 0 }
const n = (v: number) => v.toFixed(3)

function draw(t: number) {
  for (let i = 0; i <= STRIPS; i++) column(i / STRIPS, t, cols[i]!)
  // each strip is moved, squeezed and slanted onto the cloth between its two columns
  for (let i = 0; i < STRIPS; i++) {
    const l = cols[i]!
    const r = cols[i + 1]!
    const x0 = i * SW
    const a = (r.x - l.x) / SW
    const b = (r.top - l.top) / SW
    const d = (l.bottom - l.top + r.bottom - r.top) / (2 * FLAG_H)
    groups[i]?.setAttribute('transform', `matrix(${a.toFixed(5)} ${b.toFixed(5)} 0 ${d.toFixed(5)} ${n(l.x - a * x0)} ${n(l.top - b * x0)})`)
  }
  for (let j = 0; j < STOPS; j++) {
    const stop = stops[j]
    if (!stop) continue
    const { shade } = column(j / (STOPS - 1), t, light)
    stop.setAttribute('stop-color', shade < 0 ? '#fff' : '#000')
    stop.setAttribute('stop-opacity', Math.min(0.3, Math.abs(shade) * 0.34).toFixed(3))
  }
  // the outline: one path around the cloth, so it never breaks at the strips
  if (outline.value) {
    let path = `M${n(cols[0]!.x)} ${n(cols[0]!.top)}`
    for (let i = 1; i <= STRIPS; i++) path += `L${n(cols[i]!.x)} ${n(cols[i]!.top)}`
    for (let i = STRIPS; i >= 0; i--) path += `L${n(cols[i]!.x)} ${n(cols[i]!.bottom)}`
    outline.value.setAttribute('d', `${path}Z`)
  }
}

let stop: (() => void) | null = null
let seen: IntersectionObserver | null = null
function setup() {
  teardown()
  if (!props.waving || !root.value || !url.value) return
  const source = url.value
  picture.value = ''
  void flagBitmap(source, root.value.getBoundingClientRect().width || 48).then((data) => {
    if (url.value === source) picture.value = data
  })
  if (!windAllowed()) return
  draw(performance.now() / 1000)
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
      <image :id="`${uid}-img`" :href="picture || url" x="0" y="0" :width="FLAG_W" :height="FLAG_H" preserveAspectRatio="none" />
      <linearGradient :id="`${uid}-light`" gradientUnits="userSpaceOnUse" x1="0" y1="0" :x2="FLAG_W" y2="0">
        <stop v-for="j in STOPS" :key="j" :ref="(el) => (stops[j - 1] = el as SVGStopElement)" :offset="(j - 1) / (STOPS - 1)" stop-color="#000" stop-opacity="0" />
      </linearGradient>
      <!-- each strip runs on under the next one (drawn over it): no seam can show between them -->
      <clipPath v-for="i in STRIPS" :id="`${uid}-c${i}`" :key="i">
        <rect :x="(i - 1) * SW - (i === 1 ? 0 : 0.5)" y="0" :width="Math.min(SW * 1.8, FLAG_W - (i - 1) * SW) + (i === 1 ? 0 : 0.5)" :height="FLAG_H" />
      </clipPath>
    </defs>
    <g v-for="i in STRIPS" :key="i" :ref="(el) => (groups[i - 1] = el as SVGGElement)" :clip-path="`url(#${uid}-c${i})`">
      <use :href="`#${uid}-img`" />
      <rect x="0" y="0" :width="FLAG_W" :height="FLAG_H" :fill="`url(#${uid}-light)`" />
    </g>
    <path ref="outline" class="ui-flag__outline" :d="`M0 0H${FLAG_W}V${FLAG_H}H0Z`" fill="none" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
  </svg>
  <img v-else-if="url" class="ui-flag" :src="url" :alt="label ?? ''" :title="label" :aria-hidden="label ? undefined : 'true'" />
</template>

<style scoped>
.ui-flag--waving {
  overflow: visible;
  border-radius: 0;
  box-shadow: none;
  shape-rendering: geometricPrecision;
  image-rendering: auto;
}
/* The dark line around the cloth: at least a hairline, thicker on a big flag */
.ui-flag__outline {
  stroke: rgb(24 30 66 / 0.88);
  stroke-width: 0.75px;
  stroke-width: max(0.75px, 0.035em);
}
</style>
