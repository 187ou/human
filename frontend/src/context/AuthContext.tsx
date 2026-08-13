import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api, getToken, setToken, clearToken } from '../api/client'

interface User {
  id: number
  username: string
  user_type: string
  wake_hour?: number
  sleep_hour?: number
}

interface Role {
  id: number
  username: string
  user_type: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  roles: Role[]
  selectRole: (userId: number) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  roles: [],
  selectRole: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (getToken()) {
      api('/auth/me').then(d => setUser(d.data)).catch(() => { clearToken() }).finally(() => setLoading(false))
    } else {
      api('/auth/roles').then(d => setRoles(d.data)).catch(() => {}).finally(() => setLoading(false))
    }
  }, [])

  const selectRole = useCallback(async (userId: number) => {
    const data = await api('/auth/select', { method: 'POST', body: JSON.stringify({ user_id: userId }) })
    setToken(data.data.access_token)
    setUser(data.data.user)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
    api('/auth/roles').then(d => setRoles(d.data)).catch(() => {})
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, roles, selectRole, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
