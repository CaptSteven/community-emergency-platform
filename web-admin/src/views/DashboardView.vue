<template>
  <div class="page-container dashboard-page">
    <div class="page-header">
      <div>
        <div class="page-title">数据可视化大屏</div>
        <div class="page-subtitle">
          汇总社区求助、志愿者任务、灾害预警和应急资源数据，辅助管理员快速研判。
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
      v-if="overview.critical_pending_request_count > 0"
      class="dashboard-alert"
      type="warning"
      show-icon
      :closable="false"
      :title="`当前有 ${overview.critical_pending_request_count} 条高优先级待处理求助，请尽快分配志愿者。`"
    />

    <div class="section-title">应急求助概览</div>
    <el-row :gutter="18">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-label">总求助数</div>
          <div class="stat-value">{{ overview.help_request_count || 0 }}</div>
          <div class="stat-desc">社区居民累计求助</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card warning">
          <div class="stat-icon">⏳</div>
          <div class="stat-label">待处理求助</div>
          <div class="stat-value">{{ overview.pending_request_count || 0 }}</div>
          <div class="stat-desc">需要管理员尽快分配</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card success">
          <div class="stat-icon">🆕</div>
          <div class="stat-label">今日新增求助</div>
          <div class="stat-value">{{ overview.today_request_count || 0 }}</div>
          <div class="stat-desc">当天居民提交数量</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card danger">
          <div class="stat-icon">🚨</div>
          <div class="stat-label">高优先级待处理</div>
          <div class="stat-value">{{ overview.critical_pending_request_count || 0 }}</div>
          <div class="stat-desc">高/紧急且尚未处理</div>
        </div>
      </el-col>
    </el-row>

    <div class="section-title section-title--service">
      <span class="section-badge">社区服务</span>社区长期服务
      <span class="section-sub">日常上门服务与居家关怀，是平台的主要功能</span>
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
        <div class="stat-card service-card success">
          <div class="stat-icon">🚪</div>
          <div class="stat-label">本周上门工单</div>
          <div class="stat-value">{{ serviceOverview.visits_this_week || 0 }}</div>
          <div class="stat-desc">已完成 {{ serviceOverview.completed_this_week || 0 }} 单</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card service-card warning">
          <div class="stat-icon">🔧</div>
          <div class="stat-label">进行中工单</div>
          <div class="stat-value">{{ serviceOverview.pending_visits || 0 }}</div>
          <div class="stat-desc">已排班 / 服务中</div>
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

    <div class="section-title">运行状态与资源</div>
    <el-row :gutter="18" class="summary-row">
      <el-col :span="6">
        <div class="stat-card purple">
          <div class="stat-icon">✅</div>
          <div class="stat-label">任务完成率</div>
          <div class="stat-value">{{ overview.task_completion_rate || 0 }}%</div>
          <div class="stat-desc">志愿者任务闭环情况</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card cyan">
          <div class="stat-icon">⚠️</div>
          <div class="stat-label">生效预警</div>
          <div class="stat-value">{{ overview.active_warning_count || 0 }}</div>
          <div class="stat-desc">当前仍在生效的灾害预警</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card green">
          <div class="stat-icon">🙋</div>
          <div class="stat-label">可用志愿者</div>
          <div class="stat-value">{{ overview.available_volunteer_count || 0 }}</div>
          <div class="stat-desc">当前可被分配任务</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="stat-card red">
          <div class="stat-icon">📦</div>
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

    <el-row :gutter="18" class="chart-row">
      <el-col :xs="24" :lg="12">
        <div class="card">
          <div class="card-title">求助地理分布地图</div>
          <div class="card-subtitle">点击地图标记可查看求助详情。</div>
          <div id="baiduMapContainer" ref="baiduMapRef" class="baidu-map-box"></div>
        </div>
      </el-col>

      <el-col :xs="24" :lg="12">
        <div class="card map-card">
          <div class="map-card-header">
            <div>
              <div class="card-title">应急热力图</div>
              <div class="card-subtitle">
                当前展示：{{ heatmapType === 'disaster' ? '灾害发生热力' : '志愿者位置热力' }}
              </div>
            </div>

            <el-radio-group
              v-model="heatmapType"
              size="small"
              @change="handleHeatmapTypeChange"
            >
              <el-radio-button label="disaster">灾害热力</el-radio-button>
              <el-radio-button label="volunteer">志愿者热力</el-radio-button>
            </el-radio-group>
          </div>

          <div class="heatmap-tip">
            灾害热力根据求助紧急程度和处理状态计算；志愿者热力根据志愿者当前位置和是否空闲计算。
          </div>
          <div id="heatMapContainer" ref="heatMapRef" class="baidu-map-box"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import request from '../api/request'

const AUTO_REFRESH_INTERVAL = 10000

const loading = ref(false)
const overview = ref({})
const serviceOverview = ref({})
const autoRefresh = ref(true)
const lastUpdated = ref('')

const dailyChartRef = ref(null)
const statusChartRef = ref(null)
const urgencyChartRef = ref(null)
const taskChartRef = ref(null)
const warningChartRef = ref(null)
const materialChartRef = ref(null)
const baiduMapRef = ref(null)
const heatMapRef = ref(null)
const heatmapType = ref('disaster')

let dailyChart = null
let statusChart = null
let urgencyChart = null
let taskChart = null
let warningChart = null
let materialChart = null
let refreshTimer = null

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

const formatDateTime = date => {
  const pad = value => String(value).padStart(2, '0')

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const getHeatmapApiUrl = () => {
  return heatmapType.value === 'volunteer'
    ? '/analytics/volunteer-heatmap/'
    : '/analytics/disaster-heatmap/'
}

const loadData = async (options = {}) => {
  const silent = options.silent === true

  if (!silent) {
    loading.value = true
  }

  try {
    const [
      overviewData,
      dailyData,
      statusData,
      urgencyData,
      taskData,
      warningData,
      materialData,
      mapData,
      heatData,
      serviceData
    ] = await Promise.all([
      request.get('/analytics/overview/'),
      request.get('/analytics/daily-requests/'),
      request.get('/analytics/help-request-status/'),
      request.get('/analytics/help-request-urgency/'),
      request.get('/analytics/task-status/'),
      request.get('/analytics/warning-levels/'),
      request.get('/analytics/material-stock/'),
      request.get('/analytics/help-request-map/'),
      request.get(getHeatmapApiUrl()),
      request.get('/analytics/service-overview/')
    ])

    overview.value = overviewData || {}
    serviceOverview.value = serviceData || {}
    lastUpdated.value = formatDateTime(new Date())

    await nextTick()

    renderDailyChart(safeArray(dailyData))
    renderStatusChart(safeArray(statusData))
    renderUrgencyChart(safeArray(urgencyData))
    renderTaskChart(safeArray(taskData))
    renderWarningChart(safeArray(warningData))
    renderMaterialChart(safeArray(materialData))
    await renderBaiduMap(safeArray(mapData))
    await renderHeatMap(safeArray(heatData))
  } finally {
    if (!silent) {
      loading.value = false
    }
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

let baiduMap = null
let baiduMapScriptPromise = null

const loadBaiduMapScript = () => {
  if (window.BMapGL) {
    return Promise.resolve(window.BMapGL)
  }

  if (baiduMapScriptPromise) {
    return baiduMapScriptPromise
  }

  const ak = import.meta.env.VITE_BAIDU_MAP_AK

  if (!ak) {
    return Promise.reject(new Error('请先在 web-admin/.env 中配置 VITE_BAIDU_MAP_AK'))
  }

  baiduMapScriptPromise = new Promise((resolve, reject) => {
    const callbackName = '__onBaiduMapLoaded'

    window[callbackName] = () => {
      if (window.BMapGL) {
        resolve(window.BMapGL)
      } else {
        reject(new Error('百度地图加载失败：BMapGL 不存在'))
      }

      delete window[callbackName]
    }

    const script = document.createElement('script')
    script.src = `https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${ak}&callback=${callbackName}`
    script.onerror = () => reject(new Error('百度地图脚本加载失败'))
    document.head.appendChild(script)
  })

  return baiduMapScriptPromise
}

const renderBaiduMap = async data => {
  const BMapGL = await loadBaiduMapScript()

  if (!baiduMapRef.value) {
    return
  }

  if (!baiduMap) {
    baiduMap = new BMapGL.Map('baiduMapContainer')

    // 默认中心点：北京。你可以换成你项目所在城市的经纬度
    const defaultPoint = new BMapGL.Point(116.404, 39.915)

    baiduMap.centerAndZoom(defaultPoint, 12)
    baiduMap.enableScrollWheelZoom(true)
    baiduMap.addControl(new BMapGL.ScaleControl())
    baiduMap.addControl(new BMapGL.ZoomControl())
  }

  baiduMap.clearOverlays()

  const validData = data.filter(item => item.longitude && item.latitude)

  if (validData.length === 0) {
    return
  }

  const points = []

  validData.forEach(item => {
    const point = new BMapGL.Point(Number(item.longitude), Number(item.latitude))
    points.push(point)

    const marker = new BMapGL.Marker(point)
    baiduMap.addOverlay(marker)

    marker.addEventListener('click', () => {
      const content = `
        <div style="line-height: 1.8;">
          <div><strong>求助ID：</strong>${item.id}</div>
          <div><strong>类型：</strong>${item.request_type_display || '-'}</div>
          <div><strong>紧急程度：</strong>${item.urgency_display || '-'}</div>
          <div><strong>状态：</strong>${item.status_display || '-'}</div>
          <div><strong>地址：</strong>${item.address || '-'}</div>
          <div><strong>描述：</strong>${item.description || '-'}</div>
        </div>
      `

      const infoWindow = new BMapGL.InfoWindow(content, {
        width: 300,
        title: '求助详情'
      })

      baiduMap.openInfoWindow(infoWindow, point)
    })
  })

  baiduMap.setViewport(points)
}

let heatMap = null
let heatView = null
let heatLayer = null
let mapvglScriptPromise = null

const loadMapVglScript = () => {
  if (window.mapvgl) {
    return Promise.resolve(window.mapvgl)
  }

  if (mapvglScriptPromise) {
    return mapvglScriptPromise
  }

  mapvglScriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://code.bdstatic.com/npm/mapvgl@1.0.0-beta.189/dist/mapvgl.min.js'

    script.onload = () => {
      if (window.mapvgl) {
        resolve(window.mapvgl)
      } else {
        reject(new Error('MapVGL 加载失败：window.mapvgl 不存在'))
      }
    }

    script.onerror = () => reject(new Error('MapVGL 脚本加载失败'))
    document.head.appendChild(script)
  })

  return mapvglScriptPromise
}

const toHeatmapData = data => {
  return data
    .filter(item => item.longitude && item.latitude)
    .map(item => ({
      geometry: {
        type: 'Point',
        coordinates: [Number(item.longitude), Number(item.latitude)]
      },
      properties: {
        count: Number(item.count || item.urgency_weight || 50)
      },
      count: Number(item.count || item.urgency_weight || 50)
    }))
}

const getValidMapPoints = (BMapGL, data) => {
  return data
    .filter(item => item.longitude && item.latitude)
    .map(item => new BMapGL.Point(Number(item.longitude), Number(item.latitude)))
}

const renderHeatMap = async data => {
  const BMapGL = await loadBaiduMapScript()
  const mapvgl = await loadMapVglScript()

  if (!heatMapRef.value) {
    return
  }

  if (!heatMap) {
    heatMap = new BMapGL.Map('heatMapContainer')
    const defaultPoint = new BMapGL.Point(116.404, 39.915)

    heatMap.centerAndZoom(defaultPoint, 12)
    heatMap.enableScrollWheelZoom(true)
    heatMap.addControl(new BMapGL.ScaleControl())
    heatMap.addControl(new BMapGL.ZoomControl())

    heatView = new mapvgl.View({
      map: heatMap
    })

    heatLayer = new mapvgl.HeatmapLayer({
      size: 70,
      max: 100,
      min: 0,
      unit: 'px',
      height: 0,
      gradient: {
        0.0: 'rgba(0, 102, 255, 0.45)',
        0.35: 'rgba(0, 200, 120, 0.55)',
        0.65: 'rgba(255, 215, 0, 0.75)',
        1.0: 'rgba(255, 0, 0, 0.9)'
      },
      data: []
    })

    heatView.addLayer(heatLayer)
  }

  const heatData = toHeatmapData(data)

  if (typeof heatLayer.setData === 'function') {
    heatLayer.setData(heatData)
  } else {
    if (heatView && heatLayer && typeof heatView.removeLayer === 'function') {
      heatView.removeLayer(heatLayer)
    }

    heatLayer = new mapvgl.HeatmapLayer({
      size: 70,
      max: 100,
      min: 0,
      unit: 'px',
      height: 0,
      gradient: {
        0.0: 'rgba(0, 102, 255, 0.45)',
        0.35: 'rgba(0, 200, 120, 0.55)',
        0.65: 'rgba(255, 215, 0, 0.75)',
        1.0: 'rgba(255, 0, 0, 0.9)'
      },
      data: heatData
    })

    heatView.addLayer(heatLayer)
  }

  const points = getValidMapPoints(BMapGL, data)
  if (points.length > 0) {
    heatMap.setViewport(points)
  }
}

const handleHeatmapTypeChange = async () => {
  try {
    const heatData = await request.get(getHeatmapApiUrl())
    await nextTick()
    await renderHeatMap(safeArray(heatData))
  } catch (error) {
    console.error(error)
  }
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

/* 社区服务分区：作为主功能更突出（绿色强调 + 徽标 + 副标题） */
.section-title--service {
  border-left-color: #16a34a;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 28px;
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
  /* 主功能区块用柔和绿意底衬托，视觉上更突出 */
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

/* 卡片右上角柔光装饰 */
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

/* 右上角大号 emoji 图标 */
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

.stat-card.red {
  background: linear-gradient(135deg, #f43f5e, #be123c);
  box-shadow: 0 8px 22px rgba(244, 63, 94, 0.26);
}

/* 服务卡片：更高一点、白色描边，强调主功能地位 */
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
  margin-bottom: 12px;
}

.card-subtitle {
  margin-top: -4px;
  margin-bottom: 12px;
  color: #64748b;
  font-size: 13px;
}

.map-card {
  height: 100%;
}

.map-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.heatmap-tip {
  margin-top: -4px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 12px;
  line-height: 1.6;
}

.baidu-map-box {
  width: 100%;
  height: 520px;
  border-radius: 14px;
  overflow: hidden;
  background: #f1f5f9;
}

@media (max-width: 1200px) {
  .map-card {
    margin-top: 18px;
  }
}
</style>
