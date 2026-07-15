import { useEffect, useState } from 'react'
import { PageHeader } from '../../components/layout/Layout'
import { getFinanceMonths, getTeacherEarnings, getCourseFinancials, computeSnapshot } from '../../services/endpoints'
import TeacherEarnings from './TeacherEarnings'
import CourseFinancials from './CourseFinancials'

export default function FinancesPage() {
  const [months, setMonths] = useState([])
  const [selected, setSelected] = useState(null)
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
          setSelected({ year: latest.year, month: latest.month })
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
    if (nextMode === 'month' && !selected && months.length > 0) {
      const latest = months[0]
      setSelected({ year: latest.year, month: latest.month })
    }
  }

  const handleMonthChange = (event) => {
    const value = event.target.value
    if (!value) {
      setSelected(null)
      return
    }
    const [year, month] = value.split('-').map(Number)
    setSelected({ year, month })
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
                <label className="muted" htmlFor="finance-month">Snapshot</label>
                <select id="finance-month" className="ld-filter-select" value={selected ? `${selected.year}-${selected.month}` : ''} onChange={handleMonthChange}>
                  <option value="">Select month</option>
                  {months.map((m) => (
                    <option key={`${m.year}-${m.month}`} value={`${m.year}-${m.month}`}>
                      {m.year}-{String(m.month).padStart(2, '0')}
                    </option>
                  ))}
                </select>
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
