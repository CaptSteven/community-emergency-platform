<template>
  <div class="page">
    <div class="page-header">
      <h2 style="margin: 0">服务计划管理</h2>
      <div>
        <el-button type="success" :loading="generating" @click="generateVisits">生成本周排班</el-button>
        <el-button type="primary" @click="openCreate">新建服务计划</el-button>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="为居民（如独居老人）建立周期性上门服务计划；点击“生成本周排班”后，系统按技能匹配并轮流把到期计划派给志愿者。"
      style="margin-bottom: 16px"
    />

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="resident_name" label="受益居民" min-width="110" />
        <el-table-column label="服务" min-width="150">
          <template #default="{ row }">
            <span style="margin-right:6px">{{ row.service_type_icon }}</span>{{ row.service_type_name }}
          </template>
        </el-table-column>
        <el-table-column prop="frequency_display" label="周期" width="90" />
        <el-table-column prop="preferred_weekday_display" label="首选日" width="90" />
        <el-table-column prop="preferred_time" label="时段" width="90" />
        <el-table-column prop="address" label="服务地址" min-width="150" show-overflow-tooltip />
        <el-table-column prop="last_generated_date" label="最近排班" width="120" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '生效' : '暂停' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="generateNow(row)">立即排班</el-button>
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑服务计划' : '新建服务计划'" width="500px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="受益居民" required>
          <el-select v-model="form.resident" filterable placeholder="选择居民" style="width: 100%">
            <el-option v-for="r in residents" :key="r.id" :label="`${r.username}（${r.community || '—'}）`" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务类型" required>
          <el-select v-model="form.service_type" placeholder="选择服务" style="width: 100%" @change="onTypeChange">
            <el-option v-for="t in types" :key="t.id" :label="`${t.icon} ${t.name}`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务周期">
          <el-select v-model="form.frequency" style="width: 100%">
            <el-option v-for="f in FREQ" :key="f.value" :label="f.label" :value="f.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="首选星期">
          <el-select v-model="form.preferred_weekday" style="width: 100%">
            <el-option v-for="(w, i) in WEEKDAYS" :key="i" :label="w" :value="i" />
          </el-select>
        </el-form-item>
        <el-form-item label="首选时段">
          <el-input v-model="form.preferred_time" placeholder="如 09:00" style="width: 160px" />
        </el-form-item>
        <el-form-item label="服务地址">
          <el-input v-model="form.address" placeholder="留空则取居民资料地址" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="是否生效">
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
const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const loading = ref(false)
const saving = ref(false)
const generating = ref(false)
const items = ref([])
const residents = ref([])
const types = ref([])
const dialogVisible = ref(false)
const editing = ref(false)
const editId = ref(null)

const blank = () => ({
  resident: null, service_type: null, frequency: 'weekly',
  preferred_weekday: 0, preferred_time: '', address: '', note: '', is_active: true
})
const form = reactive(blank())

const loadData = async () => {
  loading.value = true
  try {
    const data = await request.get('/service-subscriptions/')
    items.value = Array.isArray(data) ? data : (data.results || [])
  } catch (e) { /* 拦截器提示 */ } finally { loading.value = false }
}

const loadRefs = async () => {
  try {
    const [r, t] = await Promise.all([
      request.get('/users/', { params: { role: 'resident' } }),
      request.get('/service-types/', { params: { is_active: true } })
    ])
    residents.value = Array.isArray(r) ? r : (r.results || [])
    types.value = Array.isArray(t) ? t : (t.results || [])
  } catch (e) { /* 拦截器提示 */ }
}

const onTypeChange = id => {
  const t = types.value.find(x => x.id === id)
  if (t && !editing.value) form.frequency = t.default_frequency
}

const openCreate = () => {
  editing.value = false; editId.value = null
  Object.assign(form, blank())
  dialogVisible.value = true
}

const openEdit = row => {
  editing.value = true; editId.value = row.id
  Object.assign(form, {
    resident: row.resident, service_type: row.service_type, frequency: row.frequency,
    preferred_weekday: row.preferred_weekday, preferred_time: row.preferred_time || '',
    address: row.address || '', note: row.note || '', is_active: row.is_active
  })
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.resident || !form.service_type) { ElMessage.warning('请选择居民与服务类型'); return }
  saving.value = true
  try {
    if (editing.value) {
      await request.patch(`/service-subscriptions/${editId.value}/`, form)
      ElMessage.success('已更新')
    } else {
      await request.post('/service-subscriptions/', form)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) { /* 拦截器提示 */ } finally { saving.value = false }
}

const remove = async row => {
  try {
    await ElMessageBox.confirm(`确定删除「${row.resident_name} · ${row.service_type_name}」计划吗？`, '提示', { type: 'warning' })
  } catch (e) { return }
  try {
    await request.delete(`/service-subscriptions/${row.id}/`)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { /* 拦截器提示 */ }
}

const generateVisits = async () => {
  generating.value = true
  try {
    const res = await request.post('/service-subscriptions/generate-visits/')
    ElMessage.success(res.message || '已生成排班')
    loadData()
  } catch (e) { /* 拦截器提示 */ } finally { generating.value = false }
}

const generateNow = async row => {
  try {
    const res = await request.post(`/service-subscriptions/${row.id}/generate-now/`)
    ElMessage.success(res.message || '已生成工单')
    loadData()
  } catch (e) { /* 拦截器提示 */ }
}

onMounted(() => { loadData(); loadRefs() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
