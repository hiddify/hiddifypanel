import { computed, onBeforeUnmount, ref } from 'vue'
import { CLOUDFLARE_RANGES, parseRanges, probeIp, randomIps } from '../api'

export interface ScanResult {
  ip: string
  ms: number
}

/** A dozen probes at a time: more makes the latencies of a slow phone connection meaningless. */
const PARALLEL = 12

/** The in-browser scan of random Cloudflare IPs: what works on this browser's internet, fastest first. */
export function useIpScan() {
  /** The ranges to pick IPs from (the full test uses them too), editable; Cloudflare's by default. */
  const rangesText = ref(CLOUDFLARE_RANGES.join('\n'))
  const parsedRanges = computed(() => parseRanges(rangesText.value))
  const ranges = computed(() => parsedRanges.value.ranges)
  const perRange = ref(4)
  const timeoutSec = ref(4)
  const running = ref(false)
  const stopping = ref(false)
  const done = ref(0)
  const total = ref(0)
  const passed = ref<ScanResult[]>([])

  const estimate = computed(() => perRange.value * ranges.value.length)
  const progress = computed(() => (total.value ? Math.round((done.value / total.value) * 100) : 0))

  async function start() {
    if (!ranges.value.length) return
    const ips = ranges.value.flatMap((range) => randomIps(range, perRange.value))
    for (let i = ips.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[ips[i], ips[j]] = [ips[j], ips[i]]
    }
    passed.value = []
    done.value = 0
    total.value = ips.length
    running.value = true
    stopping.value = false
    let next = 0
    const worker = async () => {
      while (next < ips.length && !stopping.value) {
        const ip = ips[next++]
        const result = await probeIp(ip, timeoutSec.value * 1000)
        done.value++
        if (result.ok) {
          passed.value.push({ ip, ms: result.ms })
          passed.value.sort((a, b) => a.ms - b.ms)
        }
      }
    }
    await Promise.all(Array.from({ length: PARALLEL }, worker))
    running.value = false
  }

  function stop() {
    stopping.value = true
  }

  /** Results from elsewhere (a full test run) shown as if scanned here. */
  function setResults(results: ScanResult[], tested: number) {
    passed.value = [...results].sort((a, b) => a.ms - b.ms)
    total.value = tested
    done.value = tested
  }

  onBeforeUnmount(stop)

  return { rangesText, ranges, perRange, timeoutSec, running, stopping, done, total, passed, estimate, progress, start, stop, setResults }
}

export type IpScan = ReturnType<typeof useIpScan>
