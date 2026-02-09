import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { DataTable } from "mantine-datatable";

const KNOWN_PLATOONS = ["כפיר", "מחץ", "סופה", "Kfir", "Mahatz", "Sufa"];

const trendMetricOptions = [
  { value: "total_gaps", label: "סה\"כ פערים" },
  { value: "reports", label: "מספר דיווחים" },
  { value: "gap_rate", label: "פערים לדיווח" },
  { value: "distinct_tanks", label: "טנקים מדווחים" },
];

const gapGroupOptions = [
  { value: "item", label: "לפי פריט" },
  { value: "tank", label: "לפי טנק" },
  { value: "family", label: "לפי משפחה" },
];

function EmptyState({ label }) {
  return (
    <Group justify="center" py="xl">
      <Text c="dimmed">{label}</Text>
    </Group>
  );
}

export function DashboardContent({ client, user, onLogout }) {
  const fixedPlatoon = user?.platoon || "";
  const isRestricted = Boolean(fixedPlatoon);

  const [viewMode, setViewMode] = useState(isRestricted ? "platoon" : "battalion");
  const [week, setWeek] = useState("");
  const [platoon, setPlatoon] = useState(fixedPlatoon);
  const [searchText, setSearchText] = useState("");
  const [searchSubmitted, setSearchSubmitted] = useState("");
  const [groupBy, setGroupBy] = useState("item");
  const [trendMetric, setTrendMetric] = useState("total_gaps");
  const [ingestJson, setIngestJson] = useState(`{
  "schema_version": "v2",
  "source_id": "manual-local",
  "payload": {
    "צ טנק": "צ'653",
    "חותמת זמן": "2026-02-08T10:00:00Z",
    "פלוגה": "כפיר",
    "דוח זיווד [חבל פריסה]": "חוסר"
  }
}`);

  const scopedPlatoon = useMemo(() => {
    if (isRestricted) return fixedPlatoon;
    if (viewMode === "platoon") return platoon || undefined;
    return undefined;
  }, [isRestricted, fixedPlatoon, viewMode, platoon]);

  const weekParam = week || undefined;

  const health = useQuery({
    queryKey: ["health", client.baseUrl],
    queryFn: ({ signal }) => client.health(signal),
    staleTime: 60_000,
  });

  const weeks = useQuery({
    queryKey: ["weeks", client.baseUrl, scopedPlatoon],
    queryFn: ({ signal }) => client.getWeeks({ platoon: scopedPlatoon }, signal),
    staleTime: 30_000,
  });

  const overview = useQuery({
    queryKey: ["overview", client.baseUrl, weekParam, scopedPlatoon],
    queryFn: ({ signal }) =>
      scopedPlatoon
        ? client.getPlatoonMetrics(scopedPlatoon, { week: weekParam }, signal)
        : client.getOverview({ week: weekParam }, signal),
    staleTime: 10_000,
  });

  const tankMetrics = useQuery({
    queryKey: ["tanks", client.baseUrl, scopedPlatoon, weekParam],
    queryFn: ({ signal }) =>
      client.getTankMetrics({ platoon: scopedPlatoon, week: weekParam }, signal),
    enabled: Boolean(scopedPlatoon),
    staleTime: 10_000,
  });

  const gaps = useQuery({
    queryKey: ["gaps", client.baseUrl, scopedPlatoon, weekParam, groupBy],
    queryFn: ({ signal }) =>
      client.getGaps(
        { week: weekParam, platoon: scopedPlatoon, group_by: groupBy, limit: 100 },
        signal,
      ),
    staleTime: 10_000,
  });

  const trends = useQuery({
    queryKey: ["trends", client.baseUrl, scopedPlatoon, trendMetric],
    queryFn: ({ signal }) =>
      client.getTrends(
        {
          metric: trendMetric,
          window_weeks: 8,
          platoon: scopedPlatoon,
        },
        signal,
      ),
    staleTime: 10_000,
  });

  const search = useQuery({
    queryKey: ["search", client.baseUrl, scopedPlatoon, weekParam, searchSubmitted],
    queryFn: ({ signal }) =>
      client.searchResponses(
        {
          q: searchSubmitted,
          week: weekParam,
          platoon: scopedPlatoon,
          limit: 100,
        },
        signal,
      ),
    enabled: searchSubmitted.length >= 2,
    staleTime: 5_000,
  });

  const weekOptions = useMemo(
    () => (weeks.data?.weeks || []).map((w) => ({ value: w, label: w })),
    [weeks.data],
  );

  const platoonOptions = useMemo(() => {
    const fromOverview = Object.keys(overview.data?.platoons || {});
    const all = new Set([...KNOWN_PLATOONS, ...fromOverview]);
    return Array.from(all).map((name) => ({ value: name, label: name }));
  }, [overview.data]);

  const refreshAll = () =>
    Promise.all([
      health.refetch(),
      weeks.refetch(),
      overview.refetch(),
      gaps.refetch(),
      trends.refetch(),
      tankMetrics.refetch(),
      search.refetch(),
    ]);

  const handleSearch = () => {
    const value = searchText.trim();
    if (value.length < 2) {
      notifications.show({
        title: "Search is too short",
        message: "Enter at least 2 characters.",
        color: "yellow",
      });
      return;
    }
    setSearchSubmitted(value);
  };

  const handleIngest = async () => {
    try {
      const payload = JSON.parse(ingestJson);
      await client.ingestFormEvent(payload);
      notifications.show({
        title: "Event ingested",
        message: "Data was saved and read models were refreshed.",
        color: "teal",
      });
      await refreshAll();
    } catch (error) {
      notifications.show({
        title: "Ingestion failed",
        message: error?.message || String(error),
        color: "red",
      });
    }
  };

  const kpis = overview.data || {
    reports: 0,
    tanks: 0,
    total_gaps: 0,
    gap_rate: 0,
    avg_gaps_per_tank: 0,
  };

  const gapRows = gaps.data?.rows || [];
  const tankRows = tankMetrics.data?.rows || [];
  const trendRows = trends.data?.rows || [];
  const searchRows = search.data?.rows || [];

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={3}>Spearhead Dashboard</Title>
          <Text size="sm" c="dimmed">
            {user?.email || "unknown user"}
          </Text>
        </div>
        <Group>
          <Badge color={health.isError ? "red" : "teal"} variant="light">
            API {health.isError ? "Offline" : "Online"}
          </Badge>
          <Button variant="light" color="gray" onClick={onLogout}>
            Logout
          </Button>
        </Group>
      </Group>

      <Card withBorder>
        <Group align="end" wrap="wrap">
          {!isRestricted ? (
            <Select
              label="Scope"
              data={[
                { value: "battalion", label: "גדוד" },
                { value: "platoon", label: "פלוגה" },
              ]}
              value={viewMode}
              onChange={(value) => setViewMode(value || "battalion")}
              allowDeselect={false}
              w={140}
            />
          ) : null}

          <Select
            label="Week"
            data={weekOptions}
            value={week}
            onChange={(value) => setWeek(value || "")}
            searchable
            clearable
            w={180}
          />

          {viewMode === "platoon" || isRestricted ? (
            <Select
              label="Platoon"
              data={platoonOptions}
              value={isRestricted ? fixedPlatoon : platoon}
              onChange={(value) => setPlatoon(value || "")}
              disabled={isRestricted}
              searchable
              clearable={!isRestricted}
              w={180}
            />
          ) : null}

          <Button variant="light" onClick={refreshAll}>
            Refresh
          </Button>
        </Group>
      </Card>

      <SimpleGrid cols={{ base: 1, md: 5 }}>
        <Card withBorder>
          <Text size="sm" c="dimmed">
            Week
          </Text>
          <Text fw={700}>{overview.data?.week_id || week || "latest"}</Text>
        </Card>
        <Card withBorder>
          <Text size="sm" c="dimmed">
            Reports
          </Text>
          <Text fw={700}>{kpis.reports ?? 0}</Text>
        </Card>
        <Card withBorder>
          <Text size="sm" c="dimmed">
            Tanks
          </Text>
          <Text fw={700}>{kpis.tanks ?? 0}</Text>
        </Card>
        <Card withBorder>
          <Text size="sm" c="dimmed">
            Total gaps
          </Text>
          <Text fw={700}>{kpis.total_gaps ?? 0}</Text>
        </Card>
        <Card withBorder>
          <Text size="sm" c="dimmed">
            Gaps/report
          </Text>
          <Text fw={700}>{kpis.gap_rate ?? 0}</Text>
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, xl: 2 }}>
        <Card withBorder>
          <Group justify="space-between" mb="sm">
            <Text fw={700}>Gaps</Text>
            <Select
              data={gapGroupOptions}
              value={groupBy}
              onChange={(value) => setGroupBy(value || "item")}
              allowDeselect={false}
              w={170}
            />
          </Group>
          {gaps.isFetching ? (
            <Loader size="sm" />
          ) : gapRows.length === 0 ? (
            <EmptyState label="No gap data." />
          ) : (
            <DataTable
              withTableBorder
              withColumnBorders
              striped
              minHeight={280}
              records={gapRows}
              columns={[
                {
                  accessor: "key",
                  title:
                    groupBy === "item"
                      ? "Item"
                      : groupBy === "tank"
                        ? "Tank"
                        : "Family",
                },
                { accessor: "gaps", title: "Gaps" },
              ]}
            />
          )}
        </Card>

        <Card withBorder>
          <Text fw={700} mb="sm">
            Tank metrics
          </Text>
          {!scopedPlatoon ? (
            <EmptyState label="Switch to platoon view to see tank metrics." />
          ) : tankMetrics.isFetching ? (
            <Loader size="sm" />
          ) : tankRows.length === 0 ? (
            <EmptyState label="No tank data." />
          ) : (
            <DataTable
              withTableBorder
              withColumnBorders
              striped
              minHeight={280}
              records={tankRows}
              columns={[
                { accessor: "tank_id", title: "Tank" },
                { accessor: "reports", title: "Reports" },
                { accessor: "gaps", title: "Gaps" },
                { accessor: "dominant_family", title: "Top family" },
              ]}
            />
          )}
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, xl: 2 }}>
        <Card withBorder>
          <Group justify="space-between" mb="sm">
            <Text fw={700}>Trends</Text>
            <Select
              data={trendMetricOptions}
              value={trendMetric}
              onChange={(value) => setTrendMetric(value || "total_gaps")}
              allowDeselect={false}
              w={220}
            />
          </Group>
          {trends.isFetching ? (
            <Loader size="sm" />
          ) : trendRows.length === 0 ? (
            <EmptyState label="No trend data." />
          ) : (
            <DataTable
              withTableBorder
              withColumnBorders
              striped
              minHeight={220}
              records={trendRows}
              columns={[
                { accessor: "week_id", title: "Week" },
                { accessor: "value", title: "Value" },
              ]}
            />
          )}
        </Card>

        <Card withBorder>
          <Group justify="space-between" mb="sm">
            <Text fw={700}>Search</Text>
            <Group>
              <TextInput
                placeholder="Item / value / tank"
                value={searchText}
                onChange={(event) => setSearchText(event.currentTarget.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") handleSearch();
                }}
              />
              <Button onClick={handleSearch}>Search</Button>
            </Group>
          </Group>
          {search.isFetching ? (
            <Loader size="sm" />
          ) : searchRows.length === 0 ? (
            <EmptyState label="No results." />
          ) : (
            <DataTable
              withTableBorder
              withColumnBorders
              striped
              minHeight={220}
              records={searchRows}
              columns={[
                { accessor: "tank_id", title: "Tank" },
                { accessor: "platoon_key", title: "Platoon" },
                { accessor: "week_id", title: "Week" },
                { accessor: "match_count", title: "Matches" },
              ]}
            />
          )}
        </Card>
      </SimpleGrid>

      <Card withBorder>
        <Text fw={700} mb="sm">
          Manual ingestion (JSON)
        </Text>
        <Textarea
          minRows={8}
          value={ingestJson}
          onChange={(event) => setIngestJson(event.currentTarget.value)}
          styles={{ input: { fontFamily: "monospace" } }}
        />
        <Group mt="sm" justify="flex-end">
          <Button color="cyan" onClick={handleIngest}>
            Ingest event
          </Button>
        </Group>
      </Card>
    </Stack>
  );
}
