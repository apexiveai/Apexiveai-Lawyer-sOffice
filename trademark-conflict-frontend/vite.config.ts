import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const apiProxyTarget =
    process.env.VITE_API_PROXY_TARGET ??
    env.VITE_API_PROXY_TARGET ??
    'http://127.0.0.1:8081'

  return {
    plugins: [react()],
    server: {
      port: 5189,
      strictPort: true,
      proxy: {
        '/api': apiProxyTarget,
        '/evidence': apiProxyTarget,
        '/health': apiProxyTarget,
      },
    },
    proxy: {
      "/api": {
        target: env.VITE_API_PROXY_TARGET,
        changeOrigin: true,
      },
      "/evidence": {
        target: env.VITE_API_PROXY_TARGET,
        changeOrigin: true,
      },
      "/health": {
        target: env.VITE_API_PROXY_TARGET,
        changeOrigin: true,
      },
    },
  }
})
