import { useMemo } from "react";
import { useDashboard } from "../../context/DashboardContext";
import { useIntelligence } from "../../hooks/useIntelligence";
import { useQueries } from "../../hooks/useQueries";
import { SummaryTable } from "../SummaryTable";
import { PlatoonComparison } from "../PlatoonComparison";
import { EmptyCard } from "../EmptyCard";
import { mapBattalionIntel } from "../../mappers/intelligence";
import { TrendChart } from "../TrendChart";
import { Card, Text } from "@mantine/core";

export function BattalionView() {
  const { data } = useDashboard();
  // We use useIntelligence without arguments to fetch battalion overview if mode is battalion
  const { battalionData, battalionLoading } = useIntelligence();
  const intel = useMemo(() => mapBattalionIntel(battalionData), [battalionData]);
  const { gapsByPlatoon } = useQueries();

  // Keep legacy summaryData for the table if needed, or switch entirely?
  // The 'SummaryTable' uses raw numbers (tanks, gaps).
  // 'PlatoonComparison' uses scores.
  const summaryData = data.summary.data;
  const tabularData = data.tabular.data;

  const comparisonData = useMemo(() => {
    if (!intel?.comparison) return [];
    return Object.entries(intel.comparison).map(([name, score]) => ({
      platoon: name,
      score: score,
    }));
  }, [intel]);

  const platoonRows = useMemo(() => {
    if (!summaryData?.platoons) return [];
    const platoons = Object.values(summaryData.platoons || {}).sort((a, b) =>
      a.platoon.localeCompare(b.platoon)
    );
    return platoons.map((p) => {
      const zivudTotal = Object.values(p.zivud_gaps || {}).reduce(
        (acc, v) => acc + (v || 0),
        0
      );
      const meansTotal = Object.values(p.means || {}).reduce(
        (acc, v) => acc + (v?.count || 0),
        0
      );
      const ammoTotal = Object.values(p.ammo || {}).reduce(
        (acc, v) => acc + (v?.total || 0),
        0
      );
      return {
        key: p.platoon,
        cells: [
          p.platoon,
          p.tank_count,
          zivudTotal,
          meansTotal,
          Math.round(ammoTotal),
        ],
      };
    });
  }, [summaryData]);

  const legacyRows = useMemo(() => {
    if (!tabularData?.totals?.length) return [];
    return tabularData.totals.slice(0, 6).map((item, idx) => ({
      key: `${item.item}-${idx}`,
      cells: [
        item.item,
        item.total ?? item.total_num ?? 0,
        item.samples ?? item.count ?? 0,
      ],
    }));
  }, [tabularData]);

  const gapRows = useMemo(() => {
    const rows = gapsByPlatoon.data || intel?.topGaps || [];
    return rows.slice(0, 10).map((g, idx) => ({
      key: `${g.item}-${idx}-${g.platoon || "all"}`,
      cells: [g.item, g.platoon || "—", g.gaps ?? (g.platoons ? Object.values(g.platoons).reduce((a, b) => a + b, 0) : 0)],
    }));
  }, [gapsByPlatoon.data, intel]);

  if (!summaryData && !battalionData)
    return <EmptyCard title="אין נתונים" message="ממתין לסנכרון..." />;

  return (
    <div
      className="battalion-view"
      style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
    >
      {/* Top: Comparison Chart */}
      {intel && <PlatoonComparison data={comparisonData} height={300} />}

      {/* Bottom: Detailed Numbers */}
      <div className="grid two-col">
        <SummaryTable
          title="סטטוס גדודי (תמונת מצב)"
          headers={[
            "פלוגה",
            "טנקים",
            "פער זיווד",
            "פער אמצעים",
            "כמות תחמושת",
          ]}
          rows={platoonRows}
        />
        {legacyRows.length > 0 && (
          <SummaryTable
            title="Legacy Excel · טופ 6 פריטים"
            headers={["פריט", "סה\"כ", "דגימות"]}
            rows={legacyRows}
          />
        )}
        {intel && (
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Text fw={800} mb="sm">
              מגמות ציון לפי פלוגה
            </Text>
            <TrendChart
              data={intel.platoons.map((p) => ({
                id: p.name,
                trend: p.trend,
              }))}
              height={240}
            />
          </Card>
        )}
        <SummaryTable
          title="פערים מובילים לפי פלוגה"
          headers={["פריט", "פלוגה", "פערים"]}
          rows={gapRows}
        />
      </div>
    </div>
  );
}
