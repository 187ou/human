import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

interface ConsumeRecord {
  id: number
  amount: number
  category: string
  merchant: string | null
  tag: string | null
  is_impulse: boolean | null
  is_waste: boolean | null
  occurred_at: string
}

interface BudgetStatus {
  category: string
  limit: number
  spent: number
  remaining: number
  percentage: number
  is_flexible: boolean
}

interface ReviewData {
  month: string
  total_spent: number
  total_budget: number
  surplus: number
  category_breakdown: Record<string, { total: number; count: number }>
  tag_breakdown: Record<string, { total: number; count: number }>
  waste_items: { title: string; amount: number; tag: string }[]
  suggestions: string[]
  summary: string
}

const categories = [
  { value: 'food', label: '🍜 餐饮' },
  { value: 'shopping', label: '🛒 购物' },
  { value: 'transport', label: '🚗 交通' },
  { value: 'entertainment', label: '🎮 娱乐' },
  { value: 'study', label: '📚 学习' },
  { value: 'rent', label: '🏠 房租' },
  { value: 'medical', label: '🏥 医疗' },
  { value: 'other', label: '📌 其他' },
]

const tagLabels: Record<string, string> = {
  necessity: '刚需', impulse: '冲动', hoarding: '囤货', fixed: '固定',
}

export default function Consume() {
  const month = new Date().toISOString().slice(0, 7)
  const [records, setRecords] = useState<ConsumeRecord[]>([])
  const [stats, setStats] = useState<any[]>([])
  const [budgets, setBudgets] = useState<BudgetStatus[]>([])
  const [review, setReview] = useState<ReviewData | null>(null)
  const [form, setForm] = useState({ amount: '', category: 'food', merchant: '' })
  const [budgetForm, setBudgetForm] = useState({ category: 'food', monthly_limit: '', is_flexible: false })
  const [showBudget, setShowBudget] = useState(false)
  const [showReview, setShowReview] = useState(false)
  const [importText, setImportText] = useState('')
  const [importSource, setImportSource] = useState('wechat')

  const load = useCallback(() => {
    api(`/consumes?month=${month}`).then(d => setRecords(d.data)).catch(() => {})
    api(`/consumes/stats?month=${month}`).then(d => setStats(d.data)).catch(() => {})
    api(`/consumes/budget/status?month=${month}`).then(d => setBudgets(d.data)).catch(() => {})
  }, [month])

  useEffect(() => { load() }, [load])

  async function add() {
    if (!form.amount) return
    await api('/consumes', { method: 'POST', body: JSON.stringify({ ...form, amount: parseFloat(form.amount) }) })
    setForm({ amount: '', category: 'food', merchant: '' })
    load()
  }

  async function setBudget() {
    if (!budgetForm.monthly_limit) return
    await api('/consumes/budget', { method: 'POST', body: JSON.stringify({
      category: budgetForm.category,
      monthly_limit: parseFloat(budgetForm.monthly_limit),
      is_flexible: budgetForm.is_flexible,
      flex_source_categories: budgetForm.is_flexible ? ['entertainment', 'shopping'] : undefined,
    }) })
    setBudgetForm({ category: 'food', monthly_limit: '', is_flexible: false })
    load()
  }

  async function loadReview() {
    const data = await api(`/consumes/review?month=${month}`)
    setReview(data.data)
    setShowReview(true)
  }

  async function importBill() {
    if (!importText.trim()) return
    try {
      await api('/consumes/import', { method: 'POST', body: JSON.stringify({ content: importText, source: importSource }) })
      setImportText('')
      alert('导入成功')
      load()
    } catch (e: any) {
      alert(`导入失败: ${e.message}`)
    }
  }

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>💰 消费记账</h2>

      {/* 记账 */}
      <div className="card">
        <div className="card-title">记一笔</div>
        <div className="form-row">
          <input type="number" placeholder="金额" step="0.01" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} />
          <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
            {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <input placeholder="商家（可选）" value={form.merchant} onChange={e => setForm({ ...form, merchant: e.target.value })} />
          <button onClick={add}>记账</button>
        </div>
      </div>

      {/* 预算状态 */}
      {budgets.length > 0 && (
        <div className="card">
          <div className="card-title">
            预算使用情况
            <button className="secondary" style={{ marginLeft: 10, padding: '2px 8px', fontSize: 12 }} onClick={() => setShowBudget(!showBudget)}>
              {showBudget ? '隐藏' : '设置'}
            </button>
          </div>
          <div style={{ display: 'grid', gap: 8 }}>
            {budgets.map(b => (
              <div key={b.category} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 60, fontSize: 13 }}>
                  {categories.find(c => c.value === b.category)?.label || b.category}
                </span>
                <div style={{ flex: 1, height: 8, background: '#eee', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(b.percentage, 100)}%`, height: '100%',
                    background: b.percentage >= 95 ? '#e74c3c' : b.percentage >= 80 ? '#f39c12' : '#27ae60',
                    borderRadius: 4, transition: 'width 0.3s',
                  }} />
                </div>
                <span style={{ fontSize: 12, color: '#666', width: 100, textAlign: 'right' }}>
                  ¥{b.spent.toFixed(0)} / ¥{b.limit.toFixed(0)} ({b.percentage}%)
                </span>
                {b.is_flexible && <span className="badge badge-info">弹性</span>}
              </div>
            ))}
          </div>

          {showBudget && (
            <div style={{ marginTop: 15, paddingTop: 15, borderTop: '1px solid #eee' }}>
              <div className="form-row">
                <select value={budgetForm.category} onChange={e => setBudgetForm({ ...budgetForm, category: e.target.value })}>
                  {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <input type="number" placeholder="月度预算" value={budgetForm.monthly_limit} onChange={e => setBudgetForm({ ...budgetForm, monthly_limit: e.target.value })} />
                <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13 }}>
                  <input type="checkbox" checked={budgetForm.is_flexible} onChange={e => setBudgetForm({ ...budgetForm, is_flexible: e.target.checked })} />
                  弹性预算
                </label>
                <button onClick={setBudget}>设置</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 账单导入 */}
      <div className="card">
        <div className="card-title">账单导入（微信/支付宝CSV）</div>
        <div className="form-row">
          <select value={importSource} onChange={e => setImportSource(e.target.value)}>
            <option value="wechat">微信</option>
            <option value="alipay">支付宝</option>
          </select>
          <button onClick={importBill}>导入</button>
        </div>
        <textarea
          placeholder="粘贴CSV账单内容到这里..."
          value={importText}
          onChange={e => setImportText(e.target.value)}
          style={{ width: '100%', height: 80, marginTop: 8, fontSize: 12, fontFamily: 'monospace' }}
        />
      </div>

      {/* 复盘报告 */}
      <div className="card">
        <div className="card-title">
          月度消费复盘
          <button className="secondary" style={{ marginLeft: 10, padding: '2px 8px', fontSize: 12 }} onClick={loadReview}>
            生成报告
          </button>
        </div>
        {review && showReview && (
          <div>
            <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{review.summary}</p>
            <div style={{ display: 'flex', gap: 15, marginBottom: 10 }}>
              <span>总消费: <strong>¥{review.total_spent.toFixed(0)}</strong></span>
              <span>总预算: <strong>¥{review.total_budget.toFixed(0)}</strong></span>
              <span style={{ color: review.surplus >= 0 ? '#27ae60' : '#e74c3c' }}>
                {review.surplus >= 0 ? '结余' : '超支'}: <strong>¥{Math.abs(review.surplus).toFixed(0)}</strong>
              </span>
            </div>
            {review.waste_items.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <strong style={{ fontSize: 13 }}>无效消费：</strong>
                {review.waste_items.map((w, i) => (
                  <span key={i} className="badge badge-danger" style={{ marginRight: 4 }}>{w.title} ¥{w.amount}</span>
                ))}
              </div>
            )}
            <div>
              <strong style={{ fontSize: 13 }}>省钱建议：</strong>
              <ul style={{ margin: '4px 0 0 20px', fontSize: 13, color: '#666' }}>
                {review.suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* 消费列表 */}
      <div>
        <h3 style={{ marginBottom: 10, fontSize: 16 }}>消费记录 ({records.length})</h3>
        {records.length === 0 ? <p style={{ color: '#999' }}>暂无记录</p> : records.slice(0, 30).map(r => (
          <div key={r.id} className="list-item">
            <span>
              {categories.find(c => c.value === r.category)?.label || r.category} {r.merchant || ''}
              {r.tag && <span className="badge badge-info" style={{ marginLeft: 6 }}>{tagLabels[r.tag] || r.tag}</span>}
              {r.is_impulse && <span className="badge badge-danger" style={{ marginLeft: 4 }}>冲动</span>}
            </span>
            <span style={{ fontWeight: 600 }}>¥{r.amount.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
