import { useAuth } from '../context/AuthContext'

const icons: Record<string, string> = { student: '🎓', worker: '💼', general: '👤' }
const typeNames: Record<string, string> = { student: '学生', worker: '职场人', general: '自由职业' }

export default function RoleSelect() {
  const { roles, selectRole } = useAuth()

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <div style={{
        background: '#fff', borderRadius: 16, padding: 40, width: 480,
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)', textAlign: 'center',
      }}>
        <h1 style={{ fontSize: 28, marginBottom: 5 }}>🧠 HumanAgent</h1>
        <p style={{ color: '#888', marginBottom: 25 }}>选择一个角色开始使用</p>
        <div style={{ display: 'grid', gap: 10 }}>
          {roles.map(r => (
            <div key={r.id} onClick={() => selectRole(r.id)} style={{
              padding: '15px 20px', border: '2px solid #eee', borderRadius: 10,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12,
              transition: 'all 0.2s',
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = '#667eea'; (e.currentTarget as HTMLElement).style.background = '#f8f9ff' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = '#eee'; (e.currentTarget as HTMLElement).style.background = '#fff' }}
            >
              <span style={{ fontSize: 28 }}>{icons[r.user_type] || '👤'}</span>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontWeight: 600, fontSize: 16 }}>{r.username}</div>
                <div style={{ fontSize: 12, color: '#999' }}>{typeNames[r.user_type] || r.user_type}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
