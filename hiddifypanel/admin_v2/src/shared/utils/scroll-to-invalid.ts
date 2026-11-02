import { nextTick } from 'vue'

/** What marks a field as wrong: PrimeVue's `invalid` prop, `aria-invalid`, or a form's own error-hint class. */
const INVALID = '.p-invalid, [aria-invalid="true"]'

/**
 * A submit stopped by a wrong field: bring the first one into view and put the cursor in it.
 * Without this, a field at the top of a long dialog turns red out of sight and "Create" seems to do nothing.
 * Call it after the flags that mark the fields (`touched`, an opened section) are set; it waits for the render.
 */
export async function scrollToFirstInvalid(root: HTMLElement | null | undefined, extra = ''): Promise<boolean> {
  await nextTick()
  if (!root) return false
  const target = root.querySelector<HTMLElement>(extra ? `${INVALID}, ${extra}` : INVALID)
  if (!target) return false
  // An error hint under a field: the field around it is the one to focus
  const field = target.parentElement ?? target
  const focusable = target.matches('input, textarea, select, [tabindex]')
    ? target
    : (target.querySelector<HTMLElement>('input, textarea, select, [tabindex]') ?? field.querySelector<HTMLElement>('input, textarea, select, [tabindex]'))
  target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  focusable?.focus({ preventScroll: true })
  return true
}
