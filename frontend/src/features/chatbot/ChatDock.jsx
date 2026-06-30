import { ChatIcon, MinimizeIcon } from '../../components/layout/Icons'
import { useDock } from './dockContext'
import ChatPanel from './ChatPanel'
import QuickInputPanel from './QuickInputPanel'
import './chatbot.css'

// Persistent right-hand assistant column. Open = full panel; collapsed = slim
// in-flow rail (still part of the page layout — it never floats over content).
// The conversation stays mounted across collapse so it isn't lost.
export default function ChatDock({ collapsed }) {
  const { setOpen, tab, setTab } = useDock()

  if (collapsed) {
    return (
      <aside className="chatdock chatdock--collapsed">
        <button className="chatdock__expand" onClick={() => setOpen(true)} title="Open assistant">
          <ChatIcon />
          <span className="chatdock__expand-label">Assistant</span>
        </button>
      </aside>
    )
  }

  return (
    <aside className="chatdock">
      <div className="chatdock__inner">
        <header className="chatdock__head">
          <div className="chatdock__title"><span className="chatdock__dot" /> Assistant</div>
          <div className="chatdock__tabs">
            <button className={tab === 'chat' ? 'active' : ''} onClick={() => setTab('chat')}>Chat</button>
            <button className={tab === 'data' ? 'active' : ''} onClick={() => setTab('data')}>Data</button>
          </div>
          <button className="chatdock__min" onClick={() => setOpen(false)} title="Minimize" aria-label="Minimize">
            <MinimizeIcon width={16} height={16} />
          </button>
        </header>

        <div className="chatdock__body">
          <div className="chatdock__pane" style={{ display: tab === 'chat' ? 'flex' : 'none' }}>
            <ChatPanel />
          </div>
          <div className="chatdock__pane chatdock__data" style={{ display: tab === 'data' ? 'block' : 'none' }}>
            <QuickInputPanel />
          </div>
        </div>
      </div>
    </aside>
  )
}
