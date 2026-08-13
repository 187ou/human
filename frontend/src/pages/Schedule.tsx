import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Schedule() {
  const [items, setItems] = useState<any[]>([])
  const [form, setForm] = useState({ title: '', category: 'fixed', start_time: '', end_time: '' })

  const load = () => api('/schedules').then(d => setItems(d.data)).catch(() => {})
  useEffect(() => { load() }, [])

  async function add() {
    if (!form.title || !form.start_time || !form.end_time) return
    await api('/schedules', { method: 'POST', body: JSON.stringify(form) })
    setForm({ title: '', category: 'fixed', start_time: '', end_time: '' })
    load()
  }

  async function complete(id: number) {
    await api(`/schedules/${id}/complete`, { method: 'POST', body: JSON.stringify({ quality: 4, duration_min: 50, is_delayed: false }) })
    load()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>📅 时间规划</h2>
      <div className="card">
        <div className="card-title">添加日程</div>
        <div className="form-row">
          <input placeholder="标题" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
            <option value="fixed">固定日程</option>
            <option value="flexible">弹性日程</option>
            <option value="study">学习</option>
            <option value="sport">运动</option>
          </select>
        </div>
        <div className="form-row">
          <input type="datetime-local" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })} />
          <input type="datetime-local" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })} />
          <button onClick={add}>添加</button>
        </div>
      </div>
      <div>
        {items.length === 0 ? <p style={{ color: '#999' }}>暂无日程</p> : items.map(s => (
          <div key={s.id} className="list-item">
            <span>{s.title}</span>
            <span>
              <span className="badge badge-info">{s.category}</span>
              {s.is_completed ? <span className="badge badge-success" style={{ marginLeft: 8 }}>✅ 已完成</span> : (
                <button style={{ marginLeft: 8, padding: '2px 8px', fontSize: 12 }} onClick={() => complete(s.id)}>完成</button>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
