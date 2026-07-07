<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">服务计划管理</div>
        <div class="page-subtitle">为居民（如独居老人）建立周期性上门服务计划；点击「生成本周排班」后，系统按技能匹配并轮流把到期计划派给志愿者。</div>
      </div>
      <div class="header-actions">
        <el-button type="success" plain :loading="generating" @click="generateVisits">生成本周排班</el-button>
        <el-button type="primary" @click="openCreate">新建服务计划</el-button>
      </div>
    </div>

    <div class="card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="resident_name" label="受益居民" min-width="110" />
        <el-table-column label="服务" min-width="180">
          <template #default="{ row }">
            <div class="svc-cell">
              <span class="svc-icon">{{ row.service_type_icon || '🛎️' }}</span>
              <span class="svc-name">{{ row.service_type_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="frequency_display" label="周期" width="90" />
        <el-table-column prop="preferred_weekday_display" label="首选日" width="90" />
        <el-table-column prop="preferred_time" label="时段" width="90" />
        <el-table-column prop="address" label="服务地址" min-width="150" show-overflow-tooltip />
        <el-table-column prop="last_generated_date" label="最近排班" width="110">
          <template #default="{ row }">
            <span v-if="row.last_generated_date">{{ row.last_generated_date }}</span>
            <span v-else class="muted">未排班</span>
          </template>
        </el-table-column>
        <!-- 循环组：多名志愿者轮流上门 -->
        <el-table-column label="循环组（轮换）" min-width="260">
          <template #default="{ row }">
            <div v-if="row.rotation_group && row.rotation_group.length" class="rot-group">
              <div class="rot-tags">
                <!-- is_next 高亮标出下一位轮到谁 -->
                <el-tag
                  v-for="m in row.rotation_group"
                  :key="m.id"
                  :type="m.is_next ? 'warning' : 'info'"
                  :effect="m.is_next ? 'dark' : 'plain'"
                  size="small"
                  round
                  class="rot-tag"
                >
                  {{ m.order }}. {{ m.username }}
                </el-tag>
              </div>
              <div class="rot-next">当前进行到：<b>{{ nextName(row) }}</b></div>
            </div>
            <div v-else class="rot-empty">
              <span class="rot-empty-icon">🔁</span>
              <span class="muted">未编排，将按负载自动派单</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <!-- 生效/暂停 快捷切换（PATCH is_active） -->
            <el-switch
              v-model="row.is_active"
              :loading="row._toggling"
              active-text="生效"
              inactive-text="暂停"
              inline-prompt
              style="--el-switch-on-color: #16a34a; --el-switch-off-color: #94a3b8"
              @change="val => toggleActive(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="generateNow(row)">立即排班</el-button>
            <!-- 编排循环组：按技能 + 距离智能筛选 -->
            <el-button size="small" type="success" plain :loading="row._building" @click="buildGroup(row)">
              {{ row.rotation_group && row.rotation_group.length ? '重排循环组' : '编排循环组' }}
            </el-button>
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-state">
            <div class="empty-emoji">📅</div>
            <div class="empty-title">还没有服务计划</div>
            <div class="empty-tip">点击「新建服务计划」，为需要长期照护的居民安排周期性上门服务</div>
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
import { buildPageParams, unwrapPaginated } from '../utils/pagination'

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

// 分页（兼容后端返回数组或 {count,results}）
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const blank = () => ({
  resident: null, service_type: null, frequency: 'weekly',
  preferred_weekday: 0, preferred_time: '', address: '', note: '', is_active: true
})
const form = reactive(blank())

const loadData = async () => {
  loading.value = true
  try {
    const data = await request.get('/service-subscriptions/', { params: { ...buildPageParams(pagination) } })
    const page = unwrapPaginated(data)
    items.value = page.list
    pagination.total = page.total
  } catch (e) { /* 拦截器提示 */ } finally { loading.value = false }
}

const handleSizeChange = size => { pagination.pageSize = size; pagination.page = 1; loadData() }
const handlePageChange = page => { pagination.page = page; loadData() }

const loadRefs = async () => {
  try {
    const [r, t] = await Promise.all([
      request.get('/users/', { params: { role: 'resident', page_size: 200 } }),
      request.get('/service-types/', { params: { is_active: true, page_size: 200 } })
    ])
    residents.value = unwrapPaginated(r).list
    types.value = unwrapPaginated(t).list
  } catch (e) { /* 拦截器提示 */ }
}

const onTypeChange = id => {
  const t = types.value.find(x => x.id === id)
  if (t && !editing.value) form.frequency = t.default_frequency
}

// 生效/暂停 快捷切换（PATCH is_active）
const toggleActive = async (row, val) => {
  row._toggling = true
  try {
    await request.patch(`/service-subscriptions/${row.id}/`, { is_active: val })
    ElMessage.success(val ? '计划已生效' : '计划已暂停')
  } catch (e) {
    row.is_active = !val   // 失败回滚
  } finally {
    row._toggling = false
  }
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

// 循环组中「下一位轮到谁」的名字（is_next）
const nextName = row => {
  const next = (row.rotation_group || []).find(m => m.is_next)
  return next ? next.username : '—'
}

// 编排循环组：后端按技能 + 距离智能筛选生成轮换序列
const buildGroup = async row => {
  row._building = true
  try {
    const res = await request.post(`/service-subscriptions/${row.id}/build-group/`)
    ElMessage.success(res.message || '循环组已编排')
    loadData()
  } catch (e) { /* 拦截器提示 */ } finally { row._building = false }
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
.header-actions { display: flex; gap: 10px; }

/* 服务单元格：大 emoji + 名称 */
.svc-cell { display: flex; align-items: center; gap: 10px; }
.svc-icon {
  font-size: 22px; line-height: 1;
  width: 38px; height: 38px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: #f0fdf4; border-radius: 10px;
}
.svc-name { font-size: 15px; font-weight: 600; color: #1e293b; }
.muted { color: #94a3b8; }

/* 循环组 */
.rot-group { display: flex; flex-direction: column; gap: 6px; }
.rot-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.rot-tag { font-weight: 600; }
.rot-next { font-size: 12px; color: #64748b; }
.rot-next b { color: #F59E0B; }
.rot-empty { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.rot-empty-icon { font-size: 15px; }

/* 空状态 */
.empty-state { padding: 28px 0; }
.empty-emoji { font-size: 46px; }
.empty-title { margin-top: 10px; font-size: 16px; font-weight: 600; color: #475569; }
.empty-tip { margin-top: 6px; font-size: 13px; color: #94a3b8; }
</style>
