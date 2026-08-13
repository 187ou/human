import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

const moduleConfig: Record<string, any> = {
  schedule: {
    title: '时间规划', icon: '◷', fields: [
      { key: 'title', label: '标题', type: 'text' },
      { key: 'start_time', label: '开始', type: 'datetime-local' },
      { key: 'end_time', label: '结束', type: 'datetime-local' },
      { key: 'category', label: '类型', type: 'select', options: ['fixed', 'flexible', 'study', 'sport'] },
    ],
    apiPath: '/schedules',
  },
  consume: {
    title: '消费记账', icon: '◉', fields: [
      { key: 'amount', label: '金额', type: 'number' },
      { key: 'category', label: '品类', type: 'select', options: ['food', 'shopping', 'transport', 'entertainment', 'study', 'rent'] },
      { key: 'merchant', label: '商家', type: 'text' },
    ],
    apiPath: '/consumes',
  },
  study: {
    title: '学习督导', icon: '◐', fields: [
      { key: 'subject', label: '学科', type: 'text' },
      { key: 'duration_minutes', label: '时长(分)', type: 'number' },
      { key: 'efficiency', label: '效率(0-1)', type: 'number' },
    ],
    apiPath: '/studies/records',
  },
  item: {
    title: '物品收纳', icon: '◑', fields: [
      { key: 'name', label: '名称', type: 'text' },
      { key: 'location', label: '位置', type: 'text' },
      { key: 'category', label: '类别', type: 'select', options: ['food', 'cosmetic', 'medicine', 'card', 'coupon', 'other'] },
      { key: 'expire_at', label: '过期时间', type: 'datetime-local' },
    ],
    apiPath: '/items',
  },
  travel: {
    title: '出行处理', icon: '◒', fields: [
      { key: 'title', label: '标题', type: 'text' },
      { key: 'destination', label: '目的地', type: 'text' },
      { key: 'travel_type', label: '类型', type: 'select', options: ['trip', 'commute', 'flight', 'hotel'] },
      { key: 'depart_time', label: '出发时间', type: 'datetime-local' },
    ],
    apiPath: '/travels',
  },
}

export default function ModulePage({ module }: { module: string }) {
  const config = moduleConfig[module]
  const [items, setItems] = useState<any[]>([])
  const [form, setForm] = useState<Record<string, string>>({})

  const load = useCallback(() => {
    api(config.apiPath).then(d => setItems(d.data || [])).catch(() => {})
  }, [config.apiPath])

  useEffect(() => { load() }, [load])

  async function add() {
    await api(config.apiPath, { method: 'POST', body: JSON.stringify(form) })
    setForm({})
    load()
  }

  if (!config) return <div>模块不存在</div>

  return (
    <div>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
        {config.icon} {config.title}
      </h1>
      <p style={{ color: '#94a3b8', marginBottom: 32 }}>
        记录你的{config.title}数据，让AI更了解你。
      </p>

      {/* 添加表单 */}
      <div className="glass-card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          {config.fields.map((f: any) => (
            <div key={f.key} style={{ flex: '1 1 150px' }}>
              <label style={{ display: 'block', fontSize: 12, color: '#94a3b8', marginBottom: 6 }}>{f.label}</label>
              {f.type === 'select' ? (
                <select className="input" value={form[f.key] || ''}
                  onChange={e => setForm({ ...form, [f.key]: e.target.value })}>
                  <option value="">选择...</option>
                  {f.options.map((o: string) => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : (
                <input className="input" type={f.type} value={form[f.key] || ''}
                  onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
              )}
            </div>
          ))}
          <button className="btn btn-primary" onClick={add}>添加</button>
        </div>
      </div>

      {/* 列表 */}
      <div>
        {items.length === 0 ? (
          <div className="glass-card" style={{ textAlign: 'center', color: '#64748b', padding: 40 }}>
            暂无记录，添加第一条吧 ✨
          </div>
        ) : items.map((item, i) => (
          <div key={i} className="list-item">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span className="tag tag-primary">{item.category || module}</span>
              <span style={{ fontWeight: 500 }}>{item.title || item.name || item.subject || `${item.amount}元`}</span>
            </div>
            <span style={{ fontSize: 13, color: '#94a3b8' }}>
              {item.start?.slice(0, 16) || item.occurred_at?.slice(0, 16) || ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
