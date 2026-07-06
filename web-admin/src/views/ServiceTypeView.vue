<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">服务目录管理</div>
        <div class="page-subtitle">定义社区长期服务（如老人健康检查、助浴、代购），所需技能用于自动排班时匹配志愿者。</div>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" @click="loadData">刷新</el-button>
        <el-button type="primary" @click="openCreate">新建服务类型</el-button>
      </div>
    </div>

    <div class="card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column label="服务" min-width="200">
          <template #default="{ row }">
            <div class="svc-cell">
              <span class="svc-icon">{{ row.icon || '🛎️' }}</span>
              <div class="svc-meta">
                <div class="svc-name">{{ row.name }}</div>
                <div class="svc-desc" v-if="row.description">{{ row.description }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="标识" width="140" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.category" type="info" effect="plain" round>{{ row.category }}</el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="required_skill" label="所需技能" width="120">
          <template #default="{ row }">
            <span v-if="row.required_skill">{{ row.required_skill }}</span>
            <span v-else class="muted">不限</span>
          </template>
        </el-table-column>
        <el-table-column prop="default_frequency_display" label="默认周期" width="100" />
        <el-table-column label="健康记录" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.needs_health_record" type="warning" effect="dark" size="small">需录入</el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="dark" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-state">
            <div class="empty-emoji">🗂️</div>
            <div class="empty-title">还没有服务类型</div>
            <div class="empty-tip">点击右上角「新建服务类型」，添加社区长期服务项目吧</div>
          </div>
        </template>
      </el-table>

      <el-pagination
        v-if="pagination.total > 0"
        class="pagination"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="pagination.total"
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

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
import { buildPageParams, unwrapPaginated } from '../utils/pagination'

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

// 分页（兼容后端返回数组或 {count,results}）
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const blank = () => ({
  name: '', code: '', category: '', icon: '🛎️', required_skill: '',
  default_frequency: 'weekly', duration_minutes: 30, description: '',
  needs_health_record: false, is_active: true
})
const form = reactive(blank())

const loadData = async () => {
  loading.value = true
  try {
    const data = await request.get('/service-types/', { params: { ...buildPageParams(pagination) } })
    const page = unwrapPaginated(data)
    items.value = page.list
    pagination.total = page.total
  } catch (e) { /* 拦截器提示 */ } finally { loading.value = false }
}

const handleSizeChange = size => { pagination.pageSize = size; pagination.page = 1; loadData() }
const handlePageChange = page => { pagination.page = page; loadData() }

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
.header-actions { display: flex; gap: 10px; }

/* 服务名称单元格：大 emoji + 名称/说明 */
.svc-cell { display: flex; align-items: center; gap: 12px; }
.svc-icon {
  font-size: 26px; line-height: 1;
  width: 44px; height: 44px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: #eff6ff; border-radius: 12px;
}
.svc-meta { min-width: 0; }
.svc-name { font-size: 15px; font-weight: 600; color: #1e293b; }
.svc-desc {
  margin-top: 2px; font-size: 12px; color: #94a3b8;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 220px;
}
.muted { color: #94a3b8; }

/* 空状态 */
.empty-state { padding: 28px 0; }
.empty-emoji { font-size: 46px; }
.empty-title { margin-top: 10px; font-size: 16px; font-weight: 600; color: #475569; }
.empty-tip { margin-top: 6px; font-size: 13px; color: #94a3b8; }
</style>
