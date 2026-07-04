<template>
  <div class="page-container">
    <div class="page-title">数据可视化大屏</div>

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
          <div class="stat-label">任务完成率</div>
          <div class="stat-value">{{ overview.task_completion_rate || 0 }}%</div>
          <div class="stat-desc">志愿者任务闭环情况</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card danger">
          <div class="stat-label">低库存物资</div>
          <div class="stat-value">{{ overview.low_stock_material_count || 0 }}</div>
          <div class="stat-desc">库存低于预警值</div>
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
          <div class="card-title">求助类型统计</div>
          <div ref="typeChartRef" class="chart-box"></div>
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
      <el-col :span="24">
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

const overview = ref({})

const dailyChartRef = ref(null)
const statusChartRef = ref(null)
const typeChartRef = ref(null)
const taskChartRef = ref(null)
const materialChartRef = ref(null)

let dailyChart = null
let statusChart = null
let typeChart = null
let taskChart = null
let materialChart = null

const loadData = async () => {
  const [
    overviewData,
    dailyData,
    statusData,
    typeData,
    taskData,
    materialData
  ] = await Promise.all([
    request.get('/analytics/overview/'),
    request.get('/analytics/daily-requests/'),
    request.get('/analytics/help-request-status/'),
    request.get('/analytics/help-request-types/'),
    request.get('/analytics/task-status/'),
    request.get('/analytics/material-stock/')
  ])

  overview.value = overviewData

  await nextTick()

  renderDailyChart(dailyData)
  renderStatusChart(statusData)
  renderTypeChart(typeData)
  renderTaskChart(taskData)
  renderMaterialChart(materialData)
}

const renderDailyChart = data => {
  dailyChart = echarts.init(dailyChartRef.value)

  dailyChart.setOption({
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.label)
    },
    yAxis: {
      type: 'value'
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
  })
}

const renderStatusChart = data => {
  statusChart = echarts.init(statusChartRef.value)

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
        data: data.map(item => ({
          name: item.label,
          value: item.count
        }))
      }
    ]
  })
}

const renderTypeChart = data => {
  typeChart = echarts.init(typeChartRef.value)

  typeChart.setOption({
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.label),
      axisLabel: {
        interval: 0,
        rotate: 25
      }
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '求助数量',
        type: 'bar',
        data: data.map(item => item.count)
      }
    ]
  })
}

const renderTaskChart = data => {
  taskChart = echarts.init(taskChartRef.value)

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
        data: data.map(item => ({
          name: item.label,
          value: item.count
        }))
      }
    ]
  })
}

const renderMaterialChart = data => {
  materialChart = echarts.init(materialChartRef.value)

  materialChart.setOption({
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      top: 0
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.name)
    },
    yAxis: {
      type: 'value'
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
  })
}

const resizeCharts = () => {
  dailyChart?.resize()
  statusChart?.resize()
  typeChart?.resize()
  taskChart?.resize()
  materialChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)

  dailyChart?.dispose()
  statusChart?.dispose()
  typeChart?.dispose()
  taskChart?.dispose()
  materialChart?.dispose()
})
</script>

<style scoped>
.stat-card {
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