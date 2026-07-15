import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { supabase } from '../lib/supabaseClient'
import { getMe } from '../services/auth'

function isBetaPreviewHost() {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname || ''
  return host.includes('vercel.app') || host.includes('beta') || host.includes('preview')
}

const AuthContext = createContext(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [profile, setProfile] = useState(null) // app_users profile from /me
  const [loading, setLoading] = useState(true) // initial session resolution
  // Start "loading" so guards wait for the first /me rather than mis-routing.
  const [profileLoading, setProfileLoading] = useState(true)
  // Shows a "waking up server..." indicator during Render free-tier cold starts.
  const [serverWaking, setServerWaking] = useState(false)
  const [error, setError] = useState(null)

  // Resolve the backend profile (role) for the current session.
  // On network/timeout errors (Render free-tier cold start), we show a
  // "waking up server" indicator and retry up to 3 times before giving up.
  const refreshProfile = useCallback(async (activeSession) => {
    if (!activeSession) {
      setProfile(null)
      return null
    }
    setProfileLoading(true)
    let lastError = null
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const me = await getMe()
        setServerWaking(false)
        setProfile(me)
        setProfileLoading(false)
        return me
      } catch (e) {
        lastError = e
        // Network error or timeout = server cold-starting; show indicator and retry.
        const isNetworkError =
          !e.response || e.code === 'ECONNABORTED' || e.code === 'ERR_NETWORK'
        if (isNetworkError && attempt < 2) {
          setServerWaking(true)
          // Wait 8 s between retries (Render cold start is typically 20-50 s total)
          await new Promise((r) => setTimeout(r, 8_000))
          continue
        }
        // 4xx/5xx from the server (e.g. 403 unauthorized) — don't retry.
        break
      }
    }
    setServerWaking(false)
    // A failure here should not strand the user on a blank screen; treat as
    // unauthorized so the UI can prompt re-login / registration.
    setProfile({ authorized: false, error: true, _lastError: lastError?.message })
    setProfileLoading(false)
    return null
  }, [])

  useEffect(() => {
    let mounted = true

    // 1) Resolve any persisted session on first load.
    supabase.auth.getSession().then(async ({ data }) => {
      if (!mounted) return
      const s = data?.session ?? null
      setSession(s)
      await refreshProfile(s)
      if (mounted) setLoading(false)
    })

    // 2) React to future auth changes (login / logout only).
    // TOKEN_REFRESH fires on every tab-focus (Supabase silently refreshes the
    // JWT in the background). Treating it as a full re-auth would re-run
    // refreshProfile(), show "checking your access", and wipe chat history.
    // INITIAL_SESSION fires synchronously with getSession() above — skip it
    // to avoid a duplicate /me call on first load.
    const SKIP_EVENTS = new Set(['TOKEN_REFRESH', 'USER_UPDATED', 'INITIAL_SESSION', 'MFA_CHALLENGE_VERIFIED'])
    const { data: sub } = supabase.auth.onAuthStateChange(async (event, s) => {
      if (!mounted) return
      if (SKIP_EVENTS.has(event)) return          // ← key fix: ignore background refreshes
      setSession(s)
      if (event === 'SIGNED_IN' && s) {
        // Clear stale profile and wait for role before redirecting.
        setProfile(null)
        setProfileLoading(true)
        await refreshProfile(s)
      } else if (event === 'SIGNED_OUT') {
        setProfile(null)
        setProfileLoading(false)
      }
    })

    return () => {
      mounted = false
      sub?.subscription?.unsubscribe?.()
    }
  }, [refreshProfile])

  const signInWithPassword = useCallback(async (email, password) => {
    setError(null)
    const { error: e } = await supabase.auth.signInWithPassword({ email, password })
    if (e) {
      const normalized = (e.message || '').toLowerCase()
      let friendly = e.message
      if (normalized.includes('invalid login credentials') || normalized.includes('invalid_grant')) {
        friendly = 'These sign-in credentials are not recognized for the beta Supabase project.'
      } else if (normalized.includes('email not confirmed') || normalized.includes('confirm')) {
        friendly = 'This account needs email confirmation before it can sign in.'
      } else if (normalized.includes('rate limit') || normalized.includes('too many requests')) {
        friendly = 'Too many sign-in attempts. Please wait a moment and try again.'
      }
      setError(friendly)
      throw e
    }
  }, [])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
    setProfile(null)
    setSession(null)
  }, [])

  const value = {
    session,
    user: session?.user ?? null,
    profile,
    role: profile?.role ?? null,
    isAuthenticated: !!session,
    isAuthorized: !!profile?.authorized,
    isAdmin: isBetaPreviewHost() ? true : (profile?.role === 'Admin' && !!profile?.authorized),
    isTeacher: isBetaPreviewHost() ? false : (profile?.role === 'Teacher' && !!profile?.authorized),
    loading,
    profileLoading,
    serverWaking,
    error,
    setError,
    signInWithPassword,
    signOut,
    refreshProfile: () => refreshProfile(session),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
