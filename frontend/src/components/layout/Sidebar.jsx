import { NavLink } from 'react-router-dom'
import { AlertIcon, CalendarIcon, ChatIcon, DashboardIcon, MoneyIcon } from './Icons'
import { useDock } from '../../features/chatbot/dockContext'
import { useAuth } from '../../context/AuthContext'

function Item({ to, label, Icon, phase }) {
  return (
    <NavLink to={to} className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
      <Icon />
      <span>{label}</span>
      {phase && <span className="nav-item__phase">{phase}</span>}
    </NavLink>
  )
}

function initials(name, email) {
  const src = (name || email || '?').trim()
  const parts = src.split(/[\s@.]+/).filter(Boolean)
  const a = parts[0]?.[0] || '?'
  const b = parts[1]?.[0] || ''
  return (a + b).toUpperCase()
}

export default function Sidebar() {
  const { open, setOpen, setTab } = useDock()
  const { profile, user, role, isAdmin, signOut } = useAuth()
  const openAssistant = () => { setTab('chat'); setOpen(true) }

  const displayName = profile?.display_name || user?.email || 'User'
  const email = profile?.email || user?.email || ''

  // Upcoming phases, filtered by role (Finances is Admin-only, s.12).
  const future = [
    { to: '/lessons', label: 'Lesson Dashboard', Icon: DashboardIcon, phase: 'P2' },
    ...(isAdmin ? [{ to: '/finances', label: 'Finances', Icon: MoneyIcon, phase: 'P3' }] : []),
    { to: '/urgent', label: 'Urgent News', Icon: AlertIcon, phase: 'P4' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo">V</span>
        <span>Vinci&nbsp;Automation</span>
      </div>

      <div className="sidebar__section">Phase 1 — Live</div>
      <Item to="/schedule" label="Schedule" Icon={CalendarIcon} />
      <button type="button" className={'nav-item nav-item--btn' + (open ? ' active' : '')} onClick={openAssistant}>
        <ChatIcon />
        <span>Assistant</span>
        <span className="nav-item__phase">{open ? 'open' : 'docked'}</span>
      </button>

      <div className="sidebar__section">Upcoming phases</div>
      {future.map((i) => <Item key={i.to} {...i} />)}

      {/* Signed-in user card + sign out */}
      <div className="sidebar__user">
        <div className="sidebar__avatar" title={email}>{initials(profile?.display_name, email)}</div>
        <div className="sidebar__userinfo">
          <div className="sidebar__username" title={displayName}>{displayName}</div>
          <div className="sidebar__userrole">
            <span className={'role-pill' + (role === 'Admin' ? ' role-pill--admin' : '')}>{role || '—'}</span>
          </div>
        </div>
        <button type="button" className="sidebar__signout" onClick={signOut} title="Sign out" aria-label="Sign out">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </aside>
  )
}
