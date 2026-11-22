/**
 * The admin panel opened from the Telegram bot (its "Hiddify" menu button or the bot's Open button): full screen on
 * a phone, the page clear of Telegram's floating buttons and the notch.
 *
 * The bot's sign-in page (api/v1/tgbot/app/) marks this tab with `hiddify.tg` in sessionStorage before it opens
 * the panel: the panel's address never carries Telegram's data (a copied address must sign nobody in), and a plain
 * browser never loads Telegram's script. In full screen Telegram gives the heights of its buttons and of the notch
 * as CSS variables; the layout's --safe-top (topbar, menu, content) takes them (`tg-fullscreen`, _topbar.scss).
 */

interface TelegramWebApp {
  version: string
  platform: string
  isFullscreen?: boolean
  ready(): void
  expand(): void
  isVersionAtLeast(version: string): boolean
  requestFullscreen?(): void
  disableVerticalSwipes?(): void
  onEvent?(event: string, handler: () => void): void
  HapticFeedback?: { impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void }
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}

const MARK = 'hiddify.tg'
const SCRIPT_URL = 'https://telegram.org/js/telegram-web-app.js'

export function openedFromTelegram(): boolean {
  try {
    return sessionStorage.getItem(MARK) === '1' || /tgWebAppData=|tgWebAppPlatform=/.test(window.location.hash)
  } catch {
    return false
  }
}

/** Advanced mode (the bot's sign-in page sets the mark): every button, link and switch taps the phone lightly. */
function haptics(app: TelegramWebApp): void {
  let on = false
  try {
    on = sessionStorage.getItem('hiddify.tg.haptics') === '1'
  } catch {
    on = false
  }
  if (!on || !app.HapticFeedback) return
  document.addEventListener(
    'click',
    (event) => {
      const target = event.target as Element | null
      if (target?.closest('button, a, [role="button"], [role="switch"], [role="tab"], .p-button, .p-toggleswitch')) app.HapticFeedback?.impactOccurred('light')
    },
    { capture: true, passive: true },
  )
}

function fit(app: TelegramWebApp): void {
  haptics(app)
  app.ready()
  app.expand()
  if (app.isVersionAtLeast('7.7')) app.disableVerticalSwipes?.()
  const phone = app.platform === 'ios' || app.platform === 'android'
  if (!phone || !app.isVersionAtLeast('8.0')) return
  const mark = () => document.documentElement.classList.toggle('tg-fullscreen', !!app.isFullscreen)
  app.onEvent?.('fullscreenChanged', mark)
  if (!app.isFullscreen) {
    try {
      app.requestFullscreen?.()
    } catch {
      /* an older client: the panel stays as it is */
    }
  }
  mark()
}

export function setupTelegramMiniApp(): void {
  if (!openedFromTelegram()) return
  if (window.Telegram?.WebApp) return fit(window.Telegram.WebApp)
  const script = document.createElement('script')
  script.src = SCRIPT_URL
  script.async = true
  script.onload = () => window.Telegram?.WebApp && fit(window.Telegram.WebApp)
  document.head.appendChild(script)
}
