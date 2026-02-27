<template>
  <div>
    <div class="page-header">
      <h1>AI Agent 自主交易</h1>
      <el-button type="primary" size="small" @click="showCreate = true" v-if="userStore.isLoggedIn">
        <el-icon><Plus /></el-icon> 创建 Agent
      </el-button>
    </div>

    <el-alert v-if="!userStore.isLoggedIn" title="请先登录以使用 AI Agent" type="info" show-icon :closable="false" style="margin-bottom:16px;">
      <el-button size="small" type="primary" @click="$router.push('/login')">去登录</el-button>
    </el-alert>

    <el-alert v-if="!deepseekOk && userStore.isLoggedIn" type="warning" show-icon :closable="false" style="margin-bottom:16px;">
      AI Agent 需要 DeepSeek 大模型支持，请在后端 .env 中配置 DEEPSEEK_API_KEY
    </el-alert>

    <!-- Agent 介绍 -->
    <div v-if="!agents.length && userStore.isLoggedIn" class="q-card" style="margin-bottom:16px;">
      <div class="q-card-title"><el-icon><Robot /></el-icon> 什么是 AI Agent？</div>
      <div style="line-height:2;font-size:14px;color:var(--q-text-secondary);">
        <p>AI Agent 是一个由 DeepSeek 大模型驱动的自主交易代理。它会：</p>
        <div class="grid-3" style="margin:16px 0;">
          <div class="stat-card" style="text-align:center;">
            <div style="font-size:28px;margin-bottom:8px;">🔍</div>
            <div class="label" style="font-weight:600;">自动分析</div>
            <div style="font-size:12px;color:var(--q-text-secondary);margin-top:4px;">实时获取行情，计算技术指标，AI 综合研判</div>
          </div>
          <div class="stat-card" style="text-align:center;">
            <div style="font-size:28px;margin-bottom:8px;">🧠</div>
            <div class="label" style="font-weight:600;">智能决策</div>
            <div style="font-size:12px;color:var(--q-text-secondary);margin-top:4px;">DeepSeek 大模型生成买/卖/持有决策</div>
          </div>
          <div class="stat-card" style="text-align:center;">
            <div style="font-size:28px;margin-bottom:8px;">⚡</div>
            <div class="label" style="font-weight:600;">自动执行</div>
            <div style="font-size:12px;color:var(--q-text-secondary);margin-top:4px;">风控校验后自动执行交易或等待审批</div>
          </div>
        </div>
        <p><strong>三种运行模式：</strong></p>
        <p>🟢 <strong>全自动 (autonomous)</strong> — AI 分析+决策+执行，全程无需人工干预（仅限模拟盘）</p>
        <p>🟡 <strong>审批模式 (approval)</strong> — AI 分析+决策，人工审批后执行</p>
        <p>🔵 <strong>观察模式 (observe)</strong> — AI 分析+决策，仅记录不执行，用于验证策略</p>
      </div>
    </div>

    <!-- Agent 列表 -->
    <div v-for="ag in agents" :key="ag.id" class="q-card" style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <div :class="['status-dot', ag.status]"></div>
          <strong style="font-size:16px;">{{ ag.name }}</strong>
          <el-tag :type="modeTag(ag.mode)" size="small" effect="dark">{{ modeLabel(ag.mode) }}</el-tag>
          <el-tag :type="statusTag(ag.status)" size="small">{{ statusLabel(ag.status) }}</el-tag>
        </div>
        <div style="display:flex;gap:4px;">
          <el-button v-if="ag.status !== 'running'" size="small" type="success" @click="startAgent(ag.id)" :disabled="!deepseekOk">
            <el-icon><VideoPlay /></el-icon> 启动
          </el-button>
          <el-button v-if="ag.status === 'running'" size="small" type="warning" @click="pauseAgent(ag.id)">
            <el-icon><VideoPause /></el-icon> 暂停
          </el-button>
          <el-button size="small" type="primary" @click="runCheck(ag)" :loading="ag._checking" :disabled="!deepseekOk">
            <el-icon><Refresh /></el-icon> 立即分析
          </el-button>
          <el-button size="small" type="danger" text @click="stopAgent(ag.id)">停止</el-button>
        </div>
      </div>

      <!-- 统计 -->
      <div class="grid-4" style="margin-bottom:12px;">
        <div class="stat-card" style="text-align:center;">
          <div class="label">总决策</div>
          <div class="value" style="font-size:18px;">{{ ag.total_decisions || 0 }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">总交易</div>
          <div class="value" style="font-size:18px;">{{ ag.total_trades || 0 }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">胜率</div>
          <div class="value" style="font-size:18px;">
            {{ ag.win_trades + ag.lose_trades > 0 ? ((ag.win_trades / (ag.win_trades + ag.lose_trades)) * 100).toFixed(0) : '--' }}%
          </div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">总盈亏</div>
          <div class="value" :class="(ag.total_pnl || 0) >= 0 ? 'price-up' : 'price-down'" style="font-size:18px;">
            {{ (ag.total_pnl || 0) >= 0 ? '+' : '' }}{{ (ag.total_pnl || 0).toFixed(0) }}
          </div>
        </div>
      </div>

      <!-- 配置摘要 -->
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">
        <el-tag v-for="s in (ag.symbols || [])" :key="s" size="small" effect="plain">{{ s }}</el-tag>
        <el-tag size="small" type="info" effect="plain">风险: {{ riskLabel(ag.risk_tolerance) }}</el-tag>
        <el-tag size="small" type="info" effect="plain">止损: {{ (ag.stop_loss_pct * 100).toFixed(0) }}%</el-tag>
        <el-tag size="small" type="info" effect="plain">止盈: {{ (ag.take_profit_pct * 100).toFixed(0) }}%</el-tag>
        <el-tag size="small" type="info" effect="plain">日限: {{ ag.max_trades_per_day }}笔</el-tag>
      </div>

      <!-- 待审批 -->
      <div v-if="ag._pending?.length" style="margin-bottom:12px;">
        <div style="font-size:13px;font-weight:600;color:var(--q-orange);margin-bottom:8px;">
          ⏳ 待审批决策 ({{ ag._pending.length }})
        </div>
        <div v-for="d in ag._pending" :key="d.id" style="display:flex;justify-content:space-between;align-items:center;padding:10px;background:var(--q-bg);border-radius:8px;margin-bottom:6px;">
          <div>
            <el-tag :type="d.action === 'buy' ? 'success' : 'danger'" size="small" effect="dark">
              {{ actionLabel(d.action) }}
            </el-tag>
            <strong style="margin:0 8px;">{{ d.symbol }}</strong>
            <span style="color:var(--q-text-secondary);font-size:13px;">
              {{ d.quantity }}股 @{{ d.price?.toFixed(2) }} | 置信度 {{ (d.confidence * 100).toFixed(0) }}%
            </span>
            <div style="font-size:12px;color:var(--q-text-secondary);margin-top:4px;">{{ d.reason }}</div>
          </div>
          <div style="display:flex;gap:4px;">
            <el-button size="small" type="success" @click="approve(d.id, ag)">通过</el-button>
            <el-button size="small" type="danger" plain @click="reject(d.id, ag)">驳回</el-button>
          </div>
        </div>
      </div>

      <!-- 最近决策 -->
      <el-collapse>
        <el-collapse-item title="决策日志">
          <div v-for="d in ag._decisions" :key="d.id" style="display:flex;justify-content:space-between;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--q-border);font-size:13px;">
            <div style="flex:1;">
              <el-tag :type="actionTag(d.action)" size="small" effect="dark" style="margin-right:4px;">{{ actionLabel(d.action) }}</el-tag>
              <strong>{{ d.symbol }}</strong>
              <span v-if="d.quantity" style="margin-left:6px;color:var(--q-text-secondary);">{{ d.quantity }}股 @{{ d.price?.toFixed(2) }}</span>
              <el-tag :type="decisionStatusTag(d.status)" size="small" effect="plain" style="margin-left:6px;">{{ decisionStatusLabel(d.status) }}</el-tag>
              <div style="color:var(--q-text-secondary);margin-top:2px;">{{ d.reason }}</div>
            </div>
            <div style="color:var(--q-text-secondary);white-space:nowrap;margin-left:8px;">
              {{ formatTime(d.created_at) }}
            </div>
          </div>
          <el-empty v-if="!ag._decisions?.length" description="暂无决策记录" :image-size="40" />
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 创建 Agent 对话框 -->
    <el-dialog v-model="showCreate" title="创建 AI Agent" width="520px">
      <el-form label-position="top" size="small">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如: 茅台智能交易" />
        </el-form-item>
        <el-form-item label="关联组合">
          <el-select v-model="form.portfolio_id" style="width:100%;">
            <el-option v-for="p in portfolios" :key="p.id" :label="`${p.name} (${p.is_paper ? '模拟' : '实盘'}) ¥${Number(p.current_value).toLocaleString()}`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="运行模式">
          <el-radio-group v-model="form.mode">
            <el-radio-button value="autonomous">🟢 全自动</el-radio-button>
            <el-radio-button value="approval">🟡 需审批</el-radio-button>
            <el-radio-button value="observe">🔵 仅观察</el-radio-button>
          </el-radio-group>
          <div style="font-size:12px;color:var(--q-text-secondary);margin-top:4px;">
            {{ { autonomous: '全自动: AI 自主分析+决策+执行，无需人工干预', approval: '审批模式: AI 生成决策，用户确认后执行', observe: '观察模式: AI 生成决策但不执行，用于策略验证' }[form.mode] }}
          </div>
        </el-form-item>
        <el-form-item label="监控标的 (逗号分隔)">
          <el-input v-model="symbolsInput" placeholder="600519.SS, BTC/USDT, 000300.SS" />
        </el-form-item>
        <el-divider content-position="left">风控参数</el-divider>
        <div class="grid-2">
          <el-form-item label="风险偏好">
            <el-select v-model="form.risk_tolerance" style="width:100%;">
              <el-option label="保守" value="low" />
              <el-option label="均衡" value="medium" />
              <el-option label="激进" value="high" />
            </el-select>
          </el-form-item>
          <el-form-item label="策略倾向">
            <el-select v-model="form.strategy_preference" style="width:100%;">
              <el-option label="保守 (低频)" value="conservative" />
              <el-option label="均衡" value="balanced" />
              <el-option label="激进 (高频)" value="aggressive" />
            </el-select>
          </el-form-item>
          <el-form-item label="单笔最大仓位 %">
            <el-slider v-model="positionPctUI" :min="5" :max="40" :step="5" show-stops />
          </el-form-item>
          <el-form-item label="日交易上限">
            <el-input-number v-model="form.max_trades_per_day" :min="1" :max="20" style="width:100%;" />
          </el-form-item>
          <el-form-item label="止损线 %">
            <el-input-number v-model="slPctUI" :min="1" :max="20" style="width:100%;" />
          </el-form-item>
          <el-form-item label="止盈线 %">
            <el-input-number v-model="tpPctUI" :min="5" :max="50" style="width:100%;" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createAgent" :loading="creating">创建 Agent</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import api from '../services/api'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const agents = ref([])
const portfolios = ref([])
const showCreate = ref(false)
const creating = ref(false)
const deepseekOk = ref(false)
const symbolsInput = ref('600519.SS, BTC/USDT')

const positionPctUI = ref(15)
const slPctUI = ref(5)
const tpPctUI = ref(15)

const form = ref({
  name: 'AI Agent',
  portfolio_id: null,
  mode: 'approval',
  symbols: [],
  risk_tolerance: 'medium',
  strategy_preference: 'balanced',
  max_trades_per_day: 5,
  max_position_pct: 0.15,
  stop_loss_pct: 0.05,
  take_profit_pct: 0.15,
})

const modeLabel = (m) => ({ autonomous: '全自动', approval: '需审批', observe: '仅观察' }[m] || m)
const modeTag = (m) => ({ autonomous: 'success', approval: 'warning', observe: 'info' }[m] || 'info')
const statusLabel = (s) => ({ running: '运行中', paused: '已暂停', stopped: '已停止', error: '异常' }[s] || s)
const statusTag = (s) => ({ running: 'success', paused: 'warning', stopped: 'info', error: 'danger' }[s] || 'info')
const riskLabel = (r) => ({ low: '保守', medium: '均衡', high: '激进' }[r] || r)
const actionLabel = (a) => ({ buy: '买入', sell: '卖出', hold: '持有', stop_loss: '止损', take_profit: '止盈', rebalance: '调仓' }[a] || a)
const actionTag = (a) => ({ buy: 'success', sell: 'danger', hold: 'info', stop_loss: 'danger', take_profit: 'success' }[a] || 'info')
const decisionStatusLabel = (s) => ({ pending: '待审批', approved: '已通过', rejected: '已驳回', executed: '已执行', expired: '已过期' }[s] || s)
const decisionStatusTag = (s) => ({ pending: 'warning', executed: 'success', rejected: 'danger', expired: 'info' }[s] || 'info')

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadAgents() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.getAgents()
    agents.value = (res.data || []).map(a => ({ ...a, _checking: false, _pending: [], _decisions: [] }))
    for (const ag of agents.value) {
      loadDecisions(ag)
      loadPending(ag)
    }
  } catch(e) { console.error(e) }
}

async function loadDecisions(ag) {
  try {
    const res = await api.getAgentDecisions(ag.id, 20)
    ag._decisions = res.data || []
  } catch(e) {}
}

async function loadPending(ag) {
  try {
    const res = await api.getAgentPending(ag.id)
    ag._pending = res.data || []
  } catch(e) {}
}

async function createAgent() {
  form.value.symbols = symbolsInput.value.split(',').map(s => s.trim()).filter(Boolean)
  form.value.max_position_pct = positionPctUI.value / 100
  form.value.stop_loss_pct = slPctUI.value / 100
  form.value.take_profit_pct = tpPctUI.value / 100
  creating.value = true
  try {
    const res = await api.createAgent(form.value)
    if (res.success) {
      ElMessage.success('Agent 创建成功')
      showCreate.value = false
      loadAgents()
    } else {
      ElMessage.error(res.message)
    }
  } catch(e) { ElMessage.error(e.message) }
  creating.value = false
}

async function startAgent(id) {
  try { await api.startAgent(id); ElMessage.success('Agent 已启动'); loadAgents() } catch(e) { ElMessage.error(e.message) }
}
async function pauseAgent(id) {
  try { await api.pauseAgent(id); ElMessage.success('Agent 已暂停'); loadAgents() } catch(e) { ElMessage.error(e.message) }
}
async function stopAgent(id) {
  try { await api.stopAgent(id); ElMessage.success('Agent 已停止'); loadAgents() } catch(e) { ElMessage.error(e.message) }
}

async function runCheck(ag) {
  ag._checking = true
  try {
    const res = await api.runAgentCheck(ag.id)
    if (res.success) {
      ElMessage.success(res.message)
      loadDecisions(ag)
      loadPending(ag)
      loadAgents()
    } else {
      ElMessage.error(res.message)
    }
  } catch(e) { ElMessage.error(e.message) }
  ag._checking = false
}

async function approve(decId, ag) {
  try {
    const res = await api.approveDecision(decId)
    if (res.success) { ElMessage.success('交易已执行'); loadDecisions(ag); loadPending(ag); loadAgents() }
    else ElMessage.error(res.message)
  } catch(e) { ElMessage.error(e.message) }
}
async function reject(decId, ag) {
  try {
    await api.rejectDecision(decId)
    ElMessage.success('已驳回')
    loadPending(ag)
    loadDecisions(ag)
  } catch(e) { ElMessage.error(e.message) }
}

async function loadPortfolios() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.getPortfolios()
    portfolios.value = res.data || []
    if (portfolios.value.length && !form.value.portfolio_id) {
      form.value.portfolio_id = portfolios.value[0].id
    }
  } catch(e) {}
}

onMounted(async () => {
  try {
    const res = await api.getDeepseekStatus()
    deepseekOk.value = res.data?.configured || false
  } catch { deepseekOk.value = false }
  loadPortfolios()
  loadAgents()
})
</script>

<style scoped>
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.running {
  background: var(--q-green);
  animation: pulse 2s infinite;
}
.status-dot.paused { background: var(--q-orange); }
.status-dot.stopped { background: var(--q-text-secondary); }
.status-dot.error { background: var(--q-red); }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
