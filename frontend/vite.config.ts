import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

/**
 * Vite multi-app build:
 *   pnpm dev:user      → src/user/main.ts  (lms.xiuedu.uz)
 *   pnpm dev:admin     → src/admin/main.ts (lms-admin.xiuedu.uz)
 *
 * Build natijalari:
 *   dist-user/   → lms.xiuedu.uz uchun
 *   dist-admin/  → lms-admin.xiuedu.uz uchun
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isAdmin = mode === 'admin'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@shared': fileURLToPath(new URL('./src/shared', import.meta.url)),
        '@user': fileURLToPath(new URL('./src/user', import.meta.url)),
        '@admin': fileURLToPath(new URL('./src/admin', import.meta.url)),
      },
    },
    root: isAdmin ? './src/admin' : './src/user',
    publicDir: fileURLToPath(new URL('./public', import.meta.url)),
    build: {
      outDir: fileURLToPath(
        new URL(isAdmin ? './dist-admin' : './dist-user', import.meta.url),
      ),
      emptyOutDir: true,
      sourcemap: env.MODE !== 'production',
      // Phase 8c — og'ir vendor kutubxonalarini alohida chunk'larga ajratish.
      // Sabab: bitta vendor.js (>1MB) o'rniga ko'p kichik chunk; brauzer
      // har deploy'da faqat o'zgargan chunk'ni qayta yuklaydi va kesh
      // hit'i yaxshilanadi. Lazy route'lar avtomatik o'zicha chunk bo'ladi.
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-vue': ['vue', 'vue-router', 'pinia', 'vue-i18n'],
            'vendor-livekit': ['livekit-client', '@livekit/track-processors'],
            'vendor-face': ['face-api.js'],
            'vendor-headlessui': ['@headlessui/vue'],
            'vendor-sentry': ['@sentry/vue'],
          },
        },
      },
      // face-api + livekit-client har biri ~600kb gacha bo'lishi mumkin —
      // bu maqbul, har biri o'z chunk'ida (faqat kerakli sahifada yuklanadi).
      chunkSizeWarningLimit: 800,
    },
    server: {
      port: isAdmin ? 8203 : 8201,
      strictPort: false,
      proxy: {
        '/api': {
          target: env.VITE_API_URL?.replace(/\/api\/v1$/, '') ?? 'http://localhost:8200',
          changeOrigin: true,
        },
        '/ws': {
          target: env.VITE_WS_URL ?? 'ws://localhost:8200',
          ws: true,
          changeOrigin: true,
        },
      },
    },
  }
})
