import { getHttp } from '@/core/api/client'

export type Audience = 'all' | 'active' | 'expired' | 'offline_1h' | 'offline_1d' | 'offline_1w' | 'selected'
export type MessageFormat = 'plain' | 'markdown' | 'html'

export interface BroadcastState {
  /** The Telegram bot is set up (a token, running). */
  bot: boolean
  bot_username: string
  /** Users each audience reaches (they started the bot; never deleted users). */
  counts: Record<Audience, number>
  limits: { text: number; caption: number; image_bytes: number }
}

export interface BroadcastJob {
  id: string
  total: number
  sent: number
  failed: number
  state: 'running' | 'done' | 'failed'
  started: number
  finished: number | null
  errors: { name: string; error: string }[]
}

/** A user an audience reaches (they started the bot). */
export interface Recipient {
  id: number
  name: string
  active: boolean
  last_online: string | null
  telegram_id: string
}

export interface SendInput {
  text: string
  format: MessageFormat
  audience: Audience
  ids: number[]
  addUsage: boolean
  image: File | null
}

export const broadcastApi = {
  async state(ids: number[]): Promise<BroadcastState> {
    const { data } = await getHttp().get<BroadcastState>('broadcast/', { params: ids.length ? { ids: ids.join(',') } : {} })
    return data
  },
  async recipients(audience: Audience, ids: number[]): Promise<Recipient[]> {
    const params: Record<string, string> = { audience }
    if (ids.length) params.ids = ids.join(',')
    const { data } = await getHttp().get<{ users: Recipient[] }>('broadcast/recipients/', { params })
    return data.users
  },
  /** The text as Telegram will show it (Telegram's HTML) and its length. */
  async preview(text: string, format: MessageFormat): Promise<{ html: string; length: number }> {
    const { data } = await getHttp().post<{ html: string; length: number }>('broadcast/preview/', { text, format })
    return data
  },
  async send(input: SendInput): Promise<BroadcastJob> {
    const form = new FormData()
    form.append('text', input.text)
    form.append('format', input.format)
    form.append('audience', input.audience)
    form.append('ids', input.ids.join(','))
    form.append('add_usage', String(input.addUsage))
    if (input.image) form.append('image', input.image)
    const { data } = await getHttp().post<BroadcastJob>('broadcast/', form, { headers: { 'Content-Type': undefined } })
    return data
  },
}

/** Telegram accepts these as a photo. */
export const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
