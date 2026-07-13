/**
 * LessonDetailDrawer — unified lesson detail + assign-tutor drawer.
 *
 * Used by BOTH the Schedule Calendar and the Lesson Dashboard.
 * After any mutation it calls:
 *   1. onChanged()  — so the parent view refreshes its own data
 *   2. invalidate() — so the OTHER view (via LessonsContext) also refreshes
 *
 * PRD-compliant assign flow:
 *   - Accepted tutors sorted highest score → lowest (PRD §2 step 4)
 *   - CLASH (different tutor already assigned) → warning modal with confirm
 *   - DUPLICATE (same tutor already assigned) → inline error message
 *   - FULL (max tutors reached) → disabled buttons
 *   - On successful assign: lesson disappears from dashboard if fully assigned
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CloseIcon, SendIcon } from '../../components/layout/Icons'
import {
  assignTutor, blastLesson, getAcceptedPool, getOffers, resendConfirmation, updateLesson, getSchools,
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
  expired:       { label: 'Expired',        color: 'grey' },
}
function getStatusMeta(status) {
  const key = (status || '').toLowerCase()
  return STATUS_META[key] || { label: status || '—', color: 'grey' }
}

function scoreBar(score) {
  const pct = Math.min(100, Math.max(0, score || 0))
  const color = pct >= 70 ? '#22c55e' : pct >= 45 ? '#f59e0b' : '#ef4444'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
      <div style={{ flex: 1, height: 4, background: '#e5e7eb', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 600, minWidth: 28 }}>{pct.toFixed(0)}</span>
    </div>
  )
}

// ── Clash Confirm Modal ───────────────────────────────────────────────────────
function ClashModal({ existingName, newName, onConfirm, onCancel }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1100,
      background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: '28px 32px', maxWidth: 420, width: '90%',
        boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
      }}>
        <div style={{ fontSize: 22, marginBottom: 8 }}>⚠️ Re-assign tutor?</div>
        <p style={{ fontSize: 14, color: '#374151', lineHeight: 1.6, margin: '0 0 20px' }}>
          This lesson already has <strong>{existingName}</strong> assigned.
          Assigning <strong>{newName}</strong> will replace them as the primary tutor.
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button className="btn btn--sm" onClick={onCancel}>Cancel</button>
          <button
            className="btn btn--sm"
            style={{ background: '#f59e0b', color: '#fff', border: '1px solid #f59e0b' }}
            onClick={onConfirm}
          >
            Yes, re-assign
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function LessonDetailDrawer({ lesson, onClose, onChanged, sourceView = 'schedule' }) {
  const [offers, setOffers]     = useState([])
  const [accepted, setAccepted] = useState([])
  const [material, setMaterial] = useState('')
  const [income, setIncome]     = useState('')
  const [school, setSchool]     = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime]   = useState('')
  const [busy, setBusy]         = useState(false)
  const [msg, setMsg]           = useState('')
  const [msgType, setMsgType]   = useState('info')
  const [schools, setSchools]         = useState([])
  const [confirmCancel, setConfirmCancel] = useState(false)
  const cancelTimerRef = useRef(null)

  // Clash modal state
  const [clashPending, setClashPending] = useState(null) // { teacherId, teacherName, existingName }

  const { invalidate } = useLessonsContext()
  const navigate = useNavigate()

  const lessonId = lesson?.id

  useEffect(() => {
    if (!lessonId) return
    setMaterial(lesson.lesson_material_link || '')
    setIncome(lesson.lesson_income ?? '')
    setSchool(lesson.school_name || '')
    setStartTime(lesson.start_time || '')
    setEndTime(lesson.end_time || '')
    setMsg('')
    setClashPending(null)
    getOffers(lessonId).then(setOffers).catch(() => setOffers([]))
    getAcceptedPool(lessonId).then(setAccepted).catch(() => setAccepted([]))
    getSchools().then(setSchools).catch(() => setSchools([]))
  }, [lessonId]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!lesson) return null

  const assignedCount = offers.filter((o) => o.offer_status === 'assigned').length
  const maxTutors     = lesson.max_tutors ?? 1
  const full          = assignedCount >= maxTutors
  const statusMeta    = getStatusMeta(lesson.status || lesson.color)
  const assignedTutors = offers
    .filter((o) => o.offer_status === 'assigned')
    .map((o) => o.teacher?.teacher_name || o.teacher_id)

  // ── Helpers ────────────────────────────────────────────────────────────────
  const flash = (t, type = 'info') => {
    setMsg(t); setMsgType(type)
    window.clearTimeout(flash._t)
    flash._t = window.setTimeout(() => setMsg(''), 4000)
  }

  const refresh = () => {
    getOffers(lessonId).then(setOffers).catch(() => {})
    getAcceptedPool(lessonId).then(setAccepted).catch(() => {})
    onChanged?.()
    invalidate()
  }

  const run = async (fn, ok) => {
    setBusy(true)
    try   { const r = await fn(); flash(ok(r), 'info'); refresh() }
    catch (e) { flash(e?.response?.data?.detail || 'Action failed — check the backend / WATI config.', 'error') }
    finally   { setBusy(false) }
  }

  const saveSchool = async () => {
    if (!school.trim()) {
      flash('School name cannot be empty', 'error')
      return
    }
    const selectedSchool = schools.find((s) => s.school_name === school)
    await run(
      () => updateLesson(lessonId, { school_name: school, school_id: selectedSchool?.school_id }).then(r => r.data),
      () => 'School updated.'
    )
  }

  const saveTime = async (field) => {
    if (field === 'start' && !startTime.trim()) {
      flash('Start time cannot be empty', 'error')
      return
    }
    if (field === 'end' && !endTime.trim()) {
      flash('End time cannot be empty', 'error')
      return
    }
    const updates = {}
    if (field === 'start' || field === 'both') {
      updates.start_time = startTime
    }
    if (field === 'end' || field === 'both') {
      updates.end_time = endTime
    }
    await run(
      () => updateLesson(lessonId, updates).then(r => r.data),
      () => 'Time updated.'
    )
  }

  // ── Assign with clash/duplicate/full handling ──────────────────────────────
  const doAssign = async (teacherId, forceReassign = false) => {
    setBusy(true)
    setMsg('')
    try {
      const resp = await assignTutor(lessonId, teacherId, true, forceReassign)
      // Success
      flash('Tutor assigned and confirmation sent.', 'info')
      refresh()
    } catch (err) {
      const status = err?.response?.status
      const body   = err?.response?.data || {}

      if (status === 409) {
        if (body.error_code === 'DUPLICATE') {
          flash(`Error: ${body.detail || 'This tutor is already assigned.'}`, 'error')
        } else if (body.error_code === 'CLASH') {
          // Show the clash modal — user must confirm
          const existingName = lesson.assigned_teacher_name || 'existing tutor'
          const newTeacher   = accepted.find((t) => t.teacher_id === teacherId)
          const newName      = newTeacher?.teacher_name || teacherId
          setClashPending({ teacherId, teacherName: newName, existingName })
        } else if (body.error_code === 'FULL') {
          flash(`Error: ${body.detail || 'Lesson is full.'}`, 'error')
        } else {
          flash(body.detail || 'Assignment failed.', 'error')
        }
      } else {
        flash(err?.response?.data?.detail || 'Assignment failed — check the backend.', 'error')
      }
    } finally {
      setBusy(false)
    }
  }

  // Accept a pending tutor (admin action — bypasses WhatsApp)
  // This has been removed in favor of WhatsApp-only acceptances

  const handleClashConfirm = () => {
    if (!clashPending) return
    const { teacherId } = clashPending
    setClashPending(null)
    doAssign(teacherId, true)
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
            <h2 style={{ margin: '10px 0 2px', fontSize: 19, display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {lesson.start_time && <span className="chip__time">{fmtTime(lesson.start_time)}</span>}
              {lesson.school_name && <span className="chip__line chip__school">{lesson.school_name}</span>}
              <span className="chip__line chip__title">{lesson.course_name || lesson.lesson_code || 'Lesson'}</span>
            </h2>
            <div className="muted" style={{ fontSize: 13 }}>
              {lesson.lesson_code}
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
            {/* Editable School */}
            <div className="field">
              <span className="field__label">School</span>
              <div className="link-input">
                <select value={school} onChange={(e) => setSchool(e.target.value)} style={{ flex: 1, padding: '6px 8px', fontSize: 13, borderRadius: 6, border: '1px solid var(--border)' }}>
                  <option value="">— select school —</option>
                  {schools.map((s) => <option key={s.school_id} value={s.school_name}>{s.school_name}</option>)}
                </select>
                <button className="btn btn--sm" disabled={busy} onClick={saveSchool}>
                  Save
                </button>
              </div>
              {(() => {
                const selectedSchool = schools.find((s) => s.school_name === school)
                return selectedSchool?.google_maps_link ? (
                  <a className="muted" style={{ fontSize: 12.5, marginTop: 4 }} href={selectedSchool.google_maps_link} target="_blank" rel="noreferrer">
                    Open Google Maps ↗
                  </a>
                ) : null
              })()}
            </div>
            
            <Field label="Date"           value={lesson.lesson_date} />
            
            {/* Editable Start Time */}
            <div className="field">
              <span className="field__label">Start</span>
              <div className="link-input">
                <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
                <button className="btn btn--sm" disabled={busy} onClick={() => saveTime('start')}>
                  Save
                </button>
              </div>
            </div>
            
            {/* Editable End Time */}
            <div className="field">
              <span className="field__label">End</span>
              <div className="link-input">
                <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
                <button className="btn btn--sm" disabled={busy} onClick={() => saveTime('end')}>
                  Save
                </button>
              </div>
            </div>
            
            <Field
              label={assignedTutors.length > 1 ? 'Assigned tutors' : 'Assigned tutor'}
              value={assignedTutors.length > 0 ? assignedTutors.join(', ') : 'Unassigned'}
            />
            <Field label="Tutors" value={`${assignedCount} / ${maxTutors}`} />
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
                onClick={() => run(() => updateLesson(lessonId, { lesson_material_link: material }).then(r => r.data), () => 'Saved.')}>
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
                onClick={() => run(
                  () => updateLesson(lessonId, { lesson_income: income === '' ? null : Number(income) }).then(r => r.data),
                  () => 'Saved.'
                )}>
                Save
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="field">
            <span className="drawer__section-title">Actions</span>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              <button className="btn btn--primary btn--sm" disabled={busy}
                onClick={() => run(() => blastLesson(lessonId).then(r => r.data ?? r), (r) => `Blasted pool — ${r.sent ?? '?'} sent, ${r.failed ?? '?'} failed.`)}>
                <SendIcon width={15} height={15} /> Send WhatsApp blast
              </button>
              {lesson.assigned_teacher_id && (
                <button className="btn btn--sm" disabled={busy}
                  onClick={() => run(() => resendConfirmation(lessonId).then(r => r.data ?? r), (r) => r.confirmation?.ok ? 'Confirmation re-sent.' : 'Send failed.')}>
                  Resend confirmation + files
                </button>
              )}
              {/* Cancel lesson — only shown when lesson is not already cancelled */}
              {(lesson.status || '').toLowerCase() !== 'cancelled' && (
                confirmCancel ? (
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', width: '100%', marginTop: 4 }}>
                    <span style={{ fontSize: 13, color: 'var(--muted)' }}>Mark this lesson as Cancelled?</span>
                    <button
                      className="btn btn--sm"
                      style={{ background: '#dc2626', color: '#fff', border: '1px solid #dc2626' }}
                      disabled={busy}
                      onClick={() => {
                        clearTimeout(cancelTimerRef.current)
                        setConfirmCancel(false)
                        run(
                          () => updateLesson(lessonId, { status: 'cancelled' }).then(r => r.data),
                          () => { setTimeout(() => onClose?.(), 800); return 'Lesson cancelled.' }
                        )
                      }}
                    >
                      Yes, cancel it
                    </button>
                    <button className="btn btn--sm" disabled={busy} onClick={() => { clearTimeout(cancelTimerRef.current); setConfirmCancel(false) }}>
                      No, keep
                    </button>
                  </div>
                ) : (
                  <button
                    className="btn btn--sm"
                    style={{ color: '#dc2626', borderColor: '#dc2626' }}
                    disabled={busy}
                    onClick={() => {
                      setConfirmCancel(true)
                      cancelTimerRef.current = setTimeout(() => setConfirmCancel(false), 8000)
                    }}
                  >
                    Cancel lesson
                  </button>
                )
              )}
            </div>
          </div>

          {/* Accepted tutors — assign from pool, sorted by score descending */}
          <div className="field">
            <span className="drawer__section-title">
              Accepted tutors ({accepted.length}) · {assignedCount}/{maxTutors} assigned
            </span>
            {full && <span className="muted" style={{ fontSize: 13, marginTop: 6 }}>Lesson is full — max {maxTutors} tutor(s) assigned.</span>}
            {!full && accepted.length === 0 && (
              <span className="muted" style={{ fontSize: 13, marginTop: 6 }}>No acceptances yet — send a blast first.</span>
            )}
            {accepted.filter(Boolean).map((t) => {
              const score = t.reliability_score ?? t.hours_score ?? null
              const isAlreadyAssigned = offers.some(
                (o) => o.teacher_id === t.teacher_id && o.offer_status === 'assigned'
              )
              return (
                <div className="pool-row" key={t.teacher_id}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontWeight: 500 }}>{t.teacher_name}</span>
                      {isAlreadyAssigned && (
                        <span style={{
                          fontSize: 10, fontWeight: 700, background: '#dcfce7', color: '#16a34a',
                          padding: '1px 6px', borderRadius: 10, letterSpacing: 0.3,
                        }}>ASSIGNED</span>
                      )}
                    </div>
                    <span className="muted" style={{ fontSize: 12 }}>{t.whatsapp_number}</span>
                    {score != null && scoreBar(score)}
                  </div>
                  <button
                    className={`btn btn--sm${isAlreadyAssigned ? '' : ' btn--primary'}`}
                    disabled={busy || (full && !isAlreadyAssigned)}
                    onClick={() => doAssign(t.teacher_id)}
                    style={isAlreadyAssigned ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
                  >
                    {isAlreadyAssigned ? 'Assigned' : full ? 'Full' : 'Assign'}
                  </button>
                </div>
              )
            })}
          </div>

          {/* Full offer pool */}
          <div className="field">
            <span className="drawer__section-title">Offer pool ({offers.length})</span>
            {offers.length === 0 && <span className="muted" style={{ fontSize: 13, marginTop: 6 }}>No tutors offered yet — send a blast.</span>}
            {offers.map((o) => {
              const isAccepted = o.offer_status === 'accepted'
              const isAssigned = o.offer_status === 'assigned'
              return (
                <div className="pool-row" key={o.id}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontWeight: 500 }}>{o.teacher?.teacher_name || o.teacher_id}</span>
                      {isAssigned && (
                        <span style={{
                          fontSize: 10, fontWeight: 700, background: '#dcfce7', color: '#16a34a',
                          padding: '1px 6px', borderRadius: 10, letterSpacing: 0.3,
                        }}>ASSIGNED</span>
                      )}
                      {isAccepted && (
                        <span style={{
                          fontSize: 10, fontWeight: 700, background: '#dbeafe', color: '#2563eb',
                          padding: '1px 6px', borderRadius: 10, letterSpacing: 0.3,
                        }}>ACCEPTED</span>
                      )}
                    </div>
                    <span className="muted" style={{ fontSize: 12 }}>{o.teacher?.whatsapp_number || ''}</span>
                  </div>
                  <span className="muted" style={{ fontSize: 12, textTransform: 'capitalize' }}>{o.offer_status}</span>
                </div>
              )
            })}
          </div>
        </div>
      </aside>

      {/* Clash confirmation modal */}
      {clashPending && (
        <ClashModal
          existingName={clashPending.existingName}
          newName={clashPending.teacherName}
          onConfirm={handleClashConfirm}
          onCancel={() => setClashPending(null)}
        />
      )}

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
