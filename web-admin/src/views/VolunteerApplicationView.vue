<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">志愿者审核</div>
        <div class="page-subtitle">线上申请的志愿者资格审核：查看/下载证件材料，安排线下面试，通过后自动开通账号。</div>
      </div>
      <el-button :loading="loading" @click="loadData">刷新</el-button>
    </div>

    <div class="card filter-card">
      <el-form :inline="true">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 160px" @change="loadData">
            <el-option v-for="s in STATUS" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div class="card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="username" label="申请账号" min-width="120" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="community" label="社区" min-width="140" show-overflow-tooltip />
        <el-table-column prop="skills" label="擅长技能" min-width="140" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" effect="dark">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="申请时间" width="170">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openDetail(row)">审核材料</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-state">
            <div class="empty-emoji">📝</div>
            <div class="empty-title">暂无志愿者申请</div>
            <div class="empty-tip">居民在 App 提交「申请成为志愿者」后会显示在这里</div>
          </div>
        </template>
      </el-table>
    </div>

    <el-dialog v-model="detailVisible" title="志愿者申请审核" width="720px">
      <template v-if="current">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="申请账号">{{ current.username }}</el-descriptions-item>
          <el-descriptions-item label="状态"><el-tag :type="statusTag(current.status)" effect="dark" size="small">{{ current.status_display }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="手机号">{{ current.phone || '—' }}</el-descriptions-item>
          <el-descriptions-item label="社区">{{ current.community || '—' }}</el-descriptions-item>
          <el-descriptions-item label="擅长技能">{{ current.skills || '—' }}</el-descriptions-item>
          <el-descriptions-item label="地址">{{ current.address || '—' }}</el-descriptions-item>
          <el-descriptions-item label="自我介绍" :span="2">{{ current.note || '—' }}</el-descriptions-item>
        </el-descriptions>

        <div class="cert-title">证件材料</div>
        <div class="cert-grid">
          <div class="cert-item" v-for="c in CERTS" :key="c.key">
            <div class="cert-label">{{ c.label }}</div>
            <template v-if="current[c.key]">
              <el-image :src="photoUrl(current[c.key])" :preview-src-list="allImages" fit="cover" class="cert-img" />
              <a :href="photoUrl(current[c.key])" target="_blank" download class="cert-dl">下载</a>
            </template>
            <div v-else class="cert-none">未上传</div>
          </div>
        </div>

        <el-input v-model="reviewNote" type="textarea" :rows="2" placeholder="审核意见（拒绝时建议填写原因）" style="margin-top: 14px" />
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="warning" plain :disabled="!canAct" @click="act('interview')">安排面试</el-button>
        <el-button type="danger" plain :disabled="!canAct" @click="act('reject')">拒绝</el-button>
        <el-button type="success" :disabled="!canAct" @click="act('approve')">通过并开通</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const STATUS = [
  { value: 'pending', label: '待审核' },
  { value: 'interviewing', label: '面试中' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已拒绝' }
]
const statusTag = s => ({ pending: 'warning', interviewing: 'primary', approved: 'success', rejected: 'info' }[s] || 'info')
const CERTS = [
  { key: 'id_card_front', label: '身份证正面' },
  { key: 'id_card_back', label: '身份证反面' },
  { key: 'skill_cert', label: '技能/资格证' },
  { key: 'health_cert', label: '健康证' },
  { key: 'profile_photo', label: '个人形象照' }
]

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/api\/?$/, '')
const photoUrl = p => (p && p.startsWith('http')) ? p : `${API_ORIGIN}${p}`
const fmt = v => v ? v.replace('T', ' ').slice(0, 19) : '-'

const loading = ref(false)
const items = ref([])
const filters = reactive({ status: '' })
const detailVisible = ref(false)
const current = ref(null)
const reviewNote = ref('')

const canAct = computed(() => current.value && !['approved', 'rejected'].includes(current.value.status))
const allImages = computed(() => current.value ? CERTS.map(c => current.value[c.key]).filter(Boolean).map(photoUrl) : [])

const loadData = async () => {
  loading.value = true
  try {
    const params = { page_size: 200 }
    if (filters.status) params.status = filters.status
    const data = await request.get('/volunteer-applications/', { params })
    items.value = Array.isArray(data) ? data : (data.results || [])
  } catch (e) { /* 拦截器提示 */ } finally { loading.value = false }
}

const openDetail = row => { current.value = row; reviewNote.value = row.review_note || ''; detailVisible.value = true }

const act = async type => {
  const labels = { interview: '面试', reject: '拒绝', approve: '通过' }
  try {
    const res = await request.post(`/volunteer-applications/${current.value.id}/${type}/`, { note: reviewNote.value })
    ElMessage.success(res.message || `已${labels[type]}`)
    detailVisible.value = false
    loadData()
  } catch (e) { /* 拦截器提示 */ }
}

onMounted(loadData)
</script>

<style scoped>
.filter-card { margin-bottom: 16px; }
.cert-title { margin: 18px 0 10px; font-size: 15px; font-weight: 700; color: #1e293b; }
.cert-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.cert-item { text-align: center; }
.cert-label { font-size: 12px; color: #64748b; margin-bottom: 6px; }
.cert-img { width: 100%; height: 96px; border-radius: 8px; border: 1px solid #eef2f7; }
.cert-dl { display: inline-block; margin-top: 4px; font-size: 12px; color: #2563eb; }
.cert-none { height: 96px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #cbd5e1; background: #f8fafc; border-radius: 8px; }
.empty-state { padding: 28px 0; }
.empty-emoji { font-size: 46px; }
.empty-title { margin-top: 10px; font-size: 16px; font-weight: 600; color: #475569; }
.empty-tip { margin-top: 6px; font-size: 13px; color: #94a3b8; }
</style>
