import { useEffect, useState } from 'react'
import { CloseIcon } from '../../components/layout/Icons'
import { createLesson, getCourses } from '../../services/endpoints'

const overlayCard = {
  position: 'fixed', inset: 0, background: 'rgba(15,23,42,.35)', zIndex: 50,
  display: 'grid', placeItems: 'center', padding: 16,
}

export default function NewLessonModal({ onClose, onCreated }) {
  const [courses, setCourses] = useState([])
  const [form, setForm] = useState({
    course_id: '', date: '', start_time: '', end_time: '', lesson_material_link: '', max_tutors: '1', lesson_income: '',
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => { getCourses().then(setCourses).catch(() => setCourses([])) }, [])

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const body = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''))
      const created = await createLesson(body)
      onCreated?.(created)
      onClose()
    } catch (e2) {
      setErr(e2?.response?.data?.detail || 'Could not create lesson.')
    } finally { setBusy(false) }
  }

  return (
    <div style={overlayCard} onClick={onClose}>
      <form className="card" style={{ width: 460, maxWidth: '100%', padding: 22 }} onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>New lesson</h2>
          <button type="button" className="drawer__close" onClick={onClose}><CloseIcon /></button>
        </div>

        <Row label="Course">
          <select value={form.course_id} onChange={set('course_id')} className="link-input" style={fieldStyle}>
            <option value="">— select course —</option>
            {courses.map((c) => <option key={c.course_id} value={c.course_id}>{c.course_name}</option>)}
          </select>
        </Row>
        <Row label="Date"><input style={fieldStyle} type="date" value={form.date} onChange={set('date')} required /></Row>
        <div style={{ display: 'flex', gap: 12 }}>
          <Row label="Start"><input style={fieldStyle} type="time" value={form.start_time} onChange={set('start_time')} /></Row>
          <Row label="End"><input style={fieldStyle} type="time" value={form.end_time} onChange={set('end_time')} /></Row>
        </div>
        <Row label="Material link (optional)"><input style={fieldStyle} value={form.lesson_material_link} onChange={set('lesson_material_link')} placeholder="https://…" /></Row>
        <div style={{ marginTop: 16, marginBottom: 12, fontWeight: 600, fontSize: 14, color: 'var(--muted)' }}>Data</div>
        <Row label="Number of tutors"><input style={fieldStyle} type="number" min="1" value={form.max_tutors} onChange={set('max_tutors')} /></Row>
        <Row label="Lesson income (HKD)"><input style={fieldStyle} type="number" min="0" step="0.01" value={form.lesson_income} onChange={set('lesson_income')} placeholder="0.00" /></Row>

        {err && <div className="banner" style={{ background: '#fee2e2', color: '#b91c1c', borderColor: '#fecaca' }}>{err}</div>}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn--primary" disabled={busy || !form.date}>Create lesson</button>
        </div>
      </form>
    </div>
  )
}

const fieldStyle = { width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 8, fontSize: 14 }

function Row({ label, children }) {
  return (
    <label className="field" style={{ marginBottom: 12, flex: 1 }}>
      <span className="field__label">{label}</span>
      {children}
    </label>
  )
}
