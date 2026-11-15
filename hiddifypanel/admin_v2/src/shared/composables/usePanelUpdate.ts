import { ref } from 'vue'
import { getHttp } from '@/core/api/client'

/** The panel's version against the latest release (the server asks GitHub at most once a day, or on "Check now") */
export interface PanelUpdateStatus {
  current: string
  latest: string | null
  outdated: boolean
  channel: 'release' | 'beta'
  /** unix seconds of the server's last look */
  checked_at: number | null
  error: string | null
}

/** Shared by the bell (its update notice) and the Update card on the Actions page */
export const panelUpdate = ref<PanelUpdateStatus | null>(null)

let pending: Promise<PanelUpdateStatus | null> | null = null

/** ``force``: the server asks GitHub now instead of giving its answer of the day */
export function loadPanelUpdate(force = false): Promise<PanelUpdateStatus | null> {
  if (pending && !force) return pending
  const run = getHttp()
    .get<PanelUpdateStatus>('panel-version/', { params: force ? { force: 1 } : {}, timeout: 20_000 })
    .then(({ data }) => (panelUpdate.value = data))
    .catch(() => null)
    .finally(() => {
      if (pending === run) pending = null
    })
  pending = run
  return run
}
