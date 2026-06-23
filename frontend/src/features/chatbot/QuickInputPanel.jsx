import { useEffect, useState } from 'react'
import {
  announceLesson, createCourse, createSchool, createTeacher, exportUrl, getSchools,
} from '../../services/endpoints'

const DATASETS = ['lessons', 'unassigned', 'urgent', 'teachers', 'courses', 'schools']
const TABS = ['lesson', 'teacher', 'course', 'school']

// Admin "input boxes". IDs/codes are generated server-side (following the
// existing data's format), so they're never typed here.
export default function QuickInputPanel() {
  const [tab, setTab] = useState('lesson')
  const [schools, setSchools] = useState([])
  const [msg, setMsg] = useState('')

  const reloadSchools = () => getSchools().then(setSchools).catch(() => setSchools([]))
  useEffect(() => { reloadSchools() }, [])

  const flash = (t) => { setMsg(t); window.clearTimeout(flash._t); flash._t = window.setTimeout(() => setMsg(''), 3000) }

  return (
    <div>
      <div className="card side-card">
        <h3>Quick input</h3>
        <p className="hint">Add data directly, or announce a lesson to tutors. IDs are auto-generated.</p>
        <div className="tabs">
          {TABS.map((t) => (
            <button key={t} className={t === tab ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>
          ))}
        </div>

        {tab === 'lesson' && <LessonAnnounceForm onFlash={flash} />}

        {tab === 'teacher' && (
          <MiniForm
            fields={[['teacher_name', 'Full name', true], ['whatsapp_number', 'WhatsApp (digits)'], ['email', 'Email']]}
            onSubmit={(v) => createTeacher(v)}
            onDone={(r) => flash(r ? `Teacher added: ${r.teacher_id}` : 'Add failed')}
          />
        )}
        {tab === 'course' && (
          <MiniForm
            fields={[['course_name', 'Course name', true], ['course_topic', 'Topic']]}
            select={{ key: 'school_id', label: 'School', options: schools.map((s) => [s.school_id, s.school_name]) }}
            onSubmit={(v) => createCourse(v)}
            onDone={(r) => flash(r ? `Course added: ${r.course_id}` : 'Add failed')}
          />
        )}
        {tab === 'school' && (
          <MiniForm
            fields={[['school_name', 'School name', true]]}
            onSubmit={(v) => createSchool(v)}
            onDone={(r) => { flash(r ? `School added: ${r.school_id}` : 'Add failed'); reloadSchools() }}
          />
        )}
      </div>

      <div className="card side-card">
        <h3>Export to Excel</h3>
        <p className="hint">Download any dataset as .xlsx.</p>
        <div className="export-grid">
          {DATASETS.map((d) => (
            <button key={d} className="btn btn--sm" onClick={() => window.open(exportUrl(d), '_blank')}>{d}</button>
          ))}
        </div>
      </div>

      {msg && <div className="toast">{msg}</div>}
    </div>
  )
}

// --- Lesson tab: create a lesson (code auto-generated) + LLM tutor outreach ---
function LessonAnnounceForm({ onFlash }) {
  const [v, setV] = useState({ date: '', start_time: '', end_time: '', course: '', school: '', max_tutors: '1', lesson_income: '' })
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setResult(null)
    try {
      const body = Object.fromEntries(Object.entries(v).filter(([, val]) => val !== ''))
      const r = await announceLesson(body)
      setResult(r)
      onFlash?.(`${r.lesson_code} · messaged ${r.count}`)
    } catch (e2) {
      setResult({ error: e2?.response?.data?.detail || 'Could not send. Is the backend up?' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="side-form" onSubmit={submit}>
      <span className="mini-label">Date</span>
      <input type="date" value={v.date} onChange={set('date')} required />
      <span className="mini-label">Time</span>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input type="time" value={v.start_time} onChange={set('start_time')} style={{ flex: 1 }} />
        <span className="muted">–</span>
        <input type="time" value={v.end_time} onChange={set('end_time')} style={{ flex: 1 }} />
      </div>
      <span className="mini-label">Course</span>
      <input value={v.course} onChange={set('course')} placeholder="Advanced Robotics Workshop" />
      <span className="mini-label">School</span>
      <input value={v.school} onChange={set('school')} placeholder="Harvard University" />
      <span className="mini-label">Number of tutors</span>
      <input type="number" min="1" value={v.max_tutors} onChange={set('max_tutors')} />
      <span className="mini-label">Lesson income (HKD)</span>
      <input type="number" min="0" step="0.01" value={v.lesson_income} onChange={set('lesson_income')} placeholder="0.00" />

      <button className="btn btn--primary btn--sm" type="submit" disabled={busy || !v.date}>
        {busy ? 'Finding tutors…' : 'Find tutors & send'}
      </button>

      {result && !result.error && (
        <div className="announce-result">
          <strong>{result.lesson_code}</strong> created
          <div className="announce-row">Messaged {result.count} tutor(s) · {result.llm_used ? 'AI-selected' : 'rule-based'}</div>
          {(result.messaged || []).map((m) => (
            <div className="announce-row" key={m.teacher_id}>{m.ok ? '✓' : '✗'} {m.name || m.teacher_id}</div>
          ))}
          {result.count === 0 && <div className="announce-row">No matching tutors found.</div>}
        </div>
      )}
      {result?.error && <div className="announce-result err">{result.error}</div>}
    </form>
  )
}

function MiniForm({ fields, select, onSubmit, onDone }) {
  const [v, setV] = useState({})
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const clean = Object.fromEntries(Object.entries(v).filter(([, val]) => val !== '' && val != null))
      const created = await onSubmit(clean)
      setV({})
      onDone?.(created)
    } catch { onDone?.(null) }
    finally { setBusy(false) }
  }

  const required = fields.find(([, , req]) => req)?.[0]

  return (
    <form className="side-form" onSubmit={submit}>
      {fields.map(([key, label, req]) => (
        <input key={key} placeholder={label + (req ? ' *' : '')} value={v[key] || ''} onChange={set(key)} />
      ))}
      {select && (
        <select value={v[select.key] || ''} onChange={set(select.key)}>
          <option value="">{select.label}…</option>
          {select.options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
        </select>
      )}
      <button className="btn btn--primary btn--sm" type="submit" disabled={busy || (required && !v[required])}>Add</button>
    </form>
  )
}
