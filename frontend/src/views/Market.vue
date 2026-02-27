<template>
  <div>
    <div class="page-header">
      <h1>行情中心</h1>
      <el-radio-group v-model="activeTab" size="small">
        <el-radio-button value="stock">A股</el-radio-button>
        <el-radio-button value="crypto">加密货币</el-radio-button>
      </el-radio-group>
    </div>

    <!-- K线图 -->
    <div class="q-card" style="min-height:420px;">
      <div class="q-card-title" style="justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:8px;">
          <el-icon><TrendCharts /></el-icon>
          {{ selectedSymbol }} K线图
        </div>
        <div style="display:flex;gap:8px;">
          <el-select v-model="selectedSymbol" size="small" style="width:160px;" @change="loadChart">
            <el-option v-for="s in currentSymbols" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
          <el-select v-model="period" size="small" style="width:80px;" @change="loadChart">
            <el-option label="1月" value="1mo" />
            <el-option label="3月" value="3mo" />
            <el-option label="6月" value="6mo" />
            <el-option label="1年" value="1y" />
            <el-option label="2年" value="2y" />
          </el-select>
        </div>
      </div>
      <v-chart :option="chartOption" style="height:360px;" autoresize v-if="chartReady" />
      <div v-else style="display:flex;align-items:center;justify-content:center;height:300px;">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      </div>
    </div>

    <!-- 行情列表 -->
    <div class="q-card">
      <el-table :data="quotes" size="small" stripe v-loading="loading" @row-click="onRowClick" style="cursor:pointer;">
        <el-table-column prop="nameOrSymbol" label="名称/代码" width="140" />
        <el-table-column label="最新价" width="120" align="right">
          <template #default="{ row }">
            <span :class="priceClass(row)">{{ formatPrice(row.price) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌幅" width="100" align="right">
          <template #default="{ row }">
            <span :class="priceClass(row)">
              {{ (row.change_pct >= 0 ? '+' : '') + Number(row.change_pct).toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="最高" width="100" align="right">
          <template #default="{ row }">{{ formatPrice(row.high) }}</template>
        </el-table-column>
        <el-table-column label="最低" width="100" align="right">
          <template #default="{ row }">{{ formatPrice(row.low) }}</template>
        </el-table-column>
        <el-table-column label="成交量" align="right">
          <template #default="{ row }">{{ formatVol(row.volume) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click.stop="goAnalysis(row)">AI分析</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CandlestickChart, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

import api from '../services/api'

const router = useRouter()
const activeTab = ref('stock')
const loading = ref(false)
const chartReady = ref(false)
const period = ref('6mo')
const quotes = ref([])

const stockSymbols = [
  { label: '沪深300', value: '000300.SS' },
  { label: '贵州茅台', value: '600519.SS' },
  { label: '宁德时代', value: '300750.SZ' },
  { label: '招商银行', value: '600036.SS' },
  { label: '比亚迪', value: '002594.SZ' },
]
const cryptoSymbols = [
  { label: 'BTC/USDT', value: 'BTC/USDT' },
  { label: 'ETH/USDT', value: 'ETH/USDT' },
  { label: 'SOL/USDT', value: 'SOL/USDT' },
  { label: 'BNB/USDT', value: 'BNB/USDT' },
]

const currentSymbols = computed(() => activeTab.value === 'stock' ? stockSymbols : cryptoSymbols)
const selectedSymbol = ref('000300.SS')

const chartOption = ref({})

async function loadQuotes() {
  loading.value = true
  try {
    if (activeTab.value === 'stock') {
      const res = await api.getStockBatch()
      quotes.value = (res.data || []).map(q => ({ ...q, nameOrSymbol: q.name || q.symbol }))
    } else {
      const res = await api.getCryptoBatch()
      quotes.value = (res.data || []).map(q => ({ ...q, nameOrSymbol: q.symbol }))
    }
  } catch(e) { console.error(e) }
  loading.value = false
}

async function loadChart() {
  chartReady.value = false
  try {
    let res
    if (activeTab.value === 'crypto') {
      res = await api.getCryptoHistory(selectedSymbol.value, '1d', 200)
    } else {
      res = await api.getStockHistory(selectedSymbol.value, period.value)
    }
    const d = res.data
    if (!d || !d.candles?.length) return

    const dates = d.candles.map(c => c.date)
    const ohlc = d.candles.map(c => [c.open, c.close, c.low, c.high])
    const volumes = d.candles.map(c => c.volume)
    const ind = d.indicators || {}

    chartOption.value = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { data: ['K线', 'MA5', 'MA20', '成交量'], textStyle: { color: '#8b949e' }, top: 0 },
      grid: [
        { left: '8%', right: '3%', top: '8%', height: '55%' },
        { left: '8%', right: '3%', top: '72%', height: '18%' },
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, axisLabel: { color: '#8b949e' }, axisLine: { lineStyle: { color: '#30363d' } } },
        { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#30363d' } } },
      ],
      yAxis: [
        { scale: true, gridIndex: 0, splitLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e' } },
        { scale: true, gridIndex: 1, splitLine: { show: false }, axisLabel: { color: '#8b949e' } },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
        { type: 'slider', xAxisIndex: [0, 1], start: 60, end: 100, height: 20, bottom: 4, borderColor: '#30363d', fillerColor: 'rgba(88,166,255,0.1)', textStyle: { color: '#8b949e' } },
      ],
      series: [
        {
          name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
          itemStyle: { color: '#3fb950', color0: '#f85149', borderColor: '#3fb950', borderColor0: '#f85149' },
        },
        ...(ind.ma5?.length ? [{ name: 'MA5', type: 'line', data: ind.ma5, smooth: true, lineStyle: { width: 1 }, symbol: 'none', xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: '#d29922' } }] : []),
        ...(ind.ma20?.length ? [{ name: 'MA20', type: 'line', data: ind.ma20, smooth: true, lineStyle: { width: 1 }, symbol: 'none', xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: '#bc8cff' } }] : []),
        {
          name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
          itemStyle: { color: (p) => ohlc[p.dataIndex]?.[1] >= ohlc[p.dataIndex]?.[0] ? '#3fb95066' : '#f8514966' },
        },
      ],
    }
    chartReady.value = true
  } catch(e) { console.error(e) }
}

function priceClass(row) {
  const c = row.change_pct ?? row.change ?? 0
  return c >= 0 ? 'price-up' : 'price-down'
}
function formatPrice(p) {
  if (!p) return '--'
  return Number(p) > 100 ? Number(p).toLocaleString(undefined, { maximumFractionDigits: 2 }) : Number(p).toFixed(2)
}
function formatVol(v) {
  if (!v) return '--'
  if (v > 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v > 1e4) return (v / 1e4).toFixed(1) + '万'
  return Number(v).toLocaleString()
}
function onRowClick(row) {
  selectedSymbol.value = row.symbol
  loadChart()
}
function goAnalysis(row) {
  const asset = activeTab.value === 'crypto' ? 'crypto' : 'stock'
  router.push(`/analysis/${encodeURIComponent(row.symbol)}?asset=${asset}`)
}

watch(activeTab, () => {
  selectedSymbol.value = currentSymbols.value[0].value
  loadQuotes()
  loadChart()
})

onMounted(() => {
  loadQuotes()
  loadChart()
})
</script>
