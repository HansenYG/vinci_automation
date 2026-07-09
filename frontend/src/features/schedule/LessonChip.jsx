import { fmtTime } from './dates'

export default function LessonChip({ lesson, size = 'sm', onClick }) {
  const color = lesson.color || 'grey'
  return (
    <button className={`chip ${color}${size === 'lg' ? ' chip--lg' : ''}`} onClick={(e) => { e.stopPropagation(); onClick(lesson) }}>
      <span className={`dot bg-${color}`} />
      <span className="chip__body">
        {lesson.start_time && <span className="chip__time">{fmtTime(lesson.start_time)}</span>}
        <span className="chip__line">{lesson.course_name || lesson.lesson_code || 'Lesson'}</span>
        {lesson.school_name && <span className="chip__line chip__school">{lesson.school_name}</span>}
      </span>
    </button>
  )
}
