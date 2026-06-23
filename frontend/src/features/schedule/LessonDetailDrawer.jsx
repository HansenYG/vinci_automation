import { useEffect, useState } from 'react'
import { CloseIcon, SendIcon } from '../../components/layout/Icons'
import {
  assignTutor, blastLesson, getAcceptedPool, getOffers, resendConfirmation, updateLesson,
} from '../../services/endpoints'
import { fmtTime } from './dates'

export default function LessonDetailDrawer({ lesson, onClose, onChanged }) {
  const [offers, setOffers] = useState([])
  const [accepted, setAccepted] = useState([])
  const [material, setMaterial] = useState('')
  const [income, setIncome] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

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

  const flash = (t) => { setMsg(t); window.clearTimeout(flash._t); flash._t = window.setTimeout(() => setMsg(''), 2800) }
  const refresh = () => {
    getOffers(lessonId).then(setOffers).catch(() => {})
    getAcceptedPool(lessonId).then(setAccepted).catch(() => {})
    onChanged?.()
  }
  const run = async (fn, ok) => {
    setBusy(true)
    try { const r = await fn(); flash(ok(r)); refresh() }
    catch (e) { flash(e?.response?.data?.detail || 'Action failed — check the backend / WATI config.') }
    finally { setBusy(false) }
  }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer__head">
          <div>
            <span className={`badge ${lesson.color}`}><span className={`dot bg-${lesson.color}`} />{lesson.status}</span>
            <h2 style={{ margin: '10px 0 2px', fontSize: 19 }}>{lesson.course_name || 'Lesson'}</h2>
            <div className="muted" style={{ fontSize: 13 }}>{lesson.lesson_code}</div>
          </div>
          <button className="drawer__close" onClick={onClose}><CloseIcon /></button>
        </div>

        <div className="drawer__body">
          <div className="field-grid">
            <Field label="School" value={lesson.school_name || '—'} />
            <Field label="Date" value={lesson.lesson_date} />
            <Field label="Start" value={fmtTime(lesson.start_time) || '—'} />
            <Field label="End" value={fmtTime(lesson.end_time) || '—'} />
            <Field label="Assigned tutor" value={lesson.assigned_teacher_name || 'Unassigned'} />
            <Field label="Tutors" value={`${assignedCount} / ${maxTutors}`} />
            <Field label="Lesson income (HKD)" value={lesson.lesson_income != null ? `$${Number(lesson.lesson_income).toFixed(2)}` : '—'} />
            <Field label="Within a week" value={lesson.within_a_week ? 'Yes' : 'No'} />
          </div>

          {/* Lesson material link — the design's extra field + "send files" */}
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

          {/* Lesson income — editable field */}
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

          {/* Trigger actions */}
          <div className="field">
            <span className="drawer__section-title">Actions</span>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              <button className="btn btn--primary btn--sm" disabled={busy}
                onClick={() => run(() => blastLesson(lessonId), (r) => `Blasted pool — ${r.sent} sent, ${r.failed} failed.`)}>
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

          {/* Accepted tutors → choose from pool (capped at max_tutors) */}
          <div className="field">
            <span className="drawer__section-title">Accepted tutors ({accepted.length}) · {assignedCount}/{maxTutors} assigned</span>
            {full && <span className="muted" style={{ fontSize: 13, marginTop: 6 }}>Lesson is full — max {maxTutors} tutor(s) assigned.</span>}
            {!full && accepted.length === 0 && <span className="muted" style={{ fontSize: 13, marginTop: 6 }}>No acceptances yet.</span>}
            {accepted.filter(Boolean).map((t) => (
              <div className="pool-row" key={t.teacher_id}>
                <span>{t.teacher_name} <span className="muted">· {t.whatsapp_number}</span></span>
                <button className="btn btn--primary btn--sm" disabled={busy || full}
                  onClick={() => run(() => assignTutor(lessonId, t.teacher_id), (r) => `Assigned ${t.teacher_name} (${r.assigned_count}/${r.max_tutors}).`)}>
                  Assign
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

      {msg && <div className="toast">{msg}</div>}
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
