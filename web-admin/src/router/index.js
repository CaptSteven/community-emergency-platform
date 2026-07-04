import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '../views/LoginView.vue'
import MainLayout from '../layout/MainLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import WarningView from '../views/WarningView.vue'
import HelpRequestView from '../views/HelpRequestView.vue'
import TaskView from '../views/TaskView.vue'
import ResourceView from '../views/ResourceView.vue'
import NotificationView from '../views/NotificationView.vue'

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
          path: 'warnings',
          component: WarningView
        },
        {
          path: 'help-requests',
          component: HelpRequestView
        },
        {
          path: 'tasks',
          component: TaskView
        },
        {
          path: 'resources',
          component: ResourceView
        },
        {
          path: 'notifications',
          component: NotificationView
        }
      ]
    }
  ]
})

// 路由守卫：没有 token 不能进入后台
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router