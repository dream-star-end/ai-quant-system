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
        <el-button size="small" @click="generateReport" :loading="reportLoading" :disabled="!deepseekOk">
          <el-icon><MagicStick /></el-icon> DeepSeek 深度报告
        </el-button>
      </div>
    </div>

    <!-- DeepSeek 状态 -->
    <el-alert v-if="deepseekChecked && !deepseekOk" type="warning" show-icon :closable="false" style="margin-bottom:16px;">
      <template #title>
        DeepSeek 未配置 — 请在后端 <code>.env</code> 中设置 <code>DEEPSEEK_API_KEY</code> 以启用 AI 大模型深度分析、智能问答、报告生成等功能。
        当前使用规则引擎进行基础分析。
      </template>
    </el-alert>

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
          <div class="sub" :style="{color: risk.risk_score?.score >= 60 ? 'var(--q-green)' : 'var(--q-red)'}">{{ risk.risk_score?.level }}</div>
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

    <!-- DeepSeek 深度分析报告 -->
    <div v-if="report" class="q-card" style="margin-top:16px;">
      <div class="q-card-title" style="justify-content:space-between;">
        <div><el-icon><Document /></el-icon> DeepSeek 深度分析报告</div>
        <el-tag type="success" size="small" effect="dark">Powered by DeepSeek</el-tag>
      </div>
      <div class="report-content" v-html="renderMarkdown(report)"></div>
    </div>

    <!-- DeepSeek 对话 -->
    <div class="q-card" style="margin-top:16px;">
      <div class="q-card-title">
        <el-icon><ChatDotRound /></el-icon> AI 投资助手
        <el-tag v-if="deepseekOk" type="success" size="small" effect="plain" style="margin-left:8px;">DeepSeek 在线</el-tag>
        <el-tag v-else type="info" size="small" effect="plain" style="margin-left:8px;">未配置</el-tag>
      </div>
      <div ref="chatBox" style="max-height:400px;overflow-y:auto;margin-bottom:12px;">
        <div v-for="(msg, i) in chatMessages" :key="i" style="margin-bottom:12px;">
          <div v-if="msg.role === 'user'" style="display:flex;justify-content:flex-end;">
            <div style="background:rgba(88,166,255,0.15);border-radius:12px 12px 2px 12px;padding:10px 14px;max-width:80%;font-size:14px;">
              {{ msg.content }}
            </div>
          </div>
          <div v-else style="display:flex;justify-content:flex-start;">
            <div style="background:var(--q-bg-hover);border-radius:12px 12px 12px 2px;padding:10px 14px;max-width:85%;font-size:14px;line-height:1.8;" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
        <div v-if="chatLoading" style="display:flex;align-items:center;gap:8px;color:var(--q-text-secondary);font-size:13px;">
          <el-icon class="is-loading"><Loading /></el-icon> DeepSeek 正在思考...
        </div>
      </div>
      <div style="display:flex;gap:8px;">
        <el-input
          v-model="chatInput"
          placeholder="问我任何投资问题... 如：茅台现在适合买入吗？BTC会不会继续涨？"
          @keyup.enter="sendChat"
          :disabled="!deepseekOk"
        />
        <el-button type="primary" @click="sendChat" :loading="chatLoading" :disabled="!deepseekOk || !chatInput.trim()">
          发送
        </el-button>
      </div>
    </div>

    <el-empty v-if="!result && !loading" description="输入股票代码或加密货币对，开始 AI 分析" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const reportLoading = ref(false)
const chatLoading = ref(false)
const symbol = ref(route.params.symbol ? decodeURIComponent(route.params.symbol) : '000300.SS')
const assetType = ref(route.query.asset || 'stock')
const result = ref(null)
const recommendation = ref(null)
const risk = ref(null)
const report = ref('')
const deepseekOk = ref(false)
const deepseekChecked = ref(false)

const chatMessages = ref([])
const chatInput = ref('')
const chatBox = ref(null)

const trendColor = computed(() => {
  if (!result.value) return '#8b949e'
  return result.value.trend === 'bullish' ? '#3fb950' : result.value.trend === 'bearish' ? '#f85149' : '#d29922'
})
const trendText = computed(() => {
  if (!result.value) return ''
  return { bullish: '看涨', bearish: '看跌', neutral: '震荡' }[result.value.trend] || ''
})

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/### (.*)/g, '<h4 style="margin:12px 0 6px;color:var(--q-blue);">$1</h4>')
    .replace(/## (.*)/g, '<h3 style="margin:16px 0 8px;color:var(--q-blue);">$1</h3>')
    .replace(/# (.*)/g, '<h2 style="margin:16px 0 8px;color:var(--q-blue);">$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code style="background:var(--q-bg);padding:2px 6px;border-radius:3px;font-size:13px;">$1</code>')
    .replace(/^- (.*)/gm, '<li style="margin-left:16px;">$1</li>')
    .replace(/^\d+\. (.*)/gm, '<li style="margin-left:16px;">$1</li>')
    .replace(/\n/g, '<br>')
}

async function analyze() {
  loading.value = true
  result.value = null
  recommendation.value = null
  risk.value = null
  report.value = ''

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

async function generateReport() {
  reportLoading.value = true
  try {
    const res = await api.getDeepseekReport(symbol.value, assetType.value)
    if (res.success) {
      report.value = res.data.report
      ElMessage.success('分析报告生成完成')
    } else {
      ElMessage.error(res.message)
    }
  } catch(e) {
    ElMessage.error(e.message)
  }
  reportLoading.value = false
}

async function sendChat() {
  const msg = chatInput.value.trim()
  if (!msg) return
  chatMessages.value.push({ role: 'user', content: msg })
  chatInput.value = ''
  chatLoading.value = true
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight

  try {
    const res = await api.deepseekChat({ message: msg, symbol: symbol.value, asset_type: assetType.value })
    if (res.success) {
      chatMessages.value.push({ role: 'assistant', content: res.data.reply })
    } else {
      chatMessages.value.push({ role: 'assistant', content: `抱歉，分析失败: ${res.message}` })
    }
  } catch(e) {
    chatMessages.value.push({ role: 'assistant', content: `调用失败: ${e.message}` })
  }
  chatLoading.value = false
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

async function checkDeepseek() {
  try {
    const res = await api.getDeepseekStatus()
    deepseekOk.value = res.data?.configured || false
  } catch { deepseekOk.value = false }
  deepseekChecked.value = true
}

onMounted(() => {
  checkDeepseek()
  if (symbol.value) analyze()
})
</script>

<style scoped>
.report-content {
  line-height: 1.8;
  font-size: 14px;
  color: var(--q-text);
}
.report-content h2, .report-content h3, .report-content h4 {
  color: var(--q-blue);
}
</style>
