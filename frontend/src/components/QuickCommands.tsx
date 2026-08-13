import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface QuickCommand {
  id: string
  icon: string
  label: string
  template: string
  example: string
  type: string
}

export default function QuickCommands({ onResult }: { onResult?: (msg: string) => void }) {
  const [commands, setCommands] = useState<QuickCommand[]>([])
  const [show, setShow] = useState(false)

  useEffect(() => {
    api('/nlp/quick-commands').then(d => setCommands(d.data)).catch(() => {})
  }, [])

  async function execute(cmd: QuickCommand) {
    let text = cmd.example
    if (cmd.type === 'record_consume') {
      const amount = prompt('金额？', '35')
      if (!amount) return
      text = `记一笔${amount}块的外卖`
    } else if (cmd.type === 'create_schedule') {
      const title = prompt('日程内容？', '')
      if (!title) return
      text = `明天做${title}`
    }

    try {
      const parsed = await api('/nlp/parse', { method: 'POST', body: JSON.stringify({ text }) })
      if (onResult) {
        onResult(`已解析: ${parsed.data.type} - ${JSON.stringify(parsed.data.params)}`)
      }
      setShow(false)
    } catch (e: any) {
      alert(`解析失败: ${e.message}`)
    }
  }

  return (
    <div style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 1000 }}>
      <button onClick={() => setShow(!show)} style={{
        width: 56, height: 56, borderRadius: 28, fontSize: 24,
        boxShadow: '0 4px 16px rgba(102,126,234,0.4)',
      }}>+</button>

      {show && (
        <div style={{
          position: 'absolute', bottom: 65, right: 0, width: 280,
          background: '#fff', borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
          padding: 12,
        }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>快捷指令</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {commands.map(cmd => (
              <div key={cmd.id} onClick={() => execute(cmd)} style={{
                padding: '8px', borderRadius: 8, background: '#f8f9fa', cursor: 'pointer',
                textAlign: 'center', transition: 'background 0.2s',
              }}
                onMouseEnter={e => (e.currentTarget.style.background = '#e8eaff')}
                onMouseLeave={e => (e.currentTarget.style.background = '#f8f9fa')}
              >
                <div style={{ fontSize: 20 }}>{cmd.icon}</div>
                <div style={{ fontSize: 11, color: '#666' }}>{cmd.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
