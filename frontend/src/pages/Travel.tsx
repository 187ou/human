import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

interface TravelPlan {
  id: number
  title: string
  type: string
  destination: string | null
  depart: string | null
  arrive: string | null
  estimated_cost: number
  weather_risk: string | null
  is_completed: boolean
}

interface PackingItem {
  item: string
  category: string
  quantity: number
  is_checked: boolean
  in_storage?: boolean
}

interface WeatherData {
  condition: string
  temperature: number
  risk_level: string
  alert_message: string
  suggestions: string[]
}

const weatherLabels: Record<string, string> = {
  sunny: '☀️ 晴', rainy: '🌧️ 雨', snowy: '❄️ 雪', cloudy: '☁️ 阴',
}

export default function Travel() {
  const [items, setItems] = useState<TravelPlan[]>([])
  const [form, setForm] = useState({ title: '', travel_type: 'trip', destination: '', depart_time: '', arrive_time: '' })
  const [packingList, setPackingList] = useState<PackingItem[]>([])
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [lastResult, setLastResult] = useState<any>(null)
  const [showPacking, setShowPacking] = useState(false)

  const load = useCallback(() => {
    api('/travels').then(d => setItems(d.data)).catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  async function add() {
    if (!form.title || !form.depart_time) return
    const body: any = { ...form }
    if (!body.arrive_time) delete body.arrive_time
    if (!body.destination) delete body.destination
    const data = await api('/travels', { method: 'POST', body: JSON.stringify(body) })
    setLastResult(data.data)
    setPackingList(data.data.packing_list || [])
    setWeather(data.data.weather)
    setShowPacking(true)
    setForm({ title: '', travel_type: 'trip', destination: '', depart_time: '', arrive_time: '' })
    load()
  }

  async function checkWeather() {
    if (!form.destination) return
    const data = await api(`/travels/weather-check?destination=${encodeURIComponent(form.destination)}`)
    setWeather(data.data)
  }

  async function generatePacking() {
    const days = form.arrive_time ? Math.max(1, Math.ceil((new Date(form.arrive_time).getTime() - new Date(form.depart_time).getTime()) / 86400000) + 1) : 1
    const data = await api(`/travels/packing-list?days=${days}`)
    setPackingList(data.data)
    setShowPacking(true)
  }

  function togglePackingItem(index: number) {
    setPackingList(prev => prev.map((item, i) => i === index ? { ...item, is_checked: !item.is_checked } : item))
  }

  async function complete(id: number) {
    await api(`/travels/${id}/complete`, { method: 'POST' })
    load()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>🚗 出行处理</h2>

      {/* 天气提醒 */}
      {weather && weather.risk_level !== 'low' && (
        <div className="card" style={{ borderLeft: `4px solid ${weather.risk_level === 'high' ? '#e74c3c' : '#f39c12'}` }}>
          <div style={{ fontWeight: 600 }}>
            {weatherLabels[weather.condition] || weather.condition} {weather.temperature}°C
            <span className={`badge ${weather.risk_level === 'high' ? 'badge-danger' : 'badge-warning'}`} style={{ marginLeft: 8 }}>
              {weather.risk_level === 'high' ? '高风险' : '中风险'}
            </span>
          </div>
          {weather.alert_message && <div style={{ fontSize: 14, marginTop: 4 }}>{weather.alert_message}</div>}
          {weather.suggestions.length > 0 && (
            <div style={{ fontSize: 13, color: '#666', marginTop: 4 }}>
              💡 {weather.suggestions.join(' · ')}
            </div>
          )}
        </div>
      )}

      {/* 创建出行 */}
      <div className="card">
        <div className="card-title">添加出行</div>
        <div className="form-row">
          <input placeholder="标题" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          <select value={form.travel_type} onChange={e => setForm({ ...form, travel_type: e.target.value })}>
            <option value="trip">旅行</option>
            <option value="commute">通勤</option>
            <option value="flight">航班</option>
            <option value="hotel">住宿</option>
          </select>
          <input placeholder="目的地" value={form.destination} onChange={e => setForm({ ...form, destination: e.target.value })} />
        </div>
        <div className="form-row">
          <input type="datetime-local" value={form.depart_time} onChange={e => setForm({ ...form, depart_time: e.target.value })} />
          <input type="datetime-local" value={form.arrive_time} onChange={e => setForm({ ...form, arrive_time: e.target.value })} />
          <button onClick={add}>创建计划</button>
          <button className="secondary" onClick={checkWeather}>查天气</button>
          <button className="secondary" onClick={generatePacking}>行李清单</button>
        </div>
      </div>

      {/* 创建结果 */}
      {lastResult && (
        <div className="card" style={{ borderLeft: '4px solid #27ae60' }}>
          <div className="card-title">计划已生成</div>
          <div style={{ display: 'flex', gap: 20, fontSize: 14, flexWrap: 'wrap' }}>
            <span>路费: <strong>¥{lastResult.estimated_costs?.transport_cost}</strong></span>
            <span>餐饮: <strong>¥{lastResult.estimated_costs?.meal_cost}</strong></span>
            <span>总开销: <strong>¥{lastResult.estimated_costs?.total_cost}</strong></span>
            <span>往返: <strong>{lastResult.estimated_costs?.duration_min}分钟</strong></span>
            <span>建议出发: <strong>{lastResult.suggested_leave_time?.slice(11, 16)}</strong></span>
          </div>
          {lastResult.cleared_schedules?.length > 0 && (
            <div style={{ fontSize: 13, color: '#666', marginTop: 4 }}>已清空 {lastResult.cleared_schedules.length} 个冲突日程</div>
          )}
        </div>
      )}

      {/* 行李清单 */}
      {showPacking && packingList.length > 0 && (
        <div className="card">
          <div className="card-title">
            行李清单 ({packingList.filter(p => p.is_checked).length}/{packingList.length})
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            {packingList.map((p, i) => (
              <div key={i} onClick={() => togglePackingItem(i)} style={{
                padding: '4px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 13,
                background: p.is_checked ? '#d4edda' : '#f8f9fa',
                textDecoration: p.is_checked ? 'line-through' : 'none',
              }}>
                {p.is_checked ? '✅' : '⬜'} {p.item} x{p.quantity}
                {p.in_storage && <span style={{ color: '#27ae60', fontSize: 11, marginLeft: 4 }}>库存✓</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 出行列表 */}
      <div>
        <h3 style={{ marginBottom: 10, fontSize: 16 }}>出行计划 ({items.length})</h3>
        {items.length === 0 ? <p style={{ color: '#999' }}>暂无出行计划</p> : items.map(t => (
          <div key={t.id} className="list-item">
            <span>
              🚗 {t.title} → {t.destination || '未设置'}
              {t.weather_risk && t.weather_risk !== 'low' && (
                <span className={`badge ${t.weather_risk === 'high' ? 'badge-danger' : 'badge-warning'}`} style={{ marginLeft: 6 }}>
                  {t.weather_risk === 'high' ? '⚠️高风险' : '中风险'}
                </span>
              )}
            </span>
            <span>
              <span style={{ fontSize: 12, color: '#999', marginRight: 8 }}>
                ¥{t.estimated_cost} · {t.depart?.slice(5, 16)}
              </span>
              {t.is_completed ? (
                <span className="badge badge-success">✅ 已完成</span>
              ) : (
                <button style={{ padding: '2px 8px', fontSize: 12 }} onClick={() => complete(t.id)}>完成</button>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
