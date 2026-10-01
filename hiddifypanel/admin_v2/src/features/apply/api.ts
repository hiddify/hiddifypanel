import { getHttp } from '@/core/api/client'

export type ApplyAction = 'apply' | 'install' | 'update' | 'restart' | 'status'

export interface LastRun {
  /** Unix seconds the log was last written. */
  mtime: number
  /** It ended with "Finished!". */
  finished: boolean
}

export interface LogFile {
  name: string
  size: number
  mtime: number
}

/** How to keep reading a log while the admin path or a domain changes under a run. */
export interface LogSources {
  /** API paths, newest admin path first. */
  api_bases: string[]
  /** Every domain of the panel (tried after the relative paths). */
  domains: string[]
  /** The login for requests to another domain (no cookies there). */
  api_key: string
  /** The admin link on each domain (new addresses after a domain or path change). */
  admin_links: string[]
}

export interface ApplyState extends LogSources {
  /** Actions running right now. */
  running: ApplyAction[]
  last: Partial<Record<ApplyAction, LastRun>>
  files: LogFile[]
  /** This panel is a node. */
  node: boolean
  now: number
}

export interface StartedRun extends ApplyState {
  action: ApplyAction
  log: string
  /** Server time the run was started: older log contents belong to a previous run. */
  started: number
}

export interface LogChunk {
  text: string
  offset: number
  size: number
  mtime: number
  /** False while the log is still the previous run's. */
  started: boolean
  progress: { percent: number; title: string; text: string } | null
  finished: boolean
  /** The file was truncated (a new run began): start the view over. */
  reset: boolean
}

export const applyApi = {
  async state(): Promise<ApplyState> {
    const { data } = await getHttp().get<ApplyState>('apply/')
    return data
  },
  async start(action: ApplyAction): Promise<StartedRun> {
    const { data } = await getHttp().post<StartedRun>(`apply/${action}/`, {}, { timeout: 60_000 })
    return data
  },
  /** One read of the current panel's log (viewer). */
  async tail(file: string): Promise<LogChunk> {
    const { data } = await getHttp().get<LogChunk>('apply/log/', { params: { file, tail: 1 }, timeout: 8000 })
    return data
  },
  downloadUrl(name: string): string {
    return `${getHttp().defaults.baseURL ?? ''}apply/logs/${encodeURIComponent(name)}/download/`
  },
}

/**
 * Reads a run's log through whatever still answers. After an admin-path or domain change only some URLs work,
 * and which ones changes while the run progresses (nginx is regenerated, then the panel restarts): the relative
 * paths first, then every domain, starting at the last URL that worked.
 */
export class LogReader {
  private urls: string[]
  private good = 0

  constructor(
    private file: string,
    private sources: Pick<LogSources, 'api_bases' | 'domains' | 'api_key'>,
  ) {
    const paths = sources.api_bases.length ? sources.api_bases : [`${getHttp().defaults.baseURL ?? '/'}`]
    this.urls = [...paths, ...sources.domains.flatMap((d) => paths.map((p) => `https://${d}${p}`))].map((base) => `${base}apply/log/`)
  }

  private async fetchOne(url: string, params: { offset: number; since: number }): Promise<LogChunk> {
    const query = new URLSearchParams({ file: this.file, offset: String(params.offset), random: String(Math.random()) })
    if (params.since) query.set('since', String(params.since))
    const ctl = new AbortController()
    const timer = window.setTimeout(() => ctl.abort(), 8000)
    try {
      const res = await fetch(`${url}?${query}`, { headers: { 'Hiddify-API-Key': this.sources.api_key }, signal: ctl.signal, cache: 'no-store' })
      const data = (await res.json()) as LogChunk
      // The login page or an error page is not the log.
      if (!res.ok || typeof data !== 'object' || data === null || typeof data.offset !== 'number') throw new Error('not the log')
      return data
    } finally {
      window.clearTimeout(timer)
    }
  }

  async read(params: { offset: number; since: number }): Promise<LogChunk> {
    let lastError: unknown
    for (let attempt = 0; attempt < this.urls.length; attempt++) {
      const index = (this.good + attempt) % this.urls.length
      try {
        const chunk = await this.fetchOne(this.urls[index]!, params)
        this.good = index
        return chunk
      } catch (err) {
        lastError = err
      }
    }
    throw lastError
  }
}

export const ACTIONS: ApplyAction[] = ['apply', 'install', 'update', 'restart', 'status']

export const ACTION_META: Record<ApplyAction, { icon: string; color: string; danger: boolean; minutes: string; confirm: boolean }> = {
  apply: { icon: 'pi pi-bolt', color: 'var(--p-primary-color)', danger: false, minutes: '1-2', confirm: false },
  install: { icon: 'pi pi-refresh', color: 'var(--p-orange-500, #f97316)', danger: true, minutes: '3-8', confirm: true },
  update: { icon: 'pi pi-cloud-download', color: 'var(--p-violet-500, #8b5cf6)', danger: true, minutes: '5-10', confirm: true },
  restart: { icon: 'pi pi-power-off', color: 'var(--p-red-500, #ef4444)', danger: true, minutes: '1', confirm: true },
  status: { icon: 'pi pi-heart-fill', color: 'var(--p-green-500, #22c55e)', danger: false, minutes: '<1', confirm: false },
}

/** The log each action writes (for the "last run" line). */
export const ACTION_LOG: Record<ApplyAction, string> = {
  apply: '0-install.log',
  install: '0-install.log',
  update: 'update.log',
  restart: 'restart.log',
  status: 'status.log',
}

/** Friendly names for the log files the scripts write. */
export const LOG_ICON: Record<string, string> = {
  '0-install.log': 'pi pi-box',
  'update.log': 'pi pi-cloud-download',
  'restart.log': 'pi pi-power-off',
  'status.log': 'pi pi-heart-fill',
  'backup.log': 'pi pi-save',
  'acme.log': 'pi pi-verified',
  'warp.log': 'pi pi-cloud',
  'panel.log': 'pi pi-server',
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
