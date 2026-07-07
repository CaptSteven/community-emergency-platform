<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">🏅 志愿排行榜</div>
        <div class="page-subtitle">按志愿积分排名，激励更多邻里守望与温暖互助。</div>
      </div>
      <el-button :loading="loading" @click="loadData">刷新</el-button>
    </div>

    <!-- 前三名领奖台 -->
    <div v-if="podium.length" class="podium">
      <div
        v-for="p in podium"
        :key="p.rank"
        class="podium-card"
        :class="`rank-${p.rank}`"
      >
        <div class="medal">{{ MEDALS[p.rank] }}</div>
        <div class="podium-name">{{ p.volunteer }}</div>
        <div class="podium-points">
          <span class="pts-num">{{ p.points || 0 }}</span>
          <span class="pts-unit">积分</span>
        </div>
        <div class="podium-meta">
          <span>⏱ {{ formatMinutes(p.total_minutes) }}</span>
          <span>✅ {{ p.completed_count || 0 }} 单</span>
        </div>
      </div>
    </div>

    <div class="card">
      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="名次" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.rank <= 3" class="rank-medal">{{ MEDALS[row.rank] }}</span>
            <span v-else class="rank-num">{{ row.rank }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="volunteer" label="志愿者" min-width="140" />
        <el-table-column label="志愿积分" width="130" align="center">
          <template #default="{ row }">
            <span class="points-badge">🏅 {{ row.points || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="总时长" min-width="130">
          <template #default="{ row }">{{ formatMinutes(row.total_minutes) }}</template>
        </el-table-column>
        <el-table-column label="本周时长" min-width="130">
          <template #default="{ row }">
            <span :class="{ 'muted': !row.week_minutes }">{{ formatMinutes(row.week_minutes) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="完成单数" width="110" align="center">
          <template #default="{ row }">{{ row.completed_count || 0 }}</template>
        </el-table-column>
        <template #empty>
          <div class="empty-state">
            <div class="empty-emoji">🌱</div>
            <div class="empty-title">暂无志愿服务记录</div>
            <div class="empty-tip">志愿者完成服务工单后，积分与时长会自动累计到这里</div>
          </div>
        </template>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import request from '../api/request'

const MEDALS = { 1: '🥇', 2: '🥈', 3: '🥉' }

const loading = ref(false)
const list = ref([])

// 前三名（有数据才展示领奖台）
const podium = computed(() => list.value.filter(item => item.rank <= 3))

// 分钟转“x小时y分”
const formatMinutes = mins => {
  const total = Number(mins) || 0
  if (total <= 0) return '0 分钟'
  const h = Math.floor(total / 60)
  const m = total % 60
  if (h && m) return `${h} 小时 ${m} 分`
  if (h) return `${h} 小时`
  return `${m} 分钟`
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await request.get('/analytics/volunteer-leaderboard/')
    list.value = Array.isArray(data) ? data : (data?.results || [])
  } catch (e) {
    /* 拦截器提示 */
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 20px; }
.page-header {
  display: flex; justify-content: space-between; align-items: flex-end;
  margin-bottom: 18px;
}
.page-title { font-size: 22px; font-weight: 700; color: #1e293b; }
.page-subtitle { margin-top: 6px; font-size: 13px; color: #64748b; }

.card {
  background: #fff; border-radius: 16px; padding: 12px 16px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, .06);
  border: 1px solid rgba(226, 232, 240, .7);
}

/* 领奖台：金银铜三张卡片 */
.podium {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.podium-card {
  background: #fff; border-radius: 16px; padding: 22px 16px;
  text-align: center;
  box-shadow: 0 8px 24px rgba(15, 23, 42, .08);
  border: 1px solid rgba(226, 232, 240, .7);
  position: relative; overflow: hidden;
  transition: transform .2s ease;
}
.podium-card:hover { transform: translateY(-3px); }
.podium-card.rank-1 { background: linear-gradient(160deg, #fffbeb, #fef3c7); border-color: #fcd34d; }
.podium-card.rank-2 { background: linear-gradient(160deg, #f8fafc, #f1f5f9); border-color: #cbd5e1; }
.podium-card.rank-3 { background: linear-gradient(160deg, #fff7ed, #ffedd5); border-color: #fdba74; }
/* 冠军略微抬高，强化第一 */
.podium-card.rank-1 { transform: translateY(-6px); }
.podium-card.rank-1:hover { transform: translateY(-9px); }

.medal { font-size: 44px; line-height: 1; }
.podium-name { margin-top: 8px; font-size: 17px; font-weight: 700; color: #1e293b; }
.podium-points { margin-top: 10px; }
.pts-num { font-size: 30px; font-weight: 800; color: #b45309; }
.pts-unit { margin-left: 4px; font-size: 13px; color: #92400e; }
.podium-meta {
  margin-top: 12px; display: flex; justify-content: center; gap: 16px;
  font-size: 13px; color: #64748b;
}

/* 表格名次 */
.rank-medal { font-size: 22px; }
.rank-num { font-size: 15px; font-weight: 700; color: #94a3b8; }

/* 积分徽章 */
.points-badge {
  display: inline-flex; align-items: center; gap: 2px;
  padding: 3px 12px; border-radius: 10px;
  font-weight: 700; font-size: 14px; color: #b45309;
  background: linear-gradient(135deg, #fef3c7, #fde68a);
}
.muted { color: #94a3b8; }

/* 空状态 */
.empty-state { padding: 34px 0; text-align: center; }
.empty-emoji { font-size: 46px; }
.empty-title { margin-top: 10px; font-size: 16px; font-weight: 600; color: #475569; }
.empty-tip { margin-top: 6px; font-size: 13px; color: #94a3b8; }
</style>
