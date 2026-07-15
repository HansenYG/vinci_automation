import React from 'react'

export default function CourseFinancials({ rows = [], loading = false }) {
  return (
    <div style={{ marginTop: 20 }}>
      <h3>Course Financials</h3>
      {loading && <div>Loading...</div>}
      {!loading && rows.length === 0 && <div>No course financials for this period.</div>}
      {!loading && rows.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left' }}>Course</th>
              <th style={{ textAlign: 'left' }}>School</th>
              <th style={{ textAlign: 'right' }}>Income</th>
              <th style={{ textAlign: 'right' }}>Expenses</th>
              <th style={{ textAlign: 'right' }}>Profit / Loss</th>
              <th style={{ textAlign: 'right' }}>Lessons</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.course_id}>
                <td>{r.course_name || r.course_id}</td>
                <td>{r.school_name || ''}</td>
                <td style={{ textAlign: 'right' }}>{Number(r.total_income || 0).toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>{Number(r.total_expenses || 0).toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>{Number(r.profit_loss || 0).toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>{r.lessons_count || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
