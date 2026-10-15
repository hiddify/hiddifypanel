import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { apiErrorMessage } from '@/core/api/client'
import type { NodeSyncStatus } from '@/features/node-home/api'

const REFRESH_MS = 10_000

/** Gets a sync report: this node's own, or a node's through the parent. */
export type NodeSyncLoader = () => Promise<NodeSyncStatus>

/** A sync report, reloaded every 10 s while `auto` is on and the tab is visible. */
export function useNodeSyncStatus(loader: NodeSyncLoader): {
  data: Ref<NodeSyncStatus | null>
  loading: Ref<boolean>
  error: Ref<string>
  auto: Ref<boolean>
  load: () => Promise<void>
} {
  const data = ref<NodeSyncStatus | null>(null)
  const loading = ref(false)
  const error = ref('')
  const auto = ref(true)
  let timer: number | undefined

  async function load(): Promise<void> {
    loading.value = true
    try {
      data.value = await loader()
      error.value = ''
    } catch (err) {
      error.value = apiErrorMessage(err)
    } finally {
      loading.value = false
    }
  }

  function schedule(): void {
    window.clearInterval(timer)
    if (auto.value) timer = window.setInterval(() => document.visibilityState === 'visible' && void load(), REFRESH_MS)
  }

  watch(auto, schedule)
  onMounted(() => {
    void load()
    schedule()
  })
  onBeforeUnmount(() => window.clearInterval(timer))

  return { data, loading, error, auto, load }
}
