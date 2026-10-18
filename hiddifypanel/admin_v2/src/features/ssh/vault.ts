/**
 * What the SSH page keeps in this browser for the signed-in admin, encrypted with its key (`ConnectionCipher`, saved.ts):
 * connections (a password, or a saved key by its id), named private keys (the last one used is the default) and commands
 * (run on one or several open sessions). One store for all the page's tabs.
 */
import { computed, reactive } from 'vue'
import { canSave, ConnectionCipher } from './saved'

export interface VaultKey {
  id: string
  name: string
  privateKey: string
  passphrase?: string
  lastUsed: number
}

export interface VaultConnection {
  id: string
  /** Optional label the admin chose (e.g. "Main server", "Node 3") so many similar hosts stay distinct. */
  name?: string
  host: string
  port: number
  username: string
  auth: 'password' | 'key'
  password?: string
  keyId?: string
  lastUsed: number
}

/** Address as `user@host` (with port when not 22). */
export function connectionAddr(c: Pick<VaultConnection, 'host' | 'port' | 'username'>): string {
  return `${c.username}@${c.host}${c.port !== 22 ? `:${c.port}` : ''}`
}

/** What to show for a saved connection: its name, or the address when it has none. */
export function connectionTitle(c: VaultConnection): string {
  const name = c.name?.trim()
  return name || connectionAddr(c)
}

export interface VaultCommand {
  id: string
  name: string
  command: string
  /** Comes with the panel (not saved, can not be removed); `name` is a translation key then. */
  builtin?: boolean
}

/** The commands that come with the panel. */
export const BUILTIN_COMMANDS: VaultCommand[] = [
  {
    id: 'builtin:install-hiddify',
    name: 'ssh.cmd.installHiddify',
    command: 'bash <(curl https://i.hiddify.com/release)',
    builtin: true,
  },
]

interface VaultData {
  connections: VaultConnection[]
  keys: VaultKey[]
  commands: VaultCommand[]
}

/** A connection with its secret in it (a deep link carries this). */
export interface ConnectTarget {
  host: string
  port: number
  username: string
  auth: 'password' | 'key'
  password?: string
  privateKey?: string
  passphrase?: string
  /** The saved key it used, if any (kept apart from the connection). */
  keyId?: string
  keyName?: string
}

/** A connection as a link (`?host=&port=&user=&s=`): the server in the clear, the secret sealed for one admin. */
export interface DeepLink {
  host: string
  port: number
  user: string
  /** The sealed {auth, password | privateKey, passphrase, keyName}; '' when there is none. */
  s: string
}

/** The connection of a link: with its secret when this admin can open it, else without (the form is filled). */
export async function openDeepLink(query: Record<string, unknown>): Promise<{ target: ConnectTarget; secretOk: boolean } | null> {
  const host = typeof query.host === 'string' ? query.host : ''
  const user = typeof query.user === 'string' ? query.user : ''
  if (!host || !user) return null
  const port = Number(query.port) || 22
  const base: ConnectTarget = { host, port, username: user, auth: 'password' }
  const sealed = typeof query.s === 'string' ? query.s : ''
  await (loading ??= load())
  if (!sealed || !cipher) return { target: base, secretOk: !sealed }
  try {
    const secret = await cipher.open<Pick<ConnectTarget, 'auth' | 'password' | 'privateKey' | 'passphrase' | 'keyName'>>(sealed)
    return { target: { ...base, ...secret }, secretOk: true }
  } catch {
    return { target: base, secretOk: false }
  }
}

const PREFIX = 'hiddify.ssh.vault.'
const OLD_PREFIX = 'hiddify.ssh.saved.'

const state = reactive({
  ready: false,
  available: canSave(),
  error: '',
  data: { connections: [], keys: [], commands: [] } as VaultData,
})
let cipher: ConnectionCipher | null = null
let loading: Promise<void> | null = null

function storageKey(): string {
  return PREFIX + (cipher?.owner ?? '')
}

async function persist() {
  if (!cipher) return
  localStorage.setItem(storageKey(), await cipher.seal(state.data))
}

/** The previous version kept only connections, a private key inside each: each key becomes a named one. */
async function migrate(): Promise<VaultData | null> {
  const raw = cipher && localStorage.getItem(OLD_PREFIX + cipher.owner)
  if (!cipher || !raw || raw.startsWith('{')) return null
  try {
    const old = await cipher.open<
      (Omit<VaultConnection, 'keyId'> & {
        privateKey?: string
        passphrase?: string
      })[]
    >(raw)
    const data: VaultData = { connections: [], keys: [], commands: [] }
    for (const c of old) {
      let keyId: string | undefined
      if (c.auth === 'key' && c.privateKey) {
        keyId = crypto.randomUUID()
        data.keys.push({
          id: keyId,
          name: `${c.username}@${c.host}`,
          privateKey: c.privateKey,
          passphrase: c.passphrase,
          lastUsed: c.lastUsed,
        })
      }
      data.connections.push({
        id: c.id,
        name: (c as { name?: string }).name,
        host: c.host,
        port: c.port,
        username: c.username,
        auth: c.auth,
        password: c.password,
        keyId,
        lastUsed: c.lastUsed,
      })
    }
    return data
  } catch {
    return null
  }
}

async function load() {
  if (!state.available) {
    state.ready = true
    return
  }
  try {
    cipher = await ConnectionCipher.forCurrentAdmin()
    const raw = localStorage.getItem(storageKey())
    const data = raw ? await cipher.open<VaultData>(raw) : await migrate()
    if (data)
      state.data = {
        connections: data.connections ?? [],
        keys: data.keys ?? [],
        commands: data.commands ?? [],
      }
    if (!raw && data) await persist()
  } catch {
    state.error = 'unreadable'
  } finally {
    state.ready = true
  }
}

const byRecent = <T extends { lastUsed: number }>(items: T[]) => [...items].sort((a, b) => b.lastUsed - a.lastUsed)

export function useVault() {
  loading ??= load()
  return {
    state,
    loaded: () => loading!,
    cipher: () => cipher,
    connections: computed(() => byRecent(state.data.connections)),
    keys: computed(() => byRecent(state.data.keys)),
    commands: computed(() => [...BUILTIN_COMMANDS, ...state.data.commands]),
    /** The key used last: the default for a new connection. */
    lastKey: computed(() => byRecent(state.data.keys)[0] ?? null),

    keyOf(c: VaultConnection): VaultKey | undefined {
      return state.data.keys.find((k) => k.id === c.keyId)
    },

    /** Saves a key (same content: renamed and marked used); its id. */
    async saveKey(name: string, privateKey: string, passphrase?: string): Promise<string> {
      const found = state.data.keys.find((k) => k.privateKey.trim() === privateKey.trim())
      const key: VaultKey = {
        id: found?.id ?? crypto.randomUUID(),
        name: name.trim() || found?.name || 'key',
        privateKey,
        passphrase: passphrase || undefined,
        lastUsed: Date.now(),
      }
      state.data.keys = [key, ...state.data.keys.filter((k) => k.id !== key.id)]
      await persist()
      return key.id
    },

    async useKey(id: string) {
      const key = state.data.keys.find((k) => k.id === id)
      if (key) key.lastUsed = Date.now()
      await persist()
    },

    async removeKey(id: string) {
      state.data.keys = state.data.keys.filter((k) => k.id !== id)
      for (const c of state.data.connections) if (c.keyId === id) c.keyId = undefined
      await persist()
    },

    /** Adds or updates (by ``id`` when given, else same user/host/port) and marks it used now. */
    async saveConnection(c: Omit<VaultConnection, 'id' | 'lastUsed'> & { id?: string }) {
      const sameHost = (o: VaultConnection) => o.host.toLowerCase() === c.host.toLowerCase() && o.port === c.port && o.username === c.username
      const found = (c.id ? state.data.connections.find((o) => o.id === c.id) : undefined) ?? state.data.connections.find(sameHost)
      const name = (c.name ?? found?.name)?.trim() || undefined
      const next: VaultConnection = {
        ...c,
        name,
        id: found?.id ?? c.id ?? crypto.randomUUID(),
        lastUsed: Date.now(),
      }
      state.data.connections = [next, ...state.data.connections.filter((o) => o.id !== next.id && !sameHost(o))]
      await persist()
      return next
    },

    async removeConnection(id: string) {
      state.data.connections = state.data.connections.filter((c) => c.id !== id)
      await persist()
    },

    async saveCommand(command: Omit<VaultCommand, 'id'> & { id?: string }) {
      const next: VaultCommand = {
        id: command.id ?? crypto.randomUUID(),
        name: command.name.trim(),
        command: command.command,
      }
      const exists = state.data.commands.some((c) => c.id === next.id)
      state.data.commands = exists ? state.data.commands.map((c) => (c.id === next.id ? next : c)) : [...state.data.commands, next]
      await persist()
    },

    async removeCommand(id: string) {
      state.data.commands = state.data.commands.filter((c) => c.id !== id)
      await persist()
    },
  }
}
