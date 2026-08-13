import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

interface ScheduleItem {
  id: number
  title: string
  start: string
  end: string
  category: string
  is_completed: boolean
  is_paused: boolean
}

interface Conflict {
  schedule_a: { id: number; title: string; start: string; end: string }
  schedule_b: { id: number; title: string; start: string; end: string }
  overlap_minutes: number
}

interface FragmentSlot {
  start: string
  end: string
  minutes: number
  slot_type: string
}

interface Exception {
  id: number
  title: string
  rule_expr: { days_of_week: number[]; start_time: string; end_time: string; action: string }
}

const dayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const slotTypeNames: Record<string, string> = {
  morning_commute: '早间通勤', morning: '早晨', forenoon: '上午', lunch: '午休',
  afternoon: '下午', evening: '晚间', fragment: '碎片',
}

export default function Schedule() {
  const { user } = useAuth()
  const today = new Date().toISOString().slice(0, 10)
  const [items, setItems] = useState<ScheduleItem[]>([])
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [slots, setSlots] = useState<FragmentSlot[]>([])
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [lateInfo, setLateInfo] = useState<any>(null)
  const [adjustedLoad, setAdjustedLoad] = useState<any>(null)
  const [selectedDate, setSelectedDate] = useState(today)
  const [form, setForm] = useState({ title: '', category: 'fixed', start_time: '', end_time: '' })
  const [nlText, setNlText] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [profile, setProfile] = useState({ wake_hour: 7, sleep_hour: 23, commute_minutes: 30 })

  const load = useCallback(() => {
    api(`/schedules?date=${selectedDate}`).then(d => setItems(d.data)).catch(() => {})
    api(`/schedules/conflicts?date=${selectedDate}`).then(d => setConflicts(d.data)).catch(() => {})
    api(`/schedules/fragment-slots?date=${selectedDate}`).then(d => setSlots(d.data)).catch(() => {})
    api('/schedules/exceptions').then(d => setExceptions(d.data)).catch(() => {})
    api(`/schedules/late-night?date=${selectedDate}`).then(d => setLateInfo(d.data)).catch(() => {})
    api(`/schedules/adjusted-load?date=${selectedDate}`).then(d => setAdjustedLoad(d.data)).catch(() => {})
  }, [selectedDate])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (user) {
      setProfile({ wake_hour: user.wake_hour || 7, sleep_hour: user.sleep_hour || 23, commute_minutes: user.commute_minutes || 30 })
    }
  }, [user])

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

  async function emergencyPause() {
    if (!confirm('确定暂停所有未来日程？')) return
    await api('/schedules/emergency/pause?reason=sick', { method: 'POST' })
    load()
  }

  async function emergencyPostpone() {
    if (!confirm('确定顺延所有未来日程2小时？')) return
    await api('/schedules/emergency/postpone?delay_hours=2&reason=overtime', { method: 'POST' })
    load()
  }

  async function resumeAll() {
    await api('/schedules/emergency/resume', { method: 'POST' })
    load()
  }

  async function addException() {
    if (!nlText.trim()) return
    try {
      const parsed = await api('/schedule-nlp/parse', { method: 'POST', body: JSON.stringify({ text: nlText }) })
      if (parsed.code !== 0) { alert('解析失败'); return }
      await api('/schedules/exceptions', { method: 'POST', body: JSON.stringify({
        title: nlText,
        rule_expr: parsed.data,
        effective_from: new Date().toISOString(),
      }) })
      setNlText('')
      load()
    } catch (e: any) {
      alert(`错误: ${e.message}`)
    }
  }

  async function applyExceptions() {
    const data = await api(`/schedules/exceptions/apply?date=${selectedDate}`)
    alert(`已应用 ${data.data.length} 条例外规则`)
    load()
  }

  async function updateProfile() {
    await api('/auth/profile', { method: 'PUT', body: JSON.stringify(profile) })
    alert('基础信息已更新')
    load()
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2>📅 时间规划</h2>
        <button className="secondary" onClick={() => setShowSettings(!showSettings)}>
          ⚙️ {showSettings ? '隐藏设置' : '基础信息'}
        </button>
      </div>

      {showSettings && (
        <div className="card">
          <div className="card-title">基础信息（起床/睡觉/通勤）</div>
          <div className="form-row">
            <label style={{ fontSize: 14, color: '#666' }}>
              起床时间
              <input type="number" min={0} max={23} value={profile.wake_hour}
                onChange={e => setProfile({ ...profile, wake_hour: parseInt(e.target.value) })}
                style={{ width: 80, marginLeft: 8 }} />
            </label>
            <label style={{ fontSize: 14, color: '#666' }}>
              睡觉时间
              <input type="number" min={0} max={23} value={profile.sleep_hour}
                onChange={e => setProfile({ ...profile, sleep_hour: parseInt(e.target.value) })}
                style={{ width: 80, marginLeft: 8 }} />
            </label>
            <label style={{ fontSize: 14, color: '#666' }}>
              通勤(分钟)
              <input type="number" min={0} max={180} value={profile.commute_minutes}
                onChange={e => setProfile({ ...profile, commute_minutes: parseInt(e.target.value) })}
                style={{ width: 80, marginLeft: 8 }} />
            </label>
            <button onClick={updateProfile}>保存</button>
          </div>
        </div>
      )}

      {lateInfo?.is_late && (
        <div className="card" style={{ borderLeft: '4px solid #e74c3c', background: '#fff5f5' }}>
          <div style={{ color: '#e74c3c', fontWeight: 600 }}>{lateInfo.message}</div>
          <div style={{ fontSize: 13, color: '#999', marginTop: 4 }}>
            {`调整系数: ${lateInfo.adjustment_factor} | 建议任务量下调${Math.round((1 - lateInfo.adjustment_factor) * 100)}%`}
          </div>
        </div>
      )}

      {adjustedLoad && (
        <div className="card" style={{ borderLeft: '4px solid #f39c12' }}>
          <div className="card-title">今日任务负荷</div>
          <div style={{ display: 'flex', gap: 20, fontSize: 14 }}>
            <span>{`原始: ${adjustedLoad.original_count}项 (${adjustedLoad.original_hours}h)`}</span>
            <span>{`调整后: ${adjustedLoad.adjusted_count}项 (${adjustedLoad.adjusted_hours}h)`}</span>
            <span className="badge badge-info">{`系数 ${adjustedLoad.adjustment_factor}`}</span>
          </div>
        </div>
      )}

      <div className="card">
        <div className="form-row">
          <label style={{ fontSize: 14, color: '#666' }}>
            选择日期
            <input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} style={{ marginLeft: 8 }} />
          </label>
        </div>
      </div>

      {conflicts.length > 0 && (
        <div className="card" style={{ borderLeft: '4px solid #e74c3c', background: '#fff5f5' }}>
          <div className="card-title" style={{ color: '#e74c3c' }}>
            {`⚠ 检测到 ${conflicts.length} 处时间冲突`}
          </div>
          {conflicts.map((c, i) => (
            <div key={i} style={{ fontSize: 13, marginBottom: 4, color: '#666' }}>
              {`${c.schedule_a.title} 与 ${c.schedule_b.title} 重叠 ${c.overlap_minutes} 分钟`}
            </div>
          ))}
        </div>
      )}

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

      <div className="card">
        <div className="card-title">突发场景</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="danger" onClick={emergencyPause}>🤒 生病-暂停全部</button>
          <button className="warning" onClick={emergencyPostpone}>💼 加班-顺延2小时</button>
          <button className="secondary" onClick={resumeAll}>✅ 恢复全部</button>
          <button className="secondary" onClick={applyExceptions}>🔄 应用例外规则</button>
        </div>
      </div>

      <div className="card">
        <div className="card-title">周期性例外日程（自然语言录入）</div>
        <div className="form-row">
          <input placeholder="例：周一至周五晚间学习，周三聚餐暂停" value={nlText}
            onChange={e => setNlText(e.target.value)} style={{ flex: 2 }} />
          <button onClick={addException}>添加例外</button>
        </div>
        {exceptions.length > 0 && (
          <div style={{ marginTop: 10 }}>
            {exceptions.map(exc => (
              <div key={exc.id} style={{ padding: '6px 0', borderBottom: '1px solid #eee', fontSize: 13 }}>
                <strong>{exc.title}</strong>
                <span style={{ color: '#999', marginLeft: 8 }}>
                  {exc.rule_expr.days_of_week.map(d => dayNames[d]).join(', ')}
                  {exc.rule_expr.start_time}-{exc.rule_expr.end_time}
                  ({exc.rule_expr.action === 'add' ? '添加' : exc.rule_expr.action === 'pause' ? '暂停' : '跳过'})
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {slots.length > 0 && (
        <div className="card">
          <div className="card-title">碎片时间挪位方案</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {slots.map((s, i) => (
              <div key={i} style={{ background: '#f8f9fa', padding: '8px 14px', borderRadius: 8, fontSize: 13 }}>
                <span className="badge badge-info">{slotTypeNames[s.slot_type] || s.slot_type}</span>
                <span style={{ marginLeft: 8 }}>{s.start.slice(11, 16)} - {s.end.slice(11, 16)}</span>
                <span style={{ color: '#999', marginLeft: 4 }}>({Math.round(s.minutes)}分钟)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 style={{ marginBottom: 10, fontSize: 16 }}>{`日程列表 (${items.length})`}</h3>
        {items.length === 0 ? <p style={{ color: '#999' }}>暂无日程</p> : items.map(s => (
          <div key={s.id} className="list-item" style={{ opacity: s.is_paused ? 0.5 : 1 }}>
            <span>
              {s.is_paused && <span style={{ color: '#e74c3c', marginRight: 8 }}>⏸️</span>}
              {s.title}
              <span className="badge badge-info" style={{ marginLeft: 8 }}>{s.category}</span>
            </span>
            <span>
              <span style={{ fontSize: 12, color: '#999', marginRight: 8 }}>
                {s.start.slice(11, 16)} - {s.end.slice(11, 16)}
              </span>
              {s.is_completed ? (
                <span className="badge badge-success">✅ 已完成</span>
              ) : (
                <button style={{ padding: '2px 8px', fontSize: 12 }} onClick={() => complete(s.id)}>完成</button>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
