"""数据源适配层 — 多源聚合数据获取

数据源:
  1. KuCoin (公开 API) — 币种列表 + 基础行情
  2. CoinGecko (需 Key) — 市值/流通量/开发者/社区数据
  3. GoPlus (免费, 可选 Key) — 合约安全检测
  4. CMC (需 Key) — 市值/交易量 (备选)
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
    max_supply: Optional[float] = None
    price_change_24h_pct: Optional[float] = None
    price_change_7d_pct: Optional[float] = None
    price_change_30d_pct: Optional[float] = None
    ath_pct: Optional[float] = None

    # CoinGecko 排名
    market_cap_rank: Optional[int] = None
    cg_id: str = ""
    cg_platforms: dict = field(default_factory=dict)  # {chain: contract_address}

    # CoinGecko dev / community
    github_commits_30d: Optional[int] = None
    developer_score: Optional[float] = None
    community_score: Optional[float] = None
    liquidity_score_cg: Optional[float] = None
    public_interest_score: Optional[float] = None

    # 链上
    top10_holder_ratio: Optional[float] = None
    holder_count: Optional[int] = None

    # 合约安全 (GoPlus)
    contract_audited: Optional[bool] = None
    contract_risks: list[str] = field(default_factory=list)
    is_honeypot: bool = False
    is_proxy: bool = False

    # 舆情 (LLM)
    sentiment_score: Optional[float] = None
    negative_sentiment_pct: Optional[float] = None
    mentions_7d: Optional[int] = None
    mentions_anomaly: bool = False
    sentiment_summary: Optional[str] = None

    # 交易所动态
    exchange_listings: list[str] = field(default_factory=list)
    exchange_delist_warning: bool = False
    delist_sources: list[str] = field(default_factory=list)
    kucoin_deposit_enabled: Optional[bool] = None
    kucoin_withdraw_enabled: Optional[bool] = None

    # 代币解锁
    unlock_event_30d: bool = False
    unlock_amount_usd: Optional[float] = None


# ═══════════════════════════════════════════
# KuCoin Adapter (公开 API, 无需 Key)
# ═══════════════════════════════════════════

class KuCoinAdapter:
    """KuCoin 公开 API — 获取现货币种列表 + 行情"""

    BASE_URL = "https://api.kucoin.com"
    TIMEOUT = 30

    async def fetch_spot_symbols(self) -> list[dict]:
        """拉取 KuCoin 所有 USDT 现货交易对，返回 [{"symbol": "BTC", "name": "Bitcoin"}, ...]"""
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            resp = await client.get(f"{self.BASE_URL}/api/v2/symbols")
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "200000":
                logger.error(f"KuCoin API error: {data.get('msg')}")
                return []

            seen = {}
            for item in data.get("data", []):
                sym = item.get("baseCurrency", "").upper()
                if sym and sym not in seen and item.get("quoteCurrency") == "USDT":
                    seen[sym] = {"symbol": sym, "name": item.get("baseCurrencyName", sym)}
            return list(seen.values())

    async def fetch_tickers(self) -> dict[str, dict]:
        """获取所有 USDT 交易对行情"""
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            resp = await client.get(f"{self.BASE_URL}/api/v1/market/allTickers")
            resp.raise_for_status()
            data = resp.json()

            tickers = {}
            for t in data.get("data", {}).get("ticker", []):
                sym = t.get("symbol", "")
                if sym.endswith("-USDT"):
                    base = sym.replace("-USDT", "")
                    tickers[base] = {
                        "price": float(t.get("last", 0)) if t.get("last") else None,
                        "vol_24h": float(t.get("volValue", 0)) if t.get("volValue") else None,
                        "change_24h_pct": float(t.get("changeRate", 0)) * 100 if t.get("changeRate") else None,
                    }
            return tickers

    async def fetch_symbol_detail(self, symbol: str) -> dict:
        """获取单个交易对详情 (含充提状态)"""
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            resp = await client.get(f"{self.BASE_URL}/api/v1/currencies/{symbol.lower()}")
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == "200000":
                detail = data.get("data", {})
                chains = detail.get("chains", [])
                # 找第一条链的状态
                deposit = None
                withdraw = None
                if chains:
                    deposit = chains[0].get("isDepositEnabled")
                    withdraw = chains[0].get("isWithdrawEnabled")
                return {"deposit_enabled": deposit, "withdraw_enabled": withdraw}
            return {}


# ═══════════════════════════════════════════
# CMC Adapter (需 Key, 备选)
# ═══════════════════════════════════════════

class CMCAdapter:
    BASE_URL = "https://pro-api.coinmarketcap.com"
    TIMEOUT = 30

    def is_configured(self) -> bool:
        return bool(settings.cmc_api_key and settings.cmc_api_key != "your_cmc_api_key")

    async def fetch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        if not self.is_configured():
            return {}
        results = {}
        batch_size = 100
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    resp = await client.get(
                        f"{self.BASE_URL}/v2/cryptocurrency/quotes/latest",
                        headers={"X-CMC_PRO_API_KEY": settings.cmc_api_key},
                        params={"symbol": ",".join(batch), "convert": "USD"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for sym, info_list in data.get("data", {}).items():
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
# CoinGecko Adapter
# ═══════════════════════════════════════════

class CoinGeckoAdapter:
    """CoinGecko API — 市场数据 + 开发者 + 社区 + 合约地址"""

    BASE_URL = "https://api.coingecko.com/api/v3"
    TIMEOUT = 30

    def __init__(self):
        self._symbol_to_id: dict[str, str] = {}

    def is_configured(self) -> bool:
        return bool(settings.coingecko_api_key)

    def _headers(self) -> dict:
        key = settings.coingecko_api_key
        if not key:
            return {}
        if key.startswith("CG-"):
            return {"x-cg-demo-api-key": key}
        else:
            return {"x-cg-pro-api-key": key}

    async def _load_symbol_map(self) -> dict[str, str]:
        """加载 CoinGecko coin_id → id 的完整映射，缓存为 symbol→id"""
        if self._symbol_to_id:
            return self._symbol_to_id

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{self.BASE_URL}/coins/list", headers=self._headers())
                resp.raise_for_status()
                coins = resp.json()
                for coin in coins:
                    sym = coin["symbol"].upper()
                    # 只保留第一个匹配 (通常是大市值的主流币)
                    if sym not in self._symbol_to_id:
                        self._symbol_to_id[sym] = coin["id"]
                logger.info(f"CG: loaded {len(self._symbol_to_id)} symbol→id mappings")
                return self._symbol_to_id
        except Exception as e:
            logger.error(f"CG symbol map load failed: {e}")
            return {}

    async def get_cg_ids(self, symbols: list[str]) -> dict[str, str]:
        """将 KuCoin symbol 列表映射到 CoinGecko coin_id"""
        mapping = await self._load_symbol_map()
        result = {}
        for s in symbols:
            if s.upper() in mapping:
                result[s] = mapping[s.upper()]
        return result

    async def fetch_markets_batch(self, cg_ids: list[str]) -> dict[str, dict]:
        """批量获取市场数据 (250 个/次)"""
        results = {}
        batch_size = 250

        for i in range(0, len(cg_ids), batch_size):
            batch = cg_ids[i:i + batch_size]
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    resp = await client.get(
                        f"{self.BASE_URL}/coins/markets",
                        headers=self._headers(),
                        params={
                            "vs_currency": "usd",
                            "ids": ",".join(batch),
                            "order": "market_cap_desc",
                            "per_page": len(batch),
                            "page": 1,
                            "sparkline": "false",
                            "price_change_percentage": "24h,7d,30d",
                        },
                    )
                    if resp.status_code == 429:
                        logger.warning("CG rate limit, waiting 60s...")
                        await asyncio.sleep(60)
                        continue
                    resp.raise_for_status()
                    for coin in resp.json():
                        sym = coin["symbol"].upper()
                        results[sym] = {
                            "cg_id": coin["id"],
                            "name": coin.get("name", sym),
                            "price_usd": coin.get("current_price"),
                            "market_cap_usd": coin.get("market_cap"),
                            "volume_24h_usd": coin.get("total_volume"),
                            "market_cap_rank": coin.get("market_cap_rank"),
                            "circulating_supply": coin.get("circulating_supply"),
                            "total_supply": coin.get("total_supply"),
                            "max_supply": coin.get("max_supply"),
                            "price_change_24h_pct": coin.get("price_change_percentage_24h_in_currency"),
                            "price_change_7d_pct": coin.get("price_change_percentage_7d_in_currency"),
                            "price_change_30d_pct": coin.get("price_change_percentage_30d_in_currency"),
                            "ath_pct": coin.get("ath_change_percentage"),
                        }
            except httpx.HTTPError as e:
                logger.error(f"CG markets error for batch {i}: {e}")
                continue

        logger.info(f"CG: fetched market data for {len(results)} symbols")
        return results

    async def fetch_coin_detail(self, cg_id: str) -> Optional[dict]:
        """获取单个币种详情 (开发者数据 + 社区数据 + 合约地址)"""
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/coins/{cg_id}",
                    headers=self._headers(),
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "community_data": "true",
                        "developer_data": "true",
                    },
                )
                if resp.status_code == 429:
                    logger.warning(f"CG rate limit on {cg_id}")
                    return None
                resp.raise_for_status()
                data = resp.json()

                dev = data.get("developer_data", {})
                comm = data.get("community_data", {})
                mkt = data.get("market_data", {})

                return {
                    "symbol": data.get("symbol", "").upper(),
                    "name": data.get("name", ""),
                    "platforms": data.get("platforms", {}),
                    "github_commits_30d": dev.get("commit_count_4_weeks"),
                    "developer_score": dev.get("score"),
                    "community_score": comm.get("score"),
                    "liquidity_score_cg": data.get("liquidity_score"),
                    "public_interest_score": data.get("public_interest_score"),
                    "sentiment_votes_up_pct": data.get("sentiment_votes_up_percentage"),
                    # Extra market data not in /markets
                    "price_change_24h_pct": mkt.get("price_change_percentage_24h"),
                    "price_change_7d_pct": mkt.get("price_change_percentage_7d"),
                    "market_cap_usd": mkt.get("market_cap", {}).get("usd"),
                    "volume_24h_usd": mkt.get("total_volume", {}).get("usd"),
                }
        except httpx.HTTPError as e:
            logger.warning(f"CG detail error for {cg_id}: {e}")
            return None


# ═══════════════════════════════════════════
# GoPlus Adapter
# ═══════════════════════════════════════════

class GoPlusAdapter:
    """GoPlus Security API — 合约安全检测 (免费)"""

    BASE_URL = "https://api.gopluslabs.io/api/v1"
    TIMEOUT = 15

    # Solana chain_id for GoPlus
    CHAIN_ID_MAP = {
        "ethereum": "1",
        "bsc": "56",
        "polygon-pos": "137",
        "solana": "solana",
        "arbitrum-one": "42161",
        "optimistic-ethereum": "10",
        "avalanche": "43114",
    }

    def is_configured(self) -> bool:
        return True  # GoPlus 完全免费，不需要 Key 也能用

    async def check_token_security(self, chain_id: str, contract: str) -> dict:
        """检测 Token 合约安全性"""
        try:
            params = {"contract_addresses": contract}
            if settings.goplus_api_key:
                params["authorization"] = settings.goplus_api_key

            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/token_security/{chain_id}",
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
                result = data.get("result", {}).get(contract.lower(), {})

                if not result:
                    return {"audited": None, "risks": [], "holder_count": 0, "top10_ratio": 0.0}

                risks = []
                if str(result.get("is_honeypot")) == "1":
                    risks.append("蜜罐代币 (Honeypot)")
                if str(result.get("is_proxy")) == "1":
                    risks.append("代理合约 (可升级，存在后门风险)")
                if str(result.get("can_take_back_ownership")) == "1":
                    risks.append("Owner 可收回权限")
                if str(result.get("owner_change_balance")) == "1":
                    risks.append("Owner 可修改余额")
                if str(result.get("hidden_owner")) == "1":
                    risks.append("隐藏 Owner")
                if str(result.get("selfdestruct")) == "1":
                    risks.append("合约可自毁")
                if str(result.get("is_mintable")) == "1":
                    risks.append("可增发 (Mintable)")
                if str(result.get("transfer_pausable")) == "1":
                    risks.append("可暂停转账")

                return {
                    "audited": str(result.get("is_open_source")) == "1",
                    "risks": risks,
                    "holder_count": int(result.get("holder_count", 0) or 0),
                    "top10_ratio": float(result.get("top_10_holder_balance_rate", 0) or 0) / 100.0,
                    "is_honeypot": str(result.get("is_honeypot")) == "1",
                    "is_proxy": str(result.get("is_proxy")) == "1",
                }
        except httpx.HTTPError as e:
            logger.warning(f"GoPlus error for {contract}: {e}")
            return {"audited": None, "risks": [], "holder_count": 0, "top10_ratio": 0.0, "is_honeypot": False, "is_proxy": False}


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
        self._cg_cache: dict[str, dict] = {}  # symbol → CG detail cache

    async def get_token_list(self) -> list[dict]:
        return await self.kucoin.fetch_spot_symbols()

    async def fetch_all_tickers(self) -> dict[str, dict]:
        return await self.kucoin.fetch_tickers()

    async def fetch_token_data(self, symbol: str, ticker: Optional[dict] = None) -> TokenDataPayload:
        payload = TokenDataPayload(symbol=symbol)
        if ticker:
            payload.price_usd = ticker.get("price")
            payload.volume_24h_usd = ticker.get("vol_24h")
            payload.price_change_24h_pct = ticker.get("change_24h_pct")
        return payload

    async def fetch_batch(self, symbols: list[str]) -> list[TokenDataPayload]:
        """
        批量获取数据 — 聚合所有数据源:
        1. KuCoin ticker (行情 + 成交量)
        2. CoinGecko 市场数据 (市值/流通量/排名)
        3. CoinGecko 详情 (开发者/社区/合约地址) — 首批 30 个
        4. GoPlus 合约安全 — 有合约地址的
        5. CMC (如果 Key 已配置)
        """
        all_tickers = await self.fetch_all_tickers()

        # ── CoinGecko 市场数据 ──
        cg_market = {}
        cg_details = {}
        if self.coingecko.is_configured():
            symbol_to_id = await self.coingecko.get_cg_ids(symbols)
            cg_ids = list(set(symbol_to_id.values()))
            if cg_ids:
                cg_market = await self.coingecko.fetch_markets_batch(cg_ids)

        # ── CMC 备选 ──
        cmc_data = {}
        if self.cmc.is_configured():
            cmc_data = await self.cmc.fetch_quotes(symbols)

        # ── 组装 payload ──
        results = []
        for sym in symbols:
            payload = TokenDataPayload(symbol=sym)

            # KuCoin ticker
            ticker = all_tickers.get(sym, {})
            payload.price_usd = ticker.get("price")
            payload.volume_24h_usd = ticker.get("vol_24h")
            payload.price_change_24h_pct = ticker.get("change_24h_pct")

            # CoinGecko market
            if sym in cg_market:
                cg = cg_market[sym]
                payload.name = cg.get("name", sym)
                payload.cg_id = cg.get("cg_id", "")
                payload.price_usd = cg.get("price_usd") or payload.price_usd
                payload.market_cap_usd = cg.get("market_cap_usd")
                payload.volume_24h_usd = cg.get("volume_24h_usd") or payload.volume_24h_usd
                payload.circulating_supply = cg.get("circulating_supply")
                payload.total_supply = cg.get("total_supply")
                payload.max_supply = cg.get("max_supply")
                payload.market_cap_rank = cg.get("market_cap_rank")
                payload.price_change_24h_pct = cg.get("price_change_24h_pct")
                payload.price_change_7d_pct = cg.get("price_change_7d_pct")
                payload.price_change_30d_pct = cg.get("price_change_30d_pct")
                payload.ath_pct = cg.get("ath_pct")
            elif sym in cmc_data:
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

            # KuCoin 充提状态 — 取前 50 个批量查
            # 暂不对全量调用以节省 API 限额

            results.append(payload)

        # ── KuCoin 充提状态 (前 50 个) ──

        # ── KuCoin 充提状态 (前 50 个) ──
        kucoin_detail_tasks = [self.kucoin.fetch_symbol_detail(r.symbol) for r in results[:50]]
        kucoin_results = await asyncio.gather(*kucoin_detail_tasks, return_exceptions=True)
        for r, kd in zip(results[:50], kucoin_results):
            if isinstance(kd, dict):
                r.kucoin_deposit_enabled = kd.get("deposit_enabled")
                r.kucoin_withdraw_enabled = kd.get("withdraw_enabled")

        # ── CoinGecko 详情 (开发者数据 + 合约地址) — 取前 30 个有 cg_id 的 ──
        if self.coingecko.is_configured():
            detail_symbols = [r for r in results if r.cg_id][:30]
            if detail_symbols:
                logger.info(f"Fetching CG details for {len(detail_symbols)} tokens...")
                detail_tasks = [self.coingecko.fetch_coin_detail(r.cg_id) for r in detail_symbols]
                detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)

                for payload, detail in zip(detail_symbols, detail_results):
                    if isinstance(detail, dict):
                        payload.github_commits_30d = detail.get("github_commits_30d")
                        payload.developer_score = detail.get("developer_score")
                        payload.community_score = detail.get("community_score")
                        payload.liquidity_score_cg = detail.get("liquidity_score_cg")
                        payload.public_interest_score = detail.get("public_interest_score")
                        payload.cg_platforms = detail.get("platforms", {})
                        # Fill in missing CG market data from detail
                        if not payload.market_cap_usd:
                            payload.market_cap_usd = detail.get("market_cap_usd")
                        if not payload.volume_24h_usd:
                            payload.volume_24h_usd = detail.get("volume_24h_usd")

        # ── GoPlus 合约安全 ──
        goplus_tasks = []
        for r in results:
            if r.cg_platforms:
                for chain, addr in r.cg_platforms.items():
                    chain_id = self.goplus.CHAIN_ID_MAP.get(chain)
                    if chain_id and addr:
                        goplus_tasks.append((r, chain_id, addr))
                        break  # 每个币只查第一条链

        if goplus_tasks:
            logger.info(f"GoPlus: checking {len(goplus_tasks)} tokens...")
            goplus_futures = [
                self.goplus.check_token_security(chain_id, addr)
                for _, chain_id, addr in goplus_tasks
            ]
            goplus_results = await asyncio.gather(*goplus_futures, return_exceptions=True)

            for (payload, _, _), gp in zip(goplus_tasks, goplus_results):
                if isinstance(gp, dict):
                    payload.contract_audited = gp.get("audited")
                    payload.contract_risks = gp.get("risks", [])
                    payload.top10_holder_ratio = gp.get("top10_ratio")
                    payload.holder_count = gp.get("holder_count")
                    payload.is_honeypot = gp.get("is_honeypot", False)
                    payload.is_proxy = gp.get("is_proxy", False)

        logger.info(
            f"DataFetcher: {len(results)} tokens, "
            f"CG market={len(cg_market)}, CG detail={len(detail_symbols) if self.coingecko.is_configured() else 0}, "
            f"GoPlus={len(goplus_tasks)}"
        )
        return results
