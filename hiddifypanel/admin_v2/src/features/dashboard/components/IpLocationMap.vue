<script lang="ts">
import type { FeatureCollection } from 'geojson'
import type { Topology } from 'topojson-specification'

/** The world's countries (Natural Earth 1:50m, public domain, via world-atlas), loaded once, the first time a map opens. */
let countries: Promise<FeatureCollection> | null = null
function loadCountries(): Promise<FeatureCollection> {
  countries ??= Promise.all([import('topojson-client'), import('world-atlas/countries-50m.json')]).then(([topo, world]) => {
    const topology = world.default as unknown as Topology
    return topo.feature(topology, topology.objects.countries) as unknown as FeatureCollection
  })
  return countries
}
</script>

<script setup lang="ts">
/**
 * The pin before a server's place in the IP sheet, and the small map it opens: a vector map around the place the IP
 * address is located at, drawn in the browser (no map service, no tiles), sharp at any size.
 *
 * The pin breathes all the time (a ripple under its tip), so that it reads as a button. The map card springs out of
 * the pin like an iOS popover and closes on a tap outside it, on Escape or on the pin again.
 */
import { computed, nextTick, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ lat: number | null | undefined; lon: number | null | undefined; place: string; city?: string }>()
const { t } = useI18n()

/** The map's drawing size (the SVG scales it to the card) and how many kilometres it spans across. */
const W = 320
const H = 200
const SPAN_KM = 1400
const CARD_W = 320
const GAP = 10

const canMap = computed(() => typeof props.lat === 'number' && typeof props.lon === 'number')
const open = ref(false)
const trigger = ref<HTMLButtonElement>()
const card = ref<HTMLElement>()
const pos = ref({ left: 0, top: 0, width: CARD_W, ox: 0, oy: 0 })

const shapes = shallowRef<{ d: string; here: boolean }[]>([])
const dot = ref<[number, number]>([W / 2, H / 2])
const failed = ref(false)

async function draw() {
  if (!canMap.value) return
  const lat = props.lat as number
  const lon = props.lon as number
  failed.value = false
  try {
    const [{ geoMercator, geoPath, geoContains }, fc] = await Promise.all([import('d3-geo'), loadCountries()])
    // Mercator: x = scale × longitude (radians); a kilometre on the ground is 1 / cos(latitude) times longer there
    const scale = (W * 6371 * Math.cos((lat * Math.PI) / 180)) / SPAN_KM
    const projection = geoMercator()
      .center([lon, lat])
      .scale(scale)
      .translate([W / 2, H / 2])
      .clipExtent([
        [-2, -2],
        [W + 2, H + 2],
      ])
    const path = geoPath(projection).digits(1)
    shapes.value = fc.features.map((f) => ({ d: path(f) || '', here: geoContains(f, [lon, lat]) })).filter((s) => s.d)
    dot.value = (projection([lon, lat]) as [number, number] | null) ?? [W / 2, H / 2]
  } catch {
    failed.value = true
  }
}

const coords = computed(() => {
  if (!canMap.value) return ''
  const lat = props.lat as number
  const lon = props.lon as number
  return `${Math.abs(lat).toFixed(2)}° ${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? 'E' : 'W'}`
})
/** Apple Maps on Apple devices, its web page elsewhere */
const mapsUrl = computed(() => `https://maps.apple.com/?ll=${props.lat},${props.lon}&q=${encodeURIComponent(props.city || props.place)}&z=10`)

/** Centred on the sheet (in every language and direction), under the pin; above it when there is no room below. It
 * still grows out of the pin: the transform origin follows the pin. */
function position() {
  const el = trigger.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const width = Math.min(CARD_W, window.innerWidth - 24)
  const sheet = el.closest('.p-dialog')?.getBoundingClientRect()
  const centre = sheet ? sheet.left + sheet.width / 2 : window.innerWidth / 2
  const left = Math.min(Math.max(centre - width / 2, 12), window.innerWidth - width - 12)
  const height = card.value?.offsetHeight || 300
  const below = r.bottom + GAP + height <= window.innerHeight - 12
  const top = below ? r.bottom + GAP : Math.max(12, r.top - GAP - height)
  pos.value = { left, top, width, ox: r.left + r.width / 2 - left, oy: below ? -GAP : height + GAP }
}

function onOutside(e: PointerEvent) {
  const target = e.target as Node
  if (card.value?.contains(target) || trigger.value?.contains(target)) return
  open.value = false
}
/** Escape closes the map only, not the sheet under it */
function onKey(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  e.stopPropagation()
  e.preventDefault()
  open.value = false
  trigger.value?.focus()
}
function listen(on: boolean) {
  const how = on ? 'addEventListener' : 'removeEventListener'
  document[how]('pointerdown', onOutside as EventListener, true)
  window[how]('keydown', onKey as EventListener, true)
  window[how]('resize', position)
  window[how]('scroll', position, true)
}

async function toggle() {
  open.value = !open.value
}

watch(open, async (now) => {
  listen(now)
  if (!now) return
  position()
  draw()
  await nextTick()
  position()
})
watch(
  () => [props.lat, props.lon],
  () => {
    if (open.value) draw()
  },
)
onBeforeUnmount(() => listen(false))
</script>

<template>
  <button v-if="canMap" ref="trigger" type="button" class="ipmap-pin" :class="{ 'is-open': open }" :aria-label="t('dashboard.ipInfo.map.show')" :title="t('dashboard.ipInfo.map.show')" :aria-expanded="open" @click="toggle">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <ellipse class="ipmap-pin__ripple" cx="12" cy="21.6" rx="5" ry="1.6" />
      <g class="ipmap-pin__body">
        <path d="M12 1.6a7.6 7.6 0 0 0-7.6 7.6c0 5.3 6.2 11.6 7 12.4a.85.85 0 0 0 1.2 0c.8-.8 7-7.1 7-12.4A7.6 7.6 0 0 0 12 1.6Z" />
        <circle cx="12" cy="9.2" r="2.7" />
      </g>
    </svg>
  </button>
  <svg v-else class="ipmap-pin ipmap-pin--still" viewBox="0 0 24 24" aria-hidden="true">
    <g class="ipmap-pin__body">
      <path d="M12 1.6a7.6 7.6 0 0 0-7.6 7.6c0 5.3 6.2 11.6 7 12.4a.85.85 0 0 0 1.2 0c.8-.8 7-7.1 7-12.4A7.6 7.6 0 0 0 12 1.6Z" />
      <circle cx="12" cy="9.2" r="2.7" />
    </g>
  </svg>

  <Teleport to="body">
    <Transition name="ipmap">
      <div
        v-if="open"
        ref="card"
        class="ipmap"
        role="dialog"
        :aria-label="t('dashboard.ipInfo.map.title')"
        :style="{ left: `${pos.left}px`, top: `${pos.top}px`, width: `${pos.width}px`, '--ox': `${pos.ox}px`, '--oy': `${pos.oy}px` }"
      >
        <div class="ipmap__map">
          <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMid slice" role="img" :aria-label="place">
            <rect class="ipmap__water" :width="W" :height="H" />
            <g class="ipmap__lands" :style="{ transformOrigin: `${dot[0]}px ${dot[1]}px` }">
              <path v-for="(s, i) in shapes" :key="i" :d="s.d" :class="['ipmap__land', { 'ipmap__land--here': s.here }]" />
            </g>
            <g v-if="shapes.length" :transform="`translate(${dot[0]} ${dot[1]})`">
              <g class="ipmap__dot">
                <circle class="ipmap__halo" r="26" />
                <circle class="ipmap__pulse" r="10" />
                <circle class="ipmap__ring" r="8.5" />
                <circle class="ipmap__core" r="5.5" />
              </g>
            </g>
          </svg>
          <span v-if="!shapes.length && !failed" class="ipmap__wait"><i class="pi pi-spin pi-spinner" /></span>
          <span v-else-if="failed" class="ipmap__wait"><i class="pi pi-map" /></span>
          <button type="button" class="ipmap__close" :aria-label="t('common.close')" @click="open = false">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7 7 17" /></svg>
          </button>
        </div>
        <div class="ipmap__info">
          <div class="ipmap__text">
            <strong>{{ place }}</strong>
            <span dir="ltr">{{ coords }}</span>
          </div>
          <a class="ipmap__open" :href="mapsUrl" target="_blank" rel="noopener noreferrer">
            {{ t('dashboard.ipInfo.map.openInMaps') }}
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 16 16 8M9.5 8H16v6.5" /></svg>
          </a>
        </div>
        <p class="ipmap__note">{{ t('dashboard.ipInfo.map.approximate') }}</p>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* the pin: a little bigger than the text, red like Apple Maps' pins, always breathing so it reads as a button */
.ipmap-pin {
  flex: none;
  display: inline-grid;
  place-items: center;
  width: 1.05rem;
  height: 1.05rem;
  margin: -0.2rem 0 -0.1rem;
  padding: 0;
  border: 0;
  background: none;
  color: #ff3b30;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.ipmap-pin svg,
svg.ipmap-pin {
  width: 100%;
  height: 100%;
  overflow: visible;
}
.ipmap-pin__body path {
  fill: currentColor;
}
.ipmap-pin__body circle {
  fill: #fff;
}
.ipmap-pin__body {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  filter: drop-shadow(0 1px 1px rgb(255 59 48 / 0.35));
  animation: ipmap-bob 2.4s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
.ipmap-pin__ripple {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.2;
  transform-box: fill-box;
  transform-origin: center;
  animation: ipmap-ripple 2.4s cubic-bezier(0.2, 0.6, 0.3, 1) infinite;
}
.ipmap-pin--still .ipmap-pin__body {
  animation: none;
}
.ipmap-pin:hover .ipmap-pin__body,
.ipmap-pin.is-open .ipmap-pin__body {
  animation-duration: 1.2s;
}
.ipmap-pin:hover .ipmap-pin__ripple,
.ipmap-pin.is-open .ipmap-pin__ripple {
  animation-duration: 1.2s;
}
.ipmap-pin:active .ipmap-pin__body {
  transform: scale(0.88);
}
.ipmap-pin:focus-visible {
  outline: 2px solid color-mix(in srgb, #ff3b30 55%, transparent);
  outline-offset: 2px;
  border-radius: 0.35rem;
}
@keyframes ipmap-bob {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }
  45% {
    transform: translateY(-1.6px) scale(1.04);
  }
}
@keyframes ipmap-ripple {
  0% {
    opacity: 0.75;
    transform: scale(0.35);
  }
  80%,
  100% {
    opacity: 0;
    transform: scale(1.7);
  }
}

/* the map card: an iOS popover of frosted glass */
.ipmap {
  position: fixed;
  z-index: 3000;
  padding: 0.4rem;
  border-radius: 1.6rem;
  background: color-mix(in srgb, var(--p-content-background) 74%, transparent);
  -webkit-backdrop-filter: blur(28px) saturate(1.8);
  backdrop-filter: blur(28px) saturate(1.8);
  box-shadow:
    0 24px 60px -16px rgb(0 0 0 / 0.32),
    0 6px 18px -6px rgb(0 0 0 / 0.12),
    inset 0 0 0 0.5px rgb(255 255 255 / 0.55),
    0 0 0 0.5px rgb(0 0 0 / 0.08);
  color: var(--p-text-color);
  transform-origin: var(--ox) var(--oy);
}
.ipmap__map {
  position: relative;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  border-radius: 1.25rem;
  background: var(--ipmap-water);
  box-shadow: inset 0 0 0 0.5px rgb(0 0 0 / 0.08);
}
.ipmap__map > svg {
  display: block;
  width: 100%;
  height: 100%;
}
.ipmap {
  --ipmap-water: #a9d5f3;
  --ipmap-land: #f3f1ec;
  --ipmap-border: #d4cfc4;
  --ipmap-here: #fde3df;
  --ipmap-here-border: #f2a39a;
}
html.app-dark .ipmap {
  --ipmap-water: #1c2a3a;
  --ipmap-land: #3a3a3c;
  --ipmap-border: #55555a;
  --ipmap-here: #4a3432;
  --ipmap-here-border: #9a4f48;
  box-shadow:
    0 24px 60px -16px rgb(0 0 0 / 0.6),
    inset 0 0 0 0.5px rgb(255 255 255 / 0.12),
    0 0 0 0.5px rgb(0 0 0 / 0.4);
}
.ipmap__water {
  fill: var(--ipmap-water);
}
.ipmap__land {
  fill: var(--ipmap-land);
  stroke: var(--ipmap-border);
  stroke-width: 0.6;
  stroke-linejoin: round;
}
.ipmap__land--here {
  fill: var(--ipmap-here);
  stroke: var(--ipmap-here-border);
  stroke-width: 0.9;
}
/* the map settles in from a little closer, like Maps zooming onto a place */
.ipmap__lands {
  animation: ipmap-settle 0.9s cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes ipmap-settle {
  from {
    transform: scale(1.18);
    opacity: 0.4;
  }
}

/* where the server is: the location dot of Apple Maps, breathing */
.ipmap__dot {
  animation: ipmap-drop 0.6s 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.ipmap__halo {
  fill: rgb(255 59 48 / 0.14);
}
.ipmap__pulse {
  fill: rgb(255 59 48 / 0.35);
  transform-box: fill-box;
  transform-origin: center;
  animation: ipmap-pulse 2.2s cubic-bezier(0.2, 0.6, 0.3, 1) infinite;
}
.ipmap__ring {
  fill: #fff;
  filter: drop-shadow(0 1px 2px rgb(0 0 0 / 0.3));
}
.ipmap__core {
  fill: #ff3b30;
}
@keyframes ipmap-drop {
  from {
    opacity: 0;
    transform: translateY(-14px) scale(0.4);
  }
}
@keyframes ipmap-pulse {
  0% {
    opacity: 0.9;
    transform: scale(0.9);
  }
  100% {
    opacity: 0;
    transform: scale(2.6);
  }
}
.ipmap__dot {
  transform-box: fill-box;
  transform-origin: center;
}

.ipmap__wait {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--p-text-muted-color);
  font-size: 1.2rem;
}
.ipmap__close {
  position: absolute;
  top: 0.55rem;
  right: 0.55rem;
  display: grid;
  place-items: center;
  width: 1.85rem;
  height: 1.85rem;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: color-mix(in srgb, var(--p-content-background) 70%, transparent);
  -webkit-backdrop-filter: blur(16px) saturate(1.6);
  backdrop-filter: blur(16px) saturate(1.6);
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.12);
  color: var(--p-text-muted-color);
  cursor: pointer;
  transition: transform 0.2s ease;
}
.ipmap__close:active {
  transform: scale(0.9);
}
.ipmap__close svg {
  width: 0.95rem;
  height: 0.95rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
}
html[dir='rtl'] .ipmap__close {
  right: auto;
  left: 0.55rem;
}

.ipmap__info {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.7rem 0.55rem 0.2rem;
}
.ipmap__text {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}
.ipmap__text strong {
  overflow: hidden;
  font-size: 0.95rem;
  font-weight: 650;
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ipmap__text span {
  color: var(--p-text-muted-color);
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
}
html[dir='rtl'] .ipmap__text span {
  text-align: right;
}
.ipmap__open {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.42rem 0.8rem;
  border-radius: 999px;
  background: color-mix(in srgb, #007aff 12%, transparent);
  color: #007aff;
  font-size: 0.8rem;
  font-weight: 600;
  text-decoration: none;
  transition:
    transform 0.2s ease,
    background 0.2s ease;
}
html.app-dark .ipmap__open {
  background: color-mix(in srgb, #0a84ff 22%, transparent);
  color: #4da3ff;
}
.ipmap__open:hover {
  background: color-mix(in srgb, #007aff 18%, transparent);
}
.ipmap__open:active {
  transform: scale(0.95);
}
.ipmap__open svg {
  width: 0.85rem;
  height: 0.85rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
html[dir='rtl'] .ipmap__open svg {
  transform: scaleX(-1);
}
.ipmap__note {
  margin: 0;
  padding: 0.15rem 0.55rem 0.45rem;
  color: var(--p-text-muted-color);
  font-size: 0.7rem;
}

/* opening: springs out of the pin; closing: a quick, soft fade back into it */
.ipmap-enter-active {
  transition:
    opacity 0.28s ease,
    transform 0.6s cubic-bezier(0.32, 1.25, 0.4, 1);
}
.ipmap-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.22s cubic-bezier(0.4, 0, 1, 1);
}
.ipmap-enter-from {
  opacity: 0;
  transform: scale(0.35);
}
.ipmap-leave-to {
  opacity: 0;
  transform: scale(0.8);
}

@media (prefers-reduced-motion: reduce) {
  .ipmap-pin__body,
  .ipmap-pin__ripple,
  .ipmap__lands,
  .ipmap__dot,
  .ipmap__pulse {
    animation: none;
  }
  .ipmap-enter-active,
  .ipmap-leave-active {
    transition: opacity 0.2s ease;
  }
  .ipmap-enter-from,
  .ipmap-leave-to {
    transform: none;
  }
}
</style>
