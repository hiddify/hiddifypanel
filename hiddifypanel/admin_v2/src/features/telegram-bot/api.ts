import { getHttp } from '@/core/api/client'

/** Why Telegram could not be asked: the token is wrong, or Telegram is out of the server's reach. */
export type BotError = 'token_rejected' | 'unreachable'

export interface BotInfo {
  id: number
  /** The bot's display name. */
  name: string
  username: string
  groups: boolean
  main_app: boolean
}

export interface WebhookInfo {
  /** Telegram has an address to send updates to. */
  set: boolean
  /** ...and it is this panel's. */
  matches: boolean
  /** The panel domain Telegram is pointed at. */
  domain: string
  /** Updates Telegram still holds (not delivered yet). */
  pending: number
  /** Telegram's last delivery error (its own English text), and when. */
  last_error: string | null
  last_error_at: string | null
}

export interface IconsInfo {
  enabled: boolean
  /** Telegram refused the icons (the owner has no Premium): plain emoji for a day, or until saved again. */
  refused: boolean
  /** The custom emoji sets, comma separated; empty: the defaults. */
  sets: string
  default_sets: string[]
  /** Of the emoji the bot's buttons start with, how many have an animated icon (null: not checked). */
  found: number | null
  needed: number | null
  /** The button emoji no set has (they stay plain). */
  missing: string[]
}

export interface BotState {
  /** A token is set. */
  configured: boolean
  bot: BotInfo | null
  error: BotError | null
  webhook: WebhookInfo | null
  /** This admin's Telegram is connected to the bot. */
  me_connected: boolean
  admins_connected: number
  users_connected: number
  icons: IconsInfo
}

export type TestError = 'not_connected' | 'blocked' | BotError

export const telegramBotApi = {
  async state(): Promise<BotState> {
    const { data } = await getHttp().get<BotState>('telegram-bot/', { timeout: 60_000 })
    return data
  },
  async test(): Promise<{ ok: boolean; error: TestError | null }> {
    const { data } = await getHttp().post<{ ok: boolean; error: TestError | null }>('telegram-bot/test/', {}, { timeout: 30_000 })
    return data
  },
  async setWebhook(): Promise<{ ok: boolean; state: BotState }> {
    const { data } = await getHttp().post<{ ok: boolean; state: BotState }>('telegram-bot/webhook/', {}, { timeout: 60_000 })
    return data
  },
  async saveIcons(input: { enabled?: boolean; sets?: string }): Promise<IconsInfo> {
    const { data } = await getHttp().put<IconsInfo>('telegram-bot/icons/', input, { timeout: 60_000 })
    return data
  },
}
