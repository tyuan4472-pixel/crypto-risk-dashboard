# API Key 申请指南

## 1. CoinMarketCap (CMC) — MVP 必需

**获取地址**: https://coinmarketcap.com/api/pricing/

步骤:
1. 注册账号
2. 选择 "Basic" 免费套餐 (10,000 calls/月)
3. 进入 Dashboard → API Key → 复制

**免费版限制**:
- 10,000 calls/月
- 每分钟 30 requests
- 够用: 1000 币种 × 1次/天 × 30天 = 30,000 (分 10 批, 3,000 calls/月)

**填入 .env**:
```
CMC_API_KEY=你的key
```

---

## 2. CoinGecko — Phase 2 (可选)

**获取地址**: https://www.coingecko.com/en/api/pricing

- Demo Key (免费): 50 calls/min, 进 Developer Dashboard 创建
- Analyst Plan ($129/月): 500 calls/min, 适合 1000 币种批量查询

**免费版用法**:
- 不填 Key 也能用 (30 calls/min, 很慢)
- 推荐至少用免费的 Demo Key

**填入 .env**:
```
COINGECKO_API_KEY=你的key
```

---

## 3. KuCoin — 当前不需要

公开行情 API (市价/成交量/币种列表) 完全免费, 无需 Key。

只有以下操作才需要 Key:
- 交易下单
- 查询账户余额
- 提现

**如果后续需要** (比如查询 KuCoin 内部数据):
1. 登录 KuCoin
2. API Management → Create API
3. 权限: 只勾 "General" (只读)
4. 设置 Passphrase (牢记)

**填入 .env**:
```
KUCOIN_API_KEY=你的key
KUCOIN_API_SECRET=你的secret
KUCOIN_API_PASSPHRASE=你设置的passphrase
```

---

## 4. OpenRouter — Phase 2 (AI 舆情分析)

**获取地址**: https://openrouter.ai/keys

步骤:
1. 注册 (支持 GitHub 登录)
2. Create Key
3. 充值 $10-20 起步

**用于**: 调用 Grok-4.3 做 X(Twitter) 舆情分析 + 深度调研报告。

**填入 .env**:
```
OPENROUTER_API_KEY=你的key
```

---

## 5. DashScope (阿里云百炼) — Phase 2 (千问)

**获取地址**: https://dashscope.console.aliyun.com/apiKey

步骤:
1. 登录阿里云
2. 开通 DashScope 服务
3. 创建 API Key

**用于**: 轻量任务 (数据清洗/格式化), 成本极低 (约 ¥0.001/次)。

**填入 .env**:
```
DASHSCOPE_API_KEY=你的key
```

---

## 安全提醒

- ⚠️ 永远不要把 Key 提交到 GitHub
- `.env` 文件已在 `.gitignore` 中排除
- 服务器上 Key 放在 `/opt/crypto-risk/.env`, 权限设为 600
- 如果 Key 泄露, 立即到对应平台撤销并重新生成
