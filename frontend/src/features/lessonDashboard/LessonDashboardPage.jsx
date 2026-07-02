import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { PageHeader } from '../../components/layout/Layout'
import { getDashboardLessons, getCourses, getTeachers } from '../../services/endpoints'
import LessonDetailDrawer from '../schedule/LessonDetailDrawer'
import { useLessonsContext } from '../../context/LessonsContext'
import './lessonDashboard.css'

// ── Helpers ─────────────────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: '', label: 'All action-needed' },
  { value: 'unassigned', label: 'Unassigned' },
  { value: 'offersent', label: 'Offer Sent' },
  { value: 'hasacceptance', label: 'Has Acceptance' },
]

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

function fmtDate(d) {
  if (!d) return '—'
  const dt = new Date(d + 'T00:00:00')
  return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function fmtTime(t) {
  if (!t) return ''
  return t.slice(0, 5)
}

function SortIcon({ dir }) {
  if (!dir) return <span style={{ opacity: 0.3, fontSize: 10, marginLeft: 3 }}>↕</span>
  return <span style={{ fontSize: 10, marginLeft: 3 }}>{dir === 'asc' ? '↑' : '↓'}</span>
}

function SearchIcon() {
  return (
    <svg className="ld-toolbar__search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  )
}

const PAGE_SIZE = 25

// ── Component ────────────────────────────────────────────────────────────────

export default function LessonDashboardPage() {
  // Filter state
  const [search, setSearch]           = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [courseFilter, setCourseFilter] = useState('')
  const [teacherFilter, setTeacherFilter] = useState('')
  const [dateFrom, setDateFrom]       = useState('')
  const [dateTo, setDateTo]           = useState('')
  const [showAll, setShowAll]         = useState(false)

  // Pagination + sort
  const [page, setPage]       = useState(1)
  const [sortCol, setSortCol] = useState('lesson_date')
  const [sortDir, setSortDir] = useState('asc')

  // Data
  const [result, setResult]   = useState({ items: [], total: 0, pages: 1 })
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [courses, setCourses] = useState([])
  const [teachers, setTeachers] = useState([])

  // Drawer
  const [selected, setSelected] = useState(null)

  // Shared context
  const { version, invalidate } = useLessonsContext()

  // Debounce search
  const searchTimer = useRef(null)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  useEffect(() => {
    clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => setDebouncedSearch(search), 350)
    return () => clearTimeout(searchTimer.current)
  }, [search])

  // Load reference data once
  useEffect(() => {
    getCourses().then(setCourses).catch(() => {})
    getTeachers().then(setTeachers).catch(() => {})
  }, [])

  // Load lessons whenever filters/page/version change
  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const params = { page, page_size: PAGE_SIZE }
    if (statusFilter)  params.status     = statusFilter
    if (courseFilter)  params.course_id  = courseFilter
    if (teacherFilter) params.teacher_id = teacherFilter
    if (dateFrom)      params.date_from  = dateFrom
    if (dateTo)        params.date_to    = dateTo
    if (showAll)       params.show_all   = true

    getDashboardLessons(params)
      .then((r) => setResult(r))
      .catch((e) => setError(e?.response?.data?.detail || 'Failed to load lessons'))
      .finally(() => setLoading(false))
  }, [page, statusFilter, courseFilter, teacherFilter, dateFrom, dateTo, showAll])

  useEffect(() => { load() }, [load, version])

  // Client-side search + sort on the current page's items
  const displayItems = useMemo(() => {
    let items = result.items || []
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase()
      items = items.filter(
        (l) =>
          (l.lesson_code || '').toLowerCase().includes(q) ||
          (l.course_name || '').toLowerCase().includes(q) ||
          (l.school_name || '').toLowerCase().includes(q) ||
          (l.assigned_teacher_name || '').toLowerCase().includes(q)
      )
    }
    // Only sort when showing all (default view preserves server-side urgency sort)
    if (showAll || statusFilter) {
      items = [...items].sort((a, b) => {
        let va = a[sortCol] ?? ''
        let vb = b[sortCol] ?? ''
        if (typeof va === 'string') va = va.toLowerCase()
        if (typeof vb === 'string') vb = vb.toLowerCase()
        if (va < vb) return sortDir === 'asc' ? -1 : 1
        if (va > vb) return sortDir === 'asc' ? 1 : -1
        return 0
      })
    }
    return items
  }, [result.items, debouncedSearch, sortCol, sortDir, showAll, statusFilter])

  const handleSort = (col) => {
    if (sortCol === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortCol(col); setSortDir('asc') }
  }

  const handleFilterChange = (setter) => (e) => { setter(e.target.value); setPage(1) }

  // Stats: computed from the current page's items.
  // The default (action-needed) view fetches all matching records server-side
  // so stats are accurate for that view.  When filters or "Show all" are active
  // the backend paginates at the query level, so per-status counts reflect only
  // the current page.
  const stats = useMemo(() => {
    const items = result.items || []
    return {
      total:         result.total,
      noAcceptance:  items.filter((l) => ['unassigned', 'offersent'].includes((l.status || '').toLowerCase())).length,
      hasAcceptance: items.filter((l) => (l.status || '').toLowerCase() === 'hasacceptance').length,
      urgent:        items.filter((l) => l.within_a_week && ['unassigned', 'offersent', 'hasacceptance'].includes((l.status || '').toLowerCase())).length,
    }
  }, [result])

  const thProps = (col) => ({
    className: sortCol === col ? 'sorted' : '',
    onClick: () => handleSort(col),
  })

  const hasFilters = statusFilter || courseFilter || teacherFilter || dateFrom || dateTo || search

  const handleChanged = () => {
    load()
    invalidate()
    setSelected(null)
  }

  const clearFilters = () => {
    setSearch(''); setStatusFilter(''); setCourseFilter('')
    setTeacherFilter(''); setDateFrom(''); setDateTo(''); setPage(1)
  }

  return (
    <>
      <PageHeader
        title="Lesson Dashboard"
        subtitle="Action-needed lessons — assign tutors, track status, and manage lesson details."
      />

      <div className="content">
        {/* Stats bar */}
        <div className="ld-stats">
          <div className="ld-stat">
            <span className="ld-stat__count">{stats.total}</span>
            <span className="ld-stat__label">Needs Action</span>
          </div>
          <div className="ld-stat">
            <span className="ld-stat__count" style={{ color: 'var(--status-red)' }}>{stats.urgent}</span>
            <span className="ld-stat__label">Urgent (≤7 days)</span>
          </div>
          <div className="ld-stat">
            <span className="ld-stat__count" style={{ color: 'var(--status-yellow)' }}>{stats.noAcceptance}</span>
            <span className="ld-stat__label">Unassigned / Offer Sent</span>
          </div>
          <div className="ld-stat">
            <span className="ld-stat__count" style={{ color: 'var(--status-green)' }}>{stats.hasAcceptance}</span>
            <span className="ld-stat__label">Has Acceptance</span>
          </div>
        </div>

        {/* Show-all toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13.5, cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={showAll}
              onChange={(e) => { setShowAll(e.target.checked); setPage(1) }}
              style={{ accentColor: 'var(--accent)', width: 15, height: 15 }}
            />
            Show all lessons (including assigned, completed, cancelled)
          </label>
        </div>

        {/* Toolbar */}
        <div className="ld-toolbar">
          <div className="ld-toolbar__search">
            <SearchIcon />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search lesson, course, school, tutor…" />
          </div>

          {/* Status filter — only show action-needed options unless showAll */}
          {!showAll && (
            <select className="ld-filter-select" value={statusFilter} onChange={handleFilterChange(setStatusFilter)}>
              {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          )}

          <select className="ld-filter-select" value={courseFilter} onChange={handleFilterChange(setCourseFilter)}>
            <option value="">All courses</option>
            {courses.map((c) => <option key={c.course_id} value={c.course_id}>{c.course_name}</option>)}
          </select>

          <select className="ld-filter-select" value={teacherFilter} onChange={handleFilterChange(setTeacherFilter)}>
            <option value="">All tutors</option>
            {teachers.map((t) => <option key={t.teacher_id} value={t.teacher_id}>{t.teacher_name}</option>)}
          </select>

          <input type="date" className="ld-filter-select" value={dateFrom} onChange={handleFilterChange(setDateFrom)} title="From date" />
          <input type="date" className="ld-filter-select" value={dateTo}   onChange={handleFilterChange(setDateTo)}   title="To date" />

          {hasFilters && (
            <button className="btn btn--sm btn--ghost" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>

        {/* Sort info banner — only in default (urgency) mode */}
        {!showAll && !statusFilter && (
          <div style={{
            fontSize: 12.5, color: 'var(--muted)', padding: '6px 0 2px',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{ fontWeight: 600, color: 'var(--status-red)' }}>Bucket 1:</span> No acceptances (Unassigned / Offer Sent) — closest date first
            &nbsp;·&nbsp;
            <span style={{ fontWeight: 600, color: 'var(--status-yellow)' }}>Bucket 2:</span> Has Acceptance — closest date first
          </div>
        )}

        {/* Table */}
        <div className="ld-table-wrap">
          {error && <div style={{ padding: '16px 20px', color: 'var(--status-red)', fontSize: 13.5 }}>Error: {error}</div>}
          {loading && !error && <div className="spinner" />}

          {!loading && !error && displayItems.length === 0 && (
            <div className="ld-empty">
              <div className="ld-empty__icon">✅</div>
              <div className="ld-empty__text">{showAll ? 'No lessons found' : 'No action needed'}</div>
              <div className="ld-empty__sub">
                {showAll ? 'Try adjusting your filters' : 'All lessons are assigned — great work!'}
              </div>
            </div>
          )}

          {!loading && !error && displayItems.length > 0 && (
            <table className="ld-table">
              <thead>
                <tr>
                  <th {...thProps('lesson_code')}>Lesson ID <SortIcon dir={sortCol === 'lesson_code' ? sortDir : null} /></th>
                  <th {...thProps('course_name')}>Course <SortIcon dir={sortCol === 'course_name' ? sortDir : null} /></th>
                  <th {...thProps('lesson_date')}>Date &amp; Time <SortIcon dir={sortCol === 'lesson_date' ? sortDir : null} /></th>
                  <th {...thProps('status')}>Status <SortIcon dir={sortCol === 'status' ? sortDir : null} /></th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {displayItems.map((lesson) => {
                  const sm = getStatusMeta(lesson.status)
                  const needsAction = ['unassigned', 'offersent', 'hasacceptance'].includes(
                    (lesson.status || '').toLowerCase()
                  )
                  return (
                    <tr key={lesson.id} className="clickable" onClick={() => setSelected(lesson)}>
                      <td>
                        <span className="ld-lesson-code">{lesson.lesson_code || '—'}</span>
                      </td>
                      <td>
                        <div className="ld-course-name">{lesson.course_name || '—'}</div>
                        <div className="ld-school-name">{lesson.school_name || ''}</div>
                      </td>
                      <td>
                        <div className="ld-datetime">
                          <div className="ld-date">
                            {lesson.within_a_week && needsAction && (
                              <span className="ld-urgent-dot" style={{ background: 'var(--status-red)' }} title="Within a week — urgent" />
                            )}
                            {fmtDate(lesson.lesson_date)}
                          </div>
                          <div className="ld-time">
                            {fmtTime(lesson.start_time)}{lesson.end_time ? ` – ${fmtTime(lesson.end_time)}` : ''}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`badge ${sm.color}`}>
                          <span className={`dot bg-${sm.color}`} />
                          {sm.label}
                        </span>
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <button className="ld-assign-btn" onClick={() => setSelected(lesson)}>
                          {needsAction ? 'Assign tutor' : 'View details'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          {/* Pagination */}
          {!loading && result.pages > 1 && (
            <div className="ld-pagination">
              <span>{result.total} lessons · Page {page} of {result.pages}</span>
              <div className="ld-pagination__pages">
                <button className="ld-pagination__btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Prev</button>
                {Array.from({ length: Math.min(result.pages, 7) }, (_, i) => {
                  const totalPages = result.pages
                  let start = Math.max(1, page - 3)
                  const end = Math.min(totalPages, start + 6)
                  start = Math.max(1, end - 6)
                  const pageNum = start + i
                  if (pageNum > totalPages) return null
                  return (
                    <button key={pageNum} className={`ld-pagination__btn${page === pageNum ? ' active' : ''}`} onClick={() => setPage(pageNum)}>
                      {pageNum}
                    </button>
                  )
                })}
                <button className="ld-pagination__btn" disabled={page >= result.pages} onClick={() => setPage((p) => p + 1)}>Next →</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Unified LessonDetailDrawer */}
      {selected && (
        <LessonDetailDrawer
          lesson={selected}
          onClose={() => setSelected(null)}
          onChanged={handleChanged}
          sourceView="dashboard"
        />
      )}
    </>
  )
}
