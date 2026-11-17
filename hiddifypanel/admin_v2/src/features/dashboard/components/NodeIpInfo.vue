<script setup lang="ts">
/**
 * A server's or node's IP addresses in one sheet, in the style of iOS: the company's logo and the country's waving
 * flag, each address, what kind of network it is, who runs it, where it is, the abuse contact and the server's
 * domains, and under "Complete IP Info" the flags of each address, by category. The panel looks the addresses up in
 * open sources and keeps the answer 7 days; this browser keeps it as long, so opening the sheet again asks nobody.
 * A bottom sheet on a phone, a card in the middle elsewhere.
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import FlagIcon from '@/shared/components/FlagIcon.vue'
import LiveIcon from './LiveIcon.vue'
import IpLocationMap from './IpLocationMap.vue'
import ServerLogo from './ServerLogo.vue'
import { countryName } from '@/shared/utils/country'
import { apiErrorMessage } from '@/core/api/client'
import { nodesApi, type IpDetails, type NodeIpInfo } from '@/features/nodes/api'
import { companyLogo, logoColor } from '../company-logos'

const props = defineProps<{ node: { id: number; title: string } | null }>()
const visible = defineModel<boolean>('visible', { default: false })

const { t, locale } = useI18n()

const info = ref<NodeIpInfo | null>(null)
const loading = ref(false)
const error = ref('')
const selected = ref(0)
const completeOpen = ref(false)
const copied = ref('')
let copiedTimer = 0

const phone = window.matchMedia('(max-width: 640px)')
const isPhone = ref(phone.matches)
const onPhone = () => (isPhone.value = phone.matches)
phone.addEventListener('change', onPhone)
onBeforeUnmount(() => phone.removeEventListener('change', onPhone))

// --- the answer, kept in this browser until the panel would look it up again ---------------------------------
const STORE = 'hm.ipinfo.v4.'
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
      // Complete IP Info starts closed each time the sheet opens
      completeOpen.value = false
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
/** A colour of the company's own (from its name), for its tag and the hero's glow when it has no brand colour */
const monogramHue = computed(() => [...company.value].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 360, 210))
/** A well-known company's vector logo (sharp at any size); others keep their website's icon */
const vectorLogo = computed(() => (current.value ? companyLogo(current.value.company.domain, company.value) : undefined))
const vectorLogoStyle = computed(() =>
  vectorLogo.value ? { '--logo-light': logoColor(vectorLogo.value.icon.hex, false), '--logo-dark': logoColor(vectorLogo.value.icon.hex, true) } : {},
)
/** The company name's faint tag: the brand's colour, else the colour of its initial */
const companyTint = computed(() => {
  const hex = vectorLogo.value?.icon.hex
  return hex
    ? { '--tint': logoColor(hex, false), '--tint-dark': logoColor(hex, true) }
    : { '--tint': `hsl(${monogramHue.value} 65% 46%)`, '--tint-dark': `hsl(${monogramHue.value} 70% 62%)` }
})

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

/**
 * The icons come alive (LiveIcon): on a desktop while the mouse is on that icon; on a touch screen a tap plays it once
 * through (about 2.6 s) and it ends where it started. Only the icon's parts move, never its size.
 */
const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)')
const ICON = '.ips__row-icon, .ips__tile-icon'
const iconOf = (target: EventTarget | null) => (target instanceof Element ? target.closest<HTMLElement>(ICON) : null)
function onIconOver(e: MouseEvent) {
  if (finePointer.matches) iconOf(e.target)?.classList.add('is-live')
}
function onIconOut(e: MouseEvent) {
  const icon = iconOf(e.target)
  if (finePointer.matches && icon && !icon.contains(e.relatedTarget as Node | null)) icon.classList.remove('is-live')
}
function onIconTap(e: MouseEvent) {
  if (finePointer.matches) return
  const icon = iconOf(e.target)
  if (!icon || icon.classList.contains('is-live')) return
  icon.classList.add('is-live', 'is-tap')
  window.setTimeout(() => icon.classList.remove('is-live', 'is-tap'), 2800)
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
/** When the panel looks the address up again: a week after it last did */
const nextLookup = computed(() => (info.value && current.value ? ago(current.value.fetched_at + info.value.ttl) : ''))

// --- Complete IP Info: the flags of the address, by category -------------------------------------------------------
type Tone = 'neutral' | 'bad'
interface FlagDef {
  key: string
  /** The flag's own name, the same in every language */
  name: string
  icon: string
  /** read from names and numbers, so a yes is only a "likely" */
  likely?: boolean
  /** a yes is a problem (red), else it is just a fact (blue) */
  tone?: Tone
  source: string
}
const FLAG_GROUPS: { key: string; color: string; flags: FlagDef[] }[] = [
  {
    key: 'network',
    color: '#007aff',
    flags: [
      { key: 'bogon', name: 'Bogon', icon: 'x-bogon', tone: 'bad', source: 'local' },
      { key: 'datacenter', name: 'Datacenter / Hosting', icon: 'pi-server', source: 'hosting' },
      { key: 'mobile', name: 'Mobile', icon: 'pi-mobile', likely: true, source: 'asName' },
      { key: 'satellite', name: 'Satellite', icon: 'x-satellite', likely: true, source: 'asName' },
      { key: 'anycast', name: 'Anycast', icon: 'x-anycast', likely: true, source: 'asName' },
      { key: 'dsl_dynamic', name: 'DSL Dynamic', icon: 'x-dsl', likely: true, source: 'ptr' },
      { key: 'ipfs', name: 'IPFS Node', icon: 'x-ipfs', source: 'port' },
    ],
  },
  {
    key: 'anonymity',
    color: '#af52de',
    flags: [
      { key: 'proxy', name: 'Proxy', icon: 'x-proxy', likely: true, source: 'datacenter' },
      { key: 'vpn', name: 'VPN', icon: 'pi-shield', likely: true, source: 'datacenter' },
      { key: 'tor', name: 'Tor', icon: 'x-onion', source: 'tor' },
      { key: 'relay', name: 'Relay / iCloud Relay', icon: 'x-relay', source: 'apple' },
      { key: 'anonymous', name: 'Anonymous', icon: 'x-mask', source: 'anonymous' },
      { key: 'active_tor', name: 'Active Tor', icon: 'x-active-tor', source: 'onionoo' },
    ],
  },
  {
    key: 'threats',
    color: '#ff3b30',
    flags: [
      { key: 'crawler', name: 'Crawler', icon: 'x-spider', source: 'crawlers' },
      { key: 'abuser', name: 'Abuser', icon: 'x-warning', tone: 'bad', source: 'blocklists' },
      { key: 'known_abuser', name: 'Known Abuser', icon: 'x-blocked', tone: 'bad', source: 'spamhaus' },
      { key: 'threat', name: 'Threat', icon: 'x-bug', tone: 'bad', source: 'abusech' },
      { key: 'attacker', name: 'Attacker', icon: 'pi-bolt', tone: 'bad', source: 'netapi' },
      { key: 'security_scanner', name: 'Security Scanner', icon: 'x-radar', likely: true, source: 'ptrAs' },
    ],
  },
  {
    key: 'web',
    color: '#34c759',
    flags: [
      { key: 'tor_exit', name: 'Tor Exit Node', icon: 'x-exit', source: 'tor' },
      { key: 'open_directory', name: 'Open Directory', icon: 'x-folder', tone: 'bad', source: 'webRoot' },
      { key: 'expired_certificate', name: 'Expired Certificate', icon: 'x-cert', tone: 'bad', source: 'tls' },
    ],
  },
]
const ICON_COLORS = ['#007aff', '#5856d6', '#af52de', '#ff9500', '#30b0c7', '#34c759', '#ff2d55', '#5ac8fa']
watch(selected, () => (completeOpen.value = completeOpen.value && !!current.value?.complete))

/**
 * Opening Complete IP Info glides the sheet down so the section comes into view as it unfolds; closing glides it back
 * to where it was. Our own easing (the iOS curve), so it is as soft in every browser.
 */
const moreButton = ref<HTMLElement | null>(null)
let scrollBefore = 0
let glideFrame = 0
function glide(el: HTMLElement, to: number, ms = 560) {
  cancelAnimationFrame(glideFrame)
  const from = el.scrollTop
  const start = performance.now()
  const ease = (x: number) => 1 - Math.pow(1 - x, 3.2)
  const step = (now: number) => {
    const k = Math.min(1, (now - start) / ms)
    el.scrollTop = from + (to - from) * ease(k)
    if (k < 1) glideFrame = requestAnimationFrame(step)
  }
  glideFrame = requestAnimationFrame(step)
}
function toggleComplete() {
  const body = sheet.value?.querySelector<HTMLElement>('.ips__body')
  const opening = !completeOpen.value
  completeOpen.value = opening
  if (!body) return
  if (opening) {
    scrollBefore = body.scrollTop
    // the button near the top of the sheet, the section unfolding under it
    const button = moreButton.value?.getBoundingClientRect()
    const target = button ? body.scrollTop + button.top - body.getBoundingClientRect().top - 14 : body.scrollTop
    void nextTick(() => glide(body, Math.max(0, target)))
  } else {
    glide(body, Math.min(scrollBefore, body.scrollTop))
  }
}

/** A flag's state for the badge: yes / likely / no / not checked */
function stateOf(def: FlagDef): { label: string; kind: 'yes' | 'bad' | 'likely' | 'no' | 'unknown' } {
  const value = current.value?.complete?.flags[def.key]
  if (value == null) return { label: t('dashboard.ipInfo.notChecked'), kind: 'unknown' }
  if (!value) return { label: t('dashboard.ipInfo.no'), kind: 'no' }
  if (def.likely) return { label: t('dashboard.ipInfo.likely'), kind: 'likely' }
  return { label: t('dashboard.ipInfo.yes'), kind: def.tone === 'bad' ? 'bad' : 'yes' }
}
/** The detail under a flag, when there is one: the certificates, the Tor relay's name, the crawler's owner */
function detailOf(def: FlagDef): string[] {
  const c = current.value?.complete
  if (!c) return []
  if (def.key === 'expired_certificate')
    return c.certificates.map((x) => `${x.name || t('dashboard.ipInfo.defaultCert')} · ${x.expired ? t('dashboard.ipInfo.expiredOn', { date: x.not_after }) : t('dashboard.ipInfo.validUntil', { date: x.not_after })}`)
  if ((def.key === 'tor' || def.key === 'active_tor') && c.tor_relay.nickname) return [t('dashboard.ipInfo.relayName', { name: c.tor_relay.nickname })]
  if (def.key === 'crawler' && c.crawler) return [c.crawler]
  return []
}
/** How many flags of a group are up (a problem first), for the group's header */
function upCount(flags: FlagDef[]): number {
  return flags.filter((f) => current.value?.complete?.flags[f.key]).length
}

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
      <div
        ref="sheet"
        class="ips"
        role="document"
        @touchstart.passive="onTouchStart"
        @touchmove="onTouchMove"
        @touchend="onTouchEnd"
        @touchcancel="onTouchEnd"
        @click="onIconTap"
        @mouseover="onIconOver"
        @mouseout="onIconOut"
      >
        <!-- a phone: the handle to pull the sheet down; elsewhere the close button -->
        <span v-if="isPhone" class="ips__grabber" aria-hidden="true" />
        <button v-else type="button" class="ips__close" :aria-label="t('common.close')" @click="closeCallback">
          <i class="pi pi-times" />
        </button>

        <!-- the server: logo, name, company, waving flag, where it is -->
        <header class="ips__hero">
          <div class="ips__logo" :class="{ 'ips__logo--bare': current }" :style="{ '--hue': monogramHue, ...vectorLogoStyle }">
            <svg v-if="vectorLogo" viewBox="0 0 24 24" role="img" :aria-label="vectorLogo.icon.title"><path :d="vectorLogo.icon.path" /></svg>
            <img v-else-if="current?.company.logo" :src="current.company.logo" alt="" />
            <ServerLogo v-else-if="current" />
            <i v-else class="pi pi-server" />
          </div>
          <div class="ips__titles">
            <h2 class="ips__name">{{ node?.title }}</h2>
            <p v-if="company" class="ips__company" :style="companyTint">
              <svg class="ips__company-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4.5 21V5.6c0-.9.6-1.6 1.5-1.8l7-1.5c1.1-.2 2 .6 2 1.7V21M15 9h3.2c.9 0 1.8.8 1.8 1.8V21M2.8 21h18.4" />
                <path d="M8 7.5h3.5M8 11h3.5M8 14.5h3.5M17.2 13h.01M17.2 16.5h.01" />
              </svg>
              <span>{{ company }}</span>
            </p>
            <p v-if="place" class="ips__place"><IpLocationMap :lat="current?.geo.latitude" :lon="current?.geo.longitude" :place="place" :city="current?.geo.city" />{{ place }}</p>
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
              <div v-for="d in detections" :key="d.key" class="ips__tile" :class="{ 'ips__tile--on': d.on }" :style="{ '--c': d.color }">
                <span class="ips__tile-icon"><LiveIcon :name="d.icon" /></span>
                <span class="ips__tile-label">{{ t(`dashboard.ipInfo.det.${d.key}`) }}</span>
                <span class="ips__tile-value">{{ d.value }}</span>
              </div>
            </div>
            <p v-if="current.detect.vpn_likely" class="ips__note"><i class="pi pi-info-circle" />{{ t('dashboard.ipInfo.vpnHint') }}</p>

            <!-- Complete IP Info: every flag of the address, opened in place -->
            <template v-if="current.complete">
              <button ref="moreButton" type="button" class="ips__more" :class="{ 'ips__more--open': completeOpen }" :aria-expanded="completeOpen" @click="toggleComplete">
                <span>Complete IP Info</span>
                <span class="ips__more-arrow"><i class="pi pi-chevron-down" /></span>
              </button>
              <div class="ips__complete" :class="{ 'ips__complete--open': completeOpen }">
                <div class="ips__complete-inner">
                  <template v-for="group in FLAG_GROUPS" :key="group.key">
                    <h3 class="ips__heading ips__heading--group">
                      <span class="ips__group-dot" :style="{ background: group.color }" />
                      {{ t(`dashboard.ipInfo.groups.${group.key}`) }}
                      <span v-if="upCount(group.flags)" class="ips__group-count">{{ upCount(group.flags) }}</span>
                    </h3>
                    <ul class="ips__group">
                      <li v-for="(def, i) in group.flags" :key="def.key" class="ips__flag-row">
                        <span class="ips__row-icon" :style="{ background: ICON_COLORS[(i + group.key.length) % ICON_COLORS.length], '--li-ink': ICON_COLORS[(i + group.key.length) % ICON_COLORS.length] }"
                          ><LiveIcon :name="def.icon"
                        /></span>
                        <span class="ips__flag-text">
                          <span class="ips__flag-name">{{ def.name }}</span>
                          <span class="ips__flag-desc">{{ t(`dashboard.ipInfo.flags.${def.key}`) }}</span>
                          <span v-for="line in detailOf(def)" :key="line" class="ips__flag-detail" dir="ltr">{{ line }}</span>
                          <span class="ips__flag-source">{{ t(`dashboard.ipInfo.src.${def.source}`) }}</span>
                        </span>
                        <span class="ips__flag-state" :class="`ips__flag-state--${stateOf(def).kind}`">{{ stateOf(def).label }}</span>
                      </li>
                    </ul>
                  </template>
                </div>
              </div>
            </template>

            <!-- grouped lists, as in iOS Settings -->
            <template v-for="section in sections" :key="section.key">
              <h3 class="ips__heading">{{ section.title }}</h3>
              <ul class="ips__group">
                <li v-for="row in section.rows" :key="row.label" class="ips__row">
                  <span class="ips__row-icon" :style="{ background: row.color, '--li-ink': row.color }"><LiveIcon :name="row.icon" /></span>
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
                    next: nextLookup,
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
/* a logo stands on its own, no tile behind it: only a very light shadow */
.ips__logo--bare {
  overflow: visible;
  border-radius: 0;
  background: none;
  box-shadow: none;
}
.ips__logo svg,
.ips__logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 1px 1.5px rgb(0 0 0 / 0.12));
}
.ips__logo svg {
  fill: var(--logo-light);
}
html.app-dark .ips__logo svg {
  fill: var(--logo-dark);
}
html.app-dark .ips__logo svg,
html.app-dark .ips__logo img {
  filter: drop-shadow(0 1px 1.5px rgb(0 0 0 / 0.35));
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
/* the company's name in a faint tag of its colour: a label, not a button (no shadow, no hover). Its icon and the
   place's pin below share one column (--ips-lead-*), so the two lines' icons and texts start at the same place. */
.ips__hero {
  --ips-lead-pad: 0.42rem;
  --ips-lead-icon: 1.05rem;
  --ips-lead-gap: 0.32rem;
}
.ips__company {
  display: inline-flex;
  align-items: center;
  gap: var(--ips-lead-gap);
  max-width: 100%;
  margin: 0.3rem 0 0;
  padding: 0.16rem 0.75rem 0.16rem var(--ips-lead-pad);
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--tint) 6%, transparent);
  /* the outline as an inset shadow: it takes no room, so the text lines up exactly with the place's below */
  box-shadow: inset 0 0 0 0.5px color-mix(in srgb, var(--tint) 16%, transparent);
  color: color-mix(in srgb, var(--tint) 35%, var(--ips-muted));
  font-size: 1rem;
  font-weight: 550;
  line-height: 1.45;
  white-space: nowrap;
  vertical-align: top;
}
.ips__company span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ips__company-icon {
  flex: none;
  width: var(--ips-lead-icon);
  height: 0.95rem;
  fill: none;
  stroke: color-mix(in srgb, var(--tint) 70%, var(--ips-muted));
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}
html.app-dark .ips__company-icon {
  stroke: color-mix(in srgb, var(--tint-dark) 75%, var(--ips-muted));
}
html.app-dark .ips__company {
  background: color-mix(in srgb, var(--tint-dark) 9%, transparent);
  box-shadow: inset 0 0 0 0.5px color-mix(in srgb, var(--tint-dark) 22%, transparent);
  color: color-mix(in srgb, var(--tint-dark) 40%, var(--ips-muted));
}
.ips__place {
  display: flex;
  align-items: center;
  gap: var(--ips-lead-gap);
  margin: 0.3rem 0 0;
  padding-inline-start: var(--ips-lead-pad);
  color: var(--ips-muted);
  font-size: 0.85rem;
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
/* the drawn icons fill a little more of their tile, so their moving parts can be seen */
.ips__tile-icon .li {
  font-size: 1.15rem;
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
.ips__row-icon .li {
  font-size: 1.05rem;
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

/* Complete IP Info: the button, and the flags it opens in place */
/* Complete IP Info: a small pill in the middle, its arrow in a little circle that turns as the section opens */
.ips__more {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0.85rem auto 0;
  padding: 0.32rem 0.38rem 0.32rem 0.85rem;
  border: 0.5px solid color-mix(in srgb, var(--p-primary-color) 22%, transparent);
  border-radius: 999px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--p-primary-color) 9%, var(--ips-bg)), color-mix(in srgb, var(--p-primary-color) 15%, var(--ips-bg)));
  box-shadow:
    0 4px 12px -6px color-mix(in srgb, var(--p-primary-color) 55%, transparent),
    inset 0 1px 0 rgb(255 255 255 / 0.35);
  color: var(--p-primary-color);
  font-size: 0.8rem;
  font-weight: 650;
  letter-spacing: -0.005em;
  cursor: pointer;
  transition:
    box-shadow 0.25s,
    background 0.25s,
    transform 0.2s;
}
html[dir='rtl'] .ips__more {
  padding: 0.32rem 0.85rem 0.32rem 0.38rem;
}
.ips__more:hover {
  box-shadow:
    0 6px 16px -6px color-mix(in srgb, var(--p-primary-color) 65%, transparent),
    inset 0 1px 0 rgb(255 255 255 / 0.35);
}
.ips__more:active {
  transform: scale(0.97);
}
.ips__more-arrow {
  display: grid;
  place-items: center;
  width: 1.3rem;
  height: 1.3rem;
  border-radius: 999px;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color, #fff);
  transition: transform 0.45s cubic-bezier(0.32, 0.72, 0, 1);
}
.ips__more-arrow i {
  font-size: 0.6rem;
}
.ips__more--open .ips__more-arrow {
  transform: rotate(180deg);
}
.ips__complete {
  display: grid;
  grid-template-rows: 0fr;
  opacity: 0;
  transition:
    grid-template-rows 0.55s cubic-bezier(0.32, 0.72, 0, 1),
    opacity 0.4s ease;
}
.ips__complete--open {
  grid-template-rows: 1fr;
  opacity: 1;
}
.ips__complete-inner {
  min-height: 0;
  overflow: hidden;
}
.ips__heading--group {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}
.ips__group-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
}
.ips__group-count {
  padding: 0 0.4rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 10%, transparent);
  color: var(--p-text-color);
  font-size: 0.7rem;
  letter-spacing: 0;
}
.ips__flag-row {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding: 0.65rem 0.85rem;
}
.ips__flag-row + .ips__flag-row {
  box-shadow: inset 0 0.5px 0 var(--ips-line);
}
.ips__flag-row .ips__row-icon {
  margin-top: 0.1rem;
}
.ips__flag-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.12rem;
  min-width: 0;
}
.ips__flag-name {
  font-size: 0.92rem;
  font-weight: 600;
}
.ips__flag-desc {
  color: var(--ips-muted);
  font-size: 0.8rem;
  line-height: 1.35;
}
.ips__flag-detail {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 0.74rem;
  overflow-wrap: anywhere;
}
.ips__flag-source {
  color: color-mix(in srgb, var(--ips-muted) 75%, transparent);
  font-size: 0.68rem;
}
.ips__flag-state {
  flex: none;
  align-self: center;
  padding: 0.18rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 650;
  white-space: nowrap;
}
.ips__flag-state--yes {
  background: color-mix(in srgb, #007aff 14%, transparent);
  color: #007aff;
}
.ips__flag-state--bad {
  background: color-mix(in srgb, #ff3b30 14%, transparent);
  color: #ff3b30;
}
.ips__flag-state--likely {
  background: color-mix(in srgb, #ff9500 16%, transparent);
  color: #e08600;
}
.ips__flag-state--no {
  background: color-mix(in srgb, #34c759 14%, transparent);
  color: #248a3d;
}
.ips__flag-state--unknown {
  background: color-mix(in srgb, var(--p-text-color) 8%, transparent);
  color: var(--ips-muted);
}
html.app-dark .ips__flag-state--no {
  color: #30d158;
}
html.app-dark .ips__flag-state--likely {
  color: #ff9f0a;
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
@media (prefers-reduced-motion: reduce) {
  .ips__shimmer {
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
/* Smart Caddy: its page colour is a thin glass (half white), which over the dimmed page read grey; the sheet takes the
   theme's strong glass, bright as in the Liquid theme */
html.theme-caddy .p-dialog.ip-sheet .ips {
  --ips-bg: var(--caddy-glass-strong);
  --ips-group: color-mix(in srgb, var(--p-text-color) 5%, transparent);
  -webkit-backdrop-filter: blur(24px) saturate(1.6);
  backdrop-filter: blur(24px) saturate(1.6);
}
html.theme-liquid .p-dialog.ip-sheet .ips {
  --ips-bg: rgb(var(--lg-tint) / 0.72);
  /* Apple's grouped cells on glass: a grey fill of their own (the system fill), not more of the sheet's white, which
     made them vanish into it */
  --ips-group: rgb(120 120 128 / 0.12);
  -webkit-backdrop-filter: blur(var(--lg-blur-float)) saturate(var(--lg-saturate));
  backdrop-filter: blur(var(--lg-blur-float)) saturate(var(--lg-saturate));
  box-shadow:
    inset 0 1px 0 var(--lg-rim),
    var(--lg-shadow-float);
}
html.theme-liquid.app-dark .p-dialog.ip-sheet .ips {
  --ips-group: rgb(118 118 128 / 0.24);
}
/* each cell a pane of glass: a light rim along its top edge and a hairline round it */
html.theme-liquid .p-dialog.ip-sheet :is(.ips__address, .ips__tile, .ips__group) {
  box-shadow:
    inset 0 1px 0 var(--lg-rim),
    inset 0 0 0 0.5px rgb(0 0 0 / 0.06);
}
html.theme-liquid.app-dark .p-dialog.ip-sheet :is(.ips__address, .ips__tile, .ips__group) {
  box-shadow:
    inset 0 1px 0 var(--lg-rim),
    inset 0 0 0 0.5px rgb(255 255 255 / 0.07);
}
/* the segmented control: a grey track and a bright glass lens on the chosen side */
html.theme-liquid .p-dialog.ip-sheet .ips__segments {
  background: rgb(120 120 128 / 0.16);
}
html.theme-liquid .p-dialog.ip-sheet .ips__segment--on {
  background: rgb(var(--lg-tint) / 0.95);
  box-shadow:
    inset 0 1px 0 var(--lg-rim),
    0 3px 10px -3px rgb(0 0 0 / 0.22);
}
html.theme-liquid.app-dark .p-dialog.ip-sheet .ips__segment--on {
  background: rgb(255 255 255 / 0.16);
}
@media (prefers-reduced-motion: reduce) {
  .p-dialog.ip-sheet.p-dialog-enter-active,
  .p-dialog.ip-sheet.p-dialog-leave-active {
    animation-duration: 0.01s;
  }
}
</style>
