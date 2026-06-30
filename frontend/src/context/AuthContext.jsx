import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { supabase } from '../lib/supabaseClient'
import { getMe } from '../services/auth'

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
  const [error, setError] = useState(null)

  // Resolve the backend profile (role) for the current session.
  const refreshProfile = useCallback(async (activeSession) => {
    if (!activeSession) {
      setProfile(null)
      return null
    }
    setProfileLoading(true)
    try {
      const me = await getMe()
      setProfile(me)
      return me
    } catch (e) {
      // A failure here should not strand the user on a blank screen; treat as
      // unauthorized so the UI can prompt re-login / registration.
      setProfile({ authorized: false, error: true })
      return null
    } finally {
      setProfileLoading(false)
    }
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

    // 2) React to future auth changes (login, logout, token refresh).
    const { data: sub } = supabase.auth.onAuthStateChange(async (event, s) => {
      if (!mounted) return
      setSession(s)
      if (s) {
        // On a brand-new sign-in, clear any stale profile and mark loading so
        // the login redirect waits for the role to resolve.
        if (event === 'SIGNED_IN') {
          setProfile(null)
          setProfileLoading(true)
        }
        await refreshProfile(s)
      } else {
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
      setError(e.message)
      throw e
    }
  }, [])

  const signInWithGoogle = useCallback(async () => {
    setError(null)
    const { error: e } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
    if (e) {
      setError(e.message)
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
    isAdmin: profile?.role === 'Admin' && !!profile?.authorized,
    isTeacher: profile?.role === 'Teacher' && !!profile?.authorized,
    loading,
    profileLoading,
    error,
    setError,
    signInWithPassword,
    signInWithGoogle,
    signOut,
    refreshProfile: () => refreshProfile(session),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
