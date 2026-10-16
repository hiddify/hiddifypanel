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
  /** What was exchanged, one short line per row (at most 50; `items_more` are not listed). */
  items?: string[]
  items_more?: number
  /** The exchanged rows as JSON: zlib, then base64 (see `rawJson`). `raw_truncated`: only its beginning. */
  raw_z?: string
  raw_size?: number
  raw_truncated?: boolean
}

/** The JSON of an entry's exchanged rows (pretty when it is whole). */
export async function rawJson(entry: NodeSyncEntry): Promise<string> {
  if (!entry.raw_z) return ''
  const bytes = Uint8Array.from(atob(entry.raw_z), (c) => c.charCodeAt(0))
  // "deflate" is the zlib format (what Python's zlib.compress writes).
  const text = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'))).text()
  if (entry.raw_truncated) return text
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
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
  /** This node's users (at most 5000; `users_more` are not listed) and admins. Missing from older nodes. */
  users?: NodeUserItem[]
  users_more?: number
  admins?: NodeAdminItem[]
  /** Why the sync log could not be read; the counts are still there. */
  error: string
  took_ms: number
}

/** A user as the node has it: enabled is what the parent sent, active is whether it is served here. */
export interface NodeUserItem {
  name: string
  uuid: string
  enable: boolean
  is_active: boolean
  owner: string
}

export interface NodeAdminItem {
  name: string
  uuid: string
  mode: string
  parent: string
}

export const nodeSyncApi = {
  async status(): Promise<NodeSyncStatus> {
    const { data } = await getHttp().get<NodeSyncStatus>('node/sync-status/')
    return data
  },
}
