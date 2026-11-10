import { effectScope, ref, type Ref } from 'vue'
import { liveWatch } from '@/core/live/live'
import { isChildPanel } from '@/core/panelShell'
import type { InboxCounts } from '@/features/inbox/api'

const counts = ref<InboxCounts>({ unread: 0, pending: 0, waiting: 0 })
let started = false

/** How many conversations wait for this admin, for the menu badge: one subscription for the whole app. */
export function useInboxCounts(): Ref<InboxCounts> {
  if (!started && !isChildPanel.value) {
    started = true
    // Detached: it must outlive the component that asked first.
    effectScope(true).run(() =>
      liveWatch<InboxCounts>('inbox/counts/', {
        intervalMs: 60_000,
        tags: ['conversation', 'message'],
        onData: (next) => {
          counts.value = next
        },
      }),
    )
  }
  return counts
}
