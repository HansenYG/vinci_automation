import { useCallback, useEffect, useRef, useState } from 'react'
import { SendIcon } from '../../components/layout/Icons'
import { executeAction, exportUrl, getCourses, getPresets, getSchools, sendChat } from '../../services/endpoints'

const STORAGE_KEY = 'vinci_chat_history'
const MAX_STORED  = 60

const GREETING = {
  role: 'assistant',
  content: "Hi! I'm the Vinci admin assistant. Ask me about lessons or modify data using natural language. Try \"show unassigned\", \"today's schedule\", or \"database summary\", or use a preset below. I can also export data to Excel from the panel on the right.",
  source: 'system',
}

const SOURCE_LABELS = {
  openai: 'AI',
  system: 'System',
  database: 'Database',
  error: 'Error',
}

const COMMANDS = [
  {
    name: 'reschedule',
    desc: "Change a lesson's date/time",
    fields: [
      { key: 'lesson_id', label: 'Lesson ID', placeholder: 'e.g. L-2026-010' },
      { key: 'date', label: 'New date', placeholder: 'YYYY-MM-DD', type: 'date' },
      { key: 'start_time', label: 'Start time', placeholder: 'HH:MM', type: 'time' },
      { key: 'end_time', label: 'End time', placeholder: 'HH:MM', type: 'time' },
    ],
    build: (vals) => {
      const parts = [`Reschedule lesson ${vals.lesson_id}`]
      if (vals.date) parts.push(`to ${vals.date}`)
      if (vals.start_time) parts.push(`at ${vals.start_time}`)
      if (vals.end_time) parts.push(`ending ${vals.end_time}`)
      return parts.join(' ')
    },
  },
  {
    name: 'update',
    desc: 'Change lesson fields (status, course, notes, time…)',
    fields: [
      { key: 'lesson_id', label: 'Lesson ID', placeholder: 'e.g. L-2026-010', required: true },
      { key: 'date', label: 'Date', placeholder: 'YYYY-MM-DD', type: 'date' },
      { key: 'start_time', label: 'Start time', placeholder: 'HH:MM', type: 'time' },
      { key: 'end_time', label: 'End time', placeholder: 'HH:MM', type: 'time' },
      { key: 'course', label: 'Course', placeholder: 'e.g. Advanced Robotics Workshop' },
      { key: 'status', label: 'Status', placeholder: 'e.g. Cancelled, Completed, Rescheduled' },
      { key: 'role', label: 'Role', placeholder: 'Tutor or Teaching Assistant' },
      { key: 'max_tutors', label: 'Max tutors', placeholder: 'e.g. 2' },
      { key: 'notes', label: 'Notes', placeholder: 'e.g. Parent requested afternoon' },
      { key: 'lesson_material_link', label: 'Material link', placeholder: 'e.g. https://…' },
    ],
    build: (vals) => {
      const parts = []
      for (const f of COMMANDS.find(c => c.name === 'update').fields) {
        if (f.key === 'lesson_id') continue
        if (vals[f.key]?.trim()) parts.push(`${f.key}=${vals[f.key].trim()}`)
      }
      return `Update lesson ${vals.lesson_id.trim()}: ${parts.join(', ')}`
    },
  },
  {
    name: 'create',
    desc: 'Create a new lesson',
    fields: [
      { key: 'course_name', label: 'Course', placeholder: '— select course —', type: 'select', optionsKey: 'courses', optionValue: 'course_id', optionLabel: 'course_name', addAny: true },
      { key: 'school_name', label: 'School', placeholder: '— select school —', type: 'select', optionsKey: 'schools', optionValue: 'school_name', optionLabel: 'school_name', addAny: true },
      { key: 'date', label: 'Date', placeholder: 'YYYY-MM-DD', type: 'date' },
      { key: 'start', label: 'Start time', placeholder: 'HH:MM', type: 'time' },
      { key: 'end', label: 'End time', placeholder: 'HH:MM', type: 'time' },
    ],
    build: (vals) => {
      const course = vals.course_name || vals.course_name_typed
      return `Create a ${course} lesson at ${vals.school_name} on ${vals.date} at ${vals.start}-${vals.end}`
    },
  },
  {
    name: 'delete',
    desc: 'Delete a lesson',
    fields: [
      { key: 'lesson_id', label: 'Lesson ID', placeholder: 'e.g. L-2026-010' },
    ],
    build: (vals) => `Delete lesson ${vals.lesson_id}`,
  },
]

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
  } catch {}
}

const EMPTY_VALS = {}
COMMANDS.forEach((c) => { EMPTY_VALS[c.name] = {}; c.fields.forEach((f) => { EMPTY_VALS[c.name][f.key] = f.type === 'time' ? '00:00' : '' }) })

export default function ChatPanel() {
  const [messages, setMessages] = useState(loadHistory)
  const [presets, setPresets]   = useState([])
  const [courses, setCourses]   = useState([])
  const [schools, setSchools]   = useState([])
  const [input, setInput]       = useState('')
  const [busy, setBusy]         = useState(false)
  const [executing, setExecuting] = useState(false)
  const [showCommands, setShowCommands] = useState(false)
  const [activeCmd, setActiveCmd] = useState(null)
  const [cmdVals, setCmdVals] = useState({})
  const scrollRef = useRef(null)

  const resetCmd = useCallback((name) => {
    setCmdVals((prev) => ({ ...prev, [name]: { ...EMPTY_VALS[name] } }))
  }, [])

  const toggleCmd = (cmd) => {
    if (activeCmd === cmd) {
      setActiveCmd(null)
    } else {
      setActiveCmd(cmd)
      if (!cmdVals[cmd]) resetCmd(cmd)
    }
  }

  const setVal = (cmd, key, val) => {
    setCmdVals((prev) => ({ ...prev, [cmd]: { ...prev[cmd], [key]: val } }))
  }

  const submitCmd = (cmd) => {
    const vals = cmdVals[cmd.name] || {}
    const missing = cmd.fields.find((f) => f.required && !vals[f.key]?.trim())
    if (missing) return
    const text = cmd.build(vals)
    setActiveCmd(null)
    ask(text)
  }

  // Persist to localStorage whenever messages change
  useEffect(() => { saveHistory(messages) }, [messages])

  useEffect(() => { getPresets().then(setPresets).catch(() => setPresets([])) }, [])
  useEffect(() => { getCourses().then(setCourses).catch(() => setCourses([])) }, [])
  useEffect(() => { getSchools().then(setSchools).catch(() => setSchools([])) }, [])
  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [messages, busy])

  const ask = async (text) => {
    if (!text.trim() || busy) return
    const history = messages.filter((m) => m.source !== 'system').map((m) => ({ role: m.role, content: m.content }))
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setBusy(true)
    try {
      const res = await sendChat(text, history)
      const entry = { role: 'assistant', content: res.reply, source: res.source }
      if (res.pendingAction) {
        entry.pendingAction = res.pendingAction
      }
      setMessages((m) => [...m, entry])
    } catch {
      setMessages((m) => [...m, {
        role: 'assistant',
        content: 'The backend is unreachable right now. Please try again in a moment.',
        source: 'error',
      }])
    } finally { setBusy(false) }
  }

  const confirmAction = async (msgIndex, action) => {
    setExecuting(true)
    try {
      const result = await executeAction(action.operation, action.params)
      const ok = result.ok !== false
      setMessages((m) => {
        const updated = [...m]
        // Remove the pending action indicator
        updated[msgIndex] = { ...updated[msgIndex], pendingAction: undefined }
        // Insert result message right after
        const resultMsg = {
          role: 'assistant',
          content: ok ? `✅ Done. ${result.message || ''}` : `❌ ${result.error || 'Action failed.'}`,
          source: 'system',
        }
        updated.splice(msgIndex + 1, 0, resultMsg)
        return updated
      })
    } catch {
      setMessages((m) => {
        const updated = [...m]
        updated[msgIndex] = { ...updated[msgIndex], pendingAction: undefined }
        updated.splice(msgIndex + 1, 0, {
          role: 'assistant',
          content: '❌ Failed to execute the action. Please try again.',
          source: 'error',
        })
        return updated
      })
    } finally { setExecuting(false) }
  }

  const cancelAction = (msgIndex) => {
    setMessages((m) => {
      const updated = [...m]
      updated[msgIndex] = { ...updated[msgIndex], pendingAction: undefined }
      updated.splice(msgIndex + 1, 0, {
        role: 'assistant',
        content: 'Action cancelled.',
        source: 'system',
      })
      return updated
    })
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

      <div className="chat-commands-toggle">
        <button className={`cmd-toggle ${showCommands ? 'cmd-toggle--open' : ''}`} onClick={() => setShowCommands(!showCommands)}>
          {showCommands ? '▲' : '▼'} Commands
        </button>
        {showCommands && (
          <div className="chat-commands">
            {COMMANDS.map((cmd) => (
              <div key={cmd.name} className={`cmd-card ${activeCmd === cmd.name ? 'cmd-card--open' : ''}`}>
                <button className="cmd-card__head" onClick={() => toggleCmd(cmd.name)}>
                  <span className="cmd-card__name">{cmd.name}</span>
                  <span className="cmd-card__desc">{cmd.desc}</span>
                  <span className="cmd-card__chevron">{activeCmd === cmd.name ? '▲' : '▼'}</span>
                </button>
                {activeCmd === cmd.name && (
                  <div className="cmd-card__form">
                    {cmd.fields.map((f) => {
                      if (f.type === 'select') {
                        const opts = f.optionsKey === 'courses' ? courses : f.optionsKey === 'schools' ? schools : []
                        const val = (cmdVals[cmd.name] || {})[f.key] || ''
                        return (
                          <div key={f.key} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <select className="cmd-card__input"
                              value={val}
                              onChange={(e) => setVal(cmd.name, f.key, e.target.value)}>
                              <option value="">{f.placeholder}</option>
                              {opts.map((o) => (
                                <option key={o[f.optionValue]} value={o[f.optionLabel]}>{o[f.optionLabel]}</option>
                              ))}
                            </select>
                            {f.addAny && !val && (
                              <input className="cmd-card__input" type="text"
                                value={(cmdVals[cmd.name] || {})[f.key + '_typed'] || ''}
                                onChange={(e) => setVal(cmd.name, f.key + '_typed', e.target.value)}
                                placeholder={`Or type new ${f.label.toLowerCase()}`} />
                            )}
                          </div>
                        )
                      }
                      return (
                        <input key={f.key} className="cmd-card__input"
                          type={f.type === 'date' ? 'date' : f.type === 'time' ? 'time' : 'text'}
                          value={(cmdVals[cmd.name] || {})[f.key] || ''}
                          onChange={(e) => setVal(cmd.name, f.key, e.target.value)}
                          placeholder={f.placeholder} />
                      )
                    })}
                    <button className="btn btn--primary btn--sm cmd-card__send"
                      onClick={() => submitCmd(cmd)}
                      disabled={!cmd.fields.every((f) => !f.required || (cmdVals[cmd.name] || {})[f.key]?.trim())}>
                      Send
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">
              {m.content}
              {m.role === 'assistant' && m.source && m.source !== 'system' && (
                <div className="bubble__src">{SOURCE_LABELS[m.source] || m.source}</div>
              )}
              {m.pendingAction && (
                <div className="confirm-actions">
                  <button className="btn btn--primary btn--sm" onClick={() => confirmAction(i, m.pendingAction)} disabled={executing}>
                    {executing ? 'Working…' : 'Yes, proceed'}
                  </button>
                  <button className="btn btn--sm" onClick={() => cancelAction(i)} disabled={executing}>
                    Cancel
                  </button>
                </div>
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
