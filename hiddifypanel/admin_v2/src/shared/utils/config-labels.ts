/** Config labels carry legacy emoji markers ("🔴 Reality"); the new UI shows icons instead. */
export function displayConfigLabel(label: string): string {
  return label.replace(/^[\p{Extended_Pictographic}\p{Emoji_Presentation}️‍\s]+/u, '').trim() || label
}

/** Text content of a (sanitized) HTML description, for search. */
export function htmlToText(html: string): string {
  const el = document.createElement('div')
  el.innerHTML = html
  return el.textContent ?? ''
}
