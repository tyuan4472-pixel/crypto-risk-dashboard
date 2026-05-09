"use client";

import { TokenScore } from "@/lib/api";
import Link from "next/link";

const RISK_BADGE: Record<string, { bg: string; text: string; border: string }> = {
  极低: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
  低:   { bg: "bg-sky-500/10",     text: "text-sky-400",     border: "border-sky-500/20"     },
  中:   { bg: "bg-amber-500/10",   text: "text-amber-400",   border: "border-amber-500/20"   },
  高:   { bg: "bg-orange-500/10",  text: "text-orange-400",  border: "border-orange-500/20"  },
  极高: { bg: "bg-rose-500/10",    text: "text-rose-400",    border: "border-rose-500/20"    },
};

interface Props {
  tokens: TokenScore[];
  loading: boolean;
}

export default function TokenTable({ tokens, loading }: Props) {
  if (loading) {
    return (
      <div className="glass-card p-12 text-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full gradient-accent animate-spin opacity-60" />
          <span className="text-slate-500 text-sm">加载中...</span>
        </div>
      </div>
    );
  }

  if (tokens.length === 0) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-slate-500 text-sm">
          暂无数据 — 后端 API 尚未连接或评估任务尚未运行
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/[0.05] text-xs text-slate-500 uppercase tracking-wider">
              <th className="px-6 py-4 font-medium text-left">币种</th>
              <th className="px-6 py-4 font-medium text-left">总分</th>
              <th className="px-6 py-4 font-medium text-left">风险等级</th>
              <th className="px-6 py-4 font-medium text-left">价格 (USD)</th>
              <th className="px-6 py-4 font-medium text-left hidden md:table-cell">市值</th>
              <th className="px-6 py-4 font-medium text-left hidden md:table-cell">24h 成交量</th>
              <th className="px-6 py-4 font-medium text-left hidden lg:table-cell">评估时间</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((token, i) => {
              const badge = RISK_BADGE[token.risk_level] || RISK_BADGE["中"];
              return (
                <tr
                  key={token.symbol}
                  className="token-table-row group"
                  style={{ animationDelay: `${Math.min(i * 20, 400)}ms` }}
                >
                  <td className="px-6 py-4">
                    <Link
                      href={`/token/${token.symbol}`}
                      className="text-blue-400 hover:text-cyan-400 font-semibold transition-colors duration-200"
                    >
                      {token.symbol}
                    </Link>
                    {token.name && (
                      <div className="text-xs text-slate-600 mt-0.5">{token.name}</div>
                    )}
                  </td>

                  <td className="px-6 py-4">
                    <span className="font-mono text-slate-200">
                      {token.total_score.toFixed(1)}
                    </span>
                  </td>

                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold border
                                  ${badge.bg} ${badge.text} ${badge.border}`}
                    >
                      {token.risk_level}
                    </span>
                  </td>

                  <td className="px-6 py-4 font-mono text-slate-300">
                    {token.price_usd ? `$${token.price_usd.toFixed(4)}` : "--"}
                  </td>

                  <td className="px-6 py-4 font-mono text-slate-400 hidden md:table-cell">
                    {token.market_cap_usd
                      ? `$${(token.market_cap_usd / 1e6).toFixed(1)}M`
                      : "--"}
                  </td>

                  <td className="px-6 py-4 font-mono text-slate-400 hidden md:table-cell">
                    {token.volume_24h_usd
                      ? `$${(token.volume_24h_usd / 1e6).toFixed(1)}M`
                      : "--"}
                  </td>

                  <td className="px-6 py-4 text-slate-600 text-xs hidden lg:table-cell">
                    {new Date(token.evaluated_at).toLocaleString("zh-CN")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
