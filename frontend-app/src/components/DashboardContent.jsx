import { useCallback, useEffect, useMemo, useState } from "react";
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
import { SectionHeader } from "./SectionHeader";
import { SummaryTable } from "./SummaryTable";
import { UploadCard } from "./UploadCard"; // Unused in main view but available
import { ChartCard } from "./ChartCard";
import { FormStatusTables } from "./FormStatusTables"; // Unused in main view but available

export function DashboardContent() {
  const { state, update, actions, data, helpers } = useDashboard();
  const { user, viewMode, platoon, week, activeTab } = state;
  const { health, summary, coverage, syncStatus, tabular } = data;
  const { syncMutation, uploadMutation, exportMutation } = actions;

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
  const coverageTotals = {
    forms: Object.values(coverageData?.platoons || {}).reduce(
      (acc, p) => acc + (p.forms || 0),
      0
    ),
    tanks: Object.values(coverageData?.platoons || {}).reduce(
      (acc, p) => acc + (p.distinct_tanks || 0),
      0
    ),
    anomalies: coverageData?.anomalies?.length || 0,
  };
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

    const list = helpers?.knownPlatoons || [];
    return list
      .map((name) => ({
        name,
        coverage: coverageData?.platoons?.[name],
        logo: platoonLogos[name] || platoonLogos.romach,
      }))
      .filter((c) => {
        // Strict filtering: If restricted, show ONLY their platoon
        if (isRestricted && c.name !== user.platoon) return false;

        // Otherwise standard logic
        return c.coverage || activeTab === "dashboard";
      });
  }, [helpers, coverageData, activeTab, isRestricted, user.platoon]);

  const platoonOptions = helpers?.knownPlatoons || [];

  // --- Detailed Table Logic ---
  const platoonSummary = useMemo(() => {
    if (!summaryData) return null;
    if (summaryData.mode === "platoon") return summaryData.summary;
    if (
      summaryData.mode === "battalion" &&
      platoon &&
      summaryData.platoons?.[platoon]
    ) {
      return summaryData.platoons[platoon];
    }
    return null;
  }, [summaryData, platoon]);

  const platoonRows = useMemo(() => {
    if (!summaryData?.platoons) return [];
    return Object.values(summaryData.platoons || {}).map((p) => {
      const zivudTotal = Object.values(p.zivud_gaps || {}).reduce(
        (acc, v) => acc + (v || 0),
        0
      );
      const meansTotal = Object.values(p.means || {}).reduce(
        (acc, v) => acc + (v?.count || 0),
        0
      );
      return {
        key: p.platoon,
        cells: [p.platoon, p.tank_count, zivudTotal, meansTotal],
      };
    });
  }, [summaryData]);

  const issueRows = useMemo(
    () =>
      (platoonSummary?.issues || []).map((issue, idx) => ({
        key: `${issue.item}-${idx}`,
        cells: [issue.item, issue.tank_id, issue.commander || "", issue.detail],
      })),
    [platoonSummary]
  );

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
        <KpiCard label="שבוע" value={summaryData?.week || "latest"} />
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
            <div className="grid two-col">
              <SummaryTable
                title="סיכום גדודי"
                headers={["פלוגה", "טנקים", "פער זיווד", "אמצעים"]}
                rows={platoonRows}
              />
            </div>
          ) : (
            <div className="grid two-col">
              <ChartCard title="פערים" />
              <ChartCard title="פערים" />
              <SummaryTable
                title="פירוט פערים"
                headers={["פריט", "צ' טנק", "מפקד", "דגשים"]}
                rows={issueRows}
              />
            </div>
          )}

          {/* Debug Info (Hidden unless empty) */}
          {!summaryData && (
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
