import { NavLink } from 'react-router-dom'
import { AlertIcon, CalendarIcon, ChatIcon, DashboardIcon, MoneyIcon } from './Icons'
import { useDock } from '../../features/chatbot/dockContext'

const future = [
  { to: '/lessons', label: 'Lesson Dashboard', Icon: DashboardIcon, phase: 'P2' },
  { to: '/finances', label: 'Finances', Icon: MoneyIcon, phase: 'P3' },
  { to: '/urgent', label: 'Urgent News', Icon: AlertIcon, phase: 'P4' },
]

function Item({ to, label, Icon, phase }) {
  return (
    <NavLink to={to} className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
      <Icon />
      <span>{label}</span>
      {phase && <span className="nav-item__phase">{phase}</span>}
    </NavLink>
  )
}

export default function Sidebar() {
  const { open, setOpen, setTab } = useDock()
  const openAssistant = () => { setTab('chat'); setOpen(true) }

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

      <div style={{ marginTop: 'auto', fontSize: 11, color: '#6f86a8', padding: '12px 10px' }}>
        Chatbot &amp; Schedule Hub
      </div>
    </aside>
  )
}
