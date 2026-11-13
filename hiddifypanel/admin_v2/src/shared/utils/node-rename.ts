/**
 * Whether a node can be renamed so the node itself takes the name too (the dashboard and the Nodes page use the same
 * rule). A rename is saved on this panel and then sent to the node's own API (`/api/v2/child/node-name/`), which only
 * works when:
 * - this panel can reach the node (the Nodes page's "Connection", the dashboard's live stats), and
 * - the node's panel is 14.0 or newer (older ones don't have that API).
 * Until it is known whether this panel can reach the node (the Nodes page checks every node as it opens), the pencil
 * says the node is being checked; a reachable node whose version is not known is allowed.
 */
export type RenameBlock = 'checking' | 'unreachable' | 'tooOld'

/** The first panel version whose nodes take a new name from their parent */
export const RENAME_MIN_MAJOR = 14

export function nodeRenameBlock(reachable: boolean | null | undefined, version?: string | null): RenameBlock | null {
  if (reachable == null) return 'checking'
  if (reachable === false) return 'unreachable'
  const major = Number.parseInt((version ?? '').replace(/^v/i, ''), 10)
  if (reachable && Number.isFinite(major) && major < RENAME_MIN_MAJOR) return 'tooOld'
  return null
}
