<template>
  <div>
    <div class="page-header">
      <h1>策略回测</h1>
    </div>

    <!-- 回测参数 -->
    <div class="q-card">
      <div class="q-card-title"><el-icon><SetUp /></el-icon> 回测参数</div>
      <el-form :model="form" inline label-position="top" size="small">
        <el-form-item label="策略类型">
          <el-select v-model="form.strategy_type" style="width:140px;" @change="onStrategyChange">
            <el-option v-for="t in strategyTypes" :key="t.type" :label="t.name" :value="t.type" />
          </el-select>
        </el-form-item>
        <el-form-item label="交易标的">
          <el-input v-model="form.symbol" style="width:140px;" placeholder="如 600519.SS" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:140px;" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:140px;" />
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="form.initial_capital" :min="10000" :step="100000" style="width:140px;" />
        </el-form-item>
        <el-form-item label="手续费率">
          <el-input-number v-model="form.commission_rate" :min="0" :max="0.01" :step="0.0001" :precision="4" style="width:140px;" />
        </el-form-item>
      </el-form>

      <!-- 策略参数 -->
      <div v-if="currentStrategyType" style="margin-top:8px;">
        <el-divider content-position="left" style="--el-border-color:var(--q-border);--el-text-color-regular:var(--q-text-secondary);">策略参数</el-divider>
        <el-form inline size="small">
          <el-form-item v-for="(val, key) in form.params" :key="key" :label="paramLabels[key] || key">
            <el-input-number v-model="form.params[key]" :min="1" style="width:120px;" />
          </el-form-item>
        </el-form>
      </div>

      <el-button type="primary" @click="runBacktest" :loading="loading" style="margin-top:12px;">
        <el-icon><VideoPlay /></el-icon> 运行回测
      </el-button>
    </div>

    <!-- 回测结果 -->
    <template v-if="result">
      <!-- 指标卡片 -->
      <div class="grid-4" style="margin-top:16px;">
        <div class="stat-card" style="text-align:center;">
          <div class="label">总收益率</div>
          <div class="value" :class="result.total_return >= 0 ? 'price-up' : 'price-down'">
            {{ result.total_return }}%
          </div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">年化收益</div>
          <div class="value" :class="result.annual_return >= 0 ? 'price-up' : 'price-down'">
            {{ result.annual_return }}%
          </div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">夏普比率</div>
          <div class="value">{{ result.sharpe_ratio }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">最大回撤</div>
          <div class="value price-down">{{ result.max_drawdown }}%</div>
        </div>
      </div>
      <div class="grid-4" style="margin-top:8px;">
        <div class="stat-card" style="text-align:center;">
          <div class="label">胜率</div>
          <div class="value">{{ result.win_rate }}%</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">盈亏比</div>
          <div class="value">{{ result.profit_factor }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">总交易数</div>
          <div class="value">{{ result.total_trades }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">最终资产</div>
          <div class="value">{{ Number(result.final_value).toLocaleString() }}</div>
        </div>
      </div>

      <div class="grid-2" style="margin-top:16px;">
        <!-- 权益曲线 -->
        <div class="q-card">
          <div class="q-card-title"><el-icon><DataLine /></el-icon> 权益曲线</div>
          <v-chart :option="equityChartOpt" style="height:300px;" autoresize />
        </div>
        <!-- 回撤曲线 -->
        <div class="q-card">
          <div class="q-card-title"><el-icon><DataLine /></el-icon> 回撤曲线</div>
          <v-chart :option="drawdownChartOpt" style="height:300px;" autoresize />
        </div>
      </div>

      <!-- 交易明细 -->
      <div class="q-card" style="margin-top:16px;">
        <div class="q-card-title"><el-icon><List /></el-icon> 交易记录 ({{ result.trades?.length || 0 }})</div>
        <el-table :data="result.trades" size="small" stripe max-height="300">
          <el-table-column prop="date" label="日期" width="110" />
          <el-table-column label="方向" width="70">
            <template #default="{ row }">
              <el-tag :type="row.direction === 'buy' ? 'success' : 'danger'" size="small" effect="dark">
                {{ row.direction === 'buy' ? '买入' : '卖出' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="价格" width="100" align="right" />
          <el-table-column prop="quantity" label="数量" width="90" align="right" />
          <el-table-column label="盈亏" width="100" align="right">
            <template #default="{ row }">
              <span v-if="row.pnl != null" :class="row.pnl >= 0 ? 'price-up' : 'price-down'">
                {{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="信号" />
        </el-table>
      </div>

      <!-- DeepSeek AI 解读 -->
      <div class="q-card" style="margin-top:16px;">
        <div class="q-card-title" style="justify-content:space-between;">
          <div><el-icon><MagicStick /></el-icon> AI 回测解读</div>
          <el-button size="small" type="primary" @click="interpretBacktest" :loading="interpretLoading">
            <el-icon><MagicStick /></el-icon> DeepSeek 解读
          </el-button>
        </div>
        <div v-if="interpretation" style="line-height:1.8;font-size:14px;" v-html="renderMd(interpretation)"></div>
        <el-empty v-else description="点击按钮让 DeepSeek 解读回测结果" :image-size="48" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])
import api from '../services/api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const result = ref(null)
const strategyTypes = ref([])
const interpretLoading = ref(false)
const interpretation = ref('')

function renderMd(text) {
  if (!text) return ''
  return text
    .replace(/### (.*)/g, '<h4 style="margin:12px 0 6px;color:var(--q-blue);">$1</h4>')
    .replace(/## (.*)/g, '<h3 style="margin:16px 0 8px;color:var(--q-blue);">$1</h3>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code style="background:var(--q-bg);padding:2px 6px;border-radius:3px;">$1</code>')
    .replace(/^- (.*)/gm, '<li style="margin-left:16px;">$1</li>')
    .replace(/\n/g, '<br>')
}

async function interpretBacktest() {
  if (!result.value) return
  interpretLoading.value = true
  try {
    const res = await api.deepseekInterpretBacktest({
      strategy_type: form.value.strategy_type,
      params: form.value.params,
      symbol: form.value.symbol,
      result: {
        total_return: result.value.total_return,
        annual_return: result.value.annual_return,
        sharpe_ratio: result.value.sharpe_ratio,
        max_drawdown: result.value.max_drawdown,
        win_rate: result.value.win_rate,
        profit_factor: result.value.profit_factor,
        total_trades: result.value.total_trades,
        winning_trades: result.value.winning_trades,
        losing_trades: result.value.losing_trades,
        avg_win: result.value.avg_win,
        avg_loss: result.value.avg_loss,
      },
    })
    if (res.success) {
      interpretation.value = res.data.interpretation
    } else {
      ElMessage.error(res.message)
    }
  } catch(e) { ElMessage.error(e.message) }
  interpretLoading.value = false
}

const paramLabels = {
  fast_period: '快线周期', slow_period: '慢线周期', period: '周期',
  overbought: '超买线', oversold: '超卖线', signal_period: '信号线周期',
  num_std: '标准差倍数', lookback: '回看天数', k1: 'K1系数', k2: 'K2系数',
  entry_period: '入场周期', exit_period: '出场周期',
}

const form = ref({
  strategy_type: 'ma_cross',
  symbol: '600519.SS',
  start_date: '2024-01-01',
  end_date: '2025-12-31',
  initial_capital: 1000000,
  commission_rate: 0.001,
  slippage: 0.001,
  params: { fast_period: 5, slow_period: 20 },
})

const currentStrategyType = computed(() => strategyTypes.value.find(t => t.type === form.value.strategy_type))

function onStrategyChange() {
  const t = currentStrategyType.value
  if (t) form.value.params = { ...t.params }
}

async function runBacktest() {
  loading.value = true
  result.value = null
  try {
    const res = await api.runBacktest(form.value)
    if (res.success) {
      result.value = res.data
      ElMessage.success(`回测完成: 收益率 ${res.data.total_return}%`)
    } else {
      ElMessage.error(res.message)
    }
  } catch(e) {
    ElMessage.error(e.message)
  }
  loading.value = false
}

const equityChartOpt = computed(() => {
  if (!result.value?.equity_curve) return {}
  const ec = result.value.equity_curve
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ec.map(e => e.date), axisLabel: { color: '#8b949e' }, axisLine: { lineStyle: { color: '#30363d' } } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e' } },
    series: [{
      type: 'line', data: ec.map(e => e.value), smooth: true, symbol: 'none',
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(88,166,255,0.3)' }, { offset: 1, color: 'rgba(88,166,255,0.02)' }] } },
      lineStyle: { color: '#58a6ff', width: 2 },
    }],
  }
})

const drawdownChartOpt = computed(() => {
  if (!result.value?.drawdown_curve) return {}
  const dc = result.value.drawdown_curve
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>回撤: -${p[0].value}%` },
    xAxis: { type: 'category', data: dc.map(d => d.date), axisLabel: { color: '#8b949e' }, axisLine: { lineStyle: { color: '#30363d' } } },
    yAxis: { type: 'value', inverse: true, splitLine: { lineStyle: { color: '#21262d' } }, axisLabel: { color: '#8b949e', formatter: v => `-${v}%` } },
    series: [{
      type: 'line', data: dc.map(d => d.drawdown), smooth: true, symbol: 'none',
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(248,81,73,0.02)' }, { offset: 1, color: 'rgba(248,81,73,0.3)' }] } },
      lineStyle: { color: '#f85149', width: 2 },
    }],
  }
})

onMounted(async () => {
  try {
    const res = await api.getStrategyTypes()
    if (res.data) strategyTypes.value = res.data
  } catch(e) { console.error(e) }
})
</script>
