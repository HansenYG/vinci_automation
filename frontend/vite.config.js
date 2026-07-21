import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-only: the strict CSP in index.html blocks the local Supabase/backend
// (127.0.0.1:54321, localhost:8000). Relax connect-src when running `vite dev`;
// the production build keeps the original CSP from index.html unchanged.
const devCsp = {
  name: 'dev-csp',
  apply: 'serve',
  transformIndexHtml(html) {
    return html.replace(
      "connect-src 'self'",
      "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*",
    )
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), devCsp],
})
