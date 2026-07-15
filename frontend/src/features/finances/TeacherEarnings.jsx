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
    <div style={{ marginTop: 20, padding: 16, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Teacher Earnings</h3>
        <div style={{ fontSize: 13, color: '#4b5563' }}>
          {viewMode === 'overall' ? 'Overall totals' : `${selected?.year || ''}-${String(selected?.month || '').padStart(2, '0')}`}
        </div>
      </div>
      {loading && <div>Loading...</div>}
      {!loading && rows.length === 0 && <div>No teacher earnings for this period.</div>}
      {!loading && rows.length > 0 && (
        <>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
            <div style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Total payout</div>
              <div style={{ fontWeight: 700 }}>{money(summary.totalPayout)}</div>
            </div>
            <div style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Lessons</div>
              <div style={{ fontWeight: 700 }}>{summary.lessons}</div>
            </div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Teacher</th>
                <th style={{ textAlign: 'right', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Tutor Hrs</th>
                <th style={{ textAlign: 'right', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>TA Hrs</th>
                <th style={{ textAlign: 'right', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Total Payout</th>
                <th style={{ textAlign: 'right', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Lessons</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.teacher_id}>
                  <td style={{ padding: '8px 4px', borderBottom: '1px solid #f3f4f6' }}>{r.teacher_name || r.teacher_id}</td>
                  <td style={{ textAlign: 'right', padding: '8px 4px' }}>{Number(r.tutor_hours || 0).toFixed(2)}</td>
                  <td style={{ textAlign: 'right', padding: '8px 4px' }}>{Number(r.ta_hours || 0).toFixed(2)}</td>
                  <td style={{ textAlign: 'right', padding: '8px 4px' }}>{money(r.total_payout)}</td>
                  <td style={{ textAlign: 'right', padding: '8px 4px' }}>{r.lessons_count || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
