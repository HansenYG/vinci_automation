import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import ChatDock from '../../features/chatbot/ChatDock'
import { DockContext } from '../../features/chatbot/dockContext'

export default function Layout() {
  // Assistant is open by default; remembers the user's choice across reloads.
  const [open, setOpen] = useState(() => localStorage.getItem('vinci.dock') !== 'closed')
  const [tab, setTab] = useState('chat')

  useEffect(() => { localStorage.setItem('vinci.dock', open ? 'open' : 'closed') }, [open])

  return (
    <DockContext.Provider value={{ open, setOpen, tab, setTab }}>
      {/* Assistant is always a real third column (collapses to a slim rail when
          minimized) — it shares the page width, never floats over content. */}
      <div className={'app' + (open ? '' : ' dock-collapsed')}>
        <Sidebar />
        <main className="main">
          <Outlet />
        </main>
        <ChatDock collapsed={!open} />
      </div>
    </DockContext.Provider>
  )
}

// Shared page header used by each page for a consistent top bar.
export function PageHeader({ title, subtitle, actions }) {
  return (
    <header className="topbar">
      <div>
        <h1 className="topbar__title">{title}</h1>
        {subtitle && <p className="topbar__subtitle">{subtitle}</p>}
      </div>
      {actions && <div style={{ display: 'flex', gap: 10 }}>{actions}</div>}
    </header>
  )
}
