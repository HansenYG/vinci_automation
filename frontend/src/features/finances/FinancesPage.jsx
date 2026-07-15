import { useEffect, useState } from 'react'
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
    if (!selected) return
    if (viewMode === 'overall') {
      setLoading(true)
      Promise.all([
        getTeacherEarnings({}).catch(() => ({ teachers: [] })),
        getCourseFinancials({}).catch(() => ({ courses: [] })),
      ])
        .then(([tRes, cRes]) => {
          setTeachers(tRes.teachers || [])
          setCourses(cRes.courses || [])
        })
        .finally(() => setLoading(false))
      return
    }

    const { year, month } = selected
    setLoading(true)
    Promise.all([
      getTeacherEarnings({ year, month }).catch(() => ({ teachers: [] })),
      getCourseFinancials({ year, month }).catch(() => ({ courses: [] })),
    ])
      .then(([tRes, cRes]) => {
        setTeachers(tRes.teachers || [])
        setCourses(cRes.courses || [])
      })
      .finally(() => setLoading(false))
  }, [selected, viewMode])

  const refreshSnapshot = async () => {
    if (!selected) return
    setLoading(true)
    try {
      await computeSnapshot({ year: selected.year, month: selected.month })
      const tRes = viewMode === 'overall'
        ? await getTeacherEarnings({})
        : await getTeacherEarnings({ year: selected.year, month: selected.month })
      const cRes = viewMode === 'overall'
        ? await getCourseFinancials({})
        : await getCourseFinancials({ year: selected.year, month: selected.month })
      setTeachers(tRes.teachers || [])
      setCourses(cRes.courses || [])
    } catch (e) {
      // ignore
    }
    setLoading(false)
  }

  return (
    <div>
      <h2>Finances</h2>
      <p>Read-only tutor earnings and course financials for the latest month, previous months, and overall totals.</p>

      <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <label>View:</label>
        <select value={viewMode} onChange={(e) => setViewMode(e.target.value)}>
          <option value="month">Selected month</option>
          <option value="overall">Overall</option>
        </select>

        {viewMode === 'month' && (
          <>
            <label>Snapshot:</label>
            <select
              value={selected ? `${selected.year}-${selected.month}` : ''}
              onChange={(e) => {
                const v = e.target.value
                if (!v) return setSelected(null)
                const [y, m] = v.split('-').map(Number)
                setSelected({ year: y, month: m })
              }}
            >
              <option value="">Select month</option>
              {months.map((m) => (
                <option key={`${m.year}-${m.month}`} value={`${m.year}-${m.month}`}>
                  {m.year}-{String(m.month).padStart(2, '0')}
                </option>
              ))}
            </select>
          </>
        )}

        <button onClick={refreshSnapshot} disabled={viewMode === 'month' && (!selected || loading) || viewMode === 'overall' && loading}>
          Recompute snapshot
        </button>
      </div>

      {selected || viewMode === 'overall' ? (
        <div>
          <TeacherEarnings rows={teachers} loading={loading} viewMode={viewMode} selected={selected} />
          <CourseFinancials rows={courses} loading={loading} viewMode={viewMode} selected={selected} />
        </div>
      ) : (
        <p>Please select a snapshot period to view finances.</p>
      )}
    </div>
  )
}
