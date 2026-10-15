import type { NodeSyncEntry, NodeSyncStatus, SyncKind } from '@/features/node-home/api'

/** fresh: synced in the last 10 minutes; stale: longer ago; never: nothing noted (since redis was cleared); error: the last try failed. */
export type SyncState = 'fresh' | 'stale' | 'never' | 'error'

export const FRESH_SECONDS = 600

export interface SyncTile {
  kind: SyncKind
  icon: string
  /** null: this kind is not counted here (usage). */
  count: number | null
  chips: string[]
  last: NodeSyncEntry | null
  /** Only when it is newer than the last success. */
  failure: NodeSyncEntry | null
  state: SyncState
}

const ICONS: Record<SyncKind, string> = {
  admins: 'pi pi-user-edit',
  users: 'pi pi-users',
  domains: 'pi pi-globe',
  outbounds: 'pi pi-directions',
  usage: 'pi pi-chart-bar',
}

export interface ChipText {
  active: (n: string) => string
  enabled: (n: string) => string
  deleted: (n: string) => string
  number: (n: number) => string
}

function stateOf(last: NodeSyncEntry | null, failure: NodeSyncEntry | null, age: (at: number) => number): SyncState {
  if (failure) return 'error'
  if (!last) return 'never'
  return age(last.at) < FRESH_SECONDS ? 'fresh' : 'stale'
}

function countAndChips(kind: SyncKind, report: NodeSyncStatus, text: ChipText): { count: number | null; chips: string[] } {
  const c = report.counts
  const byMode = (m: Record<string, number>) => Object.entries(m).map(([mode, n]) => `${mode}: ${text.number(n)}`)
  const deleted = (n: number) => (n ? [text.deleted(text.number(n))] : [])
  switch (kind) {
    case 'admins':
      return { count: c.admins.total, chips: [...byMode(c.admins.by_mode), ...deleted(c.admins.deleted)] }
    case 'users':
      return {
        count: c.users.total,
        chips: [
          ...(c.users.active !== null ? [text.active(text.number(c.users.active))] : []),
          text.enabled(text.number(c.users.enabled)),
          ...deleted(c.users.deleted),
        ],
      }
    case 'domains':
      return { count: c.domains.total, chips: byMode(c.domains.by_mode) }
    case 'outbounds':
      return { count: c.outbounds.total, chips: [text.enabled(text.number(c.outbounds.enabled))] }
    case 'usage':
      // Not held here: the tile shows how many users the last report carried.
      return { count: report.last.usage?.count ?? null, chips: [] }
  }
}

/** One tile per kind: what the node holds and when it last came. */
export function buildTiles(report: NodeSyncStatus, kinds: readonly SyncKind[], age: (at: number) => number, text: ChipText): SyncTile[] {
  return kinds.map((kind) => {
    const last = report.last[kind] ?? null
    const lastError = report.last_error[kind] ?? null
    const failure = lastError && (!last || lastError.at > last.at) ? lastError : null
    return { kind, icon: ICONS[kind], ...countAndChips(kind, report, text), last, failure, state: stateOf(last, failure, age) }
  })
}
