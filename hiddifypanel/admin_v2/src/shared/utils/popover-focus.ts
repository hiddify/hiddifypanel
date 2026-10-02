import { nextTick } from 'vue'

/**
 * A filter popover that was just opened: the first text box in it (search field / list filter)
 * takes the keyboard, so one click on the filter icon is enough to start typing.
 */
export function focusFirstInput(popover: { container?: HTMLElement | null } | undefined): void {
  void nextTick(() => setTimeout(() => popover?.container?.querySelector<HTMLInputElement>('input')?.focus(), 0))
}
