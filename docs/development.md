# 开发文档

## 环境配置

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

## 后端开发

```bash
cd backend
uvicorn main:app --reload
```

API 文档: http://localhost:8000/docs

## 前端开发

```bash
cd frontend
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build
```

## 数据采集

```bash
# A股数据
python data/stock_collector.py

# 加密货币
python data/crypto_collector.py
```

## AI 模型

```bash
# 训练预测模型
python models/predictor.py
```

## 测试

```bash
pytest tests/
```
