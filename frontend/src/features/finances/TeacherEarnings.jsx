import React from 'react'

export default function TeacherEarnings({ rows = [], loading = false }) {
  return (
    <div style={{ marginTop: 20 }}>
      <h3>Teacher Earnings</h3>
      {loading && <div>Loading...</div>}
      {!loading && rows.length === 0 && <div>No teacher earnings for this period.</div>}
      {!loading && rows.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left' }}>Teacher</th>
              <th style={{ textAlign: 'right' }}>Tutor Hours</th>
              <th style={{ textAlign: 'right' }}>TA Hours</th>
              <th style={{ textAlign: 'right' }}>Tutor Payout</th>
              <th style={{ textAlign: 'right' }}>TA Payout</th>
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
                <td style={{ textAlign: 'right' }}>{Number(r.tutor_payout || 0).toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>{Number(r.ta_payout || 0).toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>{Number(r.total_payout || 0).toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>{r.lessons_count || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
