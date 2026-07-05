<template>
  <div class="command-page">
    <div class="command-header">
      <div>
        <div class="page-title">一图统管全景指挥舱</div>
        <div class="page-subtitle">
          在同一张地图上查看高危求助、空闲志愿者与避难点，并支持拖拽式快捷派单。
        </div>
      </div>

      <div class="header-actions">
        <el-switch v-model="showOnlyPending" active-text="只看待处理" inactive-text="全部求助" @change="renderMap" />
        <el-button type="primary" :loading="loading" @click="loadData">刷新指挥舱</el-button>
      </div>
    </div>

    <div class="command-grid">
      <div class="map-panel card">
        <div class="legend-row">
          <span><i class="dot red"></i>高危/待处理求助</span>
          <span><i class="dot green"></i>空闲志愿者</span>
          <span><i class="dot blue"></i>避难点</span>
        </div>
        <div id="commandMap" ref="mapRef" class="command-map"></div>
      </div>

      <div class="side-panel">
        <div class="card panel-card">
          <div class="section-title">待调度求助</div>
          <div class="section-subtitle">把右侧志愿者卡片拖到求助卡片上即可快捷派单。</div>

          <div v-if="pendingRequests.length === 0" class="empty-tip">暂无待处理求助</div>

          <div
            v-for="item in pendingRequests"
            :key="item.id"
            class="request-card"
            @dragover.prevent
            @drop="dropAssign(item)"
          >
            <div class="request-top">
              <el-tag :type="urgencyTagType(item.urgency)">{{ item.urgency_display }}</el-tag>
              <span>#{{ item.id }}</span>
            </div>
            <div class="request-title">{{ item.summary || item.description }}</div>
            <div class="request-meta">{{ item.type_display }}｜{{ item.address || '未填写地址' }}</div>
          </div>
        </div>

        <div class="card panel-card">
          <div class="section-title">可调度志愿者</div>
          <div class="section-subtitle">拖拽志愿者到上方求助卡片，或先在地图中查看空间分布。</div>

          <div v-if="availableVolunteers.length === 0" class="empty-tip">暂无空闲志愿者</div>

          <div
            v-for="item in availableVolunteers"
            :key="item.id"
            class="volunteer-card"
            draggable="true"
            @dragstart="draggedVolunteer = item"
          >
            <div class="volunteer-avatar">{{ item.username.slice(0, 1) }}</div>
            <div>
              <div class="volunteer-name">{{ item.username }}</div>
              <div class="volunteer-meta">{{ item.phone || '无电话' }}｜{{ item.skills || '未登记擅长任务' }}</div>
            </div>
          </div>
        </div>

        <div class="card panel-card">
          <div class="section-title">避难点状态</div>
          <div class="shelter-line" v-for="item in shelters" :key="item.id">
            <span>{{ item.name }}</span>
            <el-tag size="small" :type="item.is_available ? 'success' : 'info'">
              {{ item.is_available ? '已开放' : '未开放' }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const loading = ref(false)
const mapRef = ref(null)
const showOnlyPending = ref(true)
const helpRequests = ref([])
const volunteers = ref([])
const shelters = ref([])
const draggedVolunteer = ref(null)

let commandMap = null
let mapScriptPromise = null

const pendingRequests = computed(() => helpRequests.value.filter(item => item.status === 'pending'))
const availableVolunteers = computed(() => volunteers.value.filter(item => item.is_available))

const loadBaiduMapScript = () => {
  if (window.BMapGL) return Promise.resolve(window.BMapGL)
  if (mapScriptPromise) return mapScriptPromise

  const ak = import.meta.env.VITE_BAIDU_MAP_AK
  if (!ak) return Promise.reject(new Error('请先配置 VITE_BAIDU_MAP_AK'))

  mapScriptPromise = new Promise((resolve, reject) => {
    const callbackName = '__onCommandMapLoaded'
    window[callbackName] = () => {
      if (window.BMapGL) resolve(window.BMapGL)
      else reject(new Error('百度地图加载失败'))
      delete window[callbackName]
    }
    const script = document.createElement('script')
    script.src = `https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${ak}&callback=${callbackName}`
    script.onerror = () => reject(new Error('百度地图脚本加载失败'))
    document.head.appendChild(script)
  })
  return mapScriptPromise
}

const makeLabel = (BMapGL, point, text, className, title) => {
  const label = new BMapGL.Label(text, { position: point, offset: new BMapGL.Size(-14, -14) })
  label.setStyle({
    width: '28px',
    height: '28px',
    lineHeight: '28px',
    textAlign: 'center',
    borderRadius: '999px',
    border: '2px solid #ffffff',
    color: '#ffffff',
    fontWeight: '700',
    boxShadow: '0 4px 14px rgba(15,23,42,.28)',
    backgroundColor: className === 'red' ? '#ef4444' : className === 'green' ? '#16a34a' : '#2563eb',
    cursor: 'pointer'
  })
  label.addEventListener('click', () => {
    const info = new BMapGL.InfoWindow(title, { width: 280, title: '指挥舱详情' })
    commandMap.openInfoWindow(info, point)
  })
  commandMap.addOverlay(label)
}

const renderMap = async () => {
  try {
    const BMapGL = await loadBaiduMapScript()
    await nextTick()
    if (!mapRef.value) return

    if (!commandMap) {
      commandMap = new BMapGL.Map('commandMap')
      commandMap.centerAndZoom(new BMapGL.Point(116.404, 39.915), 12)
      commandMap.enableScrollWheelZoom(true)
      commandMap.addControl(new BMapGL.ScaleControl())
      commandMap.addControl(new BMapGL.ZoomControl())
    }

    commandMap.clearOverlays()
    const points = []

    const requests = showOnlyPending.value ? pendingRequests.value : helpRequests.value
    requests.forEach(item => {
      if (!item.longitude || !item.latitude) return
      const point = new BMapGL.Point(Number(item.longitude), Number(item.latitude))
      points.push(point)
      makeLabel(BMapGL, point, '求', 'red', `
        <div style="line-height:1.8">
          <strong>${item.urgency_display} ${item.type_display}</strong><br/>
          ${item.summary || item.description || '-'}<br/>
          ${item.address || '-'}
        </div>
      `)
    })

    volunteers.value.forEach(item => {
      if (!item.longitude || !item.latitude) return
      const point = new BMapGL.Point(Number(item.longitude), Number(item.latitude))
      points.push(point)
      makeLabel(BMapGL, point, '志', item.is_available ? 'green' : 'blue', `
        <div style="line-height:1.8">
          <strong>${item.username}</strong><br/>
          ${item.is_available ? '空闲' : '忙碌'}｜${item.phone || '-'}<br/>
          擅长：${item.skills || '-'}
        </div>
      `)
    })

    shelters.value.forEach(item => {
      if (!item.longitude || !item.latitude) return
      const point = new BMapGL.Point(Number(item.longitude), Number(item.latitude))
      points.push(point)
      makeLabel(BMapGL, point, '避', 'blue', `
        <div style="line-height:1.8">
          <strong>${item.name}</strong><br/>
          ${item.is_available ? '已开放' : '未开放'}｜容量 ${item.capacity}<br/>
          ${item.address || '-'}
        </div>
      `)
    })

    if (points.length > 0) commandMap.setViewport(points)
  } catch (error) {
    ElMessage.warning(error.message || '地图加载失败')
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await request.get('/analytics/command-center/')
    helpRequests.value = data.help_requests || []
    volunteers.value = data.volunteers || []
    shelters.value = data.shelters || []
    await renderMap()
  } finally {
    loading.value = false
  }
}

const dropAssign = async helpRequest => {
  if (!draggedVolunteer.value) return

  await ElMessageBox.confirm(
    `确定将志愿者「${draggedVolunteer.value.username}」分配给求助 #${helpRequest.id} 吗？`,
    '快捷派单确认',
    { type: 'warning' }
  )

  await request.post(`/help-requests/${helpRequest.id}/assign/`, {
    volunteer_id: draggedVolunteer.value.id
  })
  ElMessage.success('派单成功')
  draggedVolunteer.value = null
  await loadData()
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
.command-page {
  padding: 20px;
}

.command-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.command-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 18px;
}

.command-map {
  width: 100%;
  height: calc(100vh - 170px);
  min-height: 640px;
  border-radius: 16px;
  overflow: hidden;
  background: #eef2ff;
}

.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-bottom: 12px;
  color: #475569;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
}

.dot.red { background: #ef4444; }
.dot.green { background: #16a34a; }
.dot.blue { background: #2563eb; }

.side-panel {
  display: grid;
  gap: 18px;
  align-content: start;
}

.panel-card {
  max-height: 310px;
  overflow: auto;
}

.section-title {
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 6px;
}

.section-subtitle {
  color: #64748b;
  font-size: 13px;
  margin-bottom: 12px;
  line-height: 1.6;
}

.empty-tip {
  color: #94a3b8;
  padding: 20px 0;
  text-align: center;
}

.request-card,
.volunteer-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: #ffffff;
}

.request-card {
  border-left: 4px solid #ef4444;
}

.request-card:hover,
.volunteer-card:hover {
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.request-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #64748b;
  margin-bottom: 8px;
}

.request-title {
  font-weight: 700;
  color: #1e293b;
  line-height: 1.5;
}

.request-meta,
.volunteer-meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.volunteer-card {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: grab;
  border-left: 4px solid #16a34a;
}

.volunteer-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #dcfce7;
  color: #15803d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
}

.volunteer-name {
  font-weight: 700;
}

.shelter-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
}

@media (max-width: 1200px) {
  .command-grid {
    grid-template-columns: 1fr;
  }

  .command-map {
    height: 560px;
  }
}
</style>
