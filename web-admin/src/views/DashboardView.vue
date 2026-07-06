<template>
  <div class="page-container dashboard-page">
    <div class="page-header">
      <div>
        <div class="page-title">社区服务数据大屏</div>
        <div class="page-subtitle">
          社区周期服务运行概览
        </div>
      </div>

      <div class="dashboard-actions">
        <div class="refresh-info">
          最后更新：{{ lastUpdated || '暂无' }} ｜ 自动刷新：{{ AUTO_REFRESH_INTERVAL / 1000 }} 秒/次
        </div>
        <el-switch
          v-model="autoRefresh"
          active-text="自动刷新"
          inactive-text="暂停刷新"
        />
        <el-button type="primary" :loading="loading" @click="loadData()">
          立即刷新
        </el-button>
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

    <!-- 服务 KPI 卡片 -->
    <div class="section-title section-title--service">
      <span class="section-badge">社区服务</span>周期服务运行指标
      <span class="section-sub">日常上门服务与居家关怀的整体运行情况</span>
    </div>
    <el-row :gutter="18" class="service-kpi-row">
      <el-col :span="6">
        <div class="stat-card service-card">
          <div class="stat-icon">🤝</div>
          <div class="stat-label">生效服务计划</div>
          <div class="stat-value">{{ serviceOverview.active_subscriptions || 0 }}</div>
          <div class="stat-desc">覆盖 {{ serviceOverview.covered_residents || 0 }} 位居民</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card service-card cyan">
          <div class="stat-icon">📋</div>
          <div class="stat-label">服务目录种类</div>
          <div class="stat-value">{{ serviceOverview.service_types || 0 }}</div>
          <div class="stat-desc">可预约的服务类型</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card service-card success">
          <div class="stat-icon">🚪</div>
          <div class="stat-label">本周上门工单</div>
          <div class="stat-value">{{ serviceOverview.visits_this_week || 0 }}</div>
          <div class="stat-desc">已完成 {{ serviceOverview.completed_this_week || 0 }} 单</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card service-card danger">
          <div class="stat-icon">📮</div>
          <div class="stat-label">待人工派单</div>
          <div class="stat-value">{{ serviceOverview.unassigned_visits || 0 }}</div>
          <div class="stat-desc">暂无匹配志愿者</div>
        </div>
      </el-col>
    </el-row>

    <div class="section-title">工单累计与进度</div>
    <el-row :gutter="18" class="summary-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-label">累计工单</div>
          <div class="stat-value">{{ serviceOverview.visits_total || 0 }}</div>
          <div class="stat-desc">平台生成的全部上门工单</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card purple">
          <div class="stat-icon">✅</div>
          <div class="stat-label">已完成工单</div>
          <div class="stat-value">{{ serviceOverview.visits_completed || 0 }}</div>
          <div class="stat-desc">完成率 {{ completionRate }}%</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card warning">
          <div class="stat-icon">🔧</div>
          <div class="stat-label">进行中工单</div>
          <div class="stat-value">{{ serviceOverview.pending_visits || 0 }}</div>
          <div class="stat-desc">已排班 / 服务中</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card green">
          <div class="stat-icon">🗓️</div>
          <div class="stat-label">本周完成</div>
          <div class="stat-value">{{ serviceOverview.completed_this_week || 0 }}</div>
          <div class="stat-desc">近 7 日已完成上门</div>
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
          <div v-show="!serviceTypeStats.length" class="empty-box">
            🗂️
            <div class="empty-text">暂无服务类型数据，先到「服务目录管理」添加服务吧</div>
          </div>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="card">
          <div class="card-title">志愿者服务负载排行</div>
          <div class="card-subtitle">按志愿者统计承接工单总量与完成量（Top 10）。</div>
          <div v-show="volunteerLoad.length" ref="loadChartRef" class="chart-box"></div>
          <div v-show="!volunteerLoad.length" class="empty-box">
            🙋
            <div class="empty-text">暂无志愿者服务记录</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 未来 7 天即将上门 -->
    <el-row :gutter="18" class="chart-row">
      <el-col :span="24">
        <div class="card">
          <div class="card-header-row">
            <div>
              <div class="card-title">未来 7 天即将上门</div>
              <div class="card-subtitle">
                {{ upcoming.range_start || '' }} ~ {{ upcoming.range_end || '' }}，共 {{ upcoming.count || 0 }} 个待上门工单。
              </div>
            </div>
          </div>

          <el-table
            v-if="upcomingVisits.length"
            :data="upcomingVisits"
            stripe
            style="width: 100%"
          >
            <el-table-column label="日期" prop="scheduled_date" width="130" />
            <el-table-column label="服务类型" min-width="150">
              <template #default="{ row }">
                <span class="svc-emoji">{{ row.icon || '🛎️' }}</span>
                {{ row.service_type }}
              </template>
            </el-table-column>
            <el-table-column label="居民" prop="resident" min-width="110" />
            <el-table-column label="志愿者" min-width="110">
              <template #default="{ row }">
                {{ row.volunteer || '待派单' }}
              </template>
            </el-table-column>
            <el-table-column label="地址" prop="address" min-width="200" show-overflow-tooltip />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" effect="light">
                  {{ row.status_display }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <div v-else class="empty-box empty-box--wide">
            🎉
            <div class="empty-text">未来 7 天暂无待上门工单，服务安排一切从容</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
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

// 工单完成率
const completionRate = computed(() => {
  const total = serviceOverview.value.visits_total || 0
  const done = serviceOverview.value.visits_completed || 0
  if (!total) return 0
  return Math.round((done / total) * 100)
})

const upcomingVisits = computed(() => safeArray(upcoming.value.visits))

// 状态标签配色，统一状态色
const statusTagType = status => {
  const map = {
    completed: 'success',
    processing: 'warning',
    assigned: 'primary',
    pending: 'info',
    unassigned: 'danger',
    cancelled: 'info'
  }
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

// 各服务类型工单量（总量 vs 完成量）
const renderTypeChart = data => {
  typeChart = getChart(typeChart, typeChartRef)
  if (!typeChart) return

  const names = data.map(item => `${item.icon || ''} ${item.name}`.trim())

  typeChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { top: 40, left: 50, right: 25, bottom: 55 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { interval: 0, rotate: names.length > 4 ? 25 : 0 }
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: '工单总量',
        type: 'bar',
        barMaxWidth: 34,
        itemStyle: { color: '#2563EB', borderRadius: [6, 6, 0, 0] },
        data: data.map(item => item.total)
      },
      {
        name: '已完成',
        type: 'bar',
        barMaxWidth: 34,
        itemStyle: { color: '#16A34A', borderRadius: [6, 6, 0, 0] },
        data: data.map(item => item.completed)
      }
    ]
  }, true)
}

// 志愿者服务负载排行（Top 10 条形图）
const renderLoadChart = data => {
  loadChart = getChart(loadChart, loadChartRef)
  if (!loadChart) return

  // 按总量降序取前 10，条形图从上到下需反转
  const sorted = [...data].sort((a, b) => (b.total || 0) - (a.total || 0)).slice(0, 10).reverse()

  loadChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { top: 40, left: 80, right: 25, bottom: 25 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: {
      type: 'category',
      data: sorted.map(item => item.volunteer)
    },
    series: [
      {
        name: '承接工单',
        type: 'bar',
        barMaxWidth: 20,
        itemStyle: { color: '#2563EB', borderRadius: [0, 6, 6, 0] },
        data: sorted.map(item => item.total)
      },
      {
        name: '已完成',
        type: 'bar',
        barMaxWidth: 20,
        itemStyle: { color: '#16A34A', borderRadius: [0, 6, 6, 0] },
        data: sorted.map(item => item.completed)
      }
    ]
  }, true)
}

const resizeCharts = () => {
  typeChart?.resize()
  loadChart?.resize()
}

const disposeCharts = () => {
  typeChart?.dispose()
  loadChart?.dispose()
  typeChart = null
  loadChart = null
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  refreshTimer = window.setInterval(() => {
    if (autoRefresh.value && document.visibilityState === 'visible' && !loading.value) {
      loadData({ silent: true })
    }
  }, AUTO_REFRESH_INTERVAL)
}

const stopAutoRefresh = () => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible' && autoRefresh.value) {
    loadData({ silent: true })
  }
}

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

.summary-row {
  margin-top: 18px;
}

.section-title {
  margin: 24px 2px 14px;
  font-size: 17px;
  font-weight: 700;
  color: #1f2937;
  border-left: 4px solid #2563eb;
  padding-left: 12px;
  line-height: 1.4;
}

/* 社区服务分区：绿色强调 + 徽标 + 副标题 */
.section-title--service {
  border-left-color: #16a34a;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
  font-size: 18px;
}

.section-badge {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #16a34a, #15803d);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 12px rgba(22, 163, 74, 0.28);
}

.section-sub {
  font-size: 13px;
  font-weight: 400;
  color: #64748b;
}

.service-kpi-row {
  margin-bottom: 4px;
  padding: 6px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(22, 163, 74, 0.06), rgba(37, 99, 235, 0.04));
}

.stat-card {
  position: relative;
  overflow: hidden;
  min-height: 140px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: white;
  border-radius: 16px;
  padding: 22px;
  box-shadow: 0 8px 22px rgba(37, 99, 235, 0.24);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.3);
}

.stat-card::after {
  content: "";
  position: absolute;
  top: -40px;
  right: -30px;
  width: 130px;
  height: 130px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
}

.stat-icon {
  position: absolute;
  top: 16px;
  right: 18px;
  font-size: 30px;
  line-height: 1;
  opacity: 0.9;
  z-index: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.12));
}

.stat-card.warning {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  box-shadow: 0 8px 22px rgba(245, 158, 11, 0.26);
}

.stat-card.success {
  background: linear-gradient(135deg, #16a34a, #059669);
  box-shadow: 0 8px 22px rgba(22, 163, 74, 0.26);
}

.stat-card.danger {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  box-shadow: 0 8px 22px rgba(239, 68, 68, 0.26);
}

.stat-card.purple {
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
  box-shadow: 0 8px 22px rgba(139, 92, 246, 0.26);
}

.stat-card.cyan {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  box-shadow: 0 8px 22px rgba(6, 182, 212, 0.26);
}

.stat-card.green {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  box-shadow: 0 8px 22px rgba(34, 197, 94, 0.26);
}

.service-card {
  min-height: 150px;
  border: 1px solid rgba(255, 255, 255, 0.35);
}

.stat-label {
  position: relative;
  z-index: 1;
  font-size: 15px;
  opacity: 0.95;
}

.stat-value {
  position: relative;
  z-index: 1;
  margin-top: 12px;
  font-size: 36px;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.stat-desc {
  position: relative;
  z-index: 1;
  margin-top: 8px;
  font-size: 13px;
  opacity: 0.88;
}

.chart-row {
  margin-top: 18px;
}

.card-title {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 6px;
}

.card-subtitle {
  margin-bottom: 12px;
  color: #64748b;
  font-size: 13px;
}

.card-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.chart-box {
  width: 100%;
  height: 360px;
}

.svc-emoji {
  margin-right: 4px;
}

/* 空状态：emoji + 引导文案 */
.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 360px;
  font-size: 46px;
  color: #94a3b8;
}

.empty-box--wide {
  height: 220px;
}

.empty-text {
  margin-top: 12px;
  font-size: 14px;
  color: #64748b;
}
</style>
