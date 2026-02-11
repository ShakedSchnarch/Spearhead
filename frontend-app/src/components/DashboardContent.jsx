import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Drawer,
  Group,
  Image,
  Loader,
  Progress,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { DataTable } from "mantine-datatable";
import { COMPANY_KEYS, battalionMeta, getUnitMeta } from "../config/unitMeta";

const DEFAULT_SECTIONS = ["Logistics", "Armament", "Communications"];
const SECTION_DISPLAY = {
  Logistics: "לוגיסטיקה",
  Armament: "חימוש",
  Communications: "תקשוב",
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
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
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

function readinessVisual(score, { reportedThisWeek = true } = {}) {
  if (!reportedThisWeek) {
    return { color: "gray", label: "ללא דיווח", accent: "#64748b" };
  }
  const value = Number(score);
  if (!Number.isFinite(value)) {
    return { color: "gray", label: "ללא נתון", accent: "#64748b" };
  }
  if (value >= 80) {
    return { color: "teal", label: "כשיר", accent: "#14b8a6" };
  }
  if (value >= 60) {
    return { color: "yellow", label: "בינוני", accent: "#f59e0b" };
  }
  return { color: "red", label: "דורש טיפול", accent: "#ef4444" };
}

function displaySection(section, sectionNames = {}) {
  return sectionNames?.[section] || SECTION_DISPLAY[section] || section;
}

function displayStatus(status) {
  const map = {
    OK: "תקין",
    Gap: "פערים",
    Critical: "קריטי",
    NoReport: "ללא דיווח",
  };
  return map[status] || status || "-";
}

function formatTankLabel(value) {
  const raw = `${value || ""}`.trim();
  if (!raw) return "צ׳-";
  const digits = raw.match(/\d{2,4}/)?.[0];
  if (digits) return `צ׳${digits}`;
  if (raw.startsWith("צ׳") || raw.startsWith("צ'")) return raw.replace(/^צ[׳']+/, "צ׳");
  return raw;
}

export function DashboardContent({ client, user, onLogout }) {
  const fixedCompany = user?.platoon || "";
  const isRestricted = Boolean(fixedCompany);
  const normalizedViewMode = `${user?.viewMode || ""}`.trim().toLowerCase();
  const prefersBattalion = normalizedViewMode === "battalion" || normalizedViewMode === "גדוד";

  const [scope, setScope] = useState(() => {
    if (isRestricted) return "company";
    return prefersBattalion ? "battalion" : "company";
  });
  const [week, setWeek] = useState("");
  const [company, setCompany] = useState(fixedCompany || "");
  const [section, setSection] = useState(DEFAULT_SECTIONS[0]);
  const [selectedTankId, setSelectedTankId] = useState(null);
  const [detailsView, setDetailsView] = useState("section");

  const selectedScope = isRestricted ? "company" : scope;
  const selectedCompany = isRestricted ? fixedCompany : company;

  const weeks = useQuery({
    queryKey: ["weeks", client.baseUrl, isRestricted ? fixedCompany : "all"],
    queryFn: ({ signal }) =>
      client.getWeeks({ platoon: isRestricted ? fixedCompany : undefined }, signal),
    staleTime: 30_000,
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

  const battalionView = useQuery({
    queryKey: ["battalion-view", client.baseUrl, weekParam, isRestricted ? fixedCompany : "all"],
    queryFn: ({ signal }) =>
      client.getBattalionView(
        {
          week: weekParam,
          company: isRestricted ? fixedCompany : undefined,
        },
        signal,
      ),
    staleTime: 10_000,
  });

  const fallbackCompanyFromView = battalionView.data?.companies?.[0] || "";
  const activeCompanyKey = isRestricted ? fixedCompany : (selectedCompany || fallbackCompanyFromView);

  const companyView = useQuery({
    queryKey: ["company-view", client.baseUrl, activeCompanyKey, weekParam],
    queryFn: ({ signal }) => client.getCompanyView(activeCompanyKey, { week: weekParam }, signal),
    enabled: Boolean((selectedScope === "company" || isRestricted) && activeCompanyKey),
    staleTime: 10_000,
  });

  const companyTanks = useQuery({
    queryKey: ["company-tanks", client.baseUrl, activeCompanyKey, weekParam],
    queryFn: ({ signal }) => client.getCompanyTanks(activeCompanyKey, { week: weekParam }, signal),
    enabled: Boolean((selectedScope === "company" || isRestricted) && activeCompanyKey),
    staleTime: 10_000,
  });

  const companyOptions = useMemo(() => {
    const fromView = battalionView.data?.companies || [];
    const values = new Map();
    COMPANY_KEYS.forEach((companyName) => {
      const meta = getUnitMeta(companyName);
      values.set(meta.key, meta.shortLabel);
    });
    fromView.forEach((companyName) => {
      const meta = getUnitMeta(companyName);
      values.set(meta.key, meta.shortLabel);
    });
    if (fixedCompany) {
      const meta = getUnitMeta(fixedCompany);
      values.set(meta.key, meta.shortLabel);
    }

    const order = new Map(COMPANY_KEYS.map((name, index) => [getUnitMeta(name).key, index]));
    return Array.from(values.entries())
      .sort(([left], [right]) => {
        const leftRank = order.has(left) ? order.get(left) : Number.MAX_SAFE_INTEGER;
        const rightRank = order.has(right) ? order.get(right) : Number.MAX_SAFE_INTEGER;
        if (leftRank !== rightRank) return leftRank - rightRank;
        return String(left).localeCompare(String(right), "he");
      })
      .map(([value, label]) => ({ value, label }));
  }, [battalionView.data, fixedCompany]);

  const sectionRows = useMemo(() => companyView.data?.sections || [], [companyView.data]);
  const sectionDisplayNames = useMemo(
    () => companyView.data?.section_display_names || battalionView.data?.section_display_names || SECTION_DISPLAY,
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

  const effectiveCompany = selectedScope === "company" || isRestricted ? activeCompanyKey : "";

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
  const battalionCompanyCards = useMemo(() => {
    const grouped = new Map();
    battalionRows.forEach((row) => {
      const companyMeta = getUnitMeta(row.company || "Unknown");
      const companyKey = companyMeta.key;
      if (!grouped.has(companyKey)) {
        grouped.set(companyKey, {
          company: row.company || companyKey,
          companyKey,
          readinessValues: [],
          totalGaps: 0,
          criticalGaps: 0,
          deltaReadiness: [],
        });
      }
      const item = grouped.get(companyKey);
      if (row.readiness_score !== null && row.readiness_score !== undefined && Number.isFinite(Number(row.readiness_score))) {
        item.readinessValues.push(Number(row.readiness_score));
      }
      if (row.delta_readiness !== null && row.delta_readiness !== undefined && Number.isFinite(Number(row.delta_readiness))) {
        item.deltaReadiness.push(Number(row.delta_readiness));
      }
      item.totalGaps += Number(row.total_gaps || 0);
      item.criticalGaps += Number(row.critical_gaps || 0);
    });

    return Array.from(grouped.values())
      .map((item) => {
        const avgReadiness = item.readinessValues.length
          ? Number((item.readinessValues.reduce((sum, value) => sum + value, 0) / item.readinessValues.length).toFixed(1))
          : null;
        const avgDeltaReadiness = item.deltaReadiness.length
          ? Number((item.deltaReadiness.reduce((sum, value) => sum + value, 0) / item.deltaReadiness.length).toFixed(1))
          : null;
        return {
          company: item.company,
          companyKey: item.companyKey,
          avgReadiness,
          avgDeltaReadiness,
          totalGaps: item.totalGaps,
          criticalGaps: item.criticalGaps,
          visual: readinessVisual(avgReadiness),
          hasData: true,
        };
      })
      .sort((a, b) => {
        const left = a.avgReadiness ?? -1;
        const right = b.avgReadiness ?? -1;
        return right - left;
      });
  }, [battalionRows]);
  const battalionDisplayCards = useMemo(() => {
    const byKey = new Map(battalionCompanyCards.map((item) => [item.companyKey, item]));
    const cards = COMPANY_KEYS.map((companyKey) => {
      const existing = byKey.get(companyKey);
      if (existing) return existing;
      return {
        company: companyKey,
        companyKey,
        avgReadiness: null,
        avgDeltaReadiness: null,
        totalGaps: 0,
        criticalGaps: 0,
        visual: { color: "gray", label: "אין דיווחים", accent: "#64748b" },
        hasData: false,
      };
    });

    battalionCompanyCards.forEach((item) => {
      if (!cards.some((card) => card.companyKey === item.companyKey)) {
        cards.push(item);
      }
    });
    return cards;
  }, [battalionCompanyCards]);
  const companiesWithDataCount = battalionDisplayCards.filter((card) => card.hasData).length;
  const hasBattalionComparison = companiesWithDataCount > 1;

  const tanksRows = useMemo(() => sectionTanks.data?.rows || [], [sectionTanks.data]);
  const companyTankRows = useMemo(() => companyTanks.data?.rows || [], [companyTanks.data]);
  const companyTankSummary = companyTanks.data?.summary || {};
  const selectedTank = useMemo(
    () => companyTankRows.find((row) => row.tank_id === selectedTankId) || null,
    [companyTankRows, selectedTankId],
  );
  const selectedTankReported = selectedTank ? (selectedTank.reported_this_week ?? Number(selectedTank.reports || 0) > 0) : false;
  const tankStatusCards = useMemo(
    () =>
      companyTankRows
        .slice()
        .sort((a, b) => String(a.tank_id).localeCompare(String(b.tank_id), "he"))
        .map((row) => ({
          ...row,
          tank_label: formatTankLabel(row.tank_id),
          reported_this_week: Number(row.reports || 0) > 0,
          readiness: readinessVisual(row.readiness_score, {
            reportedThisWeek: Number(row.reports || 0) > 0,
          }),
        })),
    [companyTankRows],
  );
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

  const selectedCompanyMeta = activeCompanyKey ? getUnitMeta(activeCompanyKey) : battalionMeta;
  const scopeMeta = selectedScope === "company" ? selectedCompanyMeta : battalionMeta;
  const companyVisual = readinessVisual(companyTankSummary.avg_readiness);
  const selectedWeekLabel =
    weekOptions.find((option) => option.value === selectedWeek)?.label || selectedWeek || "ללא שבוע";
  const reportedRatio =
    Number(companyTankSummary.known_tanks || 0) > 0
      ? `${companyTankSummary.reported_tanks || 0}/${companyTankSummary.known_tanks}`
      : `${companyTankSummary.reported_tanks || 0}/${companyTankSummary.tanks || 0}`;

  const focusSectionDetails = (sectionValue) => {
    if (sectionValue) setSection(sectionValue);
    setDetailsView("section");
  };

  const refreshAll = () =>
    Promise.all([
      weeks.refetch(),
      battalionView.refetch(),
      companyView.refetch(),
      companyTanks.refetch(),
      sectionTanks.refetch(),
    ]);
  const scopeHasErrors =
    selectedScope === "battalion"
      ? Boolean(weeks.isError || battalionView.isError)
      : Boolean(weeks.isError || battalionView.isError || companyView.isError || companyTanks.isError || sectionTanks.isError);

  return (
    <Stack gap="md">
      <Card withBorder className="dashboard-hero">
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <Group gap="md" align="center">
            <Image
              src={scopeMeta.logo}
              alt={scopeMeta.label}
              radius="md"
              w={74}
              h={74}
              fit="cover"
            />
            <div>
              <Title order={2}>קצה הרומח</Title>
              <Text size="sm" c="dimmed">
                {selectedScope === "company"
                  ? `גדוד 75 · מצב פלוגתי (${selectedCompanyMeta.shortLabel})`
                  : "גדוד 75 · מצב גדודי והשוואה בין פלוגות"}
              </Text>
              <Text size="sm" c="dimmed">
                משתמש: {user?.email || "unknown"}
              </Text>
              <Group gap="xs" mt={4}>
                <Badge variant="light" color="gray">
                  גדוד 75
                </Badge>
                {selectedScope === "company" ? (
                  <Badge variant="light" color="cyan">
                    {selectedCompanyMeta.shortLabel}
                  </Badge>
                ) : null}
              </Group>
            </div>
            {selectedScope === "company" ? (
              <Image
                src={battalionMeta.logo}
                alt={battalionMeta.label}
                radius="md"
                w={46}
                h={46}
                fit="cover"
                opacity={0.9}
              />
            ) : null}
          </Group>

          <Group gap="xs" align="center">
            <Badge variant="light" size="lg" style={{ borderColor: scopeMeta.color }}>
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
            w={{ base: "100%", sm: 340 }}
            placeholder="בחירת שבוע"
          />

          {selectedScope === "company" || isRestricted ? (
            <Select
              label="פלוגה"
              data={companyOptions}
              value={activeCompanyKey || null}
              onChange={(value) => setCompany(value || "")}
              disabled={isRestricted}
              searchable
              clearable={!isRestricted}
              w={190}
            />
          ) : null}
        </Group>
        <Text size="xs" c="dimmed" mt="xs">
          שבוע פעיל: {selectedWeekLabel}
        </Text>
      </Card>

      {scopeHasErrors ? (
        <Alert color="red" variant="light" title="שגיאת טעינה">
          לא הצלחנו לטעון את הנתונים כרגע. נסה ללחוץ על "רענון נתונים". אם זה ממשיך, בצע התחברות מחדש.
        </Alert>
      ) : null}

      {!isRestricted && availableCompanies.length ? (
        <Card withBorder>
          <Group gap="sm" wrap="wrap">
            {availableCompanies.map((companyName) => {
              const meta = getUnitMeta(companyName);
              const active = selectedScope === "company" && activeCompanyKey === companyName;
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
                שבוע {battalionView.data?.week_id || selectedWeek || "ללא שבוע"}
              </Text>
            </div>
            <Text size="sm" c="dimmed">
              שבוע קודם: {battalionView.data?.previous_week_id || "-"}
            </Text>
          </Group>

          {battalionDisplayCards.length ? (
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} mb="md">
              {battalionDisplayCards.map((row) => {
                const companyMeta = getUnitMeta(row.companyKey || row.company);
                return (
                  <Card
                    key={`battalion-company-${companyMeta.key}`}
                    withBorder
                    className="visual-summary-card"
                    style={{ cursor: "pointer", opacity: row.hasData ? 1 : 0.78 }}
                    onClick={() => {
                      setCompany(companyMeta.key);
                      setScope("company");
                    }}
                  >
                    <Stack gap={6}>
                      <Group justify="space-between" align="center">
                        <Group gap="xs" wrap="nowrap">
                          <Image src={companyMeta.logo} alt={companyMeta.shortLabel} w={28} h={28} radius="xl" fit="cover" />
                          <Text fw={700}>{companyMeta.shortLabel}</Text>
                        </Group>
                        <Badge variant="light" color={row.visual.color}>
                          {row.hasData ? row.visual.label : "אין דיווחים"}
                        </Badge>
                      </Group>
                      <Text size="sm">כשירות ממוצעת: {row.hasData ? formatScore(row.avgReadiness) : "-"}</Text>
                      <Progress
                        size="sm"
                        radius="xl"
                        color={row.visual.color}
                        value={row.hasData && Number.isFinite(Number(row.avgReadiness)) ? Math.max(0, Math.min(100, Number(row.avgReadiness))) : 0}
                      />
                      <Text size="sm" c="dimmed">
                        חריגים קריטיים: {row.criticalGaps} | פערים: {row.totalGaps}
                      </Text>
                      <Text size="sm" c={readinessDeltaColor(row.avgDeltaReadiness)}>
                        שינוי שבועי: {row.hasData ? formatDelta(row.avgDeltaReadiness, 1) : "-"}
                      </Text>
                    </Stack>
                  </Card>
                );
              })}
            </SimpleGrid>
          ) : null}

          {battalionView.isFetching ? (
            <Loader size="sm" />
          ) : battalionRows.length === 0 ? (
            <EmptyState label="אין נתוני גדוד לשבוע שנבחר." />
          ) : (
            <>
              {!hasBattalionComparison ? (
                <Text size="sm" c="dimmed" mb="sm">
                  כרגע יש דיווחים מפלוגה אחת בלבד. אפשר לראות כרטיסי השוואה, ויתר הפלוגות מסומנות כ"אין דיווחים".
                </Text>
              ) : null}
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
                          <Text>{meta.shortLabel}</Text>
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
                          setCompany(getUnitMeta(row.company).key);
                          setScope("company");
                        }}
                      >
                        פתיחה
                      </Button>
                    ),
                  },
                ]}
              />
            </>
          )}
        </Card>
      ) : (
        <>
          <Card withBorder>
            <Stack gap="sm">
              <Group justify="space-between" wrap="wrap">
                <div>
                  <Text fw={700}>תמונת כשירות פלוגתית חזותית</Text>
                  <Text size="sm" c="dimmed">
                    אינדיקציה מהירה לישיבה: צבע = מצב כשירות
                  </Text>
                </div>
                <Group gap="xs">
                  <Badge variant="light" color="cyan">
                    כשירות כוללת: {formatScore(companyTankSummary.avg_readiness)}
                  </Badge>
                  <Badge variant="light" color="gray">
                    דיווחו השבוע: {reportedRatio}
                  </Badge>
                </Group>
              </Group>
              {companyView.isFetching ? (
                <Loader size="sm" />
              ) : sectionRows.length === 0 ? (
                <EmptyState label="אין נתוני תחומים להצגה חזותית." />
              ) : (
                <Stack gap="sm">
                  <Card withBorder className="company-overview-card">
                    <Stack gap={8}>
                      <Group justify="space-between" align="center" wrap="wrap">
                        <div>
                          <Text fw={700}>כשירות פלוגתית כוללת</Text>
                          <Text size="sm" c="dimmed">
                            טנקים עם חריג קריטי: {companyTankSummary.critical_tanks || 0}
                          </Text>
                        </div>
                        <Group gap="xs">
                          <Badge variant="light" color={companyVisual.color}>
                            {companyVisual.label}
                          </Badge>
                          <Text fw={800} size="xl" className="score-ltr">
                            {formatScore(companyTankSummary.avg_readiness)}
                          </Text>
                        </Group>
                      </Group>
                      <Progress
                        size="xl"
                        radius="xl"
                        color={companyVisual.color}
                        value={
                          Number.isFinite(Number(companyTankSummary.avg_readiness))
                            ? Math.max(0, Math.min(100, Number(companyTankSummary.avg_readiness)))
                            : 0
                        }
                      />
                    </Stack>
                  </Card>

                  <SimpleGrid cols={{ base: 1, md: 3 }}>
                    {sectionRows.map((row) => {
                      const visual = readinessVisual(row.readiness_score);
                      const selected = row.section === effectiveSection && detailsView === "section";
                      return (
                        <Card
                          key={`visual-${row.section}`}
                          withBorder
                          className="visual-summary-card"
                          style={{
                            cursor: "pointer",
                            borderColor: selected ? "var(--mantine-color-cyan-5)" : undefined,
                          }}
                          onClick={() => focusSectionDetails(row.section)}
                        >
                          <Stack gap={8}>
                            <Group justify="space-between" align="center" wrap="nowrap">
                              <Text fw={700}>{displaySection(row.section, sectionDisplayNames)}</Text>
                              <Badge variant="light" color={visual.color}>
                                {visual.label}
                              </Badge>
                            </Group>
                            <Text fw={800} size="lg" ta="center" className="score-ltr">
                              {formatScore(row.readiness_score)}
                            </Text>
                            <Progress
                              size="lg"
                              radius="xl"
                              color={visual.color}
                              value={
                                Number.isFinite(Number(row.readiness_score))
                                  ? Math.max(0, Math.min(100, Number(row.readiness_score)))
                                  : 0
                              }
                            />
                            <Text size="sm" c="dimmed" ta="center">
                              פערים: {row.total_gaps} | קריטיים: {row.critical_gaps || 0}
                            </Text>
                          </Stack>
                        </Card>
                      );
                    })}
                  </SimpleGrid>
                </Stack>
              )}
            </Stack>
          </Card>

          <Card withBorder>
            <Stack gap="sm">
              <Group justify="space-between" wrap="wrap">
                <div>
                  <Text fw={700}>מפת טנקים פלוגתית</Text>
                  <Text size="sm" c="dimmed">
                    לחיצה על טנק פותחת פירוט לפי לוגיסטיקה, חימוש ותקשוב
                  </Text>
                </div>
                <Badge variant="light" color="gray">
                  אפור = ללא דיווח השבוע
                </Badge>
              </Group>
              {companyTanks.isFetching ? (
                <Loader size="sm" />
              ) : tankStatusCards.length === 0 ? (
                <EmptyState label="אין טנקים להצגה בשבוע זה." />
              ) : (
                <SimpleGrid cols={{ base: 2, sm: 3, md: 4, lg: 5 }}>
                  {tankStatusCards.map((row) => (
                    <Card
                      key={`tank-card-${row.tank_id}`}
                      withBorder
                      className="tank-status-card"
                      style={{
                        borderColor: row.readiness.accent,
                        boxShadow:
                          selectedTank?.tank_id === row.tank_id
                            ? `0 0 0 1px ${row.readiness.accent}`
                            : undefined,
                      }}
                      onClick={() => setSelectedTankId(row.tank_id)}
                    >
                      <Stack gap={4}>
                        <Group justify="space-between" align="center">
                          <Text fw={700}>{row.tank_label}</Text>
                          <Badge variant="light" color={row.reported_this_week ? "teal" : "gray"}>
                            {row.reported_this_week ? "דיווח השבוע" : "לא דיווח"}
                          </Badge>
                        </Group>
                        <Text size="sm">כשירות: {row.reported_this_week ? formatScore(row.readiness_score) : "ללא דיווח"}</Text>
                        <Text size="xs" c="dimmed">
                          קריטיים: {row.critical_gaps || 0}
                        </Text>
                      </Stack>
                    </Card>
                  ))}
                </SimpleGrid>
              )}
            </Stack>
          </Card>

          <Drawer
            opened={Boolean(selectedTank)}
            onClose={() => setSelectedTankId(null)}
            title={selectedTank ? `פירוט טנק ${formatTankLabel(selectedTank.tank_id)}` : "פירוט טנק"}
            position="left"
            size="lg"
          >
            {selectedTank ? (
              <Stack gap="sm">
                <Group gap="xs">
                  <Badge
                    variant="light"
                    color={readinessVisual(selectedTank.readiness_score, { reportedThisWeek: selectedTankReported }).color}
                  >
                    כשירות כוללת: {selectedTankReported ? formatScore(selectedTank.readiness_score) : "ללא דיווח"}
                  </Badge>
                  <Badge variant="light" color={selectedTankReported ? "teal" : "gray"}>
                    {selectedTankReported ? "דיווח השבוע" : "לא דווח השבוע"}
                  </Badge>
                  <Badge variant="light" color="red">
                    חריגים קריטיים: {selectedTank.critical_gaps || 0}
                  </Badge>
                </Group>
                <SimpleGrid cols={{ base: 1, sm: 3 }}>
                  <Card withBorder>
                    <Text size="sm" c="dimmed">
                      לוגיסטיקה
                    </Text>
                    <Text fw={700}>{formatScore(selectedTank.logistics_readiness)}</Text>
                  </Card>
                  <Card withBorder>
                    <Text size="sm" c="dimmed">
                      חימוש
                    </Text>
                    <Text fw={700}>{formatScore(selectedTank.armament_readiness)}</Text>
                  </Card>
                  <Card withBorder>
                    <Text size="sm" c="dimmed">
                      תקשוב
                    </Text>
                    <Text fw={700}>{formatScore(selectedTank.communications_readiness)}</Text>
                  </Card>
                </SimpleGrid>
                <Card withBorder>
                  <Text fw={700} mb={6}>
                    אמצעים קריטיים בפער
                  </Text>
                  <Text size="sm" c="dimmed">
                    {selectedTank.critical_items?.length
                      ? selectedTank.critical_items
                          .map((item) => `${item.item} (${item.gaps})`)
                          .join(", ")
                      : "אין חריגים קריטיים בטנק זה."}
                  </Text>
                </Card>
                <Card withBorder>
                  <Text fw={700} mb={6}>
                    כלל הפערים בטנק
                  </Text>
                  <Text size="sm" c="dimmed">
                    {selectedTank.gap_items?.length
                      ? selectedTank.gap_items
                          .map((item) => `${item.item} (${item.gaps})`)
                          .join(", ")
                      : "לא נמצאו פערים בדיווח."}
                  </Text>
                </Card>
              </Stack>
            ) : null}
          </Drawer>

          <Card withBorder>
            <Group justify="space-between" mb="sm" align="end" wrap="wrap">
              <div>
                <Text fw={700}>פירוט מתקדם</Text>
                <Text size="sm" c="dimmed">
                  {activeCompanyKey || "-"} · שבוע {companyView.data?.week_id || selectedWeek || "ללא שבוע"}
                </Text>
              </div>
              <Group gap="sm" wrap="wrap">
                <SegmentedControl
                  data={[
                    { value: "section", label: "לפי תחום" },
                    { value: "tanks", label: "טבלת טנקים" },
                  ]}
                  value={detailsView}
                  onChange={setDetailsView}
                />
                {detailsView === "section" ? (
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
                ) : null}
              </Group>
            </Group>

            {detailsView === "tanks" ? (
              companyTanks.isFetching ? (
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
                    {
                      accessor: "tank_id",
                      title: "טנק",
                      render: (row) => formatTankLabel(row.tank_id),
                    },
                    {
                      accessor: "reported_this_week",
                      title: "דיווח השבוע",
                      render: (row) => (
                        <Badge variant="light" color={(row.reported_this_week ?? Number(row.reports || 0) > 0) ? "teal" : "gray"}>
                          {(row.reported_this_week ?? Number(row.reports || 0) > 0) ? "דיווח" : "לא דיווח"}
                        </Badge>
                      ),
                    },
                    {
                      accessor: "status",
                      title: "סטטוס",
                      render: (row) => displayStatus(row.status),
                    },
                    {
                      accessor: "readiness_score",
                      title: "כשירות כוללת",
                      render: (row) =>
                        (row.reported_this_week ?? Number(row.reports || 0) > 0)
                          ? formatScore(row.readiness_score)
                          : "ללא דיווח",
                    },
                    {
                      accessor: "delta_readiness",
                      title: "כשירות שבועית",
                      render: (row) => (
                        <Text c={readinessDeltaColor(row.delta_readiness)} fw={600}>
                          {formatDelta(row.delta_readiness, 1)}
                        </Text>
                      ),
                    },
                    {
                      accessor: "logistics_readiness",
                      title: "לוגיסטיקה",
                      render: (row) =>
                        (row.reported_this_week ?? Number(row.reports || 0) > 0)
                          ? formatScore(row.logistics_readiness)
                          : "-",
                    },
                    {
                      accessor: "armament_readiness",
                      title: "חימוש",
                      render: (row) =>
                        (row.reported_this_week ?? Number(row.reports || 0) > 0)
                          ? formatScore(row.armament_readiness)
                          : "-",
                    },
                    {
                      accessor: "communications_readiness",
                      title: "תקשוב",
                      render: (row) =>
                        (row.reported_this_week ?? Number(row.reports || 0) > 0)
                          ? formatScore(row.communications_readiness)
                          : "-",
                    },
                    { accessor: "critical_gaps", title: "חריגים קריטיים" },
                  ]}
                />
              )
            ) : (
              <>
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
                      {
                        accessor: "tank_id",
                        title: "טנק",
                        render: (row) => formatTankLabel(row.tank_id),
                      },
                      {
                        accessor: "status",
                        title: "סטטוס",
                        render: (row) => displayStatus(row.status),
                      },
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
                            {formatDelta(row.delta_readiness, 1)}
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
              </>
            )}
          </Card>
        </>
      )}
    </Stack>
  );
}
