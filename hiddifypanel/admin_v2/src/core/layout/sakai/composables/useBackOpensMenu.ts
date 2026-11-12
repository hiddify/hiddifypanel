/**
 * The installed app (PWA) on a phone: "back" opens the menu, it never leaves the page.
 *
 * Android's back gesture (a swipe from the screen's edge) belongs to the system: the page never sees the touch, only
 * the history step that follows. So a guard entry, with the same URL, sits on top of every page: "back" (the gesture
 * or the button) only steps off the guard, onto the same page. That step is kept from the router (a capturing listener
 * on window runs first), the menu opens and the guard goes back on top.
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const PHONE_QUERY = '(max-width: 991px)'
const APP_QUERY = '(display-mode: standalone), (display-mode: fullscreen), (display-mode: minimal-ui)'
const GUARD = 'hiddifyBackGuard'

export function useBackOpensMenu(options: { setOpen: (open: boolean) => void }) {
  const router = useRouter()
  const phone = window.matchMedia(PHONE_QUERY)
  const app = window.matchMedia(APP_QUERY)
  const active = () => phone.matches && (app.matches || (navigator as { standalone?: boolean }).standalone === true)

  /** The URL the router is showing */
  const shownUrl = () => new URL(router.resolve(router.currentRoute.value.fullPath).href, location.href).href

  /** Puts the guard on top of the current entry, unless it is there already. It holds its URL: an entry the router
   * replaced keeps the old guard flag, which then no longer matches. */
  function guard() {
    if (!active() || history.state?.[GUARD] === location.href) return
    history.pushState({ ...history.state, [GUARD]: location.href }, '', location.href)
  }

  function onPopState(e: PopStateEvent) {
    if (!active() || e.state?.[GUARD] === location.href) return
    // a step to another page (no guard was in between): a real navigation, the router follows it
    if (location.href !== shownUrl()) return
    e.stopImmediatePropagation() // the same page: not a navigation, the router must not see it
    options.setOpen(true)
    guard()
  }

  let removeAfterEach: (() => void) | null = null
  onMounted(() => {
    window.addEventListener('popstate', onPopState, { capture: true })
    removeAfterEach = router.afterEach(() => setTimeout(guard))
    router.isReady().then(guard)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('popstate', onPopState, { capture: true })
    removeAfterEach?.()
  })
}
