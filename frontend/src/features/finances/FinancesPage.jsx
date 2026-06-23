import PlaceholderPage from '../../components/common/PlaceholderPage'

export default function FinancesPage() {
  return (
    <PlaceholderPage
      title="Finances"
      subtitle="Teacher earnings and course financials."
      phase="Phase 3"
      features={[
        'Teacher earnings summary per month (posted on the 1st of the next month)',
        'Course financials — income and expenses, by month and all-time',
        'Uses the hourly_rate already stored on courses',
      ]}
    />
  )
}
