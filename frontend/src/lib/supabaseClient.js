import { createClient } from '@supabase/supabase-js'

// Browser-side Supabase client.
// Only the public anon key belongs here — never expose the service role key
// on the frontend. Set these values in your .env file.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
