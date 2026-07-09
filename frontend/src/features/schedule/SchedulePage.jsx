import { useEffect, useMemo, useState } from 'react'
import { PageHeader } from '../../components/layout/Layout'
import { ChevronLeft, ChevronRight } from '../../components/layout/Icons'
import LessonDetailDrawer from './LessonDetailDrawer'
import { DayView, MonthView, WeekView } from './views'
import { addDays, addMonths, addWeeks, periodLabel, rangeFor } from './dates'
import { useSchedule } from './useSchedule'
import { useLessonsContext } from '../../context/LessonsContext'
import { useDock } from '../chatbot/dockContext'
import './schedule.css'

const VIEWS = ['month', 'week', 'day']
const ZOOM_MIN = 0.7
const ZOOM_MAX = 1.8
const ZOOM_STEP = 0.15

const LEGEND = [
  ['green', 'Assigned'],
  ['red', 'Unassigned · within a week'],
  ['yellow', 'Unassigned · more than a week'],
  ['blue', 'Completed'],
  ['grey', 'Cancelled'],
]

const clampZoom = (z) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(z * 100) / 100))

export default function SchedulePage() {
  const [view, setView] = useState('month')
  const [anchor, setAnchor] = useState(new Date())
  const [selected, setSelected] = useState(null)
  const [zoom, setZoom] = useState(() => clampZoom(Number(localStorage.getItem('vinci.calzoom')) || 1))
  const { setOpen: setDockOpen, setTab: setDockTab } = useDock()

  useEffect(() => { localStorage.setItem('vinci.calzoom', String(zoom)) }, [zoom])

  const { start, end } = useMemo(() => rangeFor(view, anchor), [view, anchor])
  const { lessons, loading, error, reload } = useSchedule(start, end)
  const { invalidate } = useLessonsContext()

  const step = (dir) => {
    const fn = view === 'month' ? addMonths : view === 'week' ? addWeeks : addDays
    setAnchor((a) => fn(a, dir))
  }

  const ViewComp = view === 'month' ? MonthView : view === 'week' ? WeekView : DayView

  const handleDayClick = (day) => {
    setView('day')
    setAnchor(day)
  }

  // keep the open drawer in sync with refreshed data
  const selectedLive = selected ? lessons.find((l) => l.id === selected.id) || selected : null

  // After any mutation: reload this view + notify the Dashboard via context
  const handleChanged = () => {
    reload()
    invalidate()
  }

  return (
    <>
      <PageHeader
        title="Schedule"
        subtitle="The main hub — every lesson at a glance, colour-coded by status."
        actions={null}
      />

      <div className="content">
        <div className="sched-toolbar">
          <div className="segmented">
            {VIEWS.map((v) => (
              <button key={v} className={v === view ? 'active' : ''} onClick={() => setView(v)}>
                {v[0].toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>

          <div className="sched-nav">
            <button className="sched-nav__arrow" onClick={() => step(-1)} aria-label="Previous"><ChevronLeft /></button>
            <button className="btn sched-today" onClick={() => setAnchor(new Date())}>Today</button>
            <button className="sched-nav__arrow" onClick={() => step(1)} aria-label="Next"><ChevronRight /></button>
          </div>

          <span className="sched-period">{periodLabel(view, anchor)}</span>
          <span className="sched-spacer" />

          <div className="zoom-ctl" title="Zoom the calendar">
            <button onClick={() => setZoom((z) => clampZoom(z - ZOOM_STEP))} disabled={zoom <= ZOOM_MIN} aria-label="Zoom out">−</button>
            <button className="zoom-ctl__val" onClick={() => setZoom(1)} title="Reset zoom">{Math.round(zoom * 100)}%</button>
            <button onClick={() => setZoom((z) => clampZoom(z + ZOOM_STEP))} disabled={zoom >= ZOOM_MAX} aria-label="Zoom in">+</button>
          </div>

          <div className="legend">
            {LEGEND.map(([c, label]) => (
              <span key={c}><span className={`dot bg-${c}`} />{label}</span>
            ))}
          </div>
        </div>

        {error && <div className="banner" style={{ background: '#fee2e2', color: '#b91c1c', borderColor: '#fecaca' }}>
          Could not load lessons. Is the backend running and Supabase configured?
        </div>}

        <div className="cal-zoom" style={{ '--zoom': zoom }}>
          {loading ? <div className="spinner" /> : <ViewComp lessons={lessons} anchor={anchor} onSelect={setSelected} onDayClick={handleDayClick} />}
        </div>
      </div>

      {selectedLive && (
        <LessonDetailDrawer
          lesson={selectedLive}
          onClose={() => setSelected(null)}
          onChanged={handleChanged}
          sourceView="schedule"
        />
      )}
      {/* NewLessonModal replaced by the unified QuickInputPanel in the assistant dock */}
    </>
  )
}
