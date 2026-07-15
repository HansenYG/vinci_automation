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

  useEffect(() => {
    getFinanceMonths().then((m) => setMonths(m || [])).catch(() => setMonths([]))
  }, [])

  useEffect(() => {
    if (!selected) return
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
  }, [selected])

  const refreshSnapshot = async () => {
    if (!selected) return
    setLoading(true)
    try {
      await computeSnapshot({ year: selected.year, month: selected.month })
      const tRes = await getTeacherEarnings({ year: selected.year, month: selected.month })
      const cRes = await getCourseFinancials({ year: selected.year, month: selected.month })
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
      <p>Teacher earnings and course financials.</p>

      <div style={{ marginBottom: 12 }}>
        <label style={{ marginRight: 8 }}>Snapshot:</label>
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
        <button style={{ marginLeft: 8 }} onClick={refreshSnapshot} disabled={!selected || loading}>
          Recompute snapshot
        </button>
      </div>

      {selected ? (
        <div>
          <TeacherEarnings rows={teachers} loading={loading} />
          <CourseFinancials rows={courses} loading={loading} />
        </div>
      ) : (
        <p>Please select a snapshot period to view finances.</p>
      )}
    </div>
  )
}
