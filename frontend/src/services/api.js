import axios from 'axios'
import { supabase } from '../lib/supabaseClient'

// Central HTTP client for talking to the FastAPI backend.
// Prefer the beta backend in hosted preview deployments; otherwise use the
// explicit VITE_API_BASE_URL env or the local dev server.
function resolveApiBaseUrl() {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname || ''
    if (host.includes('vercel.app') || host.includes('beta') || host.includes('preview')) {
      return 'https://vinci-automation-api-beta.onrender.com'
    }
  }
  return import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
}

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  // Render free tier can take up to 50 s to cold-start; give it 70 s before
  // treating a timeout as an auth failure.
  timeout: 70_000,
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

// Retry once on network errors (ECONNRESET, timeout) to handle Render
// free-tier cold starts gracefully without dropping the user to /unauthorized.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config
    // Only retry once, and only for network/timeout errors (not 4xx/5xx).
    if (!config || config._retried) return Promise.reject(error)
    const isNetworkOrTimeout =
      !error.response || error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK'
    if (!isNetworkOrTimeout) return Promise.reject(error)
    config._retried = true
    // Wait 5 s before retrying to give the cold-start server time to wake up.
    await new Promise((r) => setTimeout(r, 5_000))
    return api(config)
  }
)

export default api
