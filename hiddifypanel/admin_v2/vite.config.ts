import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import Components from 'unplugin-vue-components/vite'
import { PrimeVueResolver } from '@primevue/auto-import-resolver'

const adminV2Dir = path.dirname(fileURLToPath(import.meta.url))
const panelSrcDir = path.resolve(adminV2Dir, '../..')
const python = '/opt/hiddify-manager/.venv313/bin/python'

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
      rollupOptions: {
        output: {
          entryFileNames: 'assets/index.js',
          chunkFileNames: 'assets/[name].js',
          assetFileNames: 'assets/[name][extname]',
        },
      },
    },
  }
})
