import { useState } from 'react'
import { api } from '../api/client'

export default function EvolutionPage() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function runEvolution(type: string) {
    setLoading(true)
    try {
      const path = type === 'online' ? '/engine/online-reflection' :
                   type === 'nightly' ? '/engine/nightly-evolution' :
                   type === 'weekly' ? '/engine/weekly-evolution' :
                   '/evolution-advanced/risk-check'
      const data = await api(path, {
        method: 'POST',
        body: JSON.stringify(type === 'online' ? { event_type: 'task_completed', event_data: { dimension: 'time' } } :
                          type === 'risk' ? { rule_name: 'test', rule_expr: { task_count_boost: 3 } } : {})
      })
      setResult(data.data)
    } catch (e: any) {
      setResult({ error: e.message })
    }
    setLoading(false)
  }

  const actions = [
    { id: 'online', label: '在线反射', desc: '单次任务后微调', color: '#6366f1', icon: '◈' },
    { id: 'nightly', label: '夜间演化', desc: '轻量增量优化', color: '#06b6d4', icon: '◷' },
    { id: 'weekly', label: '深度演化', desc: '全量复盘重构', color: '#8b5cf6', icon: '◎' },
    { id: 'risk', label: '风险自检', desc: '规则安全验证', color: '#f43f5e', icon: '◉' },
  ]

  return (
    <div>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
        ◎ 自适应演化
      </h1>
      <p style={{ color: '#94a3b8', marginBottom: 32 }}>
        三层进化架构：在线即时反射 → 夜间轻量演化 → 周度深度复盘
      </p>

      {/* 操作面板 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {actions.map(a => (
          <button key={a.id} className="glass-card" onClick={() => runEvolution(a.id)}
            style={{ cursor: 'pointer', textAlign: 'left', border: `1px solid ${a.color}33` }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>{a.icon}</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{a.label}</div>
            <div style={{ fontSize: 12, color: '#94a3b8' }}>{a.desc}</div>
          </button>
        ))}
      </div>

      {/* 结果 */}
      {loading && (
        <div className="glass-card" style={{ textAlign: 'center', color: '#94a3b8' }}>
          <div className="animate-pulse" style={{ fontSize: 24, marginBottom: 8 }}>◎</div>
          演化中...
        </div>
      )}
      {result && !loading && (
        <div className="glass-card">
          <h3 style={{ marginBottom: 12 }}>演化结果</h3>
          <pre style={{ fontSize: 13, color: '#94a3b8', overflow: 'auto', maxHeight: 300 }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
