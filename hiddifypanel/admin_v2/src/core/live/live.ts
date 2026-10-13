/**
 * The live channel: one connection per tab to `<admin API>/live/…` (hiddifypanel/live/channel.py) that brings the pages what
 * they would otherwise ask for again and again. What carries it (transports.ts) is a streamed response plus POSTs — riding
 * the page's HTTP/3 or HTTP/2 connection — or a WebSocket where that does not work; nothing below depends on which.
 *
 * - `liveWatch(path)` — the answer of `GET <admin API>/<path>` now and whenever it changes (the server asks the endpoint itself,
 *   on a timer and at once when one of `tags` — table names like `user`, or `cert`, `apply` — is published).
 * - `liveStream(topic)` — a log or job followed from a position (`apply.log`, `config-tester`, `node.job`), then its end.
 * - `liveRequest(method, path)` — a request of the page over the channel (starting a job, a delete…), answered as over HTTP.
 * - `liveCall(method)` — one answer (the WebSocket test).
 *
 * The channel comes and goes (the panel restarts after Apply; under `flask run` there is none): meanwhile every subscription
 * runs its `fallback` — the HTTP request it replaces — and when the channel is back it subscribes again from where it got to
 * (`params()` is asked each time). A subscription the server refuses (signed out, too many) stays on its fallback, so a 401
 * still reaches the sign-in redirect of the HTTP client.
 *
 * Data is delivered in order: a fallback request still running when the channel takes over (or when the subscription
 * restarts) is ignored, and so are messages for a subscription's earlier parameters (each restart gets a new id).
 * Subscriptions made while a component is set up (or in its `onMounted`, before any `await`) stop with it.
 */
import { getCurrentScope, onScopeDispose, ref } from 'vue'
import { getHttp, goToLogin } from '@/core/api/client'
import { makeTransport, type Transport, type TransportKind } from './transports'

export type LiveState = 'idle' | 'connecting' | 'open' | 'offline'
export interface LiveError {
  status: number
  message: string
  /** Not the end: the server (or the fallback) asks again. */
  retrying?: boolean
  /** From the HTTP fallback, not the channel. */
  fallback?: boolean
}

export interface SubscriptionOptions<T> {
  onData: (data: T) => void
  onError?: (error: LiveError) => void
  /** The stream is over (not called when it was refused: the subscription then goes on over its fallback). */
  onEnd?: () => void
  /** One HTTP read, used while the channel is not open and after the server refused the subscription. */
  fallback?: () => Promise<T>
  /** Between fallback reads; a function gets the number of failures in a row. */
  fallbackMs?: number | ((failures: number) => number)
  /** Stop while the tab is hidden (default true). */
  pauseWhenHidden?: boolean
}

export interface Subscription {
  stop(): void
  /** Subscribe again now (params changed, or to ask at once). */
  restart(): void
}

export const liveState = ref<LiveState>('idle')
/** What carries the channel now (null: nothing open). */
export const liveTransport = ref<TransportKind | null>(null)

/** The HTTP version the channel rides (`h3`, `h2`, `http/1.1`, `websocket`; null: nothing open). */
export const liveProtocol = ref<string | null>(null)
/** Why the last way tried was not taken (the WebSocket test shows it). */
export const liveIssue = ref('')

/**
 * Which way the channel goes: `auto` — a stream if it rides HTTP/3 or HTTP/2 (the page's own connection), else a WebSocket,
 * else a stream on whatever is left; or only one of `h3`, `h2` (a stream that must ride it) and `ws`. The browser picks the
 * HTTP version itself (Alt-Svc): `h3` / `h2` check what it picked, they can not make it.
 */
export type LiveChoice = 'auto' | 'h3' | 'h2' | 'ws'
let choice: LiveChoice = 'auto'

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

type Kind = 'watch' | 'stream'
interface ServerMessage {
  type: string
  id?: string
  data?: unknown
  status?: number
  message?: string
  retrying?: boolean
}

function errorOf(e: unknown): LiveError {
  const status = (e as { response?: { status?: number } })?.response?.status ?? 0
  return { status, message: (e as Error)?.message ?? String(e), retrying: true, fallback: true }
}

class Sub<T> {
  ended = false
  paused = false
  /** The server refused it: HTTP only from now on. */
  httpOnly = false
  /** Bumped whenever earlier answers must not be delivered any more (channel took over, restart, stop). */
  generation = 0
  failures = 0
  lastError: LiveError | null = null
  private timer: number | undefined
  private running = false

  constructor(
    public id: string,
    readonly kind: Kind,
    readonly topic: string,
    readonly params: () => Record<string, unknown>,
    readonly options: SubscriptionOptions<T>,
    private readonly channelOpen: () => boolean,
  ) {}

  message() {
    return { type: this.kind, id: this.id, topic: this.topic, params: this.params() }
  }

  deliver(data: T, generation: number) {
    if (this.ended || generation !== this.generation) return
    this.options.onData(data)
  }

  private wantsFallback(): boolean {
    return !this.ended && !this.paused && !!this.options.fallback && (this.httpOnly || !this.channelOpen())
  }

  private delay(): number {
    const wait = this.options.fallbackMs ?? 10_000
    return typeof wait === 'function' ? wait(this.failures) : wait
  }

  startFallback() {
    if (this.timer === undefined && this.wantsFallback()) this.timer = window.setTimeout(() => void this.tick(), 0)
  }

  private async tick() {
    this.timer = undefined
    if (!this.wantsFallback()) return
    if (!this.running) {
      this.running = true
      const generation = this.generation
      try {
        const data = await this.options.fallback!()
        this.failures = 0
        this.deliver(data, generation)
      } catch (e) {
        this.failures++
        if (!this.ended && generation === this.generation) this.options.onError?.(errorOf(e))
      } finally {
        this.running = false
      }
    }
    if (this.timer === undefined && this.wantsFallback()) this.timer = window.setTimeout(() => void this.tick(), this.delay())
  }

  /** No more fallback reads, and the answer of one still running is dropped. */
  stopFallback() {
    window.clearTimeout(this.timer)
    this.timer = undefined
    this.generation++
  }
}

const OPEN_TIMEOUT_MS = 8000
/** A request waits this long for the channel to open, then goes over HTTP. */
const OPEN_WAIT_FOR_REQUEST_MS = 3000
const MAX_RECONNECT_MS = 60_000
/** A channel that looks open but no longer answers (sleep, network change) is closed and opened again. */
const HEARTBEAT_MS = 25_000
const HEARTBEAT_TIMEOUT_MS = 10_000

class LiveClient {
  private transport: Transport | null = null
  private connecting = false
  /** Counts connection attempts: one overtaken by a reconnect closes what it opened. */
  private attempt = 0
  private subs = new Map<string, Sub<any>>()
  private calls = new Map<string, { resolve: (v: any) => void; reject: (e: unknown) => void; timer: number; sent: boolean }>()
  private seq = 0
  private failures = 0
  private reconnectTimer: number | undefined
  private heartbeat: number | undefined
  private visibilityBound = false

  private nextId(prefix: string) {
    this.seq += 1
    return `${prefix}${this.seq}`
  }

  private open(): boolean {
    return this.transport !== null
  }

  private bindVisibility() {
    if (this.visibilityBound) return
    this.visibilityBound = true
    document.addEventListener('visibilitychange', () => {
      for (const sub of this.subs.values()) {
        if (sub.options.pauseWhenHidden === false || sub.ended) continue
        if (document.hidden) {
          sub.paused = true
          sub.stopFallback()
          this.send({ type: 'stop', id: sub.id })
        } else if (sub.paused) {
          sub.paused = false
          this.activate(sub)
        }
      }
    })
  }

  private send(message: object): boolean {
    return this.transport?.send(message) ?? false
  }

  /** On the channel if it is open (and the server has not refused it), else on its fallback while the channel is (re)opened. */
  private activate(sub: Sub<any>) {
    if (sub.ended || sub.paused) return
    if (!sub.httpOnly && this.send(sub.message())) return
    sub.startFallback()
    if (!sub.httpOnly) this.connect()
  }

  connect() {
    if (this.transport || this.connecting || this.reconnectTimer !== undefined) return
    if (!this.subs.size && !this.calls.size) {
      liveState.value = 'idle'
      return
    }
    liveState.value = 'connecting'
    this.connecting = true
    void this.openFirst(ATTEMPTS[choice], ++this.attempt)
  }

  private async openFirst(attempts: Attempt[], attempt: number) {
    for (const { kind, accepts } of attempts) {
      let transport: Transport | null = null
      transport = makeTransport(kind, {
        onMessage: (text) => this.transport === transport && this.received(text),
        onClose: () => this.transport === transport && this.closed(),
      })
      try {
        await transport.open()
      } catch (e) {
        transport.close()
        liveIssue.value = `${kind}: ${(e as Error)?.message ?? e}`
        if (attempt !== this.attempt) return
        continue
      }
      if (!accepts(transport.protocol)) {
        liveIssue.value = `${kind} rode ${transport.protocol || 'an unknown protocol'}`
        transport.close()
        if (attempt !== this.attempt) return
        continue
      }
      if (attempt !== this.attempt) {
        transport.close() // overtaken by a reconnect
        return
      }
      this.connecting = false
      this.opened(transport)
      return
    }
    if (attempt !== this.attempt) return
    this.connecting = false
    this.closed()
  }

  private opened(transport: Transport) {
    this.transport = transport
    liveTransport.value = transport.kind
    liveProtocol.value = transport.protocol || null
    liveState.value = 'open'
    this.failures = 0
    for (const sub of this.subs.values()) {
      if (sub.ended || sub.paused || sub.httpOnly) continue
      sub.stopFallback() // an HTTP answer still on its way is older than what the channel sends now
      this.send(sub.message())
    }
    this.startHeartbeat()
  }

  private startHeartbeat() {
    window.clearInterval(this.heartbeat)
    this.heartbeat = window.setInterval(() => {
      if (!this.open() || !this.subs.size) return
      const transport = this.transport
      this.call('ping', {}, HEARTBEAT_TIMEOUT_MS).catch(() => {
        if (this.transport === transport) this.drop()
      })
    }, HEARTBEAT_MS)
  }

  /** Forget the current transport (its late messages included) and fall back until a new one is open. */
  private drop() {
    this.transport?.close()
    this.closed()
  }

  private closed() {
    this.transport = null
    liveTransport.value = null
    liveProtocol.value = null
    window.clearInterval(this.heartbeat)
    for (const [id, call] of this.calls) {
      window.clearTimeout(call.timer)
      call.reject(call.sent ? new Error('The live connection closed') : new LiveNotSent())
      this.calls.delete(id)
    }
    for (const sub of this.subs.values()) sub.startFallback()
    if (!this.subs.size) {
      liveState.value = 'idle'
      return
    }
    liveState.value = 'offline'
    this.failures += 1
    const wait = Math.min(MAX_RECONNECT_MS, 1000 * 2 ** Math.min(this.failures - 1, 6))
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = undefined
      this.connect()
    }, wait * (0.8 + Math.random() * 0.4))
  }

  private received(text: string) {
    let message: ServerMessage
    try {
      message = JSON.parse(text)
    } catch {
      return
    }
    const id = message.id ?? ''
    const call = this.calls.get(id)
    if (call) {
      window.clearTimeout(call.timer)
      this.calls.delete(id)
      if (message.type === 'result') call.resolve(message.data)
      else call.reject(Object.assign(new Error(message.message ?? 'failed'), { status: message.status }))
      return
    }
    const sub = this.subs.get(id)
    if (!sub || sub.ended) return
    if (message.type === 'data') {
      sub.lastError = null
      sub.deliver(message.data, sub.generation)
    } else if (message.type === 'error') {
      sub.lastError = { status: message.status ?? 0, message: message.message ?? '', retrying: message.retrying }
      sub.options.onError?.(sub.lastError)
    } else if (message.type === 'end') {
      if (sub.lastError && !sub.lastError.retrying && sub.options.fallback) {
        // Refused (signed out, too many subscriptions, the endpoint failed): over HTTP from now on.
        sub.httpOnly = true
        sub.startFallback()
        return
      }
      sub.ended = true
      this.subs.delete(id)
      sub.options.onEnd?.()
    }
  }

  subscribe<T>(kind: Kind, topic: string, params: () => Record<string, unknown>, options: SubscriptionOptions<T>): Subscription {
    this.bindVisibility()
    const sub = new Sub<T>(this.nextId(kind[0]!), kind, topic, params, options, () => this.open())
    sub.paused = options.pauseWhenHidden !== false && document.hidden
    this.subs.set(sub.id, sub)
    this.activate(sub)
    const handle: Subscription = {
      stop: () => {
        if (sub.ended) return
        sub.ended = true
        sub.stopFallback()
        this.subs.delete(sub.id)
        this.send({ type: 'stop', id: sub.id })
      },
      restart: () => {
        if (sub.ended) return
        sub.stopFallback()
        // A new id: what is still on its way for the earlier params is not delivered.
        this.send({ type: 'stop', id: sub.id })
        this.subs.delete(sub.id)
        sub.id = this.nextId(kind[0]!)
        this.subs.set(sub.id, sub)
        this.activate(sub)
      },
    }
    if (getCurrentScope()) onScopeDispose(handle.stop)
    return handle
  }

  /**
   * One answer. Waits up to `openWaitMs` for the channel to open; a call that could not be sent in that time (or before the
   * channel closed) fails with `LiveNotSent`, so the caller may send it another way without doing it twice.
   */
  call<T>(method: string, params: Record<string, unknown> = {}, timeoutMs = 15_000, openWaitMs = timeoutMs): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const id = this.nextId('c')
      const message = { type: 'call', id, method, params }
      let waitOpen: number | undefined
      const settle = () => {
        window.clearInterval(waitOpen)
        window.clearTimeout(timer)
        this.calls.delete(id)
      }
      const timer = window.setTimeout(() => {
        const entry = this.calls.get(id)
        settle()
        reject(entry?.sent ? new Error('No answer from the live connection') : new LiveNotSent())
      }, timeoutMs)
      const entry = {
        sent: false,
        timer,
        resolve: (v: T) => {
          settle()
          resolve(v)
        },
        reject: (e: unknown) => {
          settle()
          reject(e)
        },
      }
      this.calls.set(id, entry)
      const trySend = () => {
        if (!this.calls.has(id) || !this.send(message)) return false
        entry.sent = true
        window.clearInterval(waitOpen)
        return true
      }
      if (trySend()) return
      this.connect()
      const giveUpAt = Date.now() + openWaitMs
      waitOpen = window.setInterval(() => {
        if (trySend()) return
        if (Date.now() >= giveUpAt && this.calls.has(id)) entry.reject(new LiveNotSent())
      }, 100)
    })
  }

  /** Close and open again (the WebSocket test). */
  reconnect() {
    this.attempt++ // an attempt still running gives way
    this.connecting = false
    this.failures = 0
    this.drop()
    window.clearTimeout(this.reconnectTimer)
    this.reconnectTimer = undefined
    this.connect()
  }
}

const client = new LiveClient()

export interface WatchOptions<T> extends Omit<SubscriptionOptions<T>, 'fallback'> {
  query?: Record<string, unknown> | (() => Record<string, unknown>)
  /** How often the server asks the endpoint (ms); the fallback asks as often. */
  intervalMs: number
  /** Ask at once when one of these is published (table names: `user`, `domain`, `child`…; or `cert`, `apply`). */
  tags?: string[]
}

/** `GET <admin API>/<path>` now and whenever its answer changes. */
export function liveWatch<T>(path: string, options: WatchOptions<T>): Subscription {
  const query = () => (typeof options.query === 'function' ? options.query() : (options.query ?? {}))
  let last = ''
  const deliver = (data: T) => {
    const text = JSON.stringify(data)
    if (text === last) return
    last = text
    options.onData(data)
  }
  return client.subscribe<T>('watch', '', () => ({ path, query: query(), interval: options.intervalMs / 1000, tags: options.tags ?? [] }), {
    ...options,
    onData: deliver,
    fallbackMs: options.fallbackMs ?? options.intervalMs,
    fallback: async () => (await getHttp().get<T>(path, { params: query() })).data,
  })
}

/** A log or job followed from a position; `params()` is asked again on every (re)subscription. */
export function liveStream<T>(topic: string, params: () => Record<string, unknown>, options: SubscriptionOptions<T>): Subscription {
  return client.subscribe<T>('stream', topic, params, options)
}

/** The call never left this page: nothing was done on the server, it may be sent another way. */
export class LiveNotSent extends Error {
  constructor() {
    super('The live connection is not open')
  }
}

export type RequestMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface LiveRequestOptions {
  query?: Record<string, unknown>
  body?: unknown
  timeoutMs?: number
  /** A 401 is handed to the caller instead of leaving the page for the sign-in page (as axios' `skipAuthRedirect`). */
  skipAuthRedirect?: boolean
}

/** Shaped like a failed axios request (`response.status`, `response.data`): the pages read both the same way. */
export class LiveRequestError extends Error {
  response: { status: number; data: unknown }
  constructor(status: number, data: unknown) {
    const message = (data as { message?: unknown })?.message
    super(typeof message === 'string' && message ? message : `Request failed with status code ${status}`)
    this.response = { status, data }
  }
}

/**
 * `<method> <admin API>/<path>` over the live channel when it is open (the endpoint answers exactly as over HTTP), else over
 * HTTP. A request that went out on the channel is never sent again over HTTP: it may have been done (a job started twice).
 */
export async function liveRequest<T>(method: RequestMethod, path: string, options: LiveRequestOptions = {}): Promise<T> {
  const overHttp = async () => (await getHttp().request<T>({ method, url: path, params: options.query, data: options.body, timeout: options.timeoutMs, skipAuthRedirect: options.skipAuthRedirect })).data
  if (liveState.value === 'offline') return overHttp() // known to be down: no need to wait for it
  let answer: { status: number; data: T }
  try {
    answer = await client.call('request', { method, path, query: options.query ?? {}, body: options.body ?? null }, options.timeoutMs ?? 60_000, OPEN_WAIT_FOR_REQUEST_MS)
  } catch (e) {
    if (e instanceof LiveNotSent) return overHttp()
    throw e
  }
  if (answer.status >= 200 && answer.status < 300) return answer.data
  if (answer.status === 401 && !options.skipAuthRedirect) goToLogin()
  throw new LiveRequestError(answer.status, answer.data)
}

export function liveCall<T>(method: string, params: Record<string, unknown> = {}, timeoutMs?: number): Promise<T> {
  return client.call<T>(method, params, timeoutMs)
}

export function liveReconnect() {
  client.reconnect()
}

/** Which way the channel goes (the WebSocket test); reconnects. */
export function liveChoose(next: LiveChoice) {
  choice = next
  liveIssue.value = ''
  client.reconnect()
}

export type { TransportKind }
