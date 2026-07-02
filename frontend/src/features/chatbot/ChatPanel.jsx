import { useEffect, useRef, useState } from 'react'
import { SendIcon } from '../../components/layout/Icons'
import { exportUrl, getPresets, sendChat } from '../../services/endpoints'

const STORAGE_KEY = 'vinci_chat_history'
const MAX_STORED  = 60   // keep last 60 messages in localStorage

const GREETING = {
  role: 'assistant',
  content: "Hi! I'm the Vinci admin assistant. Ask me about lessons (\"show unassigned\", \"urgent within a week\", \"today's schedule\", \"database summary\"), or use a preset below. I can also export data to Excel from the panel on the right.",
  source: 'system',
}

const SOURCE_LABELS = {
  openai: 'AI',
  system: 'System',
  database: 'Database',
  error: 'Error',
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return [GREETING]
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || parsed.length === 0) return [GREETING]
    return parsed
  } catch {
    return [GREETING]
  }
}

function saveHistory(msgs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-MAX_STORED)))
  } catch { /* quota or private mode — ignore */ }
}

export default function ChatPanel() {
  const [messages, setMessages] = useState(loadHistory)
  const [presets, setPresets]   = useState([])
  const [input, setInput]       = useState('')
  const [busy, setBusy]         = useState(false)
  const scrollRef = useRef(null)

  // Persist to localStorage whenever messages change
  useEffect(() => { saveHistory(messages) }, [messages])

  useEffect(() => { getPresets().then(setPresets).catch(() => setPresets([])) }, [])
  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [messages, busy])

  const ask = async (text) => {
    if (!text.trim() || busy) return
    const history = messages.filter((m) => m.source !== 'system').map((m) => ({ role: m.role, content: m.content }))
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setBusy(true)
    try {
      const res = await sendChat(text, history)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply, source: res.source }])
    } catch {
      setMessages((m) => [...m, {
        role: 'assistant',
        content: 'The backend is unreachable right now. Please try again in a moment.',
        source: 'error',
      }])
    } finally { setBusy(false) }
  }

  const onPreset = (p) => {
    if (p.action === 'export') { window.open(exportUrl(p.dataset), '_blank'); return }
    ask(p.prompt)
  }

  const clearHistory = () => {
    localStorage.removeItem(STORAGE_KEY)
    setMessages([GREETING])
  }

  return (
    <div className="chat-window">
      <div className="presets">
        {presets.map((p) => <button key={p.id} className="preset" onClick={() => onPreset(p)}>{p.label}</button>)}
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">
              {m.content}
              {m.role === 'assistant' && m.source && m.source !== 'system' && (
                <div className="bubble__src">{SOURCE_LABELS[m.source] || m.source}</div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="msg assistant"><div className="bubble muted">…thinking</div></div>}
      </div>

      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); ask(input) }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about lessons, tutors, schedule…" />
        <button className="btn btn--primary" type="submit" disabled={busy || !input.trim()}><SendIcon width={16} height={16} /></button>
      </form>

      {/* Clear history link */}
      <div style={{ textAlign: 'right', padding: '4px 12px 8px' }}>
        <button
          onClick={clearHistory}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11.5, color: 'var(--muted)', opacity: 0.6 }}
        >
          Clear chat history
        </button>
      </div>
    </div>
  )
}
