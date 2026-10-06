import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import Components from 'unplugin-vue-components/vite'
import { PrimeVueResolver } from '@primevue/auto-import-resolver'

const adminV2Dir = path.dirname(fileURLToPath(import.meta.url))
const panelSrcDir = path.resolve(adminV2Dir, '../..')
const python = '/opt/hiddify-manager/.venv313/bin/python'

// Monaco is not bundled (see src/shared/monaco/monaco.ts): its prebuilt build is copied
// to `<outDir>/monaco/vs` and served from node_modules in dev.
const monacoMinDir = path.resolve(adminV2Dir, 'node_modules/monaco-editor/min/vs')
const MONACO_URL_MARKER = '/monaco/vs/'

/** Left out of the copy: JSON/CSS/HTML/TypeScript language services (~7 MB, unused) and UI translations. */
function monacoFileWanted(relative: string): boolean {
  const rel = relative.split(path.sep).join('/')
  return !(rel === 'language' || rel.startsWith('language/') || /^nls\.messages\./.test(rel))
}

/**
 * The translation files (hiddifypanel/translations.i18n/*.json) are shared with the classic
 * panel; this UI only reads their `adminV2` section (src/core/i18n). Keep just that part, so
 * the rest (~75% of every locale) is neither bundled into index.js nor processed by the build.
 */
function adminV2TranslationsOnly(): Plugin {
  return {
    name: 'hiddify-admin-v2-translations',
    enforce: 'pre',
    transform(code, id) {
      if (!/[\\/]translations\.i18n[\\/][^\\/]+\.json$/.test(id.split('?', 1)[0]!)) return null
      const data = JSON.parse(code) as { adminV2?: unknown }
      return { code: JSON.stringify({ adminV2: data.adminV2 ?? {} }), map: null }
    },
  }
}

function prebuiltMonaco(): Plugin {
  let outDir = ''
  return {
    name: 'hiddify-prebuilt-monaco',
    configResolved(config) {
      outDir = path.resolve(config.root, config.build.outDir)
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = (req.url ?? '').split('?')[0]!
        const at = url.indexOf(MONACO_URL_MARKER)
        if (at < 0) return next()
        const file = path.resolve(monacoMinDir, decodeURIComponent(url.slice(at + MONACO_URL_MARKER.length)))
        if (!file.startsWith(monacoMinDir + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) return next()
        res.setHeader('Content-Type', file.endsWith('.css') ? 'text/css; charset=utf-8' : 'text/javascript; charset=utf-8')
        fs.createReadStream(file).pipe(res)
      })
    },
    writeBundle() {
      fs.cpSync(monacoMinDir, path.join(outDir, 'monaco', 'vs'), {
        recursive: true,
        filter: (src) => monacoFileWanted(path.relative(monacoMinDir, src)),
      })
    },
  }
}

function normalizeBase(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return '/'
  return trimmed.endsWith('/') ? trimmed : `${trimmed}/`
}

function readProxyPath(env: Record<string, string>): string | undefined {
  const fromEnv = env.VITE_PROXY_PATH?.trim().replace(/^\/+|\/+$/g, '')
  if (fromEnv) return fromEnv

  try {
    const out = execFileSync(python, ['-m', 'hiddifypanel', 'get-setting', 'proxy_path_admin'], {
      cwd: panelSrcDir,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    })
    return out.trim() || undefined
  } catch {
    return undefined
  }
}

function resolveDevBase(env: Record<string, string>): string {
  if (env.VITE_DEV_BASE?.trim()) {
    return normalizeBase(env.VITE_DEV_BASE)
  }
  const proxyPath = readProxyPath(env)
  return proxyPath ? normalizeBase(`/${proxyPath}/admin/v2`) : '/'
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || 'http://127.0.0.1:9001'
  const devPort = Number(env.VITE_DEV_PORT || 9000)
  const devHost = env.VITE_DEV_HOST || '127.0.0.1'
  const devBase = resolveDevBase(env)
  const proxyPath = readProxyPath(env)

  const base = mode === 'production' ? './' : devBase
  if (mode !== 'production' && devBase !== '/') {
    console.log(`[admin-v2] Vite base: ${devBase}`)
  } else if (mode !== 'production') {
    console.warn(
      '[admin-v2] Could not resolve proxy_path — run `python -m hiddifypanel get-setting proxy_path_admin` or set VITE_PROXY_PATH',
    )
  }

  const devDefines =
    proxyPath && mode === 'development'
      ? {
        'import.meta.env.VITE_PROXY_PATH': JSON.stringify(proxyPath),
        'import.meta.env.VITE_API_BASE': JSON.stringify(`/${proxyPath}/api/v2/admin/`),
      }
      : {}

  const flaskProxy = {
    target: apiTarget,
    changeOrigin: false,
    secure: false,
    cookieDomainRewrite: '',
  }

  return {
    base,
    define: devDefines,
    plugins: [
      adminV2TranslationsOnly(),
      prebuiltMonaco(),
      vue(),
      tailwindcss(),
      Components({
        resolvers: [PrimeVueResolver()],
      }),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler',
        },
      },
    },
    server: {
      host: devHost,
      port: devPort,
      allowedHosts: true,
      strictPort: true,
      hmr: devBase !== '/' ? { path: devBase } : undefined,
      proxy: {
        '/__admin_v2_bootstrap': flaskProxy,
        '^/(?![@.])[^/]+/__admin_v2_bootstrap': flaskProxy,
        // Panel API (admin, user, panel, …)
        '^/(?![@.])[^/]+/api': flaskProxy,
        // Legacy admin dashboard — everything under /admin except /admin/v2 (Vite SPA)
        '^/(?![@.])[^/]+/(?!admin/v2(?:/|$))': flaskProxy,
        // Legacy admin static assets
        '^/(?![@.])[^/]+/static': flaskProxy,
      },
    },
    build: {
      outDir: '../static/admin-v2',
      emptyOutDir: true,
      // Servers build this during install: keep peak memory down (see also shared/monaco/monaco.ts).
      reportCompressedSize: false,
      // Content-hashed file names + manifest: no stable `assets/index.js`, so no cache (browser/CDN)
      // can keep serving a stale bundle after an update. `panel/admin/v2_view.py` reads the manifest
      // for the entry file names.
      manifest: true,
      rollupOptions: {
        maxParallelFileOps: 2,
        output: {
          entryFileNames: 'assets/[name]-[hash].js',
          chunkFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash][extname]',
        },
      },
    },
  }
})
