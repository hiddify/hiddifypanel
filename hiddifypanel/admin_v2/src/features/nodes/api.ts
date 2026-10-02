import { getHttp } from '@/core/api/client'

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

export interface NodePing {
  online: boolean
  version: string
  error: string
}

/** 400 body of a failed registration: `code` is translated by the UI. */
export interface NodeRegisterError {
  code?: 'invalid_link' | 'self' | 'unreachable' | 'rejected' | string
  message?: string
}

export const nodesApi = {
  async list(): Promise<{ nodes: PanelNode[]; panel_version: string }> {
    const { data } = await getHttp().get<{ nodes: PanelNode[]; panel_version: string }>('nodes/')
    return data
  },
  async register(adminLink: string, name: string): Promise<PanelNode | null> {
    // The node calls this panel back while we wait, so this can take a while.
    const { data } = await getHttp().post<{ node: PanelNode | null }>('nodes/', { admin_link: adminLink, name }, { timeout: 90_000 })
    return data.node
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
  async sync(id: number): Promise<void> {
    await getHttp().post(`nodes/${id}/sync/`, null, { timeout: 60_000 })
  },
}
