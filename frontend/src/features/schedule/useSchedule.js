import { useCallback, useEffect, useState } from 'react'
import { getSchedule } from '../../services/endpoints'
import { useLessonsContext } from '../../context/LessonsContext'

/**
 * Fetch the schedule for an ISO date range.
 * Re-runs when the range changes OR when LessonsContext.version increments
 * (i.e. when the Dashboard or any other view mutates a lesson).
 */
export function useSchedule(start, end) {
  const [lessons, setLessons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { version } = useLessonsContext()

  const reload = useCallback(() => {
    setLoading(true)
    getSchedule(start, end)
      .then((d) => { setLessons(d); setError(null) })
      .catch((e) => setError(e))
      .finally(() => setLoading(false))
  }, [start, end])

  // Re-fetch when date range changes OR when global version increments
  useEffect(() => { reload() }, [reload, version])

  return { lessons, loading, error, reload }
}
