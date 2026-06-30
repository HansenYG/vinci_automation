/**
 * LessonDetailDrawer — unified lesson detail + assign-tutor drawer.
 *
 * Used by BOTH the Schedule Calendar and the Lesson Dashboard.
 * After any mutation it calls:
 *   1. onChanged()  — so the parent view refreshes its own data
 *   2. invalidate() — so the OTHER view (via LessonsContext) also refreshes
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CloseIcon, SendIcon } from '../../components/layout/Icons'
import {
  assignTutor, blastLesson, getAcceptedPool, getOffers, resendConfirmation, updateLesson,
} from '../../services/endpoints'
import { useLessonsContext } from '../../context/LessonsContext'
import { fmtTime } from './dates'

// ── Status helpers ────────────────────────────────────────────────────────────
const STATUS_META = {
  unassigned:    { label: 'Unassigned',     color: 'red' },
  offersent:     { label: 'Offer Sent',     color: 'yellow' },
  hasacceptance: { label: 'Has Acceptance', color: 'yellow' },
  assigned:      { label: 'Assigned',       color: 'green' },
  completed:     { label: 'Completed',      color: 'blue' },
  cancelled:     { label: 'Cancelled',      color: 'grey' },
  rescheduled:   { label: 'Rescheduled',    color: 'yellow' },
}
function getStatusMeta(status) {
  const key = (status || '').toLowerCase()
  return STATUS_META[key] || { label: status || '—', color: 'grey' }
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function LessonDetailDrawer({ lesson, onClose, onChanged, sourceView = 'schedule' }) {
  const [offers, setOffers]     = useState([])
  const [accepted, setAccepted] = useState([])
  const [material, setMaterial] = useState('')
  const [income, setIncome]     = useState('')
  const [busy, setBusy]         = useState(false)
  const [msg, setMsg]           = useState('')
  const [msgType, setMsgType]   = useState('info')

  const { invalidate } = useLessonsContext()
  const navigate = useNavigate()

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
  const maxTutors     = lesson.max_tutors ?? 1
  const full          = assignedCount >= maxTutors
  const statusMeta    = getStatusMeta(lesson.status || lesson.color)

  // ── Helpers ────────────────────────────────────────────────────────────────
  const flash = (t, type = 'info') => {
    setMsg(t); setMsgType(type)
    window.clearTimeout(flash._t)
    flash._t = window.setTimeout(() => setMsg(''), 3000)
  }

  const refresh = () => {
    getOffers(lessonId).then(setOffers).catch(() => {})
    getAcceptedPool(lessonId).then(setAccepted).catch(() => {})
    // Notify both the parent view AND the other view via context
    onChanged?.()
    invalidate()
  }

  const run = async (fn, ok) => {
    setBusy(true)
    try   { const r = await fn(); flash(ok(r), 'info'); refresh() }
    catch (e) { flash(e?.response?.data?.detail || 'Action failed — check the backend / WATI config.', 'error') }
    finally   { setBusy(false) }
  }

  const handleAssign = (teacherId) => {
    if (lesson.assigned_teacher_id && lesson.assigned_teacher_id !== teacherId) {
      if (!window.confirm('This lesson already has an assigned tutor. Re-assign to this tutor?')) return
    }
    run(() => assignTutor(lessonId, teacherId, true), () => 'Tutor assigned and confirmation sent.')
  }

  // Cross-view navigation link
  const crossLink = sourceView === 'schedule'
    ? { label: 'View in Dashboard →', path: '/lessons' }
    : { label: '← View in Calendar', path: '/schedule' }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer">
        {/* Header */}
        <div className="drawer__head">
          <div>
            <span className={`badge ${statusMeta.color}`}>
              <span className={`dot bg-${statusMeta.color}`} />
              {statusMeta.label}
            </span>
            <h2 style={{ margin: '10px 0 2px', fontSize: 19 }}>{lesson.course_name || 'Lesson'}</h2>
            <div className="muted" style={{ fontSize: 13 }}>
              {lesson.lesson_code}
              {lesson.school_name ? ` · ${lesson.school_name}` : ''}
            </div>
            {/* Cross-view navigation */}
            <button
              className="btn btn--ghost"
              style={{ fontSize: 12, marginTop: 6, padding: '2px 0', opacity: 0.7 }}
              onClick={() => { onClose(); navigate(crossLink.path) }}
            >
              {crossLink.label}
            </button>
          </div>
          <button className="drawer__close" onClick={onClose}><CloseIcon /></button>
        </div>

        <div className="drawer__body">
          {/* Core fields */}
          <div className="field-grid">
            <Field label="School"         value={lesson.school_name || '—'} />
            <Field label="Date"           value={lesson.lesson_date} />
            <Field label="Start"          value={fmtTime(lesson.start_time) || '—'} />
            <Field label="End"            value={fmtTime(lesson.end_time) || '—'} />
            <Field label="Assigned tutor" value={lesson.assigned_teacher_name || 'Unassigned'} />
            <Field label="Tutors"         value={`${assignedCount} / ${maxTutors}`} />
            <Field label="Lesson income (HKD)" value={lesson.lesson_income != null ? `$${Number(lesson.lesson_income).toFixed(2)}` : '—'} />
            <Field label="Within a week"  value={lesson.within_a_week ? 'Yes ⚠️' : 'No'} />
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
              <input value={material} placeholder="https://…" onChange={(e) => setMaterial(e.target.value)} />
              <button className="btn btn--sm" disabled={busy}
                onClick={() => run(() => updateLesson(lessonId, { lesson_material_link: material }), () => 'Saved.')}>
                Save
              </button>
            </div>
            {lesson.lesson_material_link && (
              <a className="muted" style={{ fontSize: 12.5, marginTop: 4 }} href={lesson.lesson_material_link} target="_blank" rel="noreferrer">
                Open current link ↗
              </a>
            )}
          </div>

          {/* Lesson income */}
          <div className="field">
            <span className="field__label">Lesson income (HKD)</span>
            <div className="link-input">
              <input type="number" min="0" step="0.01" value={income} placeholder="0.00" onChange={(e) => setIncome(e.target.value)} />
              <button className="btn btn--sm" disabled={busy}
                onClick={() => run(() => updateLesson(lessonId, { lesson_income: income === '' ? null : Number(income) }), () => 'Saved.')}>
                Save
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="field">
            <span className="drawer__section-title">Actions</span>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              <button className="btn btn--primary btn--sm" disabled={busy}
                onClick={() => run(() => blastLesson(lessonId), (r) => `Blasted pool — ${r.sent ?? '?'} sent, ${r.failed ?? '?'} failed.`)}>
                <SendIcon width={15} height={15} /> Send WhatsApp blast
              </button>
              {lesson.assigned_teacher_id && (
                <button className="btn btn--sm" disabled={busy}
                  onClick={() => run(() => resendConfirmation(lessonId), (r) => r.confirmation?.ok ? 'Confirmation re-sent.' : 'Send failed.')}>
                  Resend confirmation + files
                </button>
              )}
            </div>
          </div>

          {/* Accepted tutors — assign from pool */}
          <div className="field">
            <span className="drawer__section-title">
              Accepted tutors ({accepted.length}) · {assignedCount}/{maxTutors} assigned
            </span>
            {full && <span className="muted" style={{ fontSize: 13, marginTop: 6 }}>Lesson is full — max {maxTutors} tutor(s) assigned.</span>}
            {!full && accepted.length === 0 && <span className="muted" style={{ fontSize: 13, marginTop: 6 }}>No acceptances yet.</span>}
            {accepted.filter(Boolean).map((t) => (
              <div className="pool-row" key={t.teacher_id}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span>{t.teacher_name} <span className="muted">· {t.whatsapp_number}</span></span>
                  {t.reliability_score != null && (
                    <span className="muted" style={{ fontSize: 12 }}>Score: {t.reliability_score.toFixed(0)}</span>
                  )}
                </div>
                <button className="btn btn--primary btn--sm" disabled={busy || full}
                  onClick={() => handleAssign(t.teacher_id)}>
                  {full ? 'Full' : 'Assign'}
                </button>
              </div>
            ))}
          </div>

          {/* Full offer pool */}
          <div className="field">
            <span className="drawer__section-title">Offer pool ({offers.length})</span>
            {offers.length === 0 && <span className="muted" style={{ fontSize: 13, marginTop: 6 }}>No tutors offered yet — send a blast.</span>}
            {offers.map((o) => (
              <div className="pool-row" key={o.id}>
                <span>{o.teacher?.teacher_name || o.teacher_id}</span>
                <span className="muted" style={{ fontSize: 13 }}>{o.offer_status}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {msg && (
        <div className="toast" style={{ background: msgType === 'error' ? '#dc2626' : '#111827' }}>
          {msg}
        </div>
      )}
    </>
  )
}

function Field({ label, value }) {
  return (
    <div className="field">
      <span className="field__label">{label}</span>
      <span className="field__value">{value}</span>
    </div>
  )
}
