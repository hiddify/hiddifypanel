/** What a saved change needs before it takes effect (server `restart_mode`). */
export type RestartMode = 'nothing' | 'apply_config' | 'reinstall' | 'update'

const RANK: Record<RestartMode, number> = { nothing: 0, apply_config: 1, update: 2, reinstall: 3 }

/** The stronger of two pending steps, so a later small save does not hide an earlier reinstall. */
export function strongerRestartMode(a: RestartMode, b: RestartMode): RestartMode {
  return RANK[b] > RANK[a] ? b : a
}
