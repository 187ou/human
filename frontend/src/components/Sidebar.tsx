interface Props {
  modules: { id: string; name: string; icon: string }[]
  active: string
  onSelect: (id: string) => void
  user?: any
}

export default function Sidebar({ modules, active, onSelect, user }: Props) {
  return (
    <aside style={{
      width: 240,
      position: 'fixed',
      height: '100vh',
      background: 'rgba(15, 15, 26, 0.8)',
      backdropFilter: 'blur(20px)',
      borderRight: '1px solid rgba(255,255,255,0.06)',
      display: 'flex',
      flexDirection: 'column',
      padding: '24px 0',
      zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{ padding: '0 24px', marginBottom: 40 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}>
          <div style={{
            width: 40,
            height: 40,
            borderRadius: 12,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 20,
            boxShadow: '0 4px 12px rgba(99,102,241,0.3)',
          }}>◈</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16, color: '#f8fafc' }}>HumanAgent</div>
            <div style={{ fontSize: 11, color: '#64748b' }}>自适应生活助手</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '0 12px' }}>
        {modules.map(m => (
          <button
            key={m.id}
            onClick={() => onSelect(m.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              width: '100%',
              padding: '12px 16px',
              marginBottom: 4,
              background: active === m.id ? 'rgba(99,102,241,0.15)' : 'transparent',
              border: '1px solid ' + (active === m.id ? 'rgba(99,102,241,0.3)' : 'transparent'),
              borderRadius: 12,
              color: active === m.id ? '#818cf8' : '#94a3b8',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: active === m.id ? 600 : 400,
              transition: 'all 0.2s',
              fontFamily: 'inherit',
            }}
          >
            <span style={{ fontSize: 18 }}>{m.icon}</span>
            <span>{m.name}</span>
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '0 24px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <div style={{ width: 24, height: 24, borderRadius: 12, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>👤</div>
          <span style={{ fontSize: 13, color: '#94a3b8' }}>{user?.username || '用户'}</span>
        </div>
        <div style={{ fontSize: 11, color: '#64748b', textAlign: 'center' }}>
          v0.1.0 · 自演化引擎运行中
        </div>
      </div>
    </aside>
  )
}
