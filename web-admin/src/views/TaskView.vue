<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">志愿者任务管理</div>
        <div class="page-subtitle">查看志愿者任务分配、接单、处理与反馈情况。</div>
      </div>
      <el-button type="primary" @click="refreshAll">刷新数据</el-button>
    </div>

    <el-row :gutter="18" class="summary-row">
      <el-col :span="6" v-for="item in taskStatusStats" :key="item.key">
        <div class="summary-card">
          <div class="summary-label">{{ item.label }}</div>
          <div class="summary-value">{{ item.count }}</div>
          <div class="summary-desc">任务状态统计</div>
        </div>
      </el-col>
    </el-row>

    <div class="card filter-card">
      <el-form :inline="true">
        <el-form-item label="任务状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 180px">
            <el-option label="已分配" value="assigned" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="志愿者">
          <el-select v-model="filters.volunteer" placeholder="全部志愿者" clearable filterable style="width: 200px">
            <el-option v-for="item in volunteers" :key="item.id" :label="item.username" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.search" placeholder="搜索描述、地址或志愿者" clearable style="width: 220px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="card">
      <el-table v-loading="loading" :data="tasks" border style="width:100%">
        <el-table-column prop="id" label="任务ID" width="80" />
        <el-table-column prop="help_request" label="求助ID" width="80" />
        <el-table-column label="志愿者" width="120"><template #default="{ row }">{{ row.volunteer_name || '未分配' }}</template></el-table-column>
        <el-table-column prop="help_request_type" label="求助类型" width="120" />
        <el-table-column prop="help_request_description" label="求助描述" min-width="240" show-overflow-tooltip />
        <el-table-column prop="help_request_address" label="求助地址" min-width="180" show-overflow-tooltip />
        <el-table-column label="任务状态" width="110"><template #default="{ row }"><el-tag :type="statusTagType(row.status)">{{ row.status_display }}</el-tag></template></el-table-column>
        <el-table-column label="分配时间" width="180"><template #default="{ row }">{{ formatTime(row.assigned_at) }}</template></el-table-column>
        <el-table-column label="接单时间" width="180"><template #default="{ row }">{{ formatTime(row.accepted_at) }}</template></el-table-column>
        <el-table-column label="完成时间" width="180"><template #default="{ row }">{{ formatTime(row.completed_at) }}</template></el-table-column>
        <el-table-column label="操作" width="120" fixed="right"><template #default="{ row }"><el-button size="small" type="primary" @click="openDetail(row)">详情</el-button></template></el-table-column>
      </el-table>

      <el-pagination class="pagination" background layout="total, sizes, prev, pager, next, jumper" :total="pagination.total" :current-page="pagination.page" :page-size="pagination.pageSize" :page-sizes="[10,20,50]" @size-change="handleSizeChange" @current-change="handlePageChange" />
    </div>

    <el-dialog v-model="detailVisible" title="志愿者任务详情" width="720px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="任务ID">{{ currentTask?.id }}</el-descriptions-item>
        <el-descriptions-item label="求助ID">{{ currentTask?.help_request }}</el-descriptions-item>
        <el-descriptions-item label="志愿者">{{ currentTask?.volunteer_name || '未分配' }}</el-descriptions-item>
        <el-descriptions-item label="求助类型">{{ currentTask?.help_request_type }}</el-descriptions-item>
        <el-descriptions-item label="求助描述">{{ currentTask?.help_request_description }}</el-descriptions-item>
        <el-descriptions-item label="求助地址">{{ currentTask?.help_request_address }}</el-descriptions-item>
        <el-descriptions-item label="任务状态">{{ currentTask?.status_display }}</el-descriptions-item>
        <el-descriptions-item label="处理反馈">{{ currentTask?.feedback || '-' }}</el-descriptions-item>
        <el-descriptions-item label="分配时间">{{ formatTime(currentTask?.assigned_at) }}</el-descriptions-item>
        <el-descriptions-item label="接单时间">{{ formatTime(currentTask?.accepted_at) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatTime(currentTask?.completed_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import request from '../api/request'
import { buildPageParams, unwrapPaginated } from '../utils/pagination'

const loading = ref(false)
const tasks = ref([])
const volunteers = ref([])
const taskStatusStats = ref([])
const detailVisible = ref(false)
const currentTask = ref(null)
const filters = reactive({ status: '', volunteer: '', search: '' })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const loadTasks = async () => {
  loading.value = true
  try {
    const params = { ...buildPageParams(pagination) }
    if (filters.status) params.status = filters.status
    if (filters.volunteer) params.volunteer = filters.volunteer
    if (filters.search) params.search = filters.search
    const data = await request.get('/tasks/', { params })
    const page = unwrapPaginated(data)
    tasks.value = page.list
    pagination.total = page.total
  } finally { loading.value = false }
}

const loadVolunteers = async () => {
  const data = await request.get('/users/', { params: { role: 'volunteer', page_size: 200 } })
  volunteers.value = unwrapPaginated(data).list
}

const loadStats = async () => { taskStatusStats.value = await request.get('/analytics/task-status/') }
const refreshAll = async () => Promise.all([loadTasks(), loadVolunteers(), loadStats()])
const handleSearch = () => { pagination.page = 1; loadTasks() }
const resetFilters = () => { filters.status = ''; filters.volunteer = ''; filters.search = ''; handleSearch() }
const handleSizeChange = size => { pagination.pageSize = size; pagination.page = 1; loadTasks() }
const handlePageChange = page => { pagination.page = page; loadTasks() }
const openDetail = row => { currentTask.value = row; detailVisible.value = true }
const formatTime = value => value ? value.replace('T', ' ').slice(0, 19) : '-'
const statusTagType = status => ({ assigned: 'warning', processing: 'primary', completed: 'success', cancelled: 'info' }[status] || 'info')

onMounted(() => refreshAll())
</script>

<style scoped>
.summary-row { margin-bottom: 18px; }
.summary-card { background:#fff; border-radius:16px; padding:20px; box-shadow:0 8px 24px rgba(15,23,42,.06); border-left:5px solid #2563eb; }
.summary-label { font-size:15px; color:#64748b; }
.summary-value { margin-top:8px; font-size:30px; font-weight:800; color:#1e293b; }
.summary-desc { margin-top:6px; font-size:13px; color:#94a3b8; }
</style>
