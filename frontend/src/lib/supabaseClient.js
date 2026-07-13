import { createBrowserClient } from '@supabase/ssr'

// Browser-side Supabase client.
// Uses cookie-based auth via @supabase/ssr instead of localStorage
// to mitigate JWT token exfiltration via XSS.
// Only the public anon key belongs here — never expose the service role key
// on the frontend. Set these values in your .env file.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  // Surface misconfiguration early rather than failing with a cryptic error.
  // eslint-disable-next-line no-console
  console.error(
    'Supabase is not configured: set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.'
  )
}

export const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    // Use cookie-based persistence instead of localStorage.
    // Cookies with proper flags (Secure, SameSite=Lax) reduce XSS risk.
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    storageKey: 'vinci.auth',
  },
  cookieOptions: {
    name: 'vinci-auth-token',
    secure: true,
    sameSite: 'lax',
    path: '/',
    // httpOnly cannot be set from the browser — requires a custom backend endpoint.
    // For full httpOnly cookie protection, implement a token-exchange endpoint
    // on the FastAPI backend that sets httpOnly cookies server-side.
  },
})
