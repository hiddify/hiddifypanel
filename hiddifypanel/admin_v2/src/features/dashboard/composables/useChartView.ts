import { ref, watch, type Ref } from 'vue'

/**
 * The way a dashboard tile shows its data (bars, a calendar, rings…), chosen with its view switch and kept in this
 * browser, one choice per tile. An unknown stored value (a view since removed) falls back to the first one.
 */
export function useChartView<T extends string>(tile: string, views: readonly T[]): Ref<T> {
  const key = `hm.dash.view.${tile}`
  let stored: string | null = null
  try {
    stored = localStorage.getItem(key)
  } catch {
    /* private mode: the choice lasts this page only */
  }
  const view = ref((views as readonly string[]).includes(stored ?? '') ? (stored as T) : views[0]!) as Ref<T>
  watch(view, (value) => {
    try {
      localStorage.setItem(key, value)
    } catch {
      /* ignore */
    }
  })
  return view
}
