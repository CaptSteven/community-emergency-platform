import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const request = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  timeout: 10000
})

// 请求拦截器：自动携带 token
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

// 响应拦截器：统一处理错误
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      const status = error.response.status

      if (status === 401 || status === 403) {
        ElMessage.error('登录状态失效，请重新登录')
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        router.push('/login')
      } else {
        const data = error.response.data
        const message = data.message || data.detail || '请求失败'
        ElMessage.error(message)
      }
    } else {
      ElMessage.error('无法连接后端服务，请检查 Django 是否启动')
    }

    return Promise.reject(error)
  }
)

export default request