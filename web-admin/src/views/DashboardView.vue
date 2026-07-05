<template>
  <div class="page-container dashboard-page">
    <div class="page-header">
      <div>
        <div class="page-title">数据可视化大屏</div>
        <div class="page-subtitle">
          汇总社区求助、志愿者任务、灾害预警和应急资源数据，辅助管理员快速研判。
        </div>
      </div>

      <el-button type="primary" :loading="loading" @click="loadData">
        刷新数据
      </el-button>
    </div>

    <el-alert
      v-if="overview.critical_pending_request_count > 0"
      class="dashboard-alert"
      type="warning"
      show-icon
      :closable="false"
      :title="`当前有 ${overview.critical_pending_request_count} 条高优先级待处理求助，请尽快分配志愿者。`"
    />

    <el-row :gutter="18">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">总求助数</div>
          <div class="stat-value">{{ overview.help_request_count || 0 }}</div>
          <div class="stat-desc">社区居民累计求助</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card warning">
          <div class="stat-label">待处理求助</div>
          <div class="stat-value">{{ overview.pending_request_count || 0 }}</div>
          <div class="stat-desc">需要管理员尽快分配</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card success">
          <div class="stat-label">今日新增求助</div>
          <div class="stat-value">{{ overview.today_request_count || 0 }}</div>
          <div class="stat-desc">当天居民提交数量</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card danger">
          <div class="stat-label">高优先级待处理</div>
          <div class="stat-value">{{ overview.critical_pending_request_count || 0 }}</div>
          <div class="stat-desc">高/紧急且尚未处理</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="18" class="summary-row">
      <el-col :span="6">
        <div class="stat-card purple">
          <div class="stat-label">任务完成率</div>
          <div class="stat-value">{{ overview.task_completion_rate || 0 }}%</div>
          <div class="stat-desc">志愿者任务闭环情况</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card cyan">
          <div class="stat-label">生效预警</div>
          <div class="stat-value">{{ overview.active_warning_count || 0 }}</div>
          <div class="stat-desc">当前仍在生效的灾害预警</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card green">
          <div class="stat-label">可用志愿者</div>
          <div class="stat-value">{{ overview.available_volunteer_count || 0 }}</div>
          <div class="stat-desc">当前可被分配任务</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card red">
          <div class="stat-label">低库存物资</div>
          <div class="stat-value">{{ overview.low_stock_material_count || 0 }}</div>
          <div class="stat-desc">库存低于预警阈值</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="18" class="chart-row">
      <el-col :span="12">
        <div class="card">
          <div class="card-title">近 7 日求助趋势</div>
          <div ref="dailyChartRef" class="chart-box"></div>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="card">
          <div class="card-title">求助状态分布</div>
          <div ref="statusChartRef" class="chart-box"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="18" class="chart-row">
      <el-col :span="12">
        <div class="card">
          <div class="card-title">求助紧急程度统计</div>
          <div ref="urgencyChartRef" class="chart-box"></div>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="card">
          <div class="card-title">任务状态统计</div>
          <div ref="taskChartRef" class="chart-box"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="18" class="chart-row">
      <el-col :span="12">
        <div class="card">
          <div class="card-title">预警等级统计</div>
          <div ref="warningChartRef" class="chart-box"></div>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="card">
          <div class="card-title">应急物资库存</div>
          <div ref="materialChartRef" class="chart-box"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import request from '../api/request'

const loading = ref(false)
const overview = ref({})

const dailyChartRef = ref(null)
const statusChartRef = ref(null)
const urgencyChartRef = ref(null)
const taskChartRef = ref(null)
const warningChartRef = ref(null)
const materialChartRef = ref(null)

let dailyChart = null
let statusChart = null
let urgencyChart = null
let taskChart = null
let warningChart = null
let materialChart = null

const safeArray = data => {
  return Array.isArray(data) ? data : []
}

const getChart = (chart, chartRef) => {
  if (!chartRef.value) {
    return null
  }

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  return chart
}

const loadData = async () => {
  loading.value = true

  try {
    const [
      overviewData,
      dailyData,
      statusData,
      urgencyData,
      taskData,
      warningData,
      materialData
    ] = await Promise.all([
      request.get('/analytics/overview/'),
      request.get('/analytics/daily-requests/'),
      request.get('/analytics/help-request-status/'),
      request.get('/analytics/help-request-urgency/'),
      request.get('/analytics/task-status/'),
      request.get('/analytics/warning-levels/'),
      request.get('/analytics/material-stock/')
    ])

    overview.value = overviewData || {}

    await nextTick()

    renderDailyChart(safeArray(dailyData))
    renderStatusChart(safeArray(statusData))
    renderUrgencyChart(safeArray(urgencyData))
    renderTaskChart(safeArray(taskData))
    renderWarningChart(safeArray(warningData))
    renderMaterialChart(safeArray(materialData))
  } finally {
    loading.value = false
  }
}

const renderDailyChart = data => {
  dailyChart = getChart(dailyChart, dailyChartRef)
  if (!dailyChart) return

  dailyChart.setOption({
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      top: 35,
      left: 45,
      right: 25,
      bottom: 35
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.label)
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [
      {
        name: '求助数量',
        type: 'line',
        smooth: true,
        areaStyle: {},
        data: data.map(item => item.count)
      }
    ]
  }, true)
}

const renderStatusChart = data => {
  statusChart = getChart(statusChart, statusChartRef)
  if (!statusChart) return

  statusChart.setOption({
    tooltip: {
      trigger: 'item'
    },
    legend: {
      bottom: 0
    },
    series: [
      {
        name: '求助状态',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        data: data.map(item => ({
          name: item.label,
          value: item.count
        }))
      }
    ]
  }, true)
}

const renderUrgencyChart = data => {
  urgencyChart = getChart(urgencyChart, urgencyChartRef)
  if (!urgencyChart) return

  urgencyChart.setOption({
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      top: 35,
      left: 45,
      right: 25,
      bottom: 35
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.label)
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [
      {
        name: '求助数量',
        type: 'bar',
        data: data.map(item => item.count)
      }
    ]
  }, true)
}

const renderTaskChart = data => {
  taskChart = getChart(taskChart, taskChartRef)
  if (!taskChart) return

  taskChart.setOption({
    tooltip: {
      trigger: 'item'
    },
    legend: {
      bottom: 0
    },
    series: [
      {
        name: '任务状态',
        type: 'pie',
        radius: '65%',
        center: ['50%', '45%'],
        data: data.map(item => ({
          name: item.label,
          value: item.count
        }))
      }
    ]
  }, true)
}

const renderWarningChart = data => {
  warningChart = getChart(warningChart, warningChartRef)
  if (!warningChart) return

  warningChart.setOption({
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      top: 35,
      left: 45,
      right: 25,
      bottom: 35
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.label)
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [
      {
        name: '预警数量',
        type: 'bar',
        data: data.map(item => item.count)
      }
    ]
  }, true)
}

const renderMaterialChart = data => {
  materialChart = getChart(materialChart, materialChartRef)
  if (!materialChart) return

  materialChart.setOption({
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      top: 0
    },
    grid: {
      top: 45,
      left: 45,
      right: 25,
      bottom: 65
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.name),
      axisLabel: {
        interval: 0,
        rotate: 30
      }
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [
      {
        name: '库存数量',
        type: 'bar',
        data: data.map(item => item.quantity)
      },
      {
        name: '预警值',
        type: 'line',
        data: data.map(item => item.warning_quantity)
      }
    ]
  }, true)
}

const resizeCharts = () => {
  dailyChart?.resize()
  statusChart?.resize()
  urgencyChart?.resize()
  taskChart?.resize()
  warningChart?.resize()
  materialChart?.resize()
}

const disposeCharts = () => {
  dailyChart?.dispose()
  statusChart?.dispose()
  urgencyChart?.dispose()
  taskChart?.dispose()
  warningChart?.dispose()
  materialChart?.dispose()

  dailyChart = null
  statusChart = null
  urgencyChart = null
  taskChart = null
  warningChart = null
  materialChart = null
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
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

.summary-row {
  margin-top: 18px;
}

.stat-card {
  min-height: 136px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: white;
  border-radius: 18px;
  padding: 22px;
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.22);
}

.stat-card.warning {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}

.stat-card.success {
  background: linear-gradient(135deg, #10b981, #059669);
}

.stat-card.danger {
  background: linear-gradient(135deg, #ef4444, #dc2626);
}

.stat-card.purple {
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
}

.stat-card.cyan {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
}

.stat-card.green {
  background: linear-gradient(135deg, #22c55e, #16a34a);
}

.stat-card.red {
  background: linear-gradient(135deg, #f43f5e, #be123c);
}

.stat-label {
  font-size: 15px;
  opacity: 0.9;
}

.stat-value {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 800;
}

.stat-desc {
  margin-top: 8px;
  font-size: 13px;
  opacity: 0.85;
}

.chart-row {
  margin-top: 18px;
}

.card-title {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 12px;
}
</style>