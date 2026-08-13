import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

interface ItemRecord {
  id: number
  name: string
  category: string
  location_path: string
  expire_at: string | null
  is_idle: boolean
  recommendation: string | null
  last_used_at: string | null
}

interface ExpirationAlert {
  item_id: number
  name: string
  status: string
  days_left: number
  message: string
  recommendation?: string
}

interface IdleAlert {
  id: number
  item_id: number
  alert_type: string
  message: string
  suggestion: string
}

interface ItemSummary {
  total: number
  expiring_15d: number
  expiring_7d: number
  expired: number
  idle: number
  categories: Record<string, number>
}

const categories = [
  { value: 'food', label: '🍜 食品' },
  { value: 'cosmetic', label: '💄 美妆' },
  { value: 'medicine', label: '💊 药品' },
  { value: 'card', label: '💳 会员卡' },
  { value: 'coupon', label: '🎫 优惠券' },
  { value: 'document', label: '📄 证件' },
  { value: 'other', label: '📌 其他' },
]

const locationExamples = [
  'MyHome / Kitchen / Fridge / Top',
  'MyHome / Kitchen / Cabinet / Shelf1',
  'MyHome / Bathroom / Cabinet',
  'MyHome / Bedroom / Wardrobe / Drawer',
]

export default function Item() {
  const [items, setItems] = useState<ItemRecord[]>([])
  const [alerts, setAlerts] = useState<ExpirationAlert[]>([])
  const [idleAlerts, setIdleAlerts] = useState<IdleAlert[]>([])
  const [summary, setSummary] = useState<ItemSummary | null>(null)
  const [form, setForm] = useState({ name: '', category: 'food', location_path: '', expire_at: '', expire_remind_days: 15, second_remind_days: 7 })
  const [searchKeyword, setSearchKeyword] = useState('')
  const [showAlerts, setShowAlerts] = useState(false)

  const load = useCallback(() => {
    const url = searchKeyword ? `/items/search?keyword=${encodeURIComponent(searchKeyword)}` : '/items'
    api(url).then(d => setItems(d.data)).catch(() => {})
    api('/items/summary').then(d => setSummary(d.data)).catch(() => {})
    api('/items/alerts/idle').then(d => setIdleAlerts(d.data)).catch(() => {})
  }, [searchKeyword])

  useEffect(() => { load() }, [load])

  async function add() {
    if (!form.name) return
    const body: any = { ...form }
    if (!body.expire_at) delete body.expire_at
    await api('/items', { method: 'POST', body: JSON.stringify(body) })
    setForm({ name: '', category: 'food', location_path: '', expire_at: '', expire_remind_days: 15, second_remind_days: 7 })
    load()
  }

  async function useItem(id: number) {
    await api(`/items/${id}/use`, { method: 'POST' })
    load()
  }

  async function checkAlerts() {
    const data = await api('/items/alerts/expiration')
    setAlerts(data.data)
    setShowAlerts(true)
    load()
  }

  async function detectIdle() {
    await api('/items/detect-idle', { method: 'POST' })
    load()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>📦 物品收纳</h2>

      {/* 总览 */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginBottom: 20 }}>
          <div className="card" style={{ textAlign: 'center', marginBottom: 0 }}>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{summary.total}</div>
            <div style={{ fontSize: 12, color: '#999' }}>总物品</div>
          </div>
          <div className="card" style={{ textAlign: 'center', marginBottom: 0, borderTop: '3px solid #f39c12' }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#f39c12' }}>{summary.expiring_15d}</div>
            <div style={{ fontSize: 12, color: '#999' }}>15天内过期</div>
          </div>
          <div className="card" style={{ textAlign: 'center', marginBottom: 0, borderTop: '3px solid #e74c3c' }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#e74c3c' }}>{summary.expiring_7d}</div>
            <div style={{ fontSize: 12, color: '#999' }}>7天内过期</div>
          </div>
          <div className="card" style={{ textAlign: 'center', marginBottom: 0, borderTop: '3px solid #95a5a6' }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#95a5a6' }}>{summary.expired}</div>
            <div style={{ fontSize: 12, color: '#999' }}>已过期</div>
          </div>
          <div className="card" style={{ textAlign: 'center', marginBottom: 0, borderTop: '3px solid #8e44ad' }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#8e44ad' }}>{summary.idle}</div>
            <div style={{ fontSize: 12, color: '#999' }}>闲置物品</div>
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="card">
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={checkAlerts}>🔔 临期预警检查</button>
          <button className="secondary" onClick={detectIdle}>🔍 闲置检测</button>
          <button className="secondary" onClick={() => setShowAlerts(!showAlerts)}>
            {showAlerts ? '隐藏预警' : `查看预警 (${alerts.length})`}
          </button>
        </div>
      </div>

      {/* 临期预警 */}
      {showAlerts && alerts.length > 0 && (
        <div className="card" style={{ borderLeft: '4px solid #e74c3c' }}>
          <div className="card-title">临期预警</div>
          {alerts.map((a, i) => (
            <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #eee' }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>
                <span className={`badge ${a.status === 'critical' ? 'badge-danger' : a.status === 'expired' ? 'badge-danger' : 'badge-warning'}`}>
                  {a.status === 'critical' ? '紧急' : a.status === 'expired' ? '已过期' : '提醒'}
                </span>
                <span style={{ marginLeft: 8 }}>{a.message}</span>
              </div>
              {a.recommendation && (
                <div style={{ fontSize: 13, color: '#666', marginTop: 4, paddingLeft: 8 }}>
                  💡 {a.recommendation}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 闲置提醒 */}
      {idleAlerts.length > 0 && (
        <div className="card" style={{ borderLeft: '4px solid #8e44ad' }}>
          <div className="card-title">闲置提醒</div>
          {idleAlerts.map(a => (
            <div key={a.id} style={{ padding: '8px 0', borderBottom: '1px solid #eee' }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>
                <span className={`badge ${a.alert_type === 'duplicate_hoarding' ? 'badge-danger' : 'badge-warning'}`}>
                  {a.alert_type === 'duplicate_hoarding' ? '重复囤货' : '闲置'}
                </span>
                <span style={{ marginLeft: 8 }}>{a.message}</span>
              </div>
              <div style={{ fontSize: 13, color: '#666', marginTop: 4, paddingLeft: 8 }}>
                💡 {a.suggestion}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 添加物品 */}
      <div className="card">
        <div className="card-title">添加物品</div>
        <div className="form-row">
          <input placeholder="名称" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
            {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div className="form-row">
          <input placeholder="位置路径 (如: MyHome/Kitchen/Fridge)" value={form.location_path}
            onChange={e => setForm({ ...form, location_path: e.target.value })} style={{ flex: 2 }} />
          <input type="datetime-local" value={form.expire_at} onChange={e => setForm({ ...form, expire_at: e.target.value })} />
        </div>
        <div className="form-row">
          <label style={{ fontSize: 13, color: '#666' }}>
            初次提醒
            <input type="number" value={form.expire_remind_days} onChange={e => setForm({ ...form, expire_remind_days: parseInt(e.target.value) })} style={{ width: 60, marginLeft: 6 }} />
            天前
          </label>
          <label style={{ fontSize: 13, color: '#666' }}>
            二次提醒
            <input type="number" value={form.second_remind_days} onChange={e => setForm({ ...form, second_remind_days: parseInt(e.target.value) })} style={{ width: 60, marginLeft: 6 }} />
            天前
          </label>
          <button onClick={add}>添加</button>
        </div>
        <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
          常用位置: {locationExamples.map((loc, i) => (
            <span key={i} onClick={() => setForm({ ...form, location_path: loc })} style={{ cursor: 'pointer', color: '#667eea', marginRight: 10 }}>{loc}</span>
          ))}
        </div>
      </div>

      {/* 搜索 */}
      <div className="card">
        <div className="form-row">
          <input placeholder="按位置搜索..." value={searchKeyword} onChange={e => setSearchKeyword(e.target.value)} style={{ flex: 1 }} />
          {searchKeyword && <button className="secondary" onClick={() => setSearchKeyword('')}>清除</button>}
        </div>
      </div>

      {/* 物品列表 */}
      <div>
        <h3 style={{ marginBottom: 10, fontSize: 16 }}>物品列表 ({items.length})</h3>
        {items.length === 0 ? <p style={{ color: '#999' }}>暂无物品</p> : items.map(i => (
          <div key={i.id} className="list-item" style={{ opacity: i.is_idle ? 0.6 : 1 }}>
            <span>
              {categories.find(c => c.value === i.category)?.label || i.category} {i.name}
              {i.is_idle && <span className="badge badge-warning" style={{ marginLeft: 6 }}>闲置</span>}
            </span>
            <span>
              {i.expire_at && (
                <span className="badge badge-warning" style={{ marginRight: 6 }}>
                  ⏰{Math.ceil((new Date(i.expire_at).getTime() - Date.now()) / 86400000)}天
                </span>
              )}
              <span style={{ fontSize: 12, color: '#999', marginRight: 8 }}>{i.location_path || '未设置'}</span>
              <button style={{ padding: '2px 8px', fontSize: 12 }} onClick={() => useItem(i.id)}>使用</button>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
