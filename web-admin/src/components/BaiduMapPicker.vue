<template>
  <div class="map-picker">
    <el-alert
      v-if="mapError"
      type="warning"
      show-icon
      :closable="false"
      :title="mapError"
      class="map-alert"
    />

    <div v-if="!readonly" class="map-toolbar">
      <el-input
        v-model="keyword"
        placeholder="输入地点关键词后点击定位，例如：阳光社区服务中心"
        clearable
        @keyup.enter="searchKeyword"
      />
      <el-button type="primary" @click="searchKeyword">定位</el-button>
    </div>

    <div :id="containerId" class="map-container"></div>

    <div class="coordinate-row">
      <span>纬度：{{ displayLatitude }}</span>
      <span>经度：{{ displayLongitude }}</span>
      <span v-if="!readonly" class="tip">可点击地图选择位置</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'

const props = defineProps({
  latitude: {
    type: [String, Number],
    default: ''
  },
  longitude: {
    type: [String, Number],
    default: ''
  },
  address: {
    type: String,
    default: ''
  },
  readonly: {
    type: Boolean,
    default: false
  },
  height: {
    type: String,
    default: '300px'
  }
})

const emit = defineEmits(['update:latitude', 'update:longitude', 'picked'])

const containerId = `baidu-map-picker-${Math.random().toString(36).slice(2)}`
const keyword = ref(props.address || '')
const mapError = ref('')

let map = null
let marker = null

const displayLatitude = computed(() => props.latitude || '-')
const displayLongitude = computed(() => props.longitude || '-')

const loadBaiduMapScript = () => {
  if (window.BMapGL) {
    return Promise.resolve(window.BMapGL)
  }

  if (window.__baiduMapGLPromise) {
    return window.__baiduMapGLPromise
  }

  const ak = import.meta.env.VITE_BAIDU_MAP_AK
  if (!ak) {
    return Promise.reject(new Error('未配置 VITE_BAIDU_MAP_AK，地图选择器无法加载'))
  }

  window.__baiduMapGLPromise = new Promise((resolve, reject) => {
    const callbackName = '__onBaiduMapPickerLoaded'
    window[callbackName] = () => {
      if (window.BMapGL) {
        resolve(window.BMapGL)
      } else {
        reject(new Error('百度地图脚本已加载，但 BMapGL 不存在'))
      }
      delete window[callbackName]
    }

    const script = document.createElement('script')
    script.src = `https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${ak}&callback=${callbackName}`
    script.onerror = () => reject(new Error('百度地图脚本加载失败，请检查 AK、Referer 白名单或网络'))
    document.head.appendChild(script)
  })

  return window.__baiduMapGLPromise
}

const getPoint = BMapGL => {
  if (props.longitude && props.latitude) {
    return new BMapGL.Point(Number(props.longitude), Number(props.latitude))
  }
  return new BMapGL.Point(116.404, 39.915)
}

const setMarker = (BMapGL, point, shouldEmit = false) => {
  if (!map) return

  if (!marker) {
    marker = new BMapGL.Marker(point)
    map.addOverlay(marker)
  } else {
    marker.setPosition(point)
  }

  map.panTo(point)

  if (shouldEmit) {
    const longitude = Number(point.lng).toFixed(7)
    const latitude = Number(point.lat).toFixed(7)
    emit('update:longitude', longitude)
    emit('update:latitude', latitude)
    emit('picked', { longitude, latitude })
  }
}

const initMap = async () => {
  try {
    mapError.value = ''
    const BMapGL = await loadBaiduMapScript()
    await nextTick()

    const el = document.getElementById(containerId)
    if (!el || map) return

    map = new BMapGL.Map(containerId)
    const point = getPoint(BMapGL)
    map.centerAndZoom(point, props.longitude && props.latitude ? 15 : 12)
    map.enableScrollWheelZoom(true)
    map.addControl(new BMapGL.ScaleControl())
    map.addControl(new BMapGL.ZoomControl())
    setMarker(BMapGL, point, false)

    if (!props.readonly) {
      map.addEventListener('click', event => {
        setMarker(BMapGL, event.latlng, true)
      })
    }
  } catch (error) {
    mapError.value = error.message || '地图加载失败'
  }
}

const searchKeyword = async () => {
  if (!keyword.value || !map) return

  try {
    const BMapGL = await loadBaiduMapScript()
    const local = new BMapGL.LocalSearch(map, {
      onSearchComplete: results => {
        const poi = results?.getPoi?.(0)
        if (poi?.point) {
          map.centerAndZoom(poi.point, 16)
          setMarker(BMapGL, poi.point, true)
        } else {
          mapError.value = '未搜索到该地点，请换一个关键词或直接点击地图选点'
        }
      }
    })
    local.search(keyword.value)
  } catch (error) {
    mapError.value = error.message || '地点搜索失败'
  }
}

watch(
  () => [props.latitude, props.longitude],
  async () => {
    if (!map || !props.longitude || !props.latitude) return
    const BMapGL = await loadBaiduMapScript()
    setMarker(BMapGL, new BMapGL.Point(Number(props.longitude), Number(props.latitude)), false)
  }
)

onMounted(() => {
  initMap()
})
</script>

<style scoped>
.map-picker {
  width: 100%;
}

.map-alert {
  margin-bottom: 10px;
}

.map-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.map-container {
  width: 100%;
  height: v-bind(height);
  border-radius: 12px;
  overflow: hidden;
  background: #eef2ff;
}

.coordinate-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #64748b;
  font-size: 13px;
}

.tip {
  color: #2563eb;
}
</style>
