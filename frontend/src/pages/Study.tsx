import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

interface StudyRecord {
  subject: string
  total_minutes: number
  focus_minutes: number
  avg_accuracy: number | null
  sessions: number
}

interface KnowledgePoint {
  id: number
  subject: string
  title: string
  mastery_level: number
  accuracy_rate: number
  review_count: number
}

interface WrongQuestion {
  id: number
  subject: string
  question: string
  correct_answer: string | null
  my_answer: string | null
  is_mastered: boolean
  review_count: number
}

interface DailyRec {
  is_rest_day: boolean
  message?: string
  yesterday_minutes: number
  yesterday_accuracy: number
  avg_accuracy: number
  new_knowledge_target: number
  review_target: number
  suggested_duration: number
  unmet_adjustment: number
}

interface EfficiencyReport {
  period_days: number
  total_minutes: number
  focus_minutes: number
  idle_minutes: number
  focus_rate: number
  avg_accuracy: number
  total_sessions: number
  message: string
}

export default function Study() {
  const [records, setRecords] = useState<StudyRecord[]>([])
  const [knowledge, setKnowledge] = useState<KnowledgePoint[]>([])
  const [wrongQuestions, setWrongQuestions] = useState<WrongQuestion[]>([])
  const [dailyRec, setDailyRec] = useState<DailyRec | null>(null)
  const [efficiency, setEfficiency] = useState<EfficiencyReport | null>(null)
  const [form, setForm] = useState({ subject: '', duration_minutes: '', focus_minutes: '', efficiency: '', is_delayed: false })
  const [kpForm, setKpForm] = useState({ subject: '', title: '' })
  const [wqForm, setWqForm] = useState({ subject: '', question: '', correct_answer: '', my_answer: '' })
  const [showKP, setShowKP] = useState(false)
  const [showWQ, setShowWQ] = useState(false)

  const load = useCallback(() => {
    api('/studies/stats').then(d => setRecords(d.data)).catch(() => {})
    api('/studies/knowledge').then(d => setKnowledge(d.data)).catch(() => {})
    api('/studies/wrong-questions').then(d => setWrongQuestions(d.data)).catch(() => {})
    api('/studies/daily-recommendation').then(d => setDailyRec(d.data)).catch(() => {})
    api('/studies/efficiency-report').then(d => setEfficiency(d.data)).catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  async function addRecord() {
    if (!form.subject || !form.duration_minutes) return
    await api('/studies/records', { method: 'POST', body: JSON.stringify({
      subject: form.subject,
      duration_minutes: parseInt(form.duration_minutes),
      focus_minutes: parseInt(form.focus_minutes) || undefined,
      efficiency: parseFloat(form.efficiency) || undefined,
      is_delayed: form.is_delayed,
    }) })
    setForm({ subject: '', duration_minutes: '', focus_minutes: '', efficiency: '', is_delayed: false })
    load()
  }

  async function addKP() {
    if (!kpForm.subject || !kpForm.title) return
    await api('/studies/knowledge', { method: 'POST', body: JSON.stringify(kpForm) })
    setKpForm({ subject: '', title: '' })
    load()
  }

  async function addWQ() {
    if (!wqForm.subject || !wqForm.question) return
    await api('/studies/wrong-questions', { method: 'POST', body: JSON.stringify(wqForm) })
    setWqForm({ subject: '', question: '', correct_answer: '', my_answer: '' })
    load()
  }

  async function reviewKP(id: number, correct: boolean) {
    await api(`/studies/knowledge/${id}/review?correct=${correct}`, { method: 'POST' })
    load()
  }

  async function markMastered(id: number) {
    await api(`/studies/wrong-questions/${id}/mastered`, { method: 'POST' })
    load()
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>📚 学习督导</h2>

      {/* 每日推荐 */}
      {dailyRec && (
        <div className="card" style={{ borderLeft: `4px solid ${dailyRec.is_rest_day ? '#8e44ad' : '#27ae60'}` }}>
          <div className="card-title">每日学习推荐</div>
          {dailyRec.is_rest_day ? (
            <div style={{ color: '#8e44ad', fontWeight: 600 }}>{dailyRec.message}</div>
          ) : (
            <div>
              <div style={{ display: 'flex', gap: 20, fontSize: 14, marginBottom: 8 }}>
                <span>新知识点目标: <strong>{dailyRec.new_knowledge_target}个</strong></span>
                <span>复习目标: <strong>{dailyRec.review_target}个</strong></span>
                <span>建议时长: <strong>{dailyRec.suggested_duration}分钟</strong></span>
                <span>平均正确率: <strong>{(dailyRec.avg_accuracy * 100).toFixed(0)}%</strong></span>
              </div>
              {dailyRec.unmet_adjustment < 1 && (
                <div style={{ color: '#e74c3c', fontSize: 13 }}>⚠️ 昨日未达标，今日任务已下调</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 效率报告 */}
      {efficiency && (
        <div className="card">
          <div className="card-title">学习效率报告（近{efficiency.period_days}天）</div>
          <div style={{ display: 'flex', gap: 20, fontSize: 14, flexWrap: 'wrap' }}>
            <span>总时长: <strong>{efficiency.total_minutes}分钟</strong></span>
            <span>专注: <strong>{efficiency.focus_minutes}分钟</strong></span>
            <span>挂机: <strong>{efficiency.idle_minutes}分钟</strong></span>
            <span>专注率: <strong>{(efficiency.focus_rate * 100).toFixed(0)}%</strong></span>
            <span>正确率: <strong>{(efficiency.avg_accuracy * 100).toFixed(0)}%</strong></span>
          </div>
        </div>
      )}

      {/* 记录学习 */}
      <div className="card">
        <div className="card-title">记录学习</div>
        <div className="form-row">
          <input placeholder="学科" value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })} />
          <input type="number" placeholder="总时长(分)" value={form.duration_minutes} onChange={e => setForm({ ...form, duration_minutes: e.target.value })} />
          <input type="number" placeholder="专注时长(分)" value={form.focus_minutes} onChange={e => setForm({ ...form, focus_minutes: e.target.value })} />
          <input type="number" placeholder="正确率0-1" step="0.1" value={form.efficiency} onChange={e => setForm({ ...form, efficiency: e.target.value })} />
        </div>
        <div className="form-row">
          <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 14 }}>
            <input type="checkbox" checked={form.is_delayed} onChange={e => setForm({ ...form, is_delayed: e.target.checked })} />
            拖延后完成
          </label>
          <button onClick={addRecord}>记录</button>
        </div>
      </div>

      {/* 知识点 */}
      <div className="card">
        <div className="card-title">
          知识点清单
          <button className="secondary" style={{ marginLeft: 10, padding: '2px 8px', fontSize: 12 }} onClick={() => setShowKP(!showKP)}>
            {showKP ? '隐藏' : '添加'}
          </button>
        </div>
        {showKP && (
          <div className="form-row">
            <input placeholder="学科" value={kpForm.subject} onChange={e => setKpForm({ ...kpForm, subject: e.target.value })} />
            <input placeholder="知识点" value={kpForm.title} onChange={e => setKpForm({ ...kpForm, title: e.target.value })} />
            <button onClick={addKP}>添加</button>
          </div>
        )}
        {knowledge.length > 0 && (
          <div>
            {knowledge.map(kp => (
              <div key={kp.id} style={{ padding: '6px 0', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13 }}>
                  {kp.subject} - {kp.title}
                  <span className="badge badge-info" style={{ marginLeft: 6 }}>掌握{kp.mastery_level}%</span>
                  {kp.accuracy_rate > 0 && <span style={{ color: '#999', fontSize: 12, marginLeft: 4 }}>正确率{(kp.accuracy_rate * 100).toFixed(0)}%</span>}
                </span>
                <span>
                  <button style={{ padding: '2px 6px', fontSize: 11, marginRight: 4 }} onClick={() => reviewKP(kp.id, true)}>✓</button>
                  <button style={{ padding: '2px 6px', fontSize: 11 }} className="secondary" onClick={() => reviewKP(kp.id, false)}>✗</button>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 错题 */}
      <div className="card">
        <div className="card-title">
          错题记录 ({wrongQuestions.filter(w => !w.is_mastered).length}未掌握)
          <button className="secondary" style={{ marginLeft: 10, padding: '2px 8px', fontSize: 12 }} onClick={() => setShowWQ(!showWQ)}>
            {showWQ ? '隐藏' : '添加'}
          </button>
        </div>
        {showWQ && (
          <>
            <div className="form-row">
              <input placeholder="学科" value={wqForm.subject} onChange={e => setWqForm({ ...wqForm, subject: e.target.value })} />
              <input placeholder="题目" value={wqForm.question} onChange={e => setWqForm({ ...wqForm, question: e.target.value })} style={{ flex: 2 }} />
            </div>
            <div className="form-row">
              <input placeholder="正确答案" value={wqForm.correct_answer} onChange={e => setWqForm({ ...wqForm, correct_answer: e.target.value })} />
              <input placeholder="我的答案" value={wqForm.my_answer} onChange={e => setWqForm({ ...wqForm, my_answer: e.target.value })} />
              <button onClick={addWQ}>添加</button>
            </div>
          </>
        )}
        {wrongQuestions.length > 0 && (
          <div>
            {wrongQuestions.map(wq => (
              <div key={wq.id} style={{ padding: '6px 0', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13 }}>
                  {wq.question}
                  {wq.is_mastered && <span className="badge badge-success" style={{ marginLeft: 6 }}>已掌握</span>}
                </span>
                {!wq.is_mastered && (
                  <button style={{ padding: '2px 6px', fontSize: 11 }} onClick={() => markMastered(wq.id)}>标记掌握</button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 学习统计 */}
      <div>
        <h3 style={{ marginBottom: 10, fontSize: 16 }}>学习统计</h3>
        {records.length === 0 ? <p style={{ color: '#999' }}>暂无学习记录</p> : records.map(s => (
          <div key={s.subject} className="list-item">
            <span>📚 {s.subject}</span>
            <span>
              {s.total_minutes}分钟 · {s.sessions}次
              {s.avg_accuracy && <span className="badge badge-info" style={{ marginLeft: 6 }}>正确率{(s.avg_accuracy * 100).toFixed(0)}%</span>}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
