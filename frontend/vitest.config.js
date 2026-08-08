import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Separate vitest config so the designer's Tailwind work in vite.config.js
// (server proxy, plugins) is never disturbed.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
  },
})
