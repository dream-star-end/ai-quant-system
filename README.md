# AI Quant System

基于 AI 的量化投资辅助决策系统，支持 A 股和加密货币市场。

## 📁 项目结构

```
ai-quant-system/
├── data/           # 数据采集脚本
├── models/         # AI 模型
├── backend/        # FastAPI 服务
├── frontend/       # Web 界面
├── tests/          # 测试用例
├── docs/           # 文档
├── requirements.txt
└── README.md
```

## 🚀 快速开始

```bash
# 克隆仓库
git clone https://github.com/dream-star-end/ai-quant-system.git
cd ai-quant-system

# 安装依赖
pip install -r requirements.txt

# 启动后端服务
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📊 功能特性

- 📈 数据采集 (A 股、加密货币)
- 🤖 AI 趋势预测
- 📉 技术指标分析
- 🔔 智能告警

## 📄 许可证

MIT
