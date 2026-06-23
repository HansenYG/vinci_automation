import { useCallback, useEffect, useState } from 'react'
import { getSchedule } from '../../services/endpoints'

// Fetch the schedule for an ISO date range; re-runs when the range changes.
export function useSchedule(start, end) {
  const [lessons, setLessons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const reload = useCallback(() => {
    setLoading(true)
    getSchedule(start, end)
      .then((d) => { setLessons(d); setError(null) })
      .catch((e) => setError(e))
      .finally(() => setLoading(false))
  }, [start, end])

  useEffect(() => { reload() }, [reload])

  return { lessons, loading, error, reload }
}
