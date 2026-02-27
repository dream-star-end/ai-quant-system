import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.response?.data?.error || err.message
    return Promise.reject(new Error(msg))
  }
)

export default {
  // Auth
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),

  // Stocks
  getStockQuote: (symbol) => api.get(`/stocks/quote/${symbol}`),
  getStockHistory: (symbol, period = '6mo') => api.get(`/stocks/history/${symbol}?period=${period}`),
  getStockBatch: () => api.get('/stocks/batch'),
  getStockSymbols: () => api.get('/stocks/symbols'),

  // Crypto
  getCryptoPrice: (symbol) => api.get(`/crypto/price/${symbol}`),
  getCryptoHistory: (symbol, timeframe = '1d', limit = 200) =>
    api.get(`/crypto/history/${symbol}?timeframe=${timeframe}&limit=${limit}`),
  getCryptoBatch: () => api.get('/crypto/batch'),
  getCryptoSymbols: () => api.get('/crypto/symbols'),

  // Analysis
  getPredict: (symbol, asset = 'stock') => api.get(`/analysis/predict/${symbol}?asset_type=${asset}`),
  getRecommend: (symbol, asset = 'stock') => api.get(`/analysis/recommend/${symbol}?asset_type=${asset}`),
  getRisk: (symbol, asset = 'stock') => api.get(`/analysis/risk/${symbol}?asset_type=${asset}`),
  getIndicators: (symbol, asset = 'stock') => api.get(`/analysis/indicators/${symbol}?asset_type=${asset}`),

  // Backtest
  runBacktest: (data) => api.post('/backtest/run/guest', data),
  runBacktestAuth: (data) => api.post('/backtest/run', data),

  // Strategies
  getStrategies: () => api.get('/strategies/'),
  createStrategy: (data) => api.post('/strategies/', data),
  updateStrategy: (id, data) => api.put(`/strategies/${id}`, data),
  deleteStrategy: (id) => api.delete(`/strategies/${id}`),
  getStrategyTypes: () => api.get('/strategies/types/list'),

  // Portfolio
  getPortfolios: () => api.get('/portfolio/'),
  createPortfolio: (data) => api.post('/portfolio/', data),
  executeTrade: (data) => api.post('/portfolio/trade', data),
  getTrades: (portfolioId) => api.get(`/portfolio/${portfolioId}/trades`),
  getPositions: (portfolioId) => api.get(`/portfolio/${portfolioId}/positions`),

  // Alerts
  getAlerts: () => api.get('/alerts/'),
  createAlert: (data) => api.post('/alerts/', data),
  deleteAlert: (id) => api.delete(`/alerts/${id}`),
  toggleAlert: (id) => api.put(`/alerts/${id}/toggle`),

  // Watchlist
  getWatchlists: () => api.get('/watchlist/'),
  createWatchlist: (data) => api.post('/watchlist/', data),
  addToWatchlist: (id, symbol) => api.put(`/watchlist/${id}/add/${symbol}`),
  removeFromWatchlist: (id, symbol) => api.put(`/watchlist/${id}/remove/${symbol}`),
}
