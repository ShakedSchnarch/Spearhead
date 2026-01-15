import { useMemo } from "react";
import { useDashboard } from "../../context/DashboardContext";
import { useIntelligence } from "../../hooks/useIntelligence";
import { PriorityTable } from "../PriorityTable";
import { ReadinessGauge } from "../ReadinessGauge";
import { EmptyCard } from "../EmptyCard";
import { Card, Group, Text, Table, Badge } from "@mantine/core";
import { mapPlatoonIntel } from "../../mappers/intelligence";
import { TrendChart } from "../TrendChart";
import { useQueries } from "../../hooks/useQueries";

export function PlatoonView() {
  const { state } = useDashboard();
  const { platoon } = state;
  const { platoonData, platoonLoading, platoonError } = useIntelligence();
  const { byFamily } = useQueries();
  const intel = useMemo(() => mapPlatoonIntel(platoonData), [platoonData]);

  const sortedTanks = useMemo(() => {
    if (!intel?.tanks) return [];
    return [...intel.tanks].sort((a, b) => a.score - b.score);
  }, [intel]);

  if (!platoon)
    return (
      <EmptyCard title="בחר פלוגה" message="יש לבחור פלוגה כדי לראות נתונים" />
    );

  if (platoonLoading)
    return <EmptyCard title="טוען נתונים..." message="אנא המתן" />;

  if (platoonError)
    return (
      <EmptyCard
        title="שגיאת נתונים"
        message={platoonError.message || "לא ניתן לטעון את כשירות הפלוגה"}
      />
    );

  if (!intel || sortedTanks.length === 0)
    return (
      <EmptyCard
        title="אין נתונים"
        message={`לא נמצאו נתוני כשירות עבור פלוגת ${platoon}`}
      />
    );

  return (
    <div
      className="platoon-view"
      style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 2fr",
          gap: "1rem",
          alignItems: "start",
        }}
      >
        {/* Left Col: Readiness Gauge */}
        <Card
          shadow="sm"
          padding="lg"
          radius="md"
          withBorder
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <ReadinessGauge score={intel.score} size={250} />
        </Card>

        {/* Right Col: Priority List + deltas */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <Group justify="space-between" align="center">
            <Text fw={800}>מדדים פלוגתיים</Text>
            <Badge variant="light" color="cyan">
              Δ שבועי: {intel.deltas?.overall ?? "—"}
            </Badge>
          </Group>
          <Table striped highlightOnHover withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>חתך</Table.Th>
                <Table.Th>ציון</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {Object.entries(intel.breakdown || {}).map(([k, v]) => (
                <Table.Tr key={k}>
                  <Table.Td>{k}</Table.Td>
                  <Table.Td>{typeof v === "number" ? v.toFixed(1) : v}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <PriorityTable
            title="חריגים לטיפול (Priority List)"
            rows={sortedTanks}
            height={300}
          />
        </div>
      </div>

      {/* Trends & gaps */}
      <div className="grid two-col">
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Text fw={800} mb="sm">
            מגמות ציון לטנקים
          </Text>
          <TrendChart data={sortedTanks} />
        </Card>
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Text fw={800} mb="sm">
            פערים מובילים
          </Text>
          <Table withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>פריט</Table.Th>
                <Table.Th>פערים</Table.Th>
                <Table.Th>קטגוריה</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(intel.topGaps || []).slice(0, 6).map((gap, idx) => (
                <Table.Tr key={`${gap.item}-${idx}`}>
                  <Table.Td>{gap.item}</Table.Td>
                  <Table.Td>{gap.gaps}</Table.Td>
                  <Table.Td>
                    <Badge variant="outline" color="gray">
                      {gap.family || "zivud"}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      </div>

      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Text fw={800} mb="sm">
          סיכומי פערים לפי משפחה (שאילתת raw)
        </Text>
        <Table withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>פריט</Table.Th>
              <Table.Th>סה\"כ</Table.Th>
              <Table.Th>פערים</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(byFamily.data || []).slice(0, 8).map((row, idx) => (
              <Table.Tr key={`${row.item}-${idx}`}>
                <Table.Td>{row.item}</Table.Td>
                <Table.Td>{row.total}</Table.Td>
                <Table.Td>{row.gaps}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </div>
  );
}
