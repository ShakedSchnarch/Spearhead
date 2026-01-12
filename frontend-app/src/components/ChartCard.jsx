import { useEffect, useState } from "react";
import { Card } from "@mantine/core";

export function ChartCard({ title, data, color = "#22c55e" }) {
  const hasData = (data?.length || 0) > 0;
  const [recharts, setRecharts] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      const mod = await import("recharts");
      if (!mounted) return;
      setRecharts({
        ResponsiveContainer: mod.ResponsiveContainer,
        BarChart: mod.BarChart,
        Bar: mod.Bar,
        XAxis: mod.XAxis,
        YAxis: mod.YAxis,
        Tooltip: mod.Tooltip,
        Legend: mod.Legend,
        CartesianGrid: mod.CartesianGrid,
      });
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } = recharts || {};
  return (
    <Card withBorder shadow="sm" padding="md" radius="md" className="card">
      <div className="card-title">{title}</div>
      {hasData && recharts ? (
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f293b" />
              <XAxis dataKey="item" stroke="#9fb3d0" />
              <YAxis stroke="#9fb3d0" />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill={`${color}`} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="empty-hint">אין נתונים להצגה</div>
      )}
    </Card>
  );
}
