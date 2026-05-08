"""API Key 诊断脚本 — 验证所有 Key 是否有效

用法:
  cd backend
  python test_keys.py

不需要启动 uvicorn，直接运行。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
import httpx
from dotenv import load_dotenv
load_dotenv()
# Also try parent directory for root-level .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


async def test_coinchecko():
    """测试 CoinGecko API Key"""
    key = os.getenv("COINGECKO_API_KEY") or os.getenv("coingecko_api_key", "")
    if not key:
        return "❌ COINGECKO_API_KEY 未设置"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Demo key (CG-xxx) uses x-cg-demo-api-key; Pro key uses x-cg-pro-api-key
            headers = {}
            if key.startswith("CG-"):
                headers["x-cg-demo-api-key"] = key
            else:
                headers["x-cg-pro-api-key"] = key

            resp = await client.get(
                "https://api.coingecko.com/api/v3/ping",
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                return f"✅ CoinGecko OK — {data}"
            else:
                return f"❌ CoinGecko {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return f"❌ CoinGecko 连接失败: {e}"


async def test_goplus():
    """测试 GoPlus API"""
    key = os.getenv("GOPLUS_API_KEY", "")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # GoPlus — 用 USDT (ETH) 合约测试
            resp = await client.get(
                "https://api.gopluslabs.io/api/v1/token_security/1",
                params={"contract_addresses": "0xdAC17F958D2ee523a2206206994597C13D831ec7"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 1:
                    return "✅ GoPlus OK"
                return f"⚠️ GoPlus response: {data}"
            else:
                return f"❌ GoPlus {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return f"❌ GoPlus 连接失败: {e}"


async def test_anthropic():
    """测试 Anthropic 原生 API Key"""
    key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("anthropic_api_key", "")
    if not key:
        return "⚠️ ANTHROPIC_API_KEY 未设置 (将尝试 OpenRouter)"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5",
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Say OK"}],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data["content"][0]["text"]
                return f"✅ Anthropic OK → '{reply.strip()}'"
            else:
                return f"❌ Anthropic {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return f"❌ Anthropic 连接失败: {e}"


async def test_openrouter():
    """测试 OpenRouter API Key (备用)"""
    key = os.getenv("OPENROUTER_API_KEY") or os.getenv("openrouter_api_key", "")
    if not key:
        return "❌ OPENROUTER_API_KEY 未设置"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-sonnet-4-6",
                    "messages": [{"role": "user", "content": "Say 'OK' and nothing else."}],
                    "max_tokens": 5,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                return f"✅ OpenRouter OK → '{reply.strip()}'"
            else:
                return f"❌ OpenRouter {resp.status_code}: {resp.text[:300]}"
    except Exception as e:
        return f"❌ OpenRouter 连接失败: {e}"


async def test_dashscope():
    """测试 DashScope (千问) API Key"""
    key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("dashscope_api_key", "")
    if not key:
        return "❌ DASHSCOPE_API_KEY 未设置"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-turbo",
                    "messages": [{"role": "user", "content": "Say 'OK' only."}],
                    "max_tokens": 5,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                return f"✅ DashScope OK → '{reply.strip()}'"
            else:
                return f"❌ DashScope {resp.status_code}: {resp.text[:300]}"
    except Exception as e:
        return f"❌ DashScope 连接失败: {e}"


async def test_kuCoin():
    """测试 KuCoin 公开 API"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://api.kucoin.com/api/v2/symbols")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "200000":
                    count = len(data.get("data", []))
                    return f"✅ KuCoin OK — {count} spot pairs"
            return f"❌ KuCoin {resp.status_code}"
    except Exception as e:
        return f"❌ KuCoin 连接失败: {e}"


async def main():
    print("\n🔑 API Key 诊断\n" + "=" * 50)
    results = await asyncio.gather(
        test_coinchecko(),
        test_goplus(),
        test_anthropic(),
        test_openrouter(),
        test_dashscope(),
        test_kuCoin(),
    )
    for r in results:
        print(r)
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
