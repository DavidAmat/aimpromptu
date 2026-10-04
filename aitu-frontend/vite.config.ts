import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Where `/api` goes. Natively the backend is on this machine; in the container it is the
// `backend` service of compose.yaml, which sets AITU_API_PROXY.
const apiTarget = process.env.AITU_API_PROXY ?? 'http://127.0.0.1:8765'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // One port for everything (implementation 08, plan section 10.4). The browser calls `/api/...`
    // on the page's own address, and Vite passes it to the backend without the prefix. The JSON,
    // the audio files (with their range requests, for seeking) and the progress stream all take
    // this path, so the Mac needs one SSH tunnel, to 5173, and nothing else. The gzip answers of
    // the backend pass through unchanged.
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  optimizeDeps: {
    // `@aimpromptu/grid-notation` is a `file:` dependency — a symlink into the
    // sibling `vexflow-v2` checkout. Vite pre-bundles linked dependencies and
    // caches the result, so a rebuild over there would otherwise not show up
    // here until the dev server was restarted.
    exclude: ['@aimpromptu/grid-notation'],
  },
})
