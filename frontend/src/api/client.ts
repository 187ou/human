const TOKEN_KEY = 'humanagent_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export async function api(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`/api${path}`, { ...options, headers })
  if (res.status === 401) {
    clearToken()
    window.location.reload()
    throw new Error('登录已过期')
  }
  const data = await res.json()
  if (res.ok) return data
  throw new Error(data.detail || '请求失败')
}
