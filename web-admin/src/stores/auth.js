import { reactive } from 'vue'
import request from '../api/request'

export const authState = reactive({
  user: null,
  token: '',
  unreadCount: 0
})

export const initAuthFromStorage = () => {
  authState.token = localStorage.getItem('token') || ''
  try {
    authState.user = JSON.parse(localStorage.getItem('user') || 'null')
  } catch (error) {
    authState.user = null
    localStorage.removeItem('user')
  }
}

export const setAuth = ({ token, user }) => {
  authState.token = token || ''
  authState.user = user || null

  if (token) {
    localStorage.setItem('token', token)
  }

  if (user) {
    localStorage.setItem('user', JSON.stringify(user))
  }
}

export const clearAuth = () => {
  authState.token = ''
  authState.user = null
  authState.unreadCount = 0
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export const loadUnreadCount = async () => {
  if (!localStorage.getItem('token')) {
    authState.unreadCount = 0
    return
  }

  const res = await request.get('/notifications/unread_count/')
  authState.unreadCount = Number(res.unread_count || 0)
}

initAuthFromStorage()
