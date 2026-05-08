"""数据源适配层 — 真正实现 API 调用

数据源:
  1. KuCoin (公开 API, 无需 Key) — 币种列表 + 基础行情
  2. CMC (需 Key) — 市值/交易量/流通量
  3. CoinGecko (需 Key 或免费版限速) — 开发者数据/社区数据
  4. X(Twitter) via AI — 舆情 (Phase 2, 需 OpenRouter Key)
  5. GoPlus (免费) — 合约安全检测

Key 占位说明:
  - CMC_API_KEY: 在 .env 中填入，代码通过 settings 读取
  - COINGECKO_API_KEY: 同上
  - KUCOIN_API_KEY: 仅私有接口需要，公开行情不需要
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 数据载体
# ═══════════════════════════════════════════

@dataclass
class TokenDataPayload:
    """各数据源统一输出格式"""
    symbol: str
    name: str = ""
    price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    price_change_24h_pct: Optional[float] = None
    price_change_7d_pct: Optional[float] = None

    # CoinGecko dev data
    github_commits_30d: Optional[int] = None
    developer_score: Optional[float] = None
    community_score: Optional[float] = None
    volatility_30d: Optional[float] = None

    # 链上
    top10_holder_ratio: Optional[float] = None

    # 合约安全 (GoPlus)
    contract_audited: Optional[bool] = None
    contract_risks: list[str] = field(default_factory=list)

    # 舆情 (Phase 2)
    sentiment_score: Optional[float] = None
    negative_sentiment_pct: Optional[float] = None
    mentions_7d: Optional[int] = None
    mentions_anomaly: bool = False
    sentiment_summary: Optional[str] = None

    # 交易所动态
    exchange_listings: list[str] = field(default_factory=list)
    exchange_delist_warning: bool = False
    delist_sources: list[str] = field(default_factory=list)

    # 代币解锁
    unlock_event_30d: bool = False
    unlock_amount_usd: Optional[float] = None


# ═══════════════════════════════════════════
# KuCoin Adapter (公开 API, 无需 API Key)
# ═══════════════════════════════════════════

class KuCoinAdapter:
    """KuCoin 公开 API — 获取现货币种列表 + 行情"""

    BASE_URL = "https://api.kucoin.com"
    TIMEOUT = 30

    async def fetch_spot_symbols(self) -> list[dict]:
        """
        拉取 KuCoin 所有 USDT 现货交易对，提取 base currency 去重。
        返回: [{"symbol": "BTC", "name": "Bitcoin"}, ...]
        """
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            resp = await client.get(f"{self.BASE_URL}/api/v2/symbols")
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != "200000":
                logger.error(f"KuCoin API error: {data.get('msg')}")
                return []

            seen = {}
            for item in data.get("data", []):
                # 只取 USDT 交易对 (最主流、数据最全的市场)
                if item.get("quoteCurrency") == "USDT" and item.get("enableTrading"):
                    base = item.get("baseCurrency", "")
                    if base and base not in seen:
                        seen[base] = {
                            "symbol": base,
                            "name": item.get("name", base),
                        }

            logger.info(f"KuCoin: fetched {len(seen)} USDT spot symbols")
            return sorted(seen.values(), key=lambda x: x["symbol"])

    async def fetch_tickers(self) -> dict[str, dict]:
        """
        获取所有 USDT 交易对的 24h 行情。
        返回: {"BTC": {"price": 65000, "vol_24h": 1000000, ...}, ...}
        """
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            resp = await client.get(f"{self.BASE_URL}/api/v1/market/allTickers")
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != "200000":
                logger.error(f"KuCoin tickers error: {data.get('msg')}")
                return {}

            tickers = {}
            for item in data.get("data", {}).get("ticker", []):
                symbol_pair = item.get("symbol", "")
                if symbol_pair.endswith("-USDT"):
                    base = symbol_pair.replace("-USDT", "")
                    try:
                        tickers[base] = {
                            "price": float(item.get("last", 0) or 0),
                            "vol_24h": float(item.get("volValue", 0) or 0),  # USDT 计价成交量
                            "change_24h_pct": float(item.get("changeRate", 0) or 0) * 100,
                            "high_24h": float(item.get("high", 0) or 0),
                            "low_24h": float(item.get("low", 0) or 0),
                        }
                    except (ValueError, TypeError):
                        continue

            logger.info(f"KuCoin: fetched tickers for {len(tickers)} pairs")
            return tickers


# ═══════════════════════════════════════════
# CMC Adapter (需要 CMC_API_KEY)
# ═══════════════════════════════════════════

class CMCAdapter:
    """
    CoinMarketCap API 适配器。
    获取: 市值、流通量、完全稀释市值、24h 成交量、BTC dominance 等。

    ⚠️ 需要 CMC_API_KEY，在 .env 中配置。
    免费版: 10,000 calls/月，够 1000 币种每天跑一次。
    """

    BASE_URL = "https://pro-api.coinmarketcap.com"
    TIMEOUT = 30

    def _headers(self) -> dict:
        return {"X-CMC_PRO_API_KEY": settings.cmc_api_key}

    def is_configured(self) -> bool:
        """检查 API Key 是否已配置"""
        return bool(settings.cmc_api_key and settings.cmc_api_key != "your_coinmarketcap_api_key")

    async def fetch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """
        批量获取币种市场数据。
        CMC 单次最多 5000 个 symbol (逗号分隔)。
        返回: {"BTC": {"market_cap": ..., "volume_24h": ..., ...}, ...}
        """
        if not self.is_configured():
            logger.warning("CMC API Key 未配置 — 跳过 CMC 数据获取")
            return {}

        results = {}
        # 分批 (CMC 单次最多处理约 100-200 个 symbol 比较稳定)
        batch_size = 100
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    resp = await client.get(
                        f"{self.BASE_URL}/v1/cryptocurrency/quotes/latest",
                        headers=self._headers(),
                        params={"symbol": ",".join(batch), "convert": "USD"},
                    )
                    if resp.status_code == 429:
                        logger.warning("CMC rate limited, sleeping 60s...")
                        await asyncio.sleep(60)
                        continue
                    resp.raise_for_status()
                    data = resp.json().get("data", {})

                    for sym, info_list in data.items():
                        # CMC 返回的 data 可能是 list 或 dict
                        info = info_list[0] if isinstance(info_list, list) else info_list
                        quote = info.get("quote", {}).get("USD", {})
                        results[sym] = {
                            "name": info.get("name", sym),
                            "market_cap": quote.get("market_cap"),
                            "volume_24h": quote.get("volume_24h"),
                            "circulating_supply": info.get("circulating_supply"),
                            "total_supply": info.get("total_supply"),
                            "price": quote.get("price"),
                            "change_24h": quote.get("percent_change_24h"),
                            "change_7d": quote.get("percent_change_7d"),
                        }
            except httpx.HTTPError as e:
                logger.error(f"CMC API error for batch {i}: {e}")
                continue

        logger.info(f"CMC: fetched data for {len(results)} symbols")
        return results


# ═══════════════════════════════════════════
# CoinGecko Adapter (需要 COINGECKO_API_KEY, 或使用免费版)
# ═══════════════════════════════════════════

class CoinGeckoAdapter:
    """
    CoinGecko API — 补充开发者数据、社区活跃度。

    ⚠️ 需要 COINGECKO_API_KEY (Pro plan) 或使用免费版 (30 calls/min)。
    免费版太慢 (1000 币种需要 30+ 分钟), 建议使用 Demo Key (50 calls/min) 或 Pro。
    """

    BASE_URL_FREE = "https://api.coingecko.com/api/v3"
    BASE_URL_PRO = "https://pro-api.coingecko.com/api/v3"
    TIMEOUT = 30

    @property
    def base_url(self) -> str:
        return self.BASE_URL_PRO if self.is_configured() else self.BASE_URL_FREE

    def _headers(self) -> dict:
        if self.is_configured():
            return {"x-cg-pro-api-key": settings.coingecko_api_key}
        return {}

    def is_configured(self) -> bool:
        return bool(settings.coingecko_api_key and settings.coingecko_api_key != "your_coingecko_api_key")

    async def fetch_coin_data(self, coin_id: str) -> Optional[dict]:
        """获取单个币种的开发者 + 社区数据"""
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.base_url}/coins/{coin_id}",
                    headers=self._headers(),
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "market_data": "true",
                        "community_data": "true",
                        "developer_data": "true",
                    },
                )
                if resp.status_code == 429:
                    logger.warning(f"CoinGecko rate limited on {coin_id}")
                    return None
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.warning(f"CoinGecko error for {coin_id}: {e}")
            return None


# ═══════════════════════════════════════════
# GoPlus Adapter (免费, 无需 Key)
# ═══════════════════════════════════════════

class GoPlusAdapter:
    """
    GoPlus Security API — 合约安全检测。
    完全免费，无需 API Key。
    检测: 蜜罐、代理合约、Owner 权限异常等。
    """

    BASE_URL = "https://api.gopluslabs.com/api/v1"
    TIMEOUT = 15

    async def check_token_security(self, chain_id: str, contract: str) -> dict:
        """
        检测 Token 合约安全性。
        chain_id: "1" (ETH), "56" (BSC), "137" (Polygon), etc.
        contract: 合约地址
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/token_security/{chain_id}",
                    params={"contract_addresses": contract},
                )
                resp.raise_for_status()
                data = resp.json()
                result = data.get("result", {}).get(contract.lower(), {})

                risks = []
                if result.get("is_honeypot") == "1":
                    risks.append("蜜罐代币 (Honeypot)")
                if result.get("is_proxy") == "1":
                    risks.append("代理合约 (可升级，存在后门风险)")
                if result.get("can_take_back_ownership") == "1":
                    risks.append("Owner 可收回权限")
                if result.get("owner_change_balance") == "1":
                    risks.append("Owner 可修改余额")
                if result.get("hidden_owner") == "1":
                    risks.append("隐藏 Owner")
                if result.get("selfdestruct") == "1":
                    risks.append("合约可自毁")

                return {
                    "audited": result.get("is_open_source") == "1",
                    "risks": risks,
                    "holder_count": int(result.get("holder_count", 0) or 0),
                    "top10_ratio": float(result.get("top_10_holder_balance_rate", 0) or 0),
                }
        except httpx.HTTPError as e:
            logger.warning(f"GoPlus error for {contract}: {e}")
            return {"audited": None, "risks": [], "holder_count": 0, "top10_ratio": 0}


# ═══════════════════════════════════════════
# 统一数据获取入口
# ═══════════════════════════════════════════

class DataFetcher:
    """统一数据获取 — 聚合 KuCoin + CMC + CoinGecko + GoPlus"""

    def __init__(self):
        self.kucoin = KuCoinAdapter()
        self.cmc = CMCAdapter()
        self.coingecko = CoinGeckoAdapter()
        self.goplus = GoPlusAdapter()

    async def get_token_list(self) -> list[dict]:
        """获取需要评估的币种列表 (来自 KuCoin 现货)"""
        return await self.kucoin.fetch_spot_symbols()

    async def fetch_all_tickers(self) -> dict[str, dict]:
        """获取所有 KuCoin ticker 行情"""
        return await self.kucoin.fetch_tickers()

    async def fetch_token_data(self, symbol: str, ticker: Optional[dict] = None) -> TokenDataPayload:
        """
        聚合多渠道数据，输出标准化 TokenDataPayload。
        ticker: 可选，预先获取的 KuCoin 行情 (避免重复拉取)
        """
        payload = TokenDataPayload(symbol=symbol)

        # 1. KuCoin 行情 (如果没有预传)
        if ticker:
            payload.price_usd = ticker.get("price")
            payload.volume_24h_usd = ticker.get("vol_24h")
            payload.price_change_24h_pct = ticker.get("change_24h_pct")

        # 2. CMC 数据 (如果 key 已配置)
        if self.cmc.is_configured():
            cmc_data = await self.cmc.fetch_quotes([symbol])
            if symbol in cmc_data:
                info = cmc_data[symbol]
                payload.name = info.get("name", symbol)
                payload.market_cap_usd = info.get("market_cap")
                payload.volume_24h_usd = info.get("volume_24h") or payload.volume_24h_usd
                payload.circulating_supply = info.get("circulating_supply")
                payload.total_supply = info.get("total_supply")
                payload.price_usd = info.get("price") or payload.price_usd
                payload.price_change_7d_pct = info.get("change_7d")

        # 3. CoinGecko (如果 key 已配置 — Phase 2 补充)
        # TODO: 需要 symbol → CoinGecko coin_id 的映射表
        # if self.coingecko.is_configured():
        #     cg_data = await self.coingecko.fetch_coin_data(symbol.lower())
        #     if cg_data:
        #         dev_data = cg_data.get("developer_data", {})
        #         payload.github_commits_30d = dev_data.get("commit_count_4_weeks")

        # 4. GoPlus 合约安全 (Phase 2 — 需要合约地址映射)
        # TODO: 需要 symbol → chain_id + contract_address 的映射
        # goplus_result = await self.goplus.check_token_security(chain_id, contract)

        return payload

    async def fetch_batch(self, symbols: list[str]) -> list[TokenDataPayload]:
        """
        批量获取数据 — 优化策略:
        1. 先批量拉 KuCoin ticker (单次请求拿所有行情)
        2. CMC 批量查询 (100个/批)
        3. 逐个补充 CoinGecko/GoPlus (Phase 2)
        """
        # 批量拉 ticker
        all_tickers = await self.fetch_all_tickers()

        # CMC 批量 (如果配置了)
        cmc_data = {}
        if self.cmc.is_configured():
            cmc_data = await self.cmc.fetch_quotes(symbols)

        # 组装每个 symbol 的 payload
        results = []
        for sym in symbols:
            payload = TokenDataPayload(symbol=sym)
            ticker = all_tickers.get(sym, {})
            payload.price_usd = ticker.get("price")
            payload.volume_24h_usd = ticker.get("vol_24h")
            payload.price_change_24h_pct = ticker.get("change_24h_pct")

            if sym in cmc_data:
                info = cmc_data[sym]
                payload.name = info.get("name", sym)
                payload.market_cap_usd = info.get("market_cap")
                payload.volume_24h_usd = info.get("volume_24h") or payload.volume_24h_usd
                payload.circulating_supply = info.get("circulating_supply")
                payload.total_supply = info.get("total_supply")
                payload.price_usd = info.get("price") or payload.price_usd
                payload.price_change_7d_pct = info.get("change_7d")
            elif not payload.name:
                payload.name = sym

            results.append(payload)

        return results
