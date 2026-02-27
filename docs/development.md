# 开发文档

## 环境要求

- Python 3.10+
- Node.js 18+
- Supabase 项目 (免费即可)

## 环境配置

```bash
# 克隆仓库
git clone https://github.com/dream-star-end/ai-quant-system.git
cd ai-quant-system

# Python 虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 Supabase 配置
```

## 后端开发

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 目录结构

```
backend/
├── main.py          # FastAPI 入口 + 路由注册
├── config.py        # 环境配置
├── database.py      # Supabase 客户端
├── core/
│   ├── logger.py    # 日志
│   ├── exceptions.py # 自定义异常
│   └── security.py  # JWT + 密码
├── routers/         # API 路由 (9个)
├── services/        # 业务逻辑
├── schemas/         # Pydantic 模型
└── models/          # 数据库模型定义 (参考)
```

### 添加新路由

1. 在 `routers/` 下创建新文件
2. 创建 `APIRouter` 实例
3. 在 `main.py` 中注册路由

### 添加新策略

在 `services/backtest_engine.py` 中:
1. 创建信号生成函数 `_xxx_signals(df, params)`
2. 注册到 `STRATEGY_GENERATORS` 字典

## 前端开发

```bash
cd frontend
npm install
npm run dev
```

访问: http://localhost:3000

### 目录结构

```
frontend/src/
├── main.js          # 入口
├── App.vue          # 根组件 + 侧边栏布局
├── router/          # 路由
├── stores/          # Pinia 状态
├── services/api.js  # API 封装
├── views/           # 页面组件 (7个)
└── style.css        # 全局样式
```

### 技术栈
- Vue 3 (Composition API)
- Vue Router 4
- Pinia (状态管理)
- Element Plus (UI 组件库)
- ECharts (图表)
- Vite (构建)

## 数据库

使用 Supabase 托管 PostgreSQL。所有表迁移通过 Supabase Dashboard 或 CLI 管理。

关键表: users, portfolios, positions, strategies, trades, alerts, backtest_results, watchlists, market_data_cache, activity_logs, strategy_signals

## 测试

```bash
# 运行测试
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=backend
```

## Docker 部署

```bash
docker-compose up -d --build
```

- 后端: http://localhost:8000
- 前端: http://localhost:3000

## 数据源

- **A股**: yfinance (Yahoo Finance)
- **加密货币**: ccxt (Binance, Huobi, OKX)
