<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">应急资源管理</div>
        <div class="page-subtitle">
          管理社区避难点和应急物资库存，为灾害预警和居民求助提供资源支撑。
        </div>
      </div>

      <el-button type="primary" @click="refreshAll">
        刷新数据
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="18" class="summary-row">
      <el-col :span="6">
        <div class="summary-card">
          <div class="summary-label">避难点总数</div>
          <div class="summary-value">{{ shelters.length }}</div>
          <div class="summary-desc">社区登记避难点数量</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="summary-card success">
          <div class="summary-label">可用避难点</div>
          <div class="summary-value">{{ availableShelterCount }}</div>
          <div class="summary-desc">当前可对外开放</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="summary-card">
          <div class="summary-label">物资种类</div>
          <div class="summary-value">{{ materials.length }}</div>
          <div class="summary-desc">应急物资登记种类</div>
        </div>
      </el-col>

      <el-col :span="6">
        <div class="summary-card danger">
          <div class="summary-label">低库存物资</div>
          <div class="summary-value">{{ lowStockMaterialCount }}</div>
          <div class="summary-desc">库存低于预警阈值</div>
        </div>
      </el-col>
    </el-row>

    <div class="card">
      <el-tabs v-model="activeTab">
        <!-- 避难点管理 -->
        <el-tab-pane label="避难点管理" name="shelter">
          <div class="tab-toolbar">
            <div class="search-area">
              <el-input
                v-model="shelterKeyword"
                placeholder="搜索避难点名称或地址"
                clearable
                style="width: 260px"
              />

              <el-select
                v-model="shelterStatusFilter"
                placeholder="全部状态"
                clearable
                style="width: 160px"
              >
                <el-option label="可用" value="available" />
                <el-option label="不可用" value="unavailable" />
              </el-select>
            </div>

            <el-button type="primary" @click="openShelterCreateDialog">
              新增避难点
            </el-button>
          </div>

          <el-table
            v-loading="shelterLoading"
            :data="filteredShelters"
            border
            style="width: 100%"
          >
            <el-table-column prop="id" label="ID" width="70" />

            <el-table-column prop="name" label="避难点名称" min-width="160" />

            <el-table-column prop="address" label="地址" min-width="220" show-overflow-tooltip />

            <el-table-column prop="capacity" label="容量" width="100" />

            <el-table-column prop="contact_phone" label="联系电话" width="140" />

            <el-table-column label="经纬度" width="190">
              <template #default="{ row }">
                {{ row.latitude || '-' }}，{{ row.longitude || '-' }}
              </template>
            </el-table-column>

            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_available ? 'success' : 'info'">
                  {{ row.is_available ? '可用' : '不可用' }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="openShelterEditDialog(row)">
                  编辑
                </el-button>

                <el-button size="small" type="danger" @click="deleteShelter(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 应急物资管理 -->
        <el-tab-pane label="应急物资管理" name="material">
          <div class="tab-toolbar">
            <div class="search-area">
              <el-input
                v-model="materialKeyword"
                placeholder="搜索物资名称、类别或存放位置"
                clearable
                style="width: 280px"
              />

              <el-select
                v-model="materialStockFilter"
                placeholder="全部库存状态"
                clearable
                style="width: 170px"
              >
                <el-option label="库存正常" value="normal" />
                <el-option label="低库存" value="low" />
              </el-select>
            </div>

            <el-button type="primary" @click="openMaterialCreateDialog">
              新增物资
            </el-button>
          </div>

          <el-table
            v-loading="materialLoading"
            :data="filteredMaterials"
            border
            style="width: 100%"
          >
            <el-table-column prop="id" label="ID" width="70" />

            <el-table-column prop="name" label="物资名称" min-width="150" />

            <el-table-column prop="category" label="物资类别" width="130" />

            <el-table-column label="库存数量" width="120">
              <template #default="{ row }">
                <span :class="{ 'danger-text': row.is_low_stock }">
                  {{ row.quantity }} {{ row.unit }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="预警阈值" width="120">
              <template #default="{ row }">
                {{ row.warning_quantity }} {{ row.unit }}
              </template>
            </el-table-column>

            <el-table-column prop="storage_location" label="存放位置" min-width="180" show-overflow-tooltip />

            <el-table-column label="库存状态" width="110">
              <template #default="{ row }">
                <el-tag :type="row.is_low_stock ? 'danger' : 'success'">
                  {{ row.is_low_stock ? '低库存' : '正常' }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="更新时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.updated_at) }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="openMaterialEditDialog(row)">
                  编辑
                </el-button>

                <el-button size="small" type="danger" @click="deleteMaterial(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 避难点新增 / 编辑弹窗 -->
    <el-dialog
      v-model="shelterFormVisible"
      :title="shelterIsEdit ? '编辑避难点' : '新增避难点'"
      width="620px"
    >
      <el-form
        ref="shelterFormRef"
        :model="shelterForm"
        :rules="shelterRules"
        label-position="top"
      >
        <el-form-item label="避难点名称" prop="name">
          <el-input v-model="shelterForm.name" placeholder="例如：阳光社区服务中心" />
        </el-form-item>

        <el-form-item label="地址" prop="address">
          <el-input v-model="shelterForm.address" placeholder="请输入详细地址" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="容量" prop="capacity">
              <el-input-number
                v-model="shelterForm.capacity"
                :min="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="shelterForm.contact_phone" placeholder="例如：13800000000" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="纬度">
              <el-input v-model="shelterForm.latitude" placeholder="例如：39.9042" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="经度">
              <el-input v-model="shelterForm.longitude" placeholder="例如：116.4074" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="是否可用">
          <el-switch
            v-model="shelterForm.is_available"
            active-text="可用"
            inactive-text="不可用"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="shelterFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="shelterSubmitLoading" @click="submitShelterForm">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 物资新增 / 编辑弹窗 -->
    <el-dialog
      v-model="materialFormVisible"
      :title="materialIsEdit ? '编辑应急物资' : '新增应急物资'"
      width="620px"
    >
      <el-form
        ref="materialFormRef"
        :model="materialForm"
        :rules="materialRules"
        label-position="top"
      >
        <el-form-item label="物资名称" prop="name">
          <el-input v-model="materialForm.name" placeholder="例如：矿泉水、应急药箱、手电筒" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="物资类别" prop="category">
              <el-input v-model="materialForm.category" placeholder="例如：食品、医疗、照明" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="materialForm.unit" placeholder="例如：箱、个、套" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="库存数量" prop="quantity">
              <el-input-number
                v-model="materialForm.quantity"
                :min="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="预警阈值" prop="warning_quantity">
              <el-input-number
                v-model="materialForm.warning_quantity"
                :min="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="存放位置" prop="storage_location">
          <el-input v-model="materialForm.storage_location" placeholder="例如：社区仓库 A 区" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="materialFormVisible = false">取消</el-button>
        <el-button type="primary" :loading="materialSubmitLoading" @click="submitMaterialForm">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const activeTab = ref('shelter')

const shelterLoading = ref(false)
const materialLoading = ref(false)
const shelterSubmitLoading = ref(false)
const materialSubmitLoading = ref(false)

const shelters = ref([])
const materials = ref([])

const shelterKeyword = ref('')
const shelterStatusFilter = ref('')
const materialKeyword = ref('')
const materialStockFilter = ref('')

const shelterFormVisible = ref(false)
const materialFormVisible = ref(false)

const shelterIsEdit = ref(false)
const materialIsEdit = ref(false)

const shelterFormRef = ref(null)
const materialFormRef = ref(null)

const shelterForm = reactive({
  id: null,
  name: '',
  address: '',
  capacity: 0,
  contact_phone: '',
  latitude: '',
  longitude: '',
  is_available: true
})

const materialForm = reactive({
  id: null,
  name: '',
  category: '',
  quantity: 0,
  unit: '',
  storage_location: '',
  warning_quantity: 0
})

const shelterRules = {
  name: [
    { required: true, message: '请输入避难点名称', trigger: 'blur' }
  ],
  address: [
    { required: true, message: '请输入避难点地址', trigger: 'blur' }
  ],
  capacity: [
    { required: true, message: '请输入容量', trigger: 'change' }
  ]
}

const materialRules = {
  name: [
    { required: true, message: '请输入物资名称', trigger: 'blur' }
  ],
  category: [
    { required: true, message: '请输入物资类别', trigger: 'blur' }
  ],
  quantity: [
    { required: true, message: '请输入库存数量', trigger: 'change' }
  ],
  unit: [
    { required: true, message: '请输入单位', trigger: 'blur' }
  ],
  storage_location: [
    { required: true, message: '请输入存放位置', trigger: 'blur' }
  ],
  warning_quantity: [
    { required: true, message: '请输入预警阈值', trigger: 'change' }
  ]
}

const availableShelterCount = computed(() => {
  return shelters.value.filter(item => item.is_available).length
})

const lowStockMaterialCount = computed(() => {
  return materials.value.filter(item => item.is_low_stock).length
})

const filteredShelters = computed(() => {
  let result = shelters.value

  if (shelterKeyword.value) {
    const keyword = shelterKeyword.value.trim().toLowerCase()
    result = result.filter(item => {
      return (
        item.name?.toLowerCase().includes(keyword) ||
        item.address?.toLowerCase().includes(keyword)
      )
    })
  }

  if (shelterStatusFilter.value === 'available') {
    result = result.filter(item => item.is_available)
  }

  if (shelterStatusFilter.value === 'unavailable') {
    result = result.filter(item => !item.is_available)
  }

  return result
})

const filteredMaterials = computed(() => {
  let result = materials.value

  if (materialKeyword.value) {
    const keyword = materialKeyword.value.trim().toLowerCase()
    result = result.filter(item => {
      return (
        item.name?.toLowerCase().includes(keyword) ||
        item.category?.toLowerCase().includes(keyword) ||
        item.storage_location?.toLowerCase().includes(keyword)
      )
    })
  }

  if (materialStockFilter.value === 'low') {
    result = result.filter(item => item.is_low_stock)
  }

  if (materialStockFilter.value === 'normal') {
    result = result.filter(item => !item.is_low_stock)
  }

  return result
})

const loadShelters = async () => {
  shelterLoading.value = true

  try {
    shelters.value = await request.get('/shelters/')
  } finally {
    shelterLoading.value = false
  }
}

const loadMaterials = async () => {
  materialLoading.value = true

  try {
    materials.value = await request.get('/materials/')
  } finally {
    materialLoading.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([
    loadShelters(),
    loadMaterials()
  ])
}

const resetShelterForm = () => {
  shelterForm.id = null
  shelterForm.name = ''
  shelterForm.address = ''
  shelterForm.capacity = 0
  shelterForm.contact_phone = ''
  shelterForm.latitude = ''
  shelterForm.longitude = ''
  shelterForm.is_available = true
}

const resetMaterialForm = () => {
  materialForm.id = null
  materialForm.name = ''
  materialForm.category = ''
  materialForm.quantity = 0
  materialForm.unit = ''
  materialForm.storage_location = ''
  materialForm.warning_quantity = 0
}

const openShelterCreateDialog = () => {
  resetShelterForm()
  shelterIsEdit.value = false
  shelterFormVisible.value = true
}

const openShelterEditDialog = row => {
  shelterIsEdit.value = true

  shelterForm.id = row.id
  shelterForm.name = row.name
  shelterForm.address = row.address
  shelterForm.capacity = row.capacity
  shelterForm.contact_phone = row.contact_phone
  shelterForm.latitude = row.latitude
  shelterForm.longitude = row.longitude
  shelterForm.is_available = row.is_available

  shelterFormVisible.value = true
}

const openMaterialCreateDialog = () => {
  resetMaterialForm()
  materialIsEdit.value = false
  materialFormVisible.value = true
}

const openMaterialEditDialog = row => {
  materialIsEdit.value = true

  materialForm.id = row.id
  materialForm.name = row.name
  materialForm.category = row.category
  materialForm.quantity = row.quantity
  materialForm.unit = row.unit
  materialForm.storage_location = row.storage_location
  materialForm.warning_quantity = row.warning_quantity

  materialFormVisible.value = true
}

const submitShelterForm = async () => {
  await shelterFormRef.value.validate()

  shelterSubmitLoading.value = true

  try {
    const payload = {
      name: shelterForm.name,
      address: shelterForm.address,
      capacity: shelterForm.capacity,
      contact_phone: shelterForm.contact_phone,
      latitude: shelterForm.latitude || null,
      longitude: shelterForm.longitude || null,
      is_available: shelterForm.is_available
    }

    if (shelterIsEdit.value) {
      await request.patch(`/shelters/${shelterForm.id}/`, payload)
      ElMessage.success('避难点修改成功')
    } else {
      await request.post('/shelters/', payload)
      ElMessage.success('避难点新增成功')
    }

    shelterFormVisible.value = false
    loadShelters()
  } finally {
    shelterSubmitLoading.value = false
  }
}

const submitMaterialForm = async () => {
  await materialFormRef.value.validate()

  materialSubmitLoading.value = true

  try {
    const payload = {
      name: materialForm.name,
      category: materialForm.category,
      quantity: materialForm.quantity,
      unit: materialForm.unit,
      storage_location: materialForm.storage_location,
      warning_quantity: materialForm.warning_quantity
    }

    if (materialIsEdit.value) {
      await request.patch(`/materials/${materialForm.id}/`, payload)
      ElMessage.success('物资修改成功')
    } else {
      await request.post('/materials/', payload)
      ElMessage.success('物资新增成功')
    }

    materialFormVisible.value = false
    loadMaterials()
  } finally {
    materialSubmitLoading.value = false
  }
}

const deleteShelter = async row => {
  try {
    await ElMessageBox.confirm(
      `确定要删除避难点「${row.name}」吗？删除后不可恢复。`,
      '危险操作',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )

    await request.delete(`/shelters/${row.id}/`)
    ElMessage.success('避难点删除成功')
    await loadShelters()
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return
    }
  }
}

const deleteMaterial = async row => {
  try {
    await ElMessageBox.confirm(
      `确定要删除物资「${row.name}」吗？删除后不可恢复。`,
      '危险操作',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )

    await request.delete(`/materials/${row.id}/`)
    ElMessage.success('物资删除成功')
    await loadMaterials()
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return
    }
  }
}

const formatTime = value => {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.page-subtitle {
  margin-top: 6px;
  color: #64748b;
  font-size: 14px;
}

.summary-row {
  margin-bottom: 18px;
}

.summary-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  border-left: 5px solid #2563eb;
}

.summary-card.success {
  border-left-color: #10b981;
}

.summary-card.danger {
  border-left-color: #ef4444;
}

.summary-label {
  font-size: 15px;
  color: #64748b;
}

.summary-value {
  margin-top: 8px;
  font-size: 30px;
  font-weight: 800;
  color: #1e293b;
}

.summary-desc {
  margin-top: 6px;
  font-size: 13px;
  color: #94a3b8;
}

.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 10px 0 18px;
}

.search-area {
  display: flex;
  gap: 12px;
  align-items: center;
}

.danger-text {
  color: #dc2626;
  font-weight: 700;
}
</style>