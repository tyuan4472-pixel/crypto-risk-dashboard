"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface Props {
  data: Array<{ date: string; total_score: number }>;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const score = payload[0]?.value as number;
  return (
    <div
      style={{
        background: "rgba(15,15,20,0.92)",
        border: "1px solid rgba(59,130,246,0.3)",
        borderRadius: "12px",
        padding: "10px 14px",
        backdropFilter: "blur(12px)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.5)",
      }}
    >
      <p style={{ color: "#64748b", fontSize: 11, marginBottom: 4 }}>{label}</p>
      <p style={{ color: "#38bdf8", fontWeight: 700, fontSize: 18 }}>
        {score?.toFixed(1)}
        <span style={{ color: "#475569", fontWeight: 400, fontSize: 12 }}>/100</span>
      </p>
    </div>
  );
}

export default function ScoreHistory({ data }: Props) {
  const formatted = data.map((d) => ({
    ...d,
    dateLabel: new Date(d.date).toLocaleDateString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
    }),
  }));

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={formatted}
          margin={{ top: 8, right: 16, bottom: 0, left: -16 }}
        >
          <defs>
            {/* Blue→cyan gradient fill */}
            <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(56,189,248,0.3)" />
              <stop offset="75%" stopColor="rgba(59,130,246,0.05)" />
              <stop offset="100%" stopColor="transparent" />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="none"
            stroke="rgba(255,255,255,0.04)"
            vertical={false}
          />

          <XAxis
            dataKey="dateLabel"
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "#475569", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={32}
          />

          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(56,189,248,0.2)", strokeWidth: 1 }} />

          {/* Risk reference lines */}
          <ReferenceLine
            y={65}
            stroke="rgba(52,211,153,0.3)"
            strokeDasharray="4 4"
            label={{ value: "安全", position: "right", fill: "rgba(52,211,153,0.5)", fontSize: 10 }}
          />
          <ReferenceLine
            y={45}
            stroke="rgba(251,191,36,0.3)"
            strokeDasharray="4 4"
            label={{ value: "中", position: "right", fill: "rgba(251,191,36,0.5)", fontSize: 10 }}
          />
          <ReferenceLine
            y={25}
            stroke="rgba(244,63,94,0.3)"
            strokeDasharray="4 4"
            label={{ value: "危险", position: "right", fill: "rgba(244,63,94,0.5)", fontSize: 10 }}
          />

          <Area
            type="monotone"
            dataKey="total_score"
            stroke="rgba(56,189,248,0.9)"
            strokeWidth={2}
            fill="url(#scoreGradient)"
            dot={false}
            activeDot={{
              r: 5,
              fill: "#38bdf8",
              stroke: "rgba(56,189,248,0.4)",
              strokeWidth: 4,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
