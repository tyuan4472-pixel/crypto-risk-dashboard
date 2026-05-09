"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface Props {
  dimensions: Record<string, number>;
}

const LABELS: Record<string, string> = {
  liquidity: "流动性",
  volatility: "波动性",
  concentration: "集中度",
  fundamental: "基本面",
  sentiment: "舆情",
  compliance: "合规",
  security: "安全性",
  macro: "宏观",
};

/* Custom tooltip */
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
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
      <p style={{ color: "#94a3b8", fontSize: 11, marginBottom: 4 }}>
        {item.payload?.dimension}
      </p>
      <p style={{ color: "#38bdf8", fontWeight: 700, fontSize: 16 }}>
        {item.value}
        <span style={{ color: "#475569", fontWeight: 400, fontSize: 12 }}>/100</span>
      </p>
    </div>
  );
}

export default function RiskRadarChart({ dimensions }: Props) {
  const data = Object.entries(dimensions).map(([key, value]) => ({
    dimension: LABELS[key] || key,
    score: value,
    fullMark: 100,
  }));

  return (
    <div className="w-full h-80 animate-radar-glow">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          {/* Subtle concentric grid */}
          <PolarGrid
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={1.5}
            gridType="polygon"
          />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{
              fill: "#94a3b8",
              fontSize: 12,
              fontWeight: 500,
            }}
            tickLine={false}
          />
          <PolarRadiusAxis
            domain={[0, 100]}
            tick={{ fill: "rgba(148,163,184,0.5)", fontSize: 9 }}
            tickCount={5}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          {/* Glow fill radar */}
          <Radar
            name="评分"
            dataKey="score"
            stroke="rgba(56,189,248,0.9)"
            strokeWidth={2}
            fill="url(#radarGradient)"
            fillOpacity={1}
          />
          {/* SVG gradient definition */}
          <defs>
            <radialGradient id="radarGradient" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(59,130,246,0.5)" />
              <stop offset="100%" stopColor="rgba(6,182,212,0.15)" />
            </radialGradient>
          </defs>
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
