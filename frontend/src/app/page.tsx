"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Search,
  RefreshCw,
  Play,
  ChevronLeft,
  ChevronRight,
  Shield,
  AlertTriangle,
  TrendingUp,
  Activity,
  Zap,
} from "lucide-react";
import TokenTable from "@/components/TokenTable";
import {
  fetchTokens,
  fetchSchedulerStatus,
  triggerFullScan,
  TokenScore,
  SchedulerStatus,
} from "@/lib/api";

export default function Dashboard() {
  const [tokens, setTokens] = useState<TokenScore[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [sortBy, setSortBy] = useState("total_score");
  const [sortOrder, setSortOrder] = useState("asc");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);

  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [scanning, setScanning] = useState(false);

  const [riskCounts, setRiskCounts] = useState<Record<string, number>>({});

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
      setRiskCounts(data.risk_counts || {});
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
      setTimeout(() => {
        loadTokens();
        fetchSchedulerStatus().then(setScheduler).catch(() => {});
        setScanning(false);
      }, 30000);
    } catch {
      setScanning(false);
    }
  }

  const highRiskCount = (riskCounts["高"] || 0) + (riskCounts["极高"] || 0);
  const mediumRiskCount = riskCounts["中"] || 0;
  const lowRiskCount = (riskCounts["低"] || 0) + (riskCounts["极低"] || 0);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <main className="min-h-screen max-w-7xl mx-auto px-6 py-8">
      {/* ── Header ── */}
      <header className="mb-10 animate-fade-in-up">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            {/* Gradient title */}
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 rounded-xl gradient-accent flex items-center justify-center flex-shrink-0">
                <Shield className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight gradient-text">
                Crypto Risk Dashboard
              </h1>
            </div>
            <p className="text-sm text-slate-500 pl-11">
              加密货币风控评估系统 — KuCoin 现货币种
            </p>
          </div>

          {/* Scan button */}
          <button
            onClick={handleFullScan}
            disabled={scanning}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium
                       gradient-accent text-white shadow-lg shadow-blue-500/20
                       hover:opacity-90 hover:shadow-blue-500/30
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200"
          >
            {scanning ? (
              <Activity className="w-4 h-4 animate-pulse" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            {scanning ? "扫描中..." : "全量扫描"}
          </button>
        </div>
      </header>

      {/* ── Scheduler Banner ── */}
      {scheduler && scheduler.status !== "no_scans" && (
        <div className="mb-6 px-4 py-3 glass-card flex items-center gap-4 text-xs text-slate-400 animate-fade-in-up">
          <span className="flex items-center gap-2">
            {scheduler.status === "completed" ? (
              <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
            ) : (
              <span className="relative flex w-2 h-2 flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-400" />
              </span>
            )}
            {scheduler.status}
          </span>
          {scheduler.total_tokens && (
            <span className="text-slate-500">
              {scheduler.completed}/{scheduler.total_tokens} 完成
              {scheduler.failed ? `, ${scheduler.failed} 失败` : ""}
            </span>
          )}
          {scheduler.started_at && (
            <span className="text-slate-600">
              开始: {new Date(scheduler.started_at).toLocaleString("zh-CN")}
            </span>
          )}
        </div>
      )}

      {/* ── Stats Cards ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 animate-fade-in-up delay-100">
        <StatCard
          label="评估币种"
          value={String(total)}
          icon={<TrendingUp className="w-5 h-5" />}
          iconColor="text-blue-400"
          glowColor="rgba(59,130,246,0.15)"
        />
        <StatCard
          label="高风险"
          value={String(highRiskCount)}
          icon={<AlertTriangle className="w-5 h-5" />}
          iconColor="text-rose-400"
          valueColor="text-rose-400"
          glowColor="rgba(244,63,94,0.15)"
        />
        <StatCard
          label="中风险"
          value={String(mediumRiskCount)}
          icon={<Activity className="w-5 h-5" />}
          iconColor="text-amber-400"
          valueColor="text-amber-400"
          glowColor="rgba(251,191,36,0.12)"
        />
        <StatCard
          label="低风险"
          value={String(lowRiskCount)}
          icon={<Shield className="w-5 h-5" />}
          iconColor="text-emerald-400"
          valueColor="text-emerald-400"
          glowColor="rgba(52,211,153,0.12)"
        />
      </div>

      {/* ── Toolbar ── */}
      <div className="flex flex-wrap gap-3 mb-6 items-center animate-fade-in-up delay-200">
        {/* Search */}
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
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
            className="glass-input w-full pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-600"
          />
        </div>

        {/* Risk Filter */}
        <select
          value={riskFilter}
          onChange={(e) => {
            setRiskFilter(e.target.value);
            setPage(1);
          }}
          className="glass-input px-3 py-2.5 text-sm text-slate-300 cursor-pointer"
        >
          <option value="" className="bg-gray-950">全部风险</option>
          <option value="极高" className="bg-gray-950">极高</option>
          <option value="高" className="bg-gray-950">高</option>
          <option value="中" className="bg-gray-950">中</option>
          <option value="低" className="bg-gray-950">低</option>
          <option value="极低" className="bg-gray-950">极低</option>
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
          className="glass-input px-3 py-2.5 text-sm text-slate-300 cursor-pointer"
        >
          <option value="total_score:asc" className="bg-gray-950">风险最高优先</option>
          <option value="total_score:desc" className="bg-gray-950">风险最低优先</option>
          <option value="market_cap_usd:desc" className="bg-gray-950">市值最大优先</option>
          <option value="volume_24h_usd:desc" className="bg-gray-950">交易量最大优先</option>
        </select>

        {/* Refresh */}
        <button
          onClick={loadTokens}
          className="glass-input p-2.5 text-slate-400 hover:text-slate-200 transition-colors"
          title="刷新"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="mb-5 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-400 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>
            {error}
            <span className="ml-2 text-xs text-slate-500">
              (确认后端已启动: docker compose up -d)
            </span>
          </span>
        </div>
      )}

      {/* ── Table ── */}
      <div className="animate-fade-in-up delay-300">
        <TokenTable tokens={tokens} loading={loading} />
      </div>

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 text-sm text-slate-500 animate-fade-in-up delay-400">
          <span>
            共 <span className="text-slate-300 font-medium">{total}</span> 个币种 · 第{" "}
            <span className="text-slate-300">{page}</span>/{totalPages} 页
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="glass-card p-2 rounded-xl text-slate-400 hover:text-white
                         disabled:opacity-30 disabled:cursor-not-allowed
                         hover:bg-white/[0.06] transition-all duration-200"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="glass-card p-2 rounded-xl text-slate-400 hover:text-white
                         disabled:opacity-30 disabled:cursor-not-allowed
                         hover:bg-white/[0.06] transition-all duration-200"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ── Footer ── */}
      <footer className="mt-12 text-center text-xs text-slate-700">
        Crypto Risk Dashboard v0.1 · Data: KuCoin + CMC + CoinGecko
      </footer>
    </main>
  );
}

/* ── StatCard ── */
function StatCard({
  label,
  value,
  icon,
  iconColor = "text-blue-400",
  valueColor = "text-slate-100",
  glowColor = "rgba(59,130,246,0.15)",
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  iconColor?: string;
  valueColor?: string;
  glowColor?: string;
}) {
  return (
    <div className="stat-card group cursor-default">
      {/* glow blob */}
      <div
        className="absolute -top-6 -right-6 w-24 h-24 rounded-full blur-2xl pointer-events-none animate-glow"
        style={{ background: glowColor }}
      />
      <div className="relative z-10">
        <div className={`${iconColor} mb-3`}>{icon}</div>
        <div className={`text-3xl font-bold tracking-tight mb-1 ${valueColor}`}>
          {value}
        </div>
        <div className="text-xs text-slate-500 font-medium">{label}</div>
      </div>
    </div>
  );
}
