import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { path: '/dashboard', label: '📊 概览' },
  { path: '/chat', label: '💬 对话' },
  { path: '/schedule', label: '📅 日程' },
  { path: '/consume', label: '💰 消费' },
  { path: '/item', label: '📦 物品' },
  { path: '/study', label: '📚 学习' },
  { path: '/travel', label: '🚗 出行' },
  { path: '/evolution', label: '🧬 演化' },
]

export default function MainLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{
        width: 220, background: 'linear-gradient(180deg, #1e1e2f, #2d2d44)',
        color: '#fff', position: 'fixed', height: '100vh', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '20px', borderBottom: '1px solid #3a3a55' }}>
          <h1 style={{ fontSize: 18 }}>🧠 HumanAgent</h1>
          <p style={{ fontSize: 11, color: '#888', marginTop: 3 }}>自适应生活助手</p>
        </div>
        <nav style={{ flex: 1, padding: '15px 10px', overflowY: 'auto' }}>
          {navItems.map(item => (
            <NavLink key={item.path} to={item.path} style={({ isActive }) => ({
              display: 'block', padding: '10px 15px', color: isActive ? '#fff' : '#aaa',
              borderRadius: 8, marginBottom: 4, background: isActive ? '#4a4a6a' : 'transparent',
              fontSize: 14, transition: 'all 0.2s',
            })}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div style={{ padding: 15, borderTop: '1px solid #3a3a55', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 14, color: '#ccc' }}>{user?.username}</span>
          <button onClick={() => { logout(); navigate('/') }} style={{ padding: '4px 10px', fontSize: 12, background: '#e74c3c' }}>退出</button>
        </div>
      </aside>
      <main style={{ flex: 1, marginLeft: 220, padding: 30 }}>
        <Outlet />
      </main>
    </div>
  )
}
