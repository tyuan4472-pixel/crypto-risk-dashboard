const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TokenScore {
  symbol: string;
  name: string;
  total_score: number;
  risk_level: string;
  price_usd?: number;
  market_cap_usd?: number;
  volume_24h_usd?: number;
  dimensions?: Record<string, number>;
  indicators?: Record<string, any>;
  risk_details?: Array<{
    category: string;
    severity: string;
    description: string;
    source: string;
  }>;
  sentiment_summary?: string;
  evaluated_at: string;
}

export async function fetchTokens(params?: {
  risk_level?: string;
  sort_by?: string;
  order?: string;
  page?: number;
  page_size?: number;
  search?: string;
}): Promise<{ tokens: TokenScore[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.risk_level) query.set("risk_level", params.risk_level);
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.order) query.set("order", params.order);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  if (params?.search) query.set("search", params.search);

  const res = await fetch(`${API_BASE}/api/tokens?${query}`);
  if (!res.ok) throw new Error("Failed to fetch tokens");
  return res.json();
}

export async function fetchTokenDetail(symbol: string): Promise<TokenScore> {
  const res = await fetch(`${API_BASE}/api/tokens/${symbol}`);
  if (!res.ok) throw new Error("Failed to fetch token detail");
  return res.json();
}

export async function triggerEvaluation(symbol: string): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/tokens/${symbol}/trigger`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger evaluation");
  return res.json();
}
