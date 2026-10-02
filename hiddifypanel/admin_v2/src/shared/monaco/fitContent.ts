import type { Monaco } from '@/shared/monaco/monaco'

/**
 * Grows the editor's container to its content, so the whole text shows and the page
 * scrolls instead of the editor. The container's CSS `min-height` stays the minimum.
 * Returns a disposer.
 */
export function fitEditorToContent(editor: Monaco.editor.IStandaloneCodeEditor, container: HTMLElement): () => void {
  const apply = () => {
    container.style.height = `${Math.ceil(editor.getContentHeight())}px`
  }
  const sub = editor.onDidContentSizeChange((event) => {
    if (event.contentHeightChanged) apply()
  })
  apply()
  return () => sub.dispose()
}
