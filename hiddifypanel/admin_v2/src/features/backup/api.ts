import { getHttp } from '@/core/api/client'

export interface PanelCounts {
  users: number
  admins: number
  domains: number
  custom_proxies: number
  nodes: number
}

export interface BackupSummary extends PanelCounts {
  settings: number
  /** A few of its domains, to recognise the panel it came from. */
  domain_names: string[]
  /** Restoring its settings changes the admin link (it came from another panel). */
  admin_path_changes: boolean
}

export interface BackupFile {
  name: string
  size: number
  /** ISO time it was made. */
  created: string
}

export interface BackupState {
  current: PanelCounts
  /** The server's automatic backups, newest first. */
  files: BackupFile[]
  telegram: { bot: boolean; connected: boolean }
  directory: string
  created?: string
}

export interface RestoreOptions {
  settings: boolean
  users: boolean
  domains: boolean
  /** The owner of this panel takes the backup owner's GUID (admin links of the old panel keep working). */
  replace_owner_admin: boolean
}

/** Where a restore comes from: a file picked in the browser, or one of the server's backups. */
export type RestoreSource = { kind: 'upload'; name: string; size: number; data: unknown } | { kind: 'server'; name: string; size: number }

function save(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function filenameFrom(disposition: string | undefined, fallback: string): string {
  const m = /filename="?([^";]+)"?/.exec(disposition ?? '')
  return m?.[1] ?? fallback
}

/** gzip in the browser when it can (the admin path accepts uploads up to 10 MB). */
async function gzipped(text: string): Promise<Blob | null> {
  if (typeof CompressionStream === 'undefined') return null
  const stream = new Blob([text]).stream().pipeThrough(new CompressionStream('gzip'))
  return new Response(stream).blob()
}

async function postRestore<T>(body: Record<string, unknown>): Promise<T> {
  const text = JSON.stringify(body)
  const zipped = text.length > 256 * 1024 ? await gzipped(text) : null
  const { data } = zipped
    ? await getHttp().post<T>('backup/restore/', zipped, { headers: { 'Content-Type': 'application/gzip' }, timeout: 180_000 })
    : await getHttp().post<T>('backup/restore/', body, { timeout: 180_000 })
  return data
}

function sourceBody(source: RestoreSource): Record<string, unknown> {
  return source.kind === 'server' ? { file: source.name } : { data: source.data }
}

export const backupApi = {
  async state(): Promise<BackupState> {
    const { data } = await getHttp().get<BackupState>('backup/')
    return data
  },
  async download(): Promise<void> {
    const res = await getHttp().get<Blob>('backup/download/', { responseType: 'blob', timeout: 180_000 })
    save(res.data, filenameFrom(res.headers['content-disposition'] as string | undefined, 'hiddify-backup.json'))
  },
  async createOnServer(): Promise<BackupState> {
    const { data } = await getHttp().post<BackupState>('backup/files/', {}, { timeout: 180_000 })
    return data
  },
  async downloadFile(name: string): Promise<void> {
    const res = await getHttp().get<Blob>(`backup/files/${encodeURIComponent(name)}/`, { responseType: 'blob', timeout: 180_000 })
    save(res.data, `hiddify-${name}`)
  },
  async removeFile(name: string): Promise<BackupState> {
    const { data } = await getHttp().delete<BackupState>(`backup/files/${encodeURIComponent(name)}/`)
    return data
  },
  /** What a backup holds (checked by the server). */
  async summary(source: RestoreSource): Promise<BackupSummary> {
    if (source.kind === 'server') {
      const { data } = await getHttp().get<BackupSummary>(`backup/files/${encodeURIComponent(source.name)}/`, { params: { summary: 1 } })
      return data
    }
    return (await postRestore<{ summary: BackupSummary }>({ ...sourceBody(source), dry_run: true })).summary
  },
  /** Prepares the restore; `run_url` restores and reinstalls (opened in the action dialog, with its log). */
  async prepare(source: RestoreSource, options: RestoreOptions): Promise<{ run_url: string; summary: BackupSummary }> {
    return postRestore({ ...sourceBody(source), ...options })
  },
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
