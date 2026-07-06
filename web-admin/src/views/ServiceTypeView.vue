<template>
  <div class="page">
    <div class="page-header">
      <h2 style="margin: 0">服务目录管理</h2>
      <el-button type="primary" @click="openCreate">新建服务类型</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="服务目录定义社区长期服务（如老人健康检查、助浴、代购）。所需技能用于自动排班时匹配志愿者。"
      style="margin-bottom: 16px"
    />

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column label="服务" min-width="160">
          <template #default="{ row }">
            <span style="font-size:16px;margin-right:6px">{{ row.icon }}</span>{{ row.name }}
          </template>
        </el-table-column>
        <el-table-column prop="code" label="标识" width="130" />
        <el-table-column prop="category" label="分类" width="110" />
        <el-table-column prop="required_skill" label="所需技能" width="110" />
        <el-table-column prop="default_frequency_display" label="默认周期" width="100" />
        <el-table-column label="健康记录" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.needs_health_record" type="success" size="small">需录入</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑服务类型' : '新建服务类型'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="服务名称" required>
          <el-input v-model="form.name" placeholder="如 老人健康检查" />
        </el-form-item>
        <el-form-item label="服务标识" required>
          <el-input v-model="form.code" :disabled="editing" placeholder="英文标识，如 health_check" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" placeholder="如 医疗健康 / 生活照护" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" maxlength="2" placeholder="emoji，如 🩺" style="width: 120px" />
        </el-form-item>
        <el-form-item label="所需技能">
          <el-input v-model="form.required_skill" placeholder="志愿者技能需含此关键字，如 医疗" />
        </el-form-item>
        <el-form-item label="默认周期">
          <el-select v-model="form.default_frequency" style="width: 100%">
            <el-option v-for="f in FREQ" :key="f.value" :label="f.label" :value="f.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计时长">
          <el-input-number v-model="form.duration_minutes" :min="5" :max="480" :step="5" /> 分钟
        </el-form-item>
        <el-form-item label="服务说明">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="健康记录">
          <el-switch v-model="form.needs_health_record" active-text="上门需录入血压/体温等" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const FREQ = [
  { value: 'weekly', label: '每周' },
  { value: 'biweekly', label: '每两周' },
  { value: 'monthly', label: '每月' }
]

const loading = ref(false)
const saving = ref(false)
const items = ref([])
const dialogVisible = ref(false)
const editing = ref(false)
const editId = ref(null)

const blank = () => ({
  name: '', code: '', category: '', icon: '🛎️', required_skill: '',
  default_frequency: 'weekly', duration_minutes: 30, description: '',
  needs_health_record: false, is_active: true
})
const form = reactive(blank())

const loadData = async () => {
  loading.value = true
  try {
    const data = await request.get('/service-types/')
    items.value = Array.isArray(data) ? data : (data.results || [])
  } catch (e) { /* 拦截器提示 */ } finally { loading.value = false }
}

const openCreate = () => {
  editing.value = false; editId.value = null
  Object.assign(form, blank())
  dialogVisible.value = true
}

const openEdit = row => {
  editing.value = true; editId.value = row.id
  Object.assign(form, {
    name: row.name, code: row.code, category: row.category || '', icon: row.icon || '🛎️',
    required_skill: row.required_skill || '', default_frequency: row.default_frequency,
    duration_minutes: row.duration_minutes, description: row.description || '',
    needs_health_record: row.needs_health_record, is_active: row.is_active
  })
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.name || !form.code) { ElMessage.warning('请填写服务名称与标识'); return }
  saving.value = true
  try {
    if (editing.value) {
      await request.patch(`/service-types/${editId.value}/`, form)
      ElMessage.success('已更新')
    } else {
      await request.post('/service-types/', form)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) { /* 拦截器提示 */ } finally { saving.value = false }
}

const remove = async row => {
  try {
    await ElMessageBox.confirm(`确定删除服务「${row.name}」吗？`, '提示', { type: 'warning' })
  } catch (e) { return }
  try {
    await request.delete(`/service-types/${row.id}/`)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { /* 拦截器提示 */ }
}

onMounted(loadData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
