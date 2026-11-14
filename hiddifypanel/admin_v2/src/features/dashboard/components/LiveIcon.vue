<script setup lang="ts">
/**
 * The icons of the IP sheet, drawn as SVG in parts so that each one can come alive the way the thing it shows would:
 * the clock's hands turn, the envelope opens and a letter rises, a pen writes the language's lines, the globe turns,
 * the server's lights blink, smoke rises from the house… Named after the PrimeIcons they replace (pi-clock, …); an
 * unknown name shows that PrimeIcon, still.
 *
 * It plays while an ancestor has `is-live` (the sheet sets it while the mouse is on the icon, or for a moment after a
 * tap); with `is-tap` too it plays once through (about 2.6 s) and ends where it started. Only the parts move: the
 * icon's own size never changes.
 */
import { computed, useId } from 'vue'

const props = defineProps<{ name: string }>()

const DRAWN = new Set([
  'pi-server',
  'pi-shield',
  'pi-eye-slash',
  'pi-mobile',
  'pi-home',
  'pi-globe',
  'pi-building',
  'pi-link',
  'pi-tag',
  'pi-arrows-h',
  'pi-th-large',
  'pi-database',
  'pi-calendar-plus',
  'pi-calendar',
  'pi-history',
  'pi-sitemap',
  'pi-briefcase',
  'pi-id-card',
  'pi-flag',
  'pi-flag-fill',
  'pi-map-marker',
  'pi-map',
  'pi-clock',
  'pi-compass',
  'pi-wallet',
  'pi-language',
  'pi-user',
  'pi-envelope',
  'pi-phone',
])
/** These take 2.6 s for one round, so a tap plays them once; the others take 1.3 s and play twice */
const SLOW = new Set(['pi-globe', 'pi-history', 'pi-clock', 'pi-compass', 'pi-language', 'pi-envelope'])

const drawn = computed(() => DRAWN.has(props.name))
const taps = computed(() => (SLOW.has(props.name) ? 1 : 2))
const uid = `li-${useId()}`
</script>

<template>
  <svg v-if="drawn" class="li" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" :style="{ '--tap-n': taps }">
    <!-- the server: its three lights blink one after another -->
    <template v-if="name === 'pi-server'">
      <rect x="4" y="3.5" width="16" height="5" rx="1.5" />
      <rect x="4" y="9.5" width="16" height="5" rx="1.5" />
      <rect x="4" y="15.5" width="16" height="5" rx="1.5" />
      <path d="M11 6h5.5M11 12h5.5M11 18h5.5" opacity="0.55" />
      <circle class="p-led" cx="7.5" cy="6" r="1.1" fill="currentColor" stroke="none" />
      <circle class="p-led p-d2" cx="7.5" cy="12" r="1.1" fill="currentColor" stroke="none" />
      <circle class="p-led p-d3" cx="7.5" cy="18" r="1.1" fill="currentColor" stroke="none" />
    </template>

    <!-- the shield: the tick is drawn again and a gleam crosses it -->
    <template v-else-if="name === 'pi-shield'">
      <clipPath :id="`${uid}-c`"><path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" /></clipPath>
      <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" />
      <g :clip-path="`url(#${uid}-c)`"><path class="p-shine" d="M6 23L13 1" stroke-width="3.2" /></g>
      <path class="p-draw" pathLength="1" d="M8.8 12.2l2.2 2.2 4.4-4.6" />
    </template>

    <!-- the hidden eye: it blinks, looks around, and the slash is drawn across it -->
    <template v-else-if="name === 'pi-eye-slash'">
      <g class="p-lid">
        <path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12z" />
        <circle class="p-pupil" cx="12" cy="12" r="2.8" />
      </g>
      <path class="p-draw" pathLength="1" d="M4 4l16 16" />
    </template>

    <!-- the phone: it buzzes and a message pops up on its screen -->
    <template v-else-if="name === 'pi-mobile'">
      <g class="p-buzz">
        <rect x="7" y="2.5" width="10" height="19" rx="2.2" />
        <path d="M10.5 5h3" />
        <circle cx="12" cy="18.5" r="0.9" fill="currentColor" stroke="none" />
        <rect class="p-msg" x="9" y="8" width="6" height="3.6" rx="1" fill="currentColor" stroke="none" />
      </g>
    </template>

    <!-- the house: smoke rises from its chimney -->
    <template v-else-if="name === 'pi-home'">
      <path d="M3.5 11L12 4l8.5 7" />
      <path d="M5.5 9.5V20h13V9.5" />
      <path d="M10 20v-4.5h4V20" />
      <path d="M16 6.4V4h2v4" />
      <circle class="p-smoke" cx="17" cy="2.6" r="1" fill="currentColor" stroke="none" />
      <circle class="p-smoke p-d2" cx="17" cy="2.6" r="1" fill="currentColor" stroke="none" />
      <circle class="p-smoke p-d3" cx="17" cy="2.6" r="1" fill="currentColor" stroke="none" />
    </template>

    <!-- the globe: its meridians sweep across, as if it turned -->
    <template v-else-if="name === 'pi-globe'">
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M5.2 7.5h13.6M5.2 16.5h13.6" opacity="0.55" />
      <ellipse class="p-mer-rest" cx="12" cy="12" rx="4" ry="9" />
      <path class="p-mer" d="M12 3a9 9 0 0 1 0 18" />
      <path class="p-mer p-m2" d="M12 3a9 9 0 0 1 0 18" />
      <path class="p-mer p-m3" d="M12 3a9 9 0 0 1 0 18" />
    </template>

    <!-- the building: its windows light up one after another -->
    <template v-else-if="name === 'pi-building'">
      <path d="M4.5 21V4h9v17" />
      <path d="M13.5 9h6v12" />
      <path d="M3 21h18" />
      <g fill="currentColor" stroke="none">
        <rect class="p-win" x="6.6" y="6.6" width="1.9" height="1.9" rx="0.3" />
        <rect class="p-win p-w2" x="9.6" y="6.6" width="1.9" height="1.9" rx="0.3" />
        <rect class="p-win p-w3" x="6.6" y="10.2" width="1.9" height="1.9" rx="0.3" />
        <rect class="p-win p-w4" x="9.6" y="10.2" width="1.9" height="1.9" rx="0.3" />
        <rect class="p-win p-w5" x="6.6" y="13.8" width="1.9" height="1.9" rx="0.3" />
        <rect class="p-win p-w6" x="9.6" y="13.8" width="1.9" height="1.9" rx="0.3" />
        <rect class="p-win p-w7" x="15.6" y="12.2" width="1.9" height="1.9" rx="0.3" />
        <rect class="p-win p-w8" x="15.6" y="15.8" width="1.9" height="1.9" rx="0.3" />
      </g>
    </template>

    <!-- the link: its two rings pull apart and click back together -->
    <template v-else-if="name === 'pi-link'">
      <path class="p-ring-a" d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path class="p-ring-b" d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </template>

    <!-- the tag: it swings on its hole -->
    <template v-else-if="name === 'pi-tag'">
      <g class="p-swing">
        <path d="M12.6 3H5a2 2 0 0 0-2 2v7.6l9 9a2 2 0 0 0 2.8 0l6.8-6.8a2 2 0 0 0 0-2.8z" />
        <circle cx="7.5" cy="7.5" r="1.4" fill="currentColor" stroke="none" />
      </g>
    </template>

    <!-- the range: its two ends push outwards -->
    <template v-else-if="name === 'pi-arrows-h'">
      <path class="p-stretch" d="M4 12h16" />
      <path class="p-left" d="M7.5 8.5L4 12l3.5 3.5" />
      <path class="p-right" d="M16.5 8.5L20 12l-3.5 3.5" />
    </template>

    <!-- the route: its squares light up along the way -->
    <template v-else-if="name === 'pi-th-large'">
      <rect class="p-sq" x="4" y="4" width="7" height="7" rx="1.6" fill="currentColor" />
      <rect class="p-sq p-s2" x="13" y="4" width="7" height="7" rx="1.6" fill="currentColor" />
      <rect class="p-sq p-s3" x="13" y="13" width="7" height="7" rx="1.6" fill="currentColor" />
      <rect class="p-sq p-s4" x="4" y="13" width="7" height="7" rx="1.6" fill="currentColor" />
    </template>

    <!-- the registry: a bit of data drops in, the lid lifts and the rings flash -->
    <template v-else-if="name === 'pi-database'">
      <circle class="p-bit" cx="12" cy="1.5" r="1.1" fill="currentColor" stroke="none" />
      <ellipse class="p-lid-up" cx="12" cy="5.5" rx="7.5" ry="2.6" />
      <path d="M4.5 5.5v13c0 1.45 3.36 2.6 7.5 2.6s7.5-1.15 7.5-2.6v-13" />
      <path class="p-flash" d="M4.5 12c0 1.45 3.36 2.6 7.5 2.6s7.5-1.15 7.5-2.6" />
    </template>

    <!-- the calendar: a page is torn off and the plus turns -->
    <template v-else-if="name === 'pi-calendar-plus' || name === 'pi-calendar'">
      <rect x="3.5" y="5" width="17" height="15.5" rx="2.2" />
      <path class="p-rings" d="M8 3v4M16 3v4" />
      <path d="M3.5 10h17" />
      <rect class="p-sheet" x="5" y="11.2" width="14" height="8" rx="1" fill="currentColor" stroke="none" />
      <path v-if="name === 'pi-calendar-plus'" class="p-plus" d="M12 12.8v5M9.5 15.3h5" />
    </template>

    <!-- the history: the hands wind back a full turn -->
    <template v-else-if="name === 'pi-history'">
      <g class="p-arc">
        <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
        <path d="M3.2 3.8v3.9h3.9" />
      </g>
      <path class="p-hands" d="M12 7.5V12l3 2" />
    </template>

    <!-- the AS: the links are drawn from the top down and the networks light up -->
    <template v-else-if="name === 'pi-sitemap'">
      <rect x="9" y="3" width="6" height="4.5" rx="1.2" />
      <rect class="p-node" x="3" y="16.5" width="6" height="4.5" rx="1.2" fill="currentColor" />
      <rect class="p-node" x="15" y="16.5" width="6" height="4.5" rx="1.2" fill="currentColor" />
      <path class="p-draw" pathLength="1" d="M12 7.5V12" />
      <path class="p-draw-2" pathLength="1" d="M6 16.5V12h12v4.5" />
    </template>

    <!-- the organization: the briefcase sways as it is carried -->
    <template v-else-if="name === 'pi-briefcase'">
      <g class="p-carry">
        <path d="M9 7.5V5.6A1.6 1.6 0 0 1 10.6 4h2.8A1.6 1.6 0 0 1 15 5.6v1.9" />
        <rect x="3" y="7.5" width="18" height="12.5" rx="2.2" />
        <path d="M3 13h18" />
        <path d="M10.5 13v1.5h3V13" />
      </g>
    </template>

    <!-- the ID card: a scan line runs over it and its lines are written again -->
    <template v-else-if="name === 'pi-id-card'">
      <clipPath :id="`${uid}-c`"><rect x="2.5" y="5" width="19" height="14" rx="2.2" /></clipPath>
      <rect x="2.5" y="5" width="19" height="14" rx="2.2" />
      <circle cx="8" cy="10.8" r="2" />
      <path d="M5 16.2c.6-1.6 1.7-2.4 3-2.4s2.4.8 3 2.4" />
      <path class="p-draw" pathLength="1" d="M14 10.5h4.5" />
      <path class="p-draw-2" pathLength="1" d="M14 13.5h3" />
      <g :clip-path="`url(#${uid}-c)`"><path class="p-scan" d="M2.5 6.2h19" stroke-width="1.3" /></g>
    </template>

    <!-- the flag: it flutters on its pole -->
    <template v-else-if="name === 'pi-flag' || name === 'pi-flag-fill'">
      <path d="M5.5 21V3.5" />
      <path class="p-cloth" d="M5.5 4.5c3-1.6 5.5 1.6 8.5 0s4.5-1 5.5-.5v8.5c-1-.5-2.5-1.1-5.5.5s-5.5-1.6-8.5 0" :fill="name === 'pi-flag-fill' ? 'currentColor' : 'none'" />
    </template>

    <!-- the city: the pin drops in and bounces, its shadow following -->
    <template v-else-if="name === 'pi-map-marker'">
      <ellipse class="p-shadow" cx="12" cy="21.6" rx="3" ry="0.8" fill="currentColor" stroke="none" />
      <g class="p-pin">
        <path d="M12 20.3s-6.5-5.5-6.5-10.8a6.5 6.5 0 0 1 13 0c0 5.3-6.5 10.8-6.5 10.8z" />
        <circle cx="12" cy="9.6" r="2.3" />
      </g>
    </template>

    <!-- the region: the map folds and unfolds -->
    <template v-else-if="name === 'pi-map'">
      <path class="p-fold-l" d="M3.5 6.5L9 4.5v13l-5.5 2z" />
      <path d="M9 4.5l6 2v13l-6-2z" />
      <path class="p-fold-r" d="M15 6.5l5.5-2v13l-5.5 2z" />
    </template>

    <!-- the time zone: the clock's hands turn -->
    <template v-else-if="name === 'pi-clock'">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 4.6v1.2M19.4 12h-1.2M12 19.4v-1.2M4.6 12h1.2" opacity="0.6" />
      <path class="p-hour" d="M12 12V8.2" />
      <path class="p-minute" d="M12 12V5.8" stroke-width="1.4" />
      <circle cx="12" cy="12" r="0.9" fill="currentColor" stroke="none" />
    </template>

    <!-- the coordinates: the compass needle swings and settles -->
    <template v-else-if="name === 'pi-compass'">
      <circle cx="12" cy="12" r="9" />
      <g class="p-needle">
        <path d="M12 6.2l2.3 5.8h-4.6z" fill="currentColor" stroke="none" />
        <path d="M12 17.8l2.3-5.8h-4.6z" stroke-width="1.3" />
      </g>
      <circle cx="12" cy="12" r="0.8" fill="currentColor" stroke="none" />
    </template>

    <!-- the currency: a coin drops into the wallet -->
    <template v-else-if="name === 'pi-wallet'">
      <g class="p-coin">
        <circle cx="10.5" cy="3" r="2.5" />
        <path d="M10.5 1.9v2.2" stroke-width="1.3" />
      </g>
      <g class="p-purse">
        <path d="M3.5 9.5V6.6a2 2 0 0 1 2-2H16" />
        <rect x="3.5" y="7" width="17" height="13" rx="2.2" />
        <rect x="14.8" y="11.5" width="5.7" height="4" rx="1.2" />
        <circle cx="17" cy="13.5" r="0.8" fill="currentColor" stroke="none" />
      </g>
    </template>

    <!-- the languages: a pen writes the lines -->
    <template v-else-if="name === 'pi-language'">
      <path class="p-line-1" pathLength="1" d="M4 7h9" />
      <path class="p-line-2" pathLength="1" d="M4 11.5h12" />
      <path class="p-line-3" pathLength="1" d="M4 16h7" />
      <g class="p-pen" stroke-width="1.4">
        <path d="M0 0l.7-2.3 5-5 1.6 1.6-5 5z" />
        <path d="M4.6 -6.2l1.6 1.6" />
      </g>
    </template>

    <!-- the person: they wave -->
    <template v-else-if="name === 'pi-user'">
      <circle cx="10.5" cy="8" r="3.5" />
      <path d="M4 20c.7-3.5 3.3-5.5 6.5-5.5 1.6 0 3 .5 4.1 1.4" />
      <g class="p-arm">
        <path d="M15.5 15l3.2-4.2" />
        <circle cx="19.2" cy="10.1" r="1" fill="currentColor" stroke="none" />
      </g>
    </template>

    <!-- the email: the envelope opens, a letter rises out of it and goes back in -->
    <template v-else-if="name === 'pi-envelope'">
      <rect x="3" y="6" width="18" height="13" rx="2.2" />
      <!-- the flap is drawn first: open, it stands behind the letter; closed, the letter is still inside -->
      <path class="p-flap" d="M3.6 6.6L12 13l8.4-6.4" />
      <clipPath :id="`${uid}-c`"><rect x="0" y="-10" width="24" height="16.4" /></clipPath>
      <g :clip-path="`url(#${uid}-c)`">
        <g class="p-letter">
          <rect x="6.5" y="7.5" width="11" height="9" rx="1" />
          <path d="M8.8 10h6.4" stroke-width="1.3" />
        </g>
      </g>
    </template>

    <!-- the phone number: the handset rings and the sound comes out -->
    <template v-else-if="name === 'pi-phone'">
      <g class="p-handset">
        <path
          d="M20.5 16.2v2.6a1.8 1.8 0 0 1-2 1.8 17.6 17.6 0 0 1-7.7-2.7 17.3 17.3 0 0 1-5.3-5.3A17.6 17.6 0 0 1 2.8 4.8 1.8 1.8 0 0 1 4.6 3h2.6a1.8 1.8 0 0 1 1.8 1.5c.1.9.3 1.7.6 2.5a1.8 1.8 0 0 1-.4 1.9L8.1 10a14.2 14.2 0 0 0 5.3 5.3l1.1-1.1a1.8 1.8 0 0 1 1.9-.4c.8.3 1.6.5 2.5.6a1.8 1.8 0 0 1 1.6 1.8z"
        />
      </g>
      <path class="p-sound" d="M14.5 6.6a3.4 3.4 0 0 1 2.9 2.9" />
      <path class="p-sound p-d2" d="M14.5 3a7 7 0 0 1 6.5 6.5" />
    </template>
  </svg>
  <i v-else class="pi" :class="name" />
</template>

<style scoped>
.li {
  --n: infinite;
  display: block;
  width: 1em;
  height: 1em;
  overflow: visible;
}
.li * {
  transform-box: view-box;
}
/* a tap plays it once through and it ends where it started */
.is-tap > .li {
  --n: var(--tap-n);
}

/* --- what is hidden until it plays ------------------------------------------------------------------------------ */
.p-shine,
.p-msg,
.p-smoke,
.p-mer,
.p-bit,
.p-scan,
.p-coin,
.p-sound {
  opacity: 0;
}
.p-sq,
.p-node {
  fill-opacity: 0;
}
.p-sheet {
  fill-opacity: 0.16;
}
.p-win {
  opacity: 0.45;
}
.p-draw,
.p-draw-2,
.p-line-1,
.p-line-2,
.p-line-3 {
  stroke-dasharray: 1;
  stroke-dashoffset: 0;
}
.p-pen {
  transform: translate(11px, 16px);
}

/* --- where each part turns and swings around -------------------------------------------------------------------- */
.p-lid,
.p-buzz,
.p-mer,
.p-hour,
.p-minute,
.p-hands,
.p-arc,
.p-needle,
.p-handset,
.p-stretch {
  transform-origin: 12px 12px;
}
.p-swing {
  transform-origin: 7.5px 7.5px;
}
.p-carry {
  transform-origin: 12px 4px;
}
.p-cloth {
  transform-origin: 5.5px 8.5px;
}
.p-shadow {
  transform-origin: 12px 21.6px;
}
.p-fold-l {
  transform-origin: 9px 12px;
}
.p-fold-r {
  transform-origin: 15px 12px;
}
.p-flap {
  transform-origin: 12px 6.6px;
}
.p-arm {
  transform-origin: 15.5px 15px;
}
.p-plus {
  transform-origin: 12px 15.3px;
}
.p-sheet {
  transform-origin: 12px 11.2px;
}
.p-smoke {
  transform-origin: 17px 2.6px;
}

/* --- the motions, while the icon is alive ----------------------------------------------------------------------- */
.is-live > .li .p-led {
  animation: li-blink 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-led.p-d2 {
  animation-delay: 0.18s;
}
.is-live > .li .p-led.p-d3 {
  animation-delay: 0.36s;
}

.is-live > .li .p-shine {
  animation: li-shine 1.3s ease-out var(--n) both;
}
.is-live > .li .p-draw {
  animation: li-draw 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-draw-2 {
  animation: li-draw-late 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-lid {
  animation: li-eyelid 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-pupil {
  animation: li-look 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-buzz {
  animation: li-buzz 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-msg {
  animation: li-message 1.3s ease-out var(--n) both;
}

.is-live > .li .p-smoke {
  animation: li-smoke 1.3s ease-out var(--n) both;
}
.is-live > .li .p-smoke.p-d2 {
  animation-delay: 0.43s;
}
.is-live > .li .p-smoke.p-d3 {
  animation-delay: 0.86s;
}

.is-live > .li .p-mer-rest {
  opacity: 0;
  transition: opacity 0.2s;
}
.is-live > .li .p-mer {
  animation: li-meridian 2.6s linear var(--n) both;
}
.is-live > .li .p-mer.p-m2 {
  animation-delay: -0.87s;
}
.is-live > .li .p-mer.p-m3 {
  animation-delay: -1.73s;
}

.is-live > .li .p-win {
  animation: li-window 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-w2 {
  animation-delay: 0.08s;
}
.is-live > .li .p-w3 {
  animation-delay: 0.16s;
}
.is-live > .li .p-w4 {
  animation-delay: 0.24s;
}
.is-live > .li .p-w5 {
  animation-delay: 0.32s;
}
.is-live > .li .p-w6 {
  animation-delay: 0.4s;
}
.is-live > .li .p-w7 {
  animation-delay: 0.2s;
}
.is-live > .li .p-w8 {
  animation-delay: 0.36s;
}

.is-live > .li .p-ring-a {
  animation: li-pull-a 1.3s cubic-bezier(0.34, 1.4, 0.64, 1) var(--n) both;
}
.is-live > .li .p-ring-b {
  animation: li-pull-b 1.3s cubic-bezier(0.34, 1.4, 0.64, 1) var(--n) both;
}

.is-live > .li .p-swing {
  animation: li-swing 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-left {
  animation: li-push-left 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-right {
  animation: li-push-right 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-stretch {
  animation: li-stretch 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-sq {
  animation: li-fill 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-s2 {
  animation-delay: 0.15s;
}
.is-live > .li .p-s3 {
  animation-delay: 0.3s;
}
.is-live > .li .p-s4 {
  animation-delay: 0.45s;
}

.is-live > .li .p-bit {
  animation: li-bit 1.3s ease-in var(--n) both;
}
.is-live > .li .p-lid-up {
  animation: li-lid 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-flash {
  animation: li-flash 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-sheet {
  animation: li-tear 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-plus {
  animation: li-turn-plus 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-rings {
  animation: li-rings 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-hands {
  animation: li-rewind 2.6s cubic-bezier(0.6, 0, 0.3, 1) var(--n) both;
}
.is-live > .li .p-arc {
  animation: li-arc 2.6s ease-in-out var(--n) both;
}

.is-live > .li .p-node {
  animation: li-node 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-carry {
  animation: li-carry 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-scan {
  animation: li-scan 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-cloth {
  animation: li-flutter 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-pin {
  animation: li-drop 1.3s cubic-bezier(0.3, 0, 0.4, 1) var(--n) both;
}
.is-live > .li .p-shadow {
  animation: li-shadow 1.3s cubic-bezier(0.3, 0, 0.4, 1) var(--n) both;
}

.is-live > .li .p-fold-l {
  animation: li-fold 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-fold-r {
  animation: li-fold 1.3s ease-in-out 0.08s var(--n) both;
}

.is-live > .li .p-minute {
  animation: li-minute 2.6s linear var(--n) both;
}
.is-live > .li .p-hour {
  animation: li-hour 2.6s ease-in-out var(--n) both;
}

.is-live > .li .p-needle {
  animation: li-needle 2.6s ease-in-out var(--n) both;
}

.is-live > .li .p-coin {
  animation: li-coin 1.3s ease-in var(--n) both;
}
.is-live > .li .p-purse {
  animation: li-purse 1.3s ease-out var(--n) both;
}

.is-live > .li .p-line-1 {
  animation: li-write-1 2.6s linear var(--n) both;
}
.is-live > .li .p-line-2 {
  animation: li-write-2 2.6s linear var(--n) both;
}
.is-live > .li .p-line-3 {
  animation: li-write-3 2.6s linear var(--n) both;
}
.is-live > .li .p-pen {
  animation: li-pen 2.6s ease-in-out var(--n) both;
}

.is-live > .li .p-arm {
  animation: li-wave 1.3s ease-in-out var(--n) both;
}

.is-live > .li .p-flap {
  animation: li-flap 2.6s ease-in-out var(--n) both;
}
.is-live > .li .p-letter {
  animation: li-letter 2.6s ease-in-out var(--n) both;
}

.is-live > .li .p-handset {
  animation: li-ring 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-sound {
  animation: li-sound 1.3s ease-out var(--n) both;
}
.is-live > .li .p-sound.p-d2 {
  animation-delay: 0.15s;
}

@media (prefers-reduced-motion: reduce) {
  .is-live > .li * {
    animation: none !important;
  }
}

/* --- keyframes: each starts and ends at rest -------------------------------------------------------------------- */
@keyframes li-blink {
  0%,
  100% {
    opacity: 1;
  }
  25% {
    opacity: 0.2;
  }
  50% {
    opacity: 1;
  }
}
@keyframes li-shine {
  0% {
    opacity: 0;
    transform: translateX(-9px);
  }
  20% {
    opacity: 0.85;
  }
  60%,
  100% {
    opacity: 0;
    transform: translateX(11px);
  }
}
@keyframes li-draw {
  0% {
    stroke-dashoffset: 1;
  }
  45%,
  100% {
    stroke-dashoffset: 0;
  }
}
@keyframes li-draw-late {
  0%,
  25% {
    stroke-dashoffset: 1;
  }
  65%,
  100% {
    stroke-dashoffset: 0;
  }
}
@keyframes li-eyelid {
  0%,
  28%,
  44%,
  100% {
    transform: scaleY(1);
  }
  36% {
    transform: scaleY(0.08);
  }
}
@keyframes li-look {
  0%,
  100% {
    transform: translateX(0);
  }
  55% {
    transform: translateX(-1.7px);
  }
  80% {
    transform: translateX(1.7px);
  }
}
@keyframes li-buzz {
  0%,
  42%,
  100% {
    transform: rotate(0);
  }
  6%,
  18%,
  30% {
    transform: rotate(-9deg);
  }
  12%,
  24%,
  36% {
    transform: rotate(9deg);
  }
}
@keyframes li-message {
  0%,
  20% {
    opacity: 0;
    transform: translateY(2.5px);
  }
  40%,
  80% {
    opacity: 1;
    transform: translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateY(0);
  }
}
@keyframes li-smoke {
  0% {
    opacity: 0;
    transform: translate(0, 1px) scale(0.5);
  }
  30% {
    opacity: 0.9;
  }
  100% {
    opacity: 0;
    transform: translate(2.2px, -4.5px) scale(1.5);
  }
}
@keyframes li-meridian {
  0% {
    opacity: 0;
    transform: scaleX(1);
  }
  12%,
  88% {
    opacity: 1;
  }
  50% {
    transform: scaleX(0);
  }
  100% {
    opacity: 0;
    transform: scaleX(-1);
  }
}
@keyframes li-window {
  0%,
  100% {
    opacity: 0.45;
  }
  30%,
  60% {
    opacity: 1;
  }
}
@keyframes li-pull-a {
  0%,
  100% {
    transform: translate(0, 0);
  }
  40% {
    transform: translate(1.8px, -1.8px);
  }
  70% {
    transform: translate(0, 0);
  }
}
@keyframes li-pull-b {
  0%,
  100% {
    transform: translate(0, 0);
  }
  40% {
    transform: translate(-1.8px, 1.8px);
  }
  70% {
    transform: translate(0, 0);
  }
}
@keyframes li-swing {
  0%,
  100% {
    transform: rotate(0);
  }
  18% {
    transform: rotate(18deg);
  }
  38% {
    transform: rotate(-12deg);
  }
  58% {
    transform: rotate(7deg);
  }
  78% {
    transform: rotate(-3deg);
  }
}
@keyframes li-push-left {
  0%,
  100% {
    transform: translateX(0);
  }
  45% {
    transform: translateX(-2px);
  }
}
@keyframes li-push-right {
  0%,
  100% {
    transform: translateX(0);
  }
  45% {
    transform: translateX(2px);
  }
}
@keyframes li-stretch {
  0%,
  100% {
    transform: scaleX(1);
  }
  45% {
    transform: scaleX(1.22);
  }
}
@keyframes li-fill {
  0%,
  100% {
    fill-opacity: 0;
  }
  25% {
    fill-opacity: 0.9;
  }
  55% {
    fill-opacity: 0;
  }
}
@keyframes li-bit {
  0% {
    opacity: 0;
    transform: translateY(-2px);
  }
  15% {
    opacity: 1;
  }
  45%,
  100% {
    opacity: 0;
    transform: translateY(5px);
  }
}
@keyframes li-lid {
  0%,
  100% {
    transform: translateY(0);
  }
  25% {
    transform: translateY(-2px);
  }
  50% {
    transform: translateY(0);
  }
}
@keyframes li-flash {
  0%,
  45%,
  100% {
    opacity: 1;
  }
  60% {
    opacity: 0.25;
  }
  75% {
    opacity: 1;
  }
}
@keyframes li-tear {
  0%,
  100% {
    transform: scaleY(1);
    fill-opacity: 0.16;
  }
  35% {
    transform: scaleY(0);
    fill-opacity: 0.5;
  }
  36% {
    transform: scaleY(0);
    fill-opacity: 0;
  }
  70% {
    transform: scaleY(1);
    fill-opacity: 0.16;
  }
}
@keyframes li-turn-plus {
  0%,
  35% {
    transform: rotate(0);
  }
  70%,
  100% {
    transform: rotate(180deg);
  }
}
@keyframes li-rings {
  0%,
  30%,
  100% {
    transform: translateY(0);
  }
  15% {
    transform: translateY(-1.2px);
  }
}
@keyframes li-rewind {
  0% {
    transform: rotate(0);
  }
  75%,
  100% {
    transform: rotate(-360deg);
  }
}
@keyframes li-arc {
  0%,
  100% {
    transform: rotate(0);
  }
  35% {
    transform: rotate(-28deg);
  }
  75% {
    transform: rotate(0);
  }
}
@keyframes li-node {
  0%,
  55%,
  100% {
    fill-opacity: 0;
  }
  75% {
    fill-opacity: 0.85;
  }
}
@keyframes li-carry {
  0%,
  100% {
    transform: rotate(0) translateY(0);
  }
  25% {
    transform: rotate(-7deg) translateY(-0.6px);
  }
  50% {
    transform: rotate(5deg) translateY(0);
  }
  75% {
    transform: rotate(-2.5deg) translateY(-0.3px);
  }
}
@keyframes li-scan {
  0% {
    opacity: 0;
    transform: translateY(0);
  }
  10% {
    opacity: 0.95;
  }
  85% {
    opacity: 0.95;
    transform: translateY(11.6px);
  }
  100% {
    opacity: 0;
    transform: translateY(11.6px);
  }
}
@keyframes li-flutter {
  0%,
  100% {
    transform: skewY(0) scaleX(1);
  }
  25% {
    transform: skewY(-7deg) scaleX(0.95);
  }
  50% {
    transform: skewY(4deg) scaleX(1);
  }
  75% {
    transform: skewY(-3deg) scaleX(0.97);
  }
}
@keyframes li-drop {
  0% {
    transform: translateY(0);
  }
  18% {
    transform: translateY(-5px);
  }
  38% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-1.6px);
  }
  62%,
  100% {
    transform: translateY(0);
  }
}
@keyframes li-shadow {
  0%,
  38%,
  62%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  18% {
    transform: scale(0.45);
    opacity: 0.4;
  }
  50% {
    transform: scale(0.8);
  }
}
@keyframes li-fold {
  0%,
  100% {
    transform: scaleX(1);
  }
  35%,
  55% {
    transform: scaleX(0.15);
  }
}
@keyframes li-minute {
  to {
    transform: rotate(720deg);
  }
}
@keyframes li-hour {
  0% {
    transform: rotate(0);
  }
  80% {
    transform: rotate(60deg);
  }
  100% {
    transform: rotate(0);
  }
}
@keyframes li-needle {
  0%,
  100% {
    transform: rotate(0);
  }
  14% {
    transform: rotate(60deg);
  }
  30% {
    transform: rotate(-40deg);
  }
  46% {
    transform: rotate(24deg);
  }
  62% {
    transform: rotate(-12deg);
  }
  78% {
    transform: rotate(5deg);
  }
}
@keyframes li-coin {
  0% {
    opacity: 0;
    transform: translateY(-4px);
  }
  20% {
    opacity: 1;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(6.5px);
  }
  58%,
  100% {
    opacity: 0;
    transform: translateY(7px);
  }
}
@keyframes li-purse {
  0%,
  50%,
  100% {
    transform: translateY(0);
  }
  58% {
    transform: translateY(0.9px);
  }
  70% {
    transform: translateY(-0.3px);
  }
}
@keyframes li-write-1 {
  0% {
    stroke-dashoffset: 1;
  }
  22%,
  100% {
    stroke-dashoffset: 0;
  }
}
@keyframes li-write-2 {
  0%,
  27% {
    stroke-dashoffset: 1;
  }
  55%,
  100% {
    stroke-dashoffset: 0;
  }
}
@keyframes li-write-3 {
  0%,
  60% {
    stroke-dashoffset: 1;
  }
  84%,
  100% {
    stroke-dashoffset: 0;
  }
}
@keyframes li-pen {
  0% {
    transform: translate(4px, 7px);
  }
  22% {
    transform: translate(13px, 7px);
  }
  27% {
    transform: translate(4px, 11.5px);
  }
  55% {
    transform: translate(16px, 11.5px);
  }
  60% {
    transform: translate(4px, 16px);
  }
  84%,
  100% {
    transform: translate(11px, 16px);
  }
}
@keyframes li-wave {
  0%,
  100% {
    transform: rotate(0);
  }
  20% {
    transform: rotate(-24deg);
  }
  40% {
    transform: rotate(12deg);
  }
  60% {
    transform: rotate(-24deg);
  }
  80% {
    transform: rotate(8deg);
  }
}
@keyframes li-flap {
  0%,
  100% {
    transform: scaleY(1);
  }
  20%,
  70% {
    transform: scaleY(-0.85);
  }
}
@keyframes li-letter {
  0%,
  22% {
    transform: translateY(0);
  }
  40%,
  58% {
    transform: translateY(-7px);
  }
  72%,
  100% {
    transform: translateY(0);
  }
}
@keyframes li-ring {
  0%,
  44%,
  100% {
    transform: rotate(0);
  }
  4%,
  14%,
  24%,
  34% {
    transform: rotate(-11deg);
  }
  9%,
  19%,
  29%,
  39% {
    transform: rotate(11deg);
  }
}
@keyframes li-sound {
  0%,
  100% {
    opacity: 0;
  }
  20%,
  55% {
    opacity: 1;
  }
}
</style>
