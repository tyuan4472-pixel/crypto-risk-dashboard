"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw, FileText, AlertTriangle, CheckCircle, XCircle, Skull, Shield, TrendingDown } from "lucide-react";
import RiskRadarChart from "@/components/RiskRadarChart";
import ScoreHistory from "@/components/ScoreHistory";
import { fetchTokenDetail, triggerEvaluation, fetchTokenReport, TokenDetail } from "@/lib/api";

const DIM_LABELS: Record<string, string> = {
  liquidity: "流动性", volatility: "波动性", concentration: "集中度",
  fundamental: "基本面", sentiment: "舆情", compliance: "合规",
  security: "安全", macro: "宏观",
};

const RISK_COLORS: Record<string, string> = {
  "极低": "text-green-400 bg-green-900/30", "低": "text-blue-400 bg-blue-900/30",
  "中": "text-yellow-400 bg-yellow-900/30", "高": "text-orange-400 bg-orange-900/30",
  "极高": "text-red-400 bg-red-900/30",
};

function formatUsd(n: number | null | undefined): string {
  if (n == null) return "--";
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}

function formatPct(n: number | null | undefined): string {
  if (n == null) return "--";
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export default function TokenDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const [token, setToken] = useState<TokenDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [report, setReport] = useState<string | null>(null);
  const [showReport, setShowReport] = useState(false);

  useEffect(() => { loadDetail(); }, [symbol]);

  async function loadDetail() {
    setLoading(true); setError(null);
    try { setToken(await fetchTokenDetail(symbol)); } catch (err: any) { setError(err.message); setToken(null); }
    setLoading(false);
  }

  async function handleTrigger() {
    setTriggering(true);
    try { await triggerEvaluation(symbol); setTimeout(() => { loadDetail(); setTriggering(false); }, 5000); }
    catch { setTriggering(false); }
  }

  async function handleLoadReport() {
    try { const data = await fetchTokenReport(symbol); setReport(data.content); setShowReport(true); }
    catch { setReport("报告尚未生成"); setShowReport(true); }
  }

  if (loading) return <main className="min-h-screen p-6 max-w-5xl mx-auto"><div className="text-gray-500 mt-20 text-center">加载中...</div></main>;

  if (error || !token) return (
    <main className="min-h-screen p-6 max-w-5xl mx-auto">
      <Link href="/" className="text-blue-400 hover:underline text-sm flex items-center gap-1 mb-8"><ArrowLeft className="w-4 h-4" /> 返回</Link>
      <div className="text-center mt-16">
        <AlertTriangle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
        <p className="text-gray-400 text-lg mb-2">未找到 {symbol?.toUpperCase()} 的数据</p>
        <button onClick={handleTrigger} disabled={triggering}
          className="px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 disabled:opacity-50">
          {triggering ? "评估中..." : "触发评估"}
        </button>
      </div>
    </main>
  );

  const zombie = token.zombie || { score: 0, flags: [] };
  const extra = token.extra || {};
  const ind = token.indicators || {};

  return (
    <main className="min-h-screen p-6 max-w-5xl mx-auto space-y-6">
      <Link href="/" className="text-blue-400 hover:underline text-sm flex items-center gap-1"><ArrowLeft className="w-4 h-4" /> 返回 Dashboard</Link>

      {/* ── Header ── */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">{token.symbol} <span className="text-gray-500 text-lg ml-2">{token.name}</span></h1>
          <div className="flex items-center gap-3 mt-2 text-sm text-gray-400 flex-wrap">
            <span className={`px-2 py-0.5 rounded font-bold text-base ${RISK_COLORS[token.risk_level] || ""}`}>{token.risk_level}风险 · {token.total_score}/100</span>
            <span>{formatUsd(token.price_usd)}</span>
            <span>市值 {formatUsd(token.market_cap_usd)}</span>
            <span>24h量 {formatUsd(token.volume_24h_usd)}</span>
            {extra.market_cap_rank && <span className="text-gray-600"># {extra.market_cap_rank}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={handleLoadReport} className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg text-sm hover:bg-gray-700"><FileText className="w-4 h-4" /> 报告</button>
          <button onClick={handleTrigger} disabled={triggering}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${triggering ? "animate-spin" : ""}`} /> {triggering ? "评估中..." : "重新评估"}
          </button>
        </div>
      </div>

      {/* ── 🧟 Zombie Detection ── */}
      {zombie.score > 0 && (
        <section className="bg-gray-900 rounded-lg border border-red-800 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Skull className="w-5 h-5 text-red-400" />
            <h2 className="text-lg font-semibold text-red-300">🧟 僵尸币检测 — {zombie.score}/7</h2>
            {zombie.score >= 5 && <span className="text-xs bg-red-900 text-red-300 px-2 py-0.5 rounded">⚠️ 确认为僵尸币</span>}
            {zombie.score >= 3 && zombie.score < 5 && <span className="text-xs bg-orange-900 text-orange-300 px-2 py-0.5 rounded">⚠️ 疑似僵尸币</span>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
            {zombie.flags.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-red-300"><XCircle className="w-4 h-4 flex-shrink-0" /> {f}</div>
            ))}
          </div>
        </section>
      )}

      {/* ── Market Data Cards ── */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <div className="text-xs text-gray-500">市值排名</div>
          <div className="text-lg font-bold">{extra.market_cap_rank ? `#${extra.market_cap_rank}` : "--"}</div>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <div className="text-xs text-gray-500">ATH 跌幅</div>
          <div className={`text-lg font-bold ${extra.ath_pct != null && extra.ath_pct < -80 ? "text-red-400" : ""}`}>
            {formatPct(extra.ath_pct)}
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <div className="text-xs text-gray-500">流通率</div>
          <div className="text-lg font-bold">
            {extra.circulating_supply && extra.total_supply
              ? `${((extra.circulating_supply / extra.total_supply) * 100).toFixed(1)}%`
              : "--"}
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <div className="text-xs text-gray-500">持有者</div>
          <div className="text-lg font-bold">{extra.holder_count?.toLocaleString() || "--"}</div>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <div className="text-xs text-gray-500">KuCoin 充值</div>
          <div className={`text-sm font-bold ${extra.kucoin_deposit_enabled === false ? "text-red-400" : extra.kucoin_deposit_enabled === true ? "text-green-400" : "text-gray-600"}`}>
            {extra.kucoin_deposit_enabled === false ? "❌ 已关闭" : extra.kucoin_deposit_enabled === true ? "✅ 正常" : "--"}
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <div className="text-xs text-gray-500">KuCoin 提现</div>
          <div className={`text-sm font-bold ${extra.kucoin_withdraw_enabled === false ? "text-red-400" : extra.kucoin_withdraw_enabled === true ? "text-green-400" : "text-gray-600"}`}>
            {extra.kucoin_withdraw_enabled === false ? "❌ 已关闭" : extra.kucoin_withdraw_enabled === true ? "✅ 正常" : "--"}
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <div className="text-xs text-gray-500">合约安全</div>
          <div className={`text-sm font-bold ${ind.is_honeypot ? "text-red-400" : ind.contract_audited === true ? "text-green-400" : "text-gray-600"}`}>
            {ind.is_honeypot ? "🚨 蜜罐" : ind.contract_audited === true ? "✅ 已审计" : "--"}
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-3">
          <div className="text-xs text-gray-500">GitHub 30d</div>
          <div className="text-lg font-bold">{extra.github_commits_30d != null ? extra.github_commits_30d : "--"}</div>
        </div>
      </section>

      {/* ── Radar + Dimensions + Indicators ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">8 维度风险雷达</h2>
          <RiskRadarChart dimensions={token.dimensions || { liquidity: 0, volatility: 0, concentration: 0, fundamental: 0, sentiment: 0, compliance: 0, security: 0, macro: 0 }} />
        </section>
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">项目基本面</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between py-1.5 border-b border-gray-800/50">
              <span className="text-gray-400">开发者评分</span>
              <span className={extra.developer_score != null && extra.developer_score > 60 ? "text-green-400" : "text-gray-300"}>{extra.developer_score?.toFixed(1) || "--"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800/50">
              <span className="text-gray-400">社区评分</span>
              <span>{extra.community_score?.toFixed(1) || "--"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800/50">
              <span className="text-gray-400">GitHub 30d 提交</span>
              <span>{extra.github_commits_30d != null ? extra.github_commits_30d : "--"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800/50">
              <span className="text-gray-400">前10持仓占比</span>
              <span className={extra.top10_holder_ratio != null && extra.top10_holder_ratio > 0.7 ? "text-red-400" : ""}>{extra.top10_holder_ratio != null ? `${(extra.top10_holder_ratio * 100).toFixed(1)}%` : "--"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800/50">
              <span className="text-gray-400">合约审计</span>
              <span>{ind.contract_audited === true ? "✅ 是" : ind.contract_audited === false ? "❌ 否" : "--"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800/50">
              <span className="text-gray-400">代理合约</span>
              <span className={ind.is_proxy ? "text-orange-400" : "text-green-400"}>{ind.is_proxy ? "⚠️ 可升级" : "✅ 不可升级"}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-gray-400">蜜罐检测</span>
              <span className={ind.is_honeypot ? "text-red-400" : "text-green-400"}>{ind.is_honeypot ? "🚨 蜜罐" : "✅ 安全"}</span>
            </div>
          </div>
        </section>
      </div>

      {/* ── Risk Details (From 12-step investigation) ── */}
      {token.risk_details && token.risk_details.length > 0 && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">风险点明细 ({token.risk_details.length})</h2>
          <div className="space-y-2">
            {token.risk_details.map((d, i) => (
              <div key={i} className={`rounded border p-3 text-sm ${
                d.severity === "critical" ? "bg-red-900/30 border-red-700" :
                d.severity === "high" ? "bg-red-900/20 border-red-700" :
                d.severity === "medium" ? "bg-orange-900/20 border-orange-700" :
                "bg-gray-800/50 border-gray-700"
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium">{d.category}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${
                    d.severity === "critical" || d.severity === "high" ? "border-red-600 text-red-400" :
                    d.severity === "medium" ? "border-orange-600 text-orange-400" :
                    "border-gray-600 text-gray-400"
                  }`}>{d.severity}</span>
                </div>
                <p className="text-gray-400">{d.description}</p>
                {d.source && <p className="text-xs text-gray-600 mt-1">来源: {d.source}</p>}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Exchange Distribution Card ── */}
      {(extra.exchange_count != null || extra.cex_count != null) && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">🏦 交易所分布</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">上线交易所</div>
              <div className="text-xl font-bold text-white">{extra.exchange_count ?? "--"}</div>
              <div className="text-xs text-gray-600 mt-1">家</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">主流 CEX</div>
              <div className="text-xl font-bold text-white">{extra.cex_count ?? "--"}</div>
              <div className="text-xs text-gray-600 mt-1">家</div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">独占性</div>
              <div className={`text-sm font-bold mt-1 ${
                (extra.cex_count ?? 0) >= 10 ? "text-green-400" :
                (extra.cex_count ?? 0) >= 5 ? "text-yellow-400" : "text-red-400"
              }`}>
                {(extra.cex_count ?? 0) >= 10 ? "低风险" : (extra.cex_count ?? 0) >= 5 ? "中风险" : "高风险"}
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">KuCoin 量占比</div>
              <div className="text-xl font-bold text-white">
                {extra.kucoin_volume_share != null ? `${extra.kucoin_volume_share.toFixed(1)}%` : "--"}
              </div>
            </div>
          </div>
          {extra.major_exchanges && extra.major_exchanges.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-2">主流交易所覆盖 ({extra.major_exchanges.length}/13)</div>
              <div className="flex flex-wrap gap-1.5">
                {extra.major_exchanges.map((ex, i) => (
                  <span key={i} className="text-xs bg-blue-900/50 text-blue-300 border border-blue-800 px-2 py-0.5 rounded">{ex}</span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* ── Cross Validation Card ── */}
      {extra.cg_cmc_divergence_pct != null && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">🔁 数据交叉验证 (CG vs CMC)</h2>
          <div className="flex items-center gap-4">
            <div className={`text-2xl font-bold ${
              extra.cg_cmc_divergence_pct > 10 ? "text-red-400" :
              extra.cg_cmc_divergence_pct > 5 ? "text-yellow-400" : "text-green-400"
            }`}>
              {extra.cg_cmc_divergence_pct.toFixed(2)}%
            </div>
            <div>
              <div className="text-sm text-gray-300">
                {extra.cg_cmc_divergence_pct > 10
                  ? "⚠️ 数据差异较大 — 可能存在数据操纵或双重计算"
                  : extra.cg_cmc_divergence_pct > 5
                  ? "⚡ 轻微差异 — 数据源口径不同"
                  : "✅ 一致 — CG 与 CMC 数据吻合"}
              </div>
              <div className="text-xs text-gray-600 mt-1">流通量差异百分比 (CoinGecko vs CoinMarketCap)</div>
            </div>
          </div>
        </section>
      )}

      {/* ── KuCoin Market Card ── */}
      {(extra.kucoin_best_bid != null || extra.kucoin_best_ask != null) && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">📊 KuCoin 盘口数据</h2>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">最优买价 (Bid)</div>
              <div className="text-base font-bold text-green-400">
                {extra.kucoin_best_bid != null ? `$${extra.kucoin_best_bid.toPrecision(6)}` : "--"}
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">最优卖价 (Ask)</div>
              <div className="text-base font-bold text-red-400">
                {extra.kucoin_best_ask != null ? `$${extra.kucoin_best_ask.toPrecision(6)}` : "--"}
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">价差 (Spread)</div>
              <div className={`text-base font-bold ${
                extra.kucoin_spread_pct != null && extra.kucoin_spread_pct > 1 ? "text-red-400" :
                extra.kucoin_spread_pct != null && extra.kucoin_spread_pct > 0.3 ? "text-yellow-400" : "text-green-400"
              }`}>
                {extra.kucoin_spread_pct != null ? `${extra.kucoin_spread_pct.toFixed(4)}%` : "--"}
              </div>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded border ${
              extra.kucoin_deposit_enabled === false || extra.kucoin_withdraw_enabled === false
                ? "bg-red-900/30 border-red-700 text-red-400"
                : "bg-green-900/30 border-green-700 text-green-400"
            }`}>
              {extra.kucoin_deposit_enabled === false ? "⚠️ ST 限制" : "正常交易"}
            </span>
            {extra.kucoin_spread_pct != null && extra.kucoin_spread_pct > 1 && (
              <span className="text-xs text-orange-400">⚠️ 价差过大，流动性差</span>
            )}
          </div>
        </section>
      )}

      {/* ── Sentiment Section ── */}
      {extra.sentiment && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">💬 社区情绪分析</h2>
          <div className="flex items-center gap-6 mb-3">
            {/* Sentiment gauge */}
            <div className="flex flex-col items-center">
              <div className="relative w-24 h-12 overflow-hidden">
                <div className="absolute inset-0 rounded-t-full bg-gradient-to-r from-red-500 via-yellow-400 to-green-500 opacity-30" />
                <div
                  className="absolute bottom-0 left-1/2 w-1 h-10 bg-white rounded-full origin-bottom"
                  style={{
                    transform: `translateX(-50%) rotate(${
                      ((extra.sentiment.positive_pct ?? 50) - 50) * 0.9
                    }deg)`,
                  }}
                />
              </div>
              <div className="text-xl font-bold mt-1">
                {extra.sentiment.positive_pct != null ? `${extra.sentiment.positive_pct.toFixed(0)}%` : "--"}
              </div>
              <div className="text-xs text-gray-500">正面情绪</div>
            </div>
            <div className="flex-1">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-green-400">正面 {extra.sentiment.positive_pct?.toFixed(0) ?? "--"}%</span>
                <span className="text-red-400">负面 {extra.sentiment.negative_pct?.toFixed(0) ?? "--"}%</span>
              </div>
              {/* Progress bar */}
              <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full"
                  style={{ width: `${extra.sentiment.positive_pct ?? 50}%` }}
                />
              </div>
              {extra.sentiment.summary && (
                <p className="text-sm text-gray-300 mt-2">{extra.sentiment.summary}</p>
              )}
            </div>
          </div>
          {extra.sentiment.risks_found && extra.sentiment.risks_found.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">情绪风险信号</div>
              <div className="space-y-1">
                {extra.sentiment.risks_found.map((r, i) => (
                  <div key={i} className="text-xs text-orange-300 flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-orange-400 flex-shrink-0" />
                    {r}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* ── CryptoRank Fundraising ── */}
      {(extra.fundraise_rounds != null || extra.cryptorank_rank != null) && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">💰 融资 & VC 背景 (CryptoRank)</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
            {extra.cryptorank_rank != null && (
              <div className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-500">CryptoRank 排名</div>
                <div className="text-lg font-bold">#{extra.cryptorank_rank}</div>
              </div>
            )}
            {extra.fundraise_rounds != null && (
              <div className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-500">融资轮次</div>
                <div className="text-lg font-bold">{extra.fundraise_rounds}</div>
              </div>
            )}
            {extra.fundraise_total_usd != null && (
              <div className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-500">融资总额</div>
                <div className="text-lg font-bold">{formatUsd(extra.fundraise_total_usd)}</div>
              </div>
            )}
          </div>
          {extra.top_vcs && extra.top_vcs.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-2">主要投资机构</div>
              <div className="flex flex-wrap gap-1.5">
                {extra.top_vcs.map((vc, i) => (
                  <span key={i} className="text-xs bg-purple-900/40 text-purple-300 border border-purple-800 px-2 py-0.5 rounded">{vc}</span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* ── Score History ── */}
      {token.history_30d && token.history_30d.length > 1 && (
        <section className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-sm font-semibold mb-3 text-gray-400 uppercase tracking-wide">30 天评分趋势</h2>
          <ScoreHistory data={token.history_30d} />
        </section>
      )}

      {/* ── Report Modal ── */}
      {showReport && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">{symbol} 报告</h3>
              <button onClick={() => setShowReport(false)} className="text-gray-500 hover:text-white text-xl">✕</button>
            </div>
            <div className="text-sm text-gray-300 whitespace-pre-wrap font-mono">{report}</div>
          </div>
        </div>
      )}
    </main>
  );
}
