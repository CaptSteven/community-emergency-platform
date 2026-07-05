import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  timeout: 10000
})

// 请求拦截器：自动携带 Token
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')

    if (token) {
      config.headers.Authorization = `Token ${token}`
    }

    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器：统一处理后端错误
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const status = error.response?.status
    const data = error.response?.data

    let message = '请求失败，请稍后重试'

    if (typeof data === 'string') {
      message = data
    } else if (data?.message) {
      message = data.message
    } else if (data?.detail) {
      message = data.detail
    } else if (data && typeof data === 'object') {
      const firstKey = Object.keys(data)[0]
      if (firstKey && Array.isArray(data[firstKey])) {
        message = data[firstKey][0]
      }
    }

    if (status === 401) {
      ElMessage.error('登录已失效，请重新登录')
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
    } else if (status === 403) {
      ElMessage.error('没有权限执行该操作')
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请检查后端服务是否正常')
    } else if (!error.response) {
      ElMessage.error('无法连接后端服务，请确认 Django 已启动')
    } else {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  }
)

export default request