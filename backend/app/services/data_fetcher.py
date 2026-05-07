"""数据源适配层

统一接口对接多个数据源，输出标准化 TokenDataPayload。
当前支持: KuCoin (币种列表), CMC/CoinGecko (市场数据), X(Twitter) (舆情)
"""

from dataclasses import dataclass, field
from typing import Optional
import httpx

from app.config import settings


@dataclass
class TokenDataPayload:
    """各数据源统一输出格式"""
    symbol: str
    name: str
    price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None

    # CoinGecko 补充
    github_commits_30d: Optional[int] = None
    developer_score: Optional[float] = None
    community_score: Optional[float] = None
    price_change_7d_pct: Optional[float] = None
    volatility_30d: Optional[float] = None

    # 链上 (如有 Dune/Nansen)
    top10_holder_ratio: Optional[float] = None

    # 合约安全 (GoPlus/Rugcheck)
    contract_audited: Optional[bool] = None
    contract_risks: list[str] = field(default_factory=list)

    # 舆情 (X/Twitter via Groq)
    sentiment_score: Optional[float] = None            # 0-100, 越高越正面
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


class KuCoinAdapter:
    """KuCoin API — 获取支持的现货币种列表"""

    BASE_URL = "https://api.kucoin.com"

    async def fetch_symbols(self) -> list[str]:
        """拉取 KuCoin 所有现货交易对，提取 base currency 去重"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/api/v2/symbols")
            resp.raise_for_status()
            data = resp.json()
            symbols = set()
            for item in data.get("data", []):
                if item.get("market") == "USDT":  # 只取 USDT 交易对
                    symbols.add(item.get("baseCurrency", ""))
            return sorted(symbols)


class CMCAdapter:
    """CoinMarketCap API 适配器"""

    BASE_URL = "https://pro-api.coinmarketcap.com"

    async def fetch_listings(self, symbols: list[str], limit: int = 500) -> dict:
        """批量获取币种市场数据"""
        headers = {"X-CMC_PRO_API_KEY": settings.cmc_api_key}
        params = {"symbol": ",".join(symbols[:limit]), "convert": "USD"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/v1/cryptocurrency/quotes/latest",
                headers=headers, params=params, timeout=30
            )
            resp.raise_for_status()
            return resp.json()


class CoinGeckoAdapter:
    """CoinGecko API 适配器 (补充开发者/社区数据)"""

    BASE_URL = "https://pro-api.coingecko.com/api/v3"

    async def fetch_coin_data(self, coin_id: str) -> dict:
        headers = {"x-cg-pro-api-key": settings.coingecko_api_key}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/coins/{coin_id}",
                headers=headers,
                params={"developer_data": "true", "community_data": "true"},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()


class DataFetcher:
    """统一数据获取入口，聚合多个数据源"""

    def __init__(self):
        self.kucoin = KuCoinAdapter()
        self.cmc = CMCAdapter()
        self.coingecko = CoinGeckoAdapter()

    async def get_token_list(self) -> list[str]:
        """获取需要评估的币种列表 (来自 KuCoin 现货)"""
        return await self.kucoin.fetch_symbols()

    async def fetch_token_data(self, symbol: str) -> TokenDataPayload:
        """聚合多渠道数据，输出标准化的 TokenDataPayload"""
        # TODO: 并行调用 CMC / CoinGecko / 链上 / 合约审计 API
        # TODO: 舆情数据异步调用 Groq (耗时最长，单独处理)
        return TokenDataPayload(symbol=symbol, name=symbol)
