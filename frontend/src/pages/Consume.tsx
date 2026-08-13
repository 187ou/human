import { useEffect, useState } from 'react'
import { api } from '../api/client'

const categories = [
  { value: 'food', label: '🍜 餐饮' },
  { value: 'shopping', label: '🛒 购物' },
  { value: 'transport', label: '🚗 交通' },
  { value: 'entertainment', label: '🎮 娱乐' },
  { value: 'study', label: '📚 学习' },
  { value: 'rent', label: '🏠 房租' },
]

export default function Consume() {
  const [items, setItems] = useState<any[]>([])
  const [stats, setStats] = useState<any[]>([])
  const [form, setForm] = useState({ amount: '', category: 'food', merchant: '' })

  const month = new Date().toISOString().slice(0, 7)
  const load = () => {
    api('/consumes').then(d => setItems(d.data)).catch(() => {})
    api(`/consumes/stats?month=${month}`).then(d => setStats(d.data)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  async function add() {
    if (!form.amount) return
    await api('/consumes', { method: 'POST', body: JSON.stringify({ ...form, amount: parseFloat(form.amount) }) })
    setForm({ amount: '', category: 'food', merchant: '' })
    load()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>💰 消费记账</h2>
      <div className="card">
        <div className="card-title">记一笔</div>
        <div className="form-row">
          <input type="number" placeholder="金额" step="0.01" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} />
          <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
            {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <input placeholder="商家（可选）" value={form.merchant} onChange={e => setForm({ ...form, merchant: e.target.value })} />
          <button onClick={add}>记账</button>
        </div>
      </div>

      {stats.length > 0 && (
        <div className="card">
          <div className="card-title">本月统计</div>
          <div style={{ display: 'flex', gap: 15, flexWrap: 'wrap' }}>
            {stats.map(s => (
              <div key={s.category} style={{ background: '#f8f9fa', padding: '8px 16px', borderRadius: 8 }}>
                <span className="badge badge-info">{s.category}</span>
                <strong style={{ marginLeft: 8 }}>¥{s.total.toFixed(0)}</strong>
                <span style={{ color: '#999', fontSize: 12, marginLeft: 4 }}>({s.count}笔)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        {items.length === 0 ? <p style={{ color: '#999' }}>暂无记录</p> : items.slice(0, 20).map(c => (
          <div key={c.id} className="list-item">
            <span>{categories.find(x => x.value === c.category)?.label || c.category} {c.merchant || ''}</span>
            <span style={{ fontWeight: 600 }}>¥{c.amount.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
