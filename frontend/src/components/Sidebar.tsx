interface Props {
  modules: { id: string; name: string; icon: string }[]
  active: string
  onSelect: (id: string) => void
  user?: any
}

export default function Sidebar({ modules, active, onSelect, user }: Props) {
  return (
    <aside className="sidebar" style={{
      width: 'var(--sidebar-w)',
      position: 'fixed',
      height: '100vh',
      left: 0,
      top: 0,
      zIndex: 100,
      background: 'rgba(255,255,255,0.72)',
      backdropFilter: 'blur(24px) saturate(1.8)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      padding: '20px 0',
      transition: 'transform var(--dur-normal) var(--ease)',
    }}>
      {/* Logo */}
      <div style={{ padding: '0 20px', marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 'var(--r-md)',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, color: 'white',
            boxShadow: '0 4px 12px var(--primary-glow)',
          }}>◈</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>HumanAgent</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>自适应生活助手</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '0 12px', overflowY: 'auto' }}>
        {modules.map(m => (
          <button key={m.id} onClick={() => onSelect(m.id)} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            width: '100%', padding: '10px 14px', marginBottom: 2,
            background: active === m.id ? 'var(--primary-soft)' : 'transparent',
            border: '1px solid ' + (active === m.id ? 'var(--border-accent)' : 'transparent'),
            borderRadius: 'var(--r-md)',
            color: active === m.id ? 'var(--primary)' : 'var(--text-secondary)',
            cursor: 'pointer', fontSize: 13,
            fontWeight: active === m.id ? 600 : 400,
            transition: 'all var(--dur-fast) var(--ease)',
            fontFamily: 'inherit',
          }}
            onMouseEnter={e => { if (active !== m.id) { e.currentTarget.style.background = 'var(--bg-elevated)'; } }}
            onMouseLeave={e => { if (active !== m.id) { e.currentTarget.style.background = 'transparent'; } }}
          >
            <span style={{
              width: 22, height: 22, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, flexShrink: 0,
            }}>{m.icon}</span>
            <span>{m.name}</span>
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '0 20px', borderTop: '1px solid var(--border)', paddingTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <div style={{
            width: 24, height: 24, borderRadius: 'var(--r-full)',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, color: 'white',
          }}>👤</div>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{user?.username || '用户'}</span>
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'center' }}>
          v0.1.0 · 自演化引擎运行中
        </div>
      </div>
    </aside>
  )
}
