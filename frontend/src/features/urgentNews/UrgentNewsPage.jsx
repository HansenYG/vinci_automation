import { useEffect, useState } from 'react'
import { PageHeader } from '../../components/layout/Layout'
import { getUrgentNews } from '../../services/endpoints'
import LessonDetailDrawer from '../schedule/LessonDetailDrawer'
import { useLessonsContext } from '../../context/LessonsContext'
import './urgentNews.css'

function fmtDate(d) {
  if (!d) return '—'
  const dt = new Date(d + 'T00:00:00')
  return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', weekday: 'short' })
}

function fmtTime(t) {
  if (!t) return ''
  return t.slice(0, 5)
}

function eventLabel(ev) {
  const map = {
    blast: 'Offers sent',
    reblast: 'Offers re-sent',
    accept: 'Tutor accepted',
    assign: 'Tutor assigned',
    cancel: 'Tutor cancelled',
    reschedule: 'Rescheduled',
    confirmation_sent: 'Confirmation sent',
    admin_notified: 'Admin notified',
  }
  return map[ev.type] || ev.type
}

export default function UrgentNewsPage() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const { invalidate } = useLessonsContext()

  const load = () => {
    setLoading(true)
    getUrgentNews()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleChanged = () => {
    load()
    invalidate()
    setSelected(null)
  }

  const unassigned = rows.filter((r) => r.reason === 'unassigned')
  const cancelled = rows.filter((r) => r.reason === 'cancelled')
  const other = rows.filter((r) => r.reason !== 'unassigned' && r.reason !== 'cancelled')

  return (
    <>
      <PageHeader
        title="Urgent News"
        subtitle={`${rows.length} item${rows.length !== 1 ? 's' : ''} needing attention within a week.`}
      />

      <div className="content">
        {/* Stats */}
        <div className="un-stats">
          <div className="un-stat">
            <span className="un-stat__count" style={{ color: 'var(--status-red)' }}>{rows.length}</span>
            <span className="un-stat__label">Total urgent</span>
          </div>
          <div className="un-stat">
            <span className="un-stat__count" style={{ color: 'var(--status-yellow)' }}>{unassigned.length}</span>
            <span className="un-stat__label">Unassigned</span>
          </div>
          <div className="un-stat">
            <span className="un-stat__count" style={{ color: 'var(--status-grey)' }}>{cancelled.length}</span>
            <span className="un-stat__label">Cancelled</span>
          </div>
        </div>

        {loading && <div className="spinner" />}

        {!loading && rows.length === 0 && (
          <div className="un-empty">
            <div className="un-empty__icon">&#10003;</div>
            <div className="un-empty__text">All clear</div>
            <div className="un-empty__sub">No urgent items within the next 7 days.</div>
          </div>
        )}

        {!loading && rows.length > 0 && (
          <div className="un-list">
            {unassigned.length > 0 && (
              <UrgentSection title="Unassigned Lessons" items={unassigned} onSelect={setSelected} />
            )}
            {cancelled.length > 0 && (
              <UrgentSection title="Cancelled by Tutor" items={cancelled} onSelect={setSelected} />
            )}
            {other.length > 0 && (
              <UrgentSection title="Other" items={other} onSelect={setSelected} />
            )}
          </div>
        )}
      </div>

      {selected && (
        <LessonDetailDrawer
          lesson={selected}
          onClose={() => setSelected(null)}
          onChanged={handleChanged}
          sourceView="urgent"
        />
      )}
    </>
  )
}

function UrgentSection({ title, items, onSelect }) {
  return (
    <div className="un-section">
      <h3 className="un-section__title">{title} ({items.length})</h3>
      {items.map((item) => (
        <UrgentCard key={item.lesson_id} item={item} onSelect={onSelect} />
      ))}
    </div>
  )
}

function UrgentCard({ item, onSelect }) {
  const isUnassigned = item.reason === 'unassigned'
  return (
    <div className="un-card">
      <div className="un-card__main">
        <div className="un-card__header">
          <span className="un-card__code">{item.lesson_code || '—'}</span>
          <span className={`badge ${isUnassigned ? 'red' : 'grey'}`}>
            {item.reason}
          </span>
        </div>
        <div className="un-card__body">
          <div className="un-card__course">{item.course_name || '—'}</div>
          <div className="un-card__school">{item.school_name || ''}</div>
          <div className="un-card__datetime">
            {fmtDate(item.lesson_date)}{item.start_time ? ` · ${fmtTime(item.start_time)}–${fmtTime(item.end_time)}` : ''}
          </div>
          <div className="un-card__reason">{item.reason_text}</div>
        </div>
        {item.recent_events?.length > 0 && (
          <div className="un-card__events">
            {item.recent_events.map((ev, i) => (
              <span key={i} className="un-card__event">
                {eventLabel(ev)}{ev.teacher ? ` (${ev.teacher})` : ''}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="un-card__actions">
        <button className="btn btn--sm btn--primary" onClick={() => onSelect(item)}>
          {isUnassigned ? 'Assign tutor' : 'View details'}
        </button>
      </div>
    </div>
  )
}
