/**
 * Monaco is not bundled: its prebuilt `min/vs` build (from the monaco-editor package) is
 * copied next to the UI (`<ui>/monaco/<hash>/vs`, see vite.config.ts) and loaded here with
 * Monaco's own AMD loader the first time an editor opens. Bundling Monaco from source
 * roughly doubled the UI build's time and memory (servers build the UI during install).
 *
 * Types still come from the `monaco-editor` package (type-only import, nothing bundled).
 */
import type * as Monaco from 'monaco-editor'

export type { Monaco }

interface AmdRequire {
  (deps: string[], onLoad: (...modules: unknown[]) => void, onError?: (err: unknown) => void): void
  config(options: { paths: Record<string, string> }): void
}

declare global {
  interface Window {
    monaco?: typeof Monaco
  }
}

/**
 * Where the prebuilt Monaco lives: `<ui root>/monaco/vs` in dev (served by the vite plugin). The
 * build copies it under a content-hashed directory and the panel passes the path in
 * `window.__MONACO_BASE__` (see vite.config.ts, panel/admin/v2_view.py).
 */
function vsBaseUrl(): string {
  if (import.meta.env.DEV) {
    return new URL(`${import.meta.env.BASE_URL}monaco/vs`, window.location.origin).href
  }
  if (window.__MONACO_BASE__) return new URL(window.__MONACO_BASE__, window.location.origin).href
  // Fallback for shells rendered by an older panel build: chunks are in `<ui root>/assets/`,
  // resolve from this chunk's own URL so it works under any proxy path.
  const chunk = import.meta.url
  const assets = chunk.lastIndexOf('/assets/')
  const uiRoot = assets >= 0 ? chunk.slice(0, assets + 1) : new URL('./', chunk).href
  return `${uiRoot}monaco/vs`
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Could not load ${src}`))
    document.head.appendChild(script)
  })
}

let loading: Promise<typeof Monaco> | null = null

export function loadMonaco(): Promise<typeof Monaco> {
  if (window.monaco) return Promise.resolve(window.monaco)
  loading ??= (async () => {
    const vs = vsBaseUrl()
    // Workers load through a data: URL so they get the right base URL on any path.
    self.MonacoEnvironment = {
      getWorkerUrl() {
        const source = `self.MonacoEnvironment = { baseUrl: ${JSON.stringify(`${vs}/`)} };\nimportScripts(${JSON.stringify(`${vs}/base/worker/workerMain.js`)});`
        return `data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`
      },
    }
    await loadScript(`${vs}/loader.js`)
    const amdRequire = (window as unknown as { require: AmdRequire }).require
    amdRequire.config({ paths: { vs } })
    await new Promise<void>((resolve, reject) => amdRequire(['vs/editor/editor.main'], () => resolve(), reject))
    if (!window.monaco) throw new Error('Monaco did not load')
    return window.monaco
  })().catch((err) => {
    loading = null // allow a retry (e.g. after a network hiccup)
    throw err
  })
  return loading
}
