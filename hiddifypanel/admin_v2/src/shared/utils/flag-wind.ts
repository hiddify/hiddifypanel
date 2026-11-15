/**
 * The wind behind the waving flags (FlagIcon `waving`): the cloth's shape over time, and one animation loop for
 * every flag on the page, which only runs while some flag is on screen and the tab is visible, and never with
 * "reduce motion".
 *
 * The cloth (its shape measured from a reference animation, in flag heights and widths; its pace made calmer):
 * - the pole edge never moves; the cloth falls away from it: the top edge about 0.56 at the flying end, the bottom
 *   corner about 0.23, so the end is two thirds as tall, and the cloth is a tenth narrower;
 * - the wind rises and falls slowly (7.6 s, with a slower 12.3 s drift): in a lull the cloth hangs lower, in the
 *   stronger wind it lifts and ripples more;
 * - two soft ripples of different pace (1.7 s and 2.9 s) run along it to the flying end, and the end's two corners
 *   rock opposite each other (2.3 s and 3.7 s), so the flying edge keeps leaning one way and the other.
 * None of these periods divides another, so no moment comes back the same: it looks alive, not looped.
 */
export const FLAG_W = 400
export const FLAG_H = 300
/** How a flag that must not move is drawn: the cloth at this moment */
export const REST = 0
const TAU = Math.PI * 2

/**
 * One line of the cloth from its top edge to its bottom edge: where the two ends are (viewBox units; the line leans
 * when the ends differ in x) and how the light falls on it (-1 lit … 1 shaded)
 */
export interface Column {
  xt: number
  xb: number
  top: number
  bottom: number
  shade: number
}

/** The cloth at u (0 at the pole … 1 at the flying end) at time t (seconds) */
export function cloth(u: number, t: number, out: Column): Column {
  // the wind's strength, 0 (a lull) … 1
  const wind = 0.5 + 0.3 * Math.sin((TAU * t) / 7.6 + 0.4) + 0.2 * Math.sin((TAU * t) / 12.3 + 2.1)
  const lively = 0.6 + 0.6 * wind
  const p1 = TAU * (t / 1.7 - 1.3 * u)
  const p2 = TAU * (t / 2.9 - 0.8 * u) + 1.9
  const rock = 0.05 * u * u * (0.6 * Math.sin((TAU * t) / 2.3 + 1.7) + 0.4 * Math.sin((TAU * t) / 3.7))
  const narrow = u * (1 - (0.13 - 0.05 * wind) * Math.sqrt(u))
  out.xt = FLAG_W * (narrow - rock)
  out.xb = FLAG_W * (narrow + rock)
  out.top = FLAG_H * ((0.66 - 0.2 * wind) * Math.pow(u, 1.75) + 0.1 * Math.pow(u, 2.2) * lively * (0.6 * Math.sin(p1 + 2.3) + 0.5 * Math.sin(p2 + 1.1)))
  out.bottom = FLAG_H * (1 + (0.28 - 0.1 * wind) * Math.pow(u, 2.4) + 0.05 * Math.pow(u, 0.8) * lively * (0.6 * Math.sin(p1) + 0.5 * Math.sin(p2)))
  // a fold that turns up catches the light; the cloth is dimmer where it turns away from us
  out.shade = 0.8 * Math.sqrt(u) * (0.6 * Math.cos(p1) + 0.5 * Math.cos(p2)) + 0.1 * u
  return out
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
