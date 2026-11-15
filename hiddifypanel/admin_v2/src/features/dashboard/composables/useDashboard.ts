import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { dashboardApi, type DashboardNode, type DashboardNodeStats, type DashboardSnapshot } from '@/core/api/generated'
import { liveWatch, type Subscription } from '@/core/live/live'
import { useMetricHistory } from './useMetricHistory'
import { API_DAYS, MAX_DAYS, QUICK_PRESETS, addDays, daysBetween, fromIso, iso, presetRange, today, type CustomRange } from '../utils/date-range'

/** Ranges the dashboard API accepts for the usage/users history charts. */
export const RANGE_OPTIONS = [7, 30, 90, 180] as const
export const DEFAULT_RANGE = 30
/** Live server metrics refresh; the usage aggregation is much cheaper to refresh slowly (and at once when users or nodes change). */
export const SYSTEM_REFRESH_MS = 5000
export const ANALYTICS_REFRESH_MS = 60000

const RANGE_STORAGE_KEY = 'admin_v2_dashboard_range'
const NODE_STORAGE_KEY = 'admin_v2_dashboard_node'
const CUSTOM_STORAGE_KEY = 'admin_v2_dashboard_custom_range'
const DAY = /^\d{4}-\d{2}-\d{2}$/

/** A picked period kept from the last visit: a preset is worked out again for today, fixed days stay as they were */
function storedCustom(locale: string): CustomRange | null {
  try {
    const raw = JSON.parse(localStorage.getItem(CUSTOM_STORAGE_KEY) ?? 'null') as CustomRange | null
    if (!raw) return null
    if (raw.preset && (QUICK_PRESETS as readonly string[]).includes(raw.preset)) return presetRange(raw.preset, locale)
    return DAY.test(raw.start) && DAY.test(raw.end) && raw.start <= raw.end ? { start: raw.start, end: raw.end } : null
  } catch {
    return null
  }
}

function storedRange(): number {
  const stored = Number(localStorage.getItem(RANGE_STORAGE_KEY))
  return (RANGE_OPTIONS as readonly number[]).includes(stored) ? stored : DEFAULT_RANGE
}

/** `?debug_node=1` on the page is forwarded to the API to simulate a multi-node panel. */
function debugNodes(): boolean {
  return ['1', 'true', 'yes'].includes(new URLSearchParams(window.location.search).get('debug_node')?.toLowerCase() ?? '')
}

function storedNode(): number | null {
  const raw = localStorage.getItem(NODE_STORAGE_KEY)
  if (raw === null || raw === '' || raw === 'all') return null
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * Single source of truth for the dashboard, pushed over the live channel: server metrics on a short
 * interval, usage/user aggregates slowly and whenever users or nodes change; both pause while the
 * browser tab is hidden.
 */
export function useDashboard(locale = 'en') {
  const analytics = ref<DashboardSnapshot | null>(null)
  const system = ref<DashboardSnapshot['system'] | null>(null)
  const processes = ref<DashboardSnapshot['processes'] | null>(null)
  const nodeStats = ref<DashboardNodeStats[]>([])
  const history = useMetricHistory()

  const rangeDays = ref(storedRange())
  const childId = ref<number | null>(storedNode())
  /** A period picked in the period window (null: the toolbar's last N days) */
  const customRange = ref<CustomRange | null>(storedCustom(locale))
  /** The shown period, and the one of the same length just before it (for the tiles' change against it) */
  const period = computed(() => customRange.value ?? { start: iso(addDays(today(), 1 - rangeDays.value)), end: iso(today()) })
  const previousPeriod = computed(() => {
    const length = daysBetween(period.value.start, period.value.end)
    const start = fromIso(period.value.start)
    return { start: iso(addDays(start, -length)), end: iso(addDays(start, -1)) }
  })
  /** Enough days for both periods (the API keeps a year: a longer reach has no previous period) */
  const fetchDays = computed(() => {
    const back = daysBetween(previousPeriod.value.start, iso(today()))
    return API_DAYS.find((days) => days >= back) ?? MAX_DAYS
  })
  const live = ref(true)
  const loading = ref(true)
  const refreshing = ref(false)
  const failed = ref(false)
  const updatedAt = ref<Date | null>(null)

  let inFlight = false
  let systemFeed: Subscription | null = null
  let analyticsFeed: Subscription | null = null

  const debug = debugNodes()
  const query = () => ({
    days: fetchDays.value,
    ...(childId.value === null ? {} : { child_id: childId.value }),
    ...(debug ? { debug_node: 1 as const } : {}),
  })

  function applySystem(snapshot: DashboardSnapshot) {
    if (snapshot.system && Object.keys(snapshot.system).length) {
      system.value = snapshot.system
      processes.value = snapshot.processes
      history.push(snapshot.system)
    }
    if (snapshot.node_stats?.length) {
      nodeStats.value = snapshot.node_stats
      history.pushNodes(snapshot.node_stats)
    }
    updatedAt.value = new Date()
    failed.value = false
  }

  function applyAnalytics(snapshot: DashboardSnapshot) {
    analytics.value = snapshot
    applySystem(snapshot)
    loading.value = false
  }

  /** Asked by the refresh button: at once, over HTTP. */
  async function loadAnalytics() {
    if (inFlight) return
    inFlight = true
    refreshing.value = true
    try {
      applyAnalytics(await dashboardApi.get({ ...query(), processes: 16 }))
    } catch {
      failed.value = true
    } finally {
      inFlight = false
      refreshing.value = false
      loading.value = false
    }
  }

  function onError() {
    failed.value = true
    loading.value = false
  }

  function stopFeeds() {
    systemFeed?.stop()
    analyticsFeed?.stop()
    systemFeed = analyticsFeed = null
  }

  function startFeeds() {
    stopFeeds()
    if (!live.value) return // paused: neither the metrics nor the totals are refreshed
    analyticsFeed = liveWatch<DashboardSnapshot>('dashboard/', {
      query: () => ({ ...query(), processes: 16 }),
      intervalMs: ANALYTICS_REFRESH_MS,
      tags: ['user', 'child'],
      onData: applyAnalytics,
      onError,
    })
    systemFeed = liveWatch<DashboardSnapshot>('dashboard/', {
      query: () => ({ ...query(), include: 'system', processes: 16 }),
      intervalMs: SYSTEM_REFRESH_MS,
      onData: applySystem,
      onError,
    })
  }

  watch(live, startFeeds)

  watch(rangeDays, (days) => localStorage.setItem(RANGE_STORAGE_KEY, String(days)))
  watch(customRange, (range) => {
    if (range) localStorage.setItem(CUSTOM_STORAGE_KEY, JSON.stringify(range.preset ? { preset: range.preset } : range))
    else localStorage.removeItem(CUSTOM_STORAGE_KEY)
  })
  watch(fetchDays, () => analyticsFeed?.restart())

  watch(childId, (id) => {
    localStorage.setItem(NODE_STORAGE_KEY, id === null ? 'all' : String(id))
    history.reset?.()
    analyticsFeed?.restart()
    systemFeed?.restart()
  })

  onMounted(startFeeds)
  onBeforeUnmount(stopFeeds)

  const nodes = computed<DashboardNode[]>(() => analytics.value?.nodes ?? [])

  return {
    // the days the API sent, cut to the period (it sends the previous period too)
    series: computed(() => {
      const { start, end } = period.value
      return (analytics.value?.series ?? []).filter((point) => point.date >= start && point.date <= end)
    }),
    /** The period of the same length before it; null when the API's year does not reach all of it */
    previousSeries: computed(() => {
      const { start, end } = previousPeriod.value
      const days = (analytics.value?.series ?? []).filter((point) => point.date >= start && point.date <= end)
      return days.length === daysBetween(start, end) ? days : null
    }),
    usage: computed(() => analytics.value?.usage ?? null),
    users: computed(() => analytics.value?.users ?? null),
    system: computed(() => system.value),
    processes: computed(() => processes.value),
    nodeStats: computed(() => nodeStats.value),
    nodes,
    childId,
    samples: history.samples,
    nodeSamples: history.nodeSamples,
    rangeDays,
    customRange,
    live,
    loading,
    refreshing,
    failed,
    updatedAt,
    refresh: loadAnalytics,
  }
}
