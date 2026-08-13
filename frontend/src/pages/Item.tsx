import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Item() {
  const [items, setItems] = useState<any[]>([])
  const [form, setForm] = useState({ name: '', location: '', category: 'other', expire_at: '' })
  const [showExpiring, setShowExpiring] = useState(false)

  const load = () => {
    api('/items').then(d => setItems(d.data)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  async function add() {
    if (!form.name || !form.location) return
    const body: any = { name: form.name, location: form.location, category: form.category }
    if (form.expire_at) body.expire_at = form.expire_at
    await api('/items', { method: 'POST', body: JSON.stringify(body) })
    setForm({ name: '', location: '', category: 'other', expire_at: '' })
    load()
  }

  async function markUse(id: number) {
    await api(`/items/${id}/use`, { method: 'POST' })
    load()
  }

  async function loadExpiring() {
    const data = await api('/items/expiring?days=7')
    setItems(data.data)
    setShowExpiring(true)
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>📦 物品收纳</h2>
      <div className="card">
        <div className="card-title">添加物品</div>
        <div className="form-row">
          <input placeholder="名称" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <input placeholder="位置" value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} />
          <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
            <option value="food">食品</option>
            <option value="cosmetic">护肤品</option>
            <option value="medicine">药品</option>
            <option value="card">会员卡</option>
            <option value="coupon">优惠券</option>
            <option value="document">证件</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div className="form-row">
          <input type="datetime-local" placeholder="过期时间（可选）" value={form.expire_at} onChange={e => setForm({ ...form, expire_at: e.target.value })} />
          <button onClick={add}>添加</button>
          <button className="secondary" onClick={loadExpiring}>即将过期</button>
          <button className="secondary" onClick={() => { setShowExpiring(false); load() }}>全部</button>
        </div>
      </div>
      <div>
        {items.length === 0 ? <p style={{ color: '#999' }}>{showExpiring ? '暂无即将过期物品' : '暂无物品'}</p> : items.map(i => (
          <div key={i.id} className="list-item">
            <span>{i.name} · 📍{i.location}</span>
            <span>
              {i.expire_at && <span className="badge badge-warning" style={{ marginRight: 8 }}>⏰{i.expire_at.slice(0, 10)}</span>}
              <button style={{ padding: '2px 8px', fontSize: 12 }} onClick={() => markUse(i.id)}>使用</button>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
