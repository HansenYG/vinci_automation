import { useState, useEffect } from 'react'
import {
  announceLesson, createCourse, createLesson, createSchool, createTeacher,
  exportUrl, getCourses, getSchools, createMultiLesson,
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
            onSubmit={(v) => createCourse(v)}
            onDone={(r) => flash(r ? `Course added: ${r.course_id}` : 'Add failed')}
          />
        )}
        {tab === 'school' && (
          <MiniForm
            fields={[['school_name', 'School name', true], ['google_maps_link', 'Google Maps link']]}
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
// mode "multi"    → POST /api/lessons/parse-and-create (batch lesson creation)
function LessonForm({ onFlash }) {
  const { invalidate } = useLessons()
  const [courses, setCourses] = useState([])
  const [schools, setSchools] = useState([])
  const [mode, setMode] = useState('create')
  const [v, setV] = useState({
    course_id: '', school_id: '', date: '', start_time: '00:00', end_time: '00:00',
    lesson_material_link: '', max_tutors: '1', lesson_income: '',
    course: '', school: '',
    // Multi-lesson specific fields
    dates_text: `24/6/2026(星期三)(因中五級進行SBA考試,改期)
29/6/2026(星期一)(因APL交流團,取消)
6/7/2026(星期一)
8/7/2026(星期三)
13/7/2026(星期一)
15/7/2026(星期三)
16/7/2026(星期四)
17/7/2026(星期五)(改為16/7)
20/7/2026(星期一)
21/7/2026(星期二) ( 00:00 -00:00)`,
    default_start_time: '00:00',
    default_end_time: '00:00',
    location: '',
    location_note: 'N404',
  })
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [preview, setPreview] = useState([])

  useEffect(() => { getCourses().then(setCourses).catch(() => setCourses([])) }, [])
  useEffect(() => { getSchools().then(setSchools).catch(() => setSchools([])) }, [])

  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e.target.value }))

  const parsePreview = () => {
    const lines = v.dates_text.split('\n').filter(l => l.trim())
    const datePattern = /(\d{1,2})\/(\d{1,2})\/(\d{4})/
    const timePattern = /(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})/
    const weekdayPattern = /^(星期|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)/i
    
    const parsed = lines.map((line, idx) => {
      const dateMatch = datePattern.exec(line)
      const timeMatch = timePattern.exec(line)
      
      // Extract notes
      const notes = []
      const notePattern = /\(([^)]+)\)/g
      let noteMatch
      while ((noteMatch = notePattern.exec(line)) !== null) {
        const noteContent = noteMatch[1].trim()
        const isTime = timePattern.test(noteContent)
        // Skip weekday patterns (星期一, 星期二, etc., Monday, Tuesday, etc.)
        const isWeekday = weekdayPattern.test(noteContent)
        if (!isTime && !isWeekday && noteContent) {
          notes.push(noteContent)
        }
      }
      
      const isCancelled = notes.some(n => n.includes('取消') || n.toLowerCase().includes('cancel'))
      
      return {
        index: idx,
        line: line.trim(),
        date: dateMatch ? `${dateMatch[1]}/${dateMatch[2]}/${dateMatch[3]}` : 'Invalid date',
        time: timeMatch ? `${timeMatch[1]}:${timeMatch[2]}-${timeMatch[3]}:${timeMatch[4]}` : `${v.default_start_time}-${v.default_end_time}`,
        notes: notes.join(', ') || '-',
        status: isCancelled ? 'Cancelled' : 'Active'
      }
    })
    
    setPreview(parsed)
  }

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setResult(null)
    try {
      if (mode === 'multi') {
        const selectedCourse = courses.find(c => c.course_id === v.course_id)
        const body = {
          course_name: selectedCourse?.course_name || v.course,
          dates_text: v.dates_text,
          default_start_time: v.default_start_time,
          default_end_time: v.default_end_time,
          school_name: v.location || undefined,
          location: v.location_note || undefined,
          lesson_material_link: v.lesson_material_link || undefined,
          max_tutors: parseInt(v.max_tutors) || 1,
          lesson_income: v.lesson_income ? parseFloat(v.lesson_income) : undefined,
        }
        const result = await createMultiLesson(body)
        invalidate()
        setResult({ multi: true, total: result.total, failed: result.failed })
        onFlash?.(`Created ${result.total} lessons${result.failed > 0 ? ` (${result.failed} failed)` : ''}`)
        // Reset multi-specific fields
        setV(prev => ({ ...prev, dates_text: '', preview: [] }))
        setPreview([])
      } else if (mode === 'create') {
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
        setV({ course_id: '', school_id: '', date: '', start_time: '00:00', end_time: '00:00', lesson_material_link: '', max_tutors: '1', lesson_income: '', course: '', school: '' })
      } else {
        const selectedCourse = courses.find((c) => c.course_id === v.course_id)
        const body = Object.fromEntries(
          Object.entries({
            course_id: v.course_id || undefined,
            course: selectedCourse?.course_name || v.course || undefined,
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
  const isMulti = mode === 'multi'

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
        <button type="button" className={mode === 'multi' ? 'active' : ''} onClick={() => { setMode('multi'); setResult(null) }}>
          Multi-lesson
        </button>
      </div>

      {isMulti ? (
        <>
          <span className="mini-label">Course</span>
          <select value={v.course_id} onChange={set('course_id')}>
            <option value="">— select course —</option>
            {courses.map((c) => <option key={c.course_id} value={c.course_id}>{c.course_name}</option>)}
          </select>

          {!v.course_id && (
            <>
              <span className="mini-label">Or type course name</span>
              <input value={v.course} onChange={set('course')} placeholder="ICT Python AI Advanced Course" />
            </>
          )}

          <span className="mini-label">Default time</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="time" value={v.default_start_time} onChange={set('default_start_time')} style={{ flex: 1 }} />
            <span className="muted">–</span>
            <input type="time" value={v.default_end_time} onChange={set('default_end_time')} style={{ flex: 1 }} />
          </div>

          <span className="mini-label">School</span>
          <select value={v.location} onChange={set('location')}>
            <option value="">— select school —</option>
            {schools.map((s) => <option key={s.school_id} value={s.school_name}>{s.school_name}</option>)}
          </select>
          <span className="mini-label">Room (optional)</span>
          <input value={v.location_note} onChange={set('location_note')} placeholder="e.g., N404" />

          <span className="mini-label">Dates & notes</span>
          <textarea
            value={v.dates_text}
            onChange={set('dates_text')}
            placeholder="Enter dates in format: DD/MM/YYYY(Weekday)(optional notes)"
            style={{ minHeight: 120, fontSize: 12, fontFamily: 'monospace', resize: 'vertical' }}
          />

          <button type="button" className="btn btn--sm" onClick={parsePreview} style={{ marginTop: 8, width: '100%' }}>
            Preview parse
          </button>

          {preview.length > 0 && (
            <div style={{ marginTop: 8, background: '#f8fafc', borderRadius: 4, padding: 8, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, color: 'var(--muted)' }}>
                PARSED: {preview.length} lines
              </div>
              {preview.slice(0, 5).map((p, i) => (
                <div key={i} style={{ fontSize: 11, padding: '2px 0', borderBottom: i < Math.min(4, preview.length - 1) ? '1px solid #e2e8f0' : 'none' }}>
                  {p.date} {p.time} · {p.status}
                </div>
              ))}
              {preview.length > 5 && <div style={{ fontSize: 11, color: 'var(--muted)' }}>...and {preview.length - 5} more</div>}
            </div>
          )}

          <span className="mini-label">Material link (optional)</span>
          <input value={v.lesson_material_link} onChange={set('lesson_material_link')} placeholder="https://…" />

          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <span className="mini-label">Tutors</span>
              <input type="number" min="1" value={v.max_tutors} onChange={set('max_tutors')} />
            </div>
            <div style={{ flex: 1 }}>
              <span className="mini-label">Income (HKD)</span>
              <input type="number" min="0" step="0.01" value={v.lesson_income} onChange={set('lesson_income')} placeholder="0.00" />
            </div>
          </div>

          <button className="btn btn--primary btn--sm" type="submit" disabled={busy || (!v.course_id && !v.course)}>
            {busy ? 'Creating…' : 'Create lessons'}
          </button>

          {result && !result.error && result.multi && (
            <div className="announce-result">
              <strong>{result.total}</strong> lessons created
              {result.failed > 0 && <div className="announce-row">{result.failed} failed</div>}
            </div>
          )}
        </>
      ) : (
        <>
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
        </>
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
