/**
 * API 客户端 — 与后端 FastAPI 通信
 *
 * 环境变量: NEXT_PUBLIC_API_URL (默认 http://localhost:8000)
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

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
  volume_mcap_ratio?: number | null;
  market_cap_rank?: number | null;
  liquidity_depth?: number | null;
  vol_30d_exceeded?: boolean;
  top10_holder_ratio?: number | null;
  holder_count?: number | null;
  github_commits_30d?: number | null;
  developer_score?: number | null;
  community_score?: number | null;
  team_verified?: boolean;
  negative_sentiment_pct?: number | null;
  mentions_anomaly_7d?: boolean;
  exchange_delist_warning?: boolean;
  contract_audited?: boolean | null;
  is_honeypot?: boolean;
  is_proxy?: boolean;
  unlock_event_30d?: boolean;
  btc_beta_anomaly?: boolean;
  kucoin_deposit_enabled?: boolean | null;
  kucoin_withdraw_enabled?: boolean | null;
  ath_pct?: number | null;
  circulating_supply?: number | null;
  total_supply?: number | null;
}

export interface ZombieDetection {
  score: number;
  flags: string[];
}

export interface ExchangeDistribution {
  exchange_count?: number | null;
  cex_count?: number | null;
  major_exchanges?: string[];
  kucoin_volume_share?: number | null;
}

export interface CrossValidation {
  cg_cmc_divergence_pct?: number | null;
}

export interface SentimentData {
  positive_pct?: number | null;
  negative_pct?: number | null;
  summary?: string | null;
  risks_found?: string[];
}

export interface KuCoinMarket {
  best_bid?: number | null;
  best_ask?: number | null;
  spread_pct?: number | null;
}

export interface CryptoRankData {
  rank?: number | null;
  fundraise_rounds?: number | null;
  fundraise_total_usd?: number | null;
  top_vcs?: string[];
}

export interface ExtraData {
  market_cap_rank?: number | null;
  holder_count?: number | null;
  ath_pct?: number | null;
  circulating_supply?: number | null;
  total_supply?: number | null;
  kucoin_deposit_enabled?: boolean | null;
  kucoin_withdraw_enabled?: boolean | null;
  github_commits_30d?: number | null;
  developer_score?: number | null;
  community_score?: number | null;
  top10_holder_ratio?: number | null;
  // Exchange distribution
  exchange_count?: number | null;
  cex_count?: number | null;
  major_exchanges?: string[];
  kucoin_volume_share?: number | null;
  // Cross-validation
  cg_cmc_divergence_pct?: number | null;
  // CryptoRank
  cryptorank_rank?: number | null;
  fundraise_total_usd?: number | null;
  fundraise_rounds?: number | null;
  top_vcs?: string[];
  // KuCoin orderbook
  kucoin_best_bid?: number | null;
  kucoin_best_ask?: number | null;
  kucoin_spread_pct?: number | null;
  // Sentiment
  sentiment?: SentimentData | null;
  // LLM Analysis
  llm_analysis?: LLMAnalysis | null;
}

export interface RiskDetail {
  category: string;
  severity: string;
  description: string;
  source: string;
  detected_at?: string;
}

export interface LLMRecommendation {
  priority: string;
  action: string;
  reason: string;
}

export interface LLMAnalysis {
  summary?: string;
  key_risks?: string[];
  safe_factors?: string[];
  recommendations?: LLMRecommendation[];
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
  zombie?: ZombieDetection;
  risk_details?: RiskDetail[];
  extra?: ExtraData;
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
