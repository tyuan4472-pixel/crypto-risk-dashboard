"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, RefreshCw, Play, ChevronLeft, ChevronRight } from "lucide-react";
import TokenTable from "@/components/TokenTable";
import { fetchTokens, fetchSchedulerStatus, triggerFullScan, TokenScore, SchedulerStatus } from "@/lib/api";

export default function Dashboard() {
  const [tokens, setTokens] = useState<TokenScore[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选/排序/分页
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [sortBy, setSortBy] = useState("total_score");
  const [sortOrder, setSortOrder] = useState("asc");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);

  // 调度器状态
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [scanning, setScanning] = useState(false);

  const loadTokens = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTokens({
        risk_level: riskFilter || undefined,
        sort_by: sortBy,
        order: sortOrder,
        page,
        page_size: pageSize,
        search: search || undefined,
      });
      setTokens(data.tokens);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "无法连接后端 API");
      setTokens([]);
      setTotal(0);
    }
    setLoading(false);
  }, [riskFilter, sortBy, sortOrder, page, pageSize, search]);

  useEffect(() => {
    loadTokens();
  }, [loadTokens]);

  useEffect(() => {
    fetchSchedulerStatus()
      .then(setScheduler)
      .catch(() => setScheduler(null));
  }, []);

  async function handleFullScan() {
    setScanning(true);
    try {
      await triggerFullScan();
      // 30秒后刷新
      setTimeout(() => {
        loadTokens();
        fetchSchedulerStatus().then(setScheduler).catch(() => {});
        setScanning(false);
      }, 30000);
    } catch {
      setScanning(false);
    }
  }

  // 统计
  const highRiskCount = tokens.filter(
    (t) => t.risk_level === "高" || t.risk_level === "极高"
  ).length;
  const avgScore =
    tokens.length > 0
      ? (tokens.reduce((s, t) => s + t.total_score, 0) / tokens.length).toFixed(1)
      : "--";
  const totalPages = Math.ceil(total / pageSize);

  return (
    <main className="min-h-screen p-6 max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-1">Crypto Risk Dashboard</h1>
          <p className="text-gray-400 text-sm">
            加密货币风控评估系统 — KuCoin 现货币种
          </p>
        </div>
        {/* 全量扫描按钮 */}
        <button
          onClick={handleFullScan}
          disabled={scanning}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 disabled:opacity-50"
        >
          <Play className={`w-4 h-4 ${scanning ? "animate-pulse" : ""}`} />
          {scanning ? "扫描中..." : "全量扫描"}
        </button>
      </header>

      {/* Scheduler Status Banner */}
      {scheduler && scheduler.status !== "no_scans" && (
        <div className="mb-4 px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-xs text-gray-400 flex items-center gap-4">
          <span>
            最近扫描: {scheduler.status === "completed" ? "✅" : "⏳"} {scheduler.status}
          </span>
          {scheduler.total_tokens && (
            <span>
              {scheduler.completed}/{scheduler.total_tokens} 完成
              {scheduler.failed ? `, ${scheduler.failed} 失败` : ""}
            </span>
          )}
          {scheduler.started_at && (
            <span>
              开始: {new Date(scheduler.started_at).toLocaleString("zh-CN")}
            </span>
          )}
        </div>
      )}

      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="评估币种" value={String(total)} />
        <StatCard label="高风险" value={String(highRiskCount)} className="text-risk-high" />
        <StatCard label="平均分" value={avgScore} />
        <StatCard
          label="更新时间"
          value={
            tokens[0]?.evaluated_at
              ? new Date(tokens[0].evaluated_at).toLocaleDateString("zh-CN")
              : "--"
          }
          small
        />
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap gap-3 mb-6 items-center">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="搜索币种 Symbol 或名称..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                setPage(1);
                loadTokens();
              }
            }}
            className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Risk Filter */}
        <select
          value={riskFilter}
          onChange={(e) => {
            setRiskFilter(e.target.value);
            setPage(1);
          }}
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
            setPage(1);
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
          title="刷新"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-900/20 border border-red-800 rounded-lg text-sm text-red-400">
          ⚠️ {error}
          <span className="ml-2 text-xs text-gray-500">
            (确认后端已启动: docker compose up -d)
          </span>
        </div>
      )}

      {/* Table */}
      <TokenTable tokens={tokens} loading={loading} />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
          <span>
            共 {total} 个币种 · 第 {page}/{totalPages} 页
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 bg-gray-900 border border-gray-700 rounded disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 bg-gray-900 border border-gray-700 rounded disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-gray-600">
        Crypto Risk Dashboard v0.1 · Data: KuCoin + CMC + CoinGecko
      </footer>
    </main>
  );
}

function StatCard({
  label,
  value,
  className = "",
  small = false,
}: {
  label: string;
  value: string;
  className?: string;
  small?: boolean;
}) {
  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <div className="text-sm text-gray-400">{label}</div>
      <div className={`${small ? "text-lg" : "text-2xl"} font-bold mt-1 ${className}`}>
        {value}
      </div>
    </div>
  );
}
