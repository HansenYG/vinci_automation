import LessonChip from './LessonChip'
import { format, isSameDay, isSameMonth, lessonsOn, monthMatrix, weekDays } from './dates'

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export function MonthView({ lessons, anchor, onSelect, onDayClick }) {
  const days = monthMatrix(anchor)
  const today = new Date()
  return (
    <div className="month-grid">
      {DOW.map((d) => <div key={d} className="month-dow">{d}</div>)}
      {days.map((day) => {
        const dl = lessonsOn(lessons, day)
        return (
          <div
            key={day.toISOString()}
            className={'month-cell' + (isSameMonth(day, anchor) ? '' : ' dim') + (isSameDay(day, today) ? ' today' : '')}
          >
            <button className="month-cell__date" onClick={() => onDayClick?.(day)}>
              {format(day, 'd')}
            </button>
            {dl.map((l) => <LessonChip key={l.id} lesson={l} onClick={onSelect} />)}
          </div>
        )
      })}
    </div>
  )
}

export function WeekView({ lessons, anchor, onSelect, onDayClick }) {
  const days = weekDays(anchor)
  const today = new Date()
  return (
    <div className="week-grid">
      {days.map((day) => {
        const dl = lessonsOn(lessons, day)
        return (
          <div
            key={day.toISOString()}
            className={'week-col' + (isSameDay(day, today) ? ' today' : '')}
          >
            <button className="week-col__head" onClick={() => onDayClick?.(day)}>
              {format(day, 'EEE')}<small>{format(day, 'd MMM')}</small>
            </button>
            {dl.length
              ? dl.map((l) => <LessonChip key={l.id} lesson={l} onClick={onSelect} />)
              : <span className="muted" style={{ fontSize: 12 }}>—</span>}
          </div>
        )
      })}
    </div>
  )
}

export function DayView({ lessons, anchor, onSelect }) {
  const dl = lessonsOn(lessons, anchor)
  if (!dl.length) return <div className="empty">No lessons on this day.</div>
  return (
    <div className="day-list">
      {dl.map((l) => <LessonChip key={l.id} lesson={l} size="lg" onClick={onSelect} />)}
    </div>
  )
}
