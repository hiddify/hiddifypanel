/** The names this server has until an admin renames it on the dashboard: shown as "This server" (translated). */
const LOCAL_DEFAULT_NAMES = new Set(['', 'Root', 'this-server'])

/** A node's name on the dashboard; this server (id 0) shows its own name once renamed, else `thisServer`. */
export function dashboardNodeName(id: number, name: string | null | undefined, thisServer: string): string {
  if (id !== 0) return name ?? ''
  const own = (name ?? '').trim()
  return LOCAL_DEFAULT_NAMES.has(own) ? thisServer : own
}

/** The name to put in the rename field: empty while this server still has its default name. */
export function editableNodeName(id: number, name: string | null | undefined): string {
  const own = (name ?? '').trim()
  return id === 0 && LOCAL_DEFAULT_NAMES.has(own) ? '' : own
}
