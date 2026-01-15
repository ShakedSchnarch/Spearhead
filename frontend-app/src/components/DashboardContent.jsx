import { useCallback, useMemo, useState } from "react";
import {
  Button,
  Group,
  SimpleGrid,
  SegmentedControl,
  Select,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useDashboard } from "../context/DashboardContext";

import { EmptyCard } from "./EmptyCard";
import { KpiCard } from "./KpiCard";
import { PlatoonCard } from "./PlatoonCard";
import { PlatoonView } from "./views/PlatoonView";
import { BattalionView } from "./views/BattalionView";
import { SectionHeader } from "./SectionHeader";
import { FormStatusTables } from "./FormStatusTables";
import { QueryPanel } from "./QueryPanel";
import { useIntelligence } from "../hooks/useIntelligence";
import { mapBattalionIntel, mapPlatoonIntel } from "../mappers/intelligence";

export function DashboardContent() {
  const { state, update, actions, data, helpers } = useDashboard();
  const { user, viewMode, platoon, week, activeTab } = state;
  const { summary, coverage, syncStatus, tabular } = data;
  const { syncMutation, exportMutation } = actions;
  const {
    battalionData,
    platoonData,
    refetchBattalion,
    refetchPlatoon,
  } = useIntelligence();

  const battalionIntel = useMemo(
    () => mapBattalionIntel(battalionData),
    [battalionData]
  );
  const platoonIntel = useMemo(
    () => mapPlatoonIntel(platoonData),
    [platoonData]
  );

  const isRestricted = user?.platoon && user.platoon !== "battalion";
  const [banner, setBanner] = useState(null);

  // --- Error Handling ---
  const handleApiError = (err, ctx) => {
    if (err?.status === 401) {
      notifications.show({
        title: "שגיאת הרשאה",
        message: "פג תוקף הטוקן",
        color: "red",
      });
      return true;
    }
    notifications.show({
      title: ctx || "שגיאה",
      message: String(err),
      color: "red",
    });
    return false;
  };

  // --- Helpers & Computed ---
  const syncInfo = {
    status: syncStatus.data?.files?.form_responses?.status || "disabled",
    last: syncStatus.data?.files?.form_responses?.last_sync || "n/a",
    etag: syncStatus.data?.files?.form_responses?.etag || "n/a",
    source: syncStatus.data?.files?.form_responses?.source || "n/a",
  };
  const summaryData = summary.data;
  const coverageData = coverage.data;
  const normalizedCoverage = useCallback((raw) => {
    if (!raw) return null;
    return {
      forms: raw.forms ?? raw.reports_this_week ?? 0,
      distinct_tanks: raw.distinct_tanks ?? raw.expected ?? 0,
      days_since_last: raw.days_since_last ?? raw.missing_reports ?? "-",
      anomaly: raw.anomaly,
    };
  }, []);
  const coverageTotals = useMemo(() => {
    const base = { forms: 0, tanks: 0, anomalies: 0 };
    const fromCoverage = coverageData?.platoons || {};
    const fromIntel = battalionIntel?.platoons || [];

    if (Object.keys(fromCoverage).length) {
      base.forms = Object.values(fromCoverage).reduce(
        (acc, p) => acc + (p.forms || 0),
        0
      );
      base.tanks = Object.values(fromCoverage).reduce(
        (acc, p) => acc + (p.distinct_tanks || 0),
        0
      );
      base.anomalies = coverageData?.anomalies?.length || 0;
      return base;
    }

    if (fromIntel.length) {
      base.forms = fromIntel.reduce(
        (acc, p) => acc + (p.coverage?.reports_this_week || 0),
        0
      );
      base.tanks = fromIntel.reduce(
        (acc, p) => acc + (p.coverage?.expected || 0),
        0
      );
      return base;
    }

    if (platoonIntel?.coverage) {
      base.forms = platoonIntel.coverage.reports_this_week || 0;
      base.tanks = platoonIntel.coverage.expected || 0;
    }

    return base;
  }, [coverageData, battalionIntel, platoonIntel]);
  const platoonCards = useMemo(() => {
    // We need logos here too for the cards
    // TODO: Move logos to shared constant
    const assetBase = "/spearhead";
    const logoPath = (file) => `${assetBase}/logos/${file}`;
    const platoonLogos = {
      כפיר: logoPath("Kfir_logo.JPG"),
      סופה: logoPath("Sufa_logo.JPG"),
      מחץ: logoPath("Machatz_logo.JPG"),
      romach: logoPath("Romach_75_logo.JPG"),
    };

    const intelCoverageMap = {};
    (battalionIntel?.platoons || []).forEach((p) => {
      intelCoverageMap[p.name] = normalizedCoverage(p.coverage);
    });

    const namesFromIntel = (battalionIntel?.platoons || []).map((p) => p.name);
    const list =
      helpers?.knownPlatoons?.length || namesFromIntel.length
        ? Array.from(new Set([...(helpers?.knownPlatoons || []), ...namesFromIntel]))
        : [];

    return list
      .map((name) => {
        const coverage =
          normalizedCoverage(coverageData?.platoons?.[name]) ||
          intelCoverageMap[name] ||
          (platoonIntel?.platoon === name ? normalizedCoverage(platoonIntel.coverage) : null) || {
            forms: 0,
            distinct_tanks: 0,
            days_since_last: "-",
          };
        return {
          name,
          coverage,
          logo: platoonLogos[name] || platoonLogos.romach,
        };
      })
      .filter((c) => {
        if (isRestricted && c.name !== user.platoon) return false;
        return activeTab === "dashboard";
      });
  }, [
    helpers,
    coverageData,
    battalionIntel,
    platoonIntel,
    activeTab,
    isRestricted,
    user.platoon,
    normalizedCoverage,
  ]);

  const platoonOptions = useMemo(() => {
    const base = helpers?.knownPlatoons || [];
    const intelNames = (battalionIntel?.platoons || []).map((p) => p.name);
    return Array.from(new Set([...base, ...intelNames]));
  }, [helpers, battalionIntel]);

  // --- Handlers ---
  const handleSync = async () => {
    try {
      await syncMutation.mutateAsync("all");
      notifications.show({
        title: "סנכרון הצליח",
        message: "הנתונים עודכנו",
        color: "teal",
      });
      await Promise.all([
        summary.refetch(),
        coverage.refetch(),
        syncStatus.refetch(),
        tabular.refetch(),
        refetchBattalion(),
        refetchPlatoon(),
      ]);
    } catch (e) {
      handleApiError(e, "סנכרון נכשל");
    }
  };

  const handleExport = async (mode) => {
    try {
      const resolvedWeek = week || summaryData?.week;
      if (!resolvedWeek) throw new Error("לא ניתן לייצא: לא זוהה שבוע נתונים");

      const params = {
        week: resolvedWeek,
        platoon: mode === "platoon" ? platoon : undefined,
      };
      if (mode === "platoon" && !platoon) throw new Error("בחר פלוגה");

      const blob = await exportMutation.mutateAsync({ mode, params });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Spearhead_Export_${
        mode === "platoon" ? "Platoon" : "Battalion"
      }_${mode === "platoon" ? platoon + "_" : ""}${resolvedWeek}.xlsx`;
      a.click();
      notifications.show({
        title: "הורדה",
        message: "הקובץ ירד בהצלחה",
        color: "teal",
      });
    } catch (e) {
      handleApiError(e, "ייצוא נכשל");
    }
  };

  // --- Render ---
  return (
    <>
      {banner && (
        <div className={`banner ${banner.tone || "info"}`}>
          <span>{banner.text}</span>
          <button className="banner-close" onClick={() => setBanner(null)}>
            ×
          </button>
        </div>
      )}

      {/* Actions Bar */}
      <div className="actions-bar">
        <Group justify="space-between">
          <Group>
            <Button
              variant={activeTab === "dashboard" ? "filled" : "light"}
              onClick={() => update((s) => ({ ...s, activeTab: "dashboard" }))}
            >
              דשבורד
            </Button>
            <Button
              variant={activeTab === "export" ? "filled" : "light"}
              onClick={() => update((s) => ({ ...s, activeTab: "export" }))}
            >
              דוחות
            </Button>
          </Group>
          <Group>
            <Button
              onClick={handleSync}
              loading={syncMutation.isPending}
              color="cyan"
            >
              סנכרן נתונים
            </Button>
          </Group>
        </Group>
      </div>

      {/* KPI Strip */}
      <SimpleGrid
        cols={{ base: 1, sm: 2, lg: 4 }}
        spacing="md"
          className="kpi-strip"
      >
        <KpiCard
          label="שבוע"
          value={
            summaryData?.week ||
            battalionIntel?.week ||
            platoonIntel?.week ||
            "latest"
          }
        />
        <KpiCard label="דיווחים" value={coverageTotals.forms} />
        <KpiCard label="טנקים" value={coverageTotals.tanks} />
        <KpiCard
          label="חריגות"
          value={coverageTotals.anomalies}
          tone={coverageTotals.anomalies ? "warn" : "neutral"}
        />
      </SimpleGrid>

      {activeTab === "dashboard" && (
        <>
          {/* View Controls - Hidden for restricted users */}
          {!isRestricted && (
            <SectionHeader title="מבט על">
              <Group>
                <SegmentedControl
                  value={viewMode}
                  onChange={(v) => update((s) => ({ ...s, viewMode: v }))}
                  data={[
                    { label: "גדוד", value: "battalion" },
                    { label: "פלוגה", value: "platoon" },
                  ]}
                />
                <Select
                  placeholder="בחר פלוגה"
                  data={platoonOptions}
                  value={platoon}
                  onChange={(v) => update((s) => ({ ...s, platoon: v }))}
                  allowDeselect
                />
              </Group>
            </SectionHeader>
          )}

          {isRestricted && (
            <SectionHeader title={`מבט פלוגתי: ${user.platoon}`} />
          )}

          {/* Platoon Navigation */}
          <div className="platoon-grid">
            {platoonCards.map((c) => (
              <PlatoonCard
                key={c.name}
                name={c.name}
                logo={c.logo}
                coverage={c.coverage}
                isActive={platoon === c.name}
                onSelect={(p) =>
                  update((s) => ({ ...s, platoon: p, viewMode: "platoon" }))
                }
              />
            ))}
          </div>

          {/* Detailed Tables */}
          {viewMode === "battalion" ? (
            <>
              <BattalionView />
              <div style={{ marginTop: "1.5rem" }}>
                <QueryPanel />
              </div>
            </>
          ) : (
            <>
              <PlatoonView />
              <div style={{ marginTop: "2rem" }}>
                <FormStatusTables
                  formsOk={tabular.data?.forms?.ok}
                  formsGaps={tabular.data?.forms?.gaps}
                />
              </div>
              <div style={{ marginTop: "1.5rem" }}>
                <QueryPanel />
              </div>
            </>
          )}

          {/* Debug Info (Hidden unless empty) */}
          {!summaryData && !battalionIntel && !platoonIntel && (
            <div style={{ maxWidth: 400, margin: "2rem auto" }}>
              <EmptyCard
                title="אין נתונים"
                message={`לא נמצאו נתונים להצגה. אנא ודא שהסנכרון פעיל. (סטטוס: ${syncInfo.status}, עדכון אחרון: ${syncInfo.last})`}
              />
            </div>
          )}
        </>
      )}

      {activeTab === "export" && (
        <div style={{ padding: 40, textAlign: "center" }}>
          <h3>ייצוא נתונים</h3>
          <Group justify="center">
            {!isRestricted && (
              <Button onClick={() => handleExport("battalion")}>
                ייצוא גדודי
              </Button>
            )}
            <Button onClick={() => handleExport("platoon")} disabled={!platoon}>
              ייצוא פלוגתי
            </Button>
          </Group>
        </div>
      )}
    </>
  );
}
