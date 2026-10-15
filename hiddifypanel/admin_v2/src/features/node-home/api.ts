import { getHttp } from '@/core/api/client'

// Mirrors hutils/node/sync_status.py and sync_report.py (the response of GET node/sync-status/).

export const SYNC_KINDS = ['admins', 'users', 'domains', 'outbounds', 'usage'] as const
export type SyncKind = (typeof SYNC_KINDS)[number]
export type SyncSource = 'register' | 'http_sync' | 'ws_feed' | 'inventory' | 'usage_report'

/** One sync noted by the node. `at` is in Unix seconds. */
export interface NodeSyncEntry {
  kind: SyncKind
  source: SyncSource
  at: number
  count: number | null
  ok: boolean
  detail: Record<string, string | number | boolean>
}

export interface NodeSyncWebsocket {
  running: boolean
  connected: boolean
  host: string
  transport: string
  connected_since: number | null
  last_batch_at: number | null
  last_http_sync: number | null
  rows: number
  last_error: string
  saved_at: number | null
}

/** The feed's position: the last user / admin sent, as [modified time, id]. */
export interface FeedCursor {
  parent: string
  u: (string | number)[] | null
  a: (string | number)[] | null
}

interface AccountCounts {
  total: number
  enabled: number
  deleted: number
}

export interface NodeSyncStatus {
  is_node: boolean
  server_time: number
  parent: { url: string; unique_id: string; cursor: FeedCursor; last_users_sync: string }
  node: { name: string; unique_id: string }
  counts: {
    admins: AccountCounts & { by_mode: Record<string, number> }
    /** `active` is null on panels with more users than `active_count_limit`. */
    users: AccountCounts & { active: number | null }
    domains: { total: number; by_mode: Record<string, number> }
    outbounds: { total: number; enabled: number }
  }
  active_count_limit: number
  last: Partial<Record<SyncKind, NodeSyncEntry | null>>
  last_error: Partial<Record<SyncKind, NodeSyncEntry | null>>
  log: NodeSyncEntry[]
  websocket: NodeSyncWebsocket | null
  /** Why the sync log could not be read; the counts are still there. */
  error: string
  took_ms: number
}

export const nodeSyncApi = {
  async status(): Promise<NodeSyncStatus> {
    const { data } = await getHttp().get<NodeSyncStatus>('node/sync-status/')
    return data
  },
}
