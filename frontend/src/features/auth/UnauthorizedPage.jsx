import { useAuth } from '../../context/AuthContext'
import './auth.css'

export default function UnauthorizedPage() {
  const { user, profile, signOut } = useAuth()
  const email = user?.email || profile?.email || 'your account'

  return (
    <div className="auth-shell">
      <div className="auth-card auth-card--narrow">
        <div className="auth-brand">
          <span className="auth-logo">V</span>
          <div>
            <div className="auth-brand__name">Vinci Automation</div>
            <div className="auth-brand__sub">Operations Platform</div>
          </div>
        </div>

        <div className="auth-badge auth-badge--warn">Access not granted</div>
        <h1 className="auth-title">You’re signed in, but not registered</h1>
        <p className="auth-lead">
          The account <strong>{email}</strong> isn’t linked to a Vinci staff or
          tutor profile yet, so the platform can’t be opened.
        </p>

        <div className="auth-note">
          <p style={{ margin: 0 }}>To request access:</p>
          <ul>
            <li>Ask a Vinci administrator to register your email, or</li>
            <li>
              If you’re a tutor, confirm the email Vinci has on file matches the
              one you used to sign in.
            </li>
          </ul>
        </div>

        <button type="button" className="auth-submit auth-submit--ghost" onClick={signOut}>
          Sign out and try another account
        </button>
      </div>
    </div>
  )
}
