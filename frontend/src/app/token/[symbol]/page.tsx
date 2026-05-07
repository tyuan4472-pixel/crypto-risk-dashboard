"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw, FileText } from "lucide-react";
import RiskRadarChart from "@/components/RiskRadarChart";
import { fetchTokenDetail, triggerEvaluation, TokenScore } from "@/lib/api";

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

const SEVERITY_COLORS: Record<string, string> = {
  high: "bg-risk-extreme/20 border-risk-extreme text-risk-extreme",
  medium: "bg-risk-high/20 border-risk-high text-risk-high",
  low: "bg-risk-medium/20 border-risk-medium text-risk-medium",
};

export default function TokenDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const [token, setToken] = useState<TokenScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    loadDetail();
  }, [symbol]);

  async function loadDetail() {
    setLoading(true);
    try {
      const data = await fetchTokenDetail(symbol);
      setToken(data);
    } catch {
      setToken(null);
    }
    setLoading(false);
  }

  async function handleTrigger() {
    setTriggering(true);
    try {
      await triggerEvaluation(symbol);
      // 等 3 秒后刷新
      setTimeout(() => {
        loadDetail();
        setTriggering(false);
      }, 3000);
    } catch {
      setTriggering(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen p-6 max-w-5xl mx-auto">
        <div className="text-gray-500 mt-20 text-center">加载中...</div>
      </main>
    );
  }

  if (!token) {
    return (
      <main className="min-h-screen p-6 max-w-5xl mx-auto">
        <Link href="/" className="text-blue-400 hover:underline text-sm flex items-center gap-1 mb-8">
          <ArrowLeft className="w-4 h-4" /> 返回 Dashboard
        </Link>
        <div className="text-gray-500 mt-20 text-center">
          <p className="text-lg mb-2">未找到 {symbol} 的评估数据</p>
          <button
            onClick={handleTrigger}
            disabled={triggering}
            className="mt-4 px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 disabled:opacity-50"
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
            <span>总分: <span className="text-white font-bold text-lg">{token.total_score}</span></span>
            <span className="text-risk-high font-medium">{token.risk_level}风险</span>
            {token.price_usd && <span>${token.price_usd.toFixed(4)}</span>}
          </div>
        </div>
        <button
          onClick={handleTrigger}
          disabled={triggering}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${triggering ? "animate-spin" : ""}`} />
          {triggering ? "评估中..." : "重新评估"}
        </button>
      </div>

      {/* Radar Chart */}
      {token.dimensions && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">维度评分雷达图</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <RiskRadarChart dimensions={token.dimensions} />
          </div>
          {/* Dimension Scores Table */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4">
            {Object.entries(token.dimensions).map(([key, value]) => (
              <div key={key} className="bg-gray-900 rounded p-3 border border-gray-800 text-sm">
                <div className="text-gray-400">{DIM_LABELS[key] || key}</div>
                <div className="text-lg font-bold mt-1">{value}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Indicators */}
      {token.indicators && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">12 项检查指标</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              {Object.entries(token.indicators).map(([key, value]) => (
                <div key={key} className="flex justify-between py-2 border-b border-gray-800/50">
                  <span className="text-gray-400">{key}</span>
                  <span className="font-mono">
                    {typeof value === "boolean"
                      ? value ? "✅" : "❌"
                      : value !== null ? String(value) : "--"}
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
          <h2 className="text-lg font-semibold mb-4">风险点明细</h2>
          <div className="space-y-3">
            {token.risk_details.map((detail, i) => (
              <div
                key={i}
                className={`bg-gray-900 rounded-lg border p-4 ${SEVERITY_COLORS[detail.severity] || "border-gray-800"}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium">{detail.category}</span>
                  <span className="text-xs uppercase opacity-70">{detail.severity}</span>
                </div>
                <p className="text-sm text-gray-300">{detail.description}</p>
                {detail.source && (
                  <p className="text-xs text-gray-500 mt-1">来源: {detail.source}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Sentiment Summary */}
      {token.sentiment_summary && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">舆情摘要</h2>
          <div className="bg-gray-900 rounded-lg border border-gray-800 p-4 text-sm text-gray-300">
            {token.sentiment_summary}
          </div>
        </section>
      )}
    </main>
  );
}
