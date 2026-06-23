import {
  addDays, addMonths, addWeeks, eachDayOfInterval, endOfMonth, endOfWeek,
  format, isSameDay, isSameMonth, parseISO, startOfMonth, startOfWeek,
} from 'date-fns'

export { addDays, addMonths, addWeeks, eachDayOfInterval, format, isSameDay, isSameMonth, parseISO }

const iso = (d) => format(d, 'yyyy-MM-dd')

// The visible date range (inclusive ISO bounds) for a given view + anchor.
export function rangeFor(view, anchor) {
  if (view === 'day') return { start: iso(anchor), end: iso(anchor) }
  if (view === 'week') {
    return { start: iso(startOfWeek(anchor)), end: iso(endOfWeek(anchor)) }
  }
  // month: pad to full weeks so the grid is rectangular
  return {
    start: iso(startOfWeek(startOfMonth(anchor))),
    end: iso(endOfWeek(endOfMonth(anchor))),
  }
}

export function monthMatrix(anchor) {
  return eachDayOfInterval({
    start: startOfWeek(startOfMonth(anchor)),
    end: endOfWeek(endOfMonth(anchor)),
  })
}

export function weekDays(anchor) {
  return eachDayOfInterval({ start: startOfWeek(anchor), end: endOfWeek(anchor) })
}

export function periodLabel(view, anchor) {
  if (view === 'day') return format(anchor, 'EEEE, d MMMM yyyy')
  if (view === 'week') {
    const s = startOfWeek(anchor)
    const e = endOfWeek(anchor)
    return `${format(s, 'd MMM')} – ${format(e, 'd MMM yyyy')}`
  }
  return format(anchor, 'MMMM yyyy')
}

export function fmtTime(t) {
  return t ? String(t).slice(0, 5) : ''
}

export function lessonsOn(lessons, day) {
  return lessons
    .filter((l) => isSameDay(parseISO(l.lesson_date), day))
    .sort((a, b) => fmtTime(a.start_time).localeCompare(fmtTime(b.start_time)))
}
