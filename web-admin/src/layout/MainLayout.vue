<template>
  <el-container class="layout-container">
    <el-aside width="230px" class="sidebar">
      <div class="logo">
        <div class="logo-icon">应</div>
        <div>
          <div class="logo-title">社区应急平台</div>
          <div class="logo-subtitle">Emergency Admin</div>
        </div>
      </div>

      <el-menu
        router
        :default-active="$route.path"
        background-color="#111827"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
        class="side-menu"
      >
        <el-menu-item index="/dashboard">
          <span>数据大屏</span>
        </el-menu-item>

        <el-menu-item index="/warnings">
          <span>灾害预警管理</span>
        </el-menu-item>

        <el-menu-item index="/help-requests">
          <span>居民求助管理</span>
        </el-menu-item>

        <el-menu-item index="/tasks">
          <span>志愿者任务管理</span>
        </el-menu-item>

        <el-menu-item index="/resources">
          <span>应急资源管理</span>
        </el-menu-item>

        <el-menu-item index="/notifications">
          <span>站内消息管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          基于 HarmonyOS 的社区应急互助与灾害预警服务平台
        </div>

        <div class="header-right">
          <span class="user-info">{{ user?.username || '管理员' }}</span>
          <el-button type="danger" plain size="small" @click="logout">
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

const router = useRouter()

const user = computed(() => {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
})

const logout = async () => {
  await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    type: 'warning'
  })

  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.sidebar {
  background: #111827;
  color: #ffffff;
}

.logo {
  height: 74px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
}

.logo-title {
  font-size: 17px;
  font-weight: 700;
}

.logo-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: #94a3b8;
}

.side-menu {
  border-right: none;
}

.header {
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  font-size: 18px;
  font-weight: 700;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-info {
  color: #475569;
}

.main {
  background: #f3f6fb;
  padding: 0;
}
</style>