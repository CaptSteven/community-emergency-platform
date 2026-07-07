<template>
  <div class="page-container dashboard-page">
    <div class="page-header">
      <div>
        <div class="page-title">社区服务数据大屏</div>
        <div class="page-subtitle">社区周期服务运行概览</div>
      </div>

      <div class="dashboard-actions">
        <div class="refresh-info">
          最后更新：{{ lastUpdated || '暂无' }} ｜ 自动刷新：{{ AUTO_REFRESH_INTERVAL / 1000 }} 秒/次
        </div>
        <el-switch v-model="autoRefresh" active-text="自动刷新" />
        <el-button type="primary" :loading="loading" @click="loadData()">立即刷新</el-button>
      </div>
    </div>

    <el-alert
      v-if="serviceOverview.unassigned_visits > 0"
      class="dashboard-alert"
      type="warning"
      show-icon
      :closable="false"
      :title="`当前有 ${serviceOverview.unassigned_visits} 个上门工单尚未派单，请尽快安排志愿者。`"
    />

    <div class="section-title">周期服务运行指标</div>
    <el-row :gutter="18">
      <el-col :span="6" v-for="c in serviceCards" :key="c.label">
        <div class="stat-card">
          <div class="stat-ico" :class="[c.tint, { danger: c.danger }]">
            <el-icon><component :is="c.icon" /></el-icon>
          </div>
          <div class="stat-value">{{ c.value }}</div>
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-desc">{{ c.desc }}</div>
        </div>
      </el-col>
    </el-row>

    <div class="section-title">工单累计与进度</div>
    <el-row :gutter="18">
      <el-col :span="6" v-for="c in progressCards" :key="c.label">
        <div class="stat-card">
          <div class="stat-ico" :class="[c.tint, { danger: c.danger }]">
            <el-icon><component :is="c.icon" /></el-icon>
          </div>
          <div class="stat-value">{{ c.value }}</div>
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-desc">{{ c.desc }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表 -->
    <el-row :gutter="18" class="chart-row">
      <el-col :span="12">
        <div class="card">
          <div class="card-title">各服务类型工单量</div>
          <div class="card-subtitle">按服务类型统计工单总量与已完成量。</div>
          <div v-show="serviceTypeStats.length" ref="typeChartRef" class="chart-box"></div>
          <el-empty
            v-show="!serviceTypeStats.length"
            class="chart-empty"
            description="暂无服务类型数据，先到「服务目录管理」添加服务"
            :image-size="90"
          />
        </div>
      </el-col>

      <el-col :span="12">
        <div class="card">
          <div class="card-title">志愿者服务负载排行</div>
          <div class="card-subtitle">按志愿者统计承接工单总量与完成量（Top 10）。</div>
          <div v-show="volunteerLoad.length" ref="loadChartRef" class="chart-box"></div>
          <el-empty
            v-show="!volunteerLoad.length"
            class="chart-empty"
            description="暂无志愿者服务记录"
            :image-size="90"
          />
        </div>
      </el-col>
    </el-row>

    <!-- 未来 7 天即将上门 -->
    <el-row :gutter="18" class="chart-row">
      <el-col :span="24">
        <div class="card">
          <div class="card-title">未来 7 天即将上门</div>
          <div class="card-subtitle">
            {{ upcoming.range_start || '' }} ~ {{ upcoming.range_end || '' }}，共 {{ upcoming.count || 0 }} 个待上门工单。
          </div>

          <el-table v-if="upcomingVisits.length" :data="upcomingVisits" stripe style="width: 100%">
            <el-table-column label="日期" prop="scheduled_date" width="130" />
            <el-table-column label="服务类型" min-width="150">
              <template #default="{ row }">
                <span class="svc-emoji">{{ row.icon || '🛎️' }}</span>{{ row.service_type }}
              </template>
            </el-table-column>
            <el-table-column label="居民" prop="resident" min-width="110" />
            <el-table-column label="志愿者" min-width="110">
              <template #default="{ row }">{{ row.volunteer || '待派单' }}</template>
            </el-table-column>
            <el-table-column label="地址" prop="address" min-width="200" show-overflow-tooltip />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" effect="light">{{ row.status_display }}</el-tag>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else description="未来 7 天暂无待上门工单，服务安排一切从容" :image-size="80" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Tickets, List, Van, Warning, Files, CircleCheck, Clock, Select } from '@element-plus/icons-vue'
import request from '../api/request'

const AUTO_REFRESH_INTERVAL = 10000

const loading = ref(false)
const autoRefresh = ref(true)
const lastUpdated = ref('')

const serviceOverview = ref({})
const serviceTypeStats = ref([])
const volunteerLoad = ref([])
const upcoming = ref({})

const typeChartRef = ref(null)
const loadChartRef = ref(null)

let typeChart = null
let loadChart = null
let refreshTimer = null

const safeArray = data => (Array.isArray(data) ? data : [])

const completionRate = computed(() => {
  const total = serviceOverview.value.visits_total || 0
  const done = serviceOverview.value.visits_completed || 0
  if (!total) return 0
  return Math.round((done / total) * 100)
})

const upcomingVisits = computed(() => safeArray(upcoming.value.visits))

// KPI 卡：统一白卡 + 蓝色图标色块，仅“待人工派单”异常用红色强调
const serviceCards = computed(() => {
  const o = serviceOverview.value
  return [
    { icon: Tickets, label: '生效服务计划', value: o.active_subscriptions || 0, desc: `覆盖 ${o.covered_residents || 0} 位居民` },
    { icon: List, label: '服务目录种类', value: o.service_types || 0, desc: '可预约的服务类型' },
    { icon: Van, label: '本周上门工单', value: o.visits_this_week || 0, desc: `已完成 ${o.completed_this_week || 0} 单` },
    { icon: Warning, label: '待人工派单', value: o.unassigned_visits || 0, desc: '暂无匹配志愿者', danger: (o.unassigned_visits || 0) > 0 },
  ]
})

const progressCards = computed(() => {
  const o = serviceOverview.value
  return [
    { icon: Files, label: '累计工单', value: o.visits_total || 0, desc: '平台生成的全部上门工单' },
    { icon: CircleCheck, label: '已完成工单', value: o.visits_completed || 0, desc: `完成率 ${completionRate.value}%`, tint: 'service' },
    { icon: Clock, label: '进行中工单', value: o.pending_visits || 0, desc: '已排班 / 服务中 / 待确认' },
    { icon: Select, label: '本周完成', value: o.completed_this_week || 0, desc: '近 7 日已完成上门', tint: 'service' },
  ]
})

const statusTagType = status => {
  const map = { completed: 'success', processing: 'warning', pending_confirm: 'warning', assigned: 'primary', pending: 'info', unassigned: 'danger', cancelled: 'info' }
  return map[status] || 'info'
}

const getChart = (chart, chartRef) => {
  if (!chartRef.value) return null
  if (!chart) chart = echarts.init(chartRef.value)
  return chart
}

const formatDateTime = date => {
  const pad = value => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const loadData = async (options = {}) => {
  const silent = options.silent === true
  if (!silent) loading.value = true
  try {
    const [overviewData, typeData, loadData_, upcomingData] = await Promise.all([
      request.get('/analytics/service-overview/'),
      request.get('/analytics/service-type-stats/'),
      request.get('/analytics/volunteer-service-load/'),
      request.get('/analytics/service-upcoming/')
    ])
    serviceOverview.value = overviewData || {}
    serviceTypeStats.value = safeArray(typeData)
    volunteerLoad.value = safeArray(loadData_)
    upcoming.value = upcomingData || {}
    lastUpdated.value = formatDateTime(new Date())
    await nextTick()
    renderTypeChart(serviceTypeStats.value)
    renderLoadChart(volunteerLoad.value)
  } finally {
    if (!silent) loading.value = false
  }
}

const FAINT = { lineStyle: { color: '#f1f5f9' } }
const BAR_LABEL = { show: true, color: '#64748b', fontSize: 11 }

const renderTypeChart = data => {
  typeChart = getChart(typeChart, typeChartRef)
  if (!typeChart) return
  const names = data.map(item => `${item.icon || ''} ${item.name}`.trim())
  typeChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { top: 44, left: 44, right: 40, bottom: 56 },
    xAxis: { type: 'category', data: names, axisLabel: { interval: 0, rotate: names.length > 4 ? 25 : 0 }, axisTick: { show: false } },
    yAxis: { type: 'value', minInterval: 1, splitLine: FAINT, max: v => Math.max(4, Math.ceil(v.max)) },
    series: [
      { name: '工单总量', type: 'bar', barMaxWidth: 40, barGap: '20%', barCategoryGap: '45%', label: { ...BAR_LABEL, position: 'top' }, itemStyle: { color: '#2563EB', borderRadius: [5, 5, 0, 0] }, data: data.map(i => i.total) },
      { name: '已完成', type: 'bar', barMaxWidth: 40, label: { ...BAR_LABEL, position: 'top' }, itemStyle: { color: '#16A34A', borderRadius: [5, 5, 0, 0] }, data: data.map(i => i.completed) }
    ]
  }, true)
}

const renderLoadChart = data => {
  loadChart = getChart(loadChart, loadChartRef)
  if (!loadChart) return
  const sorted = [...data].sort((a, b) => (b.total || 0) - (a.total || 0)).slice(0, 10).reverse()
  loadChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { top: 44, left: 80, right: 50, bottom: 20 },
    xAxis: { type: 'value', minInterval: 1, splitLine: FAINT, max: v => Math.max(4, Math.ceil(v.max)) },
    yAxis: { type: 'category', data: sorted.map(i => i.volunteer), axisTick: { show: false } },
    series: [
      { name: '承接工单', type: 'bar', barMaxWidth: 20, barGap: '20%', barCategoryGap: '45%', label: { ...BAR_LABEL, position: 'right' }, itemStyle: { color: '#2563EB', borderRadius: [0, 5, 5, 0] }, data: sorted.map(i => i.total) },
      { name: '已完成', type: 'bar', barMaxWidth: 20, label: { ...BAR_LABEL, position: 'right' }, itemStyle: { color: '#16A34A', borderRadius: [0, 5, 5, 0] }, data: sorted.map(i => i.completed) }
    ]
  }, true)
}

const resizeCharts = () => { typeChart?.resize(); loadChart?.resize() }
const disposeCharts = () => { typeChart?.dispose(); loadChart?.dispose(); typeChart = null; loadChart = null }

const startAutoRefresh = () => {
  stopAutoRefresh()
  refreshTimer = window.setInterval(() => {
    if (autoRefresh.value && document.visibilityState === 'visible' && !loading.value) {
      loadData({ silent: true })
    }
  }, AUTO_REFRESH_INTERVAL)
}
const stopAutoRefresh = () => { if (refreshTimer) { window.clearInterval(refreshTimer); refreshTimer = null } }
const handleVisibilityChange = () => { if (document.visibilityState === 'visible' && autoRefresh.value) loadData({ silent: true }) }

onMounted(() => {
  loadData()
  startAutoRefresh()
  window.addEventListener('resize', resizeCharts)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  stopAutoRefresh()
  window.removeEventListener('resize', resizeCharts)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  disposeCharts()
})
</script>

<style scoped>
.dashboard-page {
  padding-bottom: 30px;
}

.dashboard-alert {
  margin-bottom: 18px;
  border-radius: 12px;
}

.dashboard-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.refresh-info {
  color: #64748b;
  font-size: 13px;
  white-space: nowrap;
}

.section-title {
  margin: 26px 2px 16px;
  font-size: 16px;
  font-weight: 700;
  color: #1f2937;
  border-left: 4px solid var(--brand);
  padding-left: 12px;
  line-height: 1.4;
}

/* KPI 卡：统一白卡 + 中性阴影 + 图标色块 */
.stat-card {
  background: #fff;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  box-shadow: var(--card-shadow);
  padding: 20px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--card-shadow-hover);
}

.stat-ico {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--icon-tint);
  color: var(--brand);
  font-size: 22px;
  margin-bottom: 14px;
}

.stat-ico.danger {
  background: var(--icon-tint-danger);
  color: var(--danger);
}

.stat-ico.service {
  background: rgba(22, 163, 74, 0.12);
  color: var(--service);
}

.stat-value {
  font-size: 34px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.1;
}

.stat-label {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-desc {
  margin-top: 5px;
  font-size: 13px;
  color: var(--text-secondary);
}

.chart-row {
  margin-top: 22px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 6px;
}

.card-subtitle {
  margin-bottom: 12px;
  color: #64748b;
  font-size: 13px;
}

.chart-box {
  width: 100%;
  height: 320px;
}

.chart-empty {
  height: 320px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.svc-emoji {
  margin-right: 4px;
}
</style>
