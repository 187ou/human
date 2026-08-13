import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Travel() {
  const [items, setItems] = useState<any[]>([])
  const [form, setForm] = useState({ title: '', destination: '', travel_type: 'trip', depart_time: '' })

  const load = () => api('/travels').then(d => setItems(d.data)).catch(() => {})
  useEffect(() => { load() }, [])

  async function add() {
    if (!form.title) return
    const body: any = { title: form.title, travel_type: form.travel_type }
    if (form.destination) body.destination = form.destination
    if (form.depart_time) body.depart_time = form.depart_time
    await api('/travels', { method: 'POST', body: JSON.stringify(body) })
    setForm({ title: '', destination: '', travel_type: 'trip', depart_time: '' })
    load()
  }

  async function complete(id: number) {
    await api(`/travels/${id}/complete`, { method: 'POST', body: JSON.stringify({ is_on_time: true }) })
    load()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>🚗 出行处理</h2>
      <div className="card">
        <div className="card-title">添加出行</div>
        <div className="form-row">
          <input placeholder="标题" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          <input placeholder="目的地" value={form.destination} onChange={e => setForm({ ...form, destination: e.target.value })} />
          <select value={form.travel_type} onChange={e => setForm({ ...form, travel_type: e.target.value })}>
            <option value="trip">旅行</option>
            <option value="commute">通勤</option>
            <option value="flight">航班</option>
            <option value="hotel">住宿</option>
          </select>
        </div>
        <div className="form-row">
          <input type="datetime-local" value={form.depart_time} onChange={e => setForm({ ...form, depart_time: e.target.value })} />
          <button onClick={add}>添加</button>
        </div>
      </div>
      <div>
        {items.length === 0 ? <p style={{ color: '#999' }}>暂无出行计划</p> : items.map(t => (
          <div key={t.id} className="list-item">
            <span>🚗 {t.title} → {t.destination || '未设置'}</span>
            <span>
              <span className="badge badge-info">{t.type}</span>
              <button style={{ marginLeft: 8, padding: '2px 8px', fontSize: 12 }} onClick={() => complete(t.id)}>完成</button>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
