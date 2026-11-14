/**
 * The wind behind the waving flags (FlagIcon `waving`): one animation loop for every flag on the page, which only
 * runs while some flag is on screen and the tab is visible, and never with "reduce motion".
 *
 * A flag is a row of thin vertical strips. Each strip is skewed so that its left edge follows the wave at its left
 * and its right edge the wave at its right: neighbouring strips share their edges, so the cloth is one continuous
 * surface (no steps). The wave starts at the pole and grows towards the flying end; a second, faster ripple on top
 * keeps it from looking mechanical.
 */
export const FLAG_W = 400
export const FLAG_H = 300

const AMP = 15 // the largest lift at the flying end (viewBox units, 5% of the height)
const WAVELENGTH = FLAG_W * 0.9
const PERIOD = 2.6 // seconds
const K = (2 * Math.PI) / WAVELENGTH
const W = (2 * Math.PI) / PERIOD

/** The cloth's lift at x (0 at the pole) at time t (seconds) */
export function lift(x: number, t: number): number {
  const reach = Math.pow(x / FLAG_W, 1.15)
  return AMP * reach * (Math.sin(K * x - W * t) + 0.32 * Math.sin(2.15 * K * x - 1.7 * W * t + 1.3))
}

type Flag = (t: number) => void
const flags = new Set<Flag>()
let frame = 0
const reduce = typeof window !== 'undefined' ? window.matchMedia('(prefers-reduced-motion: reduce)') : null

function loop(now: number) {
  frame = 0
  if (!flags.size || document.hidden) return
  const t = now / 1000
  for (const draw of flags) draw(t)
  frame = requestAnimationFrame(loop)
}
function start() {
  if (!frame && flags.size && !document.hidden) frame = requestAnimationFrame(loop)
}
if (typeof document !== 'undefined') document.addEventListener('visibilitychange', start)

export const windAllowed = () => !reduce?.matches

/** Animate a flag while it is on screen; returns the function that stops it */
export function blow(draw: Flag): () => void {
  flags.add(draw)
  start()
  return () => {
    flags.delete(draw)
  }
}
