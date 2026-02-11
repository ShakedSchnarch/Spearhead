import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Image,
  Loader,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { DataTable } from "mantine-datatable";
import { battalionMeta, getUnitMeta } from "../config/unitMeta";

const DEFAULT_SECTIONS = ["Logistics", "Armament", "Communications"];
const SECTION_DISPLAY = {
  Logistics: "לוגיסטיקה",
  Armament: "חימוש",
  Communications: "תקשוב",
};
const SECTION_SCOPE_NOTES = {
  Logistics: "מקלעים, תחמושת, זיווד",
  Armament: "אמצעים, חלפים, שמנים",
  Communications: "ציוד, צופן תקלות",
};

function EmptyState({ label }) {
  return (
    <Group justify="center" py="xl">
      <Text c="dimmed">{label}</Text>
    </Group>
  );
}

function deltaColor(value) {
  if (value > 0) return "red";
  if (value < 0) return "teal";
  return "gray";
}

function formatDelta(value, digits = 0) {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return "0";
  const rendered = digits > 0 ? number.toFixed(digits) : Math.round(number).toString();
  return number > 0 ? `+${rendered}` : rendered;
}

function readinessDeltaColor(value) {
  if (value > 0) return "teal";
  if (value < 0) return "red";
  return "gray";
}

function formatScore(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${Number(value).toFixed(1)}%`;
}

function displaySection(section, sectionNames = {}) {
  return sectionNames?.[section] || SECTION_DISPLAY[section] || section;
}

export function DashboardContent({ client, user, onLogout }) {
  const fixedCompany = user?.platoon || "";
  const isRestricted = Boolean(fixedCompany);

  const [scope, setScope] = useState("company");
  const [week, setWeek] = useState("");
  const [company, setCompany] = useState(fixedCompany || "Kfir");
  const [section, setSection] = useState(DEFAULT_SECTIONS[0]);

  const selectedScope = isRestricted ? "company" : scope;
  const selectedCompany = isRestricted ? fixedCompany : company;

  const health = useQuery({
    queryKey: ["health", client.baseUrl],
    queryFn: ({ signal }) => client.health(signal),
    staleTime: 60_000,
  });

  const weeks = useQuery({
    queryKey: ["weeks", client.baseUrl, selectedCompany],
    queryFn: ({ signal }) =>
      client.getWeeks({ platoon: isRestricted ? selectedCompany : undefined }, signal),
    staleTime: 30_000,
  });

  const battalionView = useQuery({
    queryKey: ["battalion-view", client.baseUrl, weekParam, isRestricted ? selectedCompany : "all"],
    queryFn: ({ signal }) =>
      client.getBattalionView(
        {
          week: weekParam,
          company: isRestricted ? selectedCompany : undefined,
        },
        signal,
      ),
    staleTime: 10_000,
  });

  const companyView = useQuery({
    queryKey: ["company-view", client.baseUrl, selectedCompany, weekParam],
    queryFn: ({ signal }) => client.getCompanyView(selectedCompany, { week: weekParam }, signal),
    enabled: Boolean((selectedScope === "company" || isRestricted) && selectedCompany),
    staleTime: 10_000,
  });

  const companyTanks = useQuery({
    queryKey: ["company-tanks", client.baseUrl, selectedCompany, weekParam],
    queryFn: ({ signal }) => client.getCompanyTanks(selectedCompany, { week: weekParam }, signal),
    enabled: Boolean((selectedScope === "company" || isRestricted) && selectedCompany),
    staleTime: 10_000,
  });

  const weekOptions = useMemo(() => {
    const metadataOptions = weeks.data?.week_options || [];
    if (metadataOptions.length) {
      return metadataOptions.map((option) => ({
        value: option.value,
        label: option.label || option.value,
      }));
    }
    return (weeks.data?.weeks || []).map((value) => ({ value, label: value }));
  }, [weeks.data]);

  const currentWeekFromApi = weeks.data?.current_week || "";
  const selectedWeek = useMemo(() => {
    const values = new Set(weekOptions.map((option) => option.value));
    if (week && values.has(week)) return week;
    if (currentWeekFromApi && values.has(currentWeekFromApi)) return currentWeekFromApi;
    return weekOptions[0]?.value || "";
  }, [week, weekOptions, currentWeekFromApi]);
  const weekParam = selectedWeek || undefined;

  const companyOptions = useMemo(() => {
    const fromView = battalionView.data?.companies || [];
    const values = new Set(fromView);
    if (fixedCompany) values.add(fixedCompany);
    return Array.from(values)
      .sort((a, b) => String(a).localeCompare(String(b), "he"))
      .map((value) => ({ value, label: value }));
  }, [battalionView.data, fixedCompany]);

  const sectionRows = useMemo(() => companyView.data?.sections || [], [companyView.data]);
  const sectionDisplayNames = useMemo(
    () => companyView.data?.section_display_names || battalionView.data?.section_display_names || SECTION_DISPLAY,
    [companyView.data, battalionView.data],
  );
  const sectionScopeNotes = useMemo(
    () => companyView.data?.section_scope_notes || battalionView.data?.section_scope_notes || SECTION_SCOPE_NOTES,
    [companyView.data, battalionView.data],
  );
  const sectionOptions = useMemo(() => {
    const names = sectionRows.length
      ? sectionRows.map((row) => row.section)
      : battalionView.data?.sections || DEFAULT_SECTIONS;
    return names.map((value) => ({ value, label: displaySection(value, sectionDisplayNames) }));
  }, [sectionRows, battalionView.data, sectionDisplayNames]);

  const effectiveSection = sectionOptions.some((option) => option.value === section)
    ? section
    : sectionOptions[0]?.value || DEFAULT_SECTIONS[0];

  const effectiveCompany =
    isRestricted || selectedScope !== "company"
      ? selectedCompany
      : selectedCompany || companyOptions[0]?.value || "";

  const sectionTanks = useQuery({
    queryKey: ["company-section-tanks", client.baseUrl, effectiveCompany, effectiveSection, weekParam],
    queryFn: ({ signal }) =>
      client.getCompanySectionTanks(effectiveCompany, effectiveSection, { week: weekParam }, signal),
    enabled: Boolean((selectedScope === "company" || isRestricted) && effectiveCompany && effectiveSection),
    staleTime: 10_000,
  });

  const battalionRows = useMemo(
    () =>
      (battalionView.data?.rows || []).map((row, index) => ({
        ...row,
        _id: `${row.company}-${row.section}-${index}`,
      })),
    [battalionView.data],
  );
  const battalionCompanies = battalionView.data?.companies || [];
  const hasBattalionComparison = battalionCompanies.length > 1;

  const tanksRows = sectionTanks.data?.rows || [];
  const companyTankRows = companyTanks.data?.rows || [];
  const companyTankSummary = companyTanks.data?.summary || {};
  const selectedSectionSummary = useMemo(
    () => sectionRows.find((row) => row.section === effectiveSection),
    [sectionRows, effectiveSection],
  );

  const availableCompanies = useMemo(() => {
    const names = companyOptions.map((option) => option.value);
    if (fixedCompany && !names.includes(fixedCompany)) {
      names.unshift(fixedCompany);
    }
    return names;
  }, [companyOptions, fixedCompany]);

  const selectedCompanyMeta = selectedCompany ? getUnitMeta(selectedCompany) : battalionMeta;

  const refreshAll = () =>
    Promise.all([
      health.refetch(),
      weeks.refetch(),
      battalionView.refetch(),
      companyView.refetch(),
      companyTanks.refetch(),
      sectionTanks.refetch(),
    ]);

  return (
    <Stack gap="md">
      <Card withBorder className="dashboard-hero">
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <Group gap="md" align="center">
            <Image
              src={battalionMeta.logo}
              alt={battalionMeta.label}
              radius="md"
              w={72}
              h={72}
              fit="cover"
            />
            <div>
              <Title order={2}>Spearhead Command Dashboard</Title>
              <Text size="sm" c="dimmed">
                גדוד 75 · דשבורד דיווחים פלוגתי
              </Text>
              <Text size="sm" c="dimmed">
                משתמש: {user?.email || "unknown"}
              </Text>
            </div>
          </Group>

          <Group gap="xs" align="center">
            <Badge color={health.isError ? "red" : "teal"} variant="filled" size="lg">
              API {health.isError ? "OFFLINE" : "ONLINE"}
            </Badge>
            <Badge variant="light" size="lg" style={{ borderColor: selectedCompanyMeta.color }}>
              {selectedScope === "company" ? selectedCompanyMeta.label : "תצוגה גדודית"}
            </Badge>
            <Button variant="subtle" color="gray" onClick={onLogout}>
              יציאה
            </Button>
          </Group>
        </Group>

        <Divider my="sm" />

        <Group justify="space-between" wrap="wrap">
          <Text size="sm" c="dimmed">
            סנכרון מתבצע בעת כניסה או בלחיצה על רענון. הנתונים מוצגים לפי שבוע ויחידה.
          </Text>
          <Button variant="light" onClick={refreshAll} loading={battalionView.isFetching || companyView.isFetching}>
            רענון נתונים
          </Button>
        </Group>
      </Card>

      <Card withBorder className="dashboard-filter-card">
        <Group align="end" wrap="wrap" gap="md">
          {!isRestricted ? (
            <SegmentedControl
              data={[
                { value: "battalion", label: "גדוד" },
                { value: "company", label: "פלוגה" },
              ]}
              value={selectedScope}
              onChange={setScope}
            />
          ) : null}

          <Select
            label="שבוע"
            data={weekOptions}
            value={selectedWeek}
            onChange={(value) => setWeek(value || "")}
            searchable
            clearable={false}
            w={180}
            placeholder="latest"
          />

          {selectedScope === "company" || isRestricted ? (
            <Select
              label="פלוגה"
              data={companyOptions}
              value={selectedCompany}
              onChange={(value) => setCompany(value || "")}
              disabled={isRestricted}
              searchable
              clearable={!isRestricted}
              w={190}
            />
          ) : null}
        </Group>
      </Card>

      {!isRestricted && availableCompanies.length ? (
        <Card withBorder>
          <Group gap="sm" wrap="wrap">
            {availableCompanies.map((companyName) => {
              const meta = getUnitMeta(companyName);
              const active = selectedScope === "company" && selectedCompany === companyName;
              return (
                <Button
                  key={companyName}
                  variant={active ? "filled" : "light"}
                  color={active ? "cyan" : "gray"}
                  leftSection={<Image src={meta.logo} alt={meta.shortLabel} w={22} h={22} radius="xl" fit="cover" />}
                  onClick={() => {
                    setCompany(companyName);
                    setScope("company");
                  }}
                >
                  {meta.shortLabel}
                </Button>
              );
            })}
          </Group>
        </Card>
      ) : null}

      {selectedScope === "battalion" ? (
        <Card withBorder>
          <Group justify="space-between" mb="sm">
            <div>
              <Text fw={700}>השוואה גדודית</Text>
              <Text size="sm" c="dimmed">
                שבוע {battalionView.data?.week_id || selectedWeek || "latest"}
              </Text>
            </div>
            <Text size="sm" c="dimmed">
              שבוע קודם: {battalionView.data?.previous_week_id || "-"}
            </Text>
          </Group>

          {battalionView.isFetching ? (
            <Loader size="sm" />
          ) : !hasBattalionComparison ? (
            <EmptyState label="אין עדיין השוואה גדודית (נמצאה פלוגה אחת בלבד)." />
          ) : battalionRows.length === 0 ? (
            <EmptyState label="אין נתוני גדוד לשבוע שנבחר." />
          ) : (
            <DataTable
              idAccessor="_id"
              withTableBorder
              withColumnBorders
              striped
              minHeight={320}
              records={battalionRows}
              columns={[
                {
                  accessor: "company",
                  title: "פלוגה",
                  render: (row) => {
                    const meta = getUnitMeta(row.company);
                    return (
                      <Group gap="xs" wrap="nowrap">
                        <Image src={meta.logo} alt={meta.shortLabel} w={22} h={22} radius="xl" fit="cover" />
                        <Text>{row.company}</Text>
                      </Group>
                    );
                  },
                },
                {
                  accessor: "section",
                  title: "תחום",
                  render: (row) => displaySection(row.section, sectionDisplayNames),
                },
                { accessor: "reports", title: "דיווחים" },
                { accessor: "tanks", title: "טנקים" },
                {
                  accessor: "readiness_score",
                  title: "כשירות",
                  render: (row) => formatScore(row.readiness_score),
                },
                { accessor: "critical_gaps", title: "חריגים קריטיים" },
                { accessor: "total_gaps", title: "פערים" },
                { accessor: "gap_rate", title: "פערים/דיווח" },
                {
                  accessor: "delta_gaps",
                  title: "פערים שבועי",
                  render: (row) => (
                    <Text c={deltaColor(row.delta_gaps)} fw={600}>
                      {formatDelta(row.delta_gaps)}
                    </Text>
                  ),
                },
                {
                  accessor: "delta_readiness",
                  title: "כשירות שבועית",
                  render: (row) => (
                    <Text c={readinessDeltaColor(row.delta_readiness)} fw={600}>
                      {row.delta_readiness === null || row.delta_readiness === undefined
                        ? "-"
                        : formatDelta(row.delta_readiness, 1)}
                    </Text>
                  ),
                },
                {
                  accessor: "drilldown",
                  title: "מעבר",
                  render: (row) => (
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        setCompany(row.company);
                        setScope("company");
                      }}
                    >
                      פתיחה
                    </Button>
                  ),
                },
              ]}
            />
          )}
        </Card>
      ) : (
        <>
          <Card withBorder>
            <Group justify="space-between" mb="sm" wrap="wrap">
              <div>
                <Text fw={700}>תמונת מצב פלוגתית: {selectedCompany || "-"}</Text>
                <Text size="sm" c="dimmed">
                  שבוע {companyView.data?.week_id || selectedWeek || "latest"}
                </Text>
              </div>
              <Text size="sm" c="dimmed">
                שבוע קודם: {companyView.data?.previous_week_id || "-"}
              </Text>
            </Group>

            {companyView.isFetching ? (
              <Loader size="sm" />
            ) : sectionRows.length === 0 ? (
              <EmptyState label="אין נתוני פלוגה לשבוע שנבחר." />
            ) : (
              <SimpleGrid cols={{ base: 1, md: 3 }}>
                {sectionRows.map((row) => {
                  const selected = row.section === section;
                  return (
                    <Card
                      key={row.section}
                      withBorder
                      className="section-summary-card"
                      style={{
                        cursor: "pointer",
                        borderColor: selected ? "var(--mantine-color-cyan-5)" : undefined,
                      }}
                      onClick={() => setSection(row.section)}
                    >
                      <Group justify="space-between" mb="xs">
                        <Text fw={700}>{displaySection(row.section, sectionDisplayNames)}</Text>
                        <Badge color={deltaColor(row.delta_gaps)} variant="light">
                          {formatDelta(row.delta_gaps)} פערים
                        </Badge>
                      </Group>
                      <Text size="xs" c="dimmed">
                        {sectionScopeNotes?.[row.section] || SECTION_SCOPE_NOTES[row.section] || ""}
                      </Text>
                      <Text size="sm" c="dimmed">
                        טנקים: {row.tanks} | דיווחים: {row.reports}
                      </Text>
                      <Text size="sm">כשירות: {formatScore(row.readiness_score)}</Text>
                      <Text size="sm">חריגים קריטיים: {row.critical_gaps || 0}</Text>
                      <Text size="sm">פערים: {row.total_gaps}</Text>
                    </Card>
                  );
                })}
              </SimpleGrid>
            )}
          </Card>

          <Card withBorder>
            <Group justify="space-between" mb="sm" wrap="wrap">
              <div>
                <Text fw={700}>טבלת כשירות טנקים</Text>
                <Text size="sm" c="dimmed">
                  תחומים: לוגיסטיקה, חימוש, תקשוב
                </Text>
              </div>
              <Group gap="xs">
                <Badge variant="light" color="cyan">
                  כשירות פלוגתית: {formatScore(companyTankSummary.avg_readiness)}
                </Badge>
                <Badge variant="light" color="red">
                  טנקים עם חריג קריטי: {companyTankSummary.critical_tanks || 0}
                </Badge>
              </Group>
            </Group>

            {companyTanks.isFetching ? (
              <Loader size="sm" />
            ) : companyTankRows.length === 0 ? (
              <EmptyState label="אין נתוני טנקים לשבוע זה." />
            ) : (
              <DataTable
                withTableBorder
                withColumnBorders
                striped
                minHeight={280}
                records={companyTankRows}
                columns={[
                  { accessor: "tank_id", title: "טנק" },
                  { accessor: "status", title: "סטטוס" },
                  {
                    accessor: "readiness_score",
                    title: "כשירות כוללת",
                    render: (row) => formatScore(row.readiness_score),
                  },
                  {
                    accessor: "delta_readiness",
                    title: "כשירות שבועית",
                    render: (row) => (
                      <Text c={readinessDeltaColor(row.delta_readiness)} fw={600}>
                        {row.delta_readiness === null || row.delta_readiness === undefined
                          ? "-"
                          : formatDelta(row.delta_readiness, 1)}
                      </Text>
                    ),
                  },
                  {
                    accessor: "logistics_readiness",
                    title: "לוגיסטיקה",
                    render: (row) => formatScore(row.logistics_readiness),
                  },
                  {
                    accessor: "armament_readiness",
                    title: "חימוש",
                    render: (row) => formatScore(row.armament_readiness),
                  },
                  {
                    accessor: "communications_readiness",
                    title: "תקשוב",
                    render: (row) => formatScore(row.communications_readiness),
                  },
                  { accessor: "critical_gaps", title: "חריגים קריטיים" },
                  {
                    accessor: "critical_items",
                    title: "אמצעים קריטיים בפער",
                    render: (row) =>
                      row.critical_items?.length
                        ? row.critical_items
                            .slice(0, 3)
                            .map((item) => `${item.item} (${item.gaps})`)
                            .join(", ")
                        : "-",
                  },
                ]}
              />
            )}
          </Card>

          <Card withBorder>
            <Group justify="space-between" mb="sm" align="end" wrap="wrap">
              <div>
                <Text fw={700}>סטטוס לפי תחום</Text>
                <Text size="sm" c="dimmed">
                  תחום: {displaySection(effectiveSection, sectionDisplayNames)}
                </Text>
              </div>
              <Select
                label="תחום"
                data={sectionOptions}
                value={effectiveSection}
                onChange={(value) => {
                  if (value) setSection(value);
                }}
                allowDeselect={false}
                w={220}
              />
            </Group>

            {selectedSectionSummary?.top_gap_items?.length ? (
              <Text size="sm" c="dimmed" mb="sm">
                פערים מובילים: {selectedSectionSummary.top_gap_items.map((item) => `${item.item} (${item.gaps})`).join(", ")}
              </Text>
            ) : null}

            {sectionTanks.isFetching ? (
              <Loader size="sm" />
            ) : tanksRows.length === 0 ? (
              <EmptyState label="אין נתוני טנקים לתחום שנבחר." />
            ) : (
              <DataTable
                withTableBorder
                withColumnBorders
                striped
                minHeight={320}
                records={tanksRows}
                columns={[
                  { accessor: "tank_id", title: "טנק" },
                  { accessor: "status", title: "סטטוס" },
                  { accessor: "reports", title: "דיווחים" },
                  { accessor: "checked_items", title: "נבדקו" },
                  {
                    accessor: "readiness_score",
                    title: "כשירות",
                    render: (row) => formatScore(row.readiness_score),
                  },
                  { accessor: "critical_gaps", title: "קריטיים" },
                  { accessor: "gaps", title: "פערים" },
                  {
                    accessor: "delta_gaps",
                    title: "פערים שבועי",
                    render: (row) => (
                      <Text c={deltaColor(row.delta_gaps)} fw={600}>
                        {formatDelta(row.delta_gaps)}
                      </Text>
                    ),
                  },
                  {
                    accessor: "delta_readiness",
                    title: "כשירות שבועית",
                    render: (row) => (
                      <Text c={readinessDeltaColor(row.delta_readiness)} fw={600}>
                        {row.delta_readiness === null || row.delta_readiness === undefined
                          ? "-"
                          : formatDelta(row.delta_readiness, 1)}
                      </Text>
                    ),
                  },
                  {
                    accessor: "gap_items",
                    title: "אמצעים בפער",
                    render: (row) =>
                      row.gap_items?.length
                        ? row.gap_items
                            .slice(0, 3)
                            .map((item) => `${item.item} (${item.gaps})`)
                            .join(", ")
                        : "-",
                  },
                  {
                    accessor: "critical_items",
                    title: "אמצעים קריטיים",
                    render: (row) =>
                      row.critical_items?.length
                        ? row.critical_items
                            .slice(0, 3)
                            .map((item) => `${item.item} (${item.gaps})`)
                            .join(", ")
                        : "-",
                  },
                ]}
              />
            )}
          </Card>
        </>
      )}
    </Stack>
  );
}
