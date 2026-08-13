import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

const moduleConfig: Record<string, any> = {
  schedule: { title: '时间规划', icon: '◷', tabs: ['日程列表', '添加日程', '冲突检测', '碎片时间', '突发场景'] },
  consume: { title: '消费记账', icon: '◉', tabs: ['记录列表', '记一笔', '预算管理', '统计分析', '账单导入'] },
  study: { title: '学习督导', icon: '◐', tabs: ['学习记录', '记录学习', '知识点', '错题本', '学习统计'] },
  item: { title: '物品收纳', icon: '◑', tabs: ['物品列表', '添加物品', '临期预警', '闲置物品', '位置管理'] },
  travel: { title: '出行处理', icon: '◒', tabs: ['出行计划', '添加出行', '行李清单', '天气查询', '开销预估'] },
}

export default function ModulePage({ module }: { module: string }) {
  const config = moduleConfig[module]
  const [activeTab, setActiveTab] = useState(0)

  if (!config) return <div className="empty"><div className="empty-icon">?</div><div>模块不存在</div></div>

  const renderTab = () => {
    const tabName = config.tabs[activeTab]
    switch (module) {
      case 'schedule': return <ScheduleTab tab={tabName} />
      case 'consume': return <ConsumeTab tab={tabName} />
      case 'study': return <StudyTab tab={tabName} />
      case 'item': return <ItemTab tab={tabName} />
      case 'travel': return <TravelTab tab={tabName} />
      default: return null
    }
  }

  return (
    <div>
      <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6, color: 'var(--text-primary)' }}>{config.icon} {config.title}</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--sp-6)', fontSize: 14 }}>管理你的{config.title}数据，智能分析助力高效生活</p>

      <div className="tabs" style={{ display: 'flex', gap: 'var(--sp-2)', marginBottom: 'var(--sp-5)', flexWrap: 'wrap' }}>
        {config.tabs.map((tab: string, i: number) => (
          <button key={i} onClick={() => setActiveTab(i)} className="btn" style={{
            background: activeTab === i ? 'var(--primary)' : 'var(--bg-frosted)',
            color: activeTab === i ? 'white' : 'var(--text-secondary)',
            boxShadow: activeTab === i ? '0 4px 12px var(--primary-glow)' : 'none',
            borderColor: activeTab !== i ? 'var(--border)' : 'transparent',
          }}>{tab}</button>
        ))}
      </div>

      <div className="glass-card" style={{ minHeight: 400 }}>
        {renderTab()}
      </div>
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return <div className="empty"><div className="empty-icon">○</div><div>{text}</div></div>
}

function getCategoryColor(cat: string): string {
  const colors: Record<string, string> = { food: '#f59e0b', shopping: '#f43f5e', transport: '#06b6d4', entertainment: '#8b5cf6', study: '#6366f1', rent: '#10b981' }
  return colors[cat] || '#94a3b8'
}

/* ==================== 时间规划 ==================== */
function ScheduleTab({ tab }: any) {
  const [items, setItems] = useState<any[]>([])
  const [conflicts, setConflicts] = useState<any[]>([])
  const [slots, setSlots] = useState<any[]>([])
  const [form, setForm] = useState<any>({})
  const [loading, setLoading] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      if (tab === '冲突检测') { const d = await api('/schedules/conflicts'); setConflicts(Array.isArray(d.data) ? d.data : []) }
      else if (tab === '碎片时间') { const d = await api('/schedules/fragment-slots'); setSlots(Array.isArray(d.data) ? d.data : []) }
      else if (tab === '日程列表') { const d = await api('/schedules'); setItems(Array.isArray(d.data) ? d.data : []) }
    } catch { /* ignore */ }
    setLoading(false)
  }, [tab])

  useEffect(() => { if (['日程列表', '冲突检测', '碎片时间'].includes(tab)) loadData() }, [tab, loadData])

  async function addSchedule() {
    try { await api('/schedules', { method: 'POST', body: JSON.stringify(form) }); setForm({}); loadData() } catch { /* */ }
  }
  async function complete(id: number) {
    try { await api(`/schedules/${id}/complete`, { method: 'POST', body: JSON.stringify({ quality: 4, duration_min: 50, is_delayed: false }) }); loadData() } catch { /* */ }
  }

  if (loading) return <Empty text="加载中..." />

  if (tab === '日程列表') {
    return <div>{items.length === 0 ? <Empty text="暂无日程" /> : items.map((s: any, i: number) => (
      <div key={i} className="list-item">
        <div><span className="tag tag-primary">{s.category}</span><span style={{ marginLeft: 8, fontWeight: 500 }}>{s.title}</span>{s.is_completed && <span className="tag tag-success" style={{ marginLeft: 8 }}>已完成</span>}</div>
        <div><span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 12 }}>{s.start?.slice(5, 16)}</span>{!s.is_completed && <button className="btn btn-ghost" style={{ padding: '2px 12px', fontSize: 12 }} onClick={() => complete(s.id)}>完成</button>}</div>
      </div>
    ))}</div>
  }

  if (tab === '添加日程') {
    return (
      <div style={{ maxWidth: 500 }}><div style={{ display: 'grid', gap: 12 }}>
        <input className="input" placeholder="日程标题" value={form.title || ''} onChange={e => setForm({ ...form, title: e.target.value })} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <input className="input" type="datetime-local" value={form.start_time || ''} onChange={e => setForm({ ...form, start_time: e.target.value })} />
          <input className="input" type="datetime-local" value={form.end_time || ''} onChange={e => setForm({ ...form, end_time: e.target.value })} />
        </div>
        <select className="input" value={form.category || ''} onChange={e => setForm({ ...form, category: e.target.value })}>
          <option value="">选择类型</option><option value="fixed">固定日程</option><option value="flexible">弹性日程</option><option value="study">学习</option><option value="sport">运动</option>
        </select>
        <button className="btn btn-primary" onClick={addSchedule}>添加日程</button>
      </div></div>
    )
  }

  if (tab === '冲突检测') {
    return <div>{conflicts.length === 0 ? <Empty text="无时间冲突 ✓" /> : conflicts.map((c: any, i: number) => (
      <div key={i} className="list-item" style={{ borderColor: 'rgba(244,63,94,0.2)' }}>
        <div><span className="tag tag-danger">冲突</span><span style={{ marginLeft: 8 }}>「{c.schedule_a?.title}」与「{c.schedule_b?.title}」</span></div>
        <span className="tag tag-warning">重叠{c.overlap_minutes}分钟</span>
      </div>
    ))}</div>
  }

  if (tab === '碎片时间') {
    return <div>{slots.length === 0 ? <Empty text="暂无碎片时间数据" /> : slots.map((s: any, i: number) => (
      <div key={i} className="list-item">
        <div><span className="tag tag-success">{s.slot_type || '空闲'}</span><span style={{ marginLeft: 8 }}>{s.start?.slice(11, 16)} - {s.end?.slice(11, 16)}</span></div>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{Math.round(s.minutes)}分钟可用</span>
      </div>
    ))}</div>
  }

  if (tab === '突发场景') {
    async function emergency(action: string) { try { await api(`/schedules/emergency/${action}`, { method: 'POST', body: JSON.stringify({ reason: action }) }) } catch { /* */ } }
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {[{ action: 'pause', icon: '🤒', title: '生病-暂停', desc: '暂停所有未来日程' }, { action: 'postpone', icon: '💼', title: '加班-顺延', desc: '所有日程延后2小时' }, { action: 'resume', icon: '✅', title: '恢复全部', desc: '恢复暂停的日程' }].map(e => (
          <div key={e.action} className="glass-card" style={{ textAlign: 'center', cursor: 'pointer' }} onClick={() => emergency(e.action)}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>{e.icon}</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{e.title}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{e.desc}</div>
          </div>
        ))}
      </div>
    )
  }
  return null
}

/* ==================== 消费记账 ==================== */
function ConsumeTab({ tab }: any) {
  const [items, setItems] = useState<any[]>([])
  const [budgets, setBudgets] = useState<any[]>([])
  const [stats, setStats] = useState<any[]>([])
  const [form, setForm] = useState<any>({})
  const [csv, setCsv] = useState('')
  const [source, setSource] = useState('wechat')
  const [loading, setLoading] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      if (tab === '记录列表') { const d = await api('/consumes?month=2026-08'); setItems(Array.isArray(d.data) ? d.data : []) }
      else if (tab === '预算管理') { const d = await api('/consumes/budget/status'); setBudgets(Array.isArray(d.data) ? d.data : []) }
      else if (tab === '统计分析') { const d = await api('/consumes/stats?month=2026-08'); setStats(Array.isArray(d.data) ? d.data : []) }
    } catch { /* */ }
    setLoading(false)
  }, [tab])

  useEffect(() => { if (['记录列表', '预算管理', '统计分析'].includes(tab)) loadData() }, [tab, loadData])

  async function addRecord() { try { await api('/consumes', { method: 'POST', body: JSON.stringify({ ...form, amount: parseFloat(form.amount) }) }); setForm({}); loadData() } catch { /* */ } }
  async function importBill() { try { await api('/consumes/import', { method: 'POST', body: JSON.stringify({ content: csv, source }) }); setCsv(''); loadData() } catch { /* */ } }

  if (loading) return <Empty text="加载中..." />

  if (tab === '记录列表') {
    return <div>{items.length === 0 ? <Empty text="暂无消费记录" /> : items.slice(0, 20).map((c: any, i: number) => (
      <div key={i} className="list-item">
        <div><span className="tag" style={{ color: getCategoryColor(c.category) }}>{c.category}</span><span style={{ marginLeft: 8 }}>{c.merchant || '-'}</span>{c.is_impulse && <span className="tag tag-danger" style={{ marginLeft: 8 }}>冲动</span>}</div>
        <span style={{ fontWeight: 600, color: '#f43f5e' }}>¥{c.amount.toFixed(2)}</span>
      </div>
    ))}</div>
  }

  if (tab === '记一笔') {
    return (
      <div style={{ maxWidth: 500 }}><div style={{ display: 'grid', gap: 12 }}>
        <input className="input" type="number" placeholder="金额" value={form.amount || ''} onChange={e => setForm({ ...form, amount: e.target.value })} />
        <select className="input" value={form.category || ''} onChange={e => setForm({ ...form, category: e.target.value })}>
          <option value="">选择品类</option><option value="food">🍜 餐饮</option><option value="shopping">🛒 购物</option><option value="transport">🚗 交通</option><option value="entertainment">🎮 娱乐</option><option value="study">📚 学习</option>
        </select>
        <input className="input" placeholder="商家（可选）" value={form.merchant || ''} onChange={e => setForm({ ...form, merchant: e.target.value })} />
        <button className="btn btn-primary" onClick={addRecord}>记账</button>
      </div></div>
    )
  }

  if (tab === '预算管理') {
    return <div>{budgets.length === 0 ? <Empty text="暂无预算设置" /> : budgets.map((b: any, i: number) => (
      <div key={i} style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 13 }}>
          <span>{b.category}</span>
          <span style={{ color: b.percentage > 80 ? '#f43f5e' : 'var(--text-muted)' }}>¥{b.spent?.toFixed(0)} / ¥{b.limit}</span>
        </div>
        <div className="progress"><div className="progress-bar" style={{ width: `${Math.min(b.percentage, 100)}%`, background: b.percentage > 80 ? 'linear-gradient(90deg,#f43f5e,#e11d48)' : undefined }} /></div>
      </div>
    ))}</div>
  }

  if (tab === '统计分析') {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {stats.map((s: any, i: number) => (
          <div key={i} className="glass-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: getCategoryColor(s.category) }}>¥{s.total?.toFixed(0)}</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{s.category}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.count}笔</div>
          </div>
        ))}
        {stats.length === 0 && <div style={{ gridColumn: '1/-1' }}><Empty text="暂无统计数据" /></div>}
      </div>
    )
  }

  if (tab === '账单导入') {
    return (
      <div style={{ maxWidth: 600 }}>
        <select className="input" value={source} onChange={e => setSource(e.target.value)} style={{ marginBottom: 12 }}>
          <option value="wechat">微信账单</option><option value="alipay">支付宝账单</option>
        </select>
        <textarea className="input" rows={6} placeholder="粘贴CSV账单内容..." value={csv} onChange={e => setCsv(e.target.value)} style={{ marginBottom: 12, fontFamily: 'monospace', fontSize: 12 }} />
        <button className="btn btn-primary" onClick={importBill}>导入账单</button>
      </div>
    )
  }
  return null
}

/* ==================== 学习督导 ==================== */
function StudyTab({ tab }: any) {
  const [records, setRecords] = useState<any[]>([])
  const [points, setPoints] = useState<any[]>([])
  const [questions, setQuestions] = useState<any[]>([])
  const [stats, setStats] = useState<any[]>([])
  const [form, setForm] = useState<any>({})
  const [loading, setLoading] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      if (tab === '学习记录') { const d = await api('/studies/records'); setRecords(Array.isArray(d.data) ? d.data : []) }
      else if (tab === '知识点') { const d = await api('/studies/knowledge'); setPoints(Array.isArray(d.data) ? d.data : []) }
      else if (tab === '错题本') { const d = await api('/studies/wrong-questions'); setQuestions(Array.isArray(d.data) ? d.data : []) }
      else if (tab === '学习统计') { const d = await api('/studies/stats'); setStats(Array.isArray(d.data) ? d.data : []) }
    } catch { /* */ }
    setLoading(false)
  }, [tab])

  useEffect(() => { if (['学习记录', '知识点', '错题本', '学习统计'].includes(tab)) loadData() }, [tab, loadData])

  async function addRecord() { try { await api('/studies/records', { method: 'POST', body: JSON.stringify(form) }); setForm({}); loadData() } catch { /* */ } }

  if (loading) return <Empty text="加载中..." />

  if (tab === '学习记录') {
    return <div>{records.length === 0 ? <Empty text="暂无学习记录" /> : records.map((r: any, i: number) => (
      <div key={i} className="list-item">
        <div><span className="tag tag-primary">{r.subject}</span><span style={{ marginLeft: 8 }}>{r.duration_minutes}分钟</span>{r.is_delayed && <span className="tag tag-warning" style={{ marginLeft: 8 }}>拖延</span>}</div>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>效率{Math.round((r.efficiency || 0) * 100)}%</span>
      </div>
    ))}</div>
  }

  if (tab === '记录学习') {
    return (
      <div style={{ maxWidth: 500 }}><div style={{ display: 'grid', gap: 12 }}>
        <input className="input" placeholder="学科/内容" value={form.subject || ''} onChange={e => setForm({ ...form, subject: e.target.value })} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <input className="input" type="number" placeholder="时长（分钟）" value={form.duration_minutes || ''} onChange={e => setForm({ ...form, duration_minutes: parseInt(e.target.value) || 0 })} />
          <input className="input" type="number" placeholder="效率 0-1" step="0.1" value={form.efficiency || ''} onChange={e => setForm({ ...form, efficiency: parseFloat(e.target.value) || 0 })} />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, color: 'var(--text-secondary)' }}>
          <input type="checkbox" checked={form.is_delayed || false} onChange={e => setForm({ ...form, is_delayed: e.target.checked })} />拖延后完成
        </label>
        <button className="btn btn-primary" onClick={addRecord}>记录学习</button>
      </div></div>
    )
  }

  if (tab === '知识点') {
    return <div>{points.length === 0 ? <Empty text="暂无知识点" /> : points.map((p: any, i: number) => (
      <div key={i} className="list-item"><div><span className="tag tag-primary">{p.subject}</span><span style={{ marginLeft: 8 }}>{p.title}</span></div><span className="tag tag-success">掌握{p.mastery_level}%</span></div>
    ))}</div>
  }

  if (tab === '错题本') {
    return <div>{questions.length === 0 ? <Empty text="暂无错题" /> : questions.map((q: any, i: number) => (
      <div key={i} className="list-item" style={{ borderColor: q.is_mastered ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)' }}>
        <div><span className="tag" style={{ color: q.is_mastered ? '#10b981' : '#f43f5e' }}>{q.is_mastered ? '已掌握' : '未掌握'}</span><span style={{ marginLeft: 8 }}>{q.question}</span></div>
      </div>
    ))}</div>
  }

  if (tab === '学习统计') {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {stats.map((s: any, i: number) => (
          <div key={i} className="glass-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#6366f1' }}>{s.total_minutes}分钟</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{s.subject}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.sessions}次</div>
          </div>
        ))}
        {stats.length === 0 && <div style={{ gridColumn: '1/-1' }}><Empty text="暂无学习数据" /></div>}
      </div>
    )
  }
  return null
}

/* ==================== 物品收纳 ==================== */
function ItemTab({ tab }: any) {
  const [items, setItems] = useState<any[]>([])
  const [expiring, setExpiring] = useState<any[]>([])
  const [form, setForm] = useState<any>({})
  const [loading, setLoading] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      if (tab === '物品列表') { const d = await api('/items'); setItems(Array.isArray(d.data) ? d.data : []) }
      else if (tab === '临期预警') { const d = await api('/items/expiring?days=7'); setExpiring(Array.isArray(d.data) ? d.data : []) }
    } catch { /* */ }
    setLoading(false)
  }, [tab])

  useEffect(() => { if (['物品列表', '临期预警'].includes(tab)) loadData() }, [tab, loadData])

  async function addItem() { try { await api('/items', { method: 'POST', body: JSON.stringify(form) }); setForm({}); loadData() } catch { /* */ } }

  if (loading) return <Empty text="加载中..." />

  if (tab === '物品列表') {
    return <div>{items.length === 0 ? <Empty text="暂无物品" /> : items.map((it: any, i: number) => (
      <div key={i} className="list-item"><div><span>{it.name}</span><span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-muted)' }}>📍{it.location_path}</span></div>{it.expire_at && <span className="tag tag-warning">⏰{it.expire_at.slice(0, 10)}</span>}</div>
    ))}</div>
  }

  if (tab === '添加物品') {
    return (
      <div style={{ maxWidth: 500 }}><div style={{ display: 'grid', gap: 12 }}>
        <input className="input" placeholder="物品名称" value={form.name || ''} onChange={e => setForm({ ...form, name: e.target.value })} />
        <input className="input" placeholder="存放位置（如：MyHome/Kitchen/Fridge）" value={form.location_path || ''} onChange={e => setForm({ ...form, location_path: e.target.value })} />
        <select className="input" value={form.category || ''} onChange={e => setForm({ ...form, category: e.target.value })}>
          <option value="">选择类别</option><option value="food">食品</option><option value="cosmetic">护肤品</option><option value="medicine">药品</option><option value="card">会员卡</option><option value="other">其他</option>
        </select>
        <input className="input" type="datetime-local" value={form.expire_at || ''} onChange={e => setForm({ ...form, expire_at: e.target.value })} />
        <button className="btn btn-primary" onClick={addItem}>添加物品</button>
      </div></div>
    )
  }

  if (tab === '临期预警') {
    return <div>{expiring.length === 0 ? <Empty text="7天内无过期物品 ✓" /> : expiring.map((it: any, i: number) => (
      <div key={i} className="list-item" style={{ borderColor: 'rgba(245,158,11,0.2)' }}>
        <div><span className="tag tag-warning">⏰ {it.days_left}天后过期</span><span style={{ marginLeft: 8 }}>{it.name}</span></div>
      </div>
    ))}</div>
  }

  if (tab === '闲置物品') {
    return <div className="empty"><div className="empty-icon">📦</div><div>闲置检测需要30天以上数据积累</div><div style={{ fontSize: 12, marginTop: 8 }}>系统会自动识别连续30天未使用的物品</div></div>
  }

  if (tab === '位置管理') {
    return (
      <div>
        <div style={{ padding: 20, background: 'var(--bg-elevated)', borderRadius: 'var(--r-md)', marginBottom: 16, fontFamily: 'monospace', fontSize: 13, color: 'var(--text-secondary)' }}>
          <div>MyHome/</div>
          <div style={{ paddingLeft: 16 }}>{'├──'} Kitchen/Fridge</div>
          <div style={{ paddingLeft: 16 }}>{'├──'} Bathroom/Cabinet</div>
          <div style={{ paddingLeft: 16 }}>{'└──'} Bedroom/Wardrobe</div>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>支持四级层级：房屋 → 房间 → 柜体 → 格子</p>
      </div>
    )
  }
  return null
}

/* ==================== 出行处理 ==================== */
function TravelTab({ tab }: any) {
  const [plans, setPlans] = useState<any[]>([])
  const [packing, setPacking] = useState<any[]>([])
  const [weather, setWeather] = useState<any>(null)
  const [estimate, setEstimate] = useState<any>(null)
  const [form, setForm] = useState<any>({})
  const [days, setDays] = useState(3)
  const [city, setCity] = useState('北京')
  const [travelType, setTravelType] = useState('trip')
  const [loading, setLoading] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try { if (tab === '出行计划') { const d = await api('/travels'); setPlans(Array.isArray(d.data) ? d.data : []) } } catch { /* */ }
    setLoading(false)
  }, [tab])

  useEffect(() => { if (tab === '出行计划') loadData() }, [tab, loadData])

  async function addTravel() { try { await api('/travels', { method: 'POST', body: JSON.stringify(form) }); setForm({}); loadData() } catch { /* */ } }
  async function generate() { try { const d = await api(`/travels/packing-list?days=${days}`); setPacking(Array.isArray(d.data) ? d.data : []) } catch { /* */ } }
  async function checkWeather() { try { const d = await api(`/travels/weather-check?destination=${city}`); setWeather(d.data) } catch { /* */ } }
  async function calcCost() { try { const d = await api(`/travels/estimate-cost?travel_type=${travelType}&days=3`); setEstimate(d.data) } catch { /* */ } }

  if (loading) return <Empty text="加载中..." />

  if (tab === '出行计划') {
    return <div>{plans.length === 0 ? <Empty text="暂无出行计划" /> : plans.map((t: any, i: number) => (
      <div key={i} className="list-item"><div><span className="tag tag-primary">{t.type}</span><span style={{ marginLeft: 8, fontWeight: 500 }}>{t.title} → {t.destination}</span></div><span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t.depart?.slice(5, 16)}</span></div>
    ))}</div>
  }

  if (tab === '添加出行') {
    return (
      <div style={{ maxWidth: 500 }}><div style={{ display: 'grid', gap: 12 }}>
        <input className="input" placeholder="出行标题" value={form.title || ''} onChange={e => setForm({ ...form, title: e.target.value })} />
        <input className="input" placeholder="目的地" value={form.destination || ''} onChange={e => setForm({ ...form, destination: e.target.value })} />
        <select className="input" value={form.travel_type || ''} onChange={e => setForm({ ...form, travel_type: e.target.value })}>
          <option value="">选择类型</option><option value="trip">旅行</option><option value="commute">通勤</option><option value="flight">航班</option><option value="hotel">住宿</option>
        </select>
        <input className="input" type="datetime-local" value={form.depart_time || ''} onChange={e => setForm({ ...form, depart_time: e.target.value })} />
        <button className="btn btn-primary" onClick={addTravel}>添加出行</button>
      </div></div>
    )
  }

  if (tab === '行李清单') {
    return (
      <div>
        <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
          <input className="input" type="number" value={days} onChange={e => setDays(parseInt(e.target.value) || 3)} style={{ width: 100 }} />
          <span style={{ alignSelf: 'center', color: 'var(--text-secondary)' }}>天</span>
          <button className="btn btn-primary" onClick={generate}>生成清单</button>
        </div>
        {packing.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            {packing.map((p: any, i: number) => (
              <div key={i} className="list-item" style={{ marginBottom: 0 }}>
                <span>{p.item} {p.in_storage && <span style={{ color: '#10b981' }}>✓</span>}</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>x{p.quantity}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (tab === '天气查询') {
    return (
      <div>
        <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
          <input className="input" value={city} onChange={e => setCity(e.target.value)} placeholder="输入城市" />
          <button className="btn btn-primary" onClick={checkWeather}>查询</button>
        </div>
        {weather && (
          <div className="glass-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48 }}>{weather.condition === 'sunny' ? '☀️' : weather.condition === 'rainy' ? '🌧️' : weather.condition === 'snowy' ? '❄️' : '☁️'}</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{weather.temperature}°C</div>
            <div style={{ color: 'var(--text-secondary)' }}>{weather.alert_message || '天气良好'}</div>
            {weather.suggestions?.length > 0 && (
              <div style={{ marginTop: 12, textAlign: 'left' }}>{weather.suggestions.map((s: string, i: number) => <div key={i} style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>• {s}</div>)}</div>
            )}
          </div>
        )}
      </div>
    )
  }

  if (tab === '开销预估') {
    return (
      <div>
        <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
          <select className="input" value={travelType} onChange={e => setTravelType(e.target.value)}>
            <option value="trip">短途旅行</option><option value="flight">航班出行</option><option value="commute">日常通勤</option>
          </select>
          <button className="btn btn-primary" onClick={calcCost}>预估</button>
        </div>
        {estimate && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {[{ label: '路费', value: estimate.transport_cost, color: '#f43f5e' }, { label: '餐饮', value: estimate.meal_cost, color: '#f59e0b' }, { label: '总计', value: estimate.total_cost, color: '#6366f1' }].map((item, i) => (
              <div key={i} className="glass-card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: item.color }}>¥{item.value}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{item.label}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }
  return null
}
