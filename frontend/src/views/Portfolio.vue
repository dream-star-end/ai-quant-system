<template>
  <div>
    <div class="page-header">
      <h1>投资组合</h1>
      <el-button type="primary" size="small" @click="showCreateDialog = true" v-if="userStore.isLoggedIn">
        <el-icon><Plus /></el-icon> 新建组合
      </el-button>
    </div>

    <el-alert v-if="!userStore.isLoggedIn" title="请先登录以使用投资组合功能" type="info" show-icon :closable="false" style="margin-bottom:16px;">
      <el-button size="small" type="primary" @click="$router.push('/login')">去登录</el-button>
    </el-alert>

    <!-- 组合列表 -->
    <div v-for="pf in portfolios" :key="pf.id" class="q-card">
      <div class="q-card-title" style="justify-content:space-between;">
        <div>
          <el-tag size="small" :type="pf.is_paper ? 'warning' : 'danger'" effect="dark" style="margin-right:8px;">
            {{ pf.is_paper ? '模拟' : '实盘' }}
          </el-tag>
          {{ pf.name }}
        </div>
        <el-button size="small" text type="primary" @click="showTradeDialog(pf)">交易</el-button>
      </div>

      <!-- 概览 -->
      <div class="grid-4" style="margin-bottom:12px;">
        <div class="stat-card" style="text-align:center;">
          <div class="label">总资产</div>
          <div class="value" style="font-size:18px;">{{ Number(pf.current_value).toLocaleString() }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">现金</div>
          <div class="value" style="font-size:18px;">{{ Number(pf.cash_balance).toLocaleString() }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">总盈亏</div>
          <div class="value" :class="pf.total_pnl >= 0 ? 'price-up' : 'price-down'" style="font-size:18px;">
            {{ pf.total_pnl >= 0 ? '+' : '' }}{{ Number(pf.total_pnl).toLocaleString() }}
          </div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">收益率</div>
          <div class="value" :class="pf.total_pnl_pct >= 0 ? 'price-up' : 'price-down'" style="font-size:18px;">
            {{ pf.total_pnl_pct >= 0 ? '+' : '' }}{{ pf.total_pnl_pct?.toFixed(2) }}%
          </div>
        </div>
      </div>

      <!-- 持仓 -->
      <el-table v-if="pf.positions?.length" :data="pf.positions" size="small" stripe>
        <el-table-column prop="symbol" label="标的" width="120" />
        <el-table-column prop="quantity" label="持仓量" width="80" align="right" />
        <el-table-column label="成本价" width="90" align="right">
          <template #default="{ row }">{{ Number(row.avg_cost).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="现价" width="90" align="right">
          <template #default="{ row }">{{ Number(row.current_price).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="市值" width="110" align="right">
          <template #default="{ row }">{{ Number(row.market_value).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="浮盈亏" width="110" align="right">
          <template #default="{ row }">
            <span :class="row.unrealized_pnl >= 0 ? 'price-up' : 'price-down'">
              {{ row.unrealized_pnl >= 0 ? '+' : '' }}{{ Number(row.unrealized_pnl).toFixed(2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="止损/止盈" width="130" align="center">
          <template #default="{ row }">
            <span class="price-down">{{ row.stop_loss?.toFixed(2) || '--' }}</span>
            /
            <span class="price-up">{{ row.take_profit?.toFixed(2) || '--' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无持仓" :image-size="48" />
    </div>

    <el-empty v-if="!portfolios.length && userStore.isLoggedIn" description="暂无投资组合" />

    <!-- 创建组合对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建投资组合" width="420px">
      <el-form label-position="top" size="small">
        <el-form-item label="名称">
          <el-input v-model="newPortfolio.name" placeholder="如: 我的A股组合" />
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="newPortfolio.initial_capital" :min="10000" :step="100000" style="width:100%;" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newPortfolio.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createPortfolio">创建</el-button>
      </template>
    </el-dialog>

    <!-- 交易对话框 -->
    <el-dialog v-model="tradeDialogVisible" title="执行交易" width="420px">
      <el-form label-position="top" size="small">
        <el-form-item label="标的代码">
          <el-input v-model="tradeForm.symbol" placeholder="如 600519.SS 或 BTC/USDT" />
        </el-form-item>
        <el-form-item label="方向">
          <el-radio-group v-model="tradeForm.direction">
            <el-radio-button value="buy">买入</el-radio-button>
            <el-radio-button value="sell">卖出</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="tradeForm.quantity" :min="1" style="width:100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="tradeForm.note" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tradeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="executeTrade" :loading="tradeLoading">
          {{ tradeForm.direction === 'buy' ? '确认买入' : '确认卖出' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import api from '../services/api'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const portfolios = ref([])
const showCreateDialog = ref(false)
const tradeDialogVisible = ref(false)
const tradeLoading = ref(false)

const newPortfolio = ref({ name: '', initial_capital: 1000000, description: '', is_paper: true })
const tradeForm = ref({ portfolio_id: 0, symbol: '', direction: 'buy', quantity: 100, note: '' })

async function loadPortfolios() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.getPortfolios()
    portfolios.value = res.data || []
  } catch(e) { console.error(e) }
}

async function createPortfolio() {
  try {
    await api.createPortfolio(newPortfolio.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    loadPortfolios()
  } catch(e) { ElMessage.error(e.message) }
}

function showTradeDialog(pf) {
  tradeForm.value.portfolio_id = pf.id
  tradeDialogVisible.value = true
}

async function executeTrade() {
  tradeLoading.value = true
  try {
    const res = await api.executeTrade(tradeForm.value)
    if (res.success) {
      ElMessage.success(res.message)
      tradeDialogVisible.value = false
      loadPortfolios()
    } else {
      ElMessage.error(res.message)
    }
  } catch(e) { ElMessage.error(e.message) }
  tradeLoading.value = false
}

onMounted(loadPortfolios)
</script>
