import { useState, useRef, useEffect } from 'react'
import { api } from '../api/client'

interface Message { role: 'user' | 'bot'; text: string }

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'bot', text: '你好！我是你的智能生活助手。可以问我消费分析、日程安排、学习效率等问题。' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight
  }, [messages])

  async function send() {
    if (!input.trim()) return
    const msg = input.trim()
    setMessages(prev => [...prev, { role: 'user', text: msg }])
    setInput('')
    setLoading(true)
    try {
      const data = await api('/agent/chat', { method: 'POST', body: JSON.stringify({ message: msg }) })
      setMessages(prev => [...prev, { role: 'bot', text: data.data?.response || '暂无回复' }])
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'bot', text: `错误: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 60px)' }}>
      <h2 style={{ marginBottom: 15 }}>💬 智能对话</h2>
      <div ref={boxRef} style={{
        flex: 1, background: '#fff', borderRadius: 12, padding: 20,
        overflowY: 'auto', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', marginBottom: 15,
      }}>
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 15, textAlign: m.role === 'user' ? 'right' : 'left' }}>
            <div style={{
              display: 'inline-block', padding: '10px 16px', borderRadius: 16,
              maxWidth: '70%', lineHeight: 1.6, fontSize: 14,
              background: m.role === 'user' ? '#667eea' : '#f0f0f0',
              color: m.role === 'user' ? '#fff' : '#333',
            }}>{m.text}</div>
          </div>
        ))}
        {loading && <div style={{ color: '#999' }}>思考中...</div>}
      </div>
      <div style={{ display: 'flex', gap: 10 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="输入需求..."
          style={{ flex: 1, padding: '12px 16px' }}
        />
        <button onClick={send} disabled={loading}>发送</button>
      </div>
    </div>
  )
}
