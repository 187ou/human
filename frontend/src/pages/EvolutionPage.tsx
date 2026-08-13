import { useState } from 'react'
import { api } from '../api/client'

export default function EvolutionPage() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function run(type: string) {
    setLoading(true)
    try {
      const path = type === 'online' ? '/engine/online-reflection' :
                   type === 'nightly' ? '/engine/nightly-evolution' :
                   type === 'weekly' ? '/engine/weekly-evolution' : '/evolution-advanced/risk-check'
      const body = type === 'online' ? { event_type: 'task_completed', event_data: { dimension: 'time' } } :
                   type === 'risk' ? { rule_name: 'test', rule_expr: { task_count_boost: 3 } } : {}
      const data = await api(path, { method: 'POST', body: JSON.stringify(body) })
      setResult(data.data)
    } catch (e: any) { setResult({ error: e.message }) }
    setLoading(false)
  }

  const actions = [
    { id: 'online', label: '在线反射', desc: '单次任务后微调规则', color: '#6366f1', icon: '◈' },
    { id: 'nightly', label: '夜间演化', desc: '轻量增量优化', color: '#06b6d4', icon: '◷' },
    { id: 'weekly', label: '深度演化', desc: '全量复盘规则重构', color: '#8b5cf6', icon: '◎' },
    { id: 'risk', label: '风险自检', desc: '规则安全验证拦截', color: '#f43f5e', icon: '◉' },
  ]

  return (
    <div>
      <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6 }}>◎ 自适应演化</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--sp-6)', fontSize: 14 }}>
        三层进化架构：在线即时反射 → 夜间轻量演化 → 周度深度复盘
      </p>

      <div className="grid-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--sp-4)', marginBottom: 'var(--sp-6)' }}>
        {actions.map(a => (
          <button key={a.id} onClick={() => run(a.id)} className="glass-card" style={{
            cursor: 'pointer', textAlign: 'left', border: `1px solid ${a.color}22`,
          }}>
            <div style={{ fontSize: 28, marginBottom: 8, color: a.color }}>{a.icon}</div>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{a.label}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{a.desc}</div>
          </button>
        ))}
      </div>

      {loading && (
        <div className="glass-card" style={{ textAlign: 'center', padding: 'var(--sp-8)', color: 'var(--text-muted)' }}>
          <div className="anim-fade-in" style={{ fontSize: 24, marginBottom: 8 }}>◎</div>
          演化中...
        </div>
      )}
      {result && !loading && (
        <div className="glass-card anim-scale-in">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 'var(--sp-3)' }}>演化结果</h3>
          <pre style={{ fontSize: 12, color: 'var(--text-secondary)', overflow: 'auto', maxHeight: 300, whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
