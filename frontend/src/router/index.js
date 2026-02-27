import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '仪表盘', icon: 'Odometer' } },
  { path: '/market', name: 'Market', component: () => import('../views/Market.vue'), meta: { title: '行情中心', icon: 'TrendCharts' } },
  { path: '/analysis/:symbol?', name: 'Analysis', component: () => import('../views/Analysis.vue'), meta: { title: 'AI分析', icon: 'MagicStick' } },
  { path: '/backtest', name: 'Backtest', component: () => import('../views/Backtest.vue'), meta: { title: '策略回测', icon: 'DataLine' } },
  { path: '/portfolio', name: 'Portfolio', component: () => import('../views/Portfolio.vue'), meta: { title: '投资组合', icon: 'Wallet' } },
  { path: '/strategy', name: 'Strategy', component: () => import('../views/StrategyView.vue'), meta: { title: '策略管理', icon: 'SetUp' } },
  { path: '/agent', name: 'Agent', component: () => import('../views/Agent.vue'), meta: { title: 'AI Agent', icon: 'Cpu' } },
  { path: '/broker', name: 'Broker', component: () => import('../views/BrokerSettings.vue'), meta: { title: '实盘交易', icon: 'Connection' } },
  { path: '/alerts', name: 'Alerts', component: () => import('../views/Alerts.vue'), meta: { title: '智能告警', icon: 'Bell' } },
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录', hide: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
export { routes }
