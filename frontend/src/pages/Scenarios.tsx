import { useState } from 'react'
import { api } from '../api/client'

export default function Scenarios() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function runScenario(type: string) {
    setLoading(true)
    try {
      let data
      if (type === 'trip') {
        data = await api('/scenarios/trip', { method: 'POST', body: JSON.stringify({
          destination: 'Hangzhou',
          depart_time: '2026-08-20T08:00:00',
          arrive_time: '2026-08-22T18:00:00',
          budget: 1000,
        }) })
      } else if (type === 'exam') {
        data = await api('/scenarios/exam-prep', { method: 'POST', body: JSON.stringify({
          subject: 'math',
          exam_date: '2026-09-01',
          daily_hours: 8,
        }) })
      } else if (type === 'sick') {
        data = await api('/scenarios/sick-rest', { method: 'POST', body: JSON.stringify({
          rest_days: 3,
          symptoms: 'fever',
        }) })
      }
      setResult(data.data)
    } catch (e: any) {
      alert(`错误: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const scenarios = [
    {
      id: 'trip',
      icon: '🏖️',
      title: '短途出游',
      desc: '出行规划 → 清空周末日程 → 预留预算 → 行李清单 → 顺延学习',
      color: '#27ae60',
    },
    {
      id: 'exam',
      icon: '📝',
      title: '备考冲刺',
      desc: '上调学习任务 → 压缩娱乐日程 → 缩减娱乐预算',
      color: '#667eea',
    },
    {
      id: 'sick',
      icon: '🤒',
      title: '生病休养',
      desc: '暂停学习工作 → 调低饮食预算 → 延后全部待办',
      color: '#e74c3c',
    },
  ]

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>🔗 跨Agent场景联动</h2>
      <p style={{ color: '#666', marginBottom: 20 }}>
        一键触发多智能体协同，自动完成跨模块的联动调整
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 15, marginBottom: 20 }}>
        {scenarios.map(s => (
          <div key={s.id} className="card" style={{ borderTop: `4px solid ${s.color}`, marginBottom: 0, cursor: 'pointer' }}
            onClick={() => !loading && runScenario(s.id)}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>{s.icon}</div>
            <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 6 }}>{s.title}</div>
            <div style={{ fontSize: 12, color: '#666', lineHeight: 1.5 }}>{s.desc}</div>
            <button style={{ marginTop: 12, width: '100%' }} disabled={loading}>
              {loading ? '执行中...' : '一键触发'}
            </button>
          </div>
        ))}
      </div>

      {result && (
        <div className="card" style={{ borderLeft: '4px solid #27ae60' }}>
          <div className="card-title">执行结果</div>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>{result.summary}</div>
          <div style={{ display: 'grid', gap: 6 }}>
            {result.steps.map((step: any, i: number) => (
              <div key={i} style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge badge-success">✓</span>
                <strong>{step.step}</strong>
                <span style={{ color: '#999' }}>
                  {Object.entries(step).filter(([k]) => k !== 'step' && k !== 'status').map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
