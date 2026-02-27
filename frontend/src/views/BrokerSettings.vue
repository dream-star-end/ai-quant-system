<template>
  <div>
    <div class="page-header">
      <h1>交易账户管理</h1>
      <el-button type="primary" size="small" @click="showAdd = true" v-if="userStore.isLoggedIn">
        <el-icon><Plus /></el-icon> 添加交易账户
      </el-button>
    </div>

    <el-alert v-if="!userStore.isLoggedIn" title="请先登录" type="info" show-icon :closable="false" style="margin-bottom:16px;" />

    <!-- 安全提醒 -->
    <el-alert type="warning" show-icon :closable="true" style="margin-bottom:16px;" v-if="userStore.isLoggedIn">
      <template #title>
        <strong>安全提醒</strong>: API Key 将加密存储。建议在交易所端设置 <strong>IP 白名单</strong> 并仅开放 <strong>交易权限</strong>（不要开提币权限）。
        推荐先用 <strong>测试网 (Testnet)</strong> 验证功能。
      </template>
    </el-alert>

    <!-- 已有账户 -->
    <div v-for="acc in accounts" :key="acc.id" class="q-card" style="margin-bottom:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="display:flex;align-items:center;gap:8px;">
          <div :class="['conn-dot', acc.connection_status === 'connected' ? 'ok' : 'fail']"></div>
          <strong>{{ acc.name }}</strong>
          <el-tag size="small" :type="acc.is_testnet ? 'warning' : 'danger'" effect="dark">
            {{ acc.is_testnet ? '测试网' : '主网实盘' }}
          </el-tag>
          <el-tag size="small" effect="plain">{{ acc.broker_type }}</el-tag>
        </div>
        <div style="display:flex;gap:4px;">
          <el-button size="small" @click="testConn(acc)" :loading="acc._testing">测试连接</el-button>
          <el-button size="small" @click="fetchBalance(acc)" :loading="acc._loadingBal">查询余额</el-button>
          <el-button size="small" type="danger" text @click="deleteAccount(acc.id)">删除</el-button>
        </div>
      </div>
      <div v-if="acc._balance" class="grid-3" style="margin-top:12px;">
        <div class="stat-card" style="text-align:center;">
          <div class="label">总权益 (USDT)</div>
          <div class="value" style="font-size:18px;">${{ Number(acc._balance.total_equity).toLocaleString() }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">可用余额</div>
          <div class="value" style="font-size:18px;">${{ Number(acc._balance.available_balance).toLocaleString() }}</div>
        </div>
        <div class="stat-card" style="text-align:center;">
          <div class="label">持仓数</div>
          <div class="value" style="font-size:18px;">{{ acc._balance.positions?.length || 0 }}</div>
        </div>
      </div>
    </div>

    <el-empty v-if="!accounts.length && userStore.isLoggedIn" description="暂无交易账户" />

    <!-- 支持的交易所 -->
    <div class="q-card" style="margin-top:24px;">
      <div class="q-card-title"><el-icon><Connection /></el-icon> 支持的交易所/券商</div>
      <div class="grid-4">
        <div v-for="b in brokerTypes" :key="b.type" class="stat-card" style="text-align:center;cursor:pointer;" @click="quickAdd(b)">
          <div class="label" style="font-weight:600;">{{ b.name }}</div>
          <div style="display:flex;gap:4px;justify-content:center;margin-top:6px;">
            <el-tag v-for="f in b.features" :key="f" size="small" type="info" effect="plain">{{ f }}</el-tag>
          </div>
          <div v-if="b.category === 'stock'" style="font-size:11px;color:var(--q-orange);margin-top:4px;">待对接</div>
        </div>
      </div>
    </div>

    <!-- 实盘订单记录 -->
    <div class="q-card" style="margin-top:16px;" v-if="orders.length">
      <div class="q-card-title"><el-icon><List /></el-icon> 实盘订单记录</div>
      <el-table :data="orders" size="small" stripe>
        <el-table-column prop="symbol" label="标的" width="110" />
        <el-table-column label="方向" width="70">
          <template #default="{ row }">
            <el-tag :type="row.side === 'buy' ? 'success' : 'danger'" size="small" effect="dark">
              {{ row.side === 'buy' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="90" align="right" />
        <el-table-column label="成交价" width="100" align="right">
          <template #default="{ row }">{{ row.filled_price?.toFixed(2) || '--' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'filled' ? 'success' : row.status === 'failed' ? 'danger' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="80">
          <template #default="{ row }">{{ row.source === 'agent' ? 'AI Agent' : '手动' }}</template>
        </el-table-column>
        <el-table-column label="时间">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加账户 -->
    <el-dialog v-model="showAdd" title="添加交易账户" width="480px">
      <el-alert type="info" :closable="false" style="margin-bottom:16px;">
        API Key 请在交易所后台创建，建议仅开放「现货交易」权限并绑定 IP。
      </el-alert>
      <el-form label-position="top" size="small">
        <el-form-item label="账户名称">
          <el-input v-model="addForm.name" placeholder="如: 我的币安账户" />
        </el-form-item>
        <el-form-item label="交易所">
          <el-select v-model="addForm.broker_type" style="width:100%;">
            <el-option v-for="b in brokerTypes.filter(x => x.category === 'crypto')" :key="b.type" :label="b.name" :value="b.type" />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="addForm.api_key" placeholder="API Key" />
        </el-form-item>
        <el-form-item label="API Secret">
          <el-input v-model="addForm.api_secret" placeholder="API Secret" type="password" show-password />
        </el-form-item>
        <el-form-item label="Passphrase (OKX 需要)">
          <el-input v-model="addForm.passphrase" placeholder="仅 OKX 需要" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="addForm.is_testnet">使用测试网 (推荐先用测试网验证)</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="addAccount" :loading="adding">添加</el-button>
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
const accounts = ref([])
const orders = ref([])
const brokerTypes = ref([])
const showAdd = ref(false)
const adding = ref(false)

const addForm = ref({
  name: '', broker_type: 'binance', api_key: '', api_secret: '', passphrase: '', is_testnet: true,
})

async function loadAccounts() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.getBrokerAccounts()
    accounts.value = (res.data || []).map(a => ({ ...a, _testing: false, _loadingBal: false, _balance: null }))
  } catch(e) {}
}
async function loadOrders() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.getLiveOrders()
    orders.value = res.data || []
  } catch(e) {}
}
async function addAccount() {
  adding.value = true
  try {
    const res = await api.createBrokerAccount(addForm.value)
    if (res.success) { ElMessage.success('添加成功'); showAdd.value = false; loadAccounts() }
    else ElMessage.error(res.message)
  } catch(e) { ElMessage.error(e.message) }
  adding.value = false
}
async function deleteAccount(id) {
  try { await api.deleteBrokerAccount(id); loadAccounts() } catch(e) { ElMessage.error(e.message) }
}
async function testConn(acc) {
  acc._testing = true
  try {
    const res = await api.testBrokerConnection(acc.id)
    ElMessage[res.data?.connected ? 'success' : 'error'](res.message)
    loadAccounts()
  } catch(e) { ElMessage.error(e.message) }
  acc._testing = false
}
async function fetchBalance(acc) {
  acc._loadingBal = true
  try {
    const res = await api.getBrokerBalance(acc.id)
    if (res.success) acc._balance = res.data
    else ElMessage.error(res.message)
  } catch(e) { ElMessage.error(e.message) }
  acc._loadingBal = false
}
function quickAdd(b) {
  if (b.category === 'stock') { ElMessage.info('A股券商接口开发中，敬请期待'); return }
  addForm.value.broker_type = b.type
  addForm.value.name = `我的${b.name}账户`
  showAdd.value = true
}

onMounted(async () => {
  try {
    const res = await api.getSupportedBrokers()
    brokerTypes.value = res.data || []
  } catch {}
  loadAccounts()
  loadOrders()
})
</script>

<style scoped>
.conn-dot { width: 8px; height: 8px; border-radius: 50%; }
.conn-dot.ok { background: var(--q-green); }
.conn-dot.fail { background: var(--q-text-secondary); }
</style>
