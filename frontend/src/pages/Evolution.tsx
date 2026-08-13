import { useEffect, useState } from 'react'
import { api } from '../api/client'

interface Rule {
  id: number
  name: string
  description: string
  dimension: string
  confidence: number
  sample_count: number
  version: number
  is_active: boolean
  priority: number
  updated_at: string
}

const dimNames: Record<string, string> = { time: '时间', consume: '消费', study: '学习', item: '物品', travel: '出行' }
const prioLabels: Record<number, string> = { 1: '低', 2: '中', 3: '高' }

export default function Evolution() {
  const [rules, setRules] = useState<Rule[]>([])
  const [lastResult, setLastResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const load = () => api('/evolution/rules').then(d => setRules(d.data)).catch(() => {})
  useEffect(() => { load() }, [])

  async function runEvolution(mode: string) {
    setLoading(true)
    try {
      const data = await api(`/evolution/run?mode=${mode}`, { method: 'POST' })
      setLastResult(data.data)
      load()
    } catch (e: any) {
      alert(`演化失败: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function toggleRule(id: number, active: boolean) {
    await api(`/evolution/rules/${id}/toggle?active=${active}`, { method: 'POST' })
    load()
  }

  async function pinRule(id: number, prio: number) {
    await api(`/evolution/rules/${id}/pin?priority=${prio}`, { method: 'POST' })
    load()
  }

  async function rollbackRule(id: number) {
    if (!confirm('确定回滚到上一版本？')) return
    await api(`/evolution/rules/${id}/rollback`, { method: 'POST' })
    load()
  }

  async function deleteRule(id: number) {
    if (!confirm('确定删除此规则？')) return
    await api(`/evolution/rules/${id}`, { method: 'DELETE' })
    load()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>🧬 自适应演化</h2>

      <div className="card">
        <p style={{ color: '#666', marginBottom: 15 }}>
          系统根据行为数据自动学习，生成专属规则。采用统计学置信度（符合样本÷总样本），最少15条数据生成正式规则。
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={() => runEvolution('incremental')} disabled={loading}>🌙 增量演化</button>
          <button onClick={() => runEvolution('full')} disabled={loading}>🔬 全量深度演化</button>
        </div>
        {lastResult && (
          <div style={{ marginTop: 15, padding: 12, background: '#f8f9fa', borderRadius: 8, fontSize: 13 }}>
            <div><strong>模式:</strong> {lastResult.mode} | <strong>规则数:</strong> {lastResult.rules_count || lastResult.rules_updated || 0}</div>
            {lastResult.prompt_evaluation && (
              <div style={{ marginTop: 4 }}>
                <strong>Prompt考核:</strong> 完成率 {(lastResult.prompt_evaluation.completion_rate * 100).toFixed(0)}% |
                超支 {lastResult.prompt_evaluation.overspend_count}次 |
                有效学习 {lastResult.prompt_evaluation.effective_study_sessions}次
                {lastResult.prompt_evaluation.should_rollback && <span style={{ color: '#e74c3c', marginLeft: 8 }}>⚠️ 建议回退</span>}
              </div>
            )}
            {lastResult.conflicts > 0 && <div style={{ color: '#f39c12' }}>冲突仲裁: {lastResult.conflicts}条</div>}
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-title">规则管理 ({rules.length}条)</div>
        {rules.length === 0 ? (
          <p style={{ color: '#999', fontSize: 14 }}>暂无规则，先积累至少15条行为数据后触发演化</p>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            {rules.map(r => (
              <div key={r.id} style={{
                padding: '12px 16px', background: r.is_active ? '#f8f9fa' : '#fafafa',
                borderRadius: 8, borderLeft: `4px solid ${r.is_active ? '#667eea' : '#ccc'}`,
                opacity: r.is_active ? 1 : 0.6,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>
                    {r.is_active ? '🟢' : '⚪'} {r.name}
                  </span>
                  <span style={{ fontSize: 12, color: '#999' }}>
                    v{r.version} · 置信度{(r.confidence * 100).toFixed(0)}% · 样本{r.sample_count}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  {dimNames[r.dimension] || r.dimension} · 优先级: {prioLabels[r.priority] || r.priority} · {r.description}
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                  <button style={{ padding: '4px 10px', fontSize: 12 }}
                    onClick={() => toggleRule(r.id, !r.is_active)}
                    className={r.is_active ? 'secondary' : 'success'}>
                    {r.is_active ? '禁用' : '启用'}
                  </button>
                  <button style={{ padding: '4px 10px', fontSize: 12 }} className="warning"
                    onClick={() => pinRule(r.id, Math.min(r.priority + 1, 3))}>置顶</button>
                  <button style={{ padding: '4px 10px', fontSize: 12 }} className="secondary"
                    onClick={() => rollbackRule(r.id)}>回滚</button>
                  <button style={{ padding: '4px 10px', fontSize: 12 }} className="danger"
                    onClick={() => deleteRule(r.id)}>删除</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
