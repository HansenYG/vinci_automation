import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/layout/Layout'
import SchedulePage from './features/schedule/SchedulePage'
import LessonDashboardPage from './features/lessonDashboard/LessonDashboardPage'
import FinancesPage from './features/finances/FinancesPage'
import UrgentNewsPage from './features/urgentNews/UrgentNewsPage'
import './App.css'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/schedule" replace />} />
        <Route path="/schedule" element={<SchedulePage />} />
        <Route path="/lessons" element={<LessonDashboardPage />} />
        <Route path="/finances" element={<FinancesPage />} />
        <Route path="/urgent" element={<UrgentNewsPage />} />
        <Route path="*" element={<Navigate to="/schedule" replace />} />
      </Route>
    </Routes>
  )
}

export default App
