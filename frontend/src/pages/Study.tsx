import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Study() {
  const [records, setRecords] = useState<any[]>([])
  const [stats, setStats] = useState<any[]>([])
  const [form, setForm] = useState({ subject: '', duration_minutes: '', efficiency: '', is_delayed: false })

  const load = () => {
    api('/studies/stats').then(d => setStats(d.data)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  async function add() {
    if (!form.subject || !form.duration_minutes) return
    await api('/studies/records', { method: 'POST', body: JSON.stringify({
      subject: form.subject,
      duration_minutes: parseInt(form.duration_minutes),
      efficiency: parseFloat(form.efficiency) || null,
      is_delayed: form.is_delayed,
    }) })
    setForm({ subject: '', duration_minutes: '', efficiency: '', is_delayed: false })
    load()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>📚 学习督导</h2>
      <div className="card">
        <div className="card-title">记录学习</div>
        <div className="form-row">
          <input placeholder="学科/内容" value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })} />
          <input type="number" placeholder="时长（分钟）" value={form.duration_minutes} onChange={e => setForm({ ...form, duration_minutes: e.target.value })} />
          <input type="number" placeholder="效率 0-1" step="0.1" min="0" max="1" value={form.efficiency} onChange={e => setForm({ ...form, efficiency: e.target.value })} />
        </div>
        <div className="form-row">
          <label style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 14, color: '#666' }}>
            <input type="checkbox" checked={form.is_delayed} onChange={e => setForm({ ...form, is_delayed: e.target.checked })} />
            是否拖延后完成
          </label>
          <button onClick={add}>记录</button>
        </div>
      </div>

      <div>
        {stats.length === 0 ? <p style={{ color: '#999' }}>暂无学习记录</p> : stats.map(s => (
          <div key={s.subject} className="list-item">
            <span>📚 {s.subject}</span>
            <span>
              <strong>{s.total_minutes}分钟</strong>
              <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>({s.sessions}次)</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
