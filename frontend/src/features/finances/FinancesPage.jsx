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
  const [viewMode, setViewMode] = useState('month')

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
    if (!selected && viewMode !== 'overall') return
    setLoading(true)
    const request = viewMode === 'overall'
      ? Promise.all([
          getTeacherEarnings({}).catch(() => ({ teachers: [] })),
          getCourseFinancials({}).catch(() => ({ courses: [] })),
        ])
      : Promise.all([
          getTeacherEarnings({ year: selected.year, month: selected.month }).catch(() => ({ teachers: [] })),
          getCourseFinancials({ year: selected.year, month: selected.month }).catch(() => ({ courses: [] })),
        ])

    request
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
            <button className={viewMode === 'month' ? 'active' : ''} onClick={() => setViewMode('month')}>Selected month</button>
            <button className={viewMode === 'overall' ? 'active' : ''} onClick={() => setViewMode('overall')}>Overall</button>
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
                <select id="finance-month" className="ld-filter-select" value={selected ? `${selected.year}-${selected.month}` : ''} onChange={(e) => {
                  const v = e.target.value
                  if (!v) return setSelected(null)
                  const [y, m] = v.split('-').map(Number)
                  setSelected({ year: y, month: m })
                }}>
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
