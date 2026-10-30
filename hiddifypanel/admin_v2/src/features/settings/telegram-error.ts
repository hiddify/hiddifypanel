/**
 * Why the Telegram bot could not connect, from the panel's error (tgbot.register_bot), so Settings can say it in plain
 * words with the steps that fix it. A failed getMe is reported as "Invalid token: …" whatever the cause, so a network
 * error is looked for first.
 */
export type TelegramErrorKind = 'network' | 'webhook' | 'badToken' | 'other'

const RULES: [TelegramErrorKind, RegExp][] = [
  ['network', /HTTPSConnectionPool|Max retries|timed? ?out|Connection ?(Error|refused|reset|aborted)|Name or service not known|name resolution|Failed to resolve|Network is unreachable|ProxyError/i],
  ['webhook', /webhook|valid domain/i],
  ['badToken', /\b401\b|Unauthorized|\b404\b|Not Found|Invalid token|must contain a colon|token is invalid/i],
]

/** How many numbered steps each kind has (settings.tgError.<kind>.step1 …) */
export const TELEGRAM_ERROR_STEPS: Record<TelegramErrorKind, number> = { network: 3, webhook: 2, badToken: 3, other: 2 }

export function telegramErrorKind(error: string): TelegramErrorKind {
  return RULES.find(([, re]) => re.test(error))?.[0] ?? 'other'
}
