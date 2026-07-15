import React from 'react'

function money(value) {
  return `HK$${Number(value || 0).toFixed(2)}`
}

export default function CourseFinancials({ rows = [], loading = false, viewMode = 'month', selected = null }) {
  const summary = rows.reduce((acc, row) => ({
    income: acc.income + Number(row.total_income || 0),
    expenses: acc.expenses + Number(row.total_expenses || 0),
    profitLoss: acc.profitLoss + Number(row.profit_loss || 0),
    lessons: acc.lessons + Number(row.lessons_count || 0),
  }), { income: 0, expenses: 0, profitLoss: 0, lessons: 0 })

  return (
    <div style={{ marginTop: 20, padding: 16, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Course Financials</h3>
        <div style={{ fontSize: 13, color: '#4b5563' }}>
          {viewMode === 'overall' ? 'Overall totals' : `${selected?.year || ''}-${String(selected?.month || '').padStart(2, '0')}`}
        </div>
      </div>
      {loading && <div>Loading...</div>}
      {!loading && rows.length === 0 && <div>No course financials for this period.</div>}
      {!loading && rows.length > 0 && (
        <>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
            <div style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Income</div>
              <div style={{ fontWeight: 700 }}>{money(summary.income)}</div>
            </div>
            <div style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Expenses</div>
              <div style={{ fontWeight: 700 }}>{money(summary.expenses)}</div>
            </div>
            <div style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Profit / loss</div>
              <div style={{ fontWeight: 700 }}>{money(summary.profitLoss)}</div>
            </div>
            <div style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>Lessons</div>
              <div style={{ fontWeight: 700 }}>{summary.lessons}</div>
            </div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Course</th>
                <th style={{ textAlign: 'left', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>School</th>
                <th style={{ textAlign: 'right', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Income</th>
                <th style={{ textAlign: 'right', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Expenses</th>
                <th style={{ textAlign: 'right', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Profit / Loss</th>
                <th style={{ textAlign: 'right', padding: '8px 4px', borderBottom: '1px solid #e5e7eb' }}>Lessons</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.course_id}>
                  <td style={{ padding: '8px 4px', borderBottom: '1px solid #f3f4f6' }}>{r.course_name || r.course_id}</td>
                  <td style={{ padding: '8px 4px', borderBottom: '1px solid #f3f4f6' }}>{r.school_name || ''}</td>
                  <td style={{ textAlign: 'right', padding: '8px 4px' }}>{money(r.total_income)}</td>
                  <td style={{ textAlign: 'right', padding: '8px 4px' }}>{money(r.total_expenses)}</td>
                  <td style={{ textAlign: 'right', padding: '8px 4px' }}>{money(r.profit_loss)}</td>
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
