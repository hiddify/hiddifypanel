/** Additional configs ([kind, target, value]) for users, and for admins (all their users get them). */

export type ConfigKind = 'offline' | 'subscription'
export type ConfigTarget = 'sublink' | 'xray' | 'hiddify-core' | 'clash' | 'auto'
export const CONFIG_TARGETS: ConfigTarget[] = ['auto', 'sublink', 'xray', 'hiddify-core', 'clash']
/** offline: the config itself · subscription: a URL fetched for the user. */
export type AdditionalConfig = [ConfigKind, ConfigTarget, string]

/** The i18n key of what is wrong with a row, or null. */
export function configRowProblem(row: AdditionalConfig): string | null {
  const value = row[2].trim()
  if (!value) return 'users.configs.empty'
  if (row[0] === 'subscription' && !/^https?:\/\//i.test(value)) return 'users.configs.badUrl'
  return null
}

export function cleanConfigRows(rows: AdditionalConfig[]): AdditionalConfig[] {
  return rows.map(([kind, target, value]) => [kind, target, value.trim()] as AdditionalConfig)
}
