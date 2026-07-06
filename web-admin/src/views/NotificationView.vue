<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">站内消息管理</div>
        <div class="page-subtitle">查看社区服务的派单、完成、取消申请与系统通知等站内消息。</div>
      </div>
      <div>
        <el-button @click="loadData">刷新</el-button>
        <el-button type="primary" @click="markAllRead">全部标记已读</el-button>
      </div>
    </div>

    <el-row :gutter="18" class="summary-row">
      <el-col :span="6"><div class="summary-card"><div class="summary-label">消息总数</div><div class="summary-value">{{ pagination.total }}</div><div class="summary-desc">当前筛选结果数量</div></div></el-col>
      <el-col :span="6"><div class="summary-card danger"><div class="summary-label">全局未读消息</div><div class="summary-value">{{ authState.unreadCount }}</div><div class="summary-desc">Header 小红点同步显示</div></div></el-col>
      <el-col :span="6"><div class="summary-card warning"><div class="summary-label">本页服务消息</div><div class="summary-value">{{ serviceCount }}</div><div class="summary-desc">社区服务相关通知</div></div></el-col>
      <el-col :span="6"><div class="summary-card success"><div class="summary-label">本页系统消息</div><div class="summary-value">{{ systemCount }}</div><div class="summary-desc">系统通知数量</div></div></el-col>
    </el-row>

    <div class="card filter-card">
      <el-form :inline="true">
        <el-form-item label="消息类型">
          <el-select v-model="filters.category" placeholder="全部类型" clearable style="width: 180px">
            <el-option label="社区服务" value="service" />
            <el-option label="系统消息" value="system" />
          </el-select>
        </el-form-item>
        <el-form-item label="阅读状态">
          <el-select v-model="filters.is_read" placeholder="全部状态" clearable style="width: 160px">
            <el-option label="未读" value="false" />
            <el-option label="已读" value="true" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="card">
      <el-table v-loading="loading" :data="notifications" border style="width:100%" :row-class-name="rowClassName">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.is_read ? 'info' : 'danger'">{{ row.is_read ? '已读' : '未读' }}</el-tag></template></el-table-column>
        <el-table-column label="消息类型" width="120"><template #default="{ row }"><el-tag :type="categoryTagType(row.category)">{{ row.category_display }}</el-tag></template></el-table-column>
        <el-table-column prop="title" label="消息标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="content" label="消息内容" min-width="280" show-overflow-tooltip />
        <el-table-column prop="recipient_name" label="接收人" width="120" />
        <el-table-column label="关联对象" width="150"><template #default="{ row }"><span v-if="row.related_type && row.related_id">{{ relatedTypeText(row.related_type) }} #{{ row.related_id }}</span><span v-else>-</span></template></el-table-column>
        <el-table-column label="创建时间" width="180"><template #default="{ row }">{{ formatTime(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="220" fixed="right"><template #default="{ row }"><el-button size="small" @click="openDetail(row)">详情</el-button><el-button v-if="!row.is_read" size="small" type="primary" @click="markRead(row)">标记已读</el-button><el-button size="small" type="danger" @click="deleteNotification(row)">删除</el-button></template></el-table-column>
      </el-table>

      <el-pagination class="pagination" background layout="total, sizes, prev, pager, next, jumper" :total="pagination.total" :current-page="pagination.page" :page-size="pagination.pageSize" :page-sizes="[10,20,50]" @size-change="handleSizeChange" @current-change="handlePageChange" />
    </div>

    <el-dialog v-model="detailVisible" title="消息详情" width="650px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="消息标题">{{ currentNotification?.title }}</el-descriptions-item>
        <el-descriptions-item label="消息类型">{{ currentNotification?.category_display }}</el-descriptions-item>
        <el-descriptions-item label="阅读状态">{{ currentNotification?.is_read ? '已读' : '未读' }}</el-descriptions-item>
        <el-descriptions-item label="接收人">{{ currentNotification?.recipient_name }}</el-descriptions-item>
        <el-descriptions-item label="消息内容">{{ currentNotification?.content }}</el-descriptions-item>
        <el-descriptions-item label="关联对象"><span v-if="currentNotification?.related_type && currentNotification?.related_id">{{ relatedTypeText(currentNotification.related_type) }} #{{ currentNotification.related_id }}</span><span v-else>-</span></el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(currentNotification?.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'
import { authState, loadUnreadCount } from '../stores/auth'
import { buildPageParams, unwrapPaginated } from '../utils/pagination'

const loading = ref(false)
const notifications = ref([])
const detailVisible = ref(false)
const currentNotification = ref(null)
const filters = reactive({ category: '', is_read: '' })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const serviceCount = computed(() => notifications.value.filter(item => item.category === 'service').length)
const systemCount = computed(() => notifications.value.filter(item => item.category === 'system').length)

const loadData = async () => {
  loading.value = true
  try {
    const params = { ...buildPageParams(pagination) }
    if (filters.category) params.category = filters.category
    if (filters.is_read !== '') params.is_read = filters.is_read
    const data = await request.get('/notifications/', { params })
    const page = unwrapPaginated(data)
    notifications.value = page.list
    pagination.total = page.total
    await loadUnreadCount().catch(() => {})
  } finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; loadData() }
const resetFilters = () => { filters.category = ''; filters.is_read = ''; handleSearch() }
const handleSizeChange = size => { pagination.pageSize = size; pagination.page = 1; loadData() }
const handlePageChange = page => { pagination.page = page; loadData() }
const openDetail = row => { currentNotification.value = row; detailVisible.value = true; if (!row.is_read) markRead(row, false) }
const markRead = async (row, showMessage = true) => { await request.post(`/notifications/${row.id}/mark_read/`); row.is_read = true; await loadUnreadCount(); if (showMessage) ElMessage.success('已标记为已读') }
const markAllRead = async () => { await request.post('/notifications/mark_all_read/'); ElMessage.success('已全部标记为已读'); await loadData() }
const deleteNotification = async row => { await ElMessageBox.confirm(`确定要删除消息「${row.title}」吗？`, '提示', { type: 'warning' }); await request.delete(`/notifications/${row.id}/`); ElMessage.success('删除成功'); await loadData() }
const categoryTagType = category => ({ service: 'success', system: 'info', warning: 'danger', help_request: 'warning', task: 'primary' }[category] || 'info')
const relatedTypeText = type => ({ service_visit: '上门服务', service_subscription: '服务计划', user: '用户', warning: '灾害预警', help_request: '居民求助', task: '志愿者任务' }[type] || type)
const rowClassName = ({ row }) => row.is_read ? '' : 'unread-row'
const formatTime = value => value ? value.replace('T', ' ').slice(0, 19) : '-'

onMounted(() => loadData())
</script>

<style scoped>
.summary-row { margin-bottom: 18px; }
.summary-card { background:#fff; border-radius:16px; padding:20px; box-shadow:0 8px 24px rgba(15,23,42,.06); border-left:5px solid #2563eb; }
.summary-card.danger { border-left-color:#ef4444; }
.summary-card.warning { border-left-color:#f59e0b; }
.summary-card.success { border-left-color:#10b981; }
.summary-label { font-size:15px; color:#64748b; }
.summary-value { margin-top:8px; font-size:30px; font-weight:800; color:#1e293b; }
.summary-desc { margin-top:6px; font-size:13px; color:#94a3b8; }
:deep(.unread-row) { background-color:#fff7ed; }
</style>
