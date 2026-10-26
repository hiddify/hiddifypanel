import { telegramInfo } from '@/core/panelShell'

/**
 * The dashboard's spotlights, one per visit: the Telegram prompt first (while the admin has not linked the panel's
 * bot and has not answered it in this browser), the install guide from the next visit on.
 */
export const TELEGRAM_PROMPT_KEY = 'hiddify.admin.telegramPrompt'

export function telegramPromptDue(): boolean {
  const info = telegramInfo.value
  if (!info || info.connected) return false
  try {
    return localStorage.getItem(TELEGRAM_PROMPT_KEY) !== '1'
  } catch {
    return false
  }
}
