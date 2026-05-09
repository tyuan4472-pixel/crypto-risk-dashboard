"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  RefreshCw,
  FileText,
  AlertTriangle,
  XCircle,
  Skull,
  Shield,
  Activity,
  BarChart2,
  Globe,
  Building,
  MessageSquare,
  DollarSign,
  TrendingDown,
  Zap,
} from "lucide-react";
import RiskRadarChart from "@/components/RiskRadarChart";
import ScoreHistory from "@/components/ScoreHistory";
import {
  fetchTokenDetail,
  triggerEvaluation,
  fetchTokenReport,
  TokenDetail,
} from "@/lib/api";

const RISK_BADGE: Record<string, { bg: string; text: string; border: string }> = {
  极低: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30" },
  低:   { bg: "bg-sky-500/10",     text: "text-sky-400",     border: "border-sky-500/30"     },
  中:   { bg: "bg-amber-500/10",   text: "text-amber-400",   border: "border-amber-500/30"   },
  高:   { bg: "bg-orange-500/10",  text: "text-orange-400",  border: "border-orange-500/30"  },
  极高: { bg: "bg-rose-500/10",    text: "text-rose-400",    border: "border-rose-500/30"    },
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

/* ── Section wrapper ── */
function Section({
  title,
  icon,
  children,
  accentColor = "border-blue-500",
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  accentColor?: string;
}) {
  return (
    <section className="glass-card p-6">
      <div className={`section-title ${accentColor}`}>
        <span className="flex items-center gap-2">
          {icon}
          {title}
        </span>
      </div>
      {children}
    </section>
  );
}

/* ── Mini metric card ── */
function MetricCard({
  label,
  value,
  valueClass = "text-slate-100",
}: {
  label: string;
  value: string | React.ReactNode;
  valueClass?: string;
}) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.05] rounded-xl p-4">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${valueClass}`}>{value}</div>
    </div>
  );
}

export default function TokenDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const [token, setToken] = useState<TokenDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [report, setReport] = useState<string | null>(null);
  const [showReport, setShowReport] = useState(false);

  useEffect(() => {
    loadDetail();
  }, [symbol]);

  async function loadDetail() {
    setLoading(true);
    setError(null);
    try {
      setToken(await fetchTokenDetail(symbol));
    } catch (err: any) {
      setError(err.message);
      setToken(null);
    }
    setLoading(false);
  }

  async function handleTrigger() {
    setTriggering(true);
    try {
      await triggerEvaluation(symbol);
      setTimeout(() => {
        loadDetail();
        setTriggering(false);
      }, 5000);
    } catch {
      setTriggering(false);
    }
  }

  async function handleLoadReport() {
    try {
      const data = await fetchTokenReport(symbol);
      setReport(data.content);
      setShowReport(true);
    } catch {
      setReport("报告尚未生成");
      setShowReport(true);
    }
  }

  /* ── Loading state ── */
  if (loading) {
    return (
      <main className="min-h-screen max-w-5xl mx-auto px-6 py-8">
        <div className="flex flex-col items-center justify-center mt-32 gap-4">
          <div className="w-10 h-10 rounded-full gradient-accent animate-spin opacity-80" />
          <p className="text-slate-500 text-sm">加载中...</p>
        </div>
      </main>
    );
  }

  /* ── Error / Not found state ── */
  if (error || !token) {
    return (
      <main className="min-h-screen max-w-5xl mx-auto px-6 py-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-blue-400
                     transition-colors duration-200 mb-10 group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform duration-200" />
          返回 Dashboard
        </Link>
        <div className="text-center mt-16">
          <AlertTriangle className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 text-lg mb-6">
            未找到 {symbol?.toUpperCase()} 的数据
          </p>
          <button
            onClick={handleTrigger}
            disabled={triggering}
            className="px-5 py-2.5 gradient-accent rounded-xl text-sm font-medium text-white
                       hover:opacity-90 disabled:opacity-50 transition-all duration-200"
          >
            {triggering ? "评估中..." : "触发评估"}
          </button>
        </div>
      </main>
    );
  }

  const zombie = token.zombie || { score: 0, flags: [] };
  const extra = token.extra || {};
  const ind = token.indicators || {};
  const riskBadge = RISK_BADGE[token.risk_level] || RISK_BADGE["中"];

  /* ── Score bar color ── */
  const scoreBarColor =
    token.total_score <= 25
      ? "from-rose-500 to-red-400"
      : token.total_score <= 45
      ? "from-orange-500 to-amber-400"
      : token.total_score <= 65
      ? "from-amber-500 to-yellow-400"
      : "from-emerald-500 to-green-400";

  return (
    <main className="min-h-screen max-w-5xl mx-auto px-6 py-8 space-y-6">
      {/* ── Back ── */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-blue-400
                   transition-colors duration-200 group"
      >
        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform duration-200" />
        返回 Dashboard
      </Link>

      {/* ── Hero Header ── */}
      <div className="glass-card p-6 animate-fade-in-up">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">
                {token.symbol}
              </h1>
              {token.name && (
                <span className="text-slate-500 text-lg">{token.name}</span>
              )}
              {/* Risk badge */}
              <span
                className={`badge-risk ${riskBadge.bg} ${riskBadge.text} ${riskBadge.border}`}
              >
                {token.risk_level}风险
              </span>
            </div>

            {/* Score bar */}
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-slate-500 font-medium">综合风险分</span>
                <span className="text-2xl font-bold text-slate-100">
                  {token.total_score}
                  <span className="text-sm text-slate-500 ml-1">/100</span>
                </span>
              </div>
              <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${scoreBarColor} transition-all duration-700`}
                  style={{ width: `${token.total_score}%` }}
                />
              </div>
            </div>

            {/* Market data pills */}
            <div className="flex items-center gap-2 flex-wrap text-sm">
              {token.price_usd != null && (
                <span className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-lg text-slate-300">
                  {formatUsd(token.price_usd)}
                </span>
              )}
              {token.market_cap_usd != null && (
                <span className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-lg text-slate-400">
                  市值 {formatUsd(token.market_cap_usd)}
                </span>
              )}
              {token.volume_24h_usd != null && (
                <span className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-lg text-slate-400">
                  24h量 {formatUsd(token.volume_24h_usd)}
                </span>
              )}
              {extra.market_cap_rank && (
                <span className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-lg text-slate-500">
                  #{extra.market_cap_rank}
                </span>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2.5 flex-shrink-0">
            <button
              onClick={handleLoadReport}
              className="flex items-center gap-2 px-4 py-2.5 glass-card rounded-xl
                         text-sm text-slate-300 hover:text-white hover:bg-white/[0.06]
                         transition-all duration-200 border border-white/[0.06]"
            >
              <FileText className="w-4 h-4" />
              报告
            </button>
            <button
              onClick={handleTrigger}
              disabled={triggering}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm
                         font-medium gradient-accent text-white
                         hover:opacity-90 disabled:opacity-50 transition-all duration-200
                         shadow-lg shadow-blue-500/20"
            >
              <RefreshCw className={`w-4 h-4 ${triggering ? "animate-spin" : ""}`} />
              {triggering ? "评估中..." : "重新评估"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Zombie Detection ── */}
      {zombie.score > 0 && (
        <section className="p-6 rounded-2xl border border-rose-500/30 bg-rose-500/[0.06] animate-fade-in-up">
          <div className="flex items-center gap-3 mb-4">
            <Skull className="w-5 h-5 text-rose-400" />
            <h2 className="text-sm font-semibold uppercase tracking-widest text-rose-300 border-l-2 border-rose-500 pl-3">
              僵尸币检测 — {zombie.score}/7
            </h2>
            {zombie.score >= 5 && (
              <span className="px-2.5 py-1 rounded-lg bg-rose-500/20 border border-rose-500/40 text-xs text-rose-300 font-semibold">
                ⚠️ 确认为僵尸币
              </span>
            )}
            {zombie.score >= 3 && zombie.score < 5 && (
              <span className="px-2.5 py-1 rounded-lg bg-orange-500/20 border border-orange-500/40 text-xs text-orange-300 font-semibold">
                ⚠️ 疑似僵尸币
              </span>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-sm">
            {zombie.flags.map((f, i) => (
              <div key={i} className="flex items-start gap-2 text-rose-300">
                <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
                {f}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Market Data Cards ── */}
      <Section title="市场概况" icon={<BarChart2 className="w-3.5 h-3.5" />}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="市值排名"
            value={extra.market_cap_rank ? `#${extra.market_cap_rank}` : "--"}
          />
          <MetricCard
            label="ATH 跌幅"
            value={formatPct(extra.ath_pct)}
            valueClass={
              extra.ath_pct != null && extra.ath_pct < -80 ? "text-rose-400" : "text-slate-100"
            }
          />
          <MetricCard
            label="流通率"
            value={
              extra.circulating_supply && extra.total_supply
                ? `${((extra.circulating_supply / extra.total_supply) * 100).toFixed(1)}%`
                : "--"
            }
          />
          <MetricCard
            label="持有者数"
            value={extra.holder_count?.toLocaleString() || "--"}
          />
          <MetricCard
            label="KuCoin 充值"
            value={
              extra.kucoin_deposit_enabled === false
                ? "❌ 已关闭"
                : extra.kucoin_deposit_enabled === true
                ? "✅ 正常"
                : "--"
            }
            valueClass={
              extra.kucoin_deposit_enabled === false
                ? "text-rose-400"
                : extra.kucoin_deposit_enabled === true
                ? "text-emerald-400"
                : "text-slate-500"
            }
          />
          <MetricCard
            label="KuCoin 提现"
            value={
              extra.kucoin_withdraw_enabled === false
                ? "❌ 已关闭"
                : extra.kucoin_withdraw_enabled === true
                ? "✅ 正常"
                : "--"
            }
            valueClass={
              extra.kucoin_withdraw_enabled === false
                ? "text-rose-400"
                : extra.kucoin_withdraw_enabled === true
                ? "text-emerald-400"
                : "text-slate-500"
            }
          />
          <MetricCard
            label="合约安全"
            value={
              ind.is_honeypot ? "🚨 蜜罐" : ind.contract_audited === true ? "✅ 已审计" : "--"
            }
            valueClass={
              ind.is_honeypot ? "text-rose-400" : ind.contract_audited === true ? "text-emerald-400" : "text-slate-500"
            }
          />
          <MetricCard
            label="GitHub 30d"
            value={extra.github_commits_30d != null ? String(extra.github_commits_30d) : "--"}
          />
        </div>
      </Section>

      {/* ── Radar + Fundamentals ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Section title="8 维度风险雷达" icon={<Activity className="w-3.5 h-3.5" />} accentColor="border-blue-500">
          <RiskRadarChart
            dimensions={
              token.dimensions || {
                liquidity: 0,
                volatility: 0,
                concentration: 0,
                fundamental: 0,
                sentiment: 0,
                compliance: 0,
                security: 0,
                macro: 0,
              }
            }
          />
        </Section>

        <Section title="项目基本面" icon={<Shield className="w-3.5 h-3.5" />} accentColor="border-cyan-500">
          <div className="space-y-1 text-sm">
            {[
              {
                label: "开发者评分",
                value: extra.developer_score?.toFixed(1) || "--",
                valueClass:
                  extra.developer_score != null && extra.developer_score > 60
                    ? "text-emerald-400"
                    : "text-slate-300",
              },
              { label: "社区评分", value: extra.community_score?.toFixed(1) || "--" },
              {
                label: "GitHub 30d 提交",
                value: extra.github_commits_30d != null ? String(extra.github_commits_30d) : "--",
              },
              {
                label: "前10持仓占比",
                value:
                  extra.top10_holder_ratio != null
                    ? `${(extra.top10_holder_ratio * 100).toFixed(1)}%`
                    : "--",
                valueClass:
                  extra.top10_holder_ratio != null && extra.top10_holder_ratio > 0.7
                    ? "text-rose-400"
                    : "text-slate-300",
              },
              {
                label: "合约审计",
                value: ind.contract_audited === true ? "✅ 是" : ind.contract_audited === false ? "❌ 否" : "--",
                valueClass:
                  ind.contract_audited === true ? "text-emerald-400" : ind.contract_audited === false ? "text-rose-400" : "text-slate-500",
              },
              {
                label: "代理合约",
                value: ind.is_proxy ? "⚠️ 可升级" : "✅ 不可升级",
                valueClass: ind.is_proxy ? "text-orange-400" : "text-emerald-400",
              },
              {
                label: "蜜罐检测",
                value: ind.is_honeypot ? "🚨 蜜罐" : "✅ 安全",
                valueClass: ind.is_honeypot ? "text-rose-400" : "text-emerald-400",
              },
            ].map((row, i, arr) => (
              <div
                key={i}
                className={`flex justify-between items-center py-2.5 ${
                  i < arr.length - 1 ? "border-b border-white/[0.04]" : ""
                }`}
              >
                <span className="text-slate-400">{row.label}</span>
                <span className={`font-medium ${row.valueClass || "text-slate-300"}`}>
                  {row.value}
                </span>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* ── Risk Details ── */}
      {token.risk_details && token.risk_details.length > 0 && (
        <Section
          title={`风险点明细 (${token.risk_details.length})`}
          icon={<AlertTriangle className="w-3.5 h-3.5" />}
          accentColor="border-rose-500"
        >
          <div className="space-y-2.5">
            {token.risk_details.map((d, i) => (
              <div
                key={i}
                className={`rounded-xl border p-4 text-sm transition-all duration-200 ${
                  d.severity === "critical"
                    ? "bg-rose-500/10 border-rose-500/30"
                    : d.severity === "high"
                    ? "bg-rose-500/[0.07] border-rose-500/20"
                    : d.severity === "medium"
                    ? "bg-orange-500/[0.07] border-orange-500/20"
                    : "bg-white/[0.02] border-white/[0.05]"
                }`}
              >
                <div className="flex items-center gap-2.5 mb-2">
                  <span className="font-semibold text-slate-200">{d.category}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-md border font-medium ${
                      d.severity === "critical" || d.severity === "high"
                        ? "border-rose-500/40 text-rose-400 bg-rose-500/10"
                        : d.severity === "medium"
                        ? "border-orange-500/40 text-orange-400 bg-orange-500/10"
                        : "border-slate-600/40 text-slate-400"
                    }`}
                  >
                    {d.severity}
                  </span>
                </div>
                <p className="text-slate-400">{d.description}</p>
                {d.source && (
                  <p className="text-xs text-slate-600 mt-1.5">来源: {d.source}</p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Exchange Distribution ── */}
      {(extra.exchange_count != null || extra.cex_count != null) && (
        <Section title="交易所分布" icon={<Building className="w-3.5 h-3.5" />} accentColor="border-blue-500">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <MetricCard label="上线交易所" value={`${extra.exchange_count ?? "--"} 家`} />
            <MetricCard label="主流 CEX" value={`${extra.cex_count ?? "--"} 家`} />
            <MetricCard
              label="流动性风险"
              value={
                (extra.cex_count ?? 0) >= 10
                  ? "低风险"
                  : (extra.cex_count ?? 0) >= 5
                  ? "中风险"
                  : "高风险"
              }
              valueClass={
                (extra.cex_count ?? 0) >= 10
                  ? "text-emerald-400"
                  : (extra.cex_count ?? 0) >= 5
                  ? "text-amber-400"
                  : "text-rose-400"
              }
            />
            <MetricCard
              label="KuCoin 量占比"
              value={
                extra.kucoin_volume_share != null
                  ? `${extra.kucoin_volume_share.toFixed(1)}%`
                  : "--"
              }
            />
          </div>
          {extra.major_exchanges && extra.major_exchanges.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2">
                主流交易所覆盖 ({extra.major_exchanges.length}/13)
              </div>
              <div className="flex flex-wrap gap-1.5">
                {extra.major_exchanges.map((ex, i) => (
                  <span
                    key={i}
                    className="text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2.5 py-1 rounded-lg"
                  >
                    {ex}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* ── Cross Validation ── */}
      {extra.cg_cmc_divergence_pct != null && (
        <Section title="数据交叉验证 (CG vs CMC)" icon={<Activity className="w-3.5 h-3.5" />} accentColor="border-purple-500">
          <div className="flex items-center gap-6">
            <div
              className={`text-3xl font-bold ${
                extra.cg_cmc_divergence_pct > 10
                  ? "text-rose-400"
                  : extra.cg_cmc_divergence_pct > 5
                  ? "text-amber-400"
                  : "text-emerald-400"
              }`}
            >
              {extra.cg_cmc_divergence_pct.toFixed(2)}%
            </div>
            <div>
              <div className="text-sm text-slate-300">
                {extra.cg_cmc_divergence_pct > 10
                  ? "⚠️ 数据差异较大 — 可能存在数据操纵或双重计算"
                  : extra.cg_cmc_divergence_pct > 5
                  ? "⚡ 轻微差异 — 数据源口径不同"
                  : "✅ 一致 — CG 与 CMC 数据吻合"}
              </div>
              <div className="text-xs text-slate-600 mt-1">
                流通量差异百分比 (CoinGecko vs CoinMarketCap)
              </div>
            </div>
          </div>
        </Section>
      )}

      {/* ── KuCoin Market Card ── */}
      {(extra.kucoin_best_bid != null || extra.kucoin_best_ask != null) && (
        <Section title="KuCoin 盘口数据" icon={<BarChart2 className="w-3.5 h-3.5" />} accentColor="border-cyan-500">
          <div className="grid grid-cols-3 gap-3 mb-3">
            <MetricCard
              label="最优买价 (Bid)"
              value={
                extra.kucoin_best_bid != null
                  ? `$${extra.kucoin_best_bid.toPrecision(6)}`
                  : "--"
              }
              valueClass="text-emerald-400"
            />
            <MetricCard
              label="最优卖价 (Ask)"
              value={
                extra.kucoin_best_ask != null
                  ? `$${extra.kucoin_best_ask.toPrecision(6)}`
                  : "--"
              }
              valueClass="text-rose-400"
            />
            <MetricCard
              label="价差 (Spread)"
              value={
                extra.kucoin_spread_pct != null
                  ? `${extra.kucoin_spread_pct.toFixed(4)}%`
                  : "--"
              }
              valueClass={
                extra.kucoin_spread_pct != null && extra.kucoin_spread_pct > 1
                  ? "text-rose-400"
                  : extra.kucoin_spread_pct != null && extra.kucoin_spread_pct > 0.3
                  ? "text-amber-400"
                  : "text-emerald-400"
              }
            />
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`text-xs px-2.5 py-1 rounded-lg border ${
                extra.kucoin_deposit_enabled === false || extra.kucoin_withdraw_enabled === false
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-400"
                  : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              }`}
            >
              {extra.kucoin_deposit_enabled === false ? "⚠️ ST 限制" : "正常交易"}
            </span>
            {extra.kucoin_spread_pct != null && extra.kucoin_spread_pct > 1 && (
              <span className="text-xs text-orange-400">⚠️ 价差过大，流动性差</span>
            )}
          </div>
        </Section>
      )}

      {/* ── Sentiment ── */}
      {extra.sentiment && (
        <Section title="社区情绪分析" icon={<MessageSquare className="w-3.5 h-3.5" />} accentColor="border-violet-500">
          <div className="flex items-center gap-6 mb-4">
            {/* Gauge */}
            <div className="flex flex-col items-center flex-shrink-0">
              <div className="relative w-24 h-12 overflow-hidden">
                <div className="absolute inset-0 rounded-t-full bg-gradient-to-r from-rose-500 via-amber-400 to-emerald-500 opacity-25" />
                <div
                  className="absolute bottom-0 left-1/2 w-1 h-10 bg-white rounded-full origin-bottom"
                  style={{
                    transform: `translateX(-50%) rotate(${
                      ((extra.sentiment.positive_pct ?? 50) - 50) * 0.9
                    }deg)`,
                  }}
                />
              </div>
              <div className="text-2xl font-bold mt-1 gradient-text">
                {extra.sentiment.positive_pct != null
                  ? `${extra.sentiment.positive_pct.toFixed(0)}%`
                  : "--"}
              </div>
              <div className="text-xs text-slate-500">正面情绪</div>
            </div>

            <div className="flex-1">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-emerald-400">
                  正面 {extra.sentiment.positive_pct?.toFixed(0) ?? "--"}%
                </span>
                <span className="text-rose-400">
                  负面 {extra.sentiment.negative_pct?.toFixed(0) ?? "--"}%
                </span>
              </div>
              <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-green-400 rounded-full transition-all duration-700"
                  style={{ width: `${extra.sentiment.positive_pct ?? 50}%` }}
                />
              </div>
              {extra.sentiment.summary && (
                <p className="text-sm text-slate-300 mt-3">{extra.sentiment.summary}</p>
              )}
            </div>
          </div>
          {extra.sentiment.risks_found && extra.sentiment.risks_found.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2">情绪风险信号</div>
              <div className="space-y-1.5">
                {extra.sentiment.risks_found.map((r, i) => (
                  <div key={i} className="text-xs text-orange-300 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-orange-400 flex-shrink-0" />
                    {r}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* ── Fundraising ── */}
      {(extra.fundraise_rounds != null || extra.cryptorank_rank != null) && (
        <Section title="融资 & VC 背景 (CryptoRank)" icon={<DollarSign className="w-3.5 h-3.5" />} accentColor="border-purple-500">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
            {extra.cryptorank_rank != null && (
              <MetricCard label="CryptoRank 排名" value={`#${extra.cryptorank_rank}`} />
            )}
            {extra.fundraise_rounds != null && (
              <MetricCard label="融资轮次" value={String(extra.fundraise_rounds)} />
            )}
            {extra.fundraise_total_usd != null && (
              <MetricCard label="融资总额" value={formatUsd(extra.fundraise_total_usd)} />
            )}
          </div>
          {extra.top_vcs && extra.top_vcs.length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2">主要投资机构</div>
              <div className="flex flex-wrap gap-1.5">
                {extra.top_vcs.map((vc, i) => (
                  <span
                    key={i}
                    className="text-xs bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2.5 py-1 rounded-lg"
                  >
                    {vc}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* ── Score History ── */}
      {token.history_30d && token.history_30d.length > 1 && (
        <Section title="30 天评分趋势" icon={<TrendingDown className="w-3.5 h-3.5" />} accentColor="border-blue-500">
          <ScoreHistory data={token.history_30d} />
        </Section>
      )}

      {/* ── Report Modal ── */}
      {showReport && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-card max-w-3xl w-full max-h-[80vh] overflow-y-auto p-6 animate-fade-in-up">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-lg font-bold gradient-text">{symbol} 报告</h3>
              <button
                onClick={() => setShowReport(false)}
                className="w-8 h-8 rounded-lg bg-white/[0.05] hover:bg-white/[0.10]
                           text-slate-400 hover:text-white flex items-center justify-center
                           transition-all duration-200"
              >
                ✕
              </button>
            </div>
            <div className="text-sm text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
              {report}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
