import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * "5 min ago" for Unix-second times of the server. `serverTime` is the server's clock at the last answer:
 * the difference to the browser's is taken out, so a wrong browser clock does not show wrong ages. Ticks every second.
 */
export function useServerClock(serverTime: Ref<number | undefined>) {
  const { locale } = useI18n()
  const browserNow = ref(Date.now() / 1000)
  let clock: number | undefined

  onMounted(() => (clock = window.setInterval(() => (browserNow.value = Date.now() / 1000), 1000)))
  onBeforeUnmount(() => window.clearInterval(clock))

  // The skew is fixed when an answer arrives, not on every tick.
  const skew = ref(0)
  watch(
    serverTime,
    (t) => {
      if (t !== undefined) skew.value = t - Date.now() / 1000
    },
    { immediate: true },
  )

  const now = computed(() => browserNow.value + skew.value)
  const rtf = computed(() => new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto', style: 'short' }))

  function ago(at: number): string {
    const diff = Math.round(at - now.value)
    const abs = Math.abs(diff)
    if (abs < 60) return rtf.value.format(diff, 'second')
    if (abs < 3600) return rtf.value.format(Math.round(diff / 60), 'minute')
    if (abs < 86400) return rtf.value.format(Math.round(diff / 3600), 'hour')
    return rtf.value.format(Math.round(diff / 86400), 'day')
  }

  function absolute(at: number): string {
    return new Date(at * 1000).toLocaleString(locale.value)
  }

  /** Seconds since `at`. */
  function age(at: number): number {
    return now.value - at
  }

  return { ago, absolute, age }
}
