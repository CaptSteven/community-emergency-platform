<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">🗺️ 单次任务地图</div>
        <div class="page-subtitle">
          一图管理居民的单次求助：红标为待派单任务，蓝标为可调度志愿者。
          点选任务后按“距离由近到远”推荐志愿者，也可直接拖动蓝标到红标上完成派单。
        </div>
      </div>
      <el-button :loading="loading" @click="loadAll">刷新</el-button>
    </div>

    <!-- 地图不可用时的降级提示 -->
    <el-alert
      v-if="mapError"
      type="warning"
      show-icon
      :closable="false"
      class="mode-alert"
      :title="`${mapError}，已切换为「列表派单」模式，功能不受影响。`"
    />

    <div class="layout" :class="{ 'list-only': !mapUsable }">
      <!-- 左侧：百度地图 -->
      <div v-show="mapUsable" class="card map-card">
        <div class="card-title">
          服务地图
          <div class="legend">
            <span class="legend-item"><i class="dot dot-task"></i>待派单任务</span>
            <span class="legend-item"><i class="dot dot-vol"></i>可调度志愿者</span>
            <span class="legend-item"><i class="dot dot-active"></i>当前选中</span>
          </div>
        </div>
        <div :id="mapContainerId" class="map-container"></div>
      </div>

      <!-- 右侧：待派单列表 + 志愿者推荐 -->
      <div class="card right-card">
        <div class="card-title">
          待派单单次任务
          <el-tag type="danger" effect="dark" size="small" round>{{ tasks.length }}</el-tag>
        </div>

        <div v-if="tasks.length" class="task-list">
          <div
            v-for="t in tasks"
            :key="t.id"
            class="task-item"
            :class="{ active: selectedTask && selectedTask.id === t.id }"
            @click="selectTask(t)"
          >
            <div class="task-icon">{{ t.service_type_icon || '🛎️' }}</div>
            <div class="task-body">
              <div class="task-name">{{ t.service_type_name }} · {{ t.resident_name }}</div>
              <div class="task-addr">{{ t.address || t.note || '未填写地址' }}</div>
              <div class="task-tags">
                <el-tag size="small" effect="plain" round>{{ t.scheduled_date || '不限日期' }}</el-tag>
                <el-tag
                  v-if="hasCoord(t)"
                  size="small"
                  type="success"
                  effect="plain"
                  round
                >📍 已定位</el-tag>
                <el-tag v-else size="small" type="info" effect="plain" round>无坐标</el-tag>
              </div>
            </div>
            <el-button
              class="detail-btn"
              size="small"
              text
              type="primary"
              @click.stop="openTaskDetail(t)"
            >详情</el-button>
          </div>
        </div>
        <div v-else class="empty-state">
          <div class="empty-emoji">🎉</div>
          <div class="empty-title">暂无待派单的单次任务</div>
          <div class="empty-tip">居民在 App 发起单次求助后会出现在这里</div>
        </div>

        <!-- 选中任务后的志愿者推荐 -->
        <div v-if="selectedTask" class="vol-panel">
          <div class="card-title">
            推荐志愿者（就近优先）
          </div>
          <div v-if="!hasCoord(selectedTask)" class="coord-warn">
            ⚠️ 该任务无坐标，无法按距离排序，可直接选择志愿者分配。
          </div>
          <div v-if="sortedVolunteers.length" class="vol-list">
            <div v-for="v in sortedVolunteers" :key="v.id" class="vol-item clickable" @click="openVolDetail(v)">
              <div class="vol-avatar">{{ (v.username || '?').slice(0, 1) }}</div>
              <div class="vol-body">
                <div class="vol-name">
                  {{ v.username }}
                  <span class="vol-points">🏅 {{ v.points || 0 }}</span>
                </div>
                <div class="vol-meta">
                  <span class="vol-skill">{{ v.skills || '无技能标签' }}</span>
                  <span v-if="v._distance != null" class="vol-dist">📏 {{ formatDistance(v._distance) }}</span>
                  <span v-else class="vol-dist muted">无坐标</span>
                </div>
              </div>
              <el-button
                type="primary"
                size="small"
                :loading="assigningId === v.id"
                @click.stop="assign(v)"
              >分配</el-button>
            </div>
          </div>
          <div v-else class="empty-state small">
            <div class="empty-emoji">🙋</div>
            <div class="empty-title">暂无可调度志愿者</div>
            <div class="empty-tip">请先在「用户管理」中开通志愿者账号</div>
          </div>
        </div>
        <div v-else-if="tasks.length" class="pick-tip">
          👈 点击左侧任务，查看就近志愿者并派单
        </div>
      </div>
    </div>

    <!-- 任务详情（点击地图红标 / 列表项打开） -->
    <el-dialog v-model="taskDetailVisible" title="任务详情" width="460px">
      <el-descriptions v-if="detailTask" :column="1" border>
        <el-descriptions-item label="服务类型">{{ detailTask.service_type_icon }} {{ detailTask.service_type_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag type="danger" effect="dark" size="small">{{ detailTask.status_display }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="受益居民">{{ detailTask.resident_name }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ residentInfo?.phone || '—' }}</el-descriptions-item>
        <el-descriptions-item label="所在社区">{{ residentInfo?.community || '—' }}</el-descriptions-item>
        <el-descriptions-item label="期望日期">{{ detailTask.scheduled_date || '不限' }}</el-descriptions-item>
        <el-descriptions-item label="上门地址">{{ detailTask.address || '—' }}</el-descriptions-item>
        <el-descriptions-item label="需求说明">{{ detailTask.note || '—' }}</el-descriptions-item>
        <el-descriptions-item label="定位">
          <span v-if="hasCoord(detailTask)">📍 {{ num(detailTask.latitude).toFixed(5) }}, {{ num(detailTask.longitude).toFixed(5) }}</span>
          <span v-else class="muted">无坐标</span>
        </el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ formatTime(detailTask.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="taskDetailVisible = false">关闭</el-button>
        <el-button type="primary" @click="taskDetailVisible = false">按就近推荐派单 →</el-button>
      </template>
    </el-dialog>

    <!-- 志愿者详情（点击地图蓝标 / 推荐列表项打开） -->
    <el-dialog v-model="volDetailVisible" title="志愿者详情" width="460px">
      <el-descriptions v-if="detailVol" :column="1" border>
        <el-descriptions-item label="用户名">
          {{ detailVol.username }}
          <el-tag v-if="detailVol.is_verified" type="success" size="small" effect="dark" style="margin-left:8px">已认证</el-tag>
          <el-tag v-else type="info" size="small" effect="plain" style="margin-left:8px">未认证</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ detailVol.phone || '—' }}</el-descriptions-item>
        <el-descriptions-item label="所在社区">{{ detailVol.community || '—' }}</el-descriptions-item>
        <el-descriptions-item label="技能标签">{{ detailVol.skills || '无技能标签' }}</el-descriptions-item>
        <el-descriptions-item label="志愿积分">🏅 {{ detailVol.points || 0 }}</el-descriptions-item>
        <el-descriptions-item label="在办工单">
          <span v-if="volLoad != null">{{ volLoad }} 单（已排班/服务中）</span>
          <span v-else class="muted">统计中…</span>
        </el-descriptions-item>
        <el-descriptions-item label="本月取消">{{ detailVol.monthly_cancel_count ?? 0 }} 次</el-descriptions-item>
        <el-descriptions-item label="距选中任务">
          <span v-if="selectedTask && volDetailDistance != null" class="vol-dist">📏 {{ formatDistance(volDetailDistance) }}</span>
          <span v-else class="muted">{{ selectedTask ? '任一方无坐标' : '未选中任务' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="位置更新">{{ formatTime(detailVol.location_updated_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="volDetailVisible = false">关闭</el-button>
        <el-button
          v-if="selectedTask && detailVol"
          type="primary"
          :loading="assigningId === detailVol.id"
          @click="assignFromDetail"
        >分配给「{{ selectedTask.service_type_name }} · {{ selectedTask.resident_name }}」</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'
import { unwrapPaginated } from '../utils/pagination'

const mapContainerId = `single-task-map-${Math.random().toString(36).slice(2)}`

const loading = ref(false)
const assigningId = ref(null)
const tasks = ref([]) // 待派单单次任务（volunteer 为空 且 status=assigned）
const volunteers = ref([]) // 全部志愿者
const selectedTask = ref(null)
const mapError = ref('')

let map = null
let BMap = null
const taskMarkers = new Map() // taskId -> marker
const volunteerMarkers = new Map() // volunteerId -> marker

// 地图是否可用（无报错即视为可用；报错则降级为纯列表）
const mapUsable = computed(() => !mapError.value)

// —— 工具：坐标 / 距离 ——
const num = v => {
  const n = Number(v)
  return Number.isFinite(n) && n !== 0 ? n : null
}
const hasCoord = obj => num(obj?.latitude) != null && num(obj?.longitude) != null
const hasVolCoord = v => num(v?.current_latitude) != null && num(v?.current_longitude) != null

// Haversine 距离（公里）
const haversine = (lat1, lng1, lat2, lng2) => {
  const R = 6371
  const toRad = d => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

const formatDistance = km => {
  if (km == null) return '—'
  return km < 1 ? `${Math.round(km * 1000)} 米` : `${km.toFixed(1)} 公里`
}

// 选中任务后，志愿者按距离由近到远排序（无坐标者置后）
const sortedVolunteers = computed(() => {
  const t = selectedTask.value
  const withDist = volunteers.value.map(v => {
    let dist = null
    if (t && hasCoord(t) && hasVolCoord(v)) {
      dist = haversine(num(t.latitude), num(t.longitude), num(v.current_latitude), num(v.current_longitude))
    }
    return { ...v, _distance: dist }
  })
  return withDist.sort((a, b) => {
    if (a._distance == null && b._distance == null) return 0
    if (a._distance == null) return 1
    if (b._distance == null) return -1
    return a._distance - b._distance
  })
})

// —— 数据加载 ——
const loadTasks = async () => {
  const data = await request.get('/service-visits/', { params: { kind: 'single', status: 'assigned', page_size: 200 } })
  const list = unwrapPaginated(data).list
  // 仅保留“未指派志愿者”的待派单任务
  tasks.value = list.filter(t => !t.volunteer)
}

const loadVolunteers = async () => {
  const data = await request.get('/users/', { params: { role: 'volunteer', page_size: 200 } })
  volunteers.value = unwrapPaginated(data).list
}

const loadAll = async () => {
  loading.value = true
  try {
    await Promise.all([loadTasks(), loadVolunteers()])
    // 选中项可能已被派单，做一次校准
    if (selectedTask.value) {
      const still = tasks.value.find(t => t.id === selectedTask.value.id)
      selectedTask.value = still || null
    }
    renderMarkers()
  } catch (e) {
    /* 拦截器提示 */
  } finally {
    loading.value = false
  }
}

const selectTask = t => {
  selectedTask.value = t
  renderMarkers()
  if (map && hasCoord(t)) {
    map.panTo(new BMap.Point(num(t.longitude), num(t.latitude)))
  }
}

// —— 详情弹窗（点击地图标注 / 列表项查看） ——
const taskDetailVisible = ref(false)
const volDetailVisible = ref(false)
const detailTask = ref(null)
const detailVol = ref(null)
const residentInfo = ref(null) // 任务详情补充：居民联系方式
const volLoad = ref(null) // 志愿者详情补充：在办工单数

const formatTime = v => (v ? String(v).replace('T', ' ').slice(0, 19) : '—')

// 点击任务红标：选中（保持派单流程）并打开详情，异步补居民联系方式
const openTaskDetail = async t => {
  selectTask(t)
  detailTask.value = t
  residentInfo.value = null
  taskDetailVisible.value = true
  try {
    residentInfo.value = await request.get(`/users/${t.resident}/`)
  } catch (e) { /* 联系方式拿不到就显示 — */ }
}

// 点击志愿者蓝标：打开详情，异步统计在办工单（已排班+服务中）
const openVolDetail = async v => {
  detailVol.value = v
  volLoad.value = null
  volDetailVisible.value = true
  try {
    const [a, p] = await Promise.all([
      request.get('/service-visits/', { params: { volunteer: v.id, status: 'assigned', page_size: 1 } }),
      request.get('/service-visits/', { params: { volunteer: v.id, status: 'processing', page_size: 1 } })
    ])
    volLoad.value = unwrapPaginated(a).total + unwrapPaginated(p).total
  } catch (e) { volLoad.value = null }
}

// 志愿者详情里与「当前选中任务」的直线距离
const volDetailDistance = computed(() => {
  const t = selectedTask.value
  const v = detailVol.value
  if (!t || !v || !hasCoord(t) || !hasVolCoord(v)) return null
  return haversine(num(t.latitude), num(t.longitude), num(v.current_latitude), num(v.current_longitude))
})

// 详情弹窗内直接派单给选中任务
const assignFromDetail = async () => {
  if (!detailVol.value) return
  await assign(detailVol.value)
  volDetailVisible.value = false
}

// —— 派单 ——
const assign = async v => {
  if (!selectedTask.value) return
  assigningId.value = v.id
  try {
    await request.post(`/service-visits/${selectedTask.value.id}/reassign/`, { volunteer_id: v.id })
    ElMessage.success(`已将「${selectedTask.value.service_type_name}」派给 ${v.username}`)
    selectedTask.value = null
    await loadAll()
  } catch (e) {
    /* 拦截器提示 */
  } finally {
    assigningId.value = null
  }
}

// 拖动志愿者蓝标到任务上派单：确认后调用 assign
const assignByDrag = async (volunteer, task, distanceKm) => {
  try {
    await ElMessageBox.confirm(
      `将「${task.service_type_name} · ${task.resident_name}」派给志愿者 ${volunteer.username}？（距离约 ${formatDistance(distanceKm)}）`,
      '拖拽派单',
      { type: 'warning', confirmButtonText: '确认派单' }
    )
  } catch (e) {
    renderMarkers() // 取消则复位标注
    return
  }
  selectedTask.value = task
  await assign(volunteer)
}

// —— 百度地图 ——
const loadBaiduMapScript = () => {
  if (window.BMapGL) return Promise.resolve(window.BMapGL)
  if (window.__baiduMapGLPromise) return window.__baiduMapGLPromise

  const ak = import.meta.env.VITE_BAIDU_MAP_AK
  if (!ak) return Promise.reject(new Error('未配置百度地图 AK'))

  window.__baiduMapGLPromise = new Promise((resolve, reject) => {
    const callbackName = '__onBaiduMapGLLoaded'
    window[callbackName] = () => {
      window.BMapGL ? resolve(window.BMapGL) : reject(new Error('百度地图脚本加载异常'))
      delete window[callbackName]
    }
    const script = document.createElement('script')
    script.src = `https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${ak}&callback=${callbackName}`
    script.onerror = () => reject(new Error('百度地图脚本加载失败'))
    document.head.appendChild(script)
  })
  return window.__baiduMapGLPromise
}

// 生成水滴形图钉图标
const makePinIcon = color => {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="40" viewBox="0 0 28 36">` +
    `<path d="M14 0C6.3 0 0 6.3 0 14c0 9.5 14 22 14 22s14-12.5 14-22C28 6.3 21.7 0 14 0z" fill="${color}"/>` +
    `<circle cx="14" cy="14" r="6" fill="#fff"/></svg>`
  const url = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg)
  return new BMap.Icon(url, new BMap.Size(30, 40), { anchor: new BMap.Size(15, 40) })
}

const clearMarkers = () => {
  if (!map) return
  taskMarkers.forEach(m => map.removeOverlay(m))
  volunteerMarkers.forEach(m => map.removeOverlay(m))
  taskMarkers.clear()
  volunteerMarkers.clear()
}

const renderMarkers = () => {
  if (!map || !BMap) return
  clearMarkers()

  const bounds = []

  // 任务红标（选中为琥珀色）
  tasks.value.filter(hasCoord).forEach(t => {
    const point = new BMap.Point(num(t.longitude), num(t.latitude))
    const active = selectedTask.value && selectedTask.value.id === t.id
    const marker = new BMap.Marker(point, { icon: makePinIcon(active ? '#F59E0B' : '#EF4444') })
    marker.addEventListener('click', () => openTaskDetail(t))
    map.addOverlay(marker)
    const label = new BMap.Label(t.service_type_name, { offset: new BMap.Size(14, -6) })
    label.setStyle({ border: 'none', background: 'rgba(15,23,42,.75)', color: '#fff', padding: '1px 6px', borderRadius: '6px', fontSize: '12px' })
    marker.setLabel(label)
    taskMarkers.set(t.id, marker)
    bounds.push(point)
  })

  // 志愿者蓝标（可拖动）
  volunteers.value.filter(hasVolCoord).forEach(v => {
    const point = new BMap.Point(num(v.current_longitude), num(v.current_latitude))
    const marker = new BMap.Marker(point, { icon: makePinIcon('#2563EB'), enableDragging: true })
    const label = new BMap.Label(v.username, { offset: new BMap.Size(14, -6) })
    label.setStyle({ border: 'none', background: 'rgba(37,99,235,.85)', color: '#fff', padding: '1px 6px', borderRadius: '6px', fontSize: '12px' })
    marker.setLabel(label)

    // 点击蓝标查看志愿者详情（拖动派单不受影响）
    marker.addEventListener('click', () => openVolDetail(v))

    // 拖动结束：找最近的任务红标，落在 200 米内则确认派单
    marker.addEventListener('dragend', e => {
      const pos = e?.latlng || marker.getPosition()
      const withCoord = tasks.value.filter(hasCoord)
      if (!withCoord.length) {
        ElMessage.info('当前没有带坐标的任务，无法拖拽派单')
        renderMarkers()
        return
      }
      let nearest = null
      let best = Infinity
      withCoord.forEach(t => {
        const d = haversine(pos.lat, pos.lng, num(t.latitude), num(t.longitude))
        if (d < best) { best = d; nearest = t }
      })
      if (nearest && best <= 0.2) {
        assignByDrag(v, nearest, best)
      } else {
        ElMessage.warning('请把志愿者拖到任务红标附近（200 米内）再松手')
        renderMarkers()
      }
    })

    map.addOverlay(marker)
    volunteerMarkers.set(v.id, marker)
    bounds.push(point)
  })

  // 自动缩放到所有点
  if (bounds.length) {
    try { map.setViewport(bounds, { margins: [40, 40, 40, 40] }) } catch (e) { /* ignore */ }
  }
}

const initMap = async () => {
  try {
    BMap = await loadBaiduMapScript()
    const el = document.getElementById(mapContainerId)
    if (!el) return
    map = new BMap.Map(mapContainerId)
    map.centerAndZoom(new BMap.Point(116.404, 39.915), 12)
    map.enableScrollWheelZoom(true)
    map.addControl(new BMap.ScaleControl())
    map.addControl(new BMap.ZoomControl())
    renderMarkers()
  } catch (error) {
    // 无 AK 或加载失败 → 降级为纯列表，不白屏
    mapError.value = error.message || '地图加载失败'
  }
}

onMounted(async () => {
  await loadAll()
  await initMap()
})

onBeforeUnmount(() => {
  clearMarkers()
  map = null
})
</script>

<style scoped>
.page-container { padding: 20px; }
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 16px;
}
.page-title { font-size: 22px; font-weight: 700; color: #1e293b; }
.page-subtitle { margin-top: 6px; font-size: 13px; color: #64748b; max-width: 720px; line-height: 1.6; }
.mode-alert { margin-bottom: 16px; border-radius: 12px; }

.layout { display: flex; gap: 16px; align-items: stretch; }
.layout.list-only .right-card { flex: 1; }

.card {
  background: #fff; border-radius: 16px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, .06);
  border: 1px solid rgba(226, 232, 240, .7);
  padding: 16px;
}
.card-title {
  display: flex; align-items: center; gap: 10px;
  font-size: 16px; font-weight: 700; color: #1e293b;
  margin-bottom: 14px;
}

/* 左侧地图 */
.map-card { flex: 1.4; min-width: 0; display: flex; flex-direction: column; }
.map-container {
  flex: 1; width: 100%; min-height: 560px;
  border-radius: 12px; overflow: hidden; background: #eef2ff;
}
.legend { display: flex; gap: 14px; margin-left: auto; font-weight: 400; font-size: 12px; color: #64748b; }
.legend-item { display: inline-flex; align-items: center; gap: 5px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot-task { background: #EF4444; }
.dot-vol { background: #2563EB; }
.dot-active { background: #F59E0B; }

/* 右侧列表 */
.right-card { width: 420px; flex-shrink: 0; display: flex; flex-direction: column; max-height: 640px; overflow-y: auto; }
.task-list { display: flex; flex-direction: column; gap: 10px; }
.task-item {
  display: flex; gap: 12px; padding: 12px;
  border: 1px solid #e5e7eb; border-radius: 12px;
  cursor: pointer; transition: all .18s ease;
}
.task-item:hover { border-color: #93c5fd; background: #f8fafc; transform: translateY(-1px); }
.task-item.active { border-color: #2563EB; background: #eff6ff; box-shadow: 0 4px 14px rgba(37, 99, 235, .12); }
.task-icon {
  font-size: 22px; width: 42px; height: 42px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: #fef2f2; border-radius: 10px;
}
.task-body { min-width: 0; flex: 1; }
.task-name { font-size: 15px; font-weight: 600; color: #1e293b; }
.task-addr {
  margin-top: 3px; font-size: 13px; color: #64748b;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.task-tags { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
.detail-btn { flex-shrink: 0; align-self: flex-start; }
.vol-item.clickable { cursor: pointer; transition: all .18s ease; }
.vol-item.clickable:hover { border-color: #93c5fd; background: #eff6ff; }

/* 志愿者推荐 */
.vol-panel { margin-top: 18px; padding-top: 16px; border-top: 1px dashed #e5e7eb; }
.coord-warn {
  margin-bottom: 12px; padding: 8px 12px; border-radius: 10px;
  background: #fffbeb; color: #b45309; font-size: 13px;
}
.vol-list { display: flex; flex-direction: column; gap: 10px; }
.vol-item {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px;
  border: 1px solid #eef2f7; border-radius: 12px; background: #fafcff;
}
.vol-avatar {
  width: 38px; height: 38px; flex-shrink: 0; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  color: #fff; font-weight: 700; font-size: 16px;
}
.vol-body { flex: 1; min-width: 0; }
.vol-name { font-size: 15px; font-weight: 600; color: #1e293b; display: flex; align-items: center; gap: 8px; }
.vol-points { font-size: 12px; font-weight: 700; color: #b45309; background: #fef3c7; padding: 1px 8px; border-radius: 8px; }
.vol-meta { margin-top: 4px; display: flex; gap: 12px; font-size: 12px; color: #64748b; }
.vol-skill { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 160px; }
.vol-dist { color: #16a34a; font-weight: 600; }
.muted { color: #94a3b8; font-weight: 400; }

.pick-tip {
  margin-top: 18px; padding: 20px; text-align: center;
  color: #64748b; font-size: 14px; background: #f8fafc; border-radius: 12px;
}

/* 空状态 */
.empty-state { padding: 34px 0; text-align: center; }
.empty-state.small { padding: 20px 0; }
.empty-emoji { font-size: 44px; }
.empty-title { margin-top: 10px; font-size: 15px; font-weight: 600; color: #475569; }
.empty-tip { margin-top: 6px; font-size: 13px; color: #94a3b8; }
</style>
