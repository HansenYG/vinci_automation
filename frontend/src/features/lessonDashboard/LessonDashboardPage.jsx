import { useEffect, useState } from 'react'
import PlaceholderPage from '../../components/common/PlaceholderPage'
import { getUnassigned } from '../../services/endpoints'

export default function LessonDashboardPage() {
  const [rows, setRows] = useState([])
  useEffect(() => { getUnassigned().then(setRows).catch(() => setRows([])) }, [])

  return (
    <PlaceholderPage
      title="Lesson Dashboard"
      subtitle="Complete lesson info + direct tutor assignment."
      phase="Phase 2"
      features={[
        'Unassigned lessons sorted by closest date',
        'One-click "send urgent WhatsApp" for lessons within a week',
        'Full lesson info, Airtable-style',
        'Direct assignment of tutors who accepted the offer',
      ]}
    >
      <div className="card" style={{ padding: 20, maxWidth: 760, marginTop: 18 }}>
        <h3 style={{ marginTop: 0, fontSize: 14 }}>Live preview — unassigned lessons ({rows.length})</h3>
        <p className="muted" style={{ fontSize: 13, marginTop: 0 }}>
          Already powered by the Phase 1 API. Assignment + blast actions are testable today from the Schedule drawer.
        </p>
        {rows.slice(0, 8).map((l) => (
          <div className="pool-row" key={l.id}>
            <span>{l.lesson_code} · {l.course_name || '—'}</span>
            <span className={`badge ${l.color}`}><span className={`dot bg-${l.color}`} />{l.lesson_date}</span>
          </div>
        ))}
        {rows.length === 0 && <span className="muted" style={{ fontSize: 13 }}>No unassigned lessons.</span>}
      </div>
    </PlaceholderPage>
  )
}
