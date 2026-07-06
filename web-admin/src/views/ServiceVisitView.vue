<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">排班工单看板</div>
        <div class="page-subtitle">查看周期服务派单情况，可按状态、日期、服务类型筛选，并对未完成工单进行改派。</div>
      </div>
      <el-button type="success" :loading="generating" @click="generateVisits">生成本周排班</el-button>
    </div>

    <div class="card filter-card">
      <el-form :inline="true">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 140px" @change="handleFilter">
            <el-option v-for="s in STATUS" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务类型">
          <el-select v-model="filters.serviceType" placeholder="全部服务" clearable filterable style="width: 180px" @change="handleFilter">
            <el-option v-for="t in types" :key="t.id" :label="`${t.icon || '🛎️'} ${t.name}`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="filters.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" clearable @change="handleFilter" />
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 本页各状态数量小结 -->
    <div class="stat-bar" v-if="items.length">
      <div
        v-for="s in STATUS"
        :key="s.value"
        class="stat-chip"
        :style="{ '--chip-color': STATUS_COLOR[s.value] }"
      >
        <span class="stat-dot"></span>
        <span class="stat-label">{{ s.label }}</span>
        <span class="stat-num">{{ statusCount[s.value] || 0 }}</span>
      </div>
      <div class="stat-chip stat-total">
        <span class="stat-label">本页合计</span>
        <span class="stat-num">{{ items.length }}</span>
      </div>
    </div>

    <div class="card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="scheduled_date" label="计划日期" width="120" />
        <el-table-column prop="resident_name" label="受益居民" min-width="100" />
        <el-table-column label="服务" min-width="170">
          <template #default="{ row }">
            <div class="svc-cell">
              <span class="svc-icon">{{ row.service_type_icon || '🛎️' }}</span>
              <span class="svc-name">{{ row.service_type_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="志愿者" min-width="110">
          <template #default="{ row }">
            <span v-if="row.volunteer_name">{{ row.volunteer_name }}</span>
            <el-tag v-else type="danger" effect="dark" size="small">待派单</el-tag>
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
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :disabled="!['assigned','processing'].includes(row.status)" @click="openReassign(row)">改派</el-button>
            <el-button size="small" type="primary" plain @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-state">
            <div class="empty-emoji">📋</div>
            <div class="empty-title">暂无排班工单</div>
            <div class="empty-tip">调整上方筛选条件，或点击「生成本周排班」派发到期的服务计划</div>
          </div>
        </template>
      </el-table>

      <el-pagination
        v-if="pagination.total > 0"
        class="pagination"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="pagination.total"
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

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
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(current.status)" effect="dark" size="small">{{ current.status_display }}</el-tag>
        </el-descriptions-item>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import { buildPageParams, unwrapPaginated } from '../utils/pagination'

const STATUS = [
  { value: 'assigned', label: '已排班' },
  { value: 'processing', label: '服务中' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
  { value: 'missed', label: '已错过' }
]

// 统一状态色
const STATUS_COLOR = {
  assigned: '#F59E0B', processing: '#2563EB', completed: '#16A34A', cancelled: '#94A3B8', missed: '#EF4444'
}

const statusType = s => ({
  assigned: 'warning', processing: 'primary', completed: 'success', cancelled: 'info', missed: 'danger'
}[s] || 'info')

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/api\/?$/, '')
const photoUrl = p => (p && p.startsWith('http')) ? p : `${API_ORIGIN}${p}`

const loading = ref(false)
const saving = ref(false)
const generating = ref(false)
const items = ref([])
const volunteers = ref([])
const types = ref([])
const current = ref(null)
const reassignVisible = ref(false)
const detailVisible = ref(false)
const reassignVolunteer = ref(null)

const filters = reactive({ status: '', serviceType: '', date: '' })

// 分页（兼容后端返回数组或 {count,results}）
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

// 本页各状态数量小结
const statusCount = computed(() => {
  const map = {}
  for (const row of items.value) {
    map[row.status] = (map[row.status] || 0) + 1
  }
  return map
})

const loadData = async () => {
  loading.value = true
  try {
    const params = { ...buildPageParams(pagination) }
    if (filters.status) params.status = filters.status
    if (filters.serviceType) params.service_type = filters.serviceType
    if (filters.date) params.scheduled_date = filters.date
    const data = await request.get('/service-visits/', { params })
    const page = unwrapPaginated(data)
    items.value = page.list
    pagination.total = page.total
  } catch (e) { /* 拦截器提示 */ } finally { loading.value = false }
}

const handleSizeChange = size => { pagination.pageSize = size; pagination.page = 1; loadData() }
const handlePageChange = page => { pagination.page = page; loadData() }
const handleFilter = () => { pagination.page = 1; loadData() }

const loadRefs = async () => {
  try {
    const [v, t] = await Promise.all([
      request.get('/users/', { params: { role: 'volunteer', page_size: 200 } }),
      request.get('/service-types/', { params: { is_active: true, page_size: 200 } })
    ])
    volunteers.value = unwrapPaginated(v).list
    types.value = unwrapPaginated(t).list
  } catch (e) { /* 拦截器提示 */ }
}

const resetFilters = () => {
  filters.status = ''; filters.serviceType = ''; filters.date = ''
  pagination.page = 1
  loadData()
}

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

onMounted(() => { loadData(); loadRefs() })
</script>

<style scoped>
/* 服务单元格：大 emoji + 名称 */
.svc-cell { display: flex; align-items: center; gap: 10px; }
.svc-icon {
  font-size: 22px; line-height: 1;
  width: 38px; height: 38px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: #eff6ff; border-radius: 10px;
}
.svc-name { font-size: 15px; font-weight: 600; color: #1e293b; }
.muted { color: #94a3b8; }

/* 本页状态小结 */
.stat-bar { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
.stat-chip {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px; background: #ffffff; border-radius: 12px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, .06);
  border: 1px solid rgba(226, 232, 240, .7);
}
.stat-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--chip-color, #94a3b8);
}
.stat-label { font-size: 14px; color: #475569; }
.stat-num { font-size: 16px; font-weight: 700; color: #1e293b; }
.stat-total { background: #f8fafc; }

/* 空状态 */
.empty-state { padding: 28px 0; }
.empty-emoji { font-size: 46px; }
.empty-title { margin-top: 10px; font-size: 16px; font-weight: 600; color: #475569; }
.empty-tip { margin-top: 6px; font-size: 13px; color: #94a3b8; }
</style>
