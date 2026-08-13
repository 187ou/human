import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Line, Doughnut, Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, Title, Tooltip, Legend, Filler,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend, Filler)

interface DashboardData {
  month_consume: number
  week_study_hours: number
  upcoming_schedules: number
  expiring_items: number
  daily_consume: { day: string; total: number }[]
  study_subjects: { subject: string; minutes: number }[]
  consume_categories: { category: string; total: number }[]
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    api('/stats/dashboard').then(d => setData(d.data)).catch(() => {})
  }, [])

  if (!data) return <div>加载中...</div>

  const statCards = [
    { icon: '💰', value: `¥${data.month_consume.toFixed(0)}`, label: '本月消费' },
    { icon: '📚', value: `${data.week_study_hours}h`, label: '本周学习' },
    { icon: '📅', value: data.upcoming_schedules, label: '待办日程' },
    { icon: '⏰', value: data.expiring_items, label: '即将过期' },
  ]

  const chartOptions = { responsive: true, plugins: { legend: { display: false } } }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>📊 数据概览</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 15, marginBottom: 20 }}>
        {statCards.map((c, i) => (
          <div key={i} className="card" style={{ display: 'flex', alignItems: 'center', gap: 15, marginBottom: 0 }}>
            <span style={{ fontSize: 32 }}>{c.icon}</span>
            <div>
              <span style={{ fontSize: 24, fontWeight: 700, display: 'block' }}>{c.value}</span>
              <span style={{ fontSize: 12, color: '#999' }}>{c.label}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 15, marginBottom: 15 }}>
        <div className="card">
          <div className="card-title">📈 本月消费趋势</div>
          <Line data={{
            labels: data.daily_consume.map(x => x.day.slice(5)),
            datasets: [{ label: '消费(元)', data: data.daily_consume.map(x => x.total), borderColor: '#667eea', backgroundColor: 'rgba(102,126,234,0.1)', fill: true, tension: 0.4 }],
          }} options={chartOptions} />
        </div>
        <div className="card">
          <div className="card-title">🍩 消费品类分布</div>
          <Doughnut data={{
            labels: data.consume_categories.map(x => x.category),
            datasets: [{ data: data.consume_categories.map(x => x.total), backgroundColor: ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140'] }],
          }} options={{ responsive: true }} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 15 }}>
        <div className="card">
          <div className="card-title">📚 学习科目分布</div>
          <Bar data={{
            labels: data.study_subjects.map(x => x.subject),
            datasets: [{ label: '分钟', data: data.study_subjects.map(x => x.minutes), backgroundColor: ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a'] }],
          }} options={chartOptions} />
        </div>
        <div className="card">
          <div className="card-title">📅 近期待办</div>
          <div style={{ fontSize: 14, color: '#666' }}>
            <p>本月消费: <strong>¥{data.month_consume.toFixed(0)}</strong></p>
            <p>本周学习: <strong>{data.week_study_hours}小时</strong></p>
            <p>待办日程: <strong>{data.upcoming_schedules}项</strong></p>
            <p>即将过期: <strong>{data.expiring_items}件</strong></p>
          </div>
        </div>
      </div>
    </div>
  )
}
