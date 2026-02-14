import { useMemo } from "react";
import { DonutChart, LineChart } from "@mantine/charts";
import { Card, SimpleGrid, Text } from "@mantine/core";
import {
  Bar as ReBar,
  BarChart as ReBarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as ReTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getUnitMeta } from "../../config/unitMeta";

export function BattalionComparisonCharts({ rows, weeklyReadinessRows }) {
  const chartData = useMemo(
    () =>
      (rows || []).map((row) => ({
        key: getUnitMeta(row.companyKey || row.company).key,
        company: getUnitMeta(row.companyKey || row.company).shortLabel,
        readiness: row.avgReadiness === null || row.avgReadiness === undefined ? 0 : Number(row.avgReadiness),
        critical: Number(row.criticalGaps || 0),
        gaps: Number(row.totalGaps || 0),
        color: getUnitMeta(row.companyKey || row.company).color,
      })),
    [rows],
  );
  const donutData = useMemo(
    () =>
      chartData
        .filter((row) => row.critical > 0)
        .map((row) => ({
          name: row.company,
          value: row.critical,
          color: row.color,
        })),
    [chartData],
  );
  const lineData = useMemo(
    () =>
      (weeklyReadinessRows || []).map((row) => {
        const next = { week: row.week_id };
        Object.entries(row).forEach(([key, value]) => {
          if (key === "week_id") return;
          next[getUnitMeta(key).shortLabel] = value;
        });
        return next;
      }),
    [weeklyReadinessRows],
  );
  const lineSeries = useMemo(() => {
    if (!lineData.length) return [];
    const keys = Object.keys(lineData[0]).filter((key) => key !== "week");
    return keys.map((label) => ({
      name: label,
      label,
      color: chartData.find((row) => row.company === label)?.color || "cyan.6",
    }));
  }, [lineData, chartData]);

  if (!chartData.length) {
    return null;
  }

  return (
    <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="sm" mb="md">
      <Card withBorder>
        <Text size="sm" c="dimmed" mb="xs">
          השוואת כשירות פלוגתית
        </Text>
        <div style={{ height: 170 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ReBarChart data={chartData} margin={{ top: 6, right: 8, left: -12, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.24)" />
              <XAxis dataKey="company" axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#94a3b8", fontSize: 12 }}
                domain={[0, 100]}
              />
              <ReTooltip
                cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
                formatter={(value) => [`${Number(value || 0).toFixed(1)}%`, "כשירות"]}
              />
              <ReBar dataKey="readiness" radius={[8, 8, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell key={`readiness-${entry.key}`} fill={entry.color} />
                ))}
              </ReBar>
            </ReBarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Card withBorder>
        <Text size="sm" c="dimmed" mb="xs">
          חלוקת פערים קריטיים לפי פלוגה
        </Text>
        {donutData.length ? (
          <DonutChart
            h={170}
            data={donutData}
            withLabels
            withTooltip
            size={160}
            thickness={24}
          />
        ) : (
          <Text size="sm" c="dimmed">
            אין פערים קריטיים לשבוע זה.
          </Text>
        )}
      </Card>
      <Card withBorder>
        <Text size="sm" c="dimmed" mb="xs">
          מגמת כשירות פלוגות לפי שבועות
        </Text>
        {lineData.length && lineSeries.length ? (
          <LineChart
            h={170}
            data={lineData}
            dataKey="week"
            series={lineSeries}
            curveType="natural"
            connectNulls
          />
        ) : (
          <Text size="sm" c="dimmed">
            אין נתוני מגמה להשוואה.
          </Text>
        )}
      </Card>
    </SimpleGrid>
  );
}
