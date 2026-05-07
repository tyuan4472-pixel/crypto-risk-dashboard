# Crypto Risk Dashboard 🛡️

加密货币风控评估系统 — 基于 KuCoin 现货币种的每日定时风险评估 + 多维可视化看板。

## 功能

- **全量评估**: 定时扫描 KuCoin 全部现货 (~600-800 币种)，每日更新评分
- **8 维度评分**: 市场流动性 / 价格波动性 / 持仓集中度 / 项目基本面 / 舆情异常 / 交易所合规 / 智能合约安全 / 宏观关联
- **12 项检查指标**: 24h 成交量/市值比、7d 波动率、持仓集中度、GitHub 活跃度、舆情异常检测等
- **网页看板**: Dashboard 总览 + 单币种详情页 (雷达图 + 指标明细 + 风险点列表)
- **手动触发**: 输入币种即时评估，高风险币种自动生成详细报告
- **模型路由**: 基础任务 → 千问 (低成本) / 舆情分析 → Groq (X 平台优化)

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 + TypeScript + TailwindCSS + Recharts |
| 后端 | Python FastAPI |
| 任务队列 | Celery + Redis |
| 数据库 | PostgreSQL 16 |
| 部署 | Docker Compose |
| AI 模型 | 千问 3.6B (DashScope) + Grok-4.3 (OpenRouter) |
| 数据源 | KuCoin / CoinMarketCap / CoinGecko / X(Twitter) |

## 快速开始

### 前置条件

- Docker + Docker Compose
- API Key: CMC / CoinGecko / KuCoin / OpenRouter / DashScope

### 1. 克隆仓库

```bash
git clone git@github.com:tyuan4472-pixel/crypto-risk-dashboard.git
cd crypto-risk-dashboard
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

### 3. 启动

```bash
docker compose up -d
```

服务启动后：
- 前端: http://localhost
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 4. 手动触发首次全量扫描

```bash
docker compose exec worker celery -A tasks call tasks.run_daily_scan
```

## 项目结构

```
crypto-risk-dashboard/
├── frontend/              # Next.js 前端
│   └── src/
│       ├── app/           # 页面路由
│       │   ├── page.tsx           # Dashboard 首页
│       │   └── token/[symbol]/    # 币种详情页
│       ├── components/    # React 组件
│       └── lib/           # API 客户端
├── backend/               # FastAPI 后端
│   └── app/
│       ├── api/           # REST API 路由
│       ├── models/        # Pydantic 数据模型
│       └── services/      # 业务逻辑
│           ├── data_fetcher.py    # 数据源适配层
│           ├── risk_engine.py     # 评分引擎 (8维+12指标)
│           └── model_router.py    # AI 模型路由
├── worker/                # Celery Worker + 评估执行器
│   ├── tasks.py           # 定时/异步任务定义
│   └── evaluator.py       # 评估流程编排
├── docker/                # Nginx 配置 + 数据库初始化
├── docker-compose.yml     # 服务编排
└── .env.example           # 环境变量模板
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tokens` | 币种列表 (支持筛选/排序/分页) |
| GET | `/api/tokens/{symbol}` | 单币种详细评分 |
| POST | `/api/tokens/{symbol}/trigger` | 手动触发评估 |
| GET | `/api/tokens/{symbol}/report` | 获取币种调研报告 |
| GET | `/health` | 健康检查 |

## 部署

### 服务器部署

```bash
# SSH 到服务器
git pull
cp .env.example .env   # 首次部署或新机器
vim .env               # 填入真实 API Key
docker compose up -d --build
```

### 配 HTTPS

```bash
# 安装 certbot
apt install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```

## License

Internal tool — Donut Labs
