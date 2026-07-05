<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">应急资源管理</div>
        <div class="page-subtitle">管理避难点、物资库存和物资保质期，为灾害预警和居民求助提供资源支撑。</div>
      </div>
      <el-button type="primary" @click="refreshAll">刷新数据</el-button>
    </div>

    <el-row :gutter="18" class="summary-row">
      <el-col :span="6"><div class="summary-card"><div class="summary-label">避难点总数</div><div class="summary-value">{{ shelterPagination.total }}</div><div class="summary-desc">社区登记避难点数量</div></div></el-col>
      <el-col :span="6"><div class="summary-card success"><div class="summary-label">本页可用避难点</div><div class="summary-value">{{ availableShelterCount }}</div><div class="summary-desc">当前页可对外开放</div></div></el-col>
      <el-col :span="6"><div class="summary-card"><div class="summary-label">物资种类</div><div class="summary-value">{{ materialPagination.total }}</div><div class="summary-desc">应急物资登记种类</div></div></el-col>
      <el-col :span="6"><div class="summary-card danger"><div class="summary-label">本页库存/临期风险</div><div class="summary-value">{{ materialRiskCount }}</div><div class="summary-desc">低库存、临期或已过期</div></div></el-col>
    </el-row>

    <div class="card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="避难点管理" name="shelter">
          <div class="tab-toolbar">
            <div class="search-area">
              <el-input v-model="shelterFilters.search" placeholder="搜索避难点名称、地址或电话" clearable style="width: 260px" @keyup.enter="searchShelters" />
              <el-select v-model="shelterFilters.is_available" placeholder="全部状态" clearable style="width: 160px">
                <el-option label="可用" value="true" />
                <el-option label="不可用" value="false" />
              </el-select>
              <el-button type="primary" @click="searchShelters">查询</el-button>
              <el-button @click="resetShelterFilters">重置</el-button>
            </div>
            <el-button type="primary" @click="openShelterCreateDialog">新增避难点</el-button>
          </div>

          <el-table v-loading="shelterLoading" :data="shelters" border style="width: 100%">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="name" label="避难点名称" min-width="160" />
            <el-table-column prop="address" label="地址" min-width="220" show-overflow-tooltip />
            <el-table-column prop="capacity" label="容量" width="100" />
            <el-table-column prop="contact_phone" label="联系电话" width="140" />
            <el-table-column label="地图坐标" width="190"><template #default="{ row }">{{ row.latitude || '-' }}，{{ row.longitude || '-' }}</template></el-table-column>
            <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.is_available ? 'success' : 'info'">{{ row.is_available ? '可用' : '不可用' }}</el-tag></template></el-table-column>
            <el-table-column label="创建时间" width="180"><template #default="{ row }">{{ formatTime(row.created_at) }}</template></el-table-column>
            <el-table-column label="操作" width="210" fixed="right"><template #default="{ row }"><el-button size="small" @click="openShelterDetail(row)">地图</el-button><el-button size="small" type="primary" @click="openShelterEditDialog(row)">编辑</el-button><el-button size="small" type="danger" @click="deleteShelter(row)">删除</el-button></template></el-table-column>
          </el-table>

          <el-pagination class="pagination" background layout="total, sizes, prev, pager, next, jumper" :total="shelterPagination.total" :current-page="shelterPagination.page" :page-size="shelterPagination.pageSize" :page-sizes="[10,20,50]" @size-change="changeShelterSize" @current-change="changeShelterPage" />
        </el-tab-pane>

        <el-tab-pane label="应急物资管理" name="material">
          <div class="tab-toolbar">
            <div class="search-area">
              <el-input v-model="materialFilters.search" placeholder="搜索物资名称、类别或存放位置" clearable style="width: 260px" @keyup.enter="searchMaterials" />
              <el-select v-model="materialFilters.stock_status" placeholder="库存状态" clearable style="width: 150px">
                <el-option label="库存正常" value="normal" />
                <el-option label="低库存" value="low" />
              </el-select>
              <el-select v-model="materialFilters.expiry_status" placeholder="保质期状态" clearable style="width: 160px">
                <el-option label="正常" value="normal" />
                <el-option label="临期" value="soon" />
                <el-option label="已过期" value="expired" />
              </el-select>
              <el-button type="primary" @click="searchMaterials">查询</el-button>
              <el-button @click="resetMaterialFilters">重置</el-button>
            </div>
            <el-button type="primary" @click="openMaterialCreateDialog">新增物资</el-button>
          </div>

          <el-table v-loading="materialLoading" :data="materials" border style="width: 100%">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="name" label="物资名称" min-width="150" />
            <el-table-column prop="category" label="类别" width="120" />
            <el-table-column label="库存数量" width="120"><template #default="{ row }"><span :class="{ 'danger-text': row.is_low_stock }">{{ row.quantity }} {{ row.unit }}</span></template></el-table-column>
            <el-table-column label="预警阈值" width="120"><template #default="{ row }">{{ row.warning_quantity }} {{ row.unit }}</template></el-table-column>
            <el-table-column prop="storage_location" label="存放位置" min-width="170" show-overflow-tooltip />
            <el-table-column label="库存状态" width="110"><template #default="{ row }"><el-tag :type="row.is_low_stock ? 'danger' : 'success'">{{ row.is_low_stock ? '低库存' : '正常' }}</el-tag></template></el-table-column>
            <el-table-column label="保质期" width="180"><template #default="{ row }"><div>{{ row.expire_date || '未登记' }}</div><div class="tiny-text">{{ expiryText(row) }}</div></template></el-table-column>
            <el-table-column label="生命周期" width="110"><template #default="{ row }"><el-tag :type="lifecycleTagType(row)">{{ row.lifecycle_status }}</el-tag></template></el-table-column>
            <el-table-column label="更新时间" width="180"><template #default="{ row }">{{ formatTime(row.updated_at) }}</template></el-table-column>
            <el-table-column label="操作" width="190" fixed="right"><template #default="{ row }"><el-button size="small" type="primary" @click="openMaterialEditDialog(row)">编辑</el-button><el-button size="small" type="danger" @click="deleteMaterial(row)">删除</el-button></template></el-table-column>
          </el-table>

          <el-pagination class="pagination" background layout="total, sizes, prev, pager, next, jumper" :total="materialPagination.total" :current-page="materialPagination.page" :page-size="materialPagination.pageSize" :page-sizes="[10,20,50]" @size-change="changeMaterialSize" @current-change="changeMaterialPage" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="shelterFormVisible" :title="shelterIsEdit ? '编辑避难点' : '新增避难点'" width="760px">
      <el-form ref="shelterFormRef" :model="shelterForm" :rules="shelterRules" label-position="top">
        <el-form-item label="避难点名称" prop="name"><el-input v-model="shelterForm.name" maxlength="100" show-word-limit placeholder="例如：阳光社区服务中心" /></el-form-item>
        <el-form-item label="地址" prop="address"><el-input v-model="shelterForm.address" maxlength="255" show-word-limit placeholder="请输入详细地址" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="容量" prop="capacity"><el-input-number v-model="shelterForm.capacity" :min="1" :max="100000" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系电话" prop="contact_phone"><el-input v-model="shelterForm.contact_phone" placeholder="例如：13800000000" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="地图选点" prop="longitude">
          <BaiduMapPicker v-if="shelterFormVisible" v-model:latitude="shelterForm.latitude" v-model:longitude="shelterForm.longitude" :address="shelterForm.address" height="320px" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="纬度" prop="latitude"><el-input v-model="shelterForm.latitude" placeholder="点击地图自动填充" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="经度" prop="longitude"><el-input v-model="shelterForm.longitude" placeholder="点击地图自动填充" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="是否可用"><el-switch v-model="shelterForm.is_available" active-text="可用" inactive-text="不可用" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="shelterFormVisible = false">取消</el-button><el-button type="primary" :loading="shelterSubmitLoading" @click="submitShelterForm">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="shelterDetailVisible" title="避难点地图位置" width="760px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="避难点名称">{{ currentShelter?.name }}</el-descriptions-item>
        <el-descriptions-item label="地址">{{ currentShelter?.address }}</el-descriptions-item>
        <el-descriptions-item label="容量">{{ currentShelter?.capacity }}</el-descriptions-item>
      </el-descriptions>
      <div class="detail-map-title">地图位置</div>
      <BaiduMapPicker v-if="shelterDetailVisible" :latitude="currentShelter?.latitude" :longitude="currentShelter?.longitude" :address="currentShelter?.address" readonly height="320px" />
    </el-dialog>

    <el-dialog v-model="materialFormVisible" :title="materialIsEdit ? '编辑应急物资' : '新增应急物资'" width="680px">
      <el-form ref="materialFormRef" :model="materialForm" :rules="materialRules" label-position="top">
        <el-form-item label="物资名称" prop="name"><el-input v-model="materialForm.name" maxlength="100" show-word-limit placeholder="例如：矿泉水、应急药箱、手电筒" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="物资类别" prop="category"><el-input v-model="materialForm.category" placeholder="例如：饮用水、药品、食品" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="单位" prop="unit"><el-input v-model="materialForm.unit" placeholder="例如：箱、件、盒" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="库存数量" prop="quantity"><el-input-number v-model="materialForm.quantity" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="库存预警阈值" prop="warning_quantity"><el-input-number v-model="materialForm.warning_quantity" :min="0" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="存放位置" prop="storage_location"><el-input v-model="materialForm.storage_location" placeholder="例如：社区仓库 A 区" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="生产日期"><el-date-picker v-model="materialForm.production_date" type="date" value-format="YYYY-MM-DD" style="width:100%" placeholder="选择日期" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="过期日期" prop="expire_date"><el-date-picker v-model="materialForm.expire_date" type="date" value-format="YYYY-MM-DD" style="width:100%" placeholder="选择日期" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="临期预警天数" prop="expiry_warning_days"><el-input-number v-model="materialForm.expiry_warning_days" :min="0" :max="3650" style="width:100%" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="materialFormVisible = false">取消</el-button><el-button type="primary" :loading="materialSubmitLoading" @click="submitMaterialForm">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'
import { buildPageParams, unwrapPaginated } from '../utils/pagination'
import BaiduMapPicker from '../components/BaiduMapPicker.vue'

const activeTab = ref('shelter')
const shelterLoading = ref(false)
const materialLoading = ref(false)
const shelterSubmitLoading = ref(false)
const materialSubmitLoading = ref(false)
const shelters = ref([])
const materials = ref([])
const shelterFormVisible = ref(false)
const materialFormVisible = ref(false)
const shelterDetailVisible = ref(false)
const shelterIsEdit = ref(false)
const materialIsEdit = ref(false)
const shelterFormRef = ref(null)
const materialFormRef = ref(null)
const currentShelter = ref(null)

const shelterFilters = reactive({ search: '', is_available: '' })
const materialFilters = reactive({ search: '', stock_status: '', expiry_status: '' })
const shelterPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const materialPagination = reactive({ page: 1, pageSize: 10, total: 0 })

const shelterForm = reactive({ id: null, name: '', address: '', capacity: 1, contact_phone: '', latitude: '', longitude: '', is_available: true })
const materialForm = reactive({ id: null, name: '', category: '', quantity: 0, unit: '件', storage_location: '', warning_quantity: 10, production_date: '', expire_date: '', expiry_warning_days: 30 })

const validateText = (min, message) => (_rule, value, callback) => (!value || String(value).trim().length < min) ? callback(new Error(message)) : callback()
const validatePhone = (_rule, value, callback) => {
  if (!value) return callback()
  const digits = value.replace(/[-\s]/g, '')
  if (!/^\d{7,20}$/.test(digits)) return callback(new Error('联系电话格式不正确'))
  callback()
}
const validateLatitude = (_rule, value, callback) => {
  if (value === '' || value === null || value === undefined) return callback()
  const num = Number(value)
  if (Number.isNaN(num) || num < -90 || num > 90) return callback(new Error('纬度必须在 -90 到 90 之间'))
  callback()
}
const validateLongitude = (_rule, value, callback) => {
  if (value === '' || value === null || value === undefined) return callback()
  const num = Number(value)
  if (Number.isNaN(num) || num < -180 || num > 180) return callback(new Error('经度必须在 -180 到 180 之间'))
  callback()
}
const validateExpireDate = (_rule, value, callback) => {
  if (materialForm.production_date && value && value < materialForm.production_date) return callback(new Error('过期日期不能早于生产日期'))
  callback()
}

const shelterRules = {
  name: [{ required: true, validator: validateText(2, '避难点名称不能少于 2 个字'), trigger: 'blur' }],
  address: [{ required: true, validator: validateText(4, '避难点地址不能少于 4 个字'), trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容量', trigger: 'change' }],
  contact_phone: [{ validator: validatePhone, trigger: 'blur' }],
  latitude: [{ validator: validateLatitude, trigger: 'blur' }],
  longitude: [{ validator: validateLongitude, trigger: 'blur' }]
}

const materialRules = {
  name: [{ required: true, validator: validateText(2, '物资名称不能少于 2 个字'), trigger: 'blur' }],
  category: [{ required: true, validator: validateText(2, '物资类别不能少于 2 个字'), trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入库存数量', trigger: 'change' }],
  unit: [{ required: true, validator: validateText(1, '请输入单位'), trigger: 'blur' }],
  storage_location: [{ required: true, validator: validateText(2, '请输入存放位置'), trigger: 'blur' }],
  warning_quantity: [{ required: true, message: '请输入预警阈值', trigger: 'change' }],
  expire_date: [{ validator: validateExpireDate, trigger: 'change' }]
}

const availableShelterCount = computed(() => shelters.value.filter(item => item.is_available).length)
const materialRiskCount = computed(() => materials.value.filter(item => item.is_low_stock || item.is_expiring_soon || item.is_expired).length)

const loadShelters = async () => {
  shelterLoading.value = true
  try {
    const params = { ...buildPageParams(shelterPagination) }
    if (shelterFilters.search) params.search = shelterFilters.search
    if (shelterFilters.is_available !== '') params.is_available = shelterFilters.is_available
    const data = await request.get('/shelters/', { params })
    const page = unwrapPaginated(data)
    shelters.value = page.list
    shelterPagination.total = page.total
  } finally { shelterLoading.value = false }
}

const loadMaterials = async () => {
  materialLoading.value = true
  try {
    const params = { ...buildPageParams(materialPagination) }
    if (materialFilters.search) params.search = materialFilters.search
    if (materialFilters.stock_status) params.stock_status = materialFilters.stock_status
    if (materialFilters.expiry_status) params.expiry_status = materialFilters.expiry_status
    const data = await request.get('/materials/', { params })
    const page = unwrapPaginated(data)
    materials.value = page.list
    materialPagination.total = page.total
  } finally { materialLoading.value = false }
}

const refreshAll = () => Promise.all([loadShelters(), loadMaterials()])
const searchShelters = () => { shelterPagination.page = 1; loadShelters() }
const searchMaterials = () => { materialPagination.page = 1; loadMaterials() }
const resetShelterFilters = () => { shelterFilters.search = ''; shelterFilters.is_available = ''; searchShelters() }
const resetMaterialFilters = () => { materialFilters.search = ''; materialFilters.stock_status = ''; materialFilters.expiry_status = ''; searchMaterials() }
const changeShelterSize = size => { shelterPagination.pageSize = size; shelterPagination.page = 1; loadShelters() }
const changeShelterPage = page => { shelterPagination.page = page; loadShelters() }
const changeMaterialSize = size => { materialPagination.pageSize = size; materialPagination.page = 1; loadMaterials() }
const changeMaterialPage = page => { materialPagination.page = page; loadMaterials() }

const resetShelterForm = () => Object.assign(shelterForm, { id: null, name: '', address: '', capacity: 1, contact_phone: '', latitude: '', longitude: '', is_available: true })
const resetMaterialForm = () => Object.assign(materialForm, { id: null, name: '', category: '', quantity: 0, unit: '件', storage_location: '', warning_quantity: 10, production_date: '', expire_date: '', expiry_warning_days: 30 })
const openShelterCreateDialog = () => { resetShelterForm(); shelterIsEdit.value = false; shelterFormVisible.value = true }
const openShelterEditDialog = row => { shelterIsEdit.value = true; Object.assign(shelterForm, row); shelterFormVisible.value = true }
const openShelterDetail = row => { currentShelter.value = row; shelterDetailVisible.value = true }
const openMaterialCreateDialog = () => { resetMaterialForm(); materialIsEdit.value = false; materialFormVisible.value = true }
const openMaterialEditDialog = row => { materialIsEdit.value = true; Object.assign(materialForm, row); materialFormVisible.value = true }

const submitShelterForm = async () => {
  await shelterFormRef.value.validate()
  shelterSubmitLoading.value = true
  try {
    const payload = { ...shelterForm, latitude: shelterForm.latitude || null, longitude: shelterForm.longitude || null }
    if (shelterIsEdit.value) { await request.patch(`/shelters/${shelterForm.id}/`, payload); ElMessage.success('避难点修改成功') }
    else { await request.post('/shelters/', payload); ElMessage.success('避难点新增成功') }
    shelterFormVisible.value = false
    await loadShelters()
  } finally { shelterSubmitLoading.value = false }
}

const submitMaterialForm = async () => {
  await materialFormRef.value.validate()
  materialSubmitLoading.value = true
  try {
    const payload = { ...materialForm, production_date: materialForm.production_date || null, expire_date: materialForm.expire_date || null }
    if (materialIsEdit.value) { await request.patch(`/materials/${materialForm.id}/`, payload); ElMessage.success('物资修改成功') }
    else { await request.post('/materials/', payload); ElMessage.success('物资新增成功') }
    materialFormVisible.value = false
    await loadMaterials()
  } finally { materialSubmitLoading.value = false }
}

const deleteShelter = async row => {
  try { await ElMessageBox.confirm(`确定要删除避难点「${row.name}」吗？删除后不可恢复。`, '危险操作', { type: 'warning' }); await request.delete(`/shelters/${row.id}/`); ElMessage.success('避难点删除成功'); await loadShelters() } catch (error) { if (error === 'cancel' || error === 'close') return }
}
const deleteMaterial = async row => {
  try { await ElMessageBox.confirm(`确定要删除物资「${row.name}」吗？删除后不可恢复。`, '危险操作', { type: 'warning' }); await request.delete(`/materials/${row.id}/`); ElMessage.success('物资删除成功'); await loadMaterials() } catch (error) { if (error === 'cancel' || error === 'close') return }
}

const formatTime = value => value ? value.replace('T', ' ').slice(0, 19) : '-'
const expiryText = row => {
  if (row.days_until_expire === null || row.days_until_expire === undefined) return '未登记过期日期'
  if (row.days_until_expire < 0) return `已过期 ${Math.abs(row.days_until_expire)} 天`
  return `剩余 ${row.days_until_expire} 天`
}
const lifecycleTagType = row => row.is_expired ? 'danger' : row.is_expiring_soon ? 'warning' : row.expire_date ? 'success' : 'info'

onMounted(() => refreshAll())
</script>

<style scoped>
.summary-row { margin-bottom: 18px; }
.summary-card { background:#fff; border-radius:16px; padding:20px; box-shadow:0 8px 24px rgba(15,23,42,.06); border-left:5px solid #2563eb; }
.summary-card.success { border-left-color:#10b981; }
.summary-card.danger { border-left-color:#ef4444; }
.summary-label { font-size:15px; color:#64748b; }
.summary-value { margin-top:8px; font-size:30px; font-weight:800; color:#1e293b; }
.summary-desc { margin-top:6px; font-size:13px; color:#94a3b8; }
.tab-toolbar { display:flex; justify-content:space-between; align-items:center; margin:10px 0 18px; gap:16px; }
.search-area { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
.danger-text { color:#dc2626; font-weight:700; }
.tiny-text { color:#64748b; font-size:12px; margin-top:2px; }
.detail-map-title { margin:18px 0 10px; font-weight:700; }
</style>
