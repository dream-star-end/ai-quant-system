<template>
  <div>
    <div class="page-header">
      <h1>智能告警</h1>
      <el-button type="primary" size="small" @click="showCreate = true" v-if="userStore.isLoggedIn">
        <el-icon><Plus /></el-icon> 新建告警
      </el-button>
    </div>

    <el-alert v-if="!userStore.isLoggedIn" title="请先登录以使用告警功能" type="info" show-icon :closable="false" style="margin-bottom:16px;" />

    <div v-for="a in alerts" :key="a.id" class="q-card" style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <el-tag :type="alertTypeTag(a.alert_type)" size="small" effect="dark" style="margin-right:8px;">
          {{ alertTypeLabel(a.alert_type) }}
        </el-tag>
        <strong>{{ a.symbol || '全局' }}</strong>
        <span style="margin-left:8px;color:var(--q-text-secondary);">{{ a.message }}</span>
        <span v-if="a.condition_value" style="margin-left:8px;color:var(--q-blue);">
          条件值: {{ a.condition_value }}
        </span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <el-switch v-model="a.is_active" @change="toggleAlert(a)" />
        <el-tag v-if="a.is_triggered" type="success" size="small">已触发</el-tag>
        <el-button size="small" text type="danger" @click="deleteAlert(a.id)">删除</el-button>
      </div>
    </div>

    <el-empty v-if="!alerts.length && userStore.isLoggedIn" description="暂无告警" />

    <el-dialog v-model="showCreate" title="创建告警" width="420px">
      <el-form label-position="top" size="small">
        <el-form-item label="告警类型">
          <el-select v-model="newAlert.alert_type" style="width:100%;">
            <el-option label="价格上穿" value="price_above" />
            <el-option label="价格下穿" value="price_below" />
            <el-option label="涨跌幅" value="change_pct" />
            <el-option label="量能异动" value="volume_spike" />
            <el-option label="策略信号" value="strategy_signal" />
            <el-option label="风控警告" value="risk_warning" />
            <el-option label="回撤预警" value="drawdown" />
          </el-select>
        </el-form-item>
        <el-form-item label="标的代码">
          <el-input v-model="newAlert.symbol" placeholder="如 600519.SS" />
        </el-form-item>
        <el-form-item label="条件值">
          <el-input-number v-model="newAlert.condition_value" style="width:100%;" />
        </el-form-item>
        <el-form-item label="告警描述">
          <el-input v-model="newAlert.message" placeholder="当茅台价格超过2000时提醒" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createAlert">创建</el-button>
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
const alerts = ref([])
const showCreate = ref(false)
const newAlert = ref({ alert_type: 'price_above', symbol: '', condition_value: null, message: '' })

const alertTypeLabel = (t) => ({
  price_above: '价格上穿', price_below: '价格下穿', change_pct: '涨跌幅',
  volume_spike: '量能异动', strategy_signal: '策略信号', risk_warning: '风控警告', drawdown: '回撤预警',
}[t] || t)

const alertTypeTag = (t) => ({
  price_above: 'success', price_below: 'danger', change_pct: 'warning',
  strategy_signal: '', risk_warning: 'danger', drawdown: 'danger',
}[t] || 'info')

async function loadAlerts() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.getAlerts()
    alerts.value = res.data || []
  } catch(e) {}
}

async function createAlert() {
  try {
    await api.createAlert(newAlert.value)
    ElMessage.success('告警创建成功')
    showCreate.value = false
    loadAlerts()
  } catch(e) { ElMessage.error(e.message) }
}

async function deleteAlert(id) {
  try {
    await api.deleteAlert(id)
    alerts.value = alerts.value.filter(a => a.id !== id)
  } catch(e) { ElMessage.error(e.message) }
}

async function toggleAlert(a) {
  try { await api.toggleAlert(a.id) } catch(e) { ElMessage.error(e.message) }
}

onMounted(loadAlerts)
</script>
