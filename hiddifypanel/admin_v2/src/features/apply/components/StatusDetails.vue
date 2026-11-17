<script setup lang="ts">
/**
 * "Check Status" as cards instead of a terminal, in the style of iOS: a summary (all services running, or how many
 * are down), where the server reaches the internet from (flag, city, provider, address), WARP when it is in use, and
 * every service as a row of a grouped list with its own icon and a breathing status dot. The cards rise in one after
 * another. The raw log stays one tap away below (RunPanel).
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import FlagIcon from '@/shared/components/FlagIcon.vue'
import ServiceLogo from './ServiceLogo.vue'
import { countryCode, parseStatus, serviceLook, type StatusPlace } from '../status-parse'

const props = defineProps<{ text: string }>()
const { t } = useI18n()

const report = computed(() => parseStatus(props.text))
const services = computed(() => report.value.services.map((s) => ({ ...s, ...serviceLook(s.unit), up: s.state === 'active' })))
const down = computed(() => services.value.filter((s) => !s.up).length)
const allUp = computed(() => services.value.length > 0 && down.value === 0)

const copied = ref('')
async function copy(value: string) {
  try {
    await navigator.clipboard.writeText(value)
    copied.value = value
    setTimeout(() => copied.value === value && (copied.value = ''), 1600)
  } catch {
    /* no clipboard (http): nothing */
  }
}
function placeLine(p: StatusPlace) {
  return [p.city, p.country].filter(Boolean).join(', ')
}
function stateLabel(state: string) {
  return t(`apply.details.state.${state}`, state)
}
</script>

<template>
  <section class="sd" :aria-label="t('apply.details.title')">
    <!-- the summary -->
    <div class="sd-card sd-hero" :class="allUp ? 'sd-hero--ok' : 'sd-hero--bad'" style="--i: 0">
      <span class="sd-hero__icon" aria-hidden="true">
        <svg v-if="allUp" viewBox="0 0 24 24"><path d="M6.5 12.5l3.6 3.6L17.8 8.4" /></svg>
        <svg v-else viewBox="0 0 24 24"><path d="M12 7.5v6M12 16.8v.2" /></svg>
      </span>
      <div class="sd-hero__text">
        <strong>{{ allUp ? t('apply.details.allRunning') : t('apply.details.someDown', { n: down }, down) }}</strong>
        <span>{{ t('apply.details.runningOf', { n: services.length - down, total: services.length }) }}</span>
      </div>
      <!-- one tick per service -->
      <div class="sd-hero__ticks" aria-hidden="true">
        <i v-for="s in services" :key="s.unit" :class="{ off: !s.up }" />
      </div>
    </div>

    <div class="sd-grid">
      <!-- where the server reaches the internet from -->
      <div v-if="report.ip && (report.ip.country || report.ip.query)" class="sd-card sd-place" style="--i: 1">
        <header class="sd-card__head"><i class="pi pi-globe" />{{ t('apply.details.publicAddress') }}</header>
        <div class="sd-place__main">
          <FlagIcon v-if="countryCode(report.ip.country)" class="sd-place__flag" :code="countryCode(report.ip.country)" :label="report.ip.country" waving />
          <span v-else class="sd-place__noflag"><i class="pi pi-map-marker" /></span>
          <div>
            <strong>{{ placeLine(report.ip) || '—' }}</strong>
            <span v-if="report.ip.org">{{ report.ip.org }}</span>
          </div>
        </div>
        <button v-if="report.ip.query" type="button" class="sd-ip" :aria-label="t('common.copy')" @click="copy(report.ip.query)">
          <span dir="ltr">{{ report.ip.query }}</span>
          <i :class="copied === report.ip.query ? 'pi pi-check' : 'pi pi-copy'" />
        </button>
      </div>

      <!-- WARP, when in use -->
      <div v-if="report.warp" class="sd-card sd-place sd-place--warp" style="--i: 2">
        <header class="sd-card__head"><i class="pi pi-cloud" />WARP</header>
        <div v-if="report.warp.network && (report.warp.network.country || report.warp.network.query)" class="sd-place__main">
          <FlagIcon v-if="countryCode(report.warp.network.country)" class="sd-place__flag" :code="countryCode(report.warp.network.country)" :label="report.warp.network.country" waving />
          <div>
            <strong>{{ placeLine(report.warp.network) || '—' }}</strong>
            <span v-if="report.warp.network.org">{{ report.warp.network.org }}</span>
          </div>
        </div>
        <p v-else class="sd-muted">{{ t('apply.details.warpNoNetwork') }}</p>
        <button v-if="report.warp.network?.query" type="button" class="sd-ip" :aria-label="t('common.copy')" @click="copy(report.warp.network.query)">
          <span dir="ltr">{{ report.warp.network.query }}</span>
          <i :class="copied === report.warp.network.query ? 'pi pi-check' : 'pi pi-copy'" />
        </button>
      </div>
    </div>

    <!-- every service: a grouped list as in iOS Settings -->
    <div v-if="services.length" class="sd-card sd-services" style="--i: 3">
      <header class="sd-card__head"><i class="pi pi-th-large" />{{ t('apply.details.services') }}</header>
      <ul>
        <li v-for="(s, n) in services" :key="s.unit" :style="{ '--c': s.color, '--j': n }">
          <ServiceLogo :logo="s.logo" :icon="s.icon" :color="s.color" />
          <span class="sd-svc__name">
            <strong>{{ s.name }}</strong>
            <small dir="ltr">{{ s.unit }}</small>
          </span>
          <span class="sd-svc__state" :class="{ 'is-down': !s.up }"><i />{{ stateLabel(s.state) }}</span>
        </li>
      </ul>
    </div>

    <p v-if="!services.length && !report.ip" class="sd-muted sd-empty">{{ t('apply.details.nothing') }}</p>
  </section>
</template>

<style scoped>
.sd {
  --sd-green: #34c759;
  --sd-red: #ff3b30;
  display: grid;
  gap: 0.75rem;
  margin-top: 0.75rem;
}
html.app-dark .sd {
  --sd-green: #30d158;
  --sd-red: #ff453a;
}

/* each card rises in after the one before it */
.sd-card {
  padding: 0.9rem 1rem;
  border-radius: 1.25rem;
  background: color-mix(in srgb, var(--p-content-background) 82%, transparent);
  box-shadow:
    inset 0 0 0 0.5px color-mix(in srgb, var(--p-text-color) 9%, transparent),
    0 10px 30px -18px rgb(0 0 0 / 0.35);
  -webkit-backdrop-filter: blur(20px) saturate(1.6);
  backdrop-filter: blur(20px) saturate(1.6);
  animation: sd-rise 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(var(--i, 0) * 90ms);
}
@keyframes sd-rise {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.98);
  }
}
.sd-card__head {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.7rem;
  color: var(--p-text-muted-color);
  font-size: 0.72rem;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.sd-card__head i {
  font-size: 0.75rem;
}

/* the summary */
.sd-hero {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.4rem 0.9rem;
  align-items: center;
  --tone: var(--sd-green);
  background: linear-gradient(135deg, color-mix(in srgb, var(--tone) 14%, var(--p-content-background)), var(--p-content-background) 70%);
}
.sd-hero--bad {
  --tone: var(--sd-red);
}
.sd-hero__icon {
  position: relative;
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  background: var(--tone);
  box-shadow: 0 8px 20px -8px color-mix(in srgb, var(--tone) 70%, transparent);
}
/* a slow ring, like a pulse */
.sd-hero__icon::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--tone) 45%, transparent);
  animation: sd-ring 2.4s ease-out infinite;
}
@keyframes sd-ring {
  to {
    box-shadow: 0 0 0 14px transparent;
  }
}
.sd-hero__icon svg {
  width: 1.6rem;
  height: 1.6rem;
  fill: none;
  stroke: #fff;
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 24;
  animation: sd-draw 0.7s 0.25s cubic-bezier(0.65, 0, 0.35, 1) both;
}
@keyframes sd-draw {
  from {
    stroke-dashoffset: 24;
  }
}
.sd-hero__text strong {
  display: block;
  font-size: 1.08rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.sd-hero__text span {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.sd-hero__ticks {
  grid-column: 1 / -1;
  display: flex;
  gap: 3px;
  margin-top: 0.35rem;
}
.sd-hero__ticks i {
  flex: 1;
  height: 0.35rem;
  border-radius: 999px;
  background: var(--sd-green);
  animation: sd-rise 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.sd-hero__ticks i.off {
  background: var(--sd-red);
}

.sd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: 0.75rem;
}

/* where the server is seen from */
.sd-place__main {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.sd-place__flag {
  flex: none;
  font-size: 2.4rem;
}
.sd-place__noflag {
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 0.8rem;
  background: color-mix(in srgb, #ff3b30 14%, transparent);
  color: #ff3b30;
}
.sd-place__main strong {
  display: block;
  font-size: 1rem;
  font-weight: 650;
}
.sd-place__main span {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.sd-ip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  width: 100%;
  margin-top: 0.8rem;
  padding: 0.55rem 0.75rem;
  border: 0;
  border-radius: 0.8rem;
  background: color-mix(in srgb, var(--p-text-color) 5%, transparent);
  color: var(--p-text-color);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.9rem;
  cursor: pointer;
  transition:
    background 0.2s,
    transform 0.2s;
}
.sd-ip:hover {
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
}
.sd-ip:active {
  transform: scale(0.98);
}
.sd-ip i {
  color: var(--p-primary-color);
}
.sd-place--warp .sd-card__head i {
  color: #f48120;
}

/* the services: a grouped list */
.sd-services ul {
  margin: 0;
  padding: 0;
  list-style: none;
  border-radius: 0.9rem;
  overflow: hidden;
  background: color-mix(in srgb, var(--p-text-color) 3%, transparent);
}
.sd-services li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  animation: sd-rise 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(300ms + var(--j, 0) * 45ms);
}
.sd-services li + li {
  box-shadow: inset 0 0.5px 0 color-mix(in srgb, var(--p-text-color) 10%, transparent);
}
.sd-svc__name {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}
.sd-svc__name strong {
  font-size: 0.92rem;
  font-weight: 600;
}
.sd-svc__name small {
  overflow: hidden;
  color: var(--p-text-muted-color);
  font-size: 0.72rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
html[dir='rtl'] .sd-svc__name small {
  text-align: right;
}
.sd-svc__state {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--sd-green) 14%, transparent);
  color: color-mix(in srgb, var(--sd-green) 75%, var(--p-text-color));
  font-size: 0.78rem;
  font-weight: 600;
}
.sd-svc__state i {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--sd-green);
  animation: sd-breathe 2.4s ease-in-out infinite;
}
.sd-svc__state.is-down {
  background: color-mix(in srgb, var(--sd-red) 14%, transparent);
  color: color-mix(in srgb, var(--sd-red) 80%, var(--p-text-color));
}
.sd-svc__state.is-down i {
  background: var(--sd-red);
  animation: none;
}
@keyframes sd-breathe {
  50% {
    opacity: 0.35;
    transform: scale(0.8);
  }
}

.sd-muted {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.sd-empty {
  padding: 0.5rem 0.25rem;
}

@media (prefers-reduced-motion: reduce) {
  .sd-card,
  .sd-services li,
  .sd-hero__ticks i,
  .sd-hero__icon svg,
  .sd-hero__icon::after,
  .sd-svc__state i {
    animation: none;
  }
}
</style>
