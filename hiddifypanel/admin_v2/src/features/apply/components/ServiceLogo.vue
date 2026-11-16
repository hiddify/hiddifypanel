<script setup lang="ts">
/**
 * A service's real logo as an app icon (status details): the vendor's mark from Simple Icons (CC0-1.0, the
 * brands' current logos, in their own colours) on a white tile; XRay's four-pointed star; Hiddify Manager's hexagon
 * (black for Hiddify Core, blue for the panel), which fills its tile. Other services keep a PrimeIcon on a tile of
 * their colour.
 */
import { useId } from 'vue'
import type { SimpleIcon } from 'simple-icons'
import type { ServiceLogoKind } from '../status-parse'

defineProps<{ logo: ServiceLogoKind | undefined; icon: string; color: string }>()
const id = useId()

/**
 * How large each mark is drawn on its 1.9rem tile: thin or airy marks (XRay's star, WireGuard's dragon, MySQL's
 * dolphin, HAProxy) larger, so every logo reads at the same weight.
 */
const SIZES: Record<string, string> = { xray: '1.55rem', WireGuard: '1.6rem', MySQL: '1.6rem', HAProxy: '1.6rem', Telegram: '1.45rem' }
function size(logo: ServiceLogoKind): string {
  return SIZES[typeof logo === 'string' ? logo : logo.title] ?? '1.3rem'
}
/** MySQL's brand blue is light and its dolphin thin: drawn in MySQL's darker blue so it reads */
function fill(logo: SimpleIcon): string {
  return logo.title === 'MySQL' ? '#00618a' : `#${logo.hex}`
}

const XRAY = 'M11.26 0 11.26 11.26 2.37 11.26 8.42 8.42ZM24 11.26 12.74 11.26 12.74 2.37 15.58 8.42ZM12.74 24 12.74 12.74 21.63 12.74 15.58 15.58ZM0 12.74 11.26 12.74 11.26 21.63 8.42 15.58Z'
/** Hiddify Manager's hexagon (rounded corners) and mark, on the 1024 grid of the app icon */
const HEX =
  'M970.14,310.98 L970.14,713.02 A109.95,109.95 0 0 1 915.16,808.25 L566.98,1009.27 A109.95,109.95 0 0 1 457.02,1009.27 L108.84,808.25 A109.95,109.95 0 0 1 53.86,713.02 L53.86,310.98 A109.95,109.95 0 0 1 108.84,215.75 L457.02,14.73 A109.95,109.95 0 0 1 566.98,14.73 L915.16,215.75 A109.95,109.95 0 0 1 970.14,310.98 Z'
</script>

<template>
  <!-- Hiddify: the hexagon is the icon -->
  <svg v-if="logo === 'hiddify-black' || logo === 'hiddify-blue'" class="svc-logo svc-logo--hex" viewBox="0 0 1024 1024" aria-hidden="true">
    <defs>
      <linearGradient :id="`${id}-g`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" :stop-color="logo === 'hiddify-blue' ? '#5b9dff' : '#3a3a3c'" />
        <stop offset="1" :stop-color="logo === 'hiddify-blue' ? '#2563eb' : '#000000'" />
      </linearGradient>
    </defs>
    <!-- the reverse look (as the top bar's logo): a ring in the colour, white inside, the mark in the colour -->
    <path :d="HEX" :fill="`url(#${id}-g)`" />
    <path :d="HEX" fill="#fff" transform="translate(512,512) scale(0.86) translate(-512,-512)" />
    <g transform="translate(68.7,32.4) scale(1.385)" :fill="`url(#${id}-g)`" :stroke="`url(#${id}-g)`" stroke-width="12" stroke-linejoin="round">
      <path d="M158,372 L234,328 L234,416 L283,416 L283,292 L356,249 L356,467 L283,467 L283,424 L234,424 L234,467 L158,467 Z" />
      <path d="M407,226 L482,181 L482,254 L407,254 Z" />
      <rect x="407" y="286" width="75" height="181" />
    </g>
  </svg>
  <!-- a vendor's mark on a white tile, as an app icon -->
  <span v-else-if="logo" class="svc-logo svc-logo--tile" :class="{ 'svc-logo--ink': logo === 'xray' }" aria-hidden="true">
    <svg viewBox="0 0 24 24" :style="{ width: size(logo), height: size(logo) }"><path :d="logo === 'xray' ? XRAY : logo.path" :fill="logo === 'xray' ? 'currentColor' : fill(logo)" /></svg>
  </span>
  <span v-else class="svc-logo svc-logo--glyph" :style="{ background: color }" aria-hidden="true"><i :class="icon" /></span>
</template>

<style scoped>
.svc-logo {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
}
.svc-logo--hex {
  filter: drop-shadow(0 1px 1.5px rgb(0 0 0 / 0.2));
}
.svc-logo--tile,
.svc-logo--glyph {
  border-radius: 0.55rem;
}
.svc-logo--tile {
  background: #fff;
  box-shadow:
    inset 0 0 0 0.5px rgb(0 0 0 / 0.12),
    0 1px 2px rgb(0 0 0 / 0.08);
}
.svc-logo--tile svg {
  display: block;
}
.svc-logo--ink {
  color: #1c1c1e;
}
html.app-dark .svc-logo--tile {
  background: #2c2c2e;
  box-shadow: inset 0 0 0 0.5px rgb(255 255 255 / 0.12);
}
html.app-dark .svc-logo--ink {
  color: #fff;
}
.svc-logo--glyph {
  box-shadow: inset 0 0.5px 0 rgb(255 255 255 / 0.35);
  color: #fff;
  font-size: 0.85rem;
}
</style>
