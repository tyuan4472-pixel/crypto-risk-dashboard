/**
 * API 客户端 — 与后端 FastAPI 通信
 *
 * 环境变量: NEXT_PUBLIC_API_URL (默认 http://localhost:8000)
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ═══════════════════════════════════════════
// 类型定义
// ═══════════════════════════════════════════

export interface DimensionScores {
  [key: string]: number;
  liquidity: number;
  volatility: number;
  concentration: number;
  fundamental: number;
  sentiment: number;
  compliance: number;
  security: number;
  macro: number;
}

export interface CheckIndicators {
  volume_mcap_ratio?: number;
  liquidity_depth?: number;
  vol_7d_exceeded?: boolean;
  top10_holder_ratio?: number;
  github_commits_30d?: number;
  team_verified?: boolean;
  negative_sentiment_pct?: number;
  mentions_anomaly_7d?: boolean;
  exchange_delist_warning?: boolean;
  contract_audited?: boolean;
  unlock_event_30d?: boolean;
  btc_beta_anomaly?: boolean;
}

export interface RiskDetail {
  category: string;
  severity: string;
  description: string;
  source: string;
  detected_at?: string;
}

export interface TokenScore {
  symbol: string;
  name: string;
  total_score: number;
  risk_level: string;
  price_usd?: number;
  market_cap_usd?: number;
  volume_24h_usd?: number;
  evaluated_at: string;
}

export interface TokenDetail extends TokenScore {
  dimensions?: DimensionScores;
  indicators?: CheckIndicators;
  risk_details?: RiskDetail[];
  sentiment_summary?: string;
  history_30d?: Array<{ date: string; total_score: number }>;
}

export interface TokenListResponse {
  tokens: TokenScore[];
  total: number;
  page: number;
  page_size: number;
}

export interface SchedulerStatus {
  batch_id?: string;
  status: string;
  total_tokens?: number;
  completed?: number;
  failed?: number;
  started_at?: string;
  finished_at?: string;
  message?: string;
}

// ═══════════════════════════════════════════
// API 调用
// ═══════════════════════════════════════════

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error: ${res.status}`);
  }

  return res.json();
}

/**
 * 获取币种列表 (带筛选/排序/分页)
 */
export async function fetchTokens(params?: {
  risk_level?: string;
  sort_by?: string;
  order?: string;
  page?: number;
  page_size?: number;
  search?: string;
}): Promise<TokenListResponse> {
  const query = new URLSearchParams();
  if (params?.risk_level) query.set("risk_level", params.risk_level);
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.order) query.set("order", params.order);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  if (params?.search) query.set("search", params.search);

  return apiFetch<TokenListResponse>(`/api/tokens?${query}`);
}

/**
 * 获取单币种详细评分
 */
export async function fetchTokenDetail(symbol: string): Promise<TokenDetail> {
  return apiFetch<TokenDetail>(`/api/tokens/${encodeURIComponent(symbol)}`);
}

/**
 * 手动触发单币种评估
 */
export async function triggerEvaluation(
  symbol: string
): Promise<{ task_id: string; status: string }> {
  return apiFetch(`/api/tokens/${encodeURIComponent(symbol)}/trigger`, {
    method: "POST",
  });
}

/**
 * 获取调度器状态 (最近一次扫描)
 */
export async function fetchSchedulerStatus(): Promise<SchedulerStatus> {
  return apiFetch<SchedulerStatus>("/api/scheduler/status");
}

/**
 * 触发全量扫描
 */
export async function triggerFullScan(): Promise<{ task_id: string; status: string }> {
  return apiFetch("/api/scheduler/trigger", { method: "POST" });
}

/**
 * 获取币种报告
 */
export async function fetchTokenReport(
  symbol: string,
  reportType: string = "full"
): Promise<{ symbol: string; content: string; generated_at: string }> {
  return apiFetch(`/api/tokens/${encodeURIComponent(symbol)}/report?report_type=${reportType}`);
}
