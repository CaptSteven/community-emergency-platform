<template>
  <el-container class="layout-container">
    <el-aside width="234px" class="sidebar">
      <div class="logo">
        <div class="logo-icon">社</div>
        <div>
          <div class="logo-title">社区服务平台</div>
          <div class="logo-subtitle">Community Service Admin</div>
        </div>
      </div>

      <el-menu
        router
        :default-active="$route.path"
        background-color="transparent"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
        class="side-menu"
      >
        <!-- 总览：社区服务数据大屏 -->
        <el-menu-item-group title="总览">
          <el-menu-item index="/dashboard">
            <el-icon><DataLine /></el-icon>
            <span>数据大屏</span>
          </el-menu-item>
        </el-menu-item-group>

        <!-- 社区服务：平台主线业务，置顶主分组 -->
        <el-menu-item-group title="社区服务">
          <el-menu-item index="/service-subscriptions" class="svc-item">
            <el-icon><Calendar /></el-icon>
            <span>服务计划管理</span>
          </el-menu-item>
          <el-menu-item index="/service-visits" class="svc-item">
            <el-icon><Tickets /></el-icon>
            <span>排班工单看板</span>
          </el-menu-item>
          <el-menu-item index="/service-types" class="svc-item">
            <el-icon><List /></el-icon>
            <span>服务目录管理</span>
          </el-menu-item>
          <!-- 🗺️ 单次任务地图：一图拖拽派单 -->
          <el-menu-item index="/single-tasks" class="svc-item">
            <el-icon><Location /></el-icon>
            <span>单次任务地图</span>
          </el-menu-item>
          <!-- 🏅 志愿积分排行榜 -->
          <el-menu-item index="/leaderboard" class="svc-item">
            <el-icon><Trophy /></el-icon>
            <span>志愿排行榜</span>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item-group title="系统">
          <el-menu-item index="/users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/notifications">
            <el-icon><Bell /></el-icon>
            <span>站内消息管理</span>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="loc-ico"><Location /></el-icon>
          <span class="loc-root">社区服务平台</span>
          <span class="loc-sep">/</span>
          <span class="loc-current">{{ pageName }}</span>
        </div>

        <div class="header-right">
          <el-badge :value="authState.unreadCount" :hidden="authState.unreadCount <= 0" class="bell-badge">
            <el-button circle :icon="Bell" @click="router.push('/notifications')" />
          </el-badge>

          <span class="user-info">
            {{ authState.user?.username || '管理员' }}
          </span>

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
import { onBeforeUnmount, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { DataLine, Calendar, Tickets, List, User, Bell, Location, Trophy } from '@element-plus/icons-vue'
import { authState, clearAuth, initAuthFromStorage, loadUnreadCount } from '../stores/auth'

const router = useRouter()
const route = useRoute()
let unreadTimer = null

const ROUTE_NAMES = {
  '/dashboard': '数据大屏',
  '/service-subscriptions': '服务计划管理',
  '/service-visits': '排班工单看板',
  '/service-types': '服务目录管理',
  '/single-tasks': '单次任务地图',
  '/leaderboard': '志愿排行榜',
  '/users': '用户管理',
  '/notifications': '站内消息管理'
}
const pageName = computed(() => ROUTE_NAMES[route.path] || '概览')

const logout = async () => {
  await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    type: 'warning'
  })

  clearAuth()
  router.push('/login')
}

onMounted(() => {
  initAuthFromStorage()
  loadUnreadCount().catch(() => {})
  unreadTimer = window.setInterval(() => {
    loadUnreadCount().catch(() => {})
  }, 15000)
})

onBeforeUnmount(() => {
  if (unreadTimer) {
    window.clearInterval(unreadTimer)
    unreadTimer = null
  }
})
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.sidebar {
  /* 深色品牌渐变，层级更立体 */
  background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
  color: #ffffff;
  overflow-y: auto;
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
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 18px;
  color: #ffffff;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.45);
}

.logo-title {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: #94a3b8;
  letter-spacing: 0.5px;
}

.side-menu {
  border-right: none;
  padding: 6px 10px 20px;
}

/* 菜单前的线性图标，统一尺寸与间距 */
.side-menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
  margin-right: 10px;
  width: 20px;
}

/* 分组标题：更精致的层级 */
.side-menu :deep(.el-menu-item-group__title) {
  padding: 16px 12px 6px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1px;
  color: #64748b;
}

/* 菜单项：圆角、留白、字号更易读 */
.side-menu :deep(.el-menu-item) {
  height: 46px;
  line-height: 46px;
  margin: 4px 0;
  padding-left: 14px !important;
  border-radius: 10px;
  font-size: 14.5px;
  color: #cbd5e1;
  transition: background 0.2s ease, color 0.2s ease, transform 0.15s ease;
}

/* hover 反馈 */
.side-menu :deep(.el-menu-item:hover) {
  background: rgba(37, 99, 235, 0.16) !important;
  color: #ffffff !important;
  transform: translateX(2px);
}

/* 激活态：品牌蓝高亮 + 左侧标识条 */
.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.32), rgba(37, 99, 235, 0.14)) !important;
  color: #ffffff !important;
  font-weight: 600;
  box-shadow: inset 3px 0 0 0 #2563eb;
}

/* 社区服务为主线业务：hover / 激活态改用服务绿，强化识别 */
.side-menu :deep(.svc-item:hover) {
  background: rgba(22, 163, 74, 0.16) !important;
}

.side-menu :deep(.svc-item.is-active) {
  background: linear-gradient(90deg, rgba(22, 163, 74, 0.32), rgba(22, 163, 74, 0.14)) !important;
  box-shadow: inset 3px 0 0 0 #16a34a;
}

.header {
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

/* 头部改为面包屑式当前位置，不再与页内标题抢层级 */
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: #64748b;
}

.loc-ico {
  font-size: 16px;
  color: #94a3b8;
}

.loc-root {
  color: #64748b;
}

.loc-sep {
  color: #cbd5e1;
}

.loc-current {
  color: #1e293b;
  font-weight: 700;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-info {
  color: #475569;
  font-weight: 600;
}

.bell-badge :deep(.el-button) {
  font-size: 15px;
}

.main {
  background: #f3f6fb;
  padding: 0;
}
</style>
