import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { dashboardApi, type DashboardNode, type DashboardNodeStats, type DashboardSnapshot } from '@/core/api/generated'
import { useMetricHistory } from './useMetricHistory'

/** Ranges the dashboard API accepts for the usage/users history charts. */
export const RANGE_OPTIONS = [7, 30, 90, 180] as const
export const DEFAULT_RANGE = 30
/** Live server metrics refresh; the usage aggregation is much cheaper to poll slowly. */
export const SYSTEM_REFRESH_MS = 5000
export const ANALYTICS_REFRESH_MS = 60000

const RANGE_STORAGE_KEY = 'admin_v2_dashboard_range'
const NODE_STORAGE_KEY = 'admin_v2_dashboard_node'

function storedRange(): number {
  const stored = Number(localStorage.getItem(RANGE_STORAGE_KEY))
  return (RANGE_OPTIONS as readonly number[]).includes(stored) ? stored : DEFAULT_RANGE
}

function storedNode(): number | null {
  const raw = localStorage.getItem(NODE_STORAGE_KEY)
  if (raw === null || raw === '' || raw === 'all') return null
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * Single source of truth for the dashboard. Server metrics poll on a short
 * interval while usage/user aggregates refresh slowly, both pausing while the
 * browser tab is hidden.
 */
export function useDashboard() {
  const analytics = ref<DashboardSnapshot | null>(null)
  const system = ref<DashboardSnapshot['system'] | null>(null)
  const processes = ref<DashboardSnapshot['processes'] | null>(null)
  const nodeStats = ref<DashboardNodeStats[]>([])
  const history = useMetricHistory()

  const rangeDays = ref(storedRange())
  const childId = ref<number | null>(storedNode())
  const live = ref(true)
  const loading = ref(true)
  const refreshing = ref(false)
  const failed = ref(false)
  const updatedAt = ref<Date | null>(null)

  const timers: number[] = []
  let inFlight = false

  const query = () => ({
    days: rangeDays.value,
    ...(childId.value === null ? {} : { child_id: childId.value }),
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

  async function loadAnalytics() {
    if (inFlight) return
    inFlight = true
    refreshing.value = true
    try {
      const snapshot = await dashboardApi.get({ ...query(), processes: 16 })
      analytics.value = snapshot
      applySystem(snapshot)
    } catch {
      failed.value = true
    } finally {
      inFlight = false
      refreshing.value = false
      loading.value = false
    }
  }

  async function loadSystem() {
    if (inFlight) return
    try {
      applySystem(await dashboardApi.get({ ...query(), include: 'system', processes: 16 }))
    } catch {
      failed.value = true
    }
  }

  function stopTimers() {
    while (timers.length) window.clearInterval(timers.pop())
  }

  function startTimers() {
    stopTimers()
    if (!live.value || document.hidden) return
    timers.push(window.setInterval(loadSystem, SYSTEM_REFRESH_MS))
    timers.push(window.setInterval(loadAnalytics, ANALYTICS_REFRESH_MS))
  }

  function onVisibilityChange() {
    if (document.hidden) {
      stopTimers()
      return
    }
    if (live.value) {
      void loadAnalytics()
      startTimers()
    }
  }

  watch(live, (enabled) => {
    if (enabled) {
      void loadSystem()
      startTimers()
    } else {
      stopTimers()
    }
  })

  watch(rangeDays, (days) => {
    localStorage.setItem(RANGE_STORAGE_KEY, String(days))
    void loadAnalytics()
  })

  watch(childId, (id) => {
    localStorage.setItem(NODE_STORAGE_KEY, id === null ? 'all' : String(id))
    history.reset?.()
    void loadAnalytics()
  })

  onMounted(() => {
    void loadAnalytics()
    startTimers()
    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onBeforeUnmount(() => {
    stopTimers()
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  const nodes = computed<DashboardNode[]>(() => analytics.value?.nodes ?? [])

  return {
    series: computed(() => analytics.value?.series ?? []),
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
    live,
    loading,
    refreshing,
    failed,
    updatedAt,
    refresh: loadAnalytics,
  }
}
