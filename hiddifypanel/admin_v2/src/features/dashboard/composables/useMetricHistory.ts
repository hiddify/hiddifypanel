import { ref, type Ref } from 'vue'
import type { DashboardSnapshot } from '@/core/api/generated'

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

export interface MetricHistory {
  samples: Ref<MetricSample[]>
  push: (system: SystemSnapshot) => void
}

/**
 * Rolling window of live samples for the resource sparklines. The panel only
 * exposes cumulative traffic counters, so throughput is derived from the
 * difference between two consecutive snapshots.
 */
export function useMetricHistory(capacity = 60): MetricHistory {
  const samples = ref<MetricSample[]>([])
  let previous: { sent: number; recv: number; at: number } | null = null

  function push(system: SystemSnapshot) {
    const network = system.network
    const at = (network.sampled_at || Date.now() / 1000) * 1000
    let up = 0
    let down = 0

    if (previous) {
      const elapsed = (at - previous.at) / 1000
      if (elapsed > 0.5) {
        up = Math.max(0, (network.bytes_sent - previous.sent) / elapsed)
        down = Math.max(0, (network.bytes_recv - previous.recv) / elapsed)
      } else {
        const last = samples.value[samples.value.length - 1]
        up = last?.up ?? 0
        down = last?.down ?? 0
      }
    }
    previous = { sent: network.bytes_sent, recv: network.bytes_recv, at }

    samples.value = [
      ...samples.value.slice(-(capacity - 1)),
      { at, cpu: system.cpu.percent, memory: system.memory.percent, up, down },
    ]
  }

  return { samples, push }
}
