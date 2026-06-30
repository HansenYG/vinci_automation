import { createClient } from '@supabase/supabase-js'

// Browser-side Supabase client.
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

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    // Persist the session and keep it fresh so users stay logged in across
    // reloads (Business Rules s.18 "session persistence").
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    storageKey: 'vinci.auth',
  },
})
