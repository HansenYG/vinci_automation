import { useEffect, useState } from 'react'
import PlaceholderPage from '../../components/common/PlaceholderPage'
import { getUrgentNews } from '../../services/endpoints'

export default function UrgentNewsPage() {
  const [rows, setRows] = useState([])
  useEffect(() => { getUrgentNews().then(setRows).catch(() => setRows([])) }, [])

  return (
    <PlaceholderPage
      title="Urgent News"
      subtitle="Anything needing attention within a week."
      phase="Phase 4"
      features={[
        'Unassigned lessons within a week',
        'Tutor cancellations and reschedule requests',
        'Pulled from the urgent_news view + lesson_events audit log',
      ]}
    >
      <div className="card" style={{ padding: 20, maxWidth: 760, marginTop: 18 }}>
        <h3 style={{ marginTop: 0, fontSize: 14 }}>Live feed ({rows.length})</h3>
        {rows.map((r) => (
          <div className="pool-row" key={r.lesson_id}>
            <span>{r.lesson_code} · {r.course_name || '—'} <span className="muted">· {r.lesson_date}</span></span>
            <span className={`badge ${r.color}`}>{r.reason}</span>
          </div>
        ))}
        {rows.length === 0 && <span className="muted" style={{ fontSize: 13 }}>Nothing urgent within a week.</span>}
      </div>
    </PlaceholderPage>
  )
}
