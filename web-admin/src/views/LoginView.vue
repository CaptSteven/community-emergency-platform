<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-left">
        <h1>社区应急互助与灾害预警平台</h1>
        <p>面向社区管理员的预警发布、求助调度、任务处理与数据分析后台。</p>

        <div class="feature-list">
          <div>灾害预警统一发布</div>
          <div>居民求助快速响应</div>
          <div>志愿者任务闭环管理</div>
          <div>应急数据可视化复盘</div>
        </div>
      </div>

      <div class="login-right">
        <h2>管理员登录</h2>
        <p class="hint">请输入管理员账号进入后台系统</p>

        <el-form :model="form" label-position="top" @keyup.enter="handleLogin">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="例如：admin02" />
          </el-form-item>

          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              show-password
            />
          </el-form-item>

          <el-button
            type="primary"
            class="login-button"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form>

        <div class="demo-account">
          测试账号：admin02 / 123456
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import { setAuth, loadUnreadCount } from '../stores/auth'

const router = useRouter()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true

  try {
    const res = await request.post('/auth/login/', {
      username: form.username,
      password: form.password
    })

    const user = res.user

    if (!user || user.role !== 'admin') {
      ElMessage.error('当前账号不是管理员，不能进入后台')
      return
    }

    setAuth({ token: res.token, user })
    await loadUnreadCount()

    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    ElMessage.error('登录失败，请检查账号、密码或后端服务是否正常')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at 20% 20%, rgba(37, 99, 235, 0.28), transparent 28%),
    radial-gradient(circle at 80% 20%, rgba(6, 182, 212, 0.24), transparent 28%),
    linear-gradient(135deg, #0f172a, #1e293b);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
}

.login-card {
  width: 960px;
  min-height: 540px;
  background: #ffffff;
  border-radius: 28px;
  overflow: hidden;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.35);
}

.login-left {
  background: linear-gradient(135deg, #1d4ed8, #0891b2);
  color: white;
  padding: 60px 52px;
}

.login-left h1 {
  font-size: 34px;
  line-height: 1.35;
  margin: 0 0 22px;
}

.login-left p {
  font-size: 16px;
  line-height: 1.8;
  opacity: 0.92;
}

.feature-list {
  margin-top: 40px;
  display: grid;
  gap: 16px;
}

.feature-list div {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(8px);
}

.login-right {
  padding: 64px 48px;
}

.login-right h2 {
  margin: 0;
  font-size: 28px;
}

.hint {
  color: #64748b;
  margin: 10px 0 34px;
}

.login-button {
  width: 100%;
  height: 42px;
  margin-top: 8px;
}

.demo-account {
  margin-top: 20px;
  color: #64748b;
  font-size: 13px;
}
</style>