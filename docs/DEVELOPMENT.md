# 开发者指南

## 本地开发

### 前置条件

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose (用于 PostgreSQL + Redis)

### 1. 启动数据库 (仅 Postgres + Redis)

```bash
docker compose up -d postgres redis
```

### 2. 后端开发

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
cp ../.env.example .env
# 编辑 .env, 至少配置 DB_HOST=localhost

# 启动
uvicorn app.main:app --reload --port 8000
```

API 文档: http://localhost:8000/docs

### 3. 前端开发

```bash
cd frontend
npm install
npm run dev
```

访问: http://localhost:3000

### 4. Worker 开发 (本地)

```bash
cd worker
pip install -r requirements.txt

# 启动 Worker (需要 Redis 运行中)
celery -A tasks worker --loglevel=info --concurrency=2

# 另一个终端启动 Beat (定时调度)
celery -A tasks beat --loglevel=info
```

### 手动触发评估

```bash
# 通过 API
curl -X POST http://localhost:8000/api/tokens/BTC/trigger

# 通过 Celery
cd worker
python -c "from tasks import app; app.send_task('tasks.evaluate_single', args=['BTC'])"

# 全量扫描
curl -X POST http://localhost:8000/api/scheduler/trigger
```

---

## 架构概览

```
请求流: Browser → Nginx → Next.js (前端) 或 FastAPI (API)
评估流: Celery Beat → Worker → DataFetcher → RiskEngine → PostgreSQL → API → 前端

[Frontend]  ←→  [FastAPI API]  ←→  [PostgreSQL]
                     ↑                    ↑
                     |                    |
                [Celery Worker]  ─────────┘
                     |
            [KuCoin / CMC / GoPlus API]
```

---

## 代码结构

### backend/app/

| 文件 | 职责 |
|------|------|
| `main.py` | FastAPI 入口, 路由注册 |
| `config.py` | Pydantic Settings 配置 |
| `database.py` | SQLAlchemy async engine + session |
| `worker_client.py` | 向 Celery 发送任务 |
| `api/tokens.py` | 评分列表/详情/触发 API |
| `api/scheduler.py` | 扫描状态/触发 API |
| `api/health.py` | 健康检查 |
| `models/orm.py` | ORM 表定义 |
| `models/crud.py` | 数据库 CRUD |
| `models/schemas.py` | Pydantic 请求/响应模型 |
| `services/data_fetcher.py` | 多数据源适配器 |
| `services/risk_engine.py` | 8维度评分引擎 |
| `services/model_router.py` | AI 模型路由 (Phase 2) |

### worker/

| 文件 | 职责 |
|------|------|
| `tasks.py` | Celery 任务定义 |
| `evaluator.py` | 评估编排器 |
| `db.py` | 同步 DB 操作 |
| `config.py` | Worker 配置 |

### frontend/src/

| 文件 | 职责 |
|------|------|
| `app/page.tsx` | Dashboard 首页 |
| `app/token/[symbol]/page.tsx` | 币种详情页 |
| `components/TokenTable.tsx` | 列表组件 |
| `components/RiskRadarChart.tsx` | 8维雷达图 |
| `components/ScoreHistory.tsx` | 30天趋势图 |
| `lib/api.ts` | API 客户端 |

---

## API Key 说明

| Key | 用于 | 获取方式 | 必要性 |
|-----|------|---------|--------|
| `CMC_API_KEY` | 市值/交易量/流通量 | https://coinmarketcap.com/api/ | MVP 需要 |
| `COINGECKO_API_KEY` | 开发者/社区数据 | https://coingecko.com/api/ | 可选 (Phase 2) |
| `KUCOIN_API_KEY` | 私有接口 | KuCoin 后台 | 当前不需要 |
| `OPENROUTER_API_KEY` | Groq 舆情分析 | https://openrouter.ai | Phase 2 |
| `DASHSCOPE_API_KEY` | 千问基础任务 | https://dashscope.console.aliyun.com | Phase 2 |

注: KuCoin 公开行情 API 和 GoPlus 合约安全检测不需要任何 Key。

---

## 常见问题

### 后端启动报错 "Connection refused to postgres"

确保 PostgreSQL 容器已启动: `docker compose up -d postgres`

本地开发时 `.env` 中设置 `DB_HOST=localhost` (非 `postgres`)。

### 前端看不到数据

1. 确认后端 API 正常: `curl http://localhost:8000/health`
2. 确认已运行过至少一次评估: `curl -X POST http://localhost:8000/api/scheduler/trigger`
3. 等待评估完成后刷新前端

### Worker 无法连接 Redis

确保 Redis 容器已启动: `docker compose up -d redis`

本地开发时 `.env` 中设置 `REDIS_URL=redis://localhost:6379/0`。
