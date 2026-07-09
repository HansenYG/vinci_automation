import { useState, useEffect } from 'react'
import { CloseIcon, PlusIcon } from '../../components/layout/Icons'
import { createMultiLesson, getCourses } from '../../services/endpoints'

const overlayCard = {
  position: 'fixed', inset: 0, background: 'rgba(15,23,42,.35)', zIndex: 50,
  display: 'grid', placeItems: 'center', padding: 16,
}

const fieldStyle = { width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 8, fontSize: 14 }
const textareaStyle = { ...fieldStyle, minHeight: 200, fontFamily: 'monospace', resize: 'vertical' }

export default function MultiLessonModal({ onClose, onCreated }) {
  const [courses, setCourses] = useState([])
  const [form, setForm] = useState({
    course_name: '',
    dates_text: `24/6/2026(星期三)(因中五級進行SBA考試,改期)
29/6/2026(星期一)(因APL交流團,取消)
6/7/2026(星期一)
8/7/2026(星期三)
13/7/2026(星期一)
15/7/2026(星期三)
16/7/2026(星期四)
17/7/2026(星期五)(改為16/7)
20/7/2026(星期一)
21/7/2026(星期二) ( 14:30 -17:30)`,
    default_start_time: '14:30',
    default_end_time: '17:00',
    location: 'N404',
    lesson_material_link: '',
    max_tutors: '1',
    lesson_income: '',
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [preview, setPreview] = useState([])

  useEffect(() => {
    const loadCourses = async () => {
      try {
        const courseList = await getCourses()
        setCourses(courseList)
      } catch (e) {
        console.error('Failed to load courses', e)
      }
    }
    loadCourses()
  }, [])

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const parsePreview = () => {
    const lines = form.dates_text.split('\n').filter(l => l.trim())
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
        time: timeMatch ? `${timeMatch[1]}:${timeMatch[2]}-${timeMatch[3]}:${timeMatch[4]}` : `${form.default_start_time}-${form.default_end_time}`,
        notes: notes.join(', ') || '-',
        status: isCancelled ? 'Cancelled' : 'Active'
      }
    })
    
    setPreview(parsed)
  }

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const body = {
        course_name: form.course_name,
        dates_text: form.dates_text,
        default_start_time: form.default_start_time,
        default_end_time: form.default_end_time,
        location: form.location,
        lesson_material_link: form.lesson_material_link || undefined,
        max_tutors: parseInt(form.max_tutors) || 1,
        lesson_income: form.lesson_income ? parseFloat(form.lesson_income) : undefined,
      }
      const result = await createMultiLesson(body)
      onCreated?.(result)
      onClose()
    } catch (e2) {
      setErr(e2?.response?.data?.detail || 'Could not create lessons.')
    } finally { setBusy(false) }
  }

  return (
    <div style={overlayCard} onClick={onClose}>
      <div className="card" style={{ width: 700, maxWidth: '100%', padding: 22, maxHeight: '90vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Multiple Lessons Entry</h2>
          <button type="button" className="drawer__close" onClick={onClose}><CloseIcon /></button>
        </div>

        <div style={{ marginBottom: 12, fontSize: 13, color: 'var(--muted)', lineHeight: 1.4 }}>
          Enter multiple lessons at once using the semi-structured format. Dates with "取消" or "cancel" will be skipped.
        </div>

        <Row label="Course">
          <select value={form.course_name} onChange={set('course_name')} className="link-input" style={fieldStyle}>
            <option value="">— select course —</option>
            {courses.map((c) => <option key={c.course_id} value={c.course_name}>{c.course_name}</option>)}
          </select>
        </Row>

        <Row label="Default Time">
          <div style={{ display: 'flex', gap: 12 }}>
            <input style={fieldStyle} type="time" value={form.default_start_time} onChange={set('default_start_time')} />
            <span style={{ alignSelf: 'center' }}>to</span>
            <input style={fieldStyle} type="time" value={form.default_end_time} onChange={set('default_end_time')} />
          </div>
        </Row>

        <Row label="Location">
          <input style={fieldStyle} value={form.location} onChange={set('location')} placeholder="e.g., N404" />
        </Row>

        <Row label="Dates & Notes">
          <textarea
            style={textareaStyle}
            value={form.dates_text}
            onChange={set('dates_text')}
            placeholder="Enter dates in format: DD/MM/YYYY(Weekday)(optional notes)"
          />
        </Row>

        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <button type="button" className="btn" onClick={parsePreview} style={{ fontSize: 13 }}>
            Preview Parse
          </button>
          {preview.length > 0 && <span style={{ alignSelf: 'center', fontSize: 13, color: 'var(--muted)' }}>{preview.length} lines parsed</span>}
        </div>

        {preview.length > 0 && (
          <div style={{ marginBottom: 16, background: '#f8fafc', borderRadius: 8, padding: 12, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: 'var(--muted)' }}>PARSED PREVIEW</div>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  <th style={{ textAlign: 'left', padding: 4 }}>Date</th>
                  <th style={{ textAlign: 'left', padding: 4 }}>Time</th>
                  <th style={{ textAlign: 'left', padding: 4 }}>Notes</th>
                  <th style={{ textAlign: 'left', padding: 4 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {preview.map((p, i) => (
                  <tr key={i} style={{ borderBottom: i < preview.length - 1 ? '1px solid #e2e8f0' : 'none' }}>
                    <td style={{ padding: 4 }}>{p.date}</td>
                    <td style={{ padding: 4 }}>{p.time}</td>
                    <td style={{ padding: 4 }}>{p.notes}</td>
                    <td style={{ padding: 4, color: p.status === 'Cancelled' ? '#ef4444' : '#22c55e' }}>{p.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: 16, marginBottom: 12, fontWeight: 600, fontSize: 14, color: 'var(--muted)' }}>Optional Details</div>
        
        <Row label="Material link (optional)"><input style={fieldStyle} value={form.lesson_material_link} onChange={set('lesson_material_link')} placeholder="https://…" /></Row>
        <div style={{ display: 'flex', gap: 12 }}>
          <Row label="Number of tutors"><input style={fieldStyle} type="number" min="1" value={form.max_tutors} onChange={set('max_tutors')} /></Row>
          <Row label="Lesson income (HKD)"><input style={fieldStyle} type="number" min="0" step="0.01" value={form.lesson_income} onChange={set('lesson_income')} placeholder="0.00" /></Row>
        </div>

        {err && <div className="banner" style={{ background: '#fee2e2', color: '#b91c1c', borderColor: '#fecaca' }}>{err}</div>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn--primary" disabled={busy || !form.course_name} onClick={submit}>Create Lessons</button>
        </div>
      </div>
    </div>
  )
}

function Row({ label, children }) {
  return (
    <label className="field" style={{ marginBottom: 12, display: 'block' }}>
      <span className="field__label">{label}</span>
      {children}
    </label>
  )
}