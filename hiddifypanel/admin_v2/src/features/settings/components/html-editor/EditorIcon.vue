<script setup lang="ts">
/** The HTML editor's toolbar icons (24×24 strokes; primeicons has no text-formatting set). */
/** ``color``: draws the colour bar under the glyph (text colour, highlight). */
const props = defineProps<{ name: EditorIconName; color?: string }>()
</script>

<script lang="ts">
export const PATHS = {
  bold: 'M7 5h6.5a3.5 3.5 0 0 1 0 7H7z M7 12h7.5a3.5 3.5 0 0 1 0 7H7z',
  italic: 'M10 5h8 M6 19h8 M14.5 5l-5 14',
  underline: 'M7 4v7a5 5 0 0 0 10 0V4 M5 20h14',
  strike: 'M4 12h16 M16.5 7C15.8 5.3 14.2 4.5 12 4.5c-2.6 0-4.5 1.3-4.5 3.4 0 1.3.7 2.3 2.2 3 M8 16.6c.7 1.8 2.3 2.9 4.4 2.9 2.6 0 4.6-1.4 4.6-3.6 0-.6-.1-1.1-.4-1.6',
  subscript: 'M4 6l8 10 M12 6l-8 10 M21 20h-4c0-1.6.8-2.2 2-3 .9-.6 2-1.1 2-2.2a1.6 1.6 0 0 0-3-.6',
  superscript: 'M4 8l8 10 M12 8l-8 10 M21 11h-4c0-1.6.8-2.2 2-3 .9-.6 2-1.1 2-2.2a1.6 1.6 0 0 0-3-.6',
  clear: 'M4 7V5h12v2 M10 5L7.5 19 M14 14l6 6 M20 14l-6 6',
  textColor: 'M6 16L12 3l6 13 M8.3 11h7.4',
  highlight: 'M9 9.5l-5 5V17h2.5l5-5 M9 9.5l5.6-5.6a2 2 0 0 1 2.8 0l1.2 1.2a2 2 0 0 1 0 2.8L13 13.5z',
  alignLeft: 'M4 6h16 M4 10h10 M4 14h16 M4 18h10',
  alignCenter: 'M4 6h16 M7 10h10 M4 14h16 M7 18h10',
  alignRight: 'M4 6h16 M10 10h10 M4 14h16 M10 18h10',
  alignJustify: 'M4 6h16 M4 10h16 M4 14h16 M4 18h16',
  listBullet: 'M9 6h11 M9 12h11 M9 18h11 M4.5 6h.01 M4.5 12h.01 M4.5 18h.01',
  listNumber: 'M10 6h10 M10 12h10 M10 18h10 M4 4.5L5 4v4 M4 8h2 M4 14.3a1.1 1.1 0 0 1 2 .5c0 .9-2 1.5-2 2.7h2',
  indent: 'M4 5h16 M11 10h9 M11 14h9 M4 19h16 M4 9l3 3-3 3',
  outdent: 'M4 5h16 M11 10h9 M11 14h9 M4 19h16 M7 9l-3 3 3 3',
  quote: 'M5 17c2.5-1 3.5-3 3.5-5.5V7H4v5h4.5 M15 17c2.5-1 3.5-3 3.5-5.5V7H14v5h4.5',
  link: 'M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1 M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1',
  unlink: 'M15.5 8.5l1.4-1.4a3 3 0 0 0-4.2-4.2l-1.5 1.5 M8.5 15.5l-1.4 1.4a3 3 0 0 1-4.2-4.2l1.5-1.5 M3 3l18 18 M16 18v3 M21 16h-3',
  image: 'M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z M3 16l5-5 4 4 2.5-2.5L21 19 M15.5 8.5h.01',
  table: 'M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z M3 10h18 M3 15h18 M9 10v10 M15 10v10',
  hr: 'M3 12h18 M7 7h10 M7 17h10',
  box: 'M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5z M8 9h8 M8 13h5',
  button: 'M3 9a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z M8 12h8',
  emoji: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M8.5 14s1.3 2 3.5 2 3.5-2 3.5-2 M9 9.5h.01 M15 9.5h.01',
  symbol: 'M5 20h4.5v-2.3a6.5 6.5 0 1 1 5 0V20H19',
  ltr: 'M10 4v10 M14 4v10 M17 4H9.5a3.5 3.5 0 0 0 0 7H10 M4 19h15 M16 16l3 3-3 3',
  rtl: 'M10 4v10 M14 4v10 M17 4H9.5a3.5 3.5 0 0 0 0 7H10 M20 19H5 M8 16l-3 3 3 3',
  undo: 'M9 14L4 9l5-5 M4 9h10.5a5.5 5.5 0 0 1 0 11H11',
  redo: 'M15 14l5-5-5-5 M20 9H9.5a5.5 5.5 0 0 0 0 11H13',
  format: 'M4 6h16 M8 12h12 M8 18h12 M4 12l2 0 M4 18h2',
  wrap: 'M4 6h16 M4 12h13a3 3 0 0 1 0 6h-4 M15 16l-2 2 2 2 M4 18h5',
  code: 'M16 18l6-6-6-6 M8 6l-6 6 6 6',
  eye: 'M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  sparkle: 'M12 3l1.8 4.6L18.5 9.5l-4.7 1.9L12 16l-1.8-4.6L5.5 9.5l4.7-1.9z M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z',
  layers: 'M12 3l9 5-9 5-9-5z M3 13l9 5 9-5',
  template: 'M5 4h14a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z M5 14h5a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1z M15 14h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1z',
  palette: 'M12 3a9 9 0 0 0 0 18c1 0 1.6-.7 1.6-1.5 0-.4-.2-.8-.4-1.1-.3-.3-.4-.6-.4-1 0-.8.7-1.4 1.5-1.4H16a5 5 0 0 0 5-5c0-4.4-4-8-9-8z M7.5 11.5h.01 M10.5 7.5h.01 M15.5 8.5h.01',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z M20 20l-4-4',
  copy: 'M9 9h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V10a1 1 0 0 1 1-1z M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1',
  download: 'M12 4v11 M7 10l5 5 5-5 M4 20h16',
  upload: 'M12 15V4 M7 9l5-5 5 5 M4 20h16',
  broom: 'M14 3l-3.5 8 M6 12h9l1.5 9h-12z M8.5 16v5 M12.5 16v5',
  faq: 'M5 6l3 3-3 3 M11 9h9 M5 16h15 M5 20h9',
  rowAbove: 'M4 13h16v7H4z M4 16.5h16 M12 3v6 M9 6h6',
  rowBelow: 'M4 4h16v7H4z M4 7.5h16 M12 15v6 M9 18h6',
  colBefore: 'M13 4h7v16h-7z M16.5 4v16 M3 12h6 M6 9v6',
  colAfter: 'M4 4h7v16H4z M7.5 4v16 M15 12h6 M18 9v6',
  rowDelete: 'M4 4h16v7H4z M4 7.5h16 M9.5 15.5l5 5 M14.5 15.5l-5 5',
  colDelete: 'M4 4h7v16H4z M7.5 4v16 M15 9.5l5 5 M20 9.5l-5 5',
  tableDelete: 'M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z M9 9l6 6 M15 9l-6 6',
} as const

export type EditorIconName = keyof typeof PATHS
</script>

<template>
  <svg class="editor-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="PATHS[props.name]" />
    <rect v-if="props.color !== undefined" x="4" y="19.5" width="16" height="3" rx="1.5" :fill="props.color || 'currentColor'" stroke="none" />
  </svg>
</template>

<style scoped>
.editor-icon {
  display: block;
  flex: none;
}
</style>
