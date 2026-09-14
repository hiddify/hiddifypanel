import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { dashboardApi, type DashboardSnapshot } from '@/core/api/generated'
import { useMetricHistory } from './useMetricHistory'

/** Ranges the dashboard API accepts for the usage/users history charts. */
export const RANGE_OPTIONS = [7, 30, 90, 180] as const
export const DEFAULT_RANGE = 30
/** Live server metrics refresh; the usage aggregation is much cheaper to poll slowly. */
export const SYSTEM_REFRESH_MS = 5000
export const ANALYTICS_REFRESH_MS = 60000

const STORAGE_KEY = 'admin_v2_dashboard_range'

function storedRange(): number {
  const stored = Number(localStorage.getItem(STORAGE_KEY))
  return (RANGE_OPTIONS as readonly number[]).includes(stored) ? stored : DEFAULT_RANGE
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
  const history = useMetricHistory()

  const rangeDays = ref(storedRange())
  const live = ref(true)
  const loading = ref(true)
  const refreshing = ref(false)
  const failed = ref(false)
  const updatedAt = ref<Date | null>(null)

  const timers: number[] = []
  let inFlight = false

  function applySnapshot(snapshot: DashboardSnapshot) {
    system.value = snapshot.system
    processes.value = snapshot.processes
    history.push(snapshot.system)
    updatedAt.value = new Date()
    failed.value = false
  }

  async function loadAnalytics() {
    if (inFlight) return
    inFlight = true
    refreshing.value = true
    try {
      const snapshot = await dashboardApi.get({ days: rangeDays.value })
      analytics.value = snapshot
      applySnapshot(snapshot)
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
      applySnapshot(await dashboardApi.get({ include: 'system' }))
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
    localStorage.setItem(STORAGE_KEY, String(days))
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

  return {
    series: computed(() => analytics.value?.series ?? []),
    usage: computed(() => analytics.value?.usage ?? null),
    users: computed(() => analytics.value?.users ?? null),
    system: computed(() => system.value),
    processes: computed(() => processes.value),
    samples: history.samples,
    rangeDays,
    live,
    loading,
    refreshing,
    failed,
    updatedAt,
    refresh: loadAnalytics,
  }
}
