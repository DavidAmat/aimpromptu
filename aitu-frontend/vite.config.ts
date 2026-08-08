import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // `@aimpromptu/grid-notation` is a `file:` dependency — a symlink into the
    // sibling `vexflow-v2` checkout. Vite pre-bundles linked dependencies and
    // caches the result, so a rebuild over there would otherwise not show up
    // here until the dev server was restarted.
    exclude: ['@aimpromptu/grid-notation'],
  },
})
