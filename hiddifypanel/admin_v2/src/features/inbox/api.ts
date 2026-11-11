import { getHttp } from '@/core/api/client'

export type Approval = 'auto' | 'manual'
export type FreeStatus = 'none' | 'pending' | 'approved' | 'declined'
export type Sender = 'user' | 'admin' | 'system'
export type MessageKind = 'text' | 'request' | 'granted' | 'declined'
export type FreeAction = 'approve' | 'decline' | 'grant'

/** What someone gets from the free test link. */
export interface FreePackage {
  /** Its id among the admin's packages; missing on a new one ("" for the defaults). */
  id?: string
  enabled: boolean
  days: number
  usage_gb: number
  /** `auto`: given at once, one per Telegram account; `manual`: every request waits for the admin. */
  approval: Approval
}

export interface FreeTest {
  /** The package in effect: this admin's own, else its nearest parent's. */
  package: FreePackage
  /** This admin's own default package; null: it uses its parent's. */
  own: FreePackage | null
  /** All of this admin's own packages; only the default one is offered in the bot. */
  packages: FreePackage[]
  default_id: string | null
  max_packages: number
  can_edit: boolean
  /** The parent whose package applies; null when it is this admin's own (or nobody defined one). */
  inherited_from: string | null
  /** Opens the bot with this admin's offer; null without a bot. */
  link: string | null
  app_link: string | null
  /** This admin may still create a user. */
  has_room: boolean
  limits: { max_days: number; max_usage_gb: number; min_usage_gb: number }
}

export interface Conversation {
  id: number
  name: string
  username: string
  /** The account this person has from this admin. */
  account: { uuid: string; name: string; active: boolean } | null
  free_status: FreeStatus
  /** The package this person asked for or got; null: not yet (shown with the default one). */
  package_id: string | null
  free_grants: number
  /** A waiting request from someone who never had a free test or an account here. */
  first_time: boolean
  unread: number
  last_text: string
  last_sender: Sender
  last_at: string | null
}

export interface ChatMessage {
  id: number
  sender: Sender
  kind: MessageKind
  /** `granted`: "<days>|<usage_gb>" of the package given. */
  text: string
  at: string
}

export interface InboxCounts {
  /** Conversations with unread messages. */
  unread: number
  /** Free test requests waiting. */
  pending: number
  /** Conversations that need the admin: unread, or with a request waiting. */
  waiting: number
}

export interface Inbox extends InboxCounts {
  bot_username: string
  free: FreeTest
  conversations: Conversation[]
}

export interface Thread {
  conversation: Conversation
  messages: ChatMessage[]
}

export const inboxApi = {
  async get(): Promise<Inbox> {
    const { data } = await getHttp().get<Inbox>('inbox/')
    return data
  },
  async counts(): Promise<InboxCounts> {
    const { data } = await getHttp().get<InboxCounts>('inbox/counts/')
    return data
  },
  /** `null`: back to the parent's package. */
  async savePackage(value: FreePackage | null): Promise<FreeTest> {
    const { data } = await getHttp().put<FreeTest>('inbox/free-test/', value ?? { inherit: true })
    return data
  },
  /** Set all of this admin's own packages and which one is the default (a package without an id is a new one). */
  async savePackages(packages: FreePackage[], defaultId: string | null): Promise<FreeTest> {
    const { data } = await getHttp().put<FreeTest>('inbox/free-test/', { packages, default: defaultId })
    return data
  },
  /** Opening a conversation marks it read. */
  async thread(id: number): Promise<Thread> {
    const { data } = await getHttp().get<Thread>(`inbox/${id}/`)
    return data
  },
  async send(id: number, text: string): Promise<Thread> {
    const { data } = await getHttp().post<Thread>(`inbox/${id}/`, { text })
    return data
  },
  async answer(id: number, action: FreeAction): Promise<Thread> {
    const { data } = await getHttp().post<Thread>(`inbox/${id}/free/`, { action })
    return data
  },
  async remove(id: number): Promise<void> {
    await getHttp().delete(`inbox/${id}/`)
  },
}
