<script setup lang="ts">
/**
 * A country's flag (SVG), e.g. a node's location or a language; nothing when the code is unknown.
 * `waving`: the flag flies like cloth in the wind (a node's location on the dashboard and the Nodes page): it falls
 * away from the pole, flaps at its flying end and is pulled flat by a gust once a loop (shared/utils/flag-wind.ts).
 * It is drawn inside an SVG as a mesh of thin triangles of the flag, each kept on the cloth's shape, with one soft
 * gradient of light and shade over them and one dark outline around the cloth. The outline is vector and the flag's
 * picture is oversampled, so nothing looks jagged, also zoomed in a little.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { flagBitmap, flagUrl } from '@/shared/utils/flags'
import { FLAG_H, FLAG_W, blow, column, windAllowed, type Column } from '@/shared/utils/flag-wind'

const props = defineProps<{ code: string | null | undefined; label?: string; waving?: boolean }>()
const url = computed(() => flagUrl(props.code))

/** Light and shade: one gradient across the whole cloth, so it is soft, never in bands */
const STOPS = 25
const uid = `flag-${useId()}`
const root = ref<SVGSVGElement | null>(null)
/** How many strips the cloth is cut into (more on a bigger flag), and how far the pieces overlap (viewBox units) */
const strips = ref(24)
const pad = ref(4)
const groups: SVGGElement[] = []
const stops: SVGStopElement[] = []
const outline = ref<SVGPathElement | null>(null)
const shape = ref<SVGPathElement | null>(null)
/** The oversampled picture of the flag, once it is drawn (the SVG itself until then) */
const picture = ref('')
const cols: Column[] = []
const light: Column = { x: 0, top: 0, bottom: 0, shade: 0 }
const n = (v: number) => v.toFixed(3)
const k = (v: number) => v.toFixed(5)

/**
 * Each strip is two triangles (a mesh): a triangle keeps its three corners on the cloth, so neighbours always meet
 * along their whole shared edge and the picture never steps. They are cut a screen pixel larger than they are, so no
 * seam shows where two meet.
 */
const triangles = computed(() => {
  const sw = FLAG_W / strips.value
  const grow = Math.min(4, 1 + (3 * pad.value) / sw)
  const cut = (pts: [number, number][]) => {
    const cx = (pts[0]![0] + pts[1]![0] + pts[2]![0]) / 3
    const cy = (pts[0]![1] + pts[1]![1] + pts[2]![1]) / 3
    return pts.map(([x, y]) => `${n(cx + (x - cx) * grow)},${n(cy + (y - cy) * grow)}`).join(' ')
  }
  const out: string[] = []
  for (let i = 0; i < strips.value; i++) {
    const x0 = i * sw
    const x1 = x0 + sw
    out.push(
      cut([
        [x0, 0],
        [x1, 0],
        [x0, FLAG_H],
      ]),
      cut([
        [x1, 0],
        [x1, FLAG_H],
        [x0, FLAG_H],
      ]),
    )
  }
  return out
})

function draw(t: number) {
  const count = strips.value
  const sw = FLAG_W / count
  for (let i = 0; i <= count; i++) column(i / count, t, (cols[i] ??= { x: 0, top: 0, bottom: 0, shade: 0 }))
  for (let i = 0; i < count; i++) {
    const l = cols[i]!
    const r = cols[i + 1]!
    const x0 = i * sw
    const a = (r.x - l.x) / sw
    const e = l.x - a * x0
    // the upper triangle: top left, top right, bottom left
    const b1 = (r.top - l.top) / sw
    groups[2 * i]?.setAttribute('transform', `matrix(${k(a)} ${k(b1)} 0 ${k((l.bottom - l.top) / FLAG_H)} ${n(e)} ${n(l.top - b1 * x0)})`)
    // the lower triangle: top right, bottom right, bottom left
    const b2 = (r.bottom - l.bottom) / sw
    groups[2 * i + 1]?.setAttribute('transform', `matrix(${k(a)} ${k(b2)} 0 ${k((r.bottom - r.top) / FLAG_H)} ${n(e)} ${n(r.top - b2 * (x0 + sw))})`)
  }
  for (let j = 0; j < STOPS; j++) {
    const stop = stops[j]
    if (!stop) continue
    const { shade } = column(j / (STOPS - 1), t, light)
    stop.setAttribute('stop-color', shade < 0 ? '#fff' : '#000')
    stop.setAttribute('stop-opacity', Math.min(0.3, Math.abs(shade) * 0.34).toFixed(3))
  }
  // the cloth's edge: one path, for the outline and to cut the picture to it
  let path = `M${n(cols[0]!.x)} ${n(cols[0]!.top)}`
  for (let i = 1; i <= count; i++) path += `L${n(cols[i]!.x)} ${n(cols[i]!.top)}`
  for (let i = count; i >= 0; i--) path += `L${n(cols[i]!.x)} ${n(cols[i]!.bottom)}`
  path += 'Z'
  outline.value?.setAttribute('d', path)
  shape.value?.setAttribute('d', path)
}

let stop: (() => void) | null = null
let seen: IntersectionObserver | null = null
async function setup() {
  teardown()
  if (!props.waving || !root.value || !url.value) return
  const source = url.value
  const width = root.value.getBoundingClientRect().width || 48
  const pixels = width * (window.devicePixelRatio || 1)
  picture.value = ''
  void flagBitmap(source, width).then((data) => {
    if (url.value === source) picture.value = data
  })
  // a strip every four screen pixels is as smooth as the eye can tell; the pieces overlap by most of a pixel
  strips.value = Math.min(48, Math.max(14, Math.ceil(pixels / 4)))
  pad.value = (0.8 * FLAG_W) / pixels
  await nextTick()
  if (!root.value || !windAllowed()) return
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
      <clipPath :id="`${uid}-shape`">
        <path ref="shape" :d="`M0 0H${FLAG_W}V${FLAG_H}H0Z`" />
      </clipPath>
      <clipPath v-for="(points, i) in triangles" :id="`${uid}-t${i}`" :key="i">
        <polygon :points="points" />
      </clipPath>
    </defs>
    <g :clip-path="`url(#${uid}-shape)`">
      <g v-for="(_, i) in triangles" :key="i" :ref="(el) => (groups[i] = el as SVGGElement)" :clip-path="`url(#${uid}-t${i})`">
        <use :href="`#${uid}-img`" />
        <rect x="0" y="0" :width="FLAG_W" :height="FLAG_H" :fill="`url(#${uid}-light)`" />
      </g>
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
