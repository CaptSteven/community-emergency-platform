<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">居民求助管理</div>
        <div class="page-subtitle">查看居民求助事件，并为待处理求助分配志愿者。</div>
      </div>

      <el-button type="primary" @click="loadData">
        刷新数据
      </el-button>
    </div>

    <div class="card filter-card">
      <el-form :inline="true">
        <el-form-item label="处理状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 180px">
            <el-option label="待处理" value="pending" />
            <el-option label="已分配" value="assigned" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>

        <el-form-item label="紧急程度">
          <el-select v-model="filters.urgency" placeholder="全部紧急程度" clearable style="width: 180px">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="critical" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="card">
      <el-table
        v-loading="loading"
        :data="helpRequests"
        border
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="70" />

        <el-table-column prop="resident_name" label="求助居民" width="120" />

        <el-table-column prop="request_type_display" label="求助类型" width="120" />

        <el-table-column label="紧急程度" width="110">
          <template #default="{ row }">
            <el-tag :type="urgencyTagType(row.urgency)">
              {{ row.urgency_display }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="求助描述" min-width="240" show-overflow-tooltip />

        <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />

        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="提交时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDetail(row)">
              详情
            </el-button>

            <el-button
              v-if="row.status === 'pending'"
              size="small"
              type="primary"
              @click="openAssignDialog(row)"
            >
              分配志愿者
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 求助详情弹窗 -->
    <el-dialog v-model="detailVisible" title="求助详情" width="620px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="求助居民">
          {{ currentRequest?.resident_name }}
        </el-descriptions-item>

        <el-descriptions-item label="求助类型">
          {{ currentRequest?.request_type_display }}
        </el-descriptions-item>

        <el-descriptions-item label="紧急程度">
          {{ currentRequest?.urgency_display }}
        </el-descriptions-item>

        <el-descriptions-item label="处理状态">
          {{ currentRequest?.status_display }}
        </el-descriptions-item>

        <el-descriptions-item label="求助描述">
          {{ currentRequest?.description }}
        </el-descriptions-item>

        <el-descriptions-item label="求助地址">
          {{ currentRequest?.address }}
        </el-descriptions-item>

        <el-descriptions-item label="经纬度">
          {{ currentRequest?.latitude || '-' }}，{{ currentRequest?.longitude || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="提交时间">
          {{ formatTime(currentRequest?.created_at) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 分配志愿者弹窗 -->
    <el-dialog v-model="assignVisible" title="分配志愿者" width="520px">
      <el-form label-position="top">
        <el-form-item label="当前求助">
          <el-input :model-value="currentRequest?.description" disabled />
        </el-form-item>

        <el-form-item label="选择志愿者">
          <el-select
            v-model="assignForm.volunteer_id"
            placeholder="请选择志愿者"
            style="width: 100%"
          >
            <el-option
              v-for="item in volunteers"
              :key="item.id"
              :label="`${item.username}（${item.phone || '无电话'}）`"
              :value="item.id"
              :disabled="!item.is_available"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="assignLoading" @click="submitAssign">
          确认分配
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const loading = ref(false)
const assignLoading = ref(false)

const helpRequests = ref([])
const volunteers = ref([])

const detailVisible = ref(false)
const assignVisible = ref(false)
const currentRequest = ref(null)

const filters = reactive({
  status: '',
  urgency: ''
})

const assignForm = reactive({
  volunteer_id: null
})

const loadData = async () => {
  loading.value = true

  try {
    const params = {}

    if (filters.status) {
      params.status = filters.status
    }

    if (filters.urgency) {
      params.urgency = filters.urgency
    }

    helpRequests.value = await request.get('/help-requests/', { params })
  } finally {
    loading.value = false
  }
}

const loadVolunteers = async () => {
  volunteers.value = await request.get('/users/', {
    params: {
      role: 'volunteer'
    }
  })
}

const resetFilters = () => {
  filters.status = ''
  filters.urgency = ''
  loadData()
}

const openDetail = row => {
  currentRequest.value = row
  detailVisible.value = true
}

const openAssignDialog = async row => {
  currentRequest.value = row
  assignForm.volunteer_id = null
  await loadVolunteers()
  assignVisible.value = true
}

const submitAssign = async () => {
  if (!assignForm.volunteer_id) {
    ElMessage.warning('请选择志愿者')
    return
  }

  assignLoading.value = true

  try {
    await request.post(`/help-requests/${currentRequest.value.id}/assign/`, {
      volunteer_id: assignForm.volunteer_id
    })

    ElMessage.success('任务分配成功')
    assignVisible.value = false
    loadData()
  } finally {
    assignLoading.value = false
  }
}

const formatTime = value => {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

const statusTagType = status => {
  const map = {
    pending: 'warning',
    assigned: 'primary',
    processing: 'primary',
    completed: 'success',
    cancelled: 'info'
  }

  return map[status] || 'info'
}

const urgencyTagType = urgency => {
  const map = {
    low: 'info',
    medium: 'primary',
    high: 'warning',
    critical: 'danger'
  }

  return map[urgency] || 'info'
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.page-subtitle {
  margin-top: 6px;
  color: #64748b;
  font-size: 14px;
}

.filter-card {
  margin-bottom: 18px;
}
</style>