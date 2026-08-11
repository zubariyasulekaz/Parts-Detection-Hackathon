import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Without this, Vite silently moves to 5174/5175/... when 5173 is
    // taken - which would only surface as "localhost:5173 doesn't load"
    // right when presenting. Fail loudly instead: free the port or find
    // whatever's holding it, rather than guessing which port it landed on.
    port: 5555,
    strictPort: true,
  },
})
