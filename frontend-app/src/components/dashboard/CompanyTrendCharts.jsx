import { useMemo } from "react";
import { BarChart, LineChart } from "@mantine/charts";
import { Card, SimpleGrid, Text } from "@mantine/core";

const TANK_COLORS = [
  "blue.6",
  "cyan.6",
  "teal.6",
  "green.6",
  "lime.6",
  "yellow.6",
  "orange.6",
  "red.6",
  "pink.6",
  "grape.6",
  "violet.6",
];

export function CompanyTrendCharts({ readinessRows, criticalRows, tankRows, tankSeries }) {
  const readinessData = useMemo(
    () =>
      (readinessRows || []).map((row) => ({
        week: row.week_id,
        value: row.value === null || row.value === undefined ? null : Number(row.value),
      })),
    [readinessRows],
  );

  const criticalData = useMemo(
    () =>
      (criticalRows || []).map((row) => ({
        week: row.week_id,
        value: Number(row.value || 0),
      })),
    [criticalRows],
  );

  const tankData = useMemo(
    () =>
      (tankRows || []).map((row) => ({
        ...row,
        week: row.week_id,
      })),
    [tankRows],
  );
  const renderedTankSeries = useMemo(
    () =>
      (tankSeries || []).map((series, index) => ({
        name: series.key,
        label: `צ׳${series.tank_id}`,
        color: TANK_COLORS[index % TANK_COLORS.length],
      })),
    [tankSeries],
  );

  return (
    <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="sm">
      <Card withBorder>
        <Text size="sm" c="dimmed" mb="xs">
          כשירות ממוצעת (שבועות אחרונים)
        </Text>
        {readinessData.length ? (
          <LineChart
            h={160}
            data={readinessData}
            dataKey="week"
            series={[{ name: "value", label: "כשירות", color: "teal.6" }]}
            curveType="natural"
          />
        ) : (
          <Text size="sm" c="dimmed">
            אין נתוני מגמה.
          </Text>
        )}
      </Card>
      <Card withBorder>
        <Text size="sm" c="dimmed" mb="xs">
          חריגים קריטיים (שבועות אחרונים)
        </Text>
        {criticalData.length ? (
          <BarChart
            h={160}
            data={criticalData}
            dataKey="week"
            series={[{ name: "value", label: "קריטיים", color: "red.6" }]}
          />
        ) : (
          <Text size="sm" c="dimmed">
            אין נתוני מגמה.
          </Text>
        )}
      </Card>
      <Card withBorder>
        <Text size="sm" c="dimmed" mb="xs">
          כשירות לפי טנקים (שבועות אחרונים)
        </Text>
        {tankData.length && renderedTankSeries.length ? (
          <LineChart
            h={160}
            data={tankData}
            dataKey="week"
            series={renderedTankSeries}
            curveType="monotone"
            connectNulls
          />
        ) : (
          <Text size="sm" c="dimmed">
            אין נתוני טנקים למגמה.
          </Text>
        )}
      </Card>
    </SimpleGrid>
  );
}
