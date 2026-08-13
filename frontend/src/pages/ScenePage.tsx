import { useState } from 'react'
import { api } from '../api/client'

const scenes = [
  { id: 'daily', label: '日常', icon: '🏠', color: '#6366f1', desc: '正常工作学习' },
  { id: 'exam', label: '备考', icon: '📝', color: '#8b5cf6', desc: '学习权重×3' },
  { id: 'travel', label: '出差', icon: '✈️', color: '#06b6d4', desc: '出行优先' },
  { id: 'vacation', label: '假期', icon: '🏖️', color: '#10b981', desc: '娱乐权重×2' },
  { id: 'sick', label: '生病', icon: '🤒', color: '#f43f5e', desc: '休息为主' },
  { id: 'overtime', label: '加班', icon: '💼', color: '#f59e0b', desc: '工作优先' },
]

export default function ScenePage() {
  const [current, setCurrent] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function switchScene(id: string) {
    setLoading(true)
    try { await api('/fsm/switch-state', { method: 'POST', body: JSON.stringify({ new_state: id }) }); setCurrent(id) } catch { /* */ }
    setLoading(false)
  }

  return (
    <div>
      <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>◔ 场景联动</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--sp-6)', fontSize: 14 }}>
        切换生活状态，全模块自动适配。一次切换，全局联动。
      </p>

      <div className="grid-3" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--sp-4)' }}>
        {scenes.map(s => (
          <button key={s.id} onClick={() => switchScene(s.id)} className="glass-card" style={{
            cursor: 'pointer', textAlign: 'center', padding: 'var(--sp-8) var(--sp-5)',
            border: current === s.id ? `2px solid ${s.color}` : '1px solid var(--border)',
            background: current === s.id ? `${s.color}08` : undefined,
          }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>{s.icon}</div>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.desc}</div>
            {current === s.id && <div style={{ marginTop: 12 }}><span className="tag tag-primary">当前状态</span></div>}
          </button>
        ))}
      </div>

      {loading && (
        <div className="glass-card" style={{ marginTop: 'var(--sp-4)', textAlign: 'center', color: 'var(--text-muted)', padding: 'var(--sp-5)' }}>
          切换中，全模块适配...
        </div>
      )}
    </div>
  )
}
