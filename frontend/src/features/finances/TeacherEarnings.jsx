import React from 'react'

function money(value) {
  return `HK$${Number(value || 0).toFixed(2)}`
}

export default function TeacherEarnings({ rows = [], loading = false, viewMode = 'month', selected = null }) {
  const summary = rows.reduce((acc, row) => ({
    totalPayout: acc.totalPayout + Number(row.total_payout || 0),
    lessons: acc.lessons + Number(row.lessons_count || 0),
  }), { totalPayout: 0, lessons: 0 })

  return (
    <section className="card" style={{ padding: 18, marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 12, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>Teacher Earnings</h3>
        <span className="badge blue">{viewMode === 'overall' ? 'Overall totals' : `${selected?.year || ''}-${String(selected?.month || '').padStart(2, '0')}`}</span>
      </div>
      {loading && <div className="empty">Loading...</div>}
      {!loading && rows.length === 0 && <div className="empty">No teacher earnings for this period.</div>}
      {!loading && rows.length > 0 && (
        <>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
            <div className="ld-stat" style={{ minWidth: 140 }}>
              <div className="ld-stat__label">Total payout</div>
              <div className="ld-stat__count">{money(summary.totalPayout)}</div>
            </div>
            <div className="ld-stat" style={{ minWidth: 110 }}>
              <div className="ld-stat__label">Lessons</div>
              <div className="ld-stat__count">{summary.lessons}</div>
            </div>
          </div>
          <div className="ld-table-wrap">
            <table className="ld-table">
              <thead>
                <tr>
                  <th>Teacher</th>
                  <th style={{ textAlign: 'right' }}>Tutor Hrs</th>
                  <th style={{ textAlign: 'right' }}>TA Hrs</th>
                  <th style={{ textAlign: 'right' }}>Total Payout</th>
                  <th style={{ textAlign: 'right' }}>Lessons</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.teacher_id}>
                    <td>{r.teacher_name || r.teacher_id}</td>
                    <td style={{ textAlign: 'right' }}>{Number(r.tutor_hours || 0).toFixed(2)}</td>
                    <td style={{ textAlign: 'right' }}>{Number(r.ta_hours || 0).toFixed(2)}</td>
                    <td style={{ textAlign: 'right' }}>{money(r.total_payout)}</td>
                    <td style={{ textAlign: 'right' }}>{r.lessons_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
