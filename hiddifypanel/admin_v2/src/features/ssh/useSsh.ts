/**
 * One SSH session through the panel (hiddifypanel/live/ssh.py), over the same transports as the live channel: a stream on
 * HTTP/3, then HTTP/2, then a WebSocket (core/live/transports.ts `connectBest`).
 *
 * Nothing secret is kept: the password or key goes with `connect` and is forgotten. What is remembered in this browser: the
 * last host, port and user, and the host key fingerprints the admin trusted (trust on first use; a changed key is shown).
 */
import { ref, shallowRef } from 'vue'
import { connectBest, type Transport } from '@/core/live/transports'

export interface ExecResult {
  /** The command's exit status; null when it did not run to the end (see `message`). */
  status: number | null
  message: string
}

export type SshPhase = 'idle' | 'connecting' | 'hostkey' | 'ready' | 'closed'

export interface SshTarget {
  host: string
  port: number
  username: string
  password?: string
  privateKey?: string
  passphrase?: string
}

export interface HostKey {
  fingerprint: string
  algorithm: string
  /** A fingerprint was trusted for this host before, and this one differs. */
  changed: boolean
}

export interface FileEntry {
  name: string
  dir: boolean
  link: boolean
  size: number | null
  mtime: number | null
  mode: string
  /** What the signed-in user may do: `rwx`, `-` for each it may not (null: unknown). */
  access: string | null
}

export interface Listing {
  path: string
  entries: FileEntry[]
  truncated: boolean
}

/** A file operation that failed: `code` says what kind (permission, notFound, exists, noSpace, connection, ...), `message` the server's words. */
export class SshError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message)
  }
}

export interface FileContent {
  path: string
  size: number
  text?: string
  base64?: string
  too_large?: boolean
  /** This user may change it (shown with `text`). */
  writable?: boolean
}

const TRUSTED_KEY = 'hiddify.ssh.trusted'
const LAST_KEY = 'hiddify.ssh.last'

function trusted(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(TRUSTED_KEY) || '{}')
  } catch {
    return {}
  }
}

function hostId(t: Pick<SshTarget, 'host' | 'port'>): string {
  return `${t.host.toLowerCase()}:${t.port}`
}

export function lastTarget(): Partial<SshTarget> {
  try {
    return JSON.parse(localStorage.getItem(LAST_KEY) || '{}')
  } catch {
    return {}
  }
}

export function useSsh(onOutput: (data: string) => void) {
  const phase = ref<SshPhase>('idle')
  const error = ref('')
  const hostKey = ref<HostKey | null>(null)
  const protocol = ref('')
  const home = ref('')
  const filesAvailable = ref(false)
  const exitStatus = ref<number | null>(null)
  const transport = shallowRef<Transport | null>(null)

  let pending: SshTarget | null = null
  let size = { cols: 80, rows: 24 }
  let seq = 0
  const requests = new Map<number, { resolve: (v: any) => void; reject: (e: Error) => void }>()
  /** Commands run apart from the terminal (`exec`), by id. */
  const jobs = new Map<string, { onData: (d: string) => void; resolve: (r: ExecResult) => void }>()

  function send(message: object): boolean {
    return transport.value?.send(message) ?? false
  }

  function handle(text: string) {
    let m: any
    try {
      m = JSON.parse(text)
    } catch {
      return
    }
    switch (m.type) {
      case 'hostkey':
        hostKey.value = {
          fingerprint: m.fingerprint,
          algorithm: m.algorithm,
          changed: !!trusted()[hostId(pending!)],
        }
        phase.value = 'hostkey'
        break
      case 'ready':
        home.value = m.home || ''
        filesAvailable.value = !!m.files
        phase.value = 'ready'
        error.value = ''
        if (pending) {
          const { host, port, username } = pending
          localStorage.setItem(LAST_KEY, JSON.stringify({ host, port, username }))
        }
        break
      case 'data':
        onOutput(m.d)
        break
      case 'exit':
        exitStatus.value = m.status ?? null
        phase.value = 'closed'
        break
      case 'error':
        error.value = m.message
        if (phase.value === 'connecting') phase.value = 'idle'
        break
      case 'exec_data':
        jobs.get(m.id)?.onData(m.d)
        break
      case 'exec_done': {
        const job = jobs.get(m.id)
        jobs.delete(m.id)
        job?.resolve({ status: m.status ?? null, message: m.message ?? '' })
        break
      }
      case 'result':
      case 'failed': {
        const r = requests.get(m.id)
        if (!r) break
        requests.delete(m.id)
        if (m.type === 'result') r.resolve(m.data)
        else r.reject(new SshError(m.message, m.code || 'other'))
        break
      }
    }
  }

  function dropTransport() {
    transport.value?.close()
    transport.value = null
    for (const r of requests.values()) r.reject(new SshError('disconnected', 'connection'))
    requests.clear()
    for (const job of jobs.values()) job.resolve({ status: null, message: 'disconnected' })
    jobs.clear()
  }

  async function open(): Promise<boolean> {
    if (transport.value) return true
    const t = await connectBest('ssh', 'auto', {
      onMessage: (text, from) => from === transport.value && handle(text),
      onClose: (from) => {
        if (from !== transport.value) return
        transport.value = null
        if (phase.value === 'ready' || phase.value === 'connecting') {
          phase.value = 'closed'
          error.value = error.value || 'The connection to the panel was lost'
        }
      },
    })
    if (!t) return false
    transport.value = t
    protocol.value = t.protocol || t.kind
    return true
  }

  function sendConnect(target: SshTarget, fingerprint: string) {
    send({
      type: 'connect',
      host: target.host,
      port: target.port,
      username: target.username,
      password: target.password || undefined,
      private_key: target.privateKey || undefined,
      passphrase: target.passphrase || undefined,
      fingerprint,
      cols: size.cols,
      rows: size.rows,
    })
  }

  async function connect(target: SshTarget, cols: number, rows: number) {
    error.value = ''
    exitStatus.value = null
    hostKey.value = null
    size = { cols, rows }
    pending = target
    phase.value = 'connecting'
    if (!(await open())) {
      phase.value = 'idle'
      error.value = 'Could not reach the panel (HTTP/3, HTTP/2 and WebSocket all failed)'
      return
    }
    sendConnect(target, trusted()[hostId(target)] ?? '')
  }

  /** The admin trusts the shown key: remembered for this host, then the same connect again. */
  function trustAndConnect() {
    if (!pending || !hostKey.value) return
    const all = trusted()
    all[hostId(pending)] = hostKey.value.fingerprint
    localStorage.setItem(TRUSTED_KEY, JSON.stringify(all))
    phase.value = 'connecting'
    sendConnect(pending, hostKey.value.fingerprint)
  }

  function cancel() {
    pending = null
    phase.value = 'idle'
    dropTransport()
  }

  function disconnect() {
    send({ type: 'close' })
    pending = null
    phase.value = 'idle'
    dropTransport()
  }

  function input(data: string) {
    send({ type: 'input', d: data })
  }

  function resize(cols: number, rows: number) {
    size = { cols, rows }
    if (phase.value === 'ready') send({ type: 'resize', cols, rows })
  }

  function request<T>(type: 'ls' | 'read' | 'write' | 'create' | 'mkdir' | 'put' | 'extract', path: string, extra: Record<string, unknown> = {}): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const id = ++seq
      requests.set(id, { resolve, reject })
      if (!send({ type, id, path, ...extra })) {
        requests.delete(id)
        reject(new SshError('not connected', 'connection'))
      }
    })
  }

  /** Runs `command` on the server apart from the terminal: its output as it comes, then its exit status (null: it did not run). */
  function exec(command: string, onData: (data: string) => void): Promise<ExecResult> {
    return new Promise((resolve) => {
      const id = `x${++seq}`
      jobs.set(id, { onData, resolve })
      if (!send({ type: 'exec', id, command, cols: 120, rows: 40 })) {
        jobs.delete(id)
        resolve({ status: null, message: 'not connected' })
      }
    })
  }

  /** Sends a file from this browser to `path`, piece by piece (each one answered before the next); `onProgress` gets 0..1. */
  async function upload(path: string, file: Blob, onProgress: (done: number) => void, overwrite = false): Promise<{ path: string; size: number }> {
    const CHUNK = 512 * 1024
    let offset = 0
    do {
      const piece = new Uint8Array(await file.slice(offset, offset + CHUNK).arrayBuffer())
      let binary = ''
      for (let i = 0; i < piece.length; i += 0x8000) binary += String.fromCharCode(...piece.subarray(i, i + 0x8000))
      const last = offset + piece.length >= file.size
      const answer = await request<{ path?: string; size: number }>('put', path, { offset, data: btoa(binary), last, overwrite })
      offset += piece.length
      onProgress(file.size ? offset / file.size : 1)
      if (last) return { path: answer.path ?? path, size: answer.size }
    } while (offset < file.size)
    return { path, size: offset }
  }

  function stopExec() {
    for (const id of jobs.keys()) send({ type: 'exec_stop', id })
  }

  return {
    exec,
    stopExec,
    phase,
    error,
    hostKey,
    protocol,
    home,
    filesAvailable,
    exitStatus,
    connect,
    trustAndConnect,
    cancel,
    disconnect,
    input,
    resize,
    list: (path: string) => request<Listing>('ls', path),
    read: (path: string) => request<FileContent>('read', path),
    write: (path: string, content: string) => request<{ path: string; size: number }>('write', path, { content }),
    create: (path: string) => request<{ path: string; size: number }>('create', path),
    mkdir: (path: string) => request<{ path: string }>('mkdir', path),
    upload,
    extract: (path: string, dest: string, remove = false) => request<{ path: string; dest: string }>('extract', path, { dest, remove }),
  }
}
