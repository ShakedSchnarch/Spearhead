import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Button,
  Card,
  Collapse,
  Divider,
  Drawer,
  Group,
  Image,
  Loader,
  Paper,
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
import { BattalionComparisonCharts } from "./dashboard/BattalionComparisonCharts";
import { CompanyTrendCharts } from "./dashboard/CompanyTrendCharts";
import {
  DEFAULT_SECTIONS,
  deltaColor,
  displaySection,
  displayStatus,
  formatDelta,
  formatScore,
  formatTankLabel,
  readinessDeltaColor,
  readinessVisual,
  SECTION_DISPLAY,
} from "./dashboard/utils";

const DISABLED_COMPANY_KEYS = new Set(["פלס״מ"]);

function EmptyState({ label }) {
  return (
    <Group justify="center" py="xl">
      <Text c="dimmed">{label}</Text>
    </Group>
  );
}

const AI_STATUS_META = {
  green: { label: "סטטוס: יציב", color: "green" },
  yellow: { label: "סטטוס: דורש מעקב", color: "yellow" },
  red: { label: "סטטוס: סיכון גבוה", color: "red" },
};

const AI_SEVERITY_META = {
  high: { label: "גבוה", color: "red" },
  medium: { label: "בינוני", color: "yellow" },
  low: { label: "נמוך", color: "blue" },
};

const AI_PRIORITY_META = {
  p1: { label: "P1", color: "red" },
  p2: { label: "P2", color: "yellow" },
  p3: { label: "P3", color: "blue" },
};

function extractStructuredAi(raw) {
  if (!raw) return null;
  if (raw.structured && typeof raw.structured === "object") return raw.structured;
  const content = `${raw.content || ""}`.trim();
  if (!content) return null;

  const candidates = [content];
  const fencedMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fencedMatch?.[1]) candidates.push(fencedMatch[1].trim());
  const start = content.indexOf("{");
  const end = content.lastIndexOf("}");
  if (start >= 0 && end > start) candidates.push(content.slice(start, end + 1));

  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate);
      if (parsed && typeof parsed === "object") return parsed;
    } catch {
      // Try next candidate.
    }
  }
  return null;
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
  const [showBattalionTable, setShowBattalionTable] = useState(false);
  const [showAdvancedDetails, setShowAdvancedDetails] = useState(false);
  const [showAmmoTable, setShowAmmoTable] = useState(false);
  const detailsRef = useRef(null);

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
  const battalionAiAnalysis = useQuery({
    queryKey: ["battalion-ai-analysis", client.baseUrl, weekParam, isRestricted ? fixedCompany : "all"],
    queryFn: ({ signal }) =>
      client.getBattalionAiAnalysis(
        {
          week: weekParam,
          company: isRestricted ? fixedCompany : undefined,
        },
        signal,
      ),
    enabled: Boolean(selectedScope === "battalion"),
    staleTime: 30_000,
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
      if (DISABLED_COMPANY_KEYS.has(meta.key)) return;
      values.set(meta.key, meta.shortLabel);
    });
    if (fixedCompany) {
      const meta = getUnitMeta(fixedCompany);
      if (!DISABLED_COMPANY_KEYS.has(meta.key)) {
        values.set(meta.key, meta.shortLabel);
      }
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

  const companyAssets = useQuery({
    queryKey: ["company-assets", client.baseUrl, activeCompanyKey, weekParam],
    queryFn: ({ signal }) => client.getCompanyAssets(activeCompanyKey, { week: weekParam }, signal),
    enabled: Boolean((selectedScope === "company" || isRestricted) && activeCompanyKey),
    staleTime: 10_000,
  });

  const tankInventory = useQuery({
    queryKey: ["tank-inventory", client.baseUrl, activeCompanyKey, selectedTankId, weekParam],
    queryFn: ({ signal }) =>
      client.getCompanyTankInventory(activeCompanyKey, selectedTankId, { week: weekParam }, signal),
    enabled: Boolean((selectedScope === "company" || isRestricted) && activeCompanyKey && selectedTankId),
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
          reportingReported: 0,
          reportingKnown: 0,
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
      item.reportingReported = Math.max(item.reportingReported, Number(row.reports || 0));
      item.reportingKnown = Math.max(item.reportingKnown, Number(row.tanks || 0));
    });

    return Array.from(grouped.values())
      .map((item) => {
        const avgReadiness = item.readinessValues.length
          ? Number((item.readinessValues.reduce((sum, value) => sum + value, 0) / item.readinessValues.length).toFixed(1))
          : null;
        const avgDeltaReadiness = item.deltaReadiness.length
          ? Number((item.deltaReadiness.reduce((sum, value) => sum + value, 0) / item.deltaReadiness.length).toFixed(1))
          : null;
        const hasData = item.readinessValues.length > 0 || item.reportingReported > 0 || item.totalGaps > 0;
        const reportingState = item.reportingKnown <= 0
          ? { label: "ללא דיווח", color: "gray" }
          : (item.reportingReported >= item.reportingKnown
            ? { label: "דיווח מלא", color: "teal" }
            : (item.reportingReported > 0
              ? { label: "דיווח חלקי", color: "yellow" }
              : { label: "ללא דיווח", color: "gray" }));
        return {
          company: item.company,
          companyKey: item.companyKey,
          avgReadiness,
          avgDeltaReadiness,
          totalGaps: item.totalGaps,
          criticalGaps: item.criticalGaps,
          reportingReported: item.reportingReported,
          reportingKnown: item.reportingKnown,
          reportingState,
          visual: hasData ? readinessVisual(avgReadiness) : { color: "gray", label: "אין דיווחים", accent: "#64748b" },
          hasData,
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
        reportingReported: 0,
        reportingKnown: 0,
        reportingState: { label: "ללא דיווח", color: "gray" },
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
  const battalionRowsWithData = battalionDisplayCards.filter((card) => card.hasData);
  const battalionWeeklyReadinessRows = useMemo(
    () => battalionView.data?.trends?.readiness_by_company || [],
    [battalionView.data],
  );
  const battalionBestReadiness = useMemo(() => {
    const sorted = battalionRowsWithData
      .filter((row) => row.avgReadiness !== null && row.avgReadiness !== undefined)
      .slice()
      .sort((a, b) => Number(b.avgReadiness || 0) - Number(a.avgReadiness || 0));
    return sorted[0] || null;
  }, [battalionRowsWithData]);
  const battalionHighestCritical = useMemo(() => {
    const sorted = battalionRowsWithData
      .slice()
      .sort((a, b) => Number(b.criticalGaps || 0) - Number(a.criticalGaps || 0));
    return sorted[0] || null;
  }, [battalionRowsWithData]);
  const battalionAiStructured = useMemo(
    () => extractStructuredAi(battalionAiAnalysis.data),
    [battalionAiAnalysis.data],
  );
  const battalionAiStatusMeta = AI_STATUS_META[battalionAiStructured?.status] || AI_STATUS_META.yellow;

  const tanksRows = useMemo(() => sectionTanks.data?.rows || [], [sectionTanks.data]);
  const companyTankRows = useMemo(() => companyTanks.data?.rows || [], [companyTanks.data]);
  const companyTankSummary = companyTanks.data?.summary || {};
  const criticalGapRows = useMemo(() => companyTanks.data?.critical_gaps_table || [], [companyTanks.data]);
  const ammoAverageRows = useMemo(() => companyTanks.data?.ammo_averages || [], [companyTanks.data]);
  const ammoSummary = useMemo(() => {
    if (!ammoAverageRows.length) {
      return {
        items: 0,
        avgAvailabilityPct: 0,
        belowThreshold: 0,
      };
    }
    const values = ammoAverageRows
      .map((row) => Number(row.availability_pct ?? row.availability_rate ?? 0))
      .filter((value) => Number.isFinite(value));
    const avgAvailabilityPct = values.length
      ? values.reduce((sum, value) => sum + value, 0) / values.length
      : 0;
    const belowThreshold = values.filter((value) => value < 80).length;
    return {
      items: ammoAverageRows.length,
      avgAvailabilityPct,
      belowThreshold,
    };
  }, [ammoAverageRows]);
  const trendRowsReadiness = useMemo(() => companyTanks.data?.trends?.readiness || [], [companyTanks.data]);
  const trendRowsCritical = useMemo(() => companyTanks.data?.trends?.critical_gaps || [], [companyTanks.data]);
  const trendRowsTankReadiness = useMemo(() => companyTanks.data?.trends?.tank_readiness || [], [companyTanks.data]);
  const trendRowsTankSeries = useMemo(() => companyTanks.data?.trends?.tank_series || [], [companyTanks.data]);
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
          reported_this_week: row.reported_this_week ?? Number(row.reports || 0) > 0,
          readiness: readinessVisual(row.readiness_score, {
            reportedThisWeek: row.reported_this_week ?? Number(row.reports || 0) > 0,
          }),
        })),
    [companyTankRows],
  );
  const tankInventoryRows = useMemo(() => tankInventory.data?.rows || [], [tankInventory.data]);
  const companyAssetRows = useMemo(() => companyAssets.data?.rows || [], [companyAssets.data]);
  const companyAssetSummary = companyAssets.data?.summary || {};
  const selectedSectionSummary = useMemo(
    () => sectionRows.find((row) => row.section === effectiveSection),
    [sectionRows, effectiveSection],
  );

  const availableCompanies = useMemo(() => {
    const names = companyOptions.map((option) => option.value);
    if (fixedCompany && !DISABLED_COMPANY_KEYS.has(fixedCompany) && !names.includes(fixedCompany)) {
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
    setShowAdvancedDetails(true);
    window.setTimeout(() => {
      detailsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 120);
  };

  const refreshAll = () =>
    Promise.all([
      weeks.refetch(),
      battalionView.refetch(),
      battalionAiAnalysis.refetch(),
      companyView.refetch(),
      companyTanks.refetch(),
      sectionTanks.refetch(),
      companyAssets.refetch(),
      tankInventory.refetch(),
    ]);
  const scopeHasErrors =
    selectedScope === "battalion"
      ? Boolean(weeks.isError || battalionView.isError)
      : Boolean(
          weeks.isError
          || battalionView.isError
          || companyView.isError
          || companyTanks.isError
          || sectionTanks.isError
          || companyAssets.isError
          || tankInventory.isError,
        );

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
            </div>
          </Group>

          <Group gap="xs" align="center">
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
            w={{ base: 180, sm: 220 }}
            placeholder="בחירת שבוע"
          />
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

      {!isRestricted && selectedScope === "battalion" && availableCompanies.length ? (
        <Card withBorder>
          <Group gap="sm" wrap="wrap">
            {availableCompanies.map((companyName) => {
              const meta = getUnitMeta(companyName);
              const active = selectedScope === "company" && activeCompanyKey === companyName;
              return (
                <Button
                  key={companyName}
                  variant={active ? "filled" : "light"}
                  color={active ? meta.color : "gray"}
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
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} mb="md">
              {battalionDisplayCards.map((row) => {
                const companyMeta = getUnitMeta(row.companyKey || row.company);
                const companyColor = companyMeta.color || "#64748b";
                const isTopCompany = battalionBestReadiness?.companyKey === row.companyKey;
                const isHighRiskCompany = battalionHighestCritical?.companyKey === row.companyKey && Number(row.criticalGaps || 0) > 0;
                return (
                  <Card
                    key={`battalion-company-${companyMeta.key}`}
                    withBorder
                    className="visual-summary-card"
                    style={{
                      cursor: "pointer",
                      opacity: isHighRiskCompany ? 0.82 : (row.hasData ? 1 : 0.78),
                      borderColor: companyColor,
                      filter: isHighRiskCompany ? "saturate(0.72) grayscale(0.2)" : undefined,
                    }}
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
                        <Group gap={6}>
                          {isTopCompany ? (
                            <Badge variant="filled" color="yellow">
                              ★ מצטיינת
                            </Badge>
                          ) : null}
                          {isHighRiskCompany ? (
                            <Badge variant="filled" color="red">
                              נדרש שיפור מיידי
                            </Badge>
                          ) : null}
                          <Badge variant="light" color={row.visual.color}>
                            {row.hasData ? row.visual.label : "אין דיווחים"}
                          </Badge>
                        </Group>
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
                      <Group gap={6} wrap="nowrap">
                        <Badge variant="light" color={row.reportingState?.color || "gray"}>
                          {row.reportingState?.label || "ללא דיווח"}
                        </Badge>
                        <Text size="sm" c="dimmed" className="score-ltr">
                          {row.reportingKnown > 0 ? `${row.reportingReported}/${row.reportingKnown}` : "0/0"}
                        </Text>
                      </Group>
                      <Text size="sm" c={readinessDeltaColor(row.avgDeltaReadiness)} className="score-ltr">
                        שינוי שבועי: {row.hasData ? formatDelta(row.avgDeltaReadiness, 1) : "-"}
                      </Text>
                    </Stack>
                  </Card>
                );
              })}
            </SimpleGrid>
          ) : null}

          {battalionRowsWithData.length ? (
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm" mb="md">
              <Card withBorder className="visual-summary-card">
                <Text size="sm" c="dimmed">פלוגה מובילה בכשירות</Text>
                <Text fw={700} mt={4}>
                  {battalionBestReadiness ? getUnitMeta(battalionBestReadiness.companyKey).shortLabel : "-"}
                </Text>
                <Text size="sm">
                  {battalionBestReadiness ? formatScore(battalionBestReadiness.avgReadiness) : "-"}
                </Text>
              </Card>
              <Card withBorder className="visual-summary-card">
                <Text size="sm" c="dimmed">פלוגה עם הכי הרבה קריטיים</Text>
                <Text fw={700} mt={4}>
                  {battalionHighestCritical ? getUnitMeta(battalionHighestCritical.companyKey).shortLabel : "-"}
                </Text>
                <Text size="sm">
                  {battalionHighestCritical ? battalionHighestCritical.criticalGaps : "-"}
                </Text>
              </Card>
            </SimpleGrid>
          ) : null}

          <BattalionComparisonCharts rows={battalionRowsWithData} weeklyReadinessRows={battalionWeeklyReadinessRows} />

          <Card withBorder mb="md">
            <Group justify="space-between" mb="xs" align="center">
              <Text fw={700}>ניתוח AI גדודי</Text>
              <Group gap={6}>
                <Badge variant="light" color={battalionAiStatusMeta.color}>
                  {battalionAiStatusMeta.label}
                </Badge>
                <Badge variant="light" color={battalionAiAnalysis.data?.source === "remote" ? "teal" : "gray"}>
                  מקור: {battalionAiAnalysis.data?.source || "offline"}
                </Badge>
              </Group>
            </Group>
            {battalionAiAnalysis.isFetching ? (
              <Loader size="sm" />
            ) : battalionAiStructured ? (
              <Stack gap="sm">
                <Paper withBorder p="sm" className="ai-summary-panel">
                  <Text fw={700}>{battalionAiStructured.headline || "תמונת מצב"}</Text>
                  <Text size="sm" c="dimmed" mt={6}>
                    {battalionAiStructured.executive_summary || "אין סיכום זמין."}
                  </Text>
                </Paper>

                <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm">
                  <Paper withBorder p="sm" className="ai-analysis-panel">
                    <Text fw={700} mb={8}>תובנות מרכזיות</Text>
                    <Stack gap={8}>
                      {(battalionAiStructured.key_findings || []).map((item, index) => {
                        const severityMeta = AI_SEVERITY_META[item?.severity] || AI_SEVERITY_META.medium;
                        return (
                          <Paper key={`finding-${index}`} withBorder p="xs" className="ai-analysis-item">
                            <Group justify="space-between" align="start" mb={4}>
                              <Text fw={600} size="sm">{item?.title || "ללא כותרת"}</Text>
                              <Badge variant="light" color={severityMeta.color}>{severityMeta.label}</Badge>
                            </Group>
                            <Text size="sm" c="dimmed">{item?.detail || "לא זמין."}</Text>
                          </Paper>
                        );
                      })}
                    </Stack>
                  </Paper>

                  <Paper withBorder p="sm" className="ai-analysis-panel">
                    <Text fw={700} mb={8}>סיכונים מיידיים</Text>
                    <Stack gap={8}>
                      {(battalionAiStructured.immediate_risks || []).map((item, index) => {
                        const severityMeta = AI_SEVERITY_META[item?.impact] || AI_SEVERITY_META.medium;
                        return (
                          <Paper key={`risk-${index}`} withBorder p="xs" className="ai-analysis-item">
                            <Group justify="space-between" align="start" mb={4}>
                              <Text fw={600} size="sm">{item?.risk || "סיכון"}</Text>
                              <Badge variant="light" color={severityMeta.color}>{severityMeta.label}</Badge>
                            </Group>
                            <Text size="sm" c="dimmed">{item?.reason || "לא זמין."}</Text>
                          </Paper>
                        );
                      })}
                    </Stack>
                  </Paper>
                </SimpleGrid>

                <Paper withBorder p="sm" className="ai-analysis-panel">
                  <Text fw={700} mb={8}>פעולות מומלצות ל-7 ימים</Text>
                  <Stack gap={8}>
                    {(battalionAiStructured.actions_next_7_days || []).map((item, index) => {
                      const priorityMeta = AI_PRIORITY_META[item?.priority] || AI_PRIORITY_META.p2;
                      return (
                        <Paper key={`action-${index}`} withBorder p="xs" className="ai-analysis-item">
                          <Group justify="space-between" align="start" mb={4}>
                            <Text fw={600} size="sm">{item?.action || "ללא פעולה"}</Text>
                            <Badge variant="filled" color={priorityMeta.color}>{priorityMeta.label}</Badge>
                          </Group>
                          <Text size="sm" c="dimmed">אחראי: {item?.owner || "לא הוגדר"}</Text>
                          <Text size="sm" c="dimmed">השפעה צפויה: {item?.expected_effect || "לא זמין"}</Text>
                        </Paper>
                      );
                    })}
                  </Stack>
                </Paper>

                <SimpleGrid cols={{ base: 1, md: 2 }} spacing="sm">
                  <Paper withBorder p="sm" className="ai-analysis-panel">
                    <Text fw={700} mb={8}>מה לעקוב בשבוע הבא</Text>
                    <Stack gap={6}>
                      {(battalionAiStructured.watch_next_week || []).map((item, index) => (
                        <Text size="sm" c="dimmed" key={`watch-${index}`}>
                          {index + 1}. {item}
                        </Text>
                      ))}
                    </Stack>
                  </Paper>
                  <Paper withBorder p="sm" className="ai-analysis-panel">
                    <Text fw={700} mb={8}>איכות נתונים</Text>
                    <Text size="sm" c="dimmed">
                      {battalionAiStructured.data_quality?.coverage_note || "לא זמין"}
                    </Text>
                    <Text size="sm" c="dimmed" mt={6}>
                      {battalionAiStructured.data_quality?.limitations || "לא זמין"}
                    </Text>
                  </Paper>
                </SimpleGrid>
              </Stack>
            ) : (
              <Text size="sm" c="dimmed" style={{ whiteSpace: "pre-wrap" }}>
                {battalionAiAnalysis.data?.content || "אין ניתוח זמין כרגע."}
              </Text>
            )}
          </Card>

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
              <Group justify="space-between" align="center" mb="xs">
                <Text fw={700}>טבלת חתכים פלוגתית</Text>
                <Button
                  size="xs"
                  variant="light"
                  color="gray"
                  onClick={() => setShowBattalionTable((current) => !current)}
                >
                  {showBattalionTable ? "הסתר פירוט" : "הצג פירוט"}
                </Button>
              </Group>
              <Collapse in={showBattalionTable}>
                <DataTable
                  idAccessor="_id"
                  withTableBorder
                  withColumnBorders
                  striped
                  minHeight={260}
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
                        <Text c={deltaColor(row.delta_gaps)} fw={600} className="score-ltr">
                          {formatDelta(row.delta_gaps)}
                        </Text>
                      ),
                    },
                    {
                      accessor: "delta_readiness",
                      title: "כשירות שבועית",
                      render: (row) => (
                        <Text c={readinessDeltaColor(row.delta_readiness)} fw={600} className="score-ltr">
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
              </Collapse>
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

          <CompanyTrendCharts
            readinessRows={trendRowsReadiness}
            criticalRows={trendRowsCritical}
            tankRows={trendRowsTankReadiness}
            tankSeries={trendRowsTankSeries}
          />

          <SimpleGrid cols={{ base: 1, xl: 2 }} spacing="sm">
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
                          <Badge variant="outline" color={row.readiness.color}>
                            {row.readiness.label}
                          </Badge>
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

            <Stack gap="sm">
              <Card withBorder>
                <Text fw={700} mb="xs">פערים קריטיים פלוגתיים</Text>
                {criticalGapRows.length === 0 ? (
                  <Text size="sm" c="dimmed">אין חריגים קריטיים לשבוע זה.</Text>
                ) : (
                  <DataTable
                    withTableBorder
                    withColumnBorders
                    striped
                    minHeight={170}
                    records={criticalGapRows}
                    columns={[
                      { accessor: "item", title: "פריט" },
                      { accessor: "gaps", title: "כמות פערים" },
                      {
                        accessor: "tanks",
                        title: "טנקים",
                        render: (row) => (row.tanks?.length ? row.tanks.map((tankId) => formatTankLabel(tankId)).join(", ") : "-"),
                      },
                    ]}
                  />
                )}
              </Card>

            </Stack>
          </SimpleGrid>

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
                    טבלת מלאי מלאה לטנק
                  </Text>
                  {tankInventory.isFetching ? (
                    <Loader size="sm" />
                  ) : tankInventoryRows.length === 0 ? (
                    <Text size="sm" c="dimmed">
                      אין פירוט מלאי זמין לטנק זה בשבוע שנבחר.
                    </Text>
                  ) : (
                    <DataTable
                      withTableBorder
                      withColumnBorders
                      striped
                      minHeight={240}
                      records={tankInventoryRows}
                      columns={[
                        {
                          accessor: "section",
                          title: "חתך",
                          render: (row) => displaySection(row.section, sectionDisplayNames),
                        },
                        { accessor: "item", title: "פריט" },
                        {
                          accessor: "standard_quantity",
                          title: "תקן",
                          render: (row) => (row.standard_quantity === null || row.standard_quantity === undefined
                            ? "-"
                            : String(row.standard_quantity)),
                        },
                        { accessor: "status", title: "סטטוס" },
                        {
                          accessor: "is_critical",
                          title: "קריטי",
                          render: (row) => (
                            <Badge variant="light" color={row.is_critical ? "red" : "gray"}>
                              {row.is_critical ? "כן" : "לא"}
                            </Badge>
                          ),
                        },
                        {
                          accessor: "raw_value",
                          title: "דיווח",
                          render: (row) => (row.raw_value === null || row.raw_value === undefined ? "-" : String(row.raw_value)),
                        },
                      ]}
                    />
                  )}
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
            <Group justify="space-between" align="center" wrap="wrap">
              <div>
                <Text fw={700}>פירוט מתקדם</Text>
                <Text size="sm" c="dimmed">
                  {activeCompanyKey || "-"} · שבוע {companyView.data?.week_id || selectedWeek || "ללא שבוע"}
                </Text>
              </div>
              <Button
                size="xs"
                variant="light"
                color="gray"
                onClick={() => setShowAdvancedDetails((current) => !current)}
              >
                {showAdvancedDetails ? "הסתר פירוט מתקדם" : "הצג פירוט מתקדם"}
              </Button>
            </Group>
          </Card>

          <Collapse in={showAdvancedDetails}>
            <Card withBorder ref={detailsRef}>
              <Group justify="space-between" mb="sm" align="end" wrap="wrap">
                <div>
                  <Text size="sm" c="dimmed">
                    {activeCompanyKey || "-"} · שבוע {companyView.data?.week_id || selectedWeek || "ללא שבוע"}
                  </Text>
                </div>
                <Group gap="sm" wrap="wrap">
                  <SegmentedControl
                    data={[
                      { value: "section", label: "לפי תחום" },
                      { value: "tanks", label: "טבלת טנקים" },
                      { value: "assets", label: "ציוד פלוגתי" },
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
                    minHeight={220}
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
                          <Text c={readinessDeltaColor(row.delta_readiness)} fw={600} className="score-ltr">
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
            ) : detailsView === "assets" ? (
              companyAssets.isFetching ? (
                <Loader size="sm" />
              ) : companyAssetRows.length === 0 ? (
                <EmptyState label="אין נתוני ציוד פלוגתי לשבוע זה." />
              ) : (
                <Stack gap="sm">
                  <Group gap="xs">
                    <Badge variant="light" color="gray">
                      פריטים: {companyAssetSummary.items || 0}
                    </Badge>
                    <Badge variant="light" color="red">
                      פערים: {companyAssetSummary.gaps || 0}
                    </Badge>
                    <Badge variant="light" color="orange">
                      קריטיים: {companyAssetSummary.critical || 0}
                    </Badge>
                  </Group>
                  <DataTable
                    withTableBorder
                    withColumnBorders
                    striped
                    minHeight={220}
                    records={companyAssetRows}
                    columns={[
                      { accessor: "section", title: "חתך" },
                      { accessor: "group", title: "קבוצה" },
                      { accessor: "item", title: "פריט" },
                      {
                        accessor: "standard_quantity",
                        title: "תקן",
                        render: (row) => (row.standard_quantity === null || row.standard_quantity === undefined
                          ? "-"
                          : String(row.standard_quantity)),
                      },
                      { accessor: "status", title: "סטטוס" },
                      {
                        accessor: "is_gap",
                        title: "פער",
                        render: (row) => (
                          <Badge variant="light" color={row.is_gap ? "red" : "teal"}>
                            {row.is_gap ? "כן" : "לא"}
                          </Badge>
                        ),
                      },
                      {
                        accessor: "category_code",
                        title: "צ׳",
                        render: (row) => (
                          <Badge
                            variant="light"
                            color={(row.requires_category_code && !row.has_category_code) ? "red" : (row.has_category_code ? "blue" : "gray")}
                          >
                            {row.has_category_code ? "דווח" : (row.requires_category_code ? "נדרש" : "ללא")}
                          </Badge>
                        ),
                      },
                      {
                        accessor: "raw_value",
                        title: "פירוט",
                        render: (row) => (row.raw_value === null || row.raw_value === undefined ? "-" : String(row.raw_value)),
                      },
                    ]}
                  />
                </Stack>
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
                    minHeight={240}
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
                          <Text c={deltaColor(row.delta_gaps)} fw={600} className="score-ltr">
                            {formatDelta(row.delta_gaps)}
                          </Text>
                        ),
                      },
                      {
                        accessor: "delta_readiness",
                        title: "כשירות שבועית",
                        render: (row) => (
                          <Text c={readinessDeltaColor(row.delta_readiness)} fw={600} className="score-ltr">
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
          </Collapse>

          <Card withBorder>
            <Group justify="space-between" align="center" wrap="wrap">
              <div>
                <Text fw={700}>ממוצעי תחמושת לטנקים</Text>
                <Text size="sm" c="dimmed">
                  זמינות ממוצעת = אחוז טנקים שבהם הפריט דווח כתקין/קיים מתוך כלל הטנקים המדווחים.
                </Text>
              </div>
              <Button
                size="xs"
                variant="light"
                color="gray"
                onClick={() => setShowAmmoTable((current) => !current)}
              >
                {showAmmoTable ? "הסתר טבלת תחמושת" : "הצג טבלת תחמושת"}
              </Button>
            </Group>
            <Group gap="xs" mt="sm" wrap="wrap">
              <Badge variant="light" color="gray">
                פריטי תחמושת: {ammoSummary.items}
              </Badge>
              <Badge variant="light" color={ammoSummary.avgAvailabilityPct >= 80 ? "teal" : "yellow"}>
                זמינות ממוצעת: {ammoSummary.avgAvailabilityPct.toFixed(1)}%
              </Badge>
              <Badge variant="light" color={ammoSummary.belowThreshold > 0 ? "red" : "teal"}>
                פריטים מתחת ל-80%: {ammoSummary.belowThreshold}
              </Badge>
            </Group>
            <Collapse in={showAmmoTable}>
              <Divider my="sm" />
              {ammoAverageRows.length === 0 ? (
                <Text size="sm" c="dimmed">אין נתוני תחמושת להצגה.</Text>
              ) : (
                <DataTable
                  withTableBorder
                  withColumnBorders
                  striped
                  minHeight={170}
                  records={ammoAverageRows}
                  columns={[
                    { accessor: "item", title: "פריט תחמושת" },
                    {
                      accessor: "availability_pct",
                      title: "זמינות ממוצעת",
                      render: (row) => `${Number(row.availability_pct ?? row.availability_rate ?? 0).toFixed(1)}%`,
                    },
                    {
                      accessor: "available_tanks",
                      title: "טנקים תקינים",
                      render: (row) => `${row.available_tanks || 0}`,
                    },
                    {
                      accessor: "gap_tanks",
                      title: "חוסרים/תקלות",
                      render: (row) => `${row.gap_tanks || 0}`,
                    },
                    {
                      accessor: "total_tanks",
                      title: "טנקים מדווחים",
                      render: (row) => `${row.total_tanks || 0}`,
                    },
                  ]}
                />
              )}
            </Collapse>
          </Card>
        </>
      )}
    </Stack>
  );
}
