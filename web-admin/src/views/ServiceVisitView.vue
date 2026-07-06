<template>
  <div class="page">
    <div class="page-header">
      <h2 style="margin: 0">排班工单看板</h2>
      <el-button type="success" :loading="generating" @click="generateVisits">生成本周排班</el-button>
    </div>

    <el-card shadow="never" style="margin-bottom: 16px">
      <el-form :inline="true">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 140px" @change="loadData">
            <el-option v-for="s in STATUS" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="filters.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" clearable @change="loadData" />
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="scheduled_date" label="计划日期" width="120" />
        <el-table-column prop="resident_name" label="受益居民" min-width="100" />
        <el-table-column label="服务" min-width="140">
          <template #default="{ row }">
            <span style="margin-right:6px">{{ row.service_type_icon }}</span>{{ row.service_type_name }}
          </template>
        </el-table-column>
        <el-table-column label="志愿者" min-width="110">
          <template #default="{ row }">
            <span v-if="row.volunteer_name">{{ row.volunteer_name }}</span>
            <el-tag v-else type="danger" size="small">待派单</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="dark">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="健康记录" min-width="150">
          <template #default="{ row }">
            <span v-if="row.systolic || row.temperature">
              血压 {{ row.systolic || '—' }}/{{ row.diastolic || '—' }} · 体温 {{ row.temperature || '—' }}℃
            </span>
            <span v-else style="color:#94a3b8">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :disabled="!['assigned','processing'].includes(row.status)" @click="openReassign(row)">改派</el-button>
            <el-button size="small" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="reassignVisible" title="改派志愿者" width="420px">
      <el-form label-width="80px">
        <el-form-item label="工单">
          <span>{{ current?.resident_name }} · {{ current?.service_type_name }}</span>
        </el-form-item>
        <el-form-item label="志愿者" required>
          <el-select v-model="reassignVolunteer" filterable placeholder="选择志愿者" style="width: 100%">
            <el-option v-for="v in volunteers" :key="v.id" :label="`${v.username}（${v.skills || '无技能标签'}）`" :value="v.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reassignVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitReassign">确认改派</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="工单详情" width="460px">
      <el-descriptions v-if="current" :column="1" border>
        <el-descriptions-item label="受益居民">{{ current.resident_name }}</el-descriptions-item>
        <el-descriptions-item label="服务类型">{{ current.service_type_icon }} {{ current.service_type_name }}</el-descriptions-item>
        <el-descriptions-item label="志愿者">{{ current.volunteer_name || '待派单' }}</el-descriptions-item>
        <el-descriptions-item label="计划日期">{{ current.scheduled_date }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ current.status_display }}</el-descriptions-item>
        <el-descriptions-item label="服务地址">{{ current.address || '—' }}</el-descriptions-item>
        <el-descriptions-item v-if="current.needs_health_record" label="血压">{{ current.systolic || '—' }}/{{ current.diastolic || '—' }} mmHg</el-descriptions-item>
        <el-descriptions-item v-if="current.needs_health_record" label="心率">{{ current.heart_rate || '—' }} 次/分</el-descriptions-item>
        <el-descriptions-item v-if="current.needs_health_record" label="体温">{{ current.temperature || '—' }} ℃</el-descriptions-item>
        <el-descriptions-item v-if="current.health_note" label="健康备注">{{ current.health_note }}</el-descriptions-item>
        <el-descriptions-item label="服务反馈">{{ current.feedback || '—' }}</el-descriptions-item>
        <el-descriptions-item v-if="current.completion_photo" label="完成凭证">
          <el-image style="width:120px" :src="photoUrl(current.completion_photo)" :preview-src-list="[photoUrl(current.completion_photo)]" fit="cover" />
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const STATUS = [
  { value: 'assigned', label: '已排班' },
  { value: 'processing', label: '服务中' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
  { value: 'missed', label: '已错过' }
]

const statusType = s => ({
  assigned: 'warning', processing: 'primary', completed: 'success', cancelled: 'danger', missed: 'info'
}[s] || 'info')

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/api\/?$/, '')
const photoUrl = p => (p && p.startsWith('http')) ? p : `${API_ORIGIN}${p}`

const loading = ref(false)
const saving = ref(false)
const generating = ref(false)
const items = ref([])
const volunteers = ref([])
const current = ref(null)
const reassignVisible = ref(false)
const detailVisible = ref(false)
const reassignVolunteer = ref(null)

const filters = reactive({ status: '', date: '' })

const loadData = async () => {
  loading.value = true
  try {
    const params = { page_size: 200 }
    if (filters.status) params.status = filters.status
    if (filters.date) params.scheduled_date = filters.date
    const data = await request.get('/service-visits/', { params })
    items.value = Array.isArray(data) ? data : (data.results || [])
  } catch (e) { /* 拦截器提示 */ } finally { loading.value = false }
}

const loadVolunteers = async () => {
  try {
    const v = await request.get('/users/', { params: { role: 'volunteer', page_size: 200 } })
    volunteers.value = Array.isArray(v) ? v : (v.results || [])
  } catch (e) { /* 拦截器提示 */ }
}

const resetFilters = () => { filters.status = ''; filters.date = ''; loadData() }

const openReassign = row => {
  current.value = row
  reassignVolunteer.value = row.volunteer || null
  reassignVisible.value = true
}

const submitReassign = async () => {
  if (!reassignVolunteer.value) { ElMessage.warning('请选择志愿者'); return }
  saving.value = true
  try {
    await request.post(`/service-visits/${current.value.id}/reassign/`, { volunteer_id: reassignVolunteer.value })
    ElMessage.success('已改派')
    reassignVisible.value = false
    loadData()
  } catch (e) { /* 拦截器提示 */ } finally { saving.value = false }
}

const openDetail = row => { current.value = row; detailVisible.value = true }

const generateVisits = async () => {
  generating.value = true
  try {
    const res = await request.post('/service-subscriptions/generate-visits/')
    ElMessage.success(res.message || '已生成排班')
    loadData()
  } catch (e) { /* 拦截器提示 */ } finally { generating.value = false }
}

onMounted(() => { loadData(); loadVolunteers() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
