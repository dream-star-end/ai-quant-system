<template>
  <div>
    <div class="page-header">
      <h1>策略管理</h1>
      <el-button type="primary" size="small" @click="showCreate = true" v-if="userStore.isLoggedIn">
        <el-icon><Plus /></el-icon> 创建策略
      </el-button>
    </div>

    <el-alert v-if="!userStore.isLoggedIn" title="请先登录以使用策略管理功能" type="info" show-icon :closable="false" style="margin-bottom:16px;" />

    <!-- 策略类型介绍 -->
    <div class="q-card" style="margin-bottom:16px;">
      <div class="q-card-title"><el-icon><InfoFilled /></el-icon> 内置策略一览</div>
      <div class="grid-3">
        <div v-for="t in strategyTypes" :key="t.type" class="stat-card" style="cursor:pointer;" @click="quickBacktest(t)">
          <div class="label" style="font-weight:600;color:var(--q-blue);font-size:13px;">{{ t.name }}</div>
          <div style="font-size:12px;color:var(--q-text-secondary);margin-top:4px;">{{ t.description }}</div>
        </div>
      </div>
    </div>

    <!-- 策略列表 -->
    <div v-for="s in strategies" :key="s.id" class="q-card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <el-tag size="small" :type="statusType(s.status)" effect="dark" style="margin-right:8px;">{{ statusLabel(s.status) }}</el-tag>
          <strong>{{ s.name }}</strong>
          <span style="color:var(--q-text-secondary);margin-left:8px;font-size:12px;">{{ s.description }}</span>
        </div>
        <div style="display:flex;gap:4px;">
          <el-button size="small" text type="primary" @click="goBacktest(s)">回测</el-button>
          <el-button size="small" text type="danger" @click="deleteStrategy(s.id)">删除</el-button>
        </div>
      </div>
      <div v-if="s.backtest_return != null" class="grid-4" style="margin-top:12px;">
        <div class="stat-card" style="text-align:center;"><div class="label">收益率</div><div class="value" :class="s.backtest_return >= 0 ? 'price-up' : 'price-down'" style="font-size:16px;">{{ s.backtest_return }}%</div></div>
        <div class="stat-card" style="text-align:center;"><div class="label">夏普比率</div><div class="value" style="font-size:16px;">{{ s.backtest_sharpe }}</div></div>
        <div class="stat-card" style="text-align:center;"><div class="label">最大回撤</div><div class="value price-down" style="font-size:16px;">{{ s.backtest_max_drawdown }}%</div></div>
        <div class="stat-card" style="text-align:center;"><div class="label">胜率</div><div class="value" style="font-size:16px;">{{ s.backtest_win_rate }}%</div></div>
      </div>
    </div>

    <el-empty v-if="!strategies.length && userStore.isLoggedIn" description="暂无策略，点击上方按钮创建" />

    <!-- 创建策略对话框 -->
    <el-dialog v-model="showCreate" title="创建策略" width="500px">
      <el-form label-position="top" size="small">
        <el-form-item label="策略名称">
          <el-input v-model="newStrategy.name" placeholder="如: 茅台均线金叉策略" />
        </el-form-item>
        <el-form-item label="策略类型">
          <el-select v-model="newStrategy.strategy_type" style="width:100%;">
            <el-option v-for="t in strategyTypes" :key="t.type" :label="t.name" :value="t.type" />
          </el-select>
        </el-form-item>
        <el-form-item label="交易标的 (逗号分隔)">
          <el-input v-model="symbolsInput" placeholder="600519.SS, BTC/USDT" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newStrategy.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createStrategy">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import api from '../services/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const strategies = ref([])
const strategyTypes = ref([])
const showCreate = ref(false)
const symbolsInput = ref('')
const newStrategy = ref({ name: '', strategy_type: 'ma_cross', description: '', symbols: [] })

const statusType = (s) => ({ draft: 'info', active: 'success', paused: 'warning', archived: '' }[s] || 'info')
const statusLabel = (s) => ({ draft: '草稿', active: '运行中', paused: '已暂停', archived: '已归档' }[s] || s)

async function loadStrategies() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.getStrategies()
    strategies.value = res.data || []
  } catch(e) { console.error(e) }
}

async function createStrategy() {
  newStrategy.value.symbols = symbolsInput.value.split(',').map(s => s.trim()).filter(Boolean)
  try {
    await api.createStrategy(newStrategy.value)
    ElMessage.success('策略创建成功')
    showCreate.value = false
    loadStrategies()
  } catch(e) { ElMessage.error(e.message) }
}

async function deleteStrategy(id) {
  try {
    await api.deleteStrategy(id)
    ElMessage.success('已删除')
    loadStrategies()
  } catch(e) { ElMessage.error(e.message) }
}

function goBacktest(s) {
  router.push({ path: '/backtest', query: { type: s.strategy_type, symbol: s.symbols?.[0] || '' } })
}

function quickBacktest(t) {
  router.push({ path: '/backtest', query: { type: t.type } })
}

onMounted(async () => {
  try {
    const res = await api.getStrategyTypes()
    if (res.data) strategyTypes.value = res.data
  } catch(e) {}
  loadStrategies()
})
</script>
