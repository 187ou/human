import { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

interface Notification {
  id: number
  type: string
  source: string
  title: string
  content: string
  priority: string
  is_read: boolean
  created_at: string
}

const typeIcons: Record<string, string> = {
  schedule_reminder: '📅',
  item_expire: '⏰',
  budget_warning: '💰',
  budget_critical: '🚨',
  budget_exceeded: '❌',
  study_checkin: '📚',
  system: '🔔',
}

const priorityColors: Record<string, string> = {
  low: '#95a5a6',
  normal: '#3498db',
  high: '#f39c12',
  urgent: '#e74c3c',
}

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    try {
      const countData = await api('/notifications/count')
      setUnreadCount(countData.data.unread)
      const listData = await api('/notifications?limit=20')
      setNotifications(listData.data)
    } catch (e) { /* ignore */ }
  }, [])

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t) }, [load])

  async function collect() {
    setLoading(true)
    try {
      await api('/notifications/collect', { method: 'POST' })
      await load()
    } finally { setLoading(false) }
  }

  async function markRead(id: number) {
    await api(`/notifications/${id}/read`, { method: 'POST' })
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
    setUnreadCount(prev => Math.max(0, prev - 1))
  }

  async function markAllRead() {
    await api('/notifications/read-all', { method: 'POST' })
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
    setUnreadCount(0)
  }

  return (
    <div style={{ position: 'fixed', top: 12, right: 20, zIndex: 1000 }}>
      <button onClick={() => setShow(!show)} style={{ position: 'relative' }}>
        🔔
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute', top: -6, right: -6, background: '#e74c3c',
            color: '#fff', borderRadius: 10, fontSize: 11, padding: '1px 5px', minWidth: 18, textAlign: 'center',
          }}>{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {show && (
        <div style={{
          position: 'absolute', right: 0, top: 40, width: 360, maxHeight: 500,
          background: '#fff', borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
          overflow: 'hidden', display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>通知中心</strong>
            <span>
              <button onClick={collect} disabled={loading} style={{ padding: '2px 8px', fontSize: 12, marginRight: 4 }}>
                {loading ? '...' : '刷新'}
              </button>
              <button onClick={markAllRead} style={{ padding: '2px 8px', fontSize: 12 }} className="secondary">全部已读</button>
            </span>
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {notifications.length === 0 ? (
              <div style={{ padding: 20, textAlign: 'center', color: '#999', fontSize: 13 }}>暂无通知</div>
            ) : notifications.map(n => (
              <div key={n.id} onClick={() => markRead(n.id)} style={{
                padding: '10px 16px', borderBottom: '1px solid #f5f5f5', cursor: 'pointer',
                background: n.is_read ? '#fff' : '#f8f9ff',
                borderLeft: `3px solid ${priorityColors[n.priority] || '#ddd'}`,
              }}>
                <div style={{ fontSize: 13, fontWeight: n.is_read ? 400 : 600 }}>
                  {typeIcons[n.type] || '🔔'} {n.title}
                </div>
                <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{n.content}</div>
                <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                  {n.created_at?.slice(5, 16)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
