/**
 * LessonsContext — single source of truth for lesson data shared between
 * the Schedule Calendar and the Lesson Dashboard.
 *
 * Both views call invalidate() after any mutation so the other view
 * automatically reflects the change on its next render / focus.
 */
import { createContext, useCallback, useContext, useRef, useState } from 'react'

const LessonsContext = createContext(null)

export function LessonsProvider({ children }) {
  // A simple incrementing "version" counter.  Any component that holds a
  // derived value keyed on this number will re-fetch when it changes.
  const [version, setVersion] = useState(0)
  const invalidate = useCallback(() => setVersion((v) => v + 1), [])

  // Shared "open lesson" state — either view can open the unified drawer.
  const [openLesson, setOpenLesson] = useState(null)

  // Ref so callbacks always see the latest invalidate without re-renders
  const invalidateRef = useRef(invalidate)
  invalidateRef.current = invalidate

  return (
    <LessonsContext.Provider value={{ version, invalidate, openLesson, setOpenLesson }}>
      {children}
    </LessonsContext.Provider>
  )
}

export function useLessonsContext() {
  const ctx = useContext(LessonsContext)
  if (!ctx) throw new Error('useLessonsContext must be used inside <LessonsProvider>')
  return ctx
}
