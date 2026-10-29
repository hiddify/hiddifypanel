import { ref } from 'vue'
import { getHttp } from '@/core/api/client'

/** Nodes this panel cannot reach now, for the topbar's notifications (the Nodes page explains each one). */
export interface NodeProblem {
  id: number
  name: string
  /** hutils.node.contact_error: auth, timeout, refused, dns, tls, not_found, gateway, not_panel, server_error, no_url, unknown */
  code: string
  detail: string
}

export const nodeProblems = ref<NodeProblem[]>([])

export async function loadNodeProblems(): Promise<void> {
  try {
    nodeProblems.value = (await getHttp().get<{ problems: NodeProblem[] }>('nodes/problems/', { timeout: 60_000 })).data.problems ?? []
  } catch {
    /* offline, or not a parent panel: the list stays as it was */
  }
}
