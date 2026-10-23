import { getHttp } from '@/core/api/client'
import { liveStream } from '@/core/live/live'
import type { NodeSyncStatus } from '@/features/node-home/api'

export type NodeStatus = 'online' | 'late' | 'offline' | 'never'

export interface NodeDetails {
  /** Last usage report the node sent (null before the first one). */
  last_usage_report: { time: string; users: number; bytes: number } | null
  today_usage: number
  today_online: number
  last_from_node: string | null
  last_to_node: string | null
}

export interface PanelNode {
  id: number
  name: string
  host: string
  /** Opens the node's admin panel as the signed-in admin. */
  admin_url: string
  last_seen: string | null
  status: NodeStatus
  domains: string[]
  details: NodeDetails
}

/** GET nodes/<id>/sync-status/: the node's own sync report, asked by this panel. */
export interface NodeSyncReportOut {
  /** null when the node could not be asked (offline, or too old for this call): see `error`. */
  report: NodeSyncStatus | null
  error: string
  /** This panel's side of the link. */
  websocket_connected: boolean
  last_seen: string | null
}

export interface NodePing {
  online: boolean
  version: string
  error: string
}

export interface NodeIcmpPing {
  ip: string
  ok: boolean
  /** round trip in milliseconds; null when it got no answer */
  ms: number | null
  method: 'icmp' | 'tcp' | ''
  error: string
}

/** 400 body of a failed registration: `code` is translated by the UI. */
export interface NodeRegisterError {
  code?: 'invalid_link' | 'self' | 'unreachable' | 'rejected' | string
  message?: string
  /** Where it went wrong: this panel, the node, or the way between them. */
  side?: 'parent' | 'node' | 'between' | ''
  /** The id the log lines of both panels have for this registration. */
  reg?: string
}

/** How long the page waits for a registration (the node waits for this panel, which stores the node's data). */
const REGISTER_WAIT_MS = 16 * 60_000

interface NodeJobState {
  state: 'running' | 'done' | 'failed'
  result?: { ok: boolean; node?: PanelNode | null; error?: NodeRegisterError }
  error?: { status: number; message: string }
}

/** Shaped like a failed axios request, so the dialog reads it the way it reads a 400 of the panel. */
class RegisterFailure extends Error {
  response: { data: NodeRegisterError }
  constructor(data: NodeRegisterError) {
    super(data.message ?? data.code ?? 'registration failed')
    this.response = { data }
  }
}

function registerFailure(data: NodeRegisterError): RegisterFailure {
  return new RegisterFailure(data)
}

export const nodesApi = {
  async list(): Promise<{ nodes: PanelNode[]; panel_version: string }> {
    const { data } = await getHttp().get<{ nodes: PanelNode[]; panel_version: string }>('nodes/')
    return data
  },
  /**
   * Registers a node. It is a job on the panel (the node and this panel talk to each other for a while, longer than a web
   * server or CDN waits for one request): this starts it, and its result is pushed over the live channel when it is there
   * (asked over HTTP every few seconds while the live channel is down).
   * A failure throws an error shaped like a failed request, with the {@link NodeRegisterError} as `response.data`.
   */
  async register(adminLink: string, name: string): Promise<PanelNode | null> {
    const http = getHttp()
    const { data: started } = await http.post<{ job: string }>('nodes/', { admin_link: adminLink, name }, { headers: { 'X-Async-Job': '1' }, timeout: 30_000 })
    const state = await new Promise<NodeJobState>((resolve, reject) => {
      let failures = 0
      let over = false
      const finish = (result: NodeJobState | null, error?: unknown) => {
        if (over) return
        over = true
        window.clearTimeout(deadline)
        feed.stop()
        if (result) resolve(result)
        else reject(error)
      }
      const deadline = window.setTimeout(() => finish(null, registerFailure({ code: 'timeout', message: '' })), REGISTER_WAIT_MS)
      const feed = liveStream<NodeJobState>('node.job', () => ({ job: started.job }), {
        onData: (s) => {
          failures = 0
          if (s.state !== 'running') finish(s)
        },
        onError: (e) => {
          if (e.status === 401 || e.status === 403 || e.status === 404) return finish(null, registerFailure({ code: 'rejected', message: e.message }))
          // A request that did not get through (the panel is busy or restarting): the registration goes on, ask again.
          if (e.fallback && ++failures >= 20) finish(null, registerFailure({ code: 'rejected', message: e.message }))
        },
        pauseWhenHidden: false,
        fallbackMs: 1500,
        fallback: async () => (await http.get<NodeJobState>(`nodes/jobs/${started.job}/`, { timeout: 30_000 })).data,
      })
    })
    if (state.state === 'failed') throw registerFailure({ code: 'rejected', message: state.error?.message ?? '' })
    if (state.result?.ok) return state.result.node ?? null
    throw registerFailure(state.result?.error ?? { code: 'rejected', message: '' })
  },
  async rename(id: number, name: string): Promise<{ node: PanelNode; synced_to_node: boolean }> {
    const { data } = await getHttp().patch<{ node: PanelNode; synced_to_node: boolean }>(`nodes/${id}/`, { name }, { timeout: 30_000 })
    return data
  },
  /** Resolves to whether the node confirmed it left (false: it was offline or too old). */
  async remove(id: number): Promise<boolean> {
    const { data } = await getHttp().delete<{ node_unlinked?: boolean }>(`nodes/${id}/`, { timeout: 30_000 })
    return data.node_unlinked !== false
  },
  async ping(id: number): Promise<NodePing> {
    const { data } = await getHttp().get<NodePing>(`nodes/${id}/ping/`, { timeout: 30_000 })
    return data
  },
  /** One ping of the node's server from this panel (ICMP, or a TCP connect when ICMP is not possible). */
  async icmp(id: number): Promise<NodeIcmpPing> {
    const { data } = await getHttp().get<NodeIcmpPing>(`nodes/${id}/icmp/`, { timeout: 10_000 })
    return data
  },
  async syncReport(id: number): Promise<NodeSyncReportOut> {
    const { data } = await getHttp().get<NodeSyncReportOut>(`nodes/${id}/sync-status/`, { timeout: 30_000 })
    return data
  },
  async sync(id: number): Promise<void> {
    await getHttp().post(`nodes/${id}/sync/`, null, { timeout: 60_000 })
  },
}
