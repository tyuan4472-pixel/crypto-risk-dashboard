"use client";

import {
  LineChart,
  Line,
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

export default function ScoreHistory({ data }: Props) {
  // 格式化日期为 MM/DD
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
        <LineChart data={formatted} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="dateLabel"
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "#6b7280", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "8px",
              color: "#f3f4f6",
            }}
            formatter={(value: number) => [`${value.toFixed(1)}`, "总分"]}
          />
          {/* 风险等级参考线 */}
          <ReferenceLine y={65} stroke="#22c55e" strokeDasharray="4 4" label="" />
          <ReferenceLine y={45} stroke="#eab308" strokeDasharray="4 4" label="" />
          <ReferenceLine y={25} stroke="#ef4444" strokeDasharray="4 4" label="" />
          <Line
            type="monotone"
            dataKey="total_score"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: "#3b82f6", r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
