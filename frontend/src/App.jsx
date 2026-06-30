import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/layout/Layout'
import SchedulePage from './features/schedule/SchedulePage'
import LessonDashboardPage from './features/lessonDashboard/LessonDashboardPage'
import FinancesPage from './features/finances/FinancesPage'
import UrgentNewsPage from './features/urgentNews/UrgentNewsPage'
import LoginPage from './features/auth/LoginPage'
import UnauthorizedPage from './features/auth/UnauthorizedPage'
import { RequireAuth, RequireRole, RedirectIfAuthed } from './features/auth/guards'
import './App.css'

function App() {
  return (
    <Routes>
      {/* Public auth routes */}
      <Route
        path="/login"
        element={
          <RedirectIfAuthed>
            <LoginPage />
          </RedirectIfAuthed>
        }
      />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      {/* Protected application shell */}
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/schedule" replace />} />
        <Route path="/schedule" element={<SchedulePage />} />
        {/* Finances is Admin-only per Business Rules s.12 */}
        <Route
          path="/finances"
          element={
            <RequireRole roles={['Admin']}>
              <FinancesPage />
            </RequireRole>
          }
        />
        <Route path="/lessons" element={<LessonDashboardPage />} />
        <Route path="/urgent" element={<UrgentNewsPage />} />
        <Route path="*" element={<Navigate to="/schedule" replace />} />
      </Route>
    </Routes>
  )
}

export default App
