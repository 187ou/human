import { useEffect, useState } from 'react'
import { api } from '../api/client'

interface ProfileData {
  id: number
  username: string
  user_type: string
  chronotype: string
  wake_hour: number
  sleep_hour: number
  commute_minutes: number
  monthly_income: number
  spending_concept: string
  study_goal: string | null
  study_subject: string | null
  living_env: string
  has_kitchen: boolean
}

const chronotypeOptions = [
  { value: 'early_bird', label: '🌅 早鸟型（早起高效）' },
  { value: 'night_owl', label: '🦉 夜猫型（晚睡高效）' },
  { value: 'regular', label: '⏰ 规律型（作息稳定）' },
  { value: 'irregular', label: '🔄 不规律型' },
]

const spendingOptions = [
  { value: 'conservative', label: '💰 保守型（精打细算）' },
  { value: 'moderate', label: '📊 稳健型（量入为出）' },
  { value: 'aggressive', label: '🚀 宽松型（享受生活）' },
]

const livingOptions = [
  { value: 'studio', label: '🏠 单间' },
  { value: 'shared', label: '👥 合租' },
  { value: 'apartment', label: '🏢 整租' },
  { value: 'house', label: '🏡 自有住房' },
]

export default function Profile() {
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [form, setForm] = useState({
    chronotype: 'regular',
    wake_hour: 7,
    sleep_hour: 23,
    commute_minutes: 30,
    monthly_income: 0,
    spending_concept: 'moderate',
    study_goal: '',
    study_subject: '',
    living_env: 'apartment',
    has_kitchen: true,
  })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api('/profile/').then(d => {
      setProfile(d.data)
      setForm({
        chronotype: d.data.chronotype || 'regular',
        wake_hour: d.data.wake_hour || 7,
        sleep_hour: d.data.sleep_hour || 23,
        commute_minutes: d.data.commute_minutes || 30,
        monthly_income: d.data.monthly_income || 0,
        spending_concept: d.data.spending_concept || 'moderate',
        study_goal: d.data.study_goal || '',
        study_subject: d.data.study_subject || '',
        living_env: d.data.living_env || 'apartment',
        has_kitchen: d.data.has_kitchen,
      })
    }).catch(() => {})
  }, [])

  async function save() {
    await api('/profile/', { method: 'PUT', body: JSON.stringify(form) })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  async function vectorize() {
    await api('/vectors/vectorize-habits', { method: 'POST' })
    alert('习惯向量化完成')
  }

  if (!profile) return <div>加载中...</div>

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>👤 用户画像</h2>

      <div className="card">
        <div className="card-title">基础信息</div>
        <div style={{ display: 'flex', gap: 20, fontSize: 14, color: '#666' }}>
          <span>用户名: <strong>{profile.username}</strong></span>
          <span>类型: <strong>{profile.user_type}</strong></span>
        </div>
      </div>

      <div className="card">
        <div className="card-title">作息类型</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {chronotypeOptions.map(opt => (
            <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="radio" name="chronotype" value={opt.value}
                checked={form.chronotype === opt.value}
                onChange={e => setForm({ ...form, chronotype: e.target.value })} />
              {opt.label}
            </label>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-title">作息时间</div>
        <div className="form-row">
          <label style={{ fontSize: 14, color: '#666' }}>
            起床时间
            <input type="number" min={0} max={23} value={form.wake_hour}
              onChange={e => setForm({ ...form, wake_hour: parseInt(e.target.value) })}
              style={{ width: 60, marginLeft: 8 }} />
          </label>
          <label style={{ fontSize: 14, color: '#666' }}>
            睡觉时间
            <input type="number" min={0} max={23} value={form.sleep_hour}
              onChange={e => setForm({ ...form, sleep_hour: parseInt(e.target.value) })}
              style={{ width: 60, marginLeft: 8 }} />
          </label>
          <label style={{ fontSize: 14, color: '#666' }}>
            通勤(分钟)
            <input type="number" min={0} max={180} value={form.commute_minutes}
              onChange={e => setForm({ ...form, commute_minutes: parseInt(e.target.value) })}
              style={{ width: 60, marginLeft: 8 }} />
          </label>
        </div>
      </div>

      <div className="card">
        <div className="card-title">经济状况</div>
        <div className="form-row">
          <label style={{ fontSize: 14, color: '#666' }}>
            月收入(元)
            <input type="number" min={0} value={form.monthly_income}
              onChange={e => setForm({ ...form, monthly_income: parseFloat(e.target.value) })}
              style={{ width: 120, marginLeft: 8 }} />
          </label>
        </div>
        <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
          {spendingOptions.map(opt => (
            <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="radio" name="spending" value={opt.value}
                checked={form.spending_concept === opt.value}
                onChange={e => setForm({ ...form, spending_concept: e.target.value })} />
              {opt.label}
            </label>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-title">学习目标</div>
        <div className="form-row">
          <input placeholder="长期学习目标（如：通过英语六级）" value={form.study_goal}
            onChange={e => setForm({ ...form, study_goal: e.target.value })} style={{ flex: 1 }} />
        </div>
        <div className="form-row">
          <input placeholder="主要学习方向（如：英语、编程）" value={form.study_subject}
            onChange={e => setForm({ ...form, study_subject: e.target.value })} style={{ flex: 1 }} />
        </div>
      </div>

      <div className="card">
        <div className="card-title">居住环境</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {livingOptions.map(opt => (
            <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input type="radio" name="living" value={opt.value}
                checked={form.living_env === opt.value}
                onChange={e => setForm({ ...form, living_env: e.target.value })} />
              {opt.label}
            </label>
          ))}
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, fontSize: 14 }}>
          <input type="checkbox" checked={form.has_kitchen}
            onChange={e => setForm({ ...form, has_kitchen: e.target.checked })} />
          有厨房
        </label>
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
        <button onClick={save}>{saved ? '✅ 已保存' : '保存画像'}</button>
        <button className="secondary" onClick={vectorize}>🔄 习惯向量化</button>
      </div>
    </div>
  )
}
