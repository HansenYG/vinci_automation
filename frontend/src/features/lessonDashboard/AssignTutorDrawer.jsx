import { useEffect, useState } from 'react'
import { assignTutor, blastLesson, getAcceptedPool, getOffers, updateLesson } from '../../services/endpoints'
import { fmtTime } from '../schedule/dates'

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  )
}

function Field({ label, value }) {
  return (
    <div className="field">
      <span className="field__label">{label}</span>
      <span className="field__value">{value ?? '—'}</span>
    </div>
  )
}

const STATUS_LABELS = {
  unassigned: { label: 'Unassigned', color: 'red' },
  offersent: { label: 'Offer Sent', color: 'yellow' },
  hasacceptance: { label: 'Has Acceptance', color: 'yellow' },
  assigned: { label: 'Assigned', color: 'green' },
  completed: { label: 'Completed', color: 'blue' },
  cancelled: { label: 'Cancelled', color: 'grey' },
  rescheduled: { label: 'Rescheduled', color: 'yellow' },
}

export default function AssignTutorDrawer({ lesson, onClose, onChanged }) {
  const [offers, setOffers] = useState([])
  const [accepted, setAccepted] = useState([])
  const [material, setMaterial] = useState('')
  const [income, setIncome] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [msgType, setMsgType] = useState('info') // 'info' | 'error'

  const lessonId = lesson?.id

  useEffect(() => {
    if (!lessonId) return
    setMaterial(lesson.lesson_material_link || '')
    setIncome(lesson.lesson_income ?? '')
    setMsg('')
    getOffers(lessonId).then(setOffers).catch(() => setOffers([]))
    getAcceptedPool(lessonId).then(setAccepted).catch(() => setAccepted([]))
  }, [lessonId]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!lesson) return null

  const assignedCount = offers.filter((o) => o.offer_status === 'assigned').length
  const maxTutors = lesson.max_tutors ?? 1
  const full = assignedCount >= maxTutors
  const statusKey = (lesson.status || '').toLowerCase()
  const statusMeta = STATUS_LABELS[statusKey] || { label: lesson.status, color: 'grey' }

  const flash = (t, type = 'info') => {
    setMsg(t)
    setMsgType(type)
    window.clearTimeout(flash._t)
    flash._t = window.setTimeout(() => setMsg(''), 3000)
  }

  const refresh = () => {
    getOffers(lessonId).then(setOffers).catch(() => {})
    getAcceptedPool(lessonId).then(setAccepted).catch(() => {})
    onChanged?.()
  }

  const run = async (fn, ok) => {
    setBusy(true)
    try {
      const r = await fn()
      flash(ok(r), 'info')
      refresh()
    } catch (e) {
      flash(e?.response?.data?.detail || 'Action failed — check the backend / WATI config.', 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleAssign = (teacherId) => {
    // Check if already assigned to a different teacher — warn
    if (lesson.assigned_teacher_id && lesson.assigned_teacher_id !== teacherId) {
      if (!window.confirm('This lesson already has an assigned tutor. Re-assign to this tutor?')) return
    }
    run(() => assignTutor(lessonId, teacherId, true), () => 'Tutor assigned and confirmation sent.')
  }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="assign-drawer">
        <div className="assign-drawer__head">
          <div>
            <span className={`badge ${statusMeta.color}`}>
              <span className={`dot bg-${statusMeta.color}`} />
              {statusMeta.label}
            </span>
            <h2 style={{ margin: '10px 0 2px', fontSize: 18 }}>{lesson.course_name || 'Lesson'}</h2>
            <div className="muted" style={{ fontSize: 13 }}>
              {lesson.lesson_code} · {lesson.school_name || '—'}
            </div>
          </div>
          <button className="assign-drawer__close" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>

        <div className="assign-drawer__body">
          {/* Lesson details */}
          <div className="field-grid">
            <Field label="Date" value={lesson.lesson_date} />
            <Field label="Time" value={`${fmtTime(lesson.start_time) || '—'} – ${fmtTime(lesson.end_time) || '—'}`} />
            <Field label="Role" value={lesson.role || '—'} />
            <Field label="Tutors" value={`${assignedCount} / ${maxTutors}`} />
            <Field label="Assigned tutor" value={lesson.assigned_teacher_name || 'Unassigned'} />
            <Field label="Within a week" value={lesson.within_a_week ? 'Yes ⚠️' : 'No'} />
            {lesson.lesson_income != null && (
              <Field label="Lesson income (HKD)" value={`$${Number(lesson.lesson_income).toFixed(0)}`} />
            )}
          </div>

          {lesson.notes && (
            <div className="field">
              <span className="field__label">Notes</span>
              <span className="field__value" style={{ fontSize: 13.5, color: 'var(--muted)' }}>{lesson.notes}</span>
            </div>
          )}

          {/* Lesson material link */}
          <div className="field">
            <span className="field__label">Lesson material link</span>
            <div className="link-input">
              <input
                value={material}
                placeholder="https://drive.google.com/…"
                onChange={(e) => setMaterial(e.target.value)}
              />
              <button
                className="btn btn--sm"
                disabled={busy}
                onClick={() =>
                  run(
                    () => updateLesson(lessonId, { lesson_material_link: material }),
                    () => 'Saved.'
                  )
                }
              >
                Save
              </button>
            </div>
            {lesson.lesson_material_link && (
              <a
                className="muted"
                style={{ fontSize: 12.5, marginTop: 4 }}
                href={lesson.lesson_material_link}
                target="_blank"
                rel="noreferrer"
              >
                Open current link ↗
              </a>
            )}
          </div>

          {/* Lesson income */}
          <div className="field">
            <span className="field__label">Lesson income (HKD)</span>
            <div className="link-input">
              <input
                type="number"
                min="0"
                step="0.01"
                value={income}
                placeholder="0.00"
                onChange={(e) => setIncome(e.target.value)}
              />
              <button
                className="btn btn--sm"
                disabled={busy}
                onClick={() =>
                  run(
                    () => updateLesson(lessonId, { lesson_income: income === '' ? null : Number(income) }),
                    () => 'Saved.'
                  )
                }
              >
                Save
              </button>
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              className="btn btn--sm"
              disabled={busy}
              onClick={() => run(() => blastLesson(lessonId), () => 'Offer blast sent.')}
            >
              Send offer blast
            </button>
            {lesson.assigned_teacher_id && (
              <button
                className="btn btn--sm"
                disabled={busy}
                onClick={() => run(() => assignTutor(lessonId, lesson.assigned_teacher_id, true), () => 'Confirmation resent.')}
              >
                Resend confirmation
              </button>
            )}
          </div>

          {/* Accepted tutor pool */}
          {accepted.length > 0 && (
            <div>
              <div className="section-title">Tutors who accepted ({accepted.length})</div>
              <div className="teacher-pool">
                {accepted.map((t) => (
                  <div className="teacher-card" key={t.teacher_id}>
                    <div className="teacher-card__avatar">
                      {(t.teacher_name || '?').slice(0, 2).toUpperCase()}
                    </div>
                    <div className="teacher-card__info">
                      <div className="teacher-card__name">{t.teacher_name || t.teacher_id}</div>
                      <div className="teacher-card__meta">
                        {t.email || '—'} · Rate: HKD {t.tutor_rate ?? '—'}/hr
                      </div>
                    </div>
                    {t.reliability_score != null && (
                      <div className="teacher-card__score">{t.reliability_score.toFixed(0)}</div>
                    )}
                    <button
                      className="teacher-card__assign-btn"
                      disabled={busy || full}
                      onClick={() => handleAssign(t.teacher_id)}
                    >
                      {full ? 'Full' : 'Assign'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {accepted.length === 0 && (
            <div className="muted" style={{ fontSize: 13, textAlign: 'center', padding: '16px 0' }}>
              No tutors have accepted the offer yet.
            </div>
          )}
        </div>

        {/* Toast message */}
        {msg && (
          <div
            className="toast"
            style={{ background: msgType === 'error' ? '#dc2626' : '#111827' }}
          >
            {msg}
          </div>
        )}
      </aside>
    </>
  )
}
