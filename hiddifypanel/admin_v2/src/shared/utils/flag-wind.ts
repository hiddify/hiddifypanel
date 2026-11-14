/**
 * The wind behind the waving flags (FlagIcon `waving`): the cloth's shape over time, and one animation loop for
 * every flag on the page, which only runs while some flag is on screen and the tab is visible, and never with
 * "reduce motion".
 *
 * The cloth, in a 3 second loop (numbers measured from a reference animation, in flag heights):
 * - the pole edge never moves;
 * - most of the loop the cloth flies low: its top edge falls away towards the flying end (0.62 there), the cloth
 *   gets shorter as it turns away (half its height at the end) and a little narrower (7.5%);
 * - a wave runs along it to the flying end, which flaps up and down (0.3 at the bottom corner, two flaps a loop);
 * - once a loop a gust pulls it flat and fully stretched for a moment, then it falls back.
 */
export const FLAG_W = 400
export const FLAG_H = 300
/** Seconds: the loop, and one flap of the flying end (two a loop, so the loop closes) */
const LOOP = 3
const FLAP = LOOP / 2
const TAU = Math.PI * 2

const smooth = (from: number, to: number, x: number) => {
  const k = Math.min(1, Math.max(0, (x - from) / (to - from)))
  return k * k * (3 - 2 * k)
}

/** 0 while the gust holds the cloth flat (the middle of the loop), 1 while it flies low; it falls faster than it rises */
function sag(t: number): number {
  const d = (((t % LOOP) + LOOP) % LOOP) - LOOP / 2
  return d < 0 ? smooth(0.1, 0.5, -d) : smooth(0.1, 0.7, d)
}

/** One vertical line of the cloth: where it is (viewBox units) and how the light falls on it (-1 lit … 1 shaded) */
export interface Column {
  x: number
  top: number
  bottom: number
  shade: number
}

/** The cloth at u (0 at the pole … 1 at the flying end) at time t (seconds) */
export function column(u: number, t: number, out: Column): Column {
  const s = sag(t)
  const phase = TAU * (t / FLAP - 0.75 * u) + 2.39
  const wave = Math.sin(phase) + 0.2 * Math.sin(2 * phase)
  // the top corner swings a little ahead of the bottom one
  const lead = Math.sin(phase + 0.84)
  const reach = Math.pow(u, 2.5)
  const top = s * (0.62 * Math.pow(u, 1.8) + 0.2 * reach * lead)
  const bottom = 1 + s * (0.12 * Math.pow(u, 1.5) + 0.3 * reach * wave)
  out.x = FLAG_W * u * (1 - 0.075 * s * Math.sqrt(u))
  out.top = FLAG_H * top
  out.bottom = FLAG_H * Math.max(bottom, top + 0.2)
  // a fold that turns up catches the light; the cloth is dimmer where it turns away from us
  out.shade = s * (0.85 * u * Math.cos(phase) + 0.12 * u)
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
