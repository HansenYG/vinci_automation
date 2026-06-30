// Auth-related backend calls. Identity is owned by Supabase Auth; the backend
// resolves the session into a role + profile via /api/auth/me.
import api from './api'

const data = (p) => p.then((r) => r.data)

// Returns the caller's profile:
//   { user_id, email, role, is_vinci_email, teacher_id, display_name, authorized }
// `authorized: false` means a valid login with no app_users row -> show the
// "Unauthorized, request registration" page (Business Rules s.18).
export const getMe = () => data(api.get('/api/auth/me'))
