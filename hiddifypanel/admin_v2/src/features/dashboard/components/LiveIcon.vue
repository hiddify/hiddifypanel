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
  'x-bogon',
  'x-satellite',
  'x-anycast',
  'x-dsl',
  'x-ipfs',
  'x-proxy',
  'x-onion',
  'x-active-tor',
  'x-relay',
  'x-mask',
  'x-spider',
  'x-warning',
  'x-blocked',
  'x-bug',
  'x-radar',
  'x-exit',
  'x-folder',
  'x-cert',
])
/** These take 2.6 s for one round, so a tap plays them once; the others take 1.3 s and play twice */
const SLOW = new Set(['x-radar', 'pi-globe', 'pi-history', 'pi-clock', 'pi-compass', 'pi-language', 'pi-envelope'])

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
      <rect x="3" y="8" width="18" height="12" rx="2.2" />
      <!-- the flap is drawn first: open, it stands behind the letter; closed, the letter is still inside -->
      <path class="p-flap" d="M3.6 8.6L12 14.6l8.4-6" />
      <clipPath :id="`${uid}-c`"><rect x="0" y="-10" width="24" height="18.4" /></clipPath>
      <g :clip-path="`url(#${uid}-c)`">
        <!-- the letter: a white card with two lines in the icon's colour -->
        <g class="p-letter">
          <rect x="6.5" y="9.5" width="11" height="9" rx="1" fill="currentColor" stroke="none" />
          <path d="M8.6 11.8h6.8M8.6 14.2h4.6" stroke="var(--li-ink, #007aff)" stroke-width="1.3" />
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

    <!-- bogon: an address that is not on the internet: the globe dims and a slash is drawn over it -->
    <template v-else-if="name === 'x-bogon'">
      <g class="p-dim">
        <circle cx="12" cy="12" r="8.5" />
        <ellipse cx="12" cy="12" rx="3.6" ry="8.5" />
        <path d="M3.5 12h17" />
      </g>
      <path class="p-draw" pathLength="1" d="M4.5 4.5l15 15" stroke-width="2.2" />
    </template>

    <!-- satellite: it rocks in its orbit and sends its signal -->
    <template v-else-if="name === 'x-satellite'">
      <g class="p-orbit">
        <path d="M12 8.5l3.5 3.5-3.5 3.5-3.5-3.5z" />
        <rect x="2.5" y="10" width="5.5" height="4" rx="0.6" />
        <rect x="16" y="10" width="5.5" height="4" rx="0.6" />
        <path d="M5.25 10v4M18.75 10v4M8 12h.5M15.5 12h.5" stroke-width="1.3" />
      </g>
      <path class="p-sound" d="M15.8 5.2a4 4 0 0 1 3 3" />
      <path class="p-sound p-d2" d="M16 2a7 7 0 0 1 6 6" />
    </template>

    <!-- anycast: one address answering from many places: a ring spreads and the places light up -->
    <template v-else-if="name === 'x-anycast'">
      <path d="M12 12L5 6M12 12l7-6M12 12v8" opacity="0.55" />
      <circle class="p-ripple" cx="12" cy="12" r="2.2" />
      <circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none" />
      <circle class="p-led" cx="5" cy="6" r="1.7" />
      <circle class="p-led p-d2" cx="19" cy="6" r="1.7" />
      <circle class="p-led p-d3" cx="12" cy="20" r="1.7" />
    </template>

    <!-- a dynamic line: its address keeps changing: the two arrows go round -->
    <template v-else-if="name === 'x-dsl'">
      <g class="p-spin">
        <path d="M19 12a7 7 0 0 1-11.9 5" />
        <path d="M6.8 20.4V17h3.4" />
        <path d="M5 12a7 7 0 0 1 11.9-5" />
        <path d="M17.2 3.6V7h-3.4" />
      </g>
      <circle class="p-pulse" cx="12" cy="12" r="1.3" fill="currentColor" stroke="none" />
    </template>

    <!-- IPFS: the hexagon turns a sixth and lands as it was -->
    <template v-else-if="name === 'x-ipfs'">
      <g class="p-hexspin">
        <path d="M12 2.8l8 4.6v9.2l-8 4.6-8-4.6V7.4z" />
        <path d="M12 12l8-4.6M12 12v9.2M12 12L4 7.4" stroke-width="1.4" />
      </g>
      <circle class="p-pulse" cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
    </template>

    <!-- proxy: a packet goes from one end, through the box in the middle, to the other -->
    <template v-else-if="name === 'x-proxy'">
      <circle cx="4.5" cy="12" r="2" />
      <circle cx="19.5" cy="12" r="2" />
      <path d="M6.5 12H9M15 12h2.5" />
      <rect x="9" y="8.5" width="6" height="7" rx="1.5" />
      <circle class="p-travel" cx="4.5" cy="12" r="1.1" fill="currentColor" stroke="none" />
    </template>

    <!-- Tor: the onion's layers glow one after another, from the outside in -->
    <template v-else-if="name === 'x-onion' || name === 'x-active-tor'">
      <path class="p-pulse" d="M12 3c0 2.5-6.5 5-6.5 11a6.5 6.5 0 0 0 13 0C18.5 8 12 5.5 12 3z" />
      <path class="p-pulse p-d2" d="M12 9c-2.6 1.6-3.6 3.4-3.6 5.4a3.6 3.6 0 0 0 7.2 0c0-2-1-3.8-3.6-5.4z" />
      <circle class="p-pulse p-d3" cx="12" cy="14.6" r="1.2" fill="currentColor" stroke="none" />
      <template v-if="name === 'x-active-tor'">
        <circle class="p-ripple-dot" cx="19.5" cy="4.5" r="2" />
        <circle class="p-led" cx="19.5" cy="4.5" r="2" fill="currentColor" stroke="none" />
      </template>
    </template>

    <!-- iCloud Private Relay: traffic flows through the cloud -->
    <template v-else-if="name === 'x-relay'">
      <path d="M7 18.5h10.5a4 4 0 0 0 .4-8 6 6 0 0 0-11.6 1.5A3.3 3.3 0 0 0 7 18.5z" />
      <g class="p-flow">
        <path d="M8.5 14.5h7" />
        <path d="M13.6 12.6l1.9 1.9-1.9 1.9" />
      </g>
    </template>

    <!-- anonymous: the mask is lifted on and its eyes blink -->
    <template v-else-if="name === 'x-mask'">
      <g class="p-mask">
        <path d="M3 9.5c3-1.5 6-1 9 .8 3-1.8 6-2.3 9-.8-.2 4.5-2.6 7-5.3 7-1.6 0-2.7-1-3.7-2.4-1 1.4-2.1 2.4-3.7 2.4C5.6 16.5 3.2 14 3 9.5z" />
        <ellipse class="p-eye" cx="8" cy="11.8" rx="1.6" ry="1" fill="currentColor" stroke="none" />
        <ellipse class="p-eye" cx="16" cy="11.8" rx="1.6" ry="1" fill="currentColor" stroke="none" />
      </g>
    </template>

    <!-- crawler: the spider lets itself down on its thread, legs moving -->
    <template v-else-if="name === 'x-spider'">
      <path class="p-thread" d="M12 1v6" stroke-width="1.2" />
      <g class="p-spider">
        <circle cx="12" cy="8.6" r="1.8" />
        <ellipse cx="12" cy="13.4" rx="3" ry="3.6" />
        <path class="p-legs-l" d="M9.2 11.4L5 8.6M9 13.4H4.6M9.3 15.4L5 18.2" stroke-width="1.5" />
        <path class="p-legs-r" d="M14.8 11.4L19 8.6M15 13.4h4.4M14.7 15.4l4.3 2.8" stroke-width="1.5" />
      </g>
    </template>

    <!-- abuser: the warning sign shakes and its mark blinks -->
    <template v-else-if="name === 'x-warning'">
      <g class="p-buzz">
        <path d="M10.3 4.4a2 2 0 0 1 3.4 0l7.2 12.5a2 2 0 0 1-1.7 3H4.8a2 2 0 0 1-1.7-3z" />
        <path d="M12 9.5v4.2" />
        <circle class="p-led" cx="12" cy="16.7" r="1" fill="currentColor" stroke="none" />
      </g>
    </template>

    <!-- known abuser: a list is written and the ban sign is drawn over it -->
    <template v-else-if="name === 'x-blocked'">
      <path class="p-draw-2" pathLength="1" d="M4 6h10" />
      <path class="p-draw-2 p-l2" pathLength="1" d="M4 10.5h7" />
      <path class="p-draw-2 p-l3" pathLength="1" d="M4 15h4.5" />
      <circle cx="16.5" cy="15.5" r="4.6" />
      <path class="p-draw" pathLength="1" d="M13.3 12.3l6.4 6.4" />
    </template>

    <!-- threat: the bug scuttles, legs going -->
    <template v-else-if="name === 'x-bug'">
      <g class="p-bug">
        <path d="M10.5 6.4L9 4.2M13.5 6.4L15 4.2" stroke-width="1.4" />
        <path d="M9.5 8.7a2.5 2.5 0 0 1 5 0" />
        <ellipse cx="12" cy="14" rx="4.2" ry="5.5" />
        <path d="M12 9.5v10" stroke-width="1.3" />
        <path class="p-legs-l" d="M7.8 12H4.6M7.9 15.4l-3.2 1.6M8.4 10L5.4 8" stroke-width="1.4" />
        <path class="p-legs-r" d="M16.2 12h3.2M16.1 15.4l3.2 1.6M15.6 10l3-2" stroke-width="1.4" />
      </g>
    </template>

    <!-- security scanner: the radar sweeps round and its contacts light up -->
    <template v-else-if="name === 'x-radar'">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" opacity="0.5" />
      <g class="p-sweep">
        <path d="M12 12V3a9 9 0 0 1 6.4 2.6z" fill="currentColor" fill-opacity="0.35" stroke="none" />
        <path d="M12 12V3" />
      </g>
      <circle class="p-blip" cx="16.2" cy="8.2" r="1.2" fill="currentColor" stroke="none" />
      <circle class="p-blip p-d2" cx="7.6" cy="15.4" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
    </template>

    <!-- Tor exit: the door swings open and an arrow goes out through it -->
    <template v-else-if="name === 'x-exit'">
      <path d="M13 3.5H6.5A1.5 1.5 0 0 0 5 5v14a1.5 1.5 0 0 0 1.5 1.5H13" />
      <rect class="p-door" x="5.6" y="4.1" width="6.8" height="15.8" rx="0.8" fill="currentColor" fill-opacity="0.22" stroke="none" />
      <g class="p-out">
        <path d="M14.5 12H21" />
        <path d="M18.2 9.2L21 12l-2.8 2.8" />
      </g>
    </template>

    <!-- open directory: the folder opens and a page rises out of it -->
    <template v-else-if="name === 'x-folder'">
      <path d="M3 18V6.5A1.5 1.5 0 0 1 4.5 5h4.6l2 2.5h8.4A1.5 1.5 0 0 1 21 9v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18z" />
      <rect class="p-paper" x="7" y="9.5" width="10" height="6.5" rx="0.8" fill="currentColor" stroke="none" />
      <path class="p-front" d="M3.2 11.2h17.6l-1.2 6.9a1.5 1.5 0 0 1-1.5 1.4H5.9a1.5 1.5 0 0 1-1.5-1.4z" fill="var(--li-ink, #007aff)" />
    </template>

    <!-- certificate: its lines are written again and the seal swings on its ribbons -->
    <template v-else-if="name === 'x-cert'">
      <rect x="3" y="4" width="18" height="12.5" rx="1.6" />
      <path class="p-draw" pathLength="1" d="M6.5 8h11" />
      <path class="p-draw-2" pathLength="1" d="M6.5 11h6" />
      <g class="p-seal">
        <path d="M14.3 18.2l-.8 3.6 2.5-1.2 2.5 1.2-.8-3.6" stroke-width="1.5" />
        <circle cx="16" cy="15.6" r="3" fill="var(--li-ink, #007aff)" />
      </g>
    </template>
  </svg>
  <i v-else class="pi" :class="name" />
</template>

<style scoped>
.li {
  --n: infinite;
  --n-legs: infinite;
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
  --n-legs: 6;
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
  transform-origin: 12px 8.6px;
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

/* --- the Complete IP Info icons ---------------------------------------------------------------------------------- */
.p-ripple,
.p-ripple-dot,
.p-blip {
  opacity: 0;
}
.p-travel {
  opacity: 0;
}
.p-paper {
  fill-opacity: 0.9;
}
.p-orbit,
.p-spin,
.p-hexspin,
.p-sweep,
.p-ripple {
  transform-origin: 12px 12px;
}
.p-ripple-dot {
  transform-origin: 19.5px 4.5px;
}
.p-mask {
  transform-origin: 12px 13px;
}
.p-eye {
  transform-box: fill-box;
  transform-origin: center;
}
.p-thread {
  transform-origin: 12px 1px;
}
.p-legs-l {
  transform-origin: 9px 13.4px;
}
.p-legs-r {
  transform-origin: 15px 13.4px;
}
.p-bug {
  transform-origin: 12px 14px;
}
.p-door {
  transform-origin: 5.6px 12px;
}
.p-front {
  transform-origin: 12px 19.5px;
}
.p-seal {
  transform-origin: 16px 15.6px;
}

.is-live > .li .p-dim {
  animation: li-dim 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-orbit {
  animation: li-orbit 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-ripple,
.is-live > .li .p-ripple-dot {
  animation: li-ripple 1.3s ease-out var(--n) both;
}
.is-live > .li .p-spin {
  animation: li-spin 1.3s cubic-bezier(0.6, 0, 0.3, 1) var(--n) both;
}
.is-live > .li .p-hexspin {
  animation: li-hexspin 1.3s cubic-bezier(0.6, 0, 0.3, 1) var(--n) both;
}
.is-live > .li .p-travel {
  animation: li-travel 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-pulse {
  animation: li-pulse 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-pulse.p-d2 {
  animation-delay: 0.15s;
}
.is-live > .li .p-pulse.p-d3 {
  animation-delay: 0.3s;
}
.is-live > .li .p-flow {
  animation: li-flow 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-mask {
  animation: li-mask 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-eye {
  animation: li-eyelid 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-thread {
  animation: li-thread 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-spider {
  animation: li-spider 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-legs-l {
  animation: li-legs 0.43s ease-in-out var(--n-legs) both;
}
.is-live > .li .p-legs-r {
  animation: li-legs 0.43s ease-in-out 0.21s var(--n-legs) both;
}
.is-live > .li .p-bug {
  animation: li-bug 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-draw-2.p-l2 {
  animation-delay: 0.1s;
}
.is-live > .li .p-draw-2.p-l3 {
  animation-delay: 0.2s;
}
.is-live > .li .p-sweep {
  animation: li-turn 2.6s linear var(--n) both;
}
.is-live > .li .p-blip {
  animation: li-blip 2.6s ease-out var(--n) both;
}
.is-live > .li .p-blip.p-d2 {
  animation-delay: 1.2s;
}
.is-live > .li .p-door {
  animation: li-door 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-out {
  animation: li-out 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-paper {
  animation: li-paper 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-front {
  animation: li-front 1.3s ease-in-out var(--n) both;
}
.is-live > .li .p-seal {
  animation: li-seal 1.3s ease-in-out var(--n) both;
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
    transform: translateY(-8px);
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
@keyframes li-dim {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
@keyframes li-orbit {
  0%,
  100% {
    transform: rotate(0);
  }
  30% {
    transform: rotate(-12deg);
  }
  70% {
    transform: rotate(9deg);
  }
}
@keyframes li-ripple {
  0% {
    opacity: 0.9;
    transform: scale(1);
  }
  80%,
  100% {
    opacity: 0;
    transform: scale(4);
  }
}
@keyframes li-spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes li-hexspin {
  0%,
  15% {
    transform: rotate(0);
  }
  85%,
  100% {
    transform: rotate(60deg);
  }
}
@keyframes li-travel {
  0% {
    opacity: 0;
    transform: translateX(0);
  }
  10% {
    opacity: 1;
  }
  45%,
  55% {
    opacity: 0.5;
    transform: translateX(7.5px);
  }
  90% {
    opacity: 1;
    transform: translateX(15px);
  }
  100% {
    opacity: 0;
    transform: translateX(15px);
  }
}
@keyframes li-pulse {
  0%,
  100% {
    opacity: 1;
  }
  45% {
    opacity: 0.3;
  }
}
@keyframes li-flow {
  0% {
    opacity: 0;
    transform: translateX(-3px);
  }
  25%,
  75% {
    opacity: 1;
    transform: translateX(0);
  }
  100% {
    opacity: 0;
    transform: translateX(3px);
  }
}
@keyframes li-mask {
  0%,
  100% {
    transform: translateY(0) rotate(0);
  }
  35% {
    transform: translateY(-1.8px) rotate(-7deg);
  }
  65% {
    transform: translateY(-0.6px) rotate(4deg);
  }
}
@keyframes li-thread {
  0%,
  100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(1.45);
  }
}
@keyframes li-spider {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(2.6px);
  }
}
@keyframes li-legs {
  0%,
  100% {
    transform: rotate(0);
  }
  50% {
    transform: rotate(9deg);
  }
}
@keyframes li-bug {
  0%,
  100% {
    transform: translateX(0) rotate(0);
  }
  25% {
    transform: translateX(-1.4px) rotate(-6deg);
  }
  75% {
    transform: translateX(1.4px) rotate(6deg);
  }
}
@keyframes li-turn {
  to {
    transform: rotate(360deg);
  }
}
@keyframes li-blip {
  0%,
  100% {
    opacity: 0;
  }
  8% {
    opacity: 1;
  }
  45% {
    opacity: 0;
  }
}
@keyframes li-door {
  0%,
  100% {
    transform: scaleX(1);
  }
  35%,
  65% {
    transform: scaleX(0.35);
  }
}
@keyframes li-out {
  0%,
  25%,
  100% {
    transform: translateX(0);
  }
  55% {
    transform: translateX(2.4px);
  }
}
@keyframes li-paper {
  0%,
  100% {
    transform: translateY(0);
  }
  40%,
  65% {
    transform: translateY(-3.4px);
  }
}
@keyframes li-front {
  0%,
  100% {
    transform: skewX(0) scaleY(1);
  }
  40%,
  65% {
    transform: skewX(-10deg) scaleY(0.88);
  }
}
@keyframes li-seal {
  0%,
  100% {
    transform: rotate(0);
  }
  25% {
    transform: rotate(-14deg);
  }
  55% {
    transform: rotate(10deg);
  }
  80% {
    transform: rotate(-4deg);
  }
}
</style>
