// Typed-ish wrappers around the FastAPI backend. One place to see every call.
import api from './api'

const data = (p) => p.then((r) => r.data)

// --- Schedule / lessons ---
export const getSchedule = (start, end) => data(api.get('/api/lessons', { params: { start, end } }))
export const getLesson = (id) => data(api.get(`/api/lessons/${id}`))
export const createLesson = (body) => data(api.post('/api/lessons', body))
export const updateLesson = (id, body) => data(api.patch(`/api/lessons/${id}`, body))
export const deleteLesson = (id) => data(api.delete(`/api/lessons/${id}`))
export const getUnassigned = () => data(api.get('/api/lessons/unassigned'))
export const getOffers = (id) => data(api.get(`/api/lessons/${id}/offers`))

// --- Lesson Dashboard (paginated, filterable) ---
export const getDashboardLessons = (params = {}) =>
  data(api.get('/api/lessons/dashboard', { params }))

// --- Scheduling triggers ---
export const getAcceptedPool = (id) => data(api.get(`/api/scheduling/lessons/${id}/accepted`))
export const blastLesson = (id) => data(api.post(`/api/scheduling/lessons/${id}/blast`))
export const assignTutor = (id, teacherId, sendFiles = true, forceReassign = false) =>
  api.post(`/api/scheduling/lessons/${id}/assign`, {
    teacher_id: teacherId,
    send_files: sendFiles,
    force_reassign: forceReassign,
  })
export const resendConfirmation = (id) => data(api.post(`/api/scheduling/lessons/${id}/send-confirmation`))
export const announceLesson = (body) => data(api.post('/api/scheduling/announce-lesson', body))

// --- Reference data ---
export const getTeachers = () => data(api.get('/api/teachers'))
export const createTeacher = (body) => data(api.post('/api/teachers', body))
export const getCourses = () => data(api.get('/api/courses'))
export const createCourse = (body) => data(api.post('/api/courses', body))
export const getSchools = () => data(api.get('/api/schools'))
export const createSchool = (body) => data(api.post('/api/schools', body))

// --- Urgent news ---
export const getUrgentNews = () => data(api.get('/api/urgent-news'))

// --- Chatbot ---
export const getPresets = () => data(api.get('/api/chat/presets'))
export const sendChat = (message, history = []) => data(api.post('/api/chat', { message, history }))
export const executeAction = (operation, params = {}) => data(api.post('/api/chat/execute', { operation, params }))
export const exportUrl = (dataset) => `${api.defaults.baseURL}/api/chat/export/${dataset}`
