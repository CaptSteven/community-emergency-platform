<template>
  <div class="page">
    <div class="page-header">
      <h2 style="margin: 0">用户管理</h2>
      <el-button type="primary" @click="openCreate">新建用户</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="志愿者账号仅由管理员在此线下开通；居民可在 App 自助注册。"
      style="margin-bottom: 16px"
    />

    <el-card shadow="never" style="margin-bottom: 16px">
      <el-form :inline="true">
        <el-form-item label="角色">
          <el-select v-model="filters.role" placeholder="全部角色" clearable style="width: 160px">
            <el-option label="居民" value="resident" />
            <el-option label="志愿者" value="volunteer" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="filters.search" placeholder="搜索用户名" clearable style="width: 200px" @keyup.enter="loadData" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)">{{ row.role_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="community" label="社区" min-width="120" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'volunteer'" :type="row.is_available ? 'success' : 'warning'">
              {{ row.is_available ? '空闲' : '忙碌' }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="志愿积分" width="100">
          <template #default="{ row }">
            <!-- 仅志愿者展示积分，醒目徽章 -->
            <span v-if="row.role === 'volunteer'" class="points-badge">🏅 {{ row.points || 0 }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="认证" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'volunteer'" :type="row.is_verified ? 'success' : 'info'" effect="dark" size="small">
              {{ row.is_verified ? '已认证' : '未认证' }}
            </el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="本月取消" width="100">
          <template #default="{ row }">
            <span
              v-if="row.role === 'volunteer'"
              :style="{ color: (row.monthly_cancel_count || 0) > 5 ? '#F56C6C' : '#606266', fontWeight: (row.monthly_cancel_count || 0) > 5 ? 700 : 400 }"
            >
              {{ row.monthly_cancel_count || 0 }}<span v-if="(row.monthly_cancel_count || 0) > 5"> ⚠</span>
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.role === 'volunteer'" size="small" :type="row.is_verified ? 'info' : 'success'" plain @click="toggleVerify(row)">
              {{ row.is_verified ? '取消认证' : '认证' }}
            </el-button>
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="removeUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '新建用户'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="editing" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item :label="editing ? '重置密码' : '密码'" :required="!editing">
          <el-input v-model="form.password" type="password" show-password :placeholder="editing ? '留空则不修改' : '至少 6 位'" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="居民" value="resident" />
            <el-option label="志愿者" value="volunteer" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" placeholder="联系电话" />
        </el-form-item>
        <el-form-item label="社区">
          <el-input v-model="form.community" placeholder="所属社区" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" placeholder="居住地址" />
        </el-form-item>
        <el-form-item v-if="form.role === 'volunteer'" label="擅长技能">
          <el-input v-model="form.skills" placeholder="如 医疗、搬运、救援" />
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

const loading = ref(false)
const saving = ref(false)
const users = ref([])
const dialogVisible = ref(false)
const editing = ref(false)
const editId = ref(null)

const filters = reactive({ role: '', search: '' })
const form = reactive({ username: '', password: '', role: 'volunteer', phone: '', community: '', address: '', skills: '' })

const roleTagType = role => ({ admin: 'danger', volunteer: 'primary', resident: 'info' }[role] || 'info')

const toggleVerify = async row => {
  try {
    const res = await request.post(`/users/${row.id}/verify/`)
    ElMessage.success(res.message || '已更新认证状态')
    loadData()
  } catch (e) { /* 拦截器提示 */ }
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.role) params.role = filters.role
    if (filters.search) params.search = filters.search
    const data = await request.get('/users/', { params })
    users.value = Array.isArray(data) ? data : (data.results || [])
  } catch (e) {
    // 请求拦截器已统一提示
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.role = ''
  filters.search = ''
  loadData()
}

const openCreate = () => {
  editing.value = false
  editId.value = null
  Object.assign(form, { username: '', password: '', role: 'volunteer', phone: '', community: '', address: '', skills: '' })
  dialogVisible.value = true
}

const openEdit = row => {
  editing.value = true
  editId.value = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    role: row.role,
    phone: row.phone || '',
    community: row.community || '',
    address: row.address || '',
    skills: row.skills || ''
  })
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.username) {
    ElMessage.warning('请填写用户名')
    return
  }
  if (!editing.value && (!form.password || form.password.length < 6)) {
    ElMessage.warning('新建用户密码至少 6 位')
    return
  }
  saving.value = true
  try {
    const payload = {
      username: form.username,
      role: form.role,
      phone: form.phone,
      community: form.community,
      address: form.address,
      skills: form.skills
    }
    if (form.password) payload.password = form.password

    if (editing.value) {
      await request.patch(`/users/${editId.value}/`, payload)
      ElMessage.success('已更新用户')
    } else {
      await request.post('/users/', payload)
      ElMessage.success('已创建用户')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    // 拦截器提示
  } finally {
    saving.value = false
  }
}

const removeUser = async row => {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '提示', {
      type: 'warning',
      confirmButtonText: '确定删除'
    })
  } catch (e) {
    return
  }
  try {
    await request.delete(`/users/${row.id}/`)
    ElMessage.success('已删除')
    loadData()
  } catch (e) {
    // 拦截器提示
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

/* 志愿积分徽章：温暖金色，醒目易识别 */
.points-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 13px;
  color: #b45309;
  background: linear-gradient(135deg, #fef3c7, #fde68a);
}

.muted {
  color: #94a3b8;
}
</style>
