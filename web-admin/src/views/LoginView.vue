<template>
  <div class="login-page">
    <!-- 左侧品牌区：整屏铺满，消除“小卡漂浮”感 -->
    <div class="login-left">
      <div class="brand">
        <div class="brand-logo">社</div>
        <div>
          <div class="brand-name">社区服务平台</div>
          <div class="brand-sub">Community Service Admin</div>
        </div>
      </div>
      <p class="brand-tagline">基于 HarmonyOS 的社区周期服务管理平台</p>

      <div class="feature-list">
        <div class="feature-item">
          <el-icon class="feature-ico"><Calendar /></el-icon>
          <div>
            <div class="feature-title">周期上门排班</div>
            <div class="feature-text">健康检查、助浴、代购等按周期自动安排</div>
          </div>
        </div>
        <div class="feature-item">
          <el-icon class="feature-ico"><Connection /></el-icon>
          <div>
            <div class="feature-title">技能匹配派单</div>
            <div class="feature-text">按志愿者技能就近轮流自动分配</div>
          </div>
        </div>
        <div class="feature-item">
          <el-icon class="feature-ico"><CircleCheck /></el-icon>
          <div>
            <div class="feature-title">服务闭环追踪</div>
            <div class="feature-text">开始 / 完成 / 健康记录全程留痕</div>
          </div>
        </div>
        <div class="feature-item">
          <el-icon class="feature-ico"><DataAnalysis /></el-icon>
          <div>
            <div class="feature-title">数据看板复盘</div>
            <div class="feature-text">服务覆盖与志愿者负载一屏掌握</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="login-right">
      <div class="login-right-inner">
        <h2>管理员登录</h2>
        <p class="hint">请输入管理员账号进入后台管理系统</p>

        <el-form :model="form" label-position="top" @keyup.enter="handleLogin">
          <el-form-item label="用户名">
            <el-input v-model="form.username" size="large" placeholder="例如：admin02" :prefix-icon="User" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" size="large" placeholder="请输入密码" show-password :prefix-icon="Lock" />
          </el-form-item>
          <el-button type="primary" size="large" class="login-button" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form>

        <div v-if="isDev" class="demo-account">演示账号：admin02 / 123456</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Calendar, Connection, CircleCheck, DataAnalysis } from '@element-plus/icons-vue'
import request from '../api/request'
import { setAuth, loadUnreadCount } from '../stores/auth'

const router = useRouter()
const loading = ref(false)
const isDev = import.meta.env.DEV

const form = reactive({ username: '', password: '' })

const handleLogin = async () => {
  const username = form.username.trim()
  const password = form.password.trim()
  if (!username || !password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await request.post('/auth/login/', { username, password })
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
/* 整屏左右分栏，铺满视口，彻底消除“小卡漂浮”感 */
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(420px, 44%) 1fr;
}

.login-left {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 64px 60px;
  color: #fff;
  background: linear-gradient(150deg, #1d4ed8 0%, #2563eb 48%, #0891b2 100%);
}

.login-left::after {
  content: "";
  position: absolute;
  bottom: -120px;
  left: -80px;
  width: 340px;
  height: 340px;
  border-radius: 50%;
  background: rgba(22, 163, 74, 0.22);
  filter: blur(10px);
}

.brand {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-logo {
  width: 58px;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  font-weight: 800;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(6px);
}

.brand-name {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 1px;
}

.brand-sub {
  margin-top: 4px;
  font-size: 13px;
  letter-spacing: 2px;
  opacity: 0.8;
}

.brand-tagline {
  position: relative;
  z-index: 1;
  margin: 22px 0 0;
  font-size: 15px;
  line-height: 1.8;
  opacity: 0.9;
}

.feature-list {
  position: relative;
  z-index: 1;
  margin-top: 44px;
  display: grid;
  gap: 14px;
  max-width: 420px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 15px 18px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(8px);
  transition: background 0.2s ease, transform 0.2s ease;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateX(4px);
}

.feature-ico {
  font-size: 22px;
  color: #fff;
}

.feature-title {
  font-size: 16px;
  font-weight: 700;
}

.feature-text {
  margin-top: 3px;
  font-size: 13px;
  opacity: 0.85;
}

.login-right {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: #ffffff;
}

.login-right-inner {
  width: 100%;
  max-width: 360px;
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
  height: 48px;
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

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
  }
  .login-left {
    display: none;
  }
}
</style>
