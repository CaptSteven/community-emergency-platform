<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">居民求助管理</div>
        <div class="page-subtitle">查看居民求助事件，并为待处理求助分配志愿者。</div>
      </div>

      <el-button type="primary" :loading="loading" @click="loadData">
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

        <el-form-item label="关键词">
          <el-input
            v-model="filters.search"
            placeholder="搜索居民、描述、摘要或地址"
            clearable
            style="width: 240px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="card">
      <el-table v-loading="loading" :data="helpRequests" border style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="resident_name" label="求助居民" width="120" />
        <el-table-column prop="request_type_display" label="求助类型" width="120" />

        <el-table-column label="紧急程度" width="110">
          <template #default="{ row }">
            <el-tag :type="urgencyTagType(row.urgency)">{{ row.urgency_display }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="智能摘要" min-width="210" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="summary-text">{{ row.ai_summary || '待生成摘要' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="求助描述" min-width="240" show-overflow-tooltip />
        <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />

        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :color="statusColor(row.status)" effect="dark" style="border-color: transparent">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>

        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDetail(row)">详情</el-button>
            <el-button v-if="row.status === 'pending'" size="small" type="primary" @click="openAssignDialog(row)">
              分配志愿者
            </el-button>
            <el-button v-if="row.status !== 'completed' && row.status !== 'cancelled'" size="small" type="danger" @click="cancelRequest(row)">
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="pagination.total"
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50]"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <el-dialog v-model="detailVisible" title="求助详情" width="760px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="求助居民">{{ currentRequest?.resident_name }}</el-descriptions-item>
        <el-descriptions-item label="求助类型">{{ currentRequest?.request_type_display }}</el-descriptions-item>
        <el-descriptions-item label="紧急程度">{{ currentRequest?.urgency_display }}</el-descriptions-item>
        <el-descriptions-item label="处理状态">{{ currentRequest?.status_display }}</el-descriptions-item>
        <el-descriptions-item label="智能摘要">{{ currentRequest?.ai_summary || '-' }}</el-descriptions-item>
        <el-descriptions-item label="求助描述">{{ currentRequest?.description }}</el-descriptions-item>
        <el-descriptions-item label="求助地址">{{ currentRequest?.address }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ formatTime(currentRequest?.created_at) }}</el-descriptions-item>
      </el-descriptions>

      <div class="detail-map-title">求助地理位置</div>
      <BaiduMapPicker
        v-if="detailVisible"
        :latitude="currentRequest?.latitude"
        :longitude="currentRequest?.longitude"
        :address="currentRequest?.address"
        readonly
        height="300px"
      />
    </el-dialog>

    <el-dialog v-model="assignVisible" title="分配志愿者" width="720px">
      <el-form label-position="top">
        <el-form-item label="当前求助">
          <el-input :model-value="currentRequest?.ai_summary || currentRequest?.description" disabled />
        </el-form-item>

        <div class="recommend-bar">
          <div>
            <div class="recommend-title">AI 应急调度辅助</div>
            <div class="recommend-subtitle">综合距离、空闲状态、社区和擅长任务推荐 3 名志愿者。</div>
          </div>
          <el-button type="success" :loading="recommendLoading" @click="loadRecommendations">一键智能推荐</el-button>
        </div>

        <div v-if="recommendations.length" class="recommend-list">
          <div
            v-for="item in recommendations"
            :key="item.id"
            class="recommend-card"
            :class="{ selected: assignForm.volunteer_id === item.id }"
            @click="assignForm.volunteer_id = item.id"
          >
            <div class="recommend-score">{{ item.score }}</div>
            <div>
              <div class="recommend-name">{{ item.username }} <span>{{ item.phone || '无电话' }}</span></div>
              <div class="recommend-reason">{{ item.reasons.join('、') }}</div>
              <div class="recommend-reason">擅长：{{ item.skills || '未登记' }}</div>
            </div>
          </div>
        </div>

        <el-form-item label="选择志愿者">
          <el-select v-model="assignForm.volunteer_id" placeholder="请选择志愿者" filterable style="width: 100%">
            <el-option
              v-for="item in volunteers"
              :key="item.id"
              :label="`${item.username}（${item.phone || '无电话'}｜${item.is_available ? '空闲' : '忙碌'}）`"
              :value="item.id"
              :disabled="!item.is_available"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="assignLoading" @click="submitAssign">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'
import { buildPageParams, unwrapPaginated } from '../utils/pagination'
import BaiduMapPicker from '../components/BaiduMapPicker.vue'

const loading = ref(false)
const assignLoading = ref(false)
const recommendLoading = ref(false)

const helpRequests = ref([])
const volunteers = ref([])
const recommendations = ref([])
const detailVisible = ref(false)
const assignVisible = ref(false)
const currentRequest = ref(null)

const filters = reactive({
  status: '',
  urgency: '',
  search: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const assignForm = reactive({ volunteer_id: null })

const loadData = async () => {
  loading.value = true
  try {
    const params = { ...buildPageParams(pagination) }
    if (filters.status) params.status = filters.status
    if (filters.urgency) params.urgency = filters.urgency
    if (filters.search) params.search = filters.search

    const data = await request.get('/help-requests/', { params })
    const page = unwrapPaginated(data)
    helpRequests.value = page.list
    pagination.total = page.total
  } finally {
    loading.value = false
  }
}

const loadVolunteers = async () => {
  const data = await request.get('/users/', { params: { role: 'volunteer', page_size: 200 } })
  volunteers.value = unwrapPaginated(data).list
}

const loadRecommendations = async () => {
  if (!currentRequest.value) return
  recommendLoading.value = true
  try {
    recommendations.value = await request.get(`/help-requests/${currentRequest.value.id}/recommend-volunteers/`)
    if (recommendations.value[0]?.is_available) {
      assignForm.volunteer_id = recommendations.value[0].id
    }
  } finally {
    recommendLoading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadData()
}

const resetFilters = () => {
  filters.status = ''
  filters.urgency = ''
  filters.search = ''
  handleSearch()
}

const handleSizeChange = size => {
  pagination.pageSize = size
  pagination.page = 1
  loadData()
}

const handlePageChange = page => {
  pagination.page = page
  loadData()
}

const openDetail = row => {
  currentRequest.value = row
  detailVisible.value = true
}

const openAssignDialog = async row => {
  currentRequest.value = row
  assignForm.volunteer_id = null
  recommendations.value = []
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
    await loadData()
  } finally {
    assignLoading.value = false
  }
}

const cancelRequest = async row => {
  try {
    await ElMessageBox.confirm('确定要取消该求助吗？', '提示', {
      type: 'warning',
      confirmButtonText: '确定取消',
      cancelButtonText: '再想想'
    })
    await request.post(`/help-requests/${row.id}/cancel/`)
    ElMessage.success('求助已取消')
    await loadData()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}

const formatTime = value => {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

const statusColor = status => {
  const map = {
    pending: '#E6A23C',
    assigned: '#409EFF',
    processing: '#9333EA',
    completed: '#67C23A',
    cancelled: '#909399'
  }
  return map[status] || '#909399'
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

onMounted(() => loadData())
</script>

<style scoped>
.summary-text {
  color: #b45309;
  font-weight: 700;
}

.detail-map-title {
  margin: 18px 0 10px;
  font-weight: 700;
  color: #1e293b;
}

.recommend-bar {
  margin-bottom: 14px;
  padding: 12px;
  border-radius: 12px;
  background: #f0fdf4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.recommend-title {
  font-weight: 700;
  color: #166534;
}

.recommend-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #4b5563;
}

.recommend-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.recommend-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px;
  cursor: pointer;
  display: flex;
  gap: 10px;
  min-height: 118px;
}

.recommend-card.selected {
  border-color: #16a34a;
  background: #f0fdf4;
}

.recommend-score {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #16a34a;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
}

.recommend-name {
  font-weight: 700;
}

.recommend-name span,
.recommend-reason {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
  line-height: 1.5;
}

@media (max-width: 1000px) {
  .recommend-list {
    grid-template-columns: 1fr;
  }
}
</style>
