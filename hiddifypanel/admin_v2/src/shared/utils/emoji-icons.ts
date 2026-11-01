/**
 * Emoji in text from the server (setting labels and descriptions, option names, proxy names, notices) shown as
 * PrimeIcons instead: one icon set, the size and colour of the text around it. The strings themselves keep their
 * emoji, since the legacy pages and the Telegram bot use them too.
 */
import { flagCodeOfEmoji, flagUrl } from '@/shared/utils/flags'

type Tone = 'warn' | 'danger' | 'success' | 'info' | 'green' | 'yellow' | 'orange' | 'red' | 'blue' | 'purple' | 'brown' | 'gray' | 'black'

/** emoji (without the U+FE0F variation selector) → icon and, for status marks and coloured dots, a tone */
const ICONS: Record<string, [string, Tone?]> = {
  // notes, warnings, results
  '⚠': ['exclamation-triangle', 'warn'],
  '⛔': ['ban', 'danger'],
  '🚧': ['ban', 'warn'],
  '🔞': ['eye-slash', 'danger'],
  'ℹ': ['info-circle', 'info'],
  '📌': ['thumbtack'],
  '📍': ['map-marker'],
  '✅': ['check-circle', 'success'],
  '✔': ['check', 'success'],
  '☑': ['check-square'],
  '❇': ['check-circle', 'success'],
  '🆗': ['check'],
  '✖': ['times', 'danger'],
  '❌': ['times-circle', 'danger'],
  '✳': ['asterisk'],
  '✴': ['asterisk'],
  '⭐': ['star'],
  '🔝': ['arrow-up'],
  '🎉': ['sparkles'],
  '👋': ['face-smile'],
  '👇': ['arrow-down'],
  // list markers and steps
  '➖': ['minus'],
  '➕': ['plus'],
  '1⃣': ['circle'],
  '2⃣': ['circle'],
  '3⃣': ['circle'],
  '4⃣': ['hashtag'],
  '🔢': ['hashtag'],
  '🥇': ['crown'],
  '🥈': ['crown'],
  '🥉': ['crown'],
  // coloured dots (protocol and status markers)
  '🔴': ['circle-fill', 'red'],
  '🟠': ['circle-fill', 'orange'],
  '🟡': ['circle-fill', 'yellow'],
  '🟢': ['circle-fill', 'green'],
  '🔵': ['circle-fill', 'blue'],
  '🟣': ['circle-fill', 'purple'],
  '🟤': ['circle-fill', 'brown'],
  '⚫': ['circle-fill', 'black'],
  '⚪': ['circle', 'gray'],
  '⭕': ['circle'],
  // security
  '🔐': ['lock'],
  '🔒': ['lock'],
  '🔏': ['lock'],
  '🔑': ['key'],
  '🛡': ['shield'],
  '🆔': ['id-card'],
  '🪪': ['id-card'],
  // network and routing
  '🔀': ['cloud'],
  '➡': ['arrow-right'],
  '⬅': ['arrow-left'],
  '⬆': ['arrow-up'],
  '⬇': ['arrow-down'],
  '↗': ['arrow-up-right'],
  '↘': ['arrow-down-right'],
  '↔': ['arrows-h'],
  '♾': ['arrow-right-arrow-left'],
  '🔁': ['sync'],
  '🔂': ['sync'],
  '🔄': ['refresh'],
  '♻': ['replay'],
  '🔙': ['undo'],
  '➿': ['sitemap'],
  '⛓': ['link'],
  '🔗': ['link'],
  '🌍': ['globe'],
  '🌎': ['globe'],
  '🌏': ['globe'],
  '🌐': ['globe'],
  '🗺': ['map'],
  '📳': ['mobile'],
  '📤': ['upload'],
  '📥': ['download'],
  '🚀': ['gauge'],
  '⚡': ['bolt'],
  '💥': ['bolt'],
  '🆙': ['arrow-circle-up'],
  '🆚': ['arrow-right-arrow-left'],
  '🆎': ['clone'],
  '🈁': ['arrow-right-arrow-left'],
  '📺': ['desktop'],
  '🖥': ['desktop'],
  '🐉': ['shield'],
  '🔰': ['sitemap'],
  '♈': ['sitemap'],
  '♍': ['sitemap'],
  '♒': ['sliders-h'],
  'Ⓜ': ['sitemap'],
  '☣': ['bolt'],
  '☢': ['microchip'],
  '📦': ['box'],
  '🎛': ['sliders-h'],
  '🎚': ['sliders-v'],
  '⏯': ['play-circle'],
  '🔠': ['sort-alpha-down'],
  '📏': ['arrows-h'],
  '🤝': ['users'],
  // time
  '⏳': ['hourglass'],
  '⌛': ['hourglass'],
  '⏱': ['stopwatch'],
  '⏰': ['clock'],
  '🕒': ['clock'],
  '📅': ['calendar'],
  '📆': ['calendar'],
  '🗓': ['calendar'],
  '⏸': ['pause'],
  '▶': ['play'],
  // data and files
  '📈': ['arrow-up-right'],
  '📉': ['arrow-down-right'],
  '📊': ['chart-bar'],
  '📄': ['file'],
  '📑': ['file'],
  '📝': ['file-edit'],
  '✏': ['pencil'],
  '🧾': ['qrcode'],
  '📷': ['qrcode'],
  '💾': ['save'],
  '💿': ['database'],
  '📀': ['database'],
  '🗄': ['database'],
  '🗑': ['trash'],
  '🏷': ['tag'],
  '🔍': ['search'],
  '🔎': ['search'],
  '⚙': ['cog'],
  '🩺': ['wave-pulse'],
  '🎨': ['palette'],
  // people and messages
  '👥': ['users'],
  '👤': ['user'],
  '🧑‍💼': ['user'],
  '👁‍🗨': ['eye'],
  '📧': ['envelope'],
  '📢': ['megaphone'],
  '📣': ['megaphone'],
  '💬': ['comment'],
  '🏠': ['home'],
  '🧠': ['microchip'],
  // not emoji, but written in texts for the drag handle's icon
  '☰': ['bars'],
}

/** One emoji: a flag (two regional indicators), a keycap (1️⃣), or a pictograph with its ZWJ sequence. */
const EMOJI = /☰|\p{Regional_Indicator}{2}|[#*0-9]\uFE0F?\u20E3|(?![©®™])\p{Extended_Pictographic}\uFE0F?(?:\u200D\p{Extended_Pictographic}\uFE0F?)*/gu

export type IconSegment = { text: string } | { icon: string; tone?: Tone } | { flag: string; url: string }

/** The icon of one emoji, or null when it has none (it is then dropped). */
function lookup(emoji: string): IconSegment | null {
  const code = flagCodeOfEmoji(emoji)
  if (code) {
    // 🇺🇳 stands for "other countries": a globe
    const url = code === 'un' ? '' : flagUrl(code)
    return url ? { flag: code, url } : { icon: code === 'un' ? 'pi pi-globe' : 'pi pi-flag' }
  }
  const hit = ICONS[emoji.replace(/\uFE0F/g, '')]
  return hit ? { icon: `pi pi-${hit[0]}`, tone: hit[1] } : null
}

/** Text split into plain parts, icons and flags; spaces next to a dropped emoji are dropped too. */
export function emojiSegments(text: string): IconSegment[] {
  const out: IconSegment[] = []
  let last = 0
  for (const m of text.matchAll(EMOJI)) {
    if (m.index! > last) out.push({ text: text.slice(last, m.index) })
    const seg = lookup(m[0])
    if (seg) out.push(seg)
    last = m.index! + m[0].length
  }
  if (last < text.length) out.push({ text: text.slice(last) })
  return out.map((s) => ('text' in s ? { text: s.text.replace(/ {2,}/g, ' ') } : s)).filter((s) => !('text' in s) || s.text)
}

export function hasEmoji(text: string | null | undefined): boolean {
  return !!text && new RegExp(EMOJI.source, 'u').test(text)
}

/** The text with its emoji removed (for toasts and other places that already show their own icon). */
export function stripEmoji(text: string): string {
  return text.replace(EMOJI, '').replace(/[ \t]{2,}/g, ' ').trim()
}

const escapeAttr = (s: string) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')

/** An HTML string (already sanitized by the server) with each emoji replaced by its icon's markup. */
export function iconizeHtml(html: string | null | undefined): string {
  if (!html || !hasEmoji(html)) return html ?? ''
  return html.replace(EMOJI, (emoji) => {
    const seg = lookup(emoji)
    if (!seg) return ''
    if ('flag' in seg) return `<img class="ui-flag ui-flag--inline" src="${escapeAttr(seg.url)}" alt="" aria-hidden="true">`
    if ('icon' in seg) return `<i class="${seg.icon} ui-emoji-icon${seg.tone ? ` ui-emoji-icon--${seg.tone}` : ''}" aria-hidden="true"></i>`
    return ''
  })
}
