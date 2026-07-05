<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">灾害预警管理</div>
        <div class="page-subtitle">发布社区灾害预警，管理预警等级、生效状态和通知内容。</div>
      </div>

      <div>
        <el-button :loading="loading" @click="loadData">刷新</el-button>
        <el-button type="primary" @click="openCreateDialog">发布预警</el-button>
      </div>
    </div>

    <div class="card filter-card">
      <el-form :inline="true">
        <el-form-item label="预警类型">
          <el-select v-model="filters.warning_type" placeholder="全部类型" clearable style="width: 180px">
            <el-option label="暴雨" value="rainstorm" />
            <el-option label="火灾" value="fire" />
            <el-option label="停电" value="power_outage" />
            <el-option label="地震" value="earthquake" />
            <el-option label="高温" value="heat" />
            <el-option label="寒潮" value="cold_wave" />
            <el-option label="内涝" value="flood" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>

        <el-form-item label="预警等级">
          <el-select v-model="filters.level" placeholder="全部等级" clearable style="width: 180px">
            <el-option label="蓝色预警" value="blue" />
            <el-option label="黄色预警" value="yellow" />
            <el-option label="橙色预警" value="orange" />
            <el-option label="红色预警" value="red" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="filters.is_active" placeholder="全部状态" clearable style="width: 160px">
            <el-option label="生效中" value="true" />
            <el-option label="已停用" value="false" />
          </el-select>
        </el-form-item>

        <el-form-item label="关键词">
          <el-input v-model="filters.search" placeholder="搜索标题、内容或社区" clearable style="width: 220px" @keyup.enter="handleSearch" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="card">
      <el-table v-loading="loading" :data="warnings" border style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="预警标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="warning_type_display" label="类型" width="110" />
        <el-table-column label="等级" width="120">
          <template #default="{ row }"><el-tag :type="levelTagType(row.level)">{{ row.level_display }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="community" label="影响社区" width="140" />
        <el-table-column prop="content" label="预警内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '生效中' : '已停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="publisher_name" label="发布人" width="110" />
        <el-table-column label="发布时间" width="180"><template #default="{ row }">{{ formatTime(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDetail(row)">详情</el-button>
            <el-button size="small" type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" :type="row.is_active ? 'warning' : 'success'" @click="toggleActive(row)">{{ row.is_active ? '停用' : '启用' }}</el-button>
            <el-button size="small" type="danger" @click="deleteWarning(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="pagination.total"
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50]"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <el-dialog v-model="detailVisible" title="预警详情" width="650px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="预警标题">{{ currentWarning?.title }}</el-descriptions-item>
        <el-descriptions-item label="预警类型">{{ currentWarning?.warning_type_display }}</el-descriptions-item>
        <el-descriptions-item label="预警等级">{{ currentWarning?.level_display }}</el-descriptions-item>
        <el-descriptions-item label="影响社区">{{ currentWarning?.community || '-' }}</el-descriptions-item>
        <el-descriptions-item label="预警内容">{{ currentWarning?.content }}</el-descriptions-item>
        <el-descriptions-item label="发布人">{{ currentWarning?.publisher_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ currentWarning?.is_active ? '生效中' : '已停用' }}</el-descriptions-item>
        <el-descriptions-item label="发布时间">{{ formatTime(currentWarning?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatTime(currentWarning?.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <el-dialog v-model="formVisible" :title="isEdit ? '编辑预警' : '发布预警'" width="650px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="预警标题" prop="title">
          <el-input v-model="form.title" maxlength="100" show-word-limit placeholder="请输入预警标题" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="预警类型" prop="warning_type">
              <el-select v-model="form.warning_type" placeholder="请选择预警类型" style="width: 100%">
                <el-option label="暴雨" value="rainstorm" />
                <el-option label="火灾" value="fire" />
                <el-option label="停电" value="power_outage" />
                <el-option label="地震" value="earthquake" />
                <el-option label="高温" value="heat" />
                <el-option label="寒潮" value="cold_wave" />
                <el-option label="内涝" value="flood" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预警等级" prop="level">
              <el-select v-model="form.level" placeholder="请选择预警等级" style="width: 100%">
                <el-option label="蓝色预警" value="blue" />
                <el-option label="黄色预警" value="yellow" />
                <el-option label="橙色预警" value="orange" />
                <el-option label="红色预警" value="red" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="影响社区">
          <el-input v-model="form.community" placeholder="例如：阳光社区" />
        </el-form-item>

        <el-form-item label="预警内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="5" minlength="10" maxlength="1000" show-word-limit placeholder="请输入灾害情况、防护建议、避难提醒等" />
        </el-form-item>

        <el-form-item label="是否生效">
          <el-switch v-model="form.is_active" active-text="生效" inactive-text="停用" />
        </el-form-item>

        <el-alert
          v-if="!isEdit && form.level === 'red'"
          type="error"
          show-icon
          :closable="false"
          class="plan-alert"
          title="红色预警可联动启动应急预案：强提醒居民、开放避难点、向志愿者发送待命指令。"
        />

        <el-form-item v-if="!isEdit && form.level === 'red'" label="联动机制">
          <el-checkbox v-model="form.launch_emergency_plan">发布后同步启动一键应急预案</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'
import { buildPageParams, unwrapPaginated } from '../utils/pagination'

const loading = ref(false)
const submitLoading = ref(false)
const warnings = ref([])
const detailVisible = ref(false)
const formVisible = ref(false)
const isEdit = ref(false)
const currentWarning = ref(null)
const formRef = ref(null)

const filters = reactive({ warning_type: '', level: '', is_active: '', search: '' })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, title: '', warning_type: '', level: '', content: '', community: '阳光社区', is_active: true, launch_emergency_plan: false })

const validateLength = (min, message) => (_rule, value, callback) => {
  if (!value || value.trim().length < min) callback(new Error(message))
  else callback()
}

const rules = {
  title: [{ required: true, validator: validateLength(4, '预警标题不能少于 4 个字'), trigger: 'blur' }],
  warning_type: [{ required: true, message: '请选择预警类型', trigger: 'change' }],
  level: [{ required: true, message: '请选择预警等级', trigger: 'change' }],
  content: [{ required: true, validator: validateLength(10, '预警内容不能少于 10 个字'), trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const params = { ...buildPageParams(pagination) }
    if (filters.warning_type) params.warning_type = filters.warning_type
    if (filters.level) params.level = filters.level
    if (filters.is_active !== '') params.is_active = filters.is_active
    if (filters.search) params.search = filters.search
    const data = await request.get('/warnings/', { params })
    const page = unwrapPaginated(data)
    warnings.value = page.list
    pagination.total = page.total
  } finally {
    loading.value = false
  }
}

const handleSearch = () => { pagination.page = 1; loadData() }
const resetFilters = () => { filters.warning_type = ''; filters.level = ''; filters.is_active = ''; filters.search = ''; handleSearch() }
const handleSizeChange = size => { pagination.pageSize = size; pagination.page = 1; loadData() }
const handlePageChange = page => { pagination.page = page; loadData() }

const resetForm = () => {
  form.id = null
  form.title = ''
  form.warning_type = ''
  form.level = ''
  form.content = ''
  form.community = '阳光社区'
  form.is_active = true
  form.launch_emergency_plan = false
}

const openCreateDialog = () => { resetForm(); isEdit.value = false; formVisible.value = true }
const openEditDialog = row => {
  isEdit.value = true
  Object.assign(form, { ...row, launch_emergency_plan: false })
  formVisible.value = true
}
const openDetail = row => { currentWarning.value = row; detailVisible.value = true }

const submitForm = async () => {
  await formRef.value.validate()
  if (!isEdit.value && form.level === 'red' && form.launch_emergency_plan) {
    await ElMessageBox.confirm('确认发布红色预警并联动启动应急预案吗？', '红色预警联动确认', { type: 'warning' })
  }

  submitLoading.value = true
  try {
    const payload = {
      title: form.title,
      warning_type: form.warning_type,
      level: form.level,
      content: form.content,
      community: form.community,
      is_active: form.is_active,
      launch_emergency_plan: form.launch_emergency_plan
    }
    if (isEdit.value) {
      await request.patch(`/warnings/${form.id}/`, payload)
      ElMessage.success('预警修改成功')
    } else {
      await request.post('/warnings/', payload)
      ElMessage.success(form.launch_emergency_plan ? '预警发布成功，应急预案已联动启动' : '预警发布成功')
    }
    formVisible.value = false
    await loadData()
  } finally {
    submitLoading.value = false
  }
}

const toggleActive = async row => {
  const actionText = row.is_active ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${actionText}该预警吗？`, '提示', { type: 'warning', confirmButtonText: `确定${actionText}`, cancelButtonText: '取消' })
    await request.patch(`/warnings/${row.id}/`, { is_active: !row.is_active })
    ElMessage.success(`${actionText}成功`)
    await loadData()
  } catch (error) { if (error === 'cancel' || error === 'close') return }
}

const deleteWarning = async row => {
  try {
    await ElMessageBox.confirm(`确定要删除预警「${row.title}」吗？删除后不可恢复。`, '危险操作', { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' })
    await request.delete(`/warnings/${row.id}/`)
    ElMessage.success('删除成功')
    await loadData()
  } catch (error) { if (error === 'cancel' || error === 'close') return }
}

const levelTagType = level => ({ blue: 'primary', yellow: 'warning', orange: 'warning', red: 'danger' }[level] || 'info')
const formatTime = value => value ? value.replace('T', ' ').slice(0, 19) : '-'

onMounted(() => loadData())
</script>

<style scoped>
.plan-alert {
  margin-bottom: 12px;
}
</style>
