/**
 * What carries the live channel (live.ts): the same JSON messages over either
 *
 * - `stream` — one streamed response (`<admin API>/live/stream/`, an event stream) for what the server says, POSTs to
 *   `<admin API>/live/<session>/` for what the page says. Ordinary requests: they ride the page's own HTTP/3 or HTTP/2
 *   connection (no extra connection, no extra handshake) and pass every proxy and CDN.
 * - `websocket` — `<admin API>/live/`, a connection of its own (HTTP/1.1 when the page is on HTTP/3: browsers have no
 *   WebSocket over HTTP/3).
 *
 * The server's side is hiddifypanel/live/transport. A transport only opens, carries text and says when it closed; everything
 * else (subscriptions, calls, fallbacks) is the same whichever carries it.
 */
import { getApiBase } from '@/core/api/client'

export type TransportKind = 'stream' | 'websocket'

export interface TransportHandlers {
  onMessage: (text: string) => void
  /** It closed after it had opened (not called for a `close()` of this page). */
  onClose: () => void
}

export interface Transport {
  readonly kind: TransportKind
  /** The HTTP version it rides (`h3`, `h2`, `http/1.1`; '' when the browser does not say). */
  readonly protocol: string
  /** Resolves once messages can be sent; rejects when it can not be opened. */
  open(): Promise<void>
  /** Sends (or queues, in order) a message; false when it is not open. */
  send(message: object): boolean
  /** Closes it; nothing is delivered from it afterwards. */
  close(): void
}

const OPEN_TIMEOUT_MS = 8000

/** A channel of the admin API: `live` (the pages' updates), `ssh` (the SSH page). */
export type Channel = 'live' | 'ssh'

function channelUrl(channel: Channel, path: string): URL {
  return new URL(`${getApiBase()}${channel}/${path}`, window.location.href)
}

export class WebSocketTransport implements Transport {
  readonly kind = 'websocket'
  readonly protocol = 'websocket'
  private socket: WebSocket | null = null

  constructor(
    private readonly handlers: TransportHandlers,
    private readonly channel: Channel = 'live',
  ) {}

  open(): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = channelUrl(this.channel, '')
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      let socket: WebSocket
      try {
        socket = new WebSocket(url.toString())
      } catch (e) {
        reject(e)
        return
      }
      this.socket = socket
      let opened = false
      const timer = window.setTimeout(() => socket.readyState === WebSocket.CONNECTING && socket.close(), OPEN_TIMEOUT_MS)
      socket.onopen = () => {
        window.clearTimeout(timer)
        opened = true
        resolve()
      }
      socket.onmessage = (event) => this.handlers.onMessage(String(event.data))
      socket.onclose = () => {
        window.clearTimeout(timer)
        if (opened) this.handlers.onClose()
        else reject(new Error('The WebSocket could not be opened'))
      }
    })
  }

  send(message: object): boolean {
    if (this.socket?.readyState !== WebSocket.OPEN) return false
    this.socket.send(JSON.stringify(message))
    return true
  }

  close() {
    const socket = this.socket
    this.socket = null
    if (!socket) return
    socket.onopen = socket.onmessage = socket.onclose = null
    socket.close()
  }
}

/** Splits an event stream into events: `onEvent(event, data)` per event; comments (keepalives) are skipped. */
export class EventStreamParser {
  private buffer = ''

  constructor(private readonly onEvent: (event: string, data: string) => void) {}

  push(chunk: string) {
    this.buffer += chunk.replace(/\r\n?/g, '\n')
    let end: number
    while ((end = this.buffer.indexOf('\n\n')) >= 0) {
      const block = this.buffer.slice(0, end)
      this.buffer = this.buffer.slice(end + 2)
      let event = 'message'
      const data: string[] = []
      for (const line of block.split('\n')) {
        if (line.startsWith(':')) continue
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data.push(line.slice(line.startsWith('data: ') ? 6 : 5))
      }
      if (data.length) this.onEvent(event, data.join('\n'))
    }
  }
}

function entryProtocol(url: string): string {
  try {
    const entries = performance.getEntriesByName(url, 'resource') as PerformanceResourceTiming[]
    return entries.at(-1)?.nextHopProtocol ?? ''
  } catch {
    return ''
  }
}

function pageProtocol(): string {
  try {
    return (performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined)?.nextHopProtocol ?? ''
  } catch {
    return ''
  }
}

/**
 * The HTTP version a finished request to `url` used (Resource Timing). Its entry is added a moment after `fetch` resolves, so
 * it is waited for (up to ~1 s); without one, the page's own (same origin, same connection pool); '' when neither says.
 */
async function protocolOf(url: string): Promise<string> {
  for (let i = 0; i < 20; i++) {
    const found = entryProtocol(url)
    if (found) return found
    await new Promise((resolve) => window.setTimeout(resolve, 50))
  }
  return pageProtocol()
}

export class StreamTransport implements Transport {
  readonly kind = 'stream'
  protocol = ''
  private controller = new AbortController()
  private session = ''
  private opened = false
  private closedByPage = false
  private queue: string[] = []
  /** POSTs not answered yet, and the number of the next one (the server takes them in that order). */
  private inFlight = 0
  private seq = 0

  constructor(
    private readonly handlers: TransportHandlers,
    private readonly channel: Channel = 'live',
  ) {}

  open(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(() => this.controller.abort(), OPEN_TIMEOUT_MS)
      const parser = new EventStreamParser((event, data) => {
        if (event === 'session') {
          this.session = data
          this.opened = true
          window.clearTimeout(timer)
          // The stream itself is never finished (no timing entry); an empty POST on the same connection tells its HTTP version.
          void this.probe().then(resolve, resolve)
        } else if (this.opened) {
          this.handlers.onMessage(data)
        }
      })
      void (async () => {
        try {
          const response = await fetch(channelUrl(this.channel, 'stream/'), {
            credentials: 'include',
            cache: 'no-store',
            headers: { Accept: 'text/event-stream' },
            signal: this.controller.signal,
          })
          if (!response.ok || !response.body) throw new Error(`The stream answered ${response.status}`)
          const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
          for (;;) {
            const { value, done } = await reader.read()
            if (done) break
            parser.push(value)
          }
          throw new Error('The stream ended')
        } catch (e) {
          window.clearTimeout(timer)
          if (!this.opened) reject(e)
          else this.ended()
        }
      })()
    })
  }

  private ended() {
    if (this.closedByPage) return
    this.closedByPage = true // once
    this.controller.abort()
    this.handlers.onClose()
  }

  private async probe() {
    const url = channelUrl(this.channel, `${this.session}/`).toString()
    try {
      await fetch(url, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: '[]' })
    } catch {
      return
    }
    this.protocol = await protocolOf(url)
  }

  send(message: object): boolean {
    if (!this.opened || this.closedByPage) return false
    this.queue.push(JSON.stringify(message))
    this.flush()
    return true
  }

  /**
   * Each message leaves at once, without waiting for the last POST's answer (a key typed in a terminal must not wait a
   * round trip behind the one before): POSTs are numbered and the server takes them in order. Past `MAX_IN_FLIGHT`
   * unanswered ones, what is queued meanwhile goes together in the next.
   */
  private flush() {
    while (this.inFlight < MAX_IN_FLIGHT && this.queue.length && !this.closedByPage) {
      const batch = this.queue.splice(0)
      const seq = this.seq++
      this.inFlight++
      fetch(channelUrl(this.channel, `${this.session}/?seq=${seq}`), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batch),
      })
        .then((response) => {
          if (!response.ok) throw new Error(`The session answered ${response.status}`)
        })
        .catch(() => this.ended()) // the session is gone (or unreachable): the channel opens again, subscriptions start over
        .finally(() => {
          this.inFlight--
          this.flush()
        })
    }
  }

  close() {
    this.closedByPage = true
    this.controller.abort()
    this.queue = []
  }
}

/** Unanswered POSTs at a time on a stream transport. */
const MAX_IN_FLIGHT = 8

export function makeTransport(kind: TransportKind, handlers: TransportHandlers, channel: Channel = 'live'): Transport {
  return kind === 'stream' ? new StreamTransport(handlers, channel) : new WebSocketTransport(handlers, channel)
}

/**
 * Which way a channel goes: `auto` — a stream if it rides HTTP/3 or HTTP/2 (the page's own connection), else a WebSocket,
 * else a stream on whatever is left; or only one of `h3`, `h2` (a stream that must ride it) and `ws`. The browser picks the
 * HTTP version itself (Alt-Svc): `h3` / `h2` check what it picked, they can not make it.
 */
export type LiveChoice = 'auto' | 'h3' | 'h2' | 'ws'

interface Attempt {
  kind: TransportKind
  accepts: (protocol: string) => boolean
}

const ANY = () => true
const ATTEMPTS: Record<LiveChoice, Attempt[]> = {
  auto: [
    { kind: 'stream', accepts: (p) => p === 'h3' || p === 'h2' },
    { kind: 'websocket', accepts: ANY },
    { kind: 'stream', accepts: ANY },
  ],
  h3: [{ kind: 'stream', accepts: (p) => p === 'h3' }],
  h2: [{ kind: 'stream', accepts: (p) => p === 'h2' }],
  ws: [{ kind: 'websocket', accepts: ANY }],
}

export interface ConnectHandlers {
  onMessage: (text: string, transport: Transport) => void
  onClose: (transport: Transport) => void
  /** Why a way tried was not taken. */
  onIssue?: (issue: string) => void
  /** True when the caller no longer wants this attempt (it closes what it opened). */
  stale?: () => boolean
}

/** Open `channel` the best way `choice` allows (h3 → h2 → WebSocket for `auto`); null when none works (or `stale()`). */
export async function connectBest(channel: Channel, choice: LiveChoice, handlers: ConnectHandlers): Promise<Transport | null> {
  for (const { kind, accepts } of ATTEMPTS[choice]) {
    let transport: Transport | null = null
    transport = makeTransport(
      kind,
      {
        onMessage: (text) => transport && handlers.onMessage(text, transport),
        onClose: () => transport && handlers.onClose(transport),
      },
      channel,
    )
    try {
      await transport.open()
    } catch (e) {
      transport.close()
      handlers.onIssue?.(`${kind}: ${(e as Error)?.message ?? e}`)
      if (handlers.stale?.()) return null
      continue
    }
    if (handlers.stale?.()) {
      transport.close()
      return null
    }
    if (!accepts(transport.protocol)) {
      handlers.onIssue?.(`${kind} rode ${transport.protocol || 'an unknown protocol'}`)
      transport.close()
      continue
    }
    return transport
  }
  return null
}
