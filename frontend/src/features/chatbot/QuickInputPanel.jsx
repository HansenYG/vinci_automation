import { useEffect, useState } from 'react'
import {
  announceLesson, createCourse, createLesson, createSchool, createTeacher,
  exportUrl, getCourses, getSchools,
} from '../../services/endpoints'
import { useLessonsContext as useLessons } from '../../context/LessonsContext'

const DATASETS = ['lessons', 'unassigned', 'urgent', 'teachers', 'courses', 'schools']
const TABS = ['lesson', 'teacher', 'course', 'school']

export default function QuickInputPanel() {
  const [tab, setTab] = useState('lesson')
  const [schools, setSchools] = useState([])
  const [msg, setMsg] = useState('')
  const reloadSchools = () => getSchools().then(setSchools).catch(() => setSchools([]))
  useEffect(() => { reloadSchools() }, [])
  const flash = (t) => { setMsg(t); window.clearTimeout(flash._t); flash._t = window.setTimeout(() => setMsg(''), 3500) }

  return (
    <div>
      <div className="card side-card">
        <h3>Quick input</h3>
        <p className="hint">Add data directly or announce a lesson to tutors. IDs are auto-generated.</p>
        <div className="tabs">
          {TABS.map((t) => (
            <button key={t} className={t === tab ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>
          ))}
        </div>
        {tab === 'lesson' && <LessonForm onFlash={flash} />}
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
            select={{ key: 'school_name', label: 'School', options: schools.map((s) => [s.school_name, s.school_name]) }}
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

// ─── Unified lesson form ─────────────────────────────────────────────────────
// mode "create"   → POST /api/lessons  (saves to DB, no WhatsApp blast)
// mode "announce" → POST /api/scheduling/announce-lesson (creates + sends blasts)
function LessonForm({ onFlash }) {
  const { invalidate } = useLessons()
  const [courses, setCourses] = useState([])
  const [schools, setSchools] = useState([])
  const [mode, setMode] = useState('create')
  const [v, setV] = useState({
    course_id: '', school_id: '', date: '', start_time: '', end_time: '',
    lesson_material_link: '', max_tutors: '1', lesson_income: '',
    course: '', school: '',
  })
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => { getCourses().then(setCourses).catch(() => setCourses([])) }, [])
  useEffect(() => { getSchools().then(setSchools).catch(() => setSchools([])) }, [])

  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setResult(null)
    try {
      if (mode === 'create') {
        const body = Object.fromEntries(
          Object.entries({
            course_id: v.course_id || undefined,
            school_name: v.school || undefined,
            date: v.date,
            start_time: v.start_time || undefined,
            end_time: v.end_time || undefined,
            lesson_material_link: v.lesson_material_link || undefined,
            max_tutors: v.max_tutors ? Number(v.max_tutors) : undefined,
            lesson_income: v.lesson_income ? Number(v.lesson_income) : undefined,
          }).filter(([, val]) => val !== undefined && val !== '')
        )
        const created = await createLesson(body)
        invalidate()
        setResult({ created: true, code: created.lesson_code || created.lesson_id })
        onFlash?.(`Lesson ${created.lesson_code || created.lesson_id} created`)
        setV({ course_id: '', school_id: '', date: '', start_time: '', end_time: '', lesson_material_link: '', max_tutors: '1', lesson_income: '', course: '', school: '' })
      } else {
        const body = Object.fromEntries(
          Object.entries({
            course_id: v.course_id || undefined,
            course: v.course || undefined,
            school: v.school || undefined,
            date: v.date,
            start_time: v.start_time || undefined,
            end_time: v.end_time || undefined,
            max_tutors: v.max_tutors ? Number(v.max_tutors) : undefined,
            lesson_income: v.lesson_income ? Number(v.lesson_income) : undefined,
          }).filter(([, val]) => val !== undefined && val !== '')
        )
        const r = await announceLesson(body)
        invalidate()
        setResult(r)
        onFlash?.(`${r.lesson_code} · messaged ${r.count}`)
      }
    } catch (e2) {
      setResult({ error: e2?.response?.data?.detail || 'Could not save. Is the backend up?' })
    } finally {
      setBusy(false)
    }
  }

  const isAnnounce = mode === 'announce'

  return (
    <form className="side-form" onSubmit={submit}>
      {/* Mode toggle */}
      <div className="tabs" style={{ marginBottom: 10 }}>
        <button type="button" className={mode === 'create' ? 'active' : ''} onClick={() => { setMode('create'); setResult(null) }}>
          Create only
        </button>
        <button type="button" className={mode === 'announce' ? 'active' : ''} onClick={() => { setMode('announce'); setResult(null) }}>
          Create &amp; announce
        </button>
      </div>

      <span className="mini-label">Course</span>
      <select value={v.course_id} onChange={set('course_id')}>
        <option value="">— select course —</option>
        {courses.map((c) => <option key={c.course_id} value={c.course_id}>{c.course_name}</option>)}
      </select>

      <span className="mini-label">School</span>
      <select value={v.school} onChange={set('school')}>
        <option value="">— select school —</option>
        {schools.map((s) => <option key={s.school_id} value={s.school_name}>{s.school_name}</option>)}
      </select>

      {isAnnounce && !v.course_id && (
        <>
          <span className="mini-label">Or type course name</span>
          <input value={v.course} onChange={set('course')} placeholder="Advanced Robotics Workshop" />
        </>
      )}

      <span className="mini-label">Date</span>
      <input type="date" value={v.date} onChange={set('date')} required />

      <span className="mini-label">Time</span>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input type="time" value={v.start_time} onChange={set('start_time')} style={{ flex: 1 }} />
        <span className="muted">–</span>
        <input type="time" value={v.end_time} onChange={set('end_time')} style={{ flex: 1 }} />
      </div>

      {!isAnnounce && (
        <>
          <span className="mini-label">Material link (optional)</span>
          <input value={v.lesson_material_link} onChange={set('lesson_material_link')} placeholder="https://…" />
        </>
      )}

      <span className="mini-label">Number of tutors</span>
      <input type="number" min="1" value={v.max_tutors} onChange={set('max_tutors')} />

      <span className="mini-label">Lesson income (HKD)</span>
      <input type="number" min="0" step="0.01" value={v.lesson_income} onChange={set('lesson_income')} placeholder="0.00" />

      <button className="btn btn--primary btn--sm" type="submit" disabled={busy || !v.date}>
        {busy
          ? (isAnnounce ? 'Finding tutors…' : 'Saving…')
          : (isAnnounce ? 'Find tutors & send' : 'Create lesson')}
      </button>

      {result && !result.error && mode === 'create' && result.created && (
        <div className="announce-result">
          <strong>{result.code}</strong> created successfully
        </div>
      )}
      {result && !result.error && mode === 'announce' && (
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

// ─── Generic mini form ───────────────────────────────────────────────────────
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
