import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import './auth.css'

export default function LoginPage() {
  const { signInWithPassword, error, setError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signInWithPassword(email.trim(), password)
    } catch {
      // error surfaced via context
    } finally {
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
          Access is restricted to Vinci staff and registered tutors. If you can't
          sign in, contact an administrator to request access.
        </p>
      </div>
    </div>
  )
}
