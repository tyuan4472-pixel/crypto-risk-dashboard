"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw, FileText, AlertTriangle } from "lucide-react";
import RiskRadarChart from "@/components/RiskRadarChart";
import ScoreHistory from "@/components/ScoreHistory";
import { fetchTokenDetail, triggerEvaluation, fetchTokenReport, TokenDetail } from "@/lib/api";

const DIM_LABELS: Record<string, string> = {
  liquidity: "市场流动性",
  volatility: "价格波动性",
  concentration: "持仓集中度",
  fundamental: "项目基本面",
  sentiment: "舆情异常",
  compliance: "交易所合规",
  security: "智能合约安全",
  macro: "宏观关联风险",
};

const INDICATOR_LABELS: Record<string, string> = {
  volume_mcap_ratio: "24h 成交量/市值比",
  liquidity_depth: "±2% 流动性深度",
  vol_7d_exceeded: "7d 波动率超阈值",
  top10_holder_ratio: "前10地址持仓占比",
  github_commits_30d: "GitHub 30天 Commits",
  team_verified: "团队身份验证",
  negative_sentiment_pct: "负面情绪占比",
  mentions_anomaly_7d: "7d 异常提及",
  exchange_delist_warning: "交易所下架风险",
  contract_audited: "合约审计状态",
  unlock_event_30d: "30d 代币解锁",
  btc_beta_anomaly: "BTC Beta 异常",
};

const RISK_LEVEL_COLORS: Record<string, string> = {
  "极低": "text-risk-minimal",
  "低": "text-risk-low",
  "中": "text-risk-medium",
  "高": "text-risk-high",
  "极高": "text-risk-extreme",
};

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-red-900/20 border-red-700 text-red-300",
  medium: "bg-orange-900/20 border-orange-700 text-orange-300",
  low: "bg-yellow-900/20 border-yellow-700 text-yellow-300",
};

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
      const data = await fetchTokenDetail(symbol);
      setToken(data);
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
      // 等待评估完成后刷新
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
      setReport("报告尚未生成 — 请先手动触发评估");
      setShowReport(true);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen p-6 max-w-5xl mx-auto">
        <div className="text-gray-500 mt-20 text-center">加载中...</div>
      </main>
    );
  }

  if (error || !token) {
    return (
      <main className="min-h-screen p-6 max-w-5xl mx-auto">
        <Link href="/" className="text-blue-400 hover:underline text-sm flex items-center gap-1 mb-8">
          <ArrowLeft className="w-4 h-4" /> 返回 Dashboard
        </Link>
        <div className="text-center mt-16">
          <AlertTriangle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg mb-2">
            未找到 {symbol?.toUpperCase()} 的评估数据
          </p>
          <p className="text-gray-600 text-sm mb-6">{error}</p>
          <button
            onClick={handleTrigger}
            disabled={triggering}
            className="px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 disabled:opacity-50"
          >
            {triggering ? "评估中..." : "手动触发评估"}
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-6 max-w-5xl mx-auto">
      {/* Back */}
      <Link
        href="/"
        className="text-blue-400 hover:underline text-sm flex items-center gap-1 mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> 返回 Dashboard
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">
            {token.symbol}
            <span className="text-gray-500 text-lg ml-2">{token.name}</span>
          </h1>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
            <span>
              总分: <span className="text-white font-bold text-lg">{token.total_score}</span>/100
            </span>
            <span className={`font-medium ${RISK_LEVEL_COLORS[token.risk_level] || ""}`}>
              {token.risk_level}风险
            </span>
            {token.price_usd && <span>${token.price_usd.toFixed(4)}</span>}
            {token.market_cap_usd && (
              <span>市值: ${(token.market_cap_usd / 1e6).toFixed(1)}M</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleLoadReport}
            className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg text-sm hover:bg-gray-700"
          >
            <FileText className="w-4 h-4" /> 报告
          </button>
          <button
            onClick={handleTrigger}
            disabled={triggering}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${triggering ? "animate-spin" : ""}`} />
            {triggering ? "评估中..." : "重新评估"}
          </button>
        </div>
      </div>

      {/* Radar Chart + Dimension Scores */}
      {token.dimensions && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">8 维度评分雷达图</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
              <RiskRadarChart dimensions={token.dimensions} />
            </div>
            <div className="grid grid-cols-2 gap-2 content-start">
              {Object.entries(token.dimensions).map(([key, value]) => (
                <div
                  key={key}
                  className="bg-gray-900 rounded p-3 border border-gray-800 text-sm"
                >
                  <div className="text-gray-400 text-xs">{DIM_LABELS[key] || key}</div>
                  <div className={`text-lg font-bold mt-1 ${
                    value >= 70 ? "text-risk-low" :
                    value >= 45 ? "text-risk-medium" :
                    "text-risk-high"
                  }`}>
                    {value.toFixed(1)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* 12 Indicators */}
      {token.indicators && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">12 项检查指标</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3 text-sm">
              {Object.entries(token.indicators).map(([key, value]) => (
                <div
                  key={key}
                  className="flex justify-between py-2 border-b border-gray-800/50"
                >
                  <span className="text-gray-400">
                    {INDICATOR_LABELS[key] || key}
                  </span>
                  <span className="font-mono">
                    {typeof value === "boolean" ? (
                      value ? (
                        <span className="text-red-400">⚠️ 是</span>
                      ) : (
                        <span className="text-green-400">✅ 否</span>
                      )
                    ) : value !== null && value !== undefined ? (
                      typeof value === "number" ? value.toFixed(4) : String(value)
                    ) : (
                      <span className="text-gray-600">--</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Risk Details */}
      {token.risk_details && token.risk_details.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">
            风险点明细 ({token.risk_details.length})
          </h2>
          <div className="space-y-3">
            {token.risk_details.map((detail, i) => (
              <div
                key={i}
                className={`rounded-lg border p-4 ${SEVERITY_STYLES[detail.severity] || "bg-gray-900 border-gray-800"}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium">{detail.category}</span>
                  <span className="text-xs uppercase opacity-60 px-1.5 py-0.5 border border-current rounded">
                    {detail.severity}
                  </span>
                </div>
                <p className="text-sm opacity-90">{detail.description}</p>
                {detail.source && (
                  <p className="text-xs opacity-50 mt-1">来源: {detail.source}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Score History */}
      {token.history_30d && token.history_30d.length > 1 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">30 天评分趋势</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <ScoreHistory data={token.history_30d} />
          </div>
        </section>
      )}

      {/* Sentiment Summary */}
      {token.sentiment_summary && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">舆情摘要</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4 text-sm text-gray-300 whitespace-pre-wrap">
            {token.sentiment_summary}
          </div>
        </section>
      )}

      {/* Report Modal */}
      {showReport && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">{symbol} 调研报告</h3>
              <button
                onClick={() => setShowReport(false)}
                className="text-gray-500 hover:text-white text-xl"
              >
                ✕
              </button>
            </div>
            <div className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
              {report}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
