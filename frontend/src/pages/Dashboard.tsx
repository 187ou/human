import { useEffect, useState, useMemo } from 'react'
import { api } from '../api/client'

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)

  useEffect(() => {
    api('/stats/dashboard').then(d => setStats(d.data)).catch(() => {})
  }, [])

  // 使用 useMemo 缓存卡片数据，避免每次渲染重新创建
  const cards = useMemo(() => [
    { label: '本月消费', value: `¥${(stats?.month_consume || 0).toFixed(0)}`, color: '#f43f5e', icon: '◉', width: 60 + Math.random() * 30 },
    { label: '本周学习', value: `${stats?.week_study_hours || 0}h`, color: '#6366f1', icon: '◐', width: 40 + Math.random() * 40 },
    { label: '待办日程', value: stats?.upcoming_schedules || 0, color: '#f59e0b', icon: '◷', width: 30 + Math.random() * 50 },
    { label: '即将过期', value: stats?.expiring_items || 0, color: '#10b981', icon: '◑', width: 50 + Math.random() * 30 },
  ], [stats]) // 只在 stats 变化时重新计算

  return (
    <div>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
        你好，欢迎回来 ◈
      </h1>
      <p style={{ color: '#94a3b8', marginBottom: 32 }}>
        这是你的生活数据概览，一切尽在掌握。
      </p>

      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
        {cards.map((c, i) => (
          <div key={i} className="glass-card stat-card" style={{ animationDelay: `${i * 100}ms` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <span style={{ fontSize: 24, opacity: 0.8 }}>{c.icon}</span>
              <div className="progress-bar" style={{ width: 60 }}>
                <div className="progress-fill" style={{ width: `${c.width}%`, background: c.color }} />
              </div>
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: c.color }}>{c.value}</div>
            <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>{c.label}</div>
          </div>
        ))}
      </div>

      {/* 趋势图 */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <div className="glass-card">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>📈 消费趋势</h3>
          <div style={{ height: 200, display: 'flex', alignItems: 'flex-end', gap: 8, padding: '0 8px' }}>
            {(stats?.daily_consume || []).map((d: any, i: number) => (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <div style={{
                  width: '100%',
                  height: Math.max(20, (d.total / Math.max(...(stats?.daily_consume || []).map((x: any) => x.total), 1)) * 160),
                  background: 'linear-gradient(to top, #6366f1, #818cf8)',
                  borderRadius: '4px 4px 0 0',
                  transition: 'height 0.5s',
                }} />
                <span style={{ fontSize: 10, color: '#64748b' }}>{d.day.slice(5)}</span>
              </div>
            ))}
            {(!stats?.daily_consume || stats.daily_consume.length === 0) && (
              <div style={{ width: '100%', textAlign: 'center', color: '#64748b', paddingTop: 80 }}>
                暂无数据，开始记录消费吧
              </div>
            )}
          </div>
        </div>

        <div className="glass-card">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>🍩 品类分布</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {(stats?.consume_categories || []).map((c: any, i: number) => (
              <div key={i}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                  <span>{c.category}</span>
                  <span style={{ color: '#94a3b8' }}>¥{c.total.toFixed(0)}</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{
                    width: `${(c.total / Math.max(...(stats?.consume_categories || []).map((x: any) => x.total), 1)) * 100}%`
                  }} />
                </div>
              </div>
            ))}
            {(!stats?.consume_categories || stats.consume_categories.length === 0) && (
              <div style={{ textAlign: 'center', color: '#64748b', paddingTop: 40 }}>
                暂无消费记录
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
