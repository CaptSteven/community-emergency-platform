import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '../views/LoginView.vue'
import MainLayout from '../layout/MainLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import NotificationView from '../views/NotificationView.vue'
import UserView from '../views/UserView.vue'
import ServiceTypeView from '../views/ServiceTypeView.vue'
import ServiceSubscriptionView from '../views/ServiceSubscriptionView.vue'
import ServiceVisitView from '../views/ServiceVisitView.vue'
import SingleTaskMapView from '../views/SingleTaskMapView.vue'
import LeaderboardView from '../views/LeaderboardView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/login',
      component: LoginView
    },
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: 'dashboard',
          component: DashboardView
        },
        {
          path: 'service-types',
          component: ServiceTypeView
        },
        {
          path: 'service-subscriptions',
          component: ServiceSubscriptionView
        },
        {
          path: 'service-visits',
          component: ServiceVisitView
        },
        {
          // 单次任务地图：一图管理待派单单次任务
          path: 'single-tasks',
          component: SingleTaskMapView
        },
        {
          // 志愿积分排行榜
          path: 'leaderboard',
          component: LeaderboardView
        },
        {
          path: 'notifications',
          component: NotificationView
        },
        {
          path: 'users',
          component: UserView
        }
      ]
    }
  ]
})

// 路由守卫：没有 token 不能进入后台
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const rawUser = localStorage.getItem('user')

  let user = null

  try {
    user = rawUser ? JSON.parse(rawUser) : null
  } catch (e) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  if (to.path === '/login') {
    if (token && user?.role === 'admin') {
      next('/dashboard')
    } else {
      next()
    }
    return
  }

  if (!token) {
    next('/login')
    return
  }

  if (user?.role !== 'admin') {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    next('/login')
    return
  }

  next()
})

export default router