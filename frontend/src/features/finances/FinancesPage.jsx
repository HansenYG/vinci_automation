import { useEffect, useState } from 'react'
import { PageHeader } from '../../components/layout/Layout'
import { getFinanceMonths, getTeacherEarnings, getCourseFinancials, computeSnapshot } from '../../services/endpoints'
import TeacherEarnings from './TeacherEarnings'
import CourseFinancials from './CourseFinancials'

export default function FinancesPage() {
  const [months, setMonths] = useState([])
  const [selected, setSelected] = useState(null)
  const [draftSelection, setDraftSelection] = useState(null)
  const [teachers, setTeachers] = useState([])
  const [courses, setCourses] = useState([])
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState('overall')

  useEffect(() => {
    getFinanceMonths()
      .then((m) => {
        const nextMonths = m || []
        setMonths(nextMonths)
        if (nextMonths.length > 0) {
          const latest = nextMonths[0]
          const latestSelection = { year: latest.year, month: latest.month }
          setSelected(latestSelection)
          setDraftSelection(latestSelection)
        }
      })
      .catch(() => setMonths([]))
  }, [])

  useEffect(() => {
    if (viewMode === 'overall') {
      setLoading(true)
      Promise.all([
        getTeacherEarnings({}).catch(() => ({ teachers: [] })),
        getCourseFinancials({}).catch(() => ({ courses: [] })),
      ])
        .then(([tRes, cRes]) => {
          const nextTeachers = Array.isArray(tRes?.teachers) ? tRes.teachers : []
          const nextCourses = Array.isArray(cRes?.courses) ? cRes.courses : []
          setTeachers(nextTeachers)
          setCourses(nextCourses)
        })
        .finally(() => setLoading(false))
      return
    }

    if (!selected) {
      setTeachers([])
      setCourses([])
      return
    }

    setLoading(true)
    Promise.all([
      getTeacherEarnings({ year: selected.year, month: selected.month }).catch(() => ({ teachers: [] })),
      getCourseFinancials({ year: selected.year, month: selected.month }).catch(() => ({ courses: [] })),
    ])
      .then(([tRes, cRes]) => {
        const nextTeachers = Array.isArray(tRes?.teachers) ? tRes.teachers : []
        const nextCourses = Array.isArray(cRes?.courses) ? cRes.courses : []
        setTeachers(nextTeachers)
        setCourses(nextCourses)
      })
      .finally(() => setLoading(false))
  }, [selected, viewMode])

  const refreshSnapshot = async () => {
    if (!selected && viewMode !== 'overall') return
    setLoading(true)
    try {
      const target = viewMode === 'overall' ? {} : { year: selected.year, month: selected.month }
      await computeSnapshot(target)
      const tRes = viewMode === 'overall'
        ? await getTeacherEarnings({})
        : await getTeacherEarnings({ year: selected.year, month: selected.month })
      const cRes = viewMode === 'overall'
        ? await getCourseFinancials({})
        : await getCourseFinancials({ year: selected.year, month: selected.month })
      const nextTeachers = Array.isArray(tRes?.teachers) ? tRes.teachers : []
      const nextCourses = Array.isArray(cRes?.courses) ? cRes.courses : []
      setTeachers(nextTeachers)
      setCourses(nextCourses)
    } catch (e) {
      // ignore
    }
    setLoading(false)
  }

  const handleViewModeChange = (nextMode) => {
    setViewMode(nextMode)
    if (nextMode === 'month') {
      const nextSelection = selected || draftSelection || (months[0] ? { year: months[0].year, month: months[0].month } : null)
      if (nextSelection) {
        setDraftSelection(nextSelection)
        setSelected(nextSelection)
      }
    }
  }

  const applyPeriodSelection = () => {
    if (!draftSelection || draftSelection.month == null) {
      setSelected(null)
      return
    }
    setSelected({ year: draftSelection.year, month: draftSelection.month })
  }

  const currentYear = new Date().getFullYear()
  const yearOptions = Array.from({ length: Math.max(1, currentYear - 2019) }, (_, index) => currentYear - index)
  const selectedYear = draftSelection?.year ?? selected?.year ?? yearOptions[0] ?? null
  const availableMonthsForYear = months
    .filter((m) => m.year === selectedYear)
    .map((m) => m.month)
    .sort((a, b) => a - b)
  const monthOptions = (availableMonthsForYear.length > 0 ? availableMonthsForYear : Array.from({ length: 12 }, (_, index) => index + 1))
    .map((month) => ({ month, label: String(month).padStart(2, '0') }))

  const handleYearChange = (event) => {
    const year = Number(event.target.value)
    const nextSelection = year ? { year, month: null } : null
    setDraftSelection(nextSelection)
    if (!nextSelection) {
      setSelected(null)
    }
  }

  const handleMonthChange = (event) => {
    const month = Number(event.target.value)
    if (!selectedYear || !month) {
      const nextSelection = selectedYear ? { year: selectedYear, month: null } : null
      setDraftSelection(nextSelection)
      setSelected(null)
      return
    }
    const nextSelection = { year: selectedYear, month }
    setDraftSelection(nextSelection)
    setSelected(nextSelection)
  }

  const headerLabel = viewMode === 'overall'
    ? 'Overall totals'
    : selected ? `${selected.year}-${String(selected.month).padStart(2, '0')}` : 'Select a period'

  return (
    <div>
      <PageHeader
        title="Finances"
        subtitle="Read-only tutor earnings and course financials for the latest month, previous months, and overall totals."
        actions={[
          <div key="seg" className="segmented">
            <button className={viewMode === 'month' ? 'active' : ''} onClick={() => handleViewModeChange('month')}>Selected month</button>
            <button className={viewMode === 'overall' ? 'active' : ''} onClick={() => handleViewModeChange('overall')}>Overall</button>
          </div>,
          <button key="refresh" className="btn btn--primary btn--sm" onClick={refreshSnapshot} disabled={loading}>
            Recompute snapshot
          </button>,
        ]}
      />

      <section className="content">
        <div className="card" style={{ padding: 18, marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            {viewMode === 'month' && (
              <>
                <label className="muted" htmlFor="finance-year">Year</label>
                <select id="finance-year" className="ld-filter-select" value={selectedYear ?? ''} onChange={handleYearChange}>
                  <option value="">Select year</option>
                  {yearOptions.map((year) => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>

                <label className="muted" htmlFor="finance-month">Month</label>
                <select id="finance-month" className="ld-filter-select" value={draftSelection && draftSelection.month != null ? draftSelection.month : ''} onChange={handleMonthChange}>
                  <option value="">Select month</option>
                  {monthOptions.map((m) => (
                    <option key={`${selectedYear}-${m.month}`} value={m.month}>
                      {m.label}
                    </option>
                  ))}
                </select>

                <button className="btn btn--primary btn--sm" onClick={applyPeriodSelection} disabled={!draftSelection || draftSelection.month == null}>
                  View period
                </button>
              </>
            )}
            <span className="badge blue">{headerLabel}</span>
          </div>
        </div>

        {(selected || viewMode === 'overall') ? (
          <div>
            {!loading && viewMode === 'month' && selected && teachers.length === 0 && courses.length === 0 ? (
              <div className="card empty">No snapshot data is available for this month yet. Try recomputing the snapshot.</div>
            ) : null}
            <TeacherEarnings rows={teachers} loading={loading} viewMode={viewMode} selected={selected} />
            <CourseFinancials rows={courses} loading={loading} viewMode={viewMode} selected={selected} />
          </div>
        ) : (
          <div className="card empty">Please select a snapshot period to view finances.</div>
        )}
      </section>
    </div>
  )
}
