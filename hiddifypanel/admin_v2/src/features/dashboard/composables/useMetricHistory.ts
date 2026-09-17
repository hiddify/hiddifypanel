import { ref, type Ref } from 'vue'
import type { DashboardNodeStats, DashboardSnapshot } from '@/core/api/generated'

type SystemSnapshot = DashboardSnapshot['system']

/** One polled live sample of the fast-moving system metrics. */
export interface MetricSample {
  at: number
  cpu: number
  memory: number
  /** bytes per second, derived from two snapshots */
  up: number
  down: number
}

export interface NodeSample {
  at: number
  cpu: number
  memory: number
  disk: number
  up: number
  down: number
}

export interface MetricHistory {
  samples: Ref<MetricSample[]>
  nodeSamples: Ref<Record<number, NodeSample[]>>
  push: (system: SystemSnapshot) => void
  pushNodes: (nodes: DashboardNodeStats[]) => void
  reset: () => void
}

interface NetCursor {
  sent: number
  recv: number
  at: number
}

function throughput(current: NetCursor, previous: NetCursor | undefined, last: NodeSample | MetricSample | undefined): {
  up: number
  down: number
} {
  if (!previous) return { up: 0, down: 0 }
  const elapsed = (current.at - previous.at) / 1000
  if (elapsed > 0.5) {
    return {
      up: Math.max(0, (current.sent - previous.sent) / elapsed),
      down: Math.max(0, (current.recv - previous.recv) / elapsed),
    }
  }
  return { up: last?.up ?? 0, down: last?.down ?? 0 }
}

/**
 * Rolling window of live samples for the resource sparklines. The panel only
 * exposes cumulative traffic counters, so throughput is derived from the
 * difference between two consecutive snapshots.
 */
export function useMetricHistory(capacity = 60): MetricHistory {
  const samples = ref<MetricSample[]>([])
  const nodeSamples = ref<Record<number, NodeSample[]>>({})
  let previous: NetCursor | null = null
  const previousByNode = new Map<number, NetCursor>()

  function push(system: SystemSnapshot) {
    const network = system.network
    const at = (network.sampled_at || Date.now() / 1000) * 1000
    const current = { sent: network.bytes_sent, recv: network.bytes_recv, at }
    const rates = throughput(current, previous ?? undefined, samples.value[samples.value.length - 1])
    previous = current
    samples.value = [...samples.value.slice(-(capacity - 1)), { at, cpu: system.cpu.percent, memory: system.memory.percent, ...rates }]
  }

  function pushNodes(nodes: DashboardNodeStats[]) {
    const next: Record<number, NodeSample[]> = { ...nodeSamples.value }
    for (const node of nodes) {
      if (!node.ok || !node.cpu || !node.memory || !node.disk || !node.network) continue
      const at = (node.network.sampled_at || Date.now() / 1000) * 1000
      const current = { sent: node.network.bytes_sent, recv: node.network.bytes_recv, at }
      const series = next[node.id] ?? []
      const rates = throughput(current, previousByNode.get(node.id), series[series.length - 1])
      previousByNode.set(node.id, current)
      next[node.id] = [
        ...series.slice(-(capacity - 1)),
        { at, cpu: node.cpu.percent, memory: node.memory.percent, disk: node.disk.percent, ...rates },
      ]
    }
    nodeSamples.value = next
  }

  function reset() {
    samples.value = []
    nodeSamples.value = {}
    previous = null
    previousByNode.clear()
  }

  return { samples, nodeSamples, push, pushNodes, reset }
}
