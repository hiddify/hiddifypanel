/** A domain a panel link can use; the link is `${base}${path}` (admin and user links). */
export interface ShareDomain {
  domain: string
  label: string
  /** `current`: the address this panel is open on. */
  kind: 'current' | 'direct' | 'cdn' | 'auto'
  base: string
}
