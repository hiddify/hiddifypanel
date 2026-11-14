<script setup lang="ts">
/**
 * A server's or node's IP addresses in one sheet, in the style of iOS: the company's logo and the country's waving
 * flag, each address, what kind of network it is, who runs it, where it is, the abuse contact and the server's
 * domains. The panel looks the addresses up in open sources and keeps the answer 72 hours; this browser keeps it as
 * long, so opening the sheet again asks nobody.
 * A bottom sheet on a phone, a card in the middle elsewhere.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import FlagIcon from '@/shared/components/FlagIcon.vue'
import { countryName } from '@/shared/utils/country'
import { apiErrorMessage } from '@/core/api/client'
import { nodesApi, type IpDetails, type NodeIpInfo } from '@/features/nodes/api'

const props = defineProps<{ node: { id: number; title: string } | null }>()
const visible = defineModel<boolean>('visible', { default: false })

const { t, locale } = useI18n()

const info = ref<NodeIpInfo | null>(null)
const loading = ref(false)
const error = ref('')
const selected = ref(0)
const copied = ref('')
let copiedTimer = 0

const phone = window.matchMedia('(max-width: 640px)')
const isPhone = ref(phone.matches)
const onPhone = () => (isPhone.value = phone.matches)
phone.addEventListener('change', onPhone)
onBeforeUnmount(() => phone.removeEventListener('change', onPhone))

// --- the answer, kept in this browser until the panel would look it up again ---------------------------------
const STORE = 'hm.ipinfo.v2.'
function stored(id: number): NodeIpInfo | null {
  try {
    const raw = JSON.parse(localStorage.getItem(STORE + id) || 'null') as {
      until: number
      data: NodeIpInfo
    } | null
    return raw && raw.until > Date.now() ? raw.data : null
  } catch {
    return null
  }
}
function store(id: number, data: NodeIpInfo) {
  const seconds = data.refresh_in > 0 ? data.refresh_in : data.ttl
  try {
    localStorage.setItem(STORE + id, JSON.stringify({ until: Date.now() + seconds * 1000, data }))
  } catch {
    /* private mode or full: it is asked again next time */
  }
}

async function load(id: number) {
  error.value = ''
  const kept = stored(id)
  if (kept) {
    info.value = kept
    return
  }
  info.value = null
  loading.value = true
  try {
    const data = await nodesApi.ipInfo(id)
    if (props.node?.id !== id) return
    info.value = data
    if (data.ips.length) store(id, data)
  } catch (err) {
    error.value = apiErrorMessage(err)
  } finally {
    loading.value = false
  }
}

watch(
  () => [visible.value, props.node?.id] as const,
  ([open, id]) => {
    if (open && id != null) {
      selected.value = 0
      void load(id)
    }
  },
  { immediate: true },
)

const current = computed<IpDetails | null>(() => info.value?.ips[selected.value] ?? info.value?.ips[0] ?? null)
const countryCode = computed(() => current.value?.geo.country_code || current.value?.network.country || '')
const country = computed(() => (countryCode.value ? countryName(countryCode.value, locale.value) : ''))
const place = computed(() => [current.value?.geo.city, current.value?.geo.region, country.value].filter(Boolean).join(', '))
const company = computed(() => current.value?.company.name || current.value?.geo.org || '')
const monogram = computed(() => (company.value.trim()[0] || '?').toUpperCase())
/** The company's initial on a colour of its own when it has no logo */
const monogramHue = computed(() => [...company.value].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 360, 210))

// --- a phone: pull the sheet down to close it, as in iOS ------------------------------------------------------
const sheet = ref<HTMLElement | null>(null)
const dialogEl = () => sheet.value?.closest<HTMLElement>('.p-dialog') ?? null
let drag: {
  y: number
  dy: number
  active: boolean
  samples: { y: number; t: number }[]
} | null = null

/** Starts on the top of the sheet, or anywhere once its content is scrolled to the top */
function onTouchStart(e: TouchEvent) {
  if (!isPhone.value || e.touches.length !== 1) return
  const body = sheet.value?.querySelector('.ips__body')
  if (body?.contains(e.target as Node) && body.scrollTop > 0) return
  const y = e.touches[0]!.clientY
  drag = { y, dy: 0, active: false, samples: [{ y, t: performance.now() }] }
}
function onTouchMove(e: TouchEvent) {
  if (!drag) return
  const y = e.touches[0]!.clientY
  const dy = y - drag.y
  if (!drag.active) {
    if (Math.abs(dy) < 6) return
    // upwards it is a scroll of the content, not ours
    if (dy < 0) {
      drag = null
      return
    }
    drag.active = true
    const el = dialogEl()
    if (el) el.style.transition = 'none'
  }
  if (e.cancelable) e.preventDefault()
  drag.dy = Math.max(0, dy)
  const now = performance.now()
  drag.samples.push({ y, t: now })
  while (drag.samples.length > 2 && now - drag.samples[0]!.t > 90) drag.samples.shift()
  const el = dialogEl()
  if (el) el.style.transform = `translateY(${drag.dy}px)`
}
function onTouchEnd() {
  const d = drag
  drag = null
  if (!d?.active) return
  const first = d.samples[0]!
  const last = d.samples[d.samples.length - 1]!
  const speed = last.t > first.t ? (last.y - first.y) / (last.t - first.t) : 0
  const el = dialogEl()
  const height = el?.offsetHeight ?? 600
  if (d.dy > Math.min(140, height * 0.25) || speed > 0.55) {
    // closes from where the finger left it (the leave animation starts at the current transform)
    visible.value = false
    return
  }
  if (el) {
    el.style.transition = 'transform 0.42s cubic-bezier(0.32, 0.72, 0, 1)'
    el.style.transform = ''
    window.setTimeout(() => {
      if (!drag) el.style.transition = ''
    }, 450)
  }
}
watch(visible, (open) => {
  if (!open) return
  requestAnimationFrame(() => {
    const el = dialogEl()
    if (el) {
      el.style.transform = ''
      el.style.transition = ''
    }
  })
})

/** How each icon comes alive under the mouse (desktop) */
const MOTIONS: Record<string, string> = {
  'pi-globe': 'spin',
  'pi-compass': 'spin',
  'pi-history': 'spin',
  'pi-refresh': 'spin',
  'pi-map-marker': 'bounce',
  'pi-home': 'bounce',
  'pi-building': 'bounce',
  'pi-flag': 'bounce',
  'pi-flag-fill': 'bounce',
  'pi-user': 'bounce',
  'pi-map': 'bounce',
  'pi-phone': 'wiggle',
  'pi-envelope': 'wiggle',
  'pi-shield': 'wiggle',
  'pi-tag': 'wiggle',
  'pi-eye-slash': 'wiggle',
  'pi-mobile': 'wiggle',
  'pi-briefcase': 'wiggle',
  'pi-id-card': 'wiggle',
  'pi-wallet': 'wiggle',
  'pi-clock': 'tick',
  'pi-calendar': 'tick',
  'pi-calendar-plus': 'tick',
  'pi-server': 'float',
  'pi-database': 'float',
  'pi-th-large': 'float',
  'pi-sitemap': 'float',
  'pi-link': 'float',
  'pi-language': 'float',
  'pi-arrows-h': 'slide',
}
const motionOf = (icon: string) => MOTIONS[icon] ?? 'float'

/**
 * Touch screens have no hover: a tap on an icon brings its glyph alive for a few seconds (the same motion as under the
 * mouse), then it settles by itself. Only the glyph moves; the icon's tile keeps its size.
 */
const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)')
const ALIVE = 'ips-alive'
function onIconTap(e: MouseEvent) {
  if (finePointer.matches) return
  const icon = (e.target as Element | null)?.closest<HTMLElement>('.ips__row-icon, .ips__tile-icon')
  if (!icon || icon.classList.contains(ALIVE)) return
  icon.classList.add(ALIVE)
  // the animation's own end takes the class off; the timer is for "reduce motion", where nothing plays
  window.setTimeout(() => icon.classList.remove(ALIVE), 3200)
}
function onIconSettled(e: AnimationEvent) {
  ;(e.target as Element | null)?.closest('.' + ALIVE)?.classList.remove(ALIVE)
}

function copy(value: string) {
  void navigator.clipboard?.writeText(value)
  copied.value = value
  window.clearTimeout(copiedTimer)
  copiedTimer = window.setTimeout(() => (copied.value = ''), 1400)
}

function ago(seconds: number): string {
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  const diff = Math.round(seconds - Date.now() / 1000)
  if (Math.abs(diff) < 3600) return rtf.format(Math.round(diff / 60), 'minute')
  if (Math.abs(diff) < 86400) return rtf.format(Math.round(diff / 3600), 'hour')
  return rtf.format(Math.round(diff / 86400), 'day')
}
const nextLookup = computed(() => {
  if (!info.value) return 0
  const kept = info.value.refresh_in > 0 ? info.value.refresh_in : info.value.ttl
  const fetched = current.value?.fetched_at ?? Date.now() / 1000
  return Math.max(1, Math.round((fetched + kept - Date.now() / 1000) / 3600))
})

/** The kinds of network, each a coloured tile */
const detections = computed(() => {
  const d = current.value?.detect
  if (!d) return []
  return [
    {
      key: 'datacenter',
      icon: 'pi-server',
      color: '#5856d6',
      on: d.datacenter,
      value: d.datacenter ? t('dashboard.ipInfo.yes') : t('dashboard.ipInfo.no'),
    },
    {
      key: 'vpn',
      icon: 'pi-shield',
      color: '#ff9500',
      on: d.vpn_likely,
      value: d.vpn_likely ? t('dashboard.ipInfo.likely') : t('dashboard.ipInfo.unlikely'),
    },
    {
      key: 'tor',
      icon: 'pi-eye-slash',
      color: '#af52de',
      on: d.tor,
      value: d.tor ? t('dashboard.ipInfo.yes') : t('dashboard.ipInfo.no'),
    },
    {
      key: 'mobile',
      icon: 'pi-mobile',
      color: '#30b0c7',
      on: d.mobile,
      value: d.mobile ? t('dashboard.ipInfo.likely') : t('dashboard.ipInfo.no'),
    },
    {
      key: 'residential',
      icon: 'pi-home',
      color: '#34c759',
      on: d.residential,
      value: d.residential ? t('dashboard.ipInfo.likely') : t('dashboard.ipInfo.no'),
    },
    {
      key: 'public',
      icon: 'pi-globe',
      color: '#007aff',
      on: !d.bogon,
      value: d.bogon ? t('dashboard.ipInfo.bogon') : t('dashboard.ipInfo.yes'),
    },
  ]
})

type Row = {
  icon: string
  color: string
  label: string
  value: string
  mono?: boolean
  copy?: boolean
  href?: string
}
const rowsOf = (rows: (Row | false | null | undefined)[]) => rows.filter((r): r is Row => !!r && !!r.value)

const networkRows = computed(() => {
  const c = current.value
  if (!c) return []
  return rowsOf([
    {
      icon: 'pi-building',
      color: '#007aff',
      label: t('dashboard.ipInfo.company'),
      value: company.value,
    },
    {
      icon: 'pi-link',
      color: '#5ac8fa',
      label: t('dashboard.ipInfo.website'),
      value: c.company.domain,
    },
    {
      icon: 'pi-tag',
      color: '#ff9500',
      label: t('dashboard.ipInfo.netname'),
      value: c.network.netname ?? '',
      mono: true,
    },
    {
      icon: 'pi-arrows-h',
      color: '#30b0c7',
      label: t('dashboard.ipInfo.range'),
      value: c.network.range ?? '',
      mono: true,
      copy: true,
    },
    {
      icon: 'pi-th-large',
      color: '#34c759',
      label: t('dashboard.ipInfo.route'),
      value: c.network.cidr ?? '',
      mono: true,
      copy: true,
    },
    {
      icon: 'pi-database',
      color: '#8e8e93',
      label: t('dashboard.ipInfo.registry'),
      value: c.network.rir ?? '',
    },
    {
      icon: 'pi-calendar-plus',
      color: '#ff3b30',
      label: t('dashboard.ipInfo.registered'),
      value: c.network.registered ?? '',
    },
    {
      icon: 'pi-history',
      color: '#ff2d55',
      label: t('dashboard.ipInfo.updated'),
      value: c.network.updated ?? '',
    },
  ])
})
const asnRows = computed(() => {
  const a = current.value?.asn
  if (!a?.asn) return []
  return rowsOf([
    {
      icon: 'pi-sitemap',
      color: '#af52de',
      label: t('dashboard.ipInfo.asn'),
      value: a.asn,
      mono: true,
      copy: true,
    },
    {
      icon: 'pi-briefcase',
      color: '#5856d6',
      label: t('dashboard.ipInfo.asOrg'),
      value: a.org || a.name || '',
    },
    {
      icon: 'pi-id-card',
      color: '#007aff',
      label: t('dashboard.ipInfo.asName'),
      value: a.name && a.name !== a.org ? a.name : '',
      mono: true,
    },
    {
      icon: 'pi-flag',
      color: '#ff9500',
      label: t('dashboard.ipInfo.asCountry'),
      value: a.country ? countryName(a.country, locale.value) : '',
    },
    {
      icon: 'pi-calendar',
      color: '#ff3b30',
      label: t('dashboard.ipInfo.asRegistered'),
      value: a.registered ?? '',
    },
  ])
})
const locationRows = computed(() => {
  const g = current.value?.geo
  if (!g) return []
  const coords = g.latitude != null && g.longitude != null ? `${g.latitude.toFixed(4)}, ${g.longitude.toFixed(4)}` : ''
  return rowsOf([
    {
      icon: 'pi-map-marker',
      color: '#ff3b30',
      label: t('dashboard.ipInfo.city'),
      value: g.city,
    },
    {
      icon: 'pi-map',
      color: '#ff9500',
      label: t('dashboard.ipInfo.region'),
      value: [g.region, g.region_code && `(${g.region_code})`].filter(Boolean).join(' '),
    },
    {
      icon: 'pi-flag-fill',
      color: '#34c759',
      label: t('dashboard.ipInfo.country'),
      value: country.value,
    },
    {
      icon: 'pi-globe',
      color: '#007aff',
      label: t('dashboard.ipInfo.continent'),
      value: g.continent_code ? t(`dashboard.ipInfo.continents.${g.continent_code}`) : '',
    },
    {
      icon: 'pi-clock',
      color: '#5856d6',
      label: t('dashboard.ipInfo.timezone'),
      value: [g.timezone, g.utc_offset && `UTC${g.utc_offset}`].filter(Boolean).join(' · '),
    },
    // OpenStreetMap: the open map
    {
      icon: 'pi-compass',
      color: '#30b0c7',
      label: t('dashboard.ipInfo.coordinates'),
      value: coords,
      mono: true,
      href: coords ? `https://www.openstreetmap.org/?mlat=${g.latitude}&mlon=${g.longitude}#map=10/${g.latitude}/${g.longitude}` : '',
    },
    {
      icon: 'pi-wallet',
      color: '#34c759',
      label: t('dashboard.ipInfo.currency'),
      value: [g.currency, g.currency_name && `(${g.currency_name})`].filter(Boolean).join(' '),
    },
    {
      icon: 'pi-language',
      color: '#af52de',
      label: t('dashboard.ipInfo.languages'),
      value: g.languages,
    },
  ])
})
const abuseRows = computed(() => {
  const a = current.value?.network.abuse
  if (!a) return []
  return rowsOf([
    {
      icon: 'pi-user',
      color: '#8e8e93',
      label: t('dashboard.ipInfo.contactName'),
      value: a.name ?? '',
    },
    {
      icon: 'pi-envelope',
      color: '#007aff',
      label: t('dashboard.ipInfo.email'),
      value: a.email ?? '',
      copy: true,
    },
    {
      icon: 'pi-phone',
      color: '#34c759',
      label: t('dashboard.ipInfo.phone'),
      value: a.phone ?? '',
      copy: true,
    },
    {
      icon: 'pi-home',
      color: '#ff9500',
      label: t('dashboard.ipInfo.address'),
      value: a.address || current.value?.network.owner?.address || '',
    },
  ])
})
const sections = computed(() =>
  [
    {
      key: 'network',
      title: t('dashboard.ipInfo.network'),
      rows: networkRows.value,
    },
    { key: 'asn', title: t('dashboard.ipInfo.asnTitle'), rows: asnRows.value },
    {
      key: 'location',
      title: t('dashboard.ipInfo.location'),
      rows: locationRows.value,
    },
    { key: 'abuse', title: t('dashboard.ipInfo.abuse'), rows: abuseRows.value },
  ].filter((s) => s.rows.length),
)
</script>

<template>
  <Dialog v-model:visible="visible" modal dismissable-mask :draggable="false" :position="isPhone ? 'bottom' : 'center'" class="ip-sheet" :class="{ 'ip-sheet--phone': isPhone }">
    <template #container="{ closeCallback }">
      <div ref="sheet" class="ips" role="document" @touchstart.passive="onTouchStart" @touchmove="onTouchMove" @touchend="onTouchEnd" @touchcancel="onTouchEnd" @click="onIconTap" @animationend="onIconSettled">
        <!-- a phone: the handle to pull the sheet down; elsewhere the close button -->
        <span v-if="isPhone" class="ips__grabber" aria-hidden="true" />
        <button v-else type="button" class="ips__close" :aria-label="t('common.close')" @click="closeCallback">
          <i class="pi pi-times" />
        </button>

        <!-- the server: logo, name, company, waving flag, where it is -->
        <header class="ips__hero">
          <div class="ips__logo" :style="{ '--hue': monogramHue }">
            <img v-if="current?.company.logo" :src="current.company.logo" alt="" />
            <span v-else-if="current">{{ monogram }}</span>
            <i v-else class="pi pi-server" />
          </div>
          <div class="ips__titles">
            <h2 class="ips__name">{{ node?.title }}</h2>
            <p v-if="company" class="ips__company">{{ company }}</p>
            <p v-if="place" class="ips__place"><i class="pi pi-map-marker" />{{ place }}</p>
          </div>
          <FlagIcon v-if="countryCode" class="ips__flag" :code="countryCode" :label="country" waving />
        </header>

        <div class="ips__body">
          <!-- looking up: a soft shimmer of the sheet's shape -->
          <div v-if="loading" class="ips__loading" aria-busy="true">
            <p class="ips__muted"><i class="pi pi-spin pi-spinner" />{{ t('dashboard.ipInfo.loading') }}</p>
            <span v-for="n in 4" :key="n" class="ips__shimmer" />
          </div>
          <div v-else-if="error" class="ips__state">
            <i class="pi pi-exclamation-circle" />
            <p>{{ t('dashboard.ipInfo.failed') }}</p>
            <small>{{ error }}</small>
            <button type="button" class="ips__pill" @click="node && load(node.id)">
              {{ t('dashboard.ipInfo.retry') }}
            </button>
          </div>
          <div v-else-if="info && !info.ips.length" class="ips__state">
            <i class="pi pi-info-circle" />
            <p>{{ t('dashboard.ipInfo.noIps') }}</p>
          </div>

          <template v-else-if="current">
            <!-- IPv4 / IPv6: a segmented control -->
            <div v-if="info!.ips.length > 1" class="ips__segments" role="tablist">
              <button v-for="(ip, i) in info!.ips" :key="ip.ip" type="button" role="tab" :aria-selected="i === selected" class="ips__segment" :class="{ 'ips__segment--on': i === selected }" @click="selected = i">
                IPv{{ ip.version }}<small v-if="info!.ips.filter((x) => x.version === ip.version).length > 1"> {{ i + 1 }}</small>
              </button>
            </div>

            <!-- the address itself -->
            <section class="ips__address">
              <div class="ips__address-main">
                <span class="ips__badge">IPv{{ current.version }}</span>
                <code dir="ltr">{{ current.ip }}</code>
                <button type="button" class="ips__copy" :aria-label="t('dashboard.ipInfo.copy')" @click="copy(current.ip)">
                  <i :class="copied === current.ip ? 'pi pi-check' : 'pi pi-copy'" />
                </button>
              </div>
              <p v-if="current.ptr" class="ips__ptr">
                <span>{{ t('dashboard.ipInfo.ptr') }}</span>
                <code dir="ltr">{{ current.ptr }}</code>
              </p>
            </section>

            <!-- what kind of network -->
            <h3 class="ips__heading">{{ t('dashboard.ipInfo.detection') }}</h3>
            <div class="ips__tiles">
              <div v-for="d in detections" :key="d.key" class="ips__tile" :class="{ 'ips__tile--on': d.on }" :style="{ '--c': d.color }" :data-motion="motionOf(d.icon)">
                <span class="ips__tile-icon"><i class="pi" :class="d.icon" /></span>
                <span class="ips__tile-label">{{ t(`dashboard.ipInfo.det.${d.key}`) }}</span>
                <span class="ips__tile-value">{{ d.value }}</span>
              </div>
            </div>
            <p v-if="current.detect.vpn_likely" class="ips__note"><i class="pi pi-info-circle" />{{ t('dashboard.ipInfo.vpnHint') }}</p>

            <!-- grouped lists, as in iOS Settings -->
            <template v-for="section in sections" :key="section.key">
              <h3 class="ips__heading">{{ section.title }}</h3>
              <ul class="ips__group">
                <li v-for="row in section.rows" :key="row.label" class="ips__row" :data-motion="motionOf(row.icon)">
                  <span class="ips__row-icon" :style="{ background: row.color }"><i class="pi" :class="row.icon" /></span>
                  <span class="ips__row-label">{{ row.label }}</span>
                  <a v-if="row.href" class="ips__row-value ips__row-value--link" :class="{ ips__mono: row.mono }" :href="row.href" target="_blank" rel="noopener" dir="ltr">
                    {{ row.value }} <i class="pi pi-external-link" />
                  </a>
                  <span v-else class="ips__row-value" :class="{ ips__mono: row.mono }" :dir="row.mono ? 'ltr' : undefined">{{ row.value }}</span>
                  <button v-if="row.copy" type="button" class="ips__copy ips__copy--row" :aria-label="t('dashboard.ipInfo.copy')" @click="copy(row.value)">
                    <i :class="copied === row.value ? 'pi pi-check' : 'pi pi-copy'" />
                  </button>
                </li>
              </ul>
            </template>

            <!-- the server's domains in the panel -->
            <h3 class="ips__heading">{{ t('dashboard.ipInfo.domains') }}</h3>
            <div class="ips__group ips__domains">
              <span v-for="d in info!.domains" :key="d" class="ips__domain" dir="ltr"><i class="pi pi-link" />{{ d }}</span>
              <span v-if="!info!.domains.length" class="ips__muted">{{ t('dashboard.ipInfo.noDomains') }}</span>
            </div>

            <footer class="ips__footer">
              <span
                ><i class="pi pi-refresh" />{{
                  t('dashboard.ipInfo.updatedAgo', {
                    when: ago(current.fetched_at),
                    hours: nextLookup,
                  })
                }}</span
              >
              <small>{{ t('dashboard.ipInfo.sources') }}</small>
            </footer>
          </template>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.ips {
  --ips-bg: var(--p-content-background);
  --ips-group: color-mix(in srgb, var(--p-text-color) 4%, var(--ips-bg));
  --ips-line: color-mix(in srgb, var(--p-text-color) 9%, transparent);
  --ips-muted: var(--p-text-muted-color);
  position: relative;
  display: flex;
  flex-direction: column;
  width: min(30rem, 100vw);
  max-height: min(88vh, 52rem);
  overflow: hidden;
  border-radius: 1.75rem;
  background: var(--ips-bg);
  color: var(--p-text-color);
  box-shadow:
    0 30px 80px -20px rgb(0 0 0 / 0.45),
    0 0 0 0.5px color-mix(in srgb, var(--p-text-color) 10%, transparent);
}
.ips__grabber {
  position: absolute;
  top: 0.5rem;
  left: 50%;
  z-index: 2;
  width: 2.9rem;
  height: 0.36rem;
  border-radius: 999px;
  transform: translateX(-50%);
  background: color-mix(in srgb, var(--p-text-color) 38%, transparent);
  box-shadow: 0 0 0 0.5px color-mix(in srgb, var(--ips-bg) 60%, transparent);
}
/* the whole top of the sheet is where a pull starts; no browser scroll or zoom there */
.ip-sheet--phone .ips__hero {
  touch-action: none;
}
.ips__close {
  position: absolute;
  top: 0.85rem;
  inset-inline-end: 0.85rem;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  border: 0;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 9%, transparent);
  color: var(--ips-muted);
  cursor: pointer;
}
.ips__close i {
  font-size: 0.7rem;
}

/* the hero: a soft glow of the company's colour behind the logo */
.ips__hero {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 1.6rem 1.25rem 1.1rem;
  background: radial-gradient(120% 140% at 0% 0%, hsl(var(--hue, 210) 80% 60% / 0.16), transparent 60%), radial-gradient(90% 120% at 100% 0%, color-mix(in srgb, var(--p-primary-color) 12%, transparent), transparent 70%);
}
.ips__logo {
  flex: none;
  display: grid;
  place-items: center;
  width: 3.6rem;
  height: 3.6rem;
  overflow: hidden;
  border-radius: 1rem;
  background: linear-gradient(145deg, hsl(var(--hue, 210) 75% 58%), hsl(calc(var(--hue, 210) + 35) 75% 46%));
  box-shadow:
    0 8px 20px -8px hsl(var(--hue, 210) 70% 40% / 0.6),
    inset 0 0 0 0.5px rgb(255 255 255 / 0.3);
  color: #fff;
  font-size: 1.5rem;
  font-weight: 700;
}
.ips__logo img {
  width: 100%;
  height: 100%;
  padding: 0.45rem;
  object-fit: contain;
  background: #fff;
}
.ips__titles {
  min-width: 0;
  flex: 1;
}
.ips__name {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
}
.ips__company {
  margin: 0.1rem 0 0;
  color: var(--ips-muted);
  font-size: 0.95rem;
  font-weight: 500;
}
.ips__place {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin: 0.3rem 0 0;
  color: var(--ips-muted);
  font-size: 0.85rem;
}
.ips__place i {
  font-size: 0.75rem;
  color: #ff3b30;
}
.ips__flag {
  flex: none;
  align-self: flex-start;
  margin-top: 0.3rem;
  margin-inline-end: 2.1rem;
  font-size: 2.2rem;
}

.ips__body {
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0.25rem 1rem 1.25rem;
}
.ips__heading {
  margin: 1.1rem 0.5rem 0.4rem;
  color: var(--ips-muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

/* segmented control */
.ips__segments {
  display: flex;
  gap: 0.15rem;
  margin: 0.25rem 0 0.75rem;
  padding: 0.15rem;
  border-radius: 0.65rem;
  background: color-mix(in srgb, var(--p-text-color) 7%, transparent);
}
.ips__segment {
  flex: 1;
  padding: 0.35rem 0.5rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: var(--p-text-color);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.2s,
    box-shadow 0.2s;
}
.ips__segment--on {
  background: var(--ips-bg);
  box-shadow: 0 2px 8px -2px rgb(0 0 0 / 0.2);
}

/* the address card */
.ips__address {
  padding: 0.85rem 0.9rem;
  border-radius: 1rem;
  background: var(--ips-group);
}
.ips__address-main {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.ips__address-main code {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.ips__badge {
  flex: none;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: color-mix(in srgb, #007aff 14%, transparent);
  color: #007aff;
  font-size: 0.72rem;
  font-weight: 700;
}
.ips__ptr {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.45rem 0 0;
  color: var(--ips-muted);
  font-size: 0.8rem;
}
.ips__ptr code {
  color: var(--p-text-color);
  overflow-wrap: anywhere;
}
.ips__copy {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  border: 0;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-primary-color) 12%, transparent);
  color: var(--p-primary-color);
  cursor: pointer;
}
.ips__copy i {
  font-size: 0.8rem;
}
.ips__copy--row {
  width: 1.6rem;
  height: 1.6rem;
  background: transparent;
}

/* detection tiles */
.ips__tiles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}
.ips__tile {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.7rem 0.7rem 0.6rem;
  border-radius: 1rem;
  background: var(--ips-group);
  transition: transform 0.2s;
}
.ips__tile-icon {
  display: grid;
  place-items: center;
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 0.6rem;
  background: color-mix(in srgb, var(--c) 16%, transparent);
  color: var(--c);
}
.ips__tile--on .ips__tile-icon {
  background: var(--c);
  color: #fff;
  box-shadow: 0 6px 14px -6px var(--c);
}
.ips__tile-icon i {
  font-size: 0.9rem;
}
.ips__tile-label {
  color: var(--ips-muted);
  font-size: 0.75rem;
  line-height: 1.2;
}
.ips__tile-value {
  font-size: 0.9rem;
  font-weight: 650;
}
.ips__tile--on .ips__tile-value {
  color: var(--c);
}
.ips__note {
  display: flex;
  gap: 0.4rem;
  margin: 0.55rem 0.4rem 0;
  color: var(--ips-muted);
  font-size: 0.75rem;
  line-height: 1.4;
}

/* grouped list */
.ips__group {
  margin: 0;
  padding: 0;
  list-style: none;
  border-radius: 1rem;
  background: var(--ips-group);
  overflow: hidden;
}
.ips__row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 2.75rem;
  padding: 0.45rem 0.85rem;
}
.ips__row + .ips__row {
  box-shadow: inset 0 0.5px 0 var(--ips-line);
}
.ips__row-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.5rem;
  color: #fff;
}
.ips__row-icon i {
  font-size: 0.8rem;
}
.ips__row-label {
  flex: none;
  font-size: 0.9rem;
}
.ips__row-value {
  flex: 1;
  min-width: 0;
  color: var(--ips-muted);
  font-size: 0.88rem;
  text-align: end;
  overflow-wrap: anywhere;
}
.ips__row-value--link {
  color: var(--p-primary-color);
  text-decoration: none;
}
.ips__row-value--link i {
  font-size: 0.65rem;
}
.ips__mono {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 0.82rem;
}

.ips__domains {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0.7rem;
}
.ips__domain {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-primary-color) 10%, transparent);
  color: var(--p-primary-color);
  font-size: 0.8rem;
  font-weight: 500;
}
.ips__domain i {
  font-size: 0.65rem;
}

.ips__footer {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 1rem 0.5rem 0;
  color: var(--ips-muted);
  font-size: 0.75rem;
  text-align: center;
}
.ips__footer span {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: 0.35rem;
}
.ips__footer i {
  font-size: 0.65rem;
}

.ips__muted {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0;
  color: var(--ips-muted);
  font-size: 0.85rem;
}
.ips__loading {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding-top: 0.5rem;
}
.ips__shimmer {
  height: 3.2rem;
  border-radius: 1rem;
  background: linear-gradient(100deg, var(--ips-group) 30%, color-mix(in srgb, var(--p-text-color) 9%, var(--ips-bg)) 50%, var(--ips-group) 70%);
  background-size: 200% 100%;
  animation: ips-shimmer 1.4s ease-in-out infinite;
}
@keyframes ips-shimmer {
  to {
    background-position: -200% 0;
  }
}
.ips__state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  padding: 1.5rem 0.5rem;
  text-align: center;
}
.ips__state > i {
  font-size: 1.6rem;
  color: var(--ips-muted);
}
.ips__state p {
  margin: 0;
  font-weight: 600;
}
.ips__state small {
  color: var(--ips-muted);
}
.ips__pill {
  margin-top: 0.4rem;
  padding: 0.45rem 1rem;
  border: 0;
  border-radius: 999px;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font-weight: 600;
  cursor: pointer;
}

@media (max-width: 640px) {
  .ips {
    width: 100vw;
    max-height: 90vh;
    border-radius: 1.75rem 1.75rem 0 0;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
  .ips__tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
/* Desktop: an icon comes alive only while the mouse is on that icon: its glyph moves softly in its own way; the
   icon's tile itself never grows or moves */
@media (hover: hover) and (pointer: fine) {
  :is(.ips__row-icon, .ips__tile-icon) i {
    transition: transform 0.4s ease;
  }
  :is(.ips__row-icon, .ips__tile-icon):hover i {
    animation: ips-float 1.8s ease-in-out infinite;
  }
  [data-motion='spin'] :is(.ips__row-icon, .ips__tile-icon):hover i {
    animation: ips-spin 3s cubic-bezier(0.45, 0, 0.55, 1) infinite;
  }
  [data-motion='bounce'] :is(.ips__row-icon, .ips__tile-icon):hover i {
    animation: ips-bounce 1.6s cubic-bezier(0.33, 0, 0.3, 1) infinite;
  }
  [data-motion='wiggle'] :is(.ips__row-icon, .ips__tile-icon):hover i {
    animation: ips-wiggle 1.8s ease-in-out infinite;
  }
  [data-motion='tick'] :is(.ips__row-icon, .ips__tile-icon):hover i {
    animation: ips-tick 2.4s ease-in-out infinite;
  }
  [data-motion='slide'] :is(.ips__row-icon, .ips__tile-icon):hover i {
    animation: ips-slide 1.8s ease-in-out infinite;
  }
}
/* A touch screen: a tap on an icon plays the same motion for about 2.6 seconds, then it ends by itself */
:is(.ips__row-icon, .ips__tile-icon).ips-alive i {
  animation: ips-float 1.3s ease-in-out 2;
}
[data-motion='spin'] :is(.ips__row-icon, .ips__tile-icon).ips-alive i {
  animation: ips-spin 2.6s cubic-bezier(0.45, 0, 0.55, 1) 1;
}
[data-motion='bounce'] :is(.ips__row-icon, .ips__tile-icon).ips-alive i {
  animation: ips-bounce 1.3s cubic-bezier(0.33, 0, 0.3, 1) 2;
}
[data-motion='wiggle'] :is(.ips__row-icon, .ips__tile-icon).ips-alive i {
  animation: ips-wiggle 1.3s ease-in-out 2;
}
[data-motion='tick'] :is(.ips__row-icon, .ips__tile-icon).ips-alive i {
  animation: ips-tick 1.3s ease-in-out 2;
}
[data-motion='slide'] :is(.ips__row-icon, .ips__tile-icon).ips-alive i {
  animation: ips-slide 1.3s ease-in-out 2;
}
@media (hover: none), (pointer: coarse) {
  .ips__row-icon,
  .ips__tile-icon {
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
}
@keyframes ips-spin {
  to {
    transform: rotate(360deg);
  }
}
@keyframes ips-bounce {
  0%,
  55%,
  100% {
    transform: translateY(0);
  }
  25% {
    transform: translateY(-2.5px);
  }
  40% {
    transform: translateY(-0.8px);
  }
}
@keyframes ips-wiggle {
  0%,
  50%,
  100% {
    transform: rotate(0);
  }
  15% {
    transform: rotate(-10deg);
  }
  35% {
    transform: rotate(8deg);
  }
}
@keyframes ips-tick {
  0%,
  100% {
    transform: rotate(0);
  }
  50% {
    transform: rotate(20deg);
  }
}
@keyframes ips-float {
  50% {
    transform: translateY(-2px);
  }
}
@keyframes ips-slide {
  25% {
    transform: translateX(-2px);
  }
  75% {
    transform: translateX(2px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ips__shimmer,
  .ips__row-icon,
  .ips__tile-icon,
  .ips__row-icon i,
  .ips__tile-icon i {
    animation: none !important;
  }
}
</style>

<style>
/* The dialog itself (teleported to the body): no frame of its own, and an iOS entrance: a sheet that springs up
   from the bottom on a phone, a card that grows in elsewhere. The glass theme makes it glass. */
.p-dialog.ip-sheet {
  border: 0;
  background: transparent;
  box-shadow: none;
  max-height: none;
}
.p-dialog-bottom .p-dialog.ip-sheet {
  margin: 0;
}
.p-dialog.ip-sheet.p-dialog-enter-active {
  animation: ip-sheet-in 0.5s cubic-bezier(0.32, 0.72, 0, 1);
}
.p-dialog.ip-sheet.p-dialog-leave-active {
  animation: ip-sheet-out 0.28s cubic-bezier(0.4, 0, 1, 1) forwards;
}
.p-dialog.ip-sheet--phone.p-dialog-enter-active {
  animation: ip-sheet-up 0.5s cubic-bezier(0.32, 0.72, 0, 1);
}
.p-dialog.ip-sheet--phone.p-dialog-leave-active {
  animation: ip-sheet-down 0.3s cubic-bezier(0.4, 0, 1, 1) forwards;
}
@keyframes ip-sheet-in {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.92);
  }
}
@keyframes ip-sheet-out {
  to {
    opacity: 0;
    transform: scale(0.95);
  }
}
@keyframes ip-sheet-up {
  from {
    transform: translateY(100%);
  }
}
@keyframes ip-sheet-down {
  to {
    transform: translateY(100%);
  }
}
html.theme-liquid .p-dialog.ip-sheet .ips {
  --ips-bg: rgb(var(--lg-tint) / 0.72);
  --ips-group: rgb(var(--lg-tint) / 0.55);
  -webkit-backdrop-filter: blur(var(--lg-blur-float)) saturate(var(--lg-saturate));
  backdrop-filter: blur(var(--lg-blur-float)) saturate(var(--lg-saturate));
  box-shadow:
    inset 0 1px 0 var(--lg-rim),
    var(--lg-shadow-float);
}
@media (prefers-reduced-motion: reduce) {
  .p-dialog.ip-sheet.p-dialog-enter-active,
  .p-dialog.ip-sheet.p-dialog-leave-active {
    animation-duration: 0.01s;
  }
}
</style>
