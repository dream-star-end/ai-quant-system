<template>
  <div>
    <div class="page-header">
      <h1>量化投资仪表盘</h1>
      <div style="display:flex;align-items:center;gap:12px;">
        <el-tag :type="marketOpen ? 'success' : 'info'" effect="dark" round>
          {{ marketOpen ? '● 交易中' : '○ 休市' }}
        </el-tag>
        <el-button size="small" :icon="Refresh" circle @click="loadAll" :loading="loading" />
      </div>
    </div>

    <!-- 概览统计 -->
    <div class="grid-4" style="margin-bottom:20px;">
      <div class="stat-card">
        <div class="label">A股指数 (沪深300)</div>
        <div class="value" :class="stockIndex.change >= 0 ? 'price-up' : 'price-down'">
          {{ stockIndex.price || '--' }}
        </div>
        <div class="sub" :class="stockIndex.change >= 0 ? 'price-up' : 'price-down'">
          {{ stockIndex.change >= 0 ? '+' : '' }}{{ stockIndex.change_pct?.toFixed(2) || '0' }}%
        </div>
      </div>
      <div class="stat-card">
        <div class="label">BTC/USDT</div>
        <div class="value" :class="btcQuote.change_pct >= 0 ? 'price-up' : 'price-down'">
          ${{ btcQuote.price?.toLocaleString() || '--' }}
        </div>
        <div class="sub" :class="btcQuote.change_pct >= 0 ? 'price-up' : 'price-down'">
          {{ btcQuote.change_pct >= 0 ? '+' : '' }}{{ btcQuote.change_pct?.toFixed(2) || '0' }}%
        </div>
      </div>
      <div class="stat-card">
        <div class="label">ETH/USDT</div>
        <div class="value" :class="ethQuote.change_pct >= 0 ? 'price-up' : 'price-down'">
          ${{ ethQuote.price?.toLocaleString() || '--' }}
        </div>
        <div class="sub" :class="ethQuote.change_pct >= 0 ? 'price-up' : 'price-down'">
          {{ ethQuote.change_pct >= 0 ? '+' : '' }}{{ ethQuote.change_pct?.toFixed(2) || '0' }}%
        </div>
      </div>
      <div class="stat-card">
        <div class="label">AI 信号</div>
        <div class="value" :style="{ color: aiSignal.trend === 'bullish' ? 'var(--q-green)' : aiSignal.trend === 'bearish' ? 'var(--q-red)' : 'var(--q-orange)' }">
          {{ aiSignal.signal || '加载中' }}
        </div>
        <div class="sub price-neutral">
          置信度 {{ aiSignal.confidence?.toFixed(0) || '0' }}%
        </div>
      </div>
    </div>

    <div class="grid-2">
      <!-- A股行情 -->
      <div class="q-card">
        <div class="q-card-title">
          <el-icon><TrendCharts /></el-icon> A股热门
        </div>
        <el-table :data="stockQuotes" size="small" stripe style="width:100%" v-loading="loading">
          <el-table-column prop="name" label="名称" width="100" />
          <el-table-column prop="price" label="最新价" width="90" align="right">
            <template #default="{ row }">
              <span :class="row.change >= 0 ? 'price-up' : 'price-down'">{{ row.price?.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="涨跌幅" width="90" align="right">
            <template #default="{ row }">
              <span :class="row.change_pct >= 0 ? 'price-up' : 'price-down'">
                {{ row.change_pct >= 0 ? '+' : '' }}{{ row.change_pct?.toFixed(2) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="$router.push(`/analysis/${row.symbol}`)">分析</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 加密货币行情 -->
      <div class="q-card">
        <div class="q-card-title">
          <el-icon><Coin /></el-icon> 加密货币
        </div>
        <el-table :data="cryptoQuotes" size="small" stripe style="width:100%" v-loading="loading">
          <el-table-column prop="symbol" label="交易对" width="120" />
          <el-table-column label="价格" width="120" align="right">
            <template #default="{ row }">
              <span :class="row.change_pct >= 0 ? 'price-up' : 'price-down'">${{ Number(row.price)?.toLocaleString(undefined, {maximumFractionDigits:2}) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="24h涨跌" width="90" align="right">
            <template #default="{ row }">
              <span :class="row.change_pct >= 0 ? 'price-up' : 'price-down'">
                {{ row.change_pct >= 0 ? '+' : '' }}{{ Number(row.change_pct)?.toFixed(2) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="$router.push(`/analysis/${encodeURIComponent(row.symbol)}?asset=crypto`)">分析</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- AI分析摘要 -->
    <div class="q-card" style="margin-top:16px;">
      <div class="q-card-title">
        <el-icon><MagicStick /></el-icon> AI 市场分析摘要
      </div>
      <div v-if="aiSignal.analysis_summary" style="line-height:1.8;color:var(--q-text-secondary);font-size:14px;">
        {{ aiSignal.analysis_summary }}
      </div>
      <div v-if="aiSignal.signals" style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
        <el-tag
          v-for="s in aiSignal.signals"
          :key="s.name"
          :type="s.type === 'bullish' ? 'success' : s.type === 'bearish' ? 'danger' : 'info'"
          effect="dark"
          size="small"
        >
          {{ s.name }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import api from '../services/api'

const loading = ref(false)
const marketOpen = ref(false)
const stockIndex = ref({})
const btcQuote = ref({})
const ethQuote = ref({})
const aiSignal = ref({})
const stockQuotes = ref([])
const cryptoQuotes = ref([])

async function loadAll() {
  loading.value = true
  try {
    const [stocks, cryptos] = await Promise.allSettled([
      api.getStockBatch(),
      api.getCryptoBatch(),
    ])
    if (stocks.status === 'fulfilled') {
      stockQuotes.value = stocks.value.data || []
      const idx = stockQuotes.value.find(s => s.symbol === '000300.SS')
      if (idx) stockIndex.value = idx
    }
    if (cryptos.status === 'fulfilled') {
      cryptoQuotes.value = cryptos.value.data || []
      const btc = cryptoQuotes.value.find(c => c.symbol === 'BTC/USDT')
      const eth = cryptoQuotes.value.find(c => c.symbol === 'ETH/USDT')
      if (btc) btcQuote.value = btc
      if (eth) ethQuote.value = eth
    }
  } catch(e) { console.error(e) }

  try {
    const ai = await api.getPredict('000300.SS', 'stock')
    if (ai.data) aiSignal.value = ai.data
  } catch(e) { console.error(e) }

  const hour = new Date().getHours()
  marketOpen.value = hour >= 9 && hour < 15

  loading.value = false
}

onMounted(loadAll)
</script>
