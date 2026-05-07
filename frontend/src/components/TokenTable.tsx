"use client";

import { TokenScore } from "@/lib/api";
import Link from "next/link";

const RISK_COLORS: Record<string, string> = {
  "极低": "text-risk-minimal",
  "低": "text-risk-low",
  "中": "text-risk-medium",
  "高": "text-risk-high",
  "极高": "text-risk-extreme",
};

interface Props {
  tokens: TokenScore[];
  loading: boolean;
}

export default function TokenTable({ tokens, loading }: Props) {
  if (loading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-8 text-center text-gray-500">
        加载中...
      </div>
    );
  }

  if (tokens.length === 0) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-8 text-center text-gray-500">
        暂无数据 — 后端 API 尚未连接或评估任务尚未运行
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-left">
              <th className="px-4 py-3 font-medium">币种</th>
              <th className="px-4 py-3 font-medium">总分</th>
              <th className="px-4 py-3 font-medium">风险等级</th>
              <th className="px-4 py-3 font-medium">价格 (USD)</th>
              <th className="px-4 py-3 font-medium hidden md:table-cell">市值</th>
              <th className="px-4 py-3 font-medium hidden md:table-cell">24h 成交量</th>
              <th className="px-4 py-3 font-medium hidden lg:table-cell">评估时间</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((token) => (
              <tr
                key={token.symbol}
                className="border-b border-gray-800/50 hover:bg-gray-800/50 transition-colors"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/token/${token.symbol}`}
                    className="text-blue-400 hover:underline font-medium"
                  >
                    {token.symbol}
                  </Link>
                  <div className="text-xs text-gray-500">{token.name}</div>
                </td>
                <td className="px-4 py-3 font-mono">{token.total_score.toFixed(1)}</td>
                <td className="px-4 py-3">
                  <span className={`font-medium ${RISK_COLORS[token.risk_level] || ""}`}>
                    {token.risk_level}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono">
                  {token.price_usd ? `$${token.price_usd.toFixed(4)}` : "--"}
                </td>
                <td className="px-4 py-3 font-mono text-gray-400 hidden md:table-cell">
                  {token.market_cap_usd
                    ? `$${(token.market_cap_usd / 1e6).toFixed(1)}M`
                    : "--"}
                </td>
                <td className="px-4 py-3 font-mono text-gray-400 hidden md:table-cell">
                  {token.volume_24h_usd
                    ? `$${(token.volume_24h_usd / 1e6).toFixed(1)}M`
                    : "--"}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs hidden lg:table-cell">
                  {new Date(token.evaluated_at).toLocaleString("zh-CN")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
