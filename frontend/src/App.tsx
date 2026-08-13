import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import RoleSelect from './pages/RoleSelect'
import MainLayout from './components/MainLayout'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Schedule from './pages/Schedule'
import Consume from './pages/Consume'
import Item from './pages/Item'
import Study from './pages/Study'
import Travel from './pages/Travel'
import Evolution from './pages/Evolution'
import Scenarios from './pages/Scenarios'
import NotificationCenter from './components/NotificationCenter'
import QuickCommands from './components/QuickCommands'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>加载中...</div>
  if (!user) return <RoleSelect />

  return (
    <>
      <NotificationCenter />
      <QuickCommands />
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/consume" element={<Consume />} />
          <Route path="/item" element={<Item />} />
          <Route path="/study" element={<Study />} />
          <Route path="/travel" element={<Travel />} />
          <Route path="/evolution" element={<Evolution />} />
          <Route path="/scenarios" element={<Scenarios />} />
        </Route>
      </Routes>
    </>
  )
}
