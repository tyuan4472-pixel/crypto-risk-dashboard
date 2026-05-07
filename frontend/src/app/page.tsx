"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, Search, ChevronDown, RefreshCw } from "lucide-react";
import TokenTable from "@/components/TokenTable";
import { fetchTokens, TokenScore } from "@/lib/api";

const RISK_COLORS: Record<string, string> = {
  "极低": "text-risk-minimal",
  "低": "text-risk-low",
  "中": "text-risk-medium",
  "高": "text-risk-high",
  "极高": "text-risk-extreme",
};

const RISK_BG: Record<string, string> = {
  "极低": "bg-risk-minimal/20",
  "低": "bg-risk-low/20",
  "中": "bg-risk-medium/20",
  "高": "bg-risk-high/20",
  "极高": "bg-risk-extreme/20",
};

export default function Dashboard() {
  const [tokens, setTokens] = useState<TokenScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [sortBy, setSortBy] = useState("total_score");
  const [sortOrder, setSortOrder] = useState("asc");

  useEffect(() => {
    loadTokens();
  }, [riskFilter, sortBy, sortOrder]);

  async function loadTokens() {
    setLoading(true);
    try {
      const data = await fetchTokens({
        risk_level: riskFilter || undefined,
        sort_by: sortBy,
        order: sortOrder,
        search: search || undefined,
      });
      setTokens(data.tokens);
    } catch (err) {
      console.error(err);
      // Show demo data if API not available
      setTokens([]);
    }
    setLoading(false);
  }

  // 统计数据
  const totalCount = tokens.length || 0;
  const highRiskCount = tokens.filter((t) => t.risk_level === "高" || t.risk_level === "极高").length;

  return (
    <main className="min-h-screen p-6 max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-8">
        <h1 className="text-2xl font-bold mb-2">Crypto Risk Dashboard</h1>
        <p className="text-gray-400">加密货币风控评估系统 — 基于 KuCoin 现货币种</p>
      </header>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-sm text-gray-400">评估币种</div>
          <div className="text-2xl font-bold mt-1">{totalCount}</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-sm text-gray-400">高风险</div>
          <div className="text-2xl font-bold mt-1 text-risk-high">
            {highRiskCount}
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-sm text-gray-400">平均分</div>
          <div className="text-2xl font-bold mt-1">
            {tokens.length > 0
              ? (tokens.reduce((s, t) => s + t.total_score, 0) / tokens.length).toFixed(1)
              : "--"}
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-sm text-gray-400">更新时间</div>
          <div className="text-lg font-bold mt-1 text-gray-400">
            {tokens[0]?.evaluated_at
              ? new Date(tokens[0].evaluated_at).toLocaleDateString("zh-CN")
              : "--"}
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap gap-3 mb-6 items-center">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="搜索币种..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadTokens()}
            className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Risk Filter */}
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm"
        >
          <option value="">全部风险</option>
          <option value="极高">极高</option>
          <option value="高">高</option>
          <option value="中">中</option>
          <option value="低">低</option>
          <option value="极低">极低</option>
        </select>

        {/* Sort */}
        <select
          value={`${sortBy}:${sortOrder}`}
          onChange={(e) => {
            const [by, order] = e.target.value.split(":");
            setSortBy(by);
            setSortOrder(order);
          }}
          className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm"
        >
          <option value="total_score:asc">风险最高优先</option>
          <option value="total_score:desc">风险最低优先</option>
          <option value="market_cap_usd:desc">市值最大优先</option>
          <option value="volume_24h_usd:desc">交易量最大优先</option>
        </select>

        {/* Refresh */}
        <button
          onClick={loadTokens}
          className="p-2 bg-gray-900 border border-gray-700 rounded-lg hover:bg-gray-800"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Table */}
      <TokenTable tokens={tokens} loading={loading} />

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-gray-600">
        Crypto Risk Dashboard v0.1 · 数据来源: KuCoin + CMC + CoinGecko
      </footer>
    </main>
  );
}
