<template>
  <div>
    <div class="page-header">
      <h1>AI 智能分析</h1>
      <div style="display:flex;gap:8px;">
        <el-select v-model="assetType" size="small" style="width:100px;">
          <el-option label="A股" value="stock" />
          <el-option label="加密货币" value="crypto" />
        </el-select>
        <el-input v-model="symbol" size="small" style="width:160px;" placeholder="输入代码" @keyup.enter="analyze" />
        <el-button type="primary" size="small" @click="analyze" :loading="loading">开始分析</el-button>
      </div>
    </div>

    <div v-if="result" class="grid-2" style="margin-bottom:16px;">
      <!-- 信号概览 -->
      <div class="q-card">
        <div class="q-card-title"><el-icon><MagicStick /></el-icon> 综合信号</div>
        <div style="text-align:center;padding:16px 0;">
          <div style="font-size:48px;font-weight:800;" :style="{ color: trendColor }">
            {{ result.signal }}
          </div>
          <div style="margin-top:8px;color:var(--q-text-secondary);">
            趋势: {{ trendText }} · 置信度 {{ result.confidence }}%
          </div>
          <el-progress :percentage="result.confidence" :color="trendColor" :stroke-width="8" style="margin-top:16px;" />
        </div>
        <div style="display:flex;justify-content:space-around;margin-top:12px;">
          <div class="stat-card" style="flex:1;margin:0 4px;text-align:center;">
            <div class="label">多头分数</div>
            <div class="value price-up" style="font-size:18px;">{{ result.bull_score }}</div>
          </div>
          <div class="stat-card" style="flex:1;margin:0 4px;text-align:center;">
            <div class="label">空头分数</div>
            <div class="value price-down" style="font-size:18px;">{{ result.bear_score }}</div>
          </div>
          <div class="stat-card" style="flex:1;margin:0 4px;text-align:center;">
            <div class="label">当前价格</div>
            <div class="value" style="font-size:18px;">{{ result.current_price }}</div>
          </div>
        </div>
      </div>

      <!-- 信号明细 -->
      <div class="q-card">
        <div class="q-card-title"><el-icon><List /></el-icon> 信号明细</div>
        <div v-for="s in result.signals" :key="s.name" style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--q-border);">
          <span>{{ s.name }}</span>
          <el-tag :type="s.type === 'bullish' ? 'success' : s.type === 'bearish' ? 'danger' : 'info'" size="small" effect="dark">
            {{ s.type === 'bullish' ? '看涨' : s.type === 'bearish' ? '看跌' : '中性' }}
          </el-tag>
        </div>
        <div v-if="result.analysis_summary" style="margin-top:16px;line-height:1.8;color:var(--q-text-secondary);font-size:13px;">
          {{ result.analysis_summary }}
        </div>
      </div>
    </div>

    <!-- 推荐 -->
    <div v-if="recommendation" class="q-card">
      <div class="q-card-title"><el-icon><Promotion /></el-icon> 智能推荐</div>
      <div class="grid-4">
        <div class="stat-card" style="text-align:center;">
          <div class="label">操作建议</div>
          <div class="value" style="font-size:16px;" :style="{color: recommendation.action.includes('买') ? 'var(--q-green)' : recommendation.action.includes('卖') ? 'var(--q-red)' : 'var(--q-orange)'}">
            {{ recommendation.action }}
          </div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">建议仓位</div>
          <div class="value" style="font-size:16px;">{{ recommendation.position_size }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">止损价</div>
          <div class="value price-down" style="font-size:16px;">{{ recommendation.stop_loss || '--' }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">止盈价</div>
          <div class="value price-up" style="font-size:16px;">{{ recommendation.take_profit || '--' }}</div>
        </div>
      </div>
      <div v-if="recommendation.reasoning?.length" style="margin-top:12px;display:flex;gap:6px;flex-wrap:wrap;">
        <el-tag v-for="r in recommendation.reasoning" :key="r" type="warning" effect="plain" size="small">{{ r }}</el-tag>
      </div>
    </div>

    <!-- 风险分析 -->
    <div v-if="risk" class="q-card" style="margin-top:16px;">
      <div class="q-card-title"><el-icon><Warning /></el-icon> 风险评估</div>
      <div class="grid-4">
        <div class="stat-card" style="text-align:center;">
          <div class="label">风险评分</div>
          <div class="value" style="font-size:22px;">{{ risk.risk_score?.score }}/100</div>
          <div class="sub" :style="{color: risk.risk_score?.score >= 60 ? 'var(--q-green)' : 'var(--q-red)'}">
            {{ risk.risk_score?.level }}
          </div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">夏普比率</div>
          <div class="value" style="font-size:18px;">{{ risk.metrics?.sharpe_ratio }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">最大回撤</div>
          <div class="value price-down" style="font-size:18px;">{{ risk.metrics?.max_drawdown }}%</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">年化波动率</div>
          <div class="value" style="font-size:18px;">{{ risk.metrics?.volatility }}%</div>
        </div>
      </div>
    </div>

    <el-empty v-if="!result && !loading" description="输入股票代码或加密货币对，开始 AI 分析" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const loading = ref(false)
const symbol = ref(route.params.symbol || '000300.SS')
const assetType = ref(route.query.asset || 'stock')
const result = ref(null)
const recommendation = ref(null)
const risk = ref(null)

const trendColor = computed(() => {
  if (!result.value) return '#8b949e'
  return result.value.trend === 'bullish' ? '#3fb950' : result.value.trend === 'bearish' ? '#f85149' : '#d29922'
})
const trendText = computed(() => {
  if (!result.value) return ''
  return { bullish: '看涨', bearish: '看跌', neutral: '震荡' }[result.value.trend] || ''
})

async function analyze() {
  loading.value = true
  result.value = null
  recommendation.value = null
  risk.value = null

  try {
    const [pred, rec, rsk] = await Promise.allSettled([
      api.getPredict(symbol.value, assetType.value),
      api.getRecommend(symbol.value, assetType.value),
      api.getRisk(symbol.value, assetType.value),
    ])
    if (pred.status === 'fulfilled' && pred.value.success) result.value = pred.value.data
    if (rec.status === 'fulfilled' && rec.value.success) recommendation.value = rec.value.data
    if (rsk.status === 'fulfilled' && rsk.value.success) risk.value = rsk.value.data
  } catch(e) { console.error(e) }
  loading.value = false
}

onMounted(() => { if (symbol.value) analyze() })
</script>
