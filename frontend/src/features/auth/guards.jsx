import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

function FullScreenLoader({ label = 'Loading…' }) {
  return (
    <div className="auth-shell">
      <div className="auth-loader">
        <span className="auth-spinner" aria-hidden="true" />
        <span>{label}</span>
      </div>
    </div>
  )
}

// Gate that requires a valid, authorized (registered) session.
// - No session            -> redirect to /login (remember intended path)
// - Session but not in app_users -> redirect to /unauthorized
export function RequireAuth({ children }) {
  const { isAuthenticated, isAuthorized, profile, loading, profileLoading } = useAuth()
  const location = useLocation()

  // Still resolving the persisted session, or authenticated but the profile
  // (role) has not resolved yet -> show a loader rather than mis-routing.
  if (loading) return <FullScreenLoader label="Loading…" />
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (profileLoading || profile === null) {
    return <FullScreenLoader label="Checking your access…" />
  }
  if (!isAuthorized) {
    return <Navigate to="/unauthorized" replace />
  }
  return children
}

// Gate that additionally requires one of the given roles.
export function RequireRole({ roles, children }) {
  const { role } = useAuth()
  return (
    <RequireAuth>
      {roles.includes(role) ? children : <Navigate to="/schedule" replace />}
    </RequireAuth>
  )
}

// Redirect already-authenticated users away from the login page.
export function RedirectIfAuthed({ children }) {
  const { isAuthenticated, isAuthorized, profile, loading, profileLoading } = useAuth()
  if (loading) return <FullScreenLoader />
  // Authenticated but role not resolved yet: wait before deciding where to go,
  // otherwise a just-signed-in user is briefly treated as unauthorized.
  if (isAuthenticated && (profileLoading || profile === null)) {
    return <FullScreenLoader label="Signing in…" />
  }
  if (isAuthenticated && isAuthorized) return <Navigate to="/schedule" replace />
  if (isAuthenticated && !isAuthorized) return <Navigate to="/unauthorized" replace />
  return children
}
