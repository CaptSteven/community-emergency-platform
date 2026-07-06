<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-left">
        <div class="brand">
          <div class="brand-logo">🏘️</div>
          <div class="brand-name">社区服务平台</div>
        </div>
        <p class="brand-tagline">基于 HarmonyOS 的社区服务与应急互助平台</p>

        <div class="feature-list">
          <div class="feature-item">
            <span class="feature-ico">🤝</span>
            <div>
              <div class="feature-title">社区长期服务</div>
              <div class="feature-text">上门关怀、居家帮扶一站式排班</div>
            </div>
          </div>
          <div class="feature-item">
            <span class="feature-ico">🚨</span>
            <div>
              <div class="feature-title">应急求助响应</div>
              <div class="feature-text">居民求助快速受理与派单</div>
            </div>
          </div>
          <div class="feature-item">
            <span class="feature-ico">🙋</span>
            <div>
              <div class="feature-title">志愿者任务闭环</div>
              <div class="feature-text">接单、服务、完成全流程跟踪</div>
            </div>
          </div>
          <div class="feature-item">
            <span class="feature-ico">📊</span>
            <div>
              <div class="feature-title">数据可视化复盘</div>
              <div class="feature-text">运行态势与资源一屏掌握</div>
            </div>
          </div>
        </div>
      </div>

      <div class="login-right">
        <div class="login-right-inner">
          <h2>管理员登录</h2>
          <p class="hint">请输入管理员账号进入后台管理系统</p>

          <el-form :model="form" label-position="top" @keyup.enter="handleLogin">
            <el-form-item label="用户名">
              <el-input
                v-model="form.username"
                size="large"
                placeholder="例如：admin02"
                :prefix-icon="User"
              />
            </el-form-item>

            <el-form-item label="密码">
              <el-input
                v-model="form.password"
                type="password"
                size="large"
                placeholder="请输入密码"
                show-password
                :prefix-icon="Lock"
              />
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              class="login-button"
              :loading="loading"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form>

          <div class="demo-account">
            测试账号：admin02 / 123456
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import request from '../api/request'
import { setAuth, loadUnreadCount } from '../stores/auth'

const router = useRouter()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const handleLogin = async () => {
  const username = form.username.trim()
  const password = form.password.trim()

  if (!username || !password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true

  try {
    const res = await request.post('/auth/login/', {
      username,
      password
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
    const message = error?.response?.data?.message || '登录失败，请检查账号、密码或后端服务是否正常'
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at 18% 22%, rgba(37, 99, 235, 0.35), transparent 30%),
    radial-gradient(circle at 82% 18%, rgba(22, 163, 74, 0.28), transparent 32%),
    radial-gradient(circle at 75% 85%, rgba(6, 182, 212, 0.22), transparent 30%),
    linear-gradient(135deg, #0f172a, #1e293b);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px;
}

.login-card {
  width: 960px;
  min-height: 560px;
  background: #ffffff;
  border-radius: 24px;
  overflow: hidden;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.4);
}

/* 左侧品牌区：蓝→绿品牌渐变，体现社区服务基调 */
.login-left {
  position: relative;
  overflow: hidden;
  background: linear-gradient(150deg, #1d4ed8 0%, #2563eb 45%, #0891b2 100%);
  color: white;
  padding: 56px 52px;
}

.login-left::after {
  content: "";
  position: absolute;
  bottom: -80px;
  left: -60px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: rgba(22, 163, 74, 0.28);
  filter: blur(8px);
}

.brand {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-logo {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(6px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);
}

.brand-name {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 1px;
}

.brand-tagline {
  position: relative;
  z-index: 1;
  margin: 20px 0 0;
  font-size: 15px;
  line-height: 1.8;
  opacity: 0.9;
}

.feature-list {
  position: relative;
  z-index: 1;
  margin-top: 40px;
  display: grid;
  gap: 14px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(8px);
  transition: background 0.2s ease, transform 0.2s ease;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.22);
  transform: translateX(4px);
}

.feature-ico {
  font-size: 24px;
  line-height: 1;
}

.feature-title {
  font-size: 16px;
  font-weight: 700;
}

.feature-text {
  margin-top: 3px;
  font-size: 13px;
  opacity: 0.86;
}

.login-right {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
}

.login-right-inner {
  width: 100%;
  max-width: 340px;
}

.login-right h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 800;
  color: #1f2937;
}

.hint {
  color: #64748b;
  margin: 10px 0 30px;
  font-size: 14px;
}

.login-button {
  width: 100%;
  height: 46px;
  margin-top: 10px;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 4px;
  border-radius: 12px;
}

.demo-account {
  margin-top: 20px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 13px;
  text-align: center;
}

@media (max-width: 820px) {
  .login-card {
    grid-template-columns: 1fr;
    width: 100%;
    max-width: 440px;
  }

  .login-left {
    display: none;
  }
}
</style>