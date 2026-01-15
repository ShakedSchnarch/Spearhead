import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend } from "recharts";
import { Card } from "@mantine/core";

const colors = ["#22c55e", "#0ea5e9", "#f59e0b", "#ef4444", "#a855f7", "#06b6d4"];

export function TrendChart({ data, height = 260 }) {
  const series = (data || []).slice(0, 6); // limit to avoid clutter
  const lines = series.map((s, idx) => ({
    name: s.id || s.tank_id || `item-${idx}`,
    points: (s.trend || []).map((p) => ({ week: p.week, score: p.score })),
    color: colors[idx % colors.length],
  }));

  // Flatten weeks
  const allWeeks = Array.from(
    new Set(lines.flatMap((l) => l.points.map((p) => p.week)))
  ).sort();

  const chartData = allWeeks.map((week) => {
    const row = { week };
    lines.forEach((l) => {
      const point = l.points.find((p) => p.week === week);
      row[l.name] = point ? point.score : null;
    });
    return row;
  });

  if (!chartData.length) return null;

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart data={chartData}>
          <XAxis dataKey="week" />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Legend />
          {lines.map((l) => (
            <Line
              key={l.name}
              type="monotone"
              dataKey={l.name}
              stroke={l.color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
