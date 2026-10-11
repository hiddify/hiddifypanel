/** What the config tester's panel API sends (the same shapes as proxy_v3/config_tester_types.py). */

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json }
export type JsonObject = { [key: string]: Json }

export type Kind = 'xray' | 'core'
export type Source = 'xray' | 'core' | 'parsed'

export type Fetched = { user_agent: string; status: number; content_type: string; bytes: number; pasted?: undefined } | { pasted: true; bytes: number; user_agent?: undefined; status?: undefined; content_type?: undefined }

export interface ItemInfo {
  index: number
  name: string
  kind: Kind
}

export interface StartEvent {
  event: 'start'
  source: Source
  total: number
  fetched: Fetched
  raw: string
  parsed: JsonObject | null
  items: ItemInfo[]
}

export interface PingOut {
  ok: boolean
  delay_ms?: number
  error?: string
}

export interface ResultEvent {
  event: 'result'
  index: number
  name: string
  kind: Kind
  ok: boolean
  tag: string
  original: Json
  run_config?: JsonObject
  error?: string
  pings?: PingOut[]
  tries?: number
  ok_count?: number
  delay_ms?: number
  log?: string
}

export interface ErrorEvent {
  event: 'error'
  error: string
}

/** `ping`, `queued` and `done` carry nothing else. */
export type TesterEvent = StartEvent | ResultEvent | ErrorEvent | { event: 'ping' | 'queued' | 'done' }

export interface JobPage {
  events: TesterEvent[]
  next: number
  done: boolean
  lost: boolean
}
