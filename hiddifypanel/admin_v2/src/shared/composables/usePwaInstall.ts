/**
 * Installing the panel as an app (PWA). Chrome / Edge / Android fire `beforeinstallprompt`, which we keep to show the
 * browser's install dialog on a click; Safari (iOS) has no such event: there the user adds it from the share menu.
 * The listener is set when this module is first imported (main.ts imports it early, the event can come before any view).
 */
import { computed, ref } from 'vue'

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const DISMISS_KEY = 'hiddify.pwaInstall.dismissed'

const deferred = ref<BeforeInstallPromptEvent | null>(null)
const installed = ref(isStandalone())

function isStandalone(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia?.('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true
}

function isIos(): boolean {
  if (typeof navigator === 'undefined') return false
  return /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

/** Which install guide fits this device: Safari on iPhone / iPad, Chrome on Android, Chrome on a computer. */
export type PwaPlatform = 'ios' | 'android' | 'desktop'
export function detectPwaPlatform(): PwaPlatform {
  if (isIos()) return 'ios'
  if (typeof navigator !== 'undefined' && /android/i.test(navigator.userAgent)) return 'android'
  return 'desktop'
}
/** The computer's system, for the guide's title. */
export function desktopOsName(): string {
  const ua = typeof navigator === 'undefined' ? '' : navigator.userAgent
  if (/windows/i.test(ua)) return 'Windows'
  if (/mac os|macintosh/i.test(ua)) return 'macOS'
  if (/linux|x11|cros/i.test(ua)) return 'Linux'
  return 'Windows · macOS · Linux'
}

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault() // keep it for our own dialog / button
    deferred.value = e as BeforeInstallPromptEvent
  })
  window.addEventListener('appinstalled', () => {
    installed.value = true
    deferred.value = null
  })
}

function readDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISS_KEY) === '1'
  } catch {
    return false
  }
}

const dismissed = ref(readDismissed())

export function usePwaInstall() {
  /** The browser can show its install dialog. */
  const canPrompt = computed(() => !installed.value && !!deferred.value)
  /** iOS Safari: no install dialog, only "Add to Home Screen" from the share menu. */
  const iosManual = computed(() => !installed.value && !deferred.value && isIos())
  /** Something to offer: a dialog to open, or the iOS steps to show. */
  const available = computed(() => canPrompt.value || iosManual.value)

  async function install(): Promise<boolean> {
    const event = deferred.value
    if (!event) return false
    deferred.value = null // a prompt can be used once, also when it fails
    await event.prompt() // first, while the click still counts as the user's (the browser requires it)
    const { outcome } = await event.userChoice
    if (outcome === 'accepted') installed.value = true
    return outcome === 'accepted'
  }

  /** "Do not show again": kept in this browser only. */
  function dismissForever() {
    dismissed.value = true
    try {
      localStorage.setItem(DISMISS_KEY, '1')
    } catch {
      /* private mode: just for this visit */
    }
  }

  return { installed, canPrompt, iosManual, available, dismissed, install, dismissForever }
}
