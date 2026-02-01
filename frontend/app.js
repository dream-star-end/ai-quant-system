// Frontend App
const API_BASE = 'http://localhost:8000/api';

async function fetchStocks() {
    const response = await fetch(`${API_BASE}/stocks/quote/000300.SS`);
    return await response.json();
}

async function fetchCrypto() {
    const response = await fetch(`${API_BASE}/crypto/price/BTC/USDT`);
    return await response.json();
}

async function initDashboard() {
    // 加载股票数据
    try {
        const stockData = await fetchStocks();
        const stockDiv = document.getElementById('stock-summary');
        if (stockData.price) {
            const changeClass = stockData.change >= 0 ? 'up' : 'down';
            stockDiv.innerHTML = `
                <div class="stock-item">
                    <span>上证指数</span>
                    <span class="${changeClass}">
                        ${stockData.price.toFixed(2)} 
                        (${stockData.change >= 0 ? '+' : ''}${stockData.change_pct.toFixed(2)}%)
                    </span>
                </div>
            `;
        } else {
            stockDiv.innerHTML = '暂时无法获取数据';
        }
    } catch (e) {
        document.getElementById('stock-summary').innerHTML = '后端服务未启动';
    }
    
    // 加载加密货币数据
    try {
        const cryptoData = await fetchCrypto();
        const cryptoDiv = document.getElementById('crypto-summary');
        if (cryptoData.price) {
            const changeClass = cryptoData.change_pct >= 0 ? 'up' : 'down';
            cryptoDiv.innerHTML = `
                <div class="crypto-item">
                    <span>BTC/USDT</span>
                    <span class="${changeClass}">
                        $${cryptoData.price.toFixed(2)}
                        (${cryptoData.change_pct >= 0 ? '+' : ''}${cryptoData.change_pct.toFixed(2)}%)
                    </span>
                </div>
            `;
        } else {
            cryptoDiv.innerHTML = '暂时无法获取数据';
        }
    } catch (e) {
        document.getElementById('crypto-summary').innerHTML = '后端服务未启动';
    }
    
    // AI 预测占位
    document.getElementById('ai-prediction').innerHTML = `
        <div class="prediction-item">
            <p>🤖 AI 模型训练中...</p>
            <small>启动后端服务后自动开始分析</small>
        </div>
    `;
}

// 初始化
document.addEventListener('DOMContentLoaded', initDashboard);
