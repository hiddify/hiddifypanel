import { loadMonaco, type Monaco } from '@/shared/monaco/monaco'

const JINJA_JSON = 'jinja-json'
let languageReady = false

/** Loads Monaco (once) and registers the panel's `jinja-json` language (once). */
export async function ensureMonaco(): Promise<typeof Monaco> {
  const monaco = await loadMonaco()
  if (languageReady) return monaco
  languageReady = true

  monaco.languages.register({ id: JINJA_JSON })
  monaco.languages.setMonarchTokensProvider(JINJA_JSON, {
    defaultToken: 'source',
    tokenizer: {
      root: [
        [/\{%\s*(for|endfor|if|endif|else|elif|set|include|macro|endmacro)\b[^%]*%\}/, 'keyword'],
        [/\{%[\s\S]*?%\}/, 'keyword'],
        [/\{\{[\s\S]*?\}\}/, 'variable'],
        [/"([^"\\]|\\.)*$/, 'string.invalid'],
        [/"/, 'string', '@string'],
        [/\d*\.\d+([eE][-+]?\d+)?/, 'number.float'],
        [/\d+/, 'number'],
        [/[{}[\],:]/, 'delimiter'],
        [/\s+/, 'white'],
        [/[^\s{}[\],:"]+/, 'identifier'],
      ],
      string: [
        [/[^\\"]+/, 'string'],
        [/\\./, 'string.escape'],
        [/"/, 'string', '@pop'],
      ],
    },
  })
  return monaco
}

export const JINJA_JSON_LANGUAGE = JINJA_JSON
