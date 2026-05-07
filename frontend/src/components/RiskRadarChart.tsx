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

export default function RiskRadarChart({ dimensions }: Props) {
  const data = Object.entries(dimensions).map(([key, value]) => ({
    dimension: LABELS[key] || key,
    score: value,
    fullMark: 100,
  }));

  return (
    <div className="w-full h-80">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#374151" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fill: "#9ca3af", fontSize: 12 }}
          />
          <PolarRadiusAxis
            domain={[0, 100]}
            tick={{ fill: "#6b7280", fontSize: 10 }}
            tickCount={6}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "8px",
              color: "#f3f4f6",
            }}
          />
          <Radar
            name="评分"
            dataKey="score"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
