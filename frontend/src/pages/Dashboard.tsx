import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)

  useEffect(() => {
    api('/stats/dashboard').then(d => setStats(d.data)).catch(() => {})
  }, [])

  const cards = [
    { label: '本月消费', value: `¥${(stats?.month_consume || 0).toFixed(0)}`, color: '#f43f5e', icon: '◉', pct: 65 },
    { label: '本周学习', value: `${stats?.week_study_hours || 0}h`, color: '#6366f1', icon: '◐', pct: 45 },
    { label: '待办日程', value: stats?.upcoming_schedules || 0, color: '#f59e0b', icon: '◷', pct: 80 },
    { label: '即将过期', value: stats?.expiring_items || 0, color: '#10b981', icon: '◑', pct: 25 },
  ]

  return (
    <div>
      <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6, color: 'var(--text-primary)' }}>
        你好，欢迎回来 ◈
      </h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--sp-8)', fontSize: 14 }}>
        这是你的生活数据概览，一切尽在掌握。
      </p>

      {/* 统计卡片 */}
      <div className="grid-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--sp-4)', marginBottom: 'var(--sp-6)' }}>
        {cards.map((c, i) => (
          <div key={i} className="glass-card anim-fade-up" style={{ animationDelay: `${i * 80}ms` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--sp-3)' }}>
              <span style={{ fontSize: 22, color: c.color }}>{c.icon}</span>
              <div className="progress" style={{ width: 50 }}>
                <div className="progress-bar" style={{ width: `${c.pct}%`, background: c.color }} />
              </div>
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: c.color }}>{c.value}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 'var(--sp-1)' }}>{c.label}</div>
          </div>
        ))}
      </div>

      {/* 图表区域 */}
      <div className="grid-2" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--sp-4)' }}>
        {/* 消费趋势 */}
        <div className="glass-card">
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 'var(--sp-4)', color: 'var(--text-primary)' }}>📈 消费趋势</h3>
          <div style={{ height: 180, display: 'flex', alignItems: 'flex-end', gap: 6, padding: '0 4px' }}>
            {(stats?.daily_consume || []).map((d: any, i: number) => {
              const max = Math.max(...(stats?.daily_consume || []).map((x: any) => x.total), 1)
              return (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <div style={{
                    width: '100%', height: Math.max(16, (d.total / max) * 140),
                    background: `linear-gradient(to top, #6366f1, #818cf8)`, borderRadius: '4px 4px 0 0',
                    transition: 'height 0.6s var(--ease)', opacity: 0.85,
                  }} />
                  <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{d.day.slice(5)}</span>
                </div>
              )
            })}
            {(!stats?.daily_consume || stats.daily_consume.length === 0) && (
              <div className="empty" style={{ width: '100%' }}><div className="empty-icon">📊</div>暂无数据</div>
            )}
          </div>
        </div>

        {/* 品类分布 */}
        <div className="glass-card">
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 'var(--sp-4)', color: 'var(--text-primary)' }}>🍩 品类分布</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { cat: 'food', name: '餐饮', color: '#f59e0b' },
              { cat: 'shopping', name: '购物', color: '#f43f5e' },
              { cat: 'study', name: '学习', color: '#6366f1' },
              { cat: 'transport', name: '交通', color: '#06b6d4' },
              { cat: 'entertainment', name: '娱乐', color: '#8b5cf6' },
            ].map(c => {
              const item = (stats?.consume_categories || []).find((x: any) => x.category === c.cat)
              const total = Math.max(...(stats?.consume_categories || []).map((x: any) => x.total), 1)
              const amount = item?.total || 0
              return (
                <div key={c.cat}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{c.name}</span>
                    <span style={{ color: 'var(--text-muted)' }}>¥{amount.toFixed(0)}</span>
                  </div>
                  <div className="progress">
                    <div className="progress-bar" style={{ width: `${(amount / total) * 100}%`, background: c.color }} />
                  </div>
                </div>
              )
            })}
            {(!stats?.consume_categories || stats.consume_categories.length === 0) && (
              <div className="empty"><div className="empty-icon">🛒</div>暂无消费记录</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
