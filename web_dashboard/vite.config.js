import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load .env, .env.local, .env.production, etc. from web_dashboard/
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],

    // ─── Dev server ──────────────────────────────────────────────────────────
    server: {
      port: 5174,
      // Proxy /api calls to the local backend during development.
      // The proxy strips the /api prefix before forwarding.
      // Production builds call the backend directly via VITE_API_URL.
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },

    // ─── Production build output ─────────────────────────────────────────────
    build: {
      outDir: 'dist',
      // Generate a sourcemap for error tracking (Sentry etc.)
      // Set to false to reduce bundle size if you don't use error tracking.
      sourcemap: mode !== 'production',
      rollupOptions: {
        output: {
          // Chunk splitting: vendor libs in a separate chunk for better caching
          manualChunks: {
            vendor: ['react', 'react-dom'],
          },
        },
      },
    },

    // ─── Environment variable exposure ───────────────────────────────────────
    // Only variables prefixed with VITE_ are exposed to the browser bundle.
    // VITE_API_URL: the backend base URL for production builds.
    //   Local dev: leave unset (uses proxy above)
    //   Production: set in web_dashboard/.env.production or hosting provider
    //     VITE_API_URL=https://api.labelsure.app
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version || '1.0.0'),
    },
  }
})
