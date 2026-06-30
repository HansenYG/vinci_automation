import axios from 'axios'
import { supabase } from '../lib/supabaseClient'

// Central HTTP client for talking to the FastAPI backend.
// Configure the base URL via VITE_API_BASE_URL in your .env file.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach the current Supabase access token (if any) to every request so the
// FastAPI backend can verify the user and enforce role checks (Business
// Rules v1.2 s.6A). The session is read fresh each call so token refreshes
// performed by supabase-js are picked up automatically.
api.interceptors.request.use(async (config) => {
  try {
    const { data } = await supabase.auth.getSession()
    const token = data?.session?.access_token
    if (token) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${token}`
    }
  } catch {
    // No session / supabase not configured — request proceeds unauthenticated.
  }
  return config
})

export default api
