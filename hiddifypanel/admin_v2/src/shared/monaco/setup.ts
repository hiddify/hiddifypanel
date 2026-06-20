import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker'
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker'
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker'
import * as monaco from 'monaco-editor'

const JINJA_JSON = 'jinja-json'
let languageReady = false

export function setupMonaco(): void {
  if (typeof self !== 'undefined') {
    self.MonacoEnvironment = {
      getWorker(_: unknown, label: string) {
        if (label === 'json') return new jsonWorker()
        if (label === 'css' || label === 'scss' || label === 'less') return new cssWorker()
        if (label === 'html' || label === 'handlebars' || label === 'razor') return new htmlWorker()
        if (label === 'typescript' || label === 'javascript') return new tsWorker()
        return new editorWorker()
      },
    }
  }

  if (languageReady) return
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
}

export const JINJA_JSON_LANGUAGE = JINJA_JSON
