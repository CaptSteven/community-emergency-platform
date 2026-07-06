<template>
  <div class="command-page">
    <div class="command-header">
      <div>
        <div class="page-title">一图统管全景指挥舱</div>
        <div class="page-subtitle">
          在同一张地图上查看高危求助、空闲志愿者与避难点。按住绿色“志”点拖到红色“求”点或红色调度圈内，即可完成地图派单；蓝色“避”点仅用于避难点查看，不参与派单。
        </div>
      </div>

      <div class="header-actions">
        <el-switch v-model="showOnlyPending" active-text="只看可调度" inactive-text="全部求助" @change="renderMap" />
        <el-button type="primary" :loading="loading" @click="loadData">刷新指挥舱</el-button>
      </div>
    </div>

    <div class="command-grid">
      <div class="map-panel card">
        <div class="legend-row">
          <span>求助点按状态：<i style="display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 3px 0 8px;vertical-align:middle;background:#ef4444"></i>待处理<i style="display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 3px 0 8px;vertical-align:middle;background:#f97316"></i>已分配<i style="display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 3px 0 8px;vertical-align:middle;background:#3b82f6"></i>处理中<i style="display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 3px 0 8px;vertical-align:middle;background:#22c55e"></i>已完成<i style="display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 3px 0 8px;vertical-align:middle;background:#94a3b8"></i>已取消</span>
          <span><i class="dot green"></i>空闲志愿者，可拖拽派单</span>
          <span><i class="dot blue"></i>避难点，仅展示/查看，不可派单</span>
        </div>
        <div id="commandMap" ref="mapRef" class="command-map"></div>
      </div>

      <div class="side-panel">
        <div class="card panel-card">
          <div class="section-title">可调度求助</div>
          <div class="section-subtitle">右侧卡片可拖拽派单；地图上也可以把绿色“志”点拖到红色“求”点或红色调度圈内。</div>

          <div v-if="pendingRequests.length === 0" class="empty-tip">暂无可调度求助</div>

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
            <div v-if="item.task_id && !item.assigned_volunteer_id" class="request-meta warning">已有开放任务 #{{ item.task_id }}，但尚未绑定志愿者，可继续派单</div>
          </div>
        </div>

        <div class="card panel-card">
          <div class="section-title">可调度志愿者</div>
          <div class="section-subtitle">可拖拽志愿者卡片到求助卡片，也可直接拖动地图上的绿色“志”点到红色“求”点；蓝色“避”点不会触发派单。</div>

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
const dispatching = ref(false)
const mapRef = ref(null)
const showOnlyPending = ref(true)
const helpRequests = ref([])
const volunteers = ref([])
const shelters = ref([])
const draggedVolunteer = ref(null)
const highlightedRequestId = ref(null)

let commandMap = null
let mapScriptPromise = null
let BMapClass = null
let requestDropCircles = []
let requestMarkers = []
let volunteerMarkers = []
let shelterMarkers = []

// 地图拖拽派单命中规则：
// 1. 地理距离 <= 500 米：适合真实空间调度；
// 2. 屏幕像素距离 <= 90px：适合管理员把绿色“志”点拖到视觉上的红色“求”点时准确命中；
// 两者满足任意一个即可弹出确认派单。
const DISPATCH_RADIUS_KM = 0.5
const HIT_RADIUS_PX = 90
// 避难点是资源点，不是求助点。拖拽落点如果明显落在蓝色“避”点附近，
// 必须阻断派单，避免“拖到避难点也被当作求助处理”。
const SHELTER_BLOCK_RADIUS_KM = 0.2
const SHELTER_BLOCK_RADIUS_PX = 76
const REQUEST_DIRECT_HIT_RADIUS_PX = 45

const statusMarkerColor = status => {
  const map = {
    pending: '#ef4444',
    assigned: '#f97316',
    processing: '#3b82f6',
    completed: '#22c55e',
    cancelled: '#94a3b8'
  }
  return map[status] || '#ef4444'
}

const pendingRequests = computed(() => helpRequests.value.filter(item => item.is_dispatchable === true || (item.status === 'pending' && !item.assigned_volunteer_id)))
const availableVolunteers = computed(() => volunteers.value.filter(item => item.is_available))

const loadBaiduMapScript = () => {
  if (window.BMapGL) {
    BMapClass = window.BMapGL
    return Promise.resolve(window.BMapGL)
  }
  if (mapScriptPromise) return mapScriptPromise

  const ak = import.meta.env.VITE_BAIDU_MAP_AK
  if (!ak) return Promise.reject(new Error('请先配置 VITE_BAIDU_MAP_AK'))

  mapScriptPromise = new Promise((resolve, reject) => {
    const callbackName = '__onCommandMapLoaded'
    window[callbackName] = () => {
      if (window.BMapGL) {
        BMapClass = window.BMapGL
        resolve(window.BMapGL)
      } else {
        reject(new Error('百度地图加载失败'))
      }
      delete window[callbackName]
    }
    const script = document.createElement('script')
    script.src = `https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${ak}&callback=${callbackName}`
    script.onerror = () => reject(new Error('百度地图脚本加载失败'))
    document.head.appendChild(script)
  })
  return mapScriptPromise
}

const createCircleIcon = (BMapGL, text, color, options = {}) => {
  const size = options.size || 42
  const radius = options.radius || 17
  const fontSize = options.fontSize || 16
  const strokeWidth = options.strokeWidth || 4
  const strokeColor = options.strokeColor || '#ffffff'
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size / 2}" cy="${size / 2}" r="${radius}" fill="${color}" stroke="${strokeColor}" stroke-width="${strokeWidth}"/>
      <text x="${size / 2}" y="${size / 2 + 5}" text-anchor="middle" font-size="${fontSize}" font-family="Arial, sans-serif" font-weight="700" fill="#ffffff">${text}</text>
    </svg>
  `
  const url = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
  return new BMapGL.Icon(url, new BMapGL.Size(size, size), {
    anchor: new BMapGL.Size(size / 2, size / 2),
    imageSize: new BMapGL.Size(size, size)
  })
}

const openInfoWindow = (BMapGL, point, title) => {
  const info = new BMapGL.InfoWindow(title, { width: 300, title: '指挥舱详情' })
  commandMap.openInfoWindow(info, point)
}

const makeStaticMarker = (BMapGL, point, text, color, title) => {
  const marker = new BMapGL.Marker(point, {
    icon: createCircleIcon(BMapGL, text, color)
  })
  marker.addEventListener('click', () => openInfoWindow(BMapGL, point, title))
  commandMap.addOverlay(marker)
  return marker
}

const makeRequestDispatchCircle = (BMapGL, point, isHighlighted = false) => {
  const circle = new BMapGL.Circle(point, DISPATCH_RADIUS_KM * 1000, {
    strokeColor: isHighlighted ? '#facc15' : '#ef4444',
    strokeWeight: isHighlighted ? 3 : 1,
    strokeOpacity: isHighlighted ? 0.9 : 0.35,
    fillColor: isHighlighted ? '#facc15' : '#ef4444',
    fillOpacity: isHighlighted ? 0.16 : 0.08
  })
  requestDropCircles.push(circle)
  commandMap.addOverlay(circle)
}

const haversineKm = (lng1, lat1, lng2, lat2) => {
  const toRad = value => Number(value) * Math.PI / 180
  const radius = 6371.0088
  const dLng = toRad(lng2) - toRad(lng1)
  const dLat = toRad(lat2) - toRad(lat1)
  const rLat1 = toRad(lat1)
  const rLat2 = toRad(lat2)
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rLat1) * Math.cos(rLat2) * Math.sin(dLng / 2) ** 2
  return 2 * radius * Math.asin(Math.sqrt(a))
}

const getMapDistanceKm = (startPoint, endPoint) => {
  if (commandMap?.getDistance) {
    return commandMap.getDistance(startPoint, endPoint) / 1000
  }
  return haversineKm(startPoint.lng, startPoint.lat, endPoint.lng, endPoint.lat)
}

const getPointPixel = point => {
  if (!commandMap || !point) return null
  try {
    if (typeof commandMap.pointToOverlayPixel === 'function') {
      return commandMap.pointToOverlayPixel(point)
    }
    if (typeof commandMap.pointToPixel === 'function') {
      return commandMap.pointToPixel(point)
    }
  } catch (error) {
    return null
  }
  return null
}

const getPixelDistance = (pointA, pointB) => {
  const pixelA = getPointPixel(pointA)
  const pixelB = getPointPixel(pointB)
  if (!pixelA || !pixelB) return Number.POSITIVE_INFINITY
  const dx = Number(pixelA.x) - Number(pixelB.x)
  const dy = Number(pixelA.y) - Number(pixelB.y)
  return Math.sqrt(dx * dx + dy * dy)
}

const createPointFromItem = item => {
  if (!BMapClass || !item?.longitude || !item?.latitude) return null
  return new BMapClass.Point(Number(item.longitude), Number(item.latitude))
}

const formatDistance = distanceKm => {
  if (!Number.isFinite(distanceKm)) return '未知距离'
  if (distanceKm < 1) return `${Math.round(distanceKm * 1000)} 米`
  return `${distanceKm.toFixed(2)} 公里`
}

const findBestPendingRequest = dropPoint => {
  const candidates = pendingRequests.value
    .filter(item => item.longitude && item.latitude)
    .map(item => {
      const requestPoint = createPointFromItem(item)
      const distanceKm = getMapDistanceKm(dropPoint, requestPoint)
      const pixelDistance = getPixelDistance(dropPoint, requestPoint)
      const geographicHit = distanceKm <= DISPATCH_RADIUS_KM
      const visualHit = pixelDistance <= HIT_RADIUS_PX
      return {
        ...item,
        requestPoint,
        distanceKm,
        pixelDistance,
        geographicHit,
        visualHit,
        canDispatch: geographicHit || visualHit
      }
    })
    .sort((a, b) => {
      if (a.canDispatch !== b.canDispatch) return a.canDispatch ? -1 : 1
      if (a.visualHit !== b.visualHit) return a.visualHit ? -1 : 1
      if (a.geographicHit !== b.geographicHit) return a.geographicHit ? -1 : 1
      return a.pixelDistance - b.pixelDistance || a.distanceKm - b.distanceKm
    })

  return {
    target: candidates.find(item => item.canDispatch) || null,
    nearest: candidates[0] || null
  }
}


const findNearestShelter = dropPoint => {
  const candidates = shelters.value
    .filter(item => item.longitude && item.latitude)
    .map(item => {
      const shelterPoint = createPointFromItem(item)
      const distanceKm = getMapDistanceKm(dropPoint, shelterPoint)
      const pixelDistance = getPixelDistance(dropPoint, shelterPoint)
      return {
        ...item,
        shelterPoint,
        distanceKm,
        pixelDistance,
        isShelterHit: distanceKm <= SHELTER_BLOCK_RADIUS_KM || pixelDistance <= SHELTER_BLOCK_RADIUS_PX
      }
    })
    .sort((a, b) => a.pixelDistance - b.pixelDistance || a.distanceKm - b.distanceKm)

  return candidates[0] || null
}

const resolveDispatchTarget = dropPoint => {
  const { target, nearest } = findBestPendingRequest(dropPoint)
  const nearestShelter = findNearestShelter(dropPoint)

  if (nearestShelter?.isShelterHit) {
    // 如果鼠标/Marker 明显更靠近蓝色避难点，则阻断派单；
    // 只有当落点更明确地命中红色求助点时，才允许派单。
    const requestIsClearer = target && (
      target.pixelDistance <= REQUEST_DIRECT_HIT_RADIUS_PX ||
      target.pixelDistance + 12 < nearestShelter.pixelDistance
    )

    if (!requestIsClearer) {
      return {
        target: null,
        nearest,
        blockedShelter: nearestShelter
      }
    }
  }

  return {
    target,
    nearest,
    blockedShelter: null
  }
}

const setRequestMarkerHighlighted = requestId => {
  highlightedRequestId.value = requestId || null
  requestMarkers.forEach(({ marker, item }) => {
    if (!BMapClass) return
    const isHighlighted = item.id === requestId
    marker.setIcon(createCircleIcon(BMapClass, '求', isHighlighted ? '#facc15' : '#ef4444', {
      size: isHighlighted ? 52 : 42,
      radius: isHighlighted ? 21 : 17,
      fontSize: isHighlighted ? 18 : 16,
      strokeWidth: isHighlighted ? 5 : 4,
      strokeColor: isHighlighted ? '#ef4444' : '#ffffff'
    }))
  })
}

const resetVolunteerMarkerPosition = (marker, volunteer) => {
  const originPoint = marker?.__originPoint || createPointFromItem(volunteer)
  if (!originPoint || !marker) return
  marker.setPosition(originPoint)
}

const dispatchVolunteerToRequest = async (volunteer, helpRequest, marker) => {
  if (!volunteer?.id || !helpRequest?.id || dispatching.value) return

  try {
    dispatching.value = true

    // 视觉上把志愿者点吸附到求助点，提升“拖到了红点上”的反馈。
    if (helpRequest.requestPoint && marker?.setPosition) {
      marker.setPosition(helpRequest.requestPoint)
    }

    await ElMessageBox.confirm(
      `确定将志愿者「${volunteer.username}」通过地图拖拽派给求助 #${helpRequest.id} 吗？\n\n求助：${helpRequest.summary || helpRequest.description || '-'}\n识别距离：约 ${formatDistance(helpRequest.distanceKm)}`,
      '地图拖拽派单确认',
      { type: 'warning', confirmButtonText: '确认派单', cancelButtonText: '取消' }
    )

    await request.post(`/help-requests/${helpRequest.id}/map-dispatch/`, {
      volunteer_id: volunteer.id,
      drop_longitude: marker?.getPosition ? marker.getPosition().lng : undefined,
      drop_latitude: marker?.getPosition ? marker.getPosition().lat : undefined
    })

    ElMessage.success('地图拖拽派单成功')
    draggedVolunteer.value = null
    setRequestMarkerHighlighted(null)
    await loadData()
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      ElMessage.info('已取消地图拖拽派单')
    }
    resetVolunteerMarkerPosition(marker, volunteer)
  } finally {
    dispatching.value = false
  }
}

const getDropPointFromEvent = (event, marker) => {
  // BMapGL 不同版本/环境里拖拽事件字段可能不同；marker.getPosition() 最稳定。
  if (marker?.getPosition) return marker.getPosition()
  if (event?.point) return event.point
  if (event?.latLng) return event.latLng
  return null
}

const handleVolunteerMarkerDragging = (marker) => {
  const point = marker?.getPosition ? marker.getPosition() : null
  if (!point) return
  const { target, blockedShelter } = resolveDispatchTarget(point)
  setRequestMarkerHighlighted(blockedShelter ? null : target?.id || null)
}

const handleVolunteerMarkerDropped = async (volunteer, event, marker) => {
  setRequestMarkerHighlighted(null)

  if (!volunteer.is_available) {
    ElMessage.warning('该志愿者当前不是空闲状态，不能地图拖拽派单')
    resetVolunteerMarkerPosition(marker, volunteer)
    return
  }

  const dropPoint = getDropPointFromEvent(event, marker)
  if (!dropPoint) {
    ElMessage.warning('未能读取拖拽后的地图坐标，请重新拖动绿色“志”点')
    resetVolunteerMarkerPosition(marker, volunteer)
    return
  }

  const { target, nearest, blockedShelter } = resolveDispatchTarget(dropPoint)
  if (blockedShelter) {
    ElMessage.warning(`当前落点是避难点「${blockedShelter.name}」附近。避难点只能查看和开放，不能作为求助派单目标；请把绿色“志”点拖到红色“求”点或红色调度圈内。`)
    resetVolunteerMarkerPosition(marker, volunteer)
    return
  }

  if (!target) {
    const nearestText = nearest
      ? `最近的待处理求助 #${nearest.id} 距离约 ${formatDistance(nearest.distanceKm)}。`
      : '当前地图上没有带经纬度的待处理求助。'
    ElMessage.warning(`请把绿色“志”点拖到地图上的红色“求”点或红色圆形调度范围内。${nearestText}`)
    resetVolunteerMarkerPosition(marker, volunteer)
    return
  }

  await dispatchVolunteerToRequest(volunteer, target, marker)
}

const makeRequestMarker = (BMapGL, point, item) => {
  const color = statusMarkerColor(item.status)
  const marker = makeStaticMarker(BMapGL, point, '求', color, `
    <div style="line-height:1.8">
      <strong>${item.urgency_display} ${item.type_display}</strong><br/>
      状态：${item.status_display}${item.task_id ? `｜任务 #${item.task_id}${item.assigned_volunteer_name ? `｜已派：${item.assigned_volunteer_name}` : '｜未绑定志愿者'}` : ''}<br/>
      ${item.summary || item.description || '-'}<br/>
      ${item.address || '-'}
    </div>
  `)

  if (item.is_dispatchable) {
    requestMarkers.push({ marker, item, point })
    makeRequestDispatchCircle(BMapGL, point, item.id === highlightedRequestId.value)
  }

  return marker
}

const makeVolunteerMarker = (BMapGL, point, item) => {
  const color = item.is_available ? '#16a34a' : '#64748b'
  const marker = new BMapGL.Marker(point, {
    icon: createCircleIcon(BMapGL, '志', color)
  })

  marker.__originPoint = point

  marker.addEventListener('click', () => openInfoWindow(BMapGL, marker.getPosition ? marker.getPosition() : point, `
    <div style="line-height:1.8">
      <strong>${item.username}</strong><br/>
      ${item.is_available ? '空闲，可拖拽派单' : '忙碌，不可派单'}｜${item.phone || '-'}<br/>
      擅长：${item.skills || '-'}<br/>
      <span style="color:#64748b">提示：按住绿色“志”点，拖到红色“求”点或红色圆形调度范围内即可派单。</span>
    </div>
  `))

  if (item.is_available) {
    marker.enableDragging()
    marker.addEventListener('dragstart', () => {
      draggedVolunteer.value = item
      marker.__originPoint = createPointFromItem(item) || point
      ElMessage.info('请把绿色“志”点拖到地图上的红色“求”点或红色圆形调度范围内')
    })
    marker.addEventListener('dragging', () => handleVolunteerMarkerDragging(marker))
    marker.addEventListener('dragend', event => handleVolunteerMarkerDropped(item, event, marker))
  }

  volunteerMarkers.push({ marker, item })
  commandMap.addOverlay(marker)
  return marker
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
    requestDropCircles = []
    requestMarkers = []
    volunteerMarkers = []
    shelterMarkers = []
    const points = []

    const requests = showOnlyPending.value ? pendingRequests.value : helpRequests.value
    requests.forEach(item => {
      if (!item.longitude || !item.latitude) return
      const point = new BMapGL.Point(Number(item.longitude), Number(item.latitude))
      points.push(point)
      makeRequestMarker(BMapGL, point, item)
    })

    volunteers.value.forEach(item => {
      if (!item.longitude || !item.latitude) return
      const point = new BMapGL.Point(Number(item.longitude), Number(item.latitude))
      points.push(point)
      makeVolunteerMarker(BMapGL, point, item)
    })

    shelters.value.forEach(item => {
      if (!item.longitude || !item.latitude) return
      const point = new BMapGL.Point(Number(item.longitude), Number(item.latitude))
      points.push(point)
      const shelterMarker = makeStaticMarker(BMapGL, point, '避', '#2563eb', `
        <div style="line-height:1.8">
          <strong>${item.name}</strong><br/>
          类型：避难点资源，不是求助点<br/>
          ${item.is_available ? '已开放' : '未开放'}｜容量 ${item.capacity}<br/>
          ${item.address || '-'}<br/>
          <span style="color:#64748b">提示：蓝色“避”点只用于查看避难资源，不会触发志愿者派单。</span>
        </div>
      `)
      shelterMarkers.push({ marker: shelterMarker, item, point })
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

.request-meta.warning {
  color: #b45309;
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
