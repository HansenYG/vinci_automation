import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import './auth.css'

function GoogleGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z" />
    </svg>
  )
}

export default function LoginPage() {
  const { signInWithPassword, signInWithGoogle, error, setError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  // Navigation is handled by RedirectIfAuthed once the profile resolves.
  // Do NOT call navigate() here — it races with the onAuthStateChange handler.
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signInWithPassword(email.trim(), password)
      // signInWithPassword triggers onAuthStateChange → refreshProfile → RedirectIfAuthed navigates
    } catch {
      // error surfaced via context
    } finally {
      setBusy(false)
    }
  }

  const google = async () => {
    setBusy(true)
    try {
      await signInWithGoogle() // redirects away
    } catch {
      setBusy(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="auth-logo">V</span>
          <div>
            <div className="auth-brand__name">Vinci Automation</div>
            <div className="auth-brand__sub">Operations Platform</div>
          </div>
        </div>

        <h1 className="auth-title">Sign in</h1>
        <p className="auth-lead">Use your Vinci account to continue.</p>

        <button type="button" className="auth-google" onClick={google} disabled={busy}>
          <GoogleGlyph />
          <span>Continue with Google</span>
        </button>

        <div className="auth-divider"><span>or</span></div>

        <form onSubmit={submit} className="auth-form">
          <label className="auth-field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@vinciai.academy"
            />
          </label>
          <label className="auth-field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>

          {error && <div className="auth-error" role="alert">{error}</div>}

          <button type="submit" className="auth-submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="auth-foot">
          Access is restricted to Vinci staff and registered tutors. If you can’t
          sign in, contact an administrator to request access.
        </p>
      </div>
    </div>
  )
}
