<script setup lang="ts">
/** The internet this browser is on (the operator the scan tests), as the panel sees it. */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'
import FlagIcon from '@/shared/components/FlagIcon.vue'
import { countryName } from '@/shared/utils/country'
import type { CleanIpNetwork } from '../api'
import { operatorLabel } from './operatorLabel'

const props = defineProps<{ net: CleanIpNetwork | null; error: string; checking?: boolean }>()
defineEmits<{ refresh: [] }>()
const { t, locale } = useI18n()

const known = computed(() => !!props.net && props.net.short_name !== 'unknown')
// The name alone: the AS number has its own chip (shown always, detected operator or not)
const operatorName = computed(() => (props.net ? operatorLabel(t, props.net.short_name) : ''))
const asKnown = computed(() => !!props.net && /^\d+$/.test(props.net.asn))
// Another country than the panel's: a VPN is on, so the scan would test the VPN, not the users' operator
const vpnOn = computed(() => !!props.net?.panel_country && props.net.country !== 'unknown' && props.net.country !== props.net.panel_country)
/** The two countries the notice compares: where this browser seems to be, and where the panel's users are */
const here = computed(() => (props.net ? countryName(props.net.country.toUpperCase(), locale.value) : ''))
const usersHere = computed(() => (props.net?.panel_country ? countryName(props.net.panel_country.toUpperCase(), locale.value) : ''))

/** Checked again and the VPN is still on: the notice nudges, as iOS does for a wrong entry */
const nudge = ref(false)
watch(
  () => props.checking,
  (now, before) => {
    if (before && !now && vpnOn.value) {
      nudge.value = false
      requestAnimationFrame(() => (nudge.value = true))
    }
  },
)

/** The VPN is off now: the notice folds away (its height goes to 0), so the page below rises smoothly */
function foldAway(el: Element, done: () => void) {
  const box = el as HTMLElement
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return done()
  const ease = 'cubic-bezier(0.32, 0.72, 0, 1)'
  box.style.height = `${box.offsetHeight}px`
  void box.offsetHeight
  box.style.transition = `height 0.45s ${ease}, margin 0.45s ${ease}, padding 0.45s ${ease}, opacity 0.3s ease, transform 0.45s ease`
  Object.assign(box.style, { height: '0px', marginTop: '0px', paddingTop: '0px', paddingBottom: '0px', opacity: '0', transform: 'scale(0.98)' })
  setTimeout(done, 460)
}

// The detected operator's logo (assets/operators/<code>.png, sources in CREDITS.md); an operator without one, an
// unknown network or a VPN keeps the icon
const LOGOS = import.meta.glob<string>('@/assets/operators/*.png', { eager: true, query: '?url', import: 'default' })
const logo = computed(() => {
  if (!known.value || vpnOn.value) return ''
  return LOGOS[`/src/assets/operators/${props.net!.short_name}.png`] ?? ''
})
</script>

<template>
  <section class="net card">
    <div class="net__main">
      <span v-if="logo" class="net__icon net__icon--logo" :class="{ 'is-checking': checking }"><img :src="logo" :alt="operatorName" /></span>
      <span v-else class="net__icon" :class="{ 'net__icon--warn': vpnOn, 'is-checking': checking }"><i class="pi" :class="vpnOn ? 'pi-exclamation-triangle' : 'pi-wifi'" /></span>
      <div class="net__body" :class="{ 'is-checking': checking }">
        <div class="net__label">{{ t('cleanIp.yourNetwork') }}</div>
        <template v-if="net">
          <div class="net__name">
            {{ operatorName }}
            <span v-if="known" class="net__code">{{ net.short_name }}</span>
            <span class="net__code net__code--as" dir="ltr" v-tooltip.bottom="asKnown ? net.org : t('cleanIp.asUnknown')">AS{{ asKnown ? net.asn : ' ?' }}</span>
          </div>
          <div v-if="net.asn && net.asn !== 'unknown'" class="net__meta"><span class="ltr">AS{{ net.asn }} · {{ net.org }} · {{ net.country.toUpperCase() }}</span></div>
        </template>
        <div v-else-if="error" class="net__error">{{ error }}</div>
        <template v-else>
          <Skeleton width="10rem" height="1.4rem" class="mb-1" />
          <Skeleton width="14rem" height="0.9rem" />
        </template>
      </div>
      <Button :icon="checking ? 'pi pi-refresh pi-spin' : 'pi pi-refresh'" text rounded :disabled="checking" :aria-label="t('cleanIp.refreshNetwork')" v-tooltip.bottom="t('cleanIp.refreshNetwork')" @click="$emit('refresh')" />
    </div>
    <!-- Another country than the panel's: an iOS-style notice that says why, shows the two countries, and how to fix it -->
    <Transition name="vpn" appear @leave="foldAway">
      <div v-if="vpnOn && net" class="vpn" :class="{ 'is-checking': checking, 'is-nudged': nudge }" role="status" :aria-busy="checking" @animationend="nudge = false">
        <div class="vpn__head">
          <span class="vpn__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M12 2.6 4.6 5.4v5.8c0 4.6 3.1 8.6 7.4 10.2 4.3-1.6 7.4-5.6 7.4-10.2V5.4L12 2.6Z" />
              <path d="M9 9l6 6M15 9l-6 6" />
            </svg>
          </span>
          <div class="vpn__text">
            <strong>{{ t('cleanIp.vpn.title') }}</strong>
            <p>{{ t('cleanIp.vpn.body') }}</p>
          </div>
        </div>

        <!-- where this browser comes from ≠ where the users are -->
        <div class="vpn__route">
          <div class="vpn__place">
            <span class="vpn__place-label">{{ t('cleanIp.vpn.thisDevice') }}</span>
            <span class="vpn__place-name"><FlagIcon :code="net.country" :label="here" />{{ here }}</span>
          </div>
          <span class="vpn__ne" aria-hidden="true">≠</span>
          <div class="vpn__place">
            <span class="vpn__place-label">{{ t('cleanIp.vpn.yourUsers') }}</span>
            <span class="vpn__place-name"><FlagIcon :code="net.panel_country" :label="usersHere" />{{ usersHere }}</span>
          </div>
        </div>

        <ol class="vpn__steps">
          <li><span>1</span>{{ t('cleanIp.vpn.step1') }}</li>
          <li><span>2</span>{{ t('cleanIp.vpn.step2') }}</li>
        </ol>
        <div class="vpn__foot">
          <p>{{ t('cleanIp.vpn.abroad') }}</p>
          <button type="button" class="vpn__again" :disabled="checking" @click="$emit('refresh')">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.34-5.66M20 4v4.5h-4.5" /></svg>
            <Transition name="vpn-label" mode="out-in">
              <span :key="checking ? 'c' : 'a'">{{ checking ? t('cleanIp.vpn.checking') : t('cleanIp.vpn.checkAgain') }}</span>
            </Transition>
          </button>
        </div>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.net {
  margin-bottom: 0;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, color-mix(in srgb, var(--p-primary-color) 10%, var(--p-content-background)), var(--p-content-background) 60%);
}
.net__main {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}
.net__icon {
  width: 3rem;
  height: 3rem;
  flex: none;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
  border-radius: 1rem;
  color: var(--p-primary-contrast-color);
  background: var(--p-primary-color);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}
.net__icon--logo {
  overflow: hidden;
  /* each logo brings its own square background (white, or the brand colour) */
  background: #fff;
  box-shadow:
    0 6px 16px color-mix(in srgb, var(--p-primary-color) 22%, transparent),
    0 0 0 1px color-mix(in srgb, var(--p-content-border-color) 80%, transparent);
}
.net__icon--logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.net__icon--warn {
  background: var(--p-orange-500);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--p-orange-500) 35%, transparent);
}
.net__body {
  flex: 1;
  min-width: 0;
}
.net__label {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.net__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.2rem;
  font-weight: 700;
}
.net__code {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.net__code--as {
  color: var(--p-text-color);
  background: var(--p-content-hover-background);
  font-variant-numeric: tabular-nums;
}
.net__meta {
  margin-top: 0.15rem;
  font-size: 0.82rem;
  color: var(--p-text-muted-color);
  overflow-wrap: anywhere;
}
.net__error {
  color: var(--p-red-500);
  font-size: 0.9rem;
}
/* the VPN notice: an iOS grouped card of soft orange glass */
.vpn {
  --vpn: #ff9500;
  margin-top: 0.9rem;
  padding: 0.95rem;
  border-radius: 1.15rem;
  background: color-mix(in srgb, var(--vpn) 9%, var(--p-content-background));
  box-shadow:
    inset 0 0 0 0.5px color-mix(in srgb, var(--vpn) 30%, transparent),
    0 8px 24px -14px color-mix(in srgb, var(--vpn) 60%, transparent);
}
html.app-dark .vpn {
  --vpn: #ff9f0a;
  background: color-mix(in srgb, var(--vpn) 13%, var(--p-content-background));
}
.vpn__head {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}
.vpn__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 0.75rem;
  background: linear-gradient(160deg, #ffb340, #ff8a00);
  box-shadow:
    0 4px 12px -4px rgb(255 138 0 / 0.55),
    inset 0 0.5px 0 rgb(255 255 255 / 0.5);
}
.vpn__icon svg {
  width: 1.35rem;
  height: 1.35rem;
  fill: none;
  stroke: #fff;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.vpn__icon svg path:first-child {
  fill: rgb(255 255 255 / 0.22);
}
.vpn__text {
  min-width: 0;
}
.vpn__text strong {
  display: block;
  font-size: 1rem;
  font-weight: 650;
  letter-spacing: -0.01em;
}
.vpn__text p {
  margin: 0.2rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.86rem;
  line-height: 1.45;
}
.vpn__route {
  display: flex;
  align-items: stretch;
  gap: 0.5rem;
  margin-top: 0.85rem;
}
.vpn__place {
  flex: 1;
  min-width: 0;
  padding: 0.55rem 0.7rem;
  border-radius: 0.85rem;
  background: color-mix(in srgb, var(--p-content-background) 70%, transparent);
  box-shadow: inset 0 0 0 0.5px color-mix(in srgb, var(--p-text-color) 8%, transparent);
}
.vpn__place-label {
  display: block;
  color: var(--p-text-muted-color);
  font-size: 0.72rem;
  font-weight: 500;
}
.vpn__place-name {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.15rem;
  overflow: hidden;
  font-size: 0.92rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.vpn__ne {
  align-self: center;
  color: var(--vpn);
  font-size: 1.25rem;
  font-weight: 700;
}
.vpn__steps {
  display: grid;
  gap: 0.4rem;
  margin: 0.85rem 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.88rem;
}
.vpn__steps li {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}
.vpn__steps li span {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.3rem;
  height: 1.3rem;
  border-radius: 50%;
  background: color-mix(in srgb, var(--vpn) 18%, transparent);
  color: color-mix(in srgb, var(--vpn) 80%, var(--p-text-color));
  font-size: 0.72rem;
  font-weight: 700;
}
.vpn__foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  margin-top: 0.85rem;
}
.vpn__foot p {
  flex: 1 1 14rem;
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.76rem;
  line-height: 1.4;
}
.vpn__again {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0.95rem;
  border: 0;
  border-radius: 999px;
  background: var(--vpn);
  box-shadow: 0 4px 12px -4px color-mix(in srgb, var(--vpn) 70%, transparent);
  color: #fff;
  font: inherit;
  font-size: 0.85rem;
  font-weight: 650;
  cursor: pointer;
  transition: transform 0.2s ease, filter 0.2s ease;
}
.vpn__again:hover {
  filter: brightness(1.06);
}
.vpn__again:active {
  transform: scale(0.96);
}
.vpn__again svg {
  width: 0.95rem;
  height: 0.95rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
/* checking: the card keeps its content; the name dims a little and the icon breathes */
.net__body,
.net__icon {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}
.net__body.is-checking {
  opacity: 0.55;
}
.net__icon.is-checking {
  animation: net-breathe 1.2s ease-in-out infinite;
}
@keyframes net-breathe {
  50% {
    transform: scale(0.94);
  }
}
/* …and a soft light sweeps across the notice */
.vpn {
  position: relative;
  overflow: hidden;
}
.vpn.is-checking::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(105deg, transparent 30%, rgb(255 255 255 / 0.45) 50%, transparent 70%);
  transform: translateX(-100%);
  animation: vpn-sweep 1.1s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  pointer-events: none;
}
html.app-dark .vpn.is-checking::after {
  background: linear-gradient(105deg, transparent 30%, rgb(255 255 255 / 0.1) 50%, transparent 70%);
}
@keyframes vpn-sweep {
  to {
    transform: translateX(100%);
  }
}
.vpn__route,
.vpn__steps {
  transition: opacity 0.3s ease;
}
.vpn.is-checking .vpn__route,
.vpn.is-checking .vpn__steps {
  opacity: 0.6;
}
.vpn__again:disabled {
  cursor: default;
  filter: saturate(0.85);
}
.vpn.is-checking .vpn__again svg {
  animation: vpn-spin 0.9s linear infinite;
}
@keyframes vpn-spin {
  to {
    transform: rotate(360deg);
  }
}
/* still on after the check: a short, soft shake */
.vpn.is-nudged {
  animation: vpn-nudge 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97);
}
@keyframes vpn-nudge {
  20% {
    transform: translateX(-5px);
  }
  40% {
    transform: translateX(4px);
  }
  60% {
    transform: translateX(-2.5px);
  }
  80% {
    transform: translateX(1.5px);
  }
}
.vpn-label-enter-active,
.vpn-label-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.vpn-label-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.vpn-label-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.vpn-enter-active {
  transition:
    opacity 0.35s ease,
    transform 0.5s cubic-bezier(0.32, 1.2, 0.4, 1);
}
.vpn-enter-from {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}
@media (prefers-reduced-motion: reduce) {
  .vpn-enter-active {
    transition: opacity 0.2s ease;
  }
  .net__icon.is-checking,
  .vpn.is-checking::after,
  .vpn.is-checking .vpn__again svg,
  .vpn.is-nudged {
    animation: none;
  }
  .vpn-enter-from {
    transform: none;
  }
}
.ltr {
  direction: ltr;
  unicode-bidi: isolate;
}
</style>
