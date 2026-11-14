<script setup lang="ts">
/**
 * A country's flag (SVG), e.g. a node's location or a language; nothing when the code is unknown.
 * `waving`: the flag flies like cloth in the wind (a node's location on the dashboard and the Nodes page): it falls
 * away from the pole, flaps at its flying end and is pulled flat by a gust once a loop (shared/utils/flag-wind.ts).
 *
 * It is painted on a canvas at twice the screen's resolution: the flag's picture goes on in slices one canvas pixel
 * wide (half a screen pixel), each slanted and squeezed onto the cloth's shape, then one soft gradient of light and
 * shade and one dark outline around the cloth. Slices that thin leave no steps or seams, every browser draws them the
 * same way, and it stays sharp when zoomed in up to twice. The canvas is larger than the flag's box, as the flying
 * end falls below it.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { flagBitmap, flagUrl } from '@/shared/utils/flags'
import { FLAG_H, FLAG_W, REST, blow, gust, steady, windAllowed, type Column } from '@/shared/utils/flag-wind'

/** `wind`: how a waving flag flies: with a gust that pulls it flat once a loop (the default), or in a steady wind, with
 *  a sheen that runs over the cloth (the large flag of the IP sheet) */
const props = defineProps<{ code: string | null | undefined; label?: string; waving?: boolean; wind?: 'gust' | 'steady' }>()
const url = computed(() => flagUrl(props.code))

/** Room around the flag's box for the falling end and the outline, in flag heights (the styles below use the same) */
const ROOM = { left: 0.1, right: 0.1, top: 0.1, bottom: 0.6 }
/** Light and shade: one gradient across the whole cloth, so it is soft, never in bands */
const STOPS = 24
const OUTLINE = 'rgba(24, 30, 66, 0.88)'

const root = ref<HTMLElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
/** The picture could not be drawn: the plain flag shows instead */
const failed = ref(false)

let ctx: CanvasRenderingContext2D | null = null
let bitmap: HTMLCanvasElement | null = null
let w = 0 // the flag in canvas pixels
let h = 0
let ox = 0 // where its box starts on the canvas
let oy = 0
let line = 1
const cols: Column[] = []
const light: Column = { xt: 0, xb: 0, top: 0, bottom: 0, shade: 0 }

function draw(t: number) {
  if (!ctx || !bitmap) return
  const c = ctx
  const cloth = props.wind === 'steady' ? steady : gust
  const kx = w / FLAG_W
  const ky = h / FLAG_H
  for (let i = 0; i <= w; i++) cloth(i / w, t, (cols[i] ??= { xt: 0, xb: 0, top: 0, bottom: 0, shade: 0 }))
  c.setTransform(1, 0, 0, 1, 0, 0)
  c.globalCompositeOperation = 'source-over'
  c.clearRect(0, 0, c.canvas.width, c.canvas.height)
  // the picture, slice by slice: each one laid along the cloth's top edge, leaning and squeezed like the cloth there;
  // a slice runs on under the next one, so no seam shows
  for (let i = 0; i < w; i++) {
    const l = cols[i]!
    const r = cols[i + 1]!
    const a = (r.xt - l.xt) * kx
    const b = (r.top - l.top) * ky
    const lean = ((l.xb - l.xt + r.xb - r.xt) * kx) / (2 * h)
    const d = (l.bottom - l.top + r.bottom - r.top) / (2 * FLAG_H)
    c.setTransform(a, b, lean, d, ox + l.xt * kx - a * i, oy + l.top * ky - b * i)
    const cut = Math.min(2, w - i)
    c.drawImage(bitmap, i, 0, cut, h, i, 0, cut, h)
  }
  c.setTransform(1, 0, 0, 1, 0, 0)
  // light and shade, only on the cloth. In a steady wind the folds lie aslant, so the bands run aslant too, and a
  // narrow sheen travels over them
  c.globalCompositeOperation = 'source-atop'
  const last = cols[w]!
  const end = Math.max(last.xt, last.xb) * kx
  const aslant = props.wind === 'steady'
  const shade = c.createLinearGradient(ox, oy, ox + end, oy + (aslant ? 0.55 * h : 0))
  for (let j = 0; j < STOPS; j++) {
    const u = j / (STOPS - 1)
    const s = cloth(u, t, light).shade
    shade.addColorStop(u, `rgba(${s < 0 ? '255,255,255' : '0,0,0'},${Math.min(0.3, Math.abs(s) * 0.34).toFixed(3)})`)
  }
  c.fillStyle = shade
  c.fillRect(0, 0, c.canvas.width, c.canvas.height)
  if (aslant) {
    const at = ((t / 1.6) % 1) * 1.3 - 0.15
    const sheen = c.createLinearGradient(ox, oy, ox + end, oy + 0.55 * h)
    const stopAt = (v: number) => Math.min(1, Math.max(0, v))
    sheen.addColorStop(stopAt(at - 0.09), 'rgba(255,255,255,0)')
    sheen.addColorStop(stopAt(at), 'rgba(255,255,255,0.3)')
    sheen.addColorStop(stopAt(at + 0.09), 'rgba(255,255,255,0)')
    c.fillStyle = sheen
    c.fillRect(0, 0, c.canvas.width, c.canvas.height)
  }
  // the outline: one line around the cloth
  c.globalCompositeOperation = 'source-over'
  const step = Math.max(1, Math.round(w / 64))
  c.beginPath()
  c.moveTo(ox + cols[0]!.xt * kx, oy + cols[0]!.top * ky)
  for (let i = step; i < w; i += step) c.lineTo(ox + cols[i]!.xt * kx, oy + cols[i]!.top * ky)
  c.lineTo(ox + last.xt * kx, oy + last.top * ky)
  c.lineTo(ox + last.xb * kx, oy + last.bottom * ky)
  for (let i = w - step; i > 0; i -= step) c.lineTo(ox + cols[i]!.xb * kx, oy + cols[i]!.bottom * ky)
  c.lineTo(ox + cols[0]!.xb * kx, oy + cols[0]!.bottom * ky)
  c.closePath()
  c.lineJoin = 'round'
  c.lineWidth = line
  c.strokeStyle = OUTLINE
  c.stroke()
}

let stop: (() => void) | null = null
let seen: IntersectionObserver | null = null
async function setup() {
  teardown()
  failed.value = false
  if (!props.waving || !root.value || !canvas.value || !url.value) return
  const source = url.value
  const box = root.value.getBoundingClientRect()
  if (!box.width || !box.height) return
  // twice the screen's pixels (less for a very large flag)
  const scale = Math.min((window.devicePixelRatio || 1) * 2, 1200 / box.width)
  w = Math.max(24, Math.round(box.width * scale))
  h = Math.max(18, Math.round(box.height * scale))
  ox = Math.round(ROOM.left * h)
  oy = Math.round(ROOM.top * h)
  line = Math.max(0.75 * scale, 0.035 * h)
  canvas.value.width = w + ox + Math.round(ROOM.right * h)
  canvas.value.height = h + oy + Math.round(ROOM.bottom * h)
  ctx = canvas.value.getContext('2d')
  try {
    bitmap = await flagBitmap(source, w, h)
  } catch {
    failed.value = true
    return
  }
  if (url.value !== source || !root.value || !ctx) return
  if (!windAllowed()) {
    draw(REST)
    return
  }
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
  () => [props.waving, props.wind, url.value],
  () => requestAnimationFrame(setup),
)
onBeforeUnmount(teardown)
</script>

<template>
  <span v-if="url && waving && !failed" ref="root" class="ui-flag ui-flag--waving" role="img" :aria-label="label || undefined" :title="label" :aria-hidden="label ? undefined : 'true'">
    <canvas ref="canvas" class="ui-flag__cloth" aria-hidden="true" />
  </span>
  <img v-else-if="url" class="ui-flag" :src="url" :alt="label ?? ''" :title="label" :aria-hidden="label ? undefined : 'true'" />
</template>

<style scoped>
.ui-flag--waving {
  position: relative;
  overflow: visible;
  border-radius: 0;
  box-shadow: none;
}
/* Larger than the flag's box (ROOM in the script): 0.1 of its height around it, 0.6 below for the falling end */
.ui-flag__cloth {
  position: absolute;
  top: -0.1em;
  left: -0.1em;
  width: calc(100% + 0.2em);
  height: 1.7em;
  pointer-events: none;
}
</style>
