import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import ModulePage from './pages/ModulePage'
import EvolutionPage from './pages/EvolutionPage'
import ScenePage from './pages/ScenePage'
import { api, getToken, setToken } from './api/client'
import './styles/global.css'

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
      api('/auth/me').then(d => { setUser(d.data); setLoading(false) }).catch(() => loadRoles())
    } else { loadRoles() }
  }, [])

  async function loadRoles() {
    try { const data = await api('/auth/roles'); setRoles(data.data) } catch { setRoles([]) }
    setLoading(false)
  }

  async function selectRole(userId: number) {
    const data = await api('/auth/select', { method: 'POST', body: JSON.stringify({ user_id: userId }) })
    setToken(data.data.access_token)
    setUser(data.data.user)
  }

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: 'var(--text-muted)' }}>加载中...</div>

  if (!user) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1 }}>
        <div className="glass anim-scale-in" style={{ width: 420, padding: 48, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🧠</div>
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>HumanAgent</h1>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 28, fontSize: 14 }}>选择一个角色开始使用</p>
          <div style={{ display: 'grid', gap: 10 }}>
            {roles.map(r => (
              <button key={r.id} onClick={() => selectRole(r.id)} className="list-item" style={{ cursor: 'pointer', marginBottom: 0 }}>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.username}</span>
                <span className="tag">{r.user_type}</span>
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
      <main className="main-content" style={{ flex: 1, marginLeft: 'var(--sidebar-w)', padding: 'var(--sp-8)', transition: 'margin var(--dur-normal) var(--ease)' }}>
        <div className="anim-fade-up" key={active}>
          {renderPage()}
        </div>
      </main>
    </div>
  )
}
