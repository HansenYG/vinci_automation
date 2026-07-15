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
    <section className="card" style={{ padding: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 12, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>Course Financials</h3>
        <span className="badge blue">{viewMode === 'overall' ? 'Overall totals' : `${selected?.year || ''}-${String(selected?.month || '').padStart(2, '0')}`}</span>
      </div>
      {loading && <div className="empty">Loading...</div>}
      {!loading && rows.length === 0 && <div className="empty">No course financials for this period.</div>}
      {!loading && rows.length > 0 && (
        <>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
            <div className="ld-stat" style={{ minWidth: 130 }}>
              <div className="ld-stat__label">Income</div>
              <div className="ld-stat__count">{money(summary.income)}</div>
            </div>
            <div className="ld-stat" style={{ minWidth: 130 }}>
              <div className="ld-stat__label">Expenses</div>
              <div className="ld-stat__count">{money(summary.expenses)}</div>
            </div>
            <div className="ld-stat" style={{ minWidth: 150 }}>
              <div className="ld-stat__label">Profit / loss</div>
              <div className="ld-stat__count">{money(summary.profitLoss)}</div>
            </div>
            <div className="ld-stat" style={{ minWidth: 100 }}>
              <div className="ld-stat__label">Lessons</div>
              <div className="ld-stat__count">{summary.lessons}</div>
            </div>
          </div>
          <div className="ld-table-wrap">
            <table className="ld-table">
              <thead>
                <tr>
                  <th>Course</th>
                  <th>School</th>
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
                    <td style={{ textAlign: 'right' }}>{money(r.total_income)}</td>
                    <td style={{ textAlign: 'right' }}>{money(r.total_expenses)}</td>
                    <td style={{ textAlign: 'right' }}>{money(r.profit_loss)}</td>
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
