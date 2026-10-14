/** The SSH page's layout choices (a panel shown or hidden), kept in this browser; a default when storage can't be used. */
import { ref, watch, type Ref } from 'vue'

const PREFIX = 'hiddify.ssh.pref.'

export function usePref(name: string, fallback: boolean): Ref<boolean> {
  let initial = fallback
  try {
    const raw = localStorage.getItem(PREFIX + name)
    if (raw !== null) initial = raw === '1'
  } catch {
    /* private window, blocked storage */
  }
  const value = ref(initial)
  watch(value, (v) => {
    try {
      localStorage.setItem(PREFIX + name, v ? '1' : '0')
    } catch {
      /* not kept */
    }
  })
  return value
}
