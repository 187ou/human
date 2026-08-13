import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import ModulePage from './pages/ModulePage'
import EvolutionPage from './pages/EvolutionPage'
import ScenePage from './pages/ScenePage'
import { api, getToken, setToken } from './api/client'
import './styles/design-system.css'

const modules = [
  { id: 'dashboard', name: '概览', icon: '◈' },
  { id: 'schedule', name: '时间', icon: '◷' },
  { id: 'consume', name: '消费', icon: '◉' },
  { id: 'study', name: '学习', icon: '◐' },
  { id: 'item', name: '物品', icon: '◑' },
  { id: 'travel', name: '出行', icon: '◒' },
  { id: 'evolution', name: '演化', icon: '◎' },
  { id: 'scene', name: '场景', icon: '◔' },
]

export default function App() {
  const [active, setActive] = useState('dashboard')
  const [roles, setRoles] = useState<any[]>([])
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (getToken()) {
      api('/auth/me').then(d => {
        setUser(d.data)
        setLoading(false)
      }).catch(() => {
        loadRoles()
      })
    } else {
      loadRoles()
    }
  }, [])

  async function loadRoles() {
    try {
      const data = await api('/auth/roles')
      setRoles(data.data)
    } catch {
      setRoles([])
    }
    setLoading(false)
  }

  async function selectRole(userId: number) {
    const data = await api('/auth/select', { method: 'POST', body: JSON.stringify({ user_id: userId }) })
    setToken(data.data.access_token)
    setUser(data.data.user)
  }

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#94a3b8' }}>加载中...</div>

  if (!user) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1 }}>
        <div style={{ width: 480, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🧠</div>
          <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>HumanAgent</h1>
          <p style={{ color: '#94a3b8', marginBottom: 32 }}>选择一个角色开始使用</p>
          <div style={{ display: 'grid', gap: 12 }}>
            {roles.map(r => (
              <button key={r.id} onClick={() => selectRole(r.id)} className="glass-card" style={{ cursor: 'pointer', width: '100%', textAlign: 'left' }}>
                <span style={{ fontWeight: 600 }}>{r.username}</span>
                <span style={{ color: '#94a3b8', fontSize: 13, marginLeft: 12 }}>{r.user_type}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const renderPage = () => {
    if (active === 'dashboard') return <Dashboard />
    if (active === 'evolution') return <EvolutionPage />
    if (active === 'scene') return <ScenePage />
    return <ModulePage module={active} />
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', position: 'relative', zIndex: 1 }}>
      <Sidebar modules={modules} active={active} onSelect={setActive} user={user} />
      <main style={{ flex: 1, marginLeft: 240, padding: '32px 40px' }}>
        <div className="animate-fade-in" key={active}>
          {renderPage()}
        </div>
      </main>
    </div>
  )
}
