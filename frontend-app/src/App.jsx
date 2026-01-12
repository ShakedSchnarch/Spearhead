import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  SimpleGrid,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { ChartCard } from "./components/ChartCard";
import { EmptyCard } from "./components/EmptyCard";
import { FormStatusTables } from "./components/FormStatusTables";
import { HeroHeader } from "./components/HeroHeader";
import { KpiCard } from "./components/KpiCard";
import { LoginOverlay } from "./components/LoginOverlay";
import { PlatoonCard } from "./components/PlatoonCard";
import { SectionHeader } from "./components/SectionHeader";
import { SummaryTable } from "./components/SummaryTable";
import { UploadCard } from "./components/UploadCard";
import { useApiClient } from "./hooks/useApiClient";
import { useDashboardActions } from "./hooks/useDashboardActions";
import { useDashboardData } from "./hooks/useDashboardData";
import { useDashboardState } from "./hooks/useDashboardState";
import { useOAuthLanding } from "./hooks/useOAuthLanding";
import { anomalyLabels, knownPlatoons } from "./types/state";
import "./index.css";

const oauthUrl =
  typeof import.meta !== "undefined" && import.meta.env ? import.meta.env.VITE_GOOGLE_OAUTH_URL || "" : "";
const oauthReady = Boolean(oauthUrl);
const assetBase = typeof window !== "undefined" && window.location.pathname.startsWith("/app") ? "/app" : "";
const logoPath = (file) => `${assetBase}/logos/${file}`;
const platoonLogos = {
  "כפיר": logoPath("Kfir_logo.JPG"),
  "סופה": logoPath("Sufa_logo.JPG"),
  "מחץ": logoPath("Machatz_logo.JPG"),
  "פלסם": logoPath("Palsam_logo.JPG"),
  romach: logoPath("Romach_75_logo.JPG"),
};

const friendlyImportName = (kind) => {
  if (kind === "platoon-loadout") return "דוח פלוגתי";
  if (kind === "battalion-summary") return "דוח גדודי";
  if (kind === "form-responses") return "טופס תגובות";
  return kind;
};

const TrendTable = ({ title, data }) => (
  <div className="card">
    <div className="card-title">{title}</div>
    <table className="table">
      <thead>
        <tr>
          <th>Item</th>
          <th>Week</th>
          <th>Total</th>
        </tr>
      </thead>
      <tbody>
        {(data || []).flatMap((row) =>
          (row.points || []).map((p) => (
            <tr key={`${row.item}-${p.week}`}>
              <td>{row.item}</td>
              <td>{p.week}</td>
              <td>{p.total}</td>
            </tr>
          )),
        )}
      </tbody>
    </table>
  </div>
);

function App() {
  const [autoSyncDone, setAutoSyncDone] = useState(false);
  const [banner, setBanner] = useState(null); // {text, tone}
  const [lastUpdated, setLastUpdated] = useState(null);

  const { state, update } = useDashboardState();
  const { apiBase, section, topN, platoon, week, viewMode, activeTab, token, user, oauthSession } = state;
  const apiClient = useApiClient(apiBase, token, oauthSession || token);
  const filters = useMemo(
    () => ({
      section,
      topN,
      platoon,
      week,
      viewMode,
    }),
    [section, topN, platoon, week, viewMode],
  );

  const enabled = Boolean(user);
  const { health, syncStatus, summary, coverage, tabular } = useDashboardData(apiClient, filters, enabled);
  const { syncMutation, uploadMutation, exportMutation } = useDashboardActions(apiClient);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.title = "קצה הרומח · דשבורד מוכנות";
    }
  }, []);

  useEffect(() => {
    if (tabular.data) setLastUpdated(new Date().toLocaleString());
  }, [tabular.data]);

  const handleApiError = useCallback(
    (err, context) => {
      if (err?.status === 401) {
        setBanner({ text: "נדרש טוקן/Basic כדי לבצע פעולה זו", tone: "warning" });
        notifications.show({
          title: "דרוש טוקן",
          message: "הוסף טוקן או Basic כדי להמשיך.",
          color: "yellow",
        });
        return true;
      }
      if (err) {
        setBanner({
          text: `${context || "שגיאה"}: ${err.message || err}`,
          tone: "danger",
        });
      }
      return false;
    },
    [setBanner],
  );

  useEffect(() => {
    const errors = [summary.error, coverage.error, tabular.error, syncStatus.error];
    const unauthorized = errors.find((e) => e?.status === 401);
    if (unauthorized) {
      handleApiError(unauthorized);
    }
  }, [summary.error, coverage.error, tabular.error, syncStatus.error, handleApiError]);

  const handleLogin = useCallback(
    (payload) =>
      update((prev) => ({
        ...prev,
        user: { platoon: payload.platoon, email: payload.email, token: payload.token || "" },
        token: payload.token || "",
        oauthSession: payload.oauthSession || "",
        platoon: payload.platoon || prev.platoon,
        viewMode: payload.viewMode || (payload.platoon ? "platoon" : "battalion"),
        activeTab: "dashboard",
      })),
    [update],
  );

  const handleLogout = () =>
    update((prev) => ({
      ...prev,
      user: null,
      token: "",
      platoon: "",
      viewMode: "battalion",
    }));

  const applyOAuth = useCallback(
    (payload) =>
      update((prev) => ({
        ...prev,
        token: payload.token || prev.token,
        oauthSession: payload.session || payload.token || prev.oauthSession,
        user: {
          email: payload.email || prev.user?.email || "",
          platoon: payload.platoon || prev.user?.platoon || "",
          token: payload.token || prev.token,
        },
        platoon: payload.platoon || prev.platoon,
        viewMode: payload.viewMode || (payload.platoon ? "platoon" : "battalion"),
        activeTab: "dashboard",
      })),
    [update],
  );
  useOAuthLanding(applyOAuth);

  useEffect(() => {
    if (!week && summary.data?.week) {
      update((prev) => ({ ...prev, week: summary.data.week }));
    }
  }, [week, summary.data, update]);

  useEffect(() => {
    if (!week && coverage.data?.week) {
      update((prev) => ({ ...prev, week: coverage.data.week }));
    }
  }, [week, coverage.data, update]);

  useEffect(() => {
    if (!user || autoSyncDone) return;
    syncMutation
      .mutateAsync("all")
      .then((data) => {
        setBanner({
          text: `סנכרון הצליח · platoon:${data.platoon_loadout} summary:${data.battalion_summary} forms:${data.form_responses}`,
          tone: "success",
        });
      })
      .catch((err) => handleApiError(err, "שגיאה בסנכרון"))
      .finally(() => setAutoSyncDone(true));
  }, [user, autoSyncDone, syncMutation, handleApiError]);

  const healthLabel = health.data
    ? `ON · v${health.data.version}`
    : health.isError
      ? "לא מחובר"
      : "בודק...";

  const summaryData = summary.data;
  const coverageData = coverage.data;
  const tabularData = tabular.data || {};
  const syncData = syncStatus.data;

  const platoonOptions = useMemo(() => {
    const names = new Set();
    if (summaryData?.platoons) Object.keys(summaryData.platoons).forEach((p) => names.add(p));
    if (coverageData?.platoons) Object.keys(coverageData.platoons).forEach((p) => names.add(p));
    knownPlatoons.forEach((p) => names.add(p));
    return Array.from(names);
  }, [summaryData, coverageData]);

  const platoonSummary = useMemo(() => {
    if (!summaryData) return null;
    if (summaryData.mode === "platoon") return summaryData.summary;
    if (summaryData.mode === "battalion" && platoon && summaryData.platoons?.[platoon]) {
      return summaryData.platoons[platoon];
    }
    return null;
  }, [summaryData, platoon]);

  const battalionKpi = useMemo(() => {
    if (!summaryData?.battalion) return null;
    return {
      week: summaryData.week || summaryData.latest_week || "latest",
      tanks: summaryData.battalion.tank_count,
      source: syncData?.files?.form_responses?.source || "n/a",
      lastSync: syncData?.files?.form_responses?.last_sync || "n/a",
      etag: syncData?.files?.form_responses?.etag || "n/a",
    };
  }, [summaryData, syncData]);

  const coverageTotals = useMemo(() => {
    const platoons = coverageData?.platoons || {};
    const formsTotal = Object.values(platoons).reduce((acc, p) => acc + (p.forms || 0), 0);
    const tanksTotal = Object.values(platoons).reduce((acc, p) => acc + (p.distinct_tanks || 0), 0);
    const anomaliesCount = coverageData?.anomalies?.length || 0;
    return { formsTotal, tanksTotal, anomaliesCount };
  }, [coverageData]);

  const coverageRows = useMemo(() => {
    if (!coverageData?.platoons) return [];
    return Object.entries(coverageData.platoons).map(([name, c]) => ({
      key: name,
      cells: [
        name,
        c.forms ?? 0,
        c.distinct_tanks ?? 0,
        c.days_since_last ?? "-",
        c.anomaly ? anomalyLabels[c.anomaly] || c.anomaly : "תקין",
      ],
    }));
  }, [coverageData]);

  const anomalyRows = useMemo(() => {
    if (!coverageData?.anomalies?.length) return [];
    return coverageData.anomalies.map((a, idx) => ({
      key: `${a.platoon}-${idx}`,
      cells: [
        a.platoon,
        anomalyLabels[a.reason] || a.reason,
        a.forms ?? 0,
        a.avg_forms_recent ?? "-",
        a.days_since_last ?? "-",
      ],
    }));
  }, [coverageData]);

  const platoonCards = useMemo(() => {
    const entries = Object.entries(coverageData?.platoons || {}).filter(
      ([, c]) => (c?.forms || c?.distinct_tanks || 0) > 0,
    );
    if (entries.length) {
      return entries.map(([name, cov]) => ({ name, coverage: cov }));
    }
    return knownPlatoons
      .filter((name) => coverageData?.platoons?.[name])
      .map((name) => ({ name, coverage: coverageData.platoons[name] }));
  }, [coverageData]);

  const syncInfo = useMemo(() => {
    const forms = syncData?.files?.form_responses;
    return {
      status: forms?.status || (syncData?.enabled ? "enabled" : "disabled"),
      last: forms?.last_sync || "n/a",
      source: forms?.source || "n/a",
      etag: forms?.etag || "n/a",
    };
  }, [syncData]);

  const platoonRows = useMemo(() => {
    if (!summaryData?.platoons) return [];
    return Object.values(summaryData.platoons).map((p) => {
      const zivudTotal = Object.values(p.zivud_gaps || {}).reduce((acc, v) => acc + (v || 0), 0);
      const meansTotal = Object.values(p.means || {}).reduce((acc, v) => acc + (v?.count || 0), 0);
      return {
        key: p.platoon,
        cells: [p.platoon, p.tank_count, zivudTotal, meansTotal],
      };
    });
  }, [summaryData]);

  const zivudRows = useMemo(
    () => Object.entries(platoonSummary?.zivud_gaps || {}).map(([item, count]) => ({ key: item, cells: [item, count] })),
    [platoonSummary],
  );
  const ammoRows = useMemo(
    () =>
      Object.entries(platoonSummary?.ammo || {}).map(([item, vals]) => ({
        key: item,
        cells: [item, vals.total ?? 0, vals.avg_per_tank ?? 0],
      })),
    [platoonSummary],
  );
  const meansRows = useMemo(
    () =>
      Object.entries(platoonSummary?.means || {}).map(([item, vals]) => ({
        key: item,
        cells: [item, vals.count ?? 0, vals.avg_per_tank ?? 0],
      })),
    [platoonSummary],
  );
  const issueRows = useMemo(
    () =>
      (platoonSummary?.issues || []).map((issue, idx) => ({
        key: `${issue.item}-${idx}`,
        cells: [issue.item, issue.tank_id, issue.commander || "", issue.detail],
      })),
    [platoonSummary],
  );

  const sortedDelta = useMemo(() => {
    const data = [...(tabularData.delta || [])];
    return data.sort((a, b) => (a.delta ?? 0) > (b.delta ?? 0) ? -1 : 1);
  }, [tabularData.delta]);

  const sortedVariance = useMemo(() => {
    const data = [...(tabularData.variance || [])];
    return data.sort((a, b) => (a.variance ?? 0) > (b.variance ?? 0) ? -1 : 1);
  }, [tabularData.variance]);

  const handleSync = async () => {
    if (syncMutation.isPending) return;
    setBanner({ text: "סנכרון מתבצע...", tone: "warning" });
    try {
      const data = await syncMutation.mutateAsync("all");
      setBanner({
        text: `סנכרון הצליח · platoon:${data.platoon_loadout} summary:${data.battalion_summary} forms:${data.form_responses}`,
        tone: "success",
      });
      notifications.show({ title: "סנכרון הצליח", message: "הנתונים עודכנו מהמקור", color: "teal" });
      await Promise.all([syncStatus.refetch(), summary.refetch(), coverage.refetch(), tabular.refetch()]);
    } catch (err) {
      if (handleApiError(err, "שגיאה בסנכרון")) return;
      notifications.show({ title: "שגיאה בסנכרון", message: String(err), color: "red" });
    }
  };

  const refreshAll = async () => {
    await Promise.all([health.refetch(), syncStatus.refetch(), summary.refetch(), coverage.refetch(), tabular.refetch()]);
  };

  const handleUpload = async (file) => {
    try {
      const res = await uploadMutation.mutateAsync({ kind: "form-responses", file });
      const inserted = res?.inserted || 0;
      setBanner({
        text: `העלאה הצליחה (${friendlyImportName("form-responses")}) · נוספו ${inserted} רשומות`,
        tone: "success",
      });
      notifications.show({
        title: "העלאה הושלמה",
        message: `נוספו ${inserted} רשומות (${friendlyImportName("form-responses")})`,
        color: "teal",
      });
      await refreshAll();
      return inserted;
    } catch (err) {
      handleApiError(err, "שגיאה בהעלאה");
      notifications.show({ title: "שגיאה בהעלאה", message: String(err), color: "red" });
      throw err;
    }
  };

  const handleExport = async (mode) => {
    try {
      const params = {};
      if (week) params.week = week;
      if (mode === "platoon") {
        if (!platoon) throw new Error("בחר פלוגה לייצוא פלוגתי");
        params.platoon = platoon;
      }
      const blob = await exportMutation.mutateAsync({ mode, params });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      const fname = mode === "platoon" ? `platoon_${platoon}_${week || "latest"}.xlsx` : `battalion_${week || "latest"}.xlsx`;
      link.href = url;
      link.download = fname;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      notifications.show({ title: "הייצוא מוכן", message: `הקובץ ${fname} ירד בהצלחה`, color: "teal" });
    } catch (err) {
      handleApiError(err, "שגיאה בייצוא");
      notifications.show({ title: "שגיאה בייצוא", message: String(err), color: "red" });
    }
  };

  if (!user) {
    return <LoginOverlay onLogin={handleLogin} defaultPlatoon={platoon || "battalion"} oauthReady={oauthReady} oauthUrl={oauthUrl} logos={platoonLogos} />;
  }

  return (
    <div className="page">
      <HeroHeader
        user={user}
        viewMode={viewMode}
        platoon={platoon}
        health={healthLabel}
        syncEnabled={syncData?.enabled}
        onLogout={handleLogout}
        logoSrc={viewMode === "battalion" || !user.platoon ? platoonLogos.romach : platoonLogos[user.platoon] || platoonLogos.romach}
      />

      {banner && (
        <div className={`banner ${banner.tone || "info"}`}>
          <span className="dot" />
          <span>{banner.text}</span>
          <button className="banner-close" onClick={() => setBanner(null)}>
            ×
          </button>
        </div>
      )}

      <main>
        <div className="actions-bar">
          <Group gap="xs" wrap="wrap">
            <Group gap={4} className="tabs">
              <Button variant={activeTab === "dashboard" ? "filled" : "light"} onClick={() => update((prev) => ({ ...prev, activeTab: "dashboard" }))}>
                דשבורד
              </Button>
              <Button variant={activeTab === "export" ? "filled" : "light"} onClick={() => update((prev) => ({ ...prev, activeTab: "export" }))}>
                הפקת דוחות
              </Button>
            </Group>
            <Group gap="xs" className="button-group">
              <Button onClick={handleSync} loading={syncMutation.isPending} variant="filled" color="cyan">
                סנכרון מ-Google
              </Button>
              <Button
                onClick={refreshAll}
                loading={summary.isFetching || coverage.isFetching || tabular.isFetching}
                variant="light"
              >
                רענון נתונים
              </Button>
              <TextInput
                label="API"
                size="xs"
                value={apiBase}
                onChange={(e) => update((prev) => ({ ...prev, apiBase: e.target.value }))}
                placeholder="http://localhost:8000"
              />
            </Group>
          </Group>
        </div>

        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md" className="kpi-strip">
          <KpiCard label="שבוע נוכחי" value={summaryData?.latest_week || summaryData?.week || coverageData?.week || "n/a"} />
          <KpiCard label="דיווחים השבוע" value={coverageTotals.formsTotal || 0} hint="סך טפסים מכל הפלוגות" />
          <KpiCard label="טנקים מדווחים" value={coverageTotals.tanksTotal || 0} />
          <KpiCard
            label="אנומליות פעילות"
            value={coverageTotals.anomaliesCount}
            tone={coverageTotals.anomaliesCount ? "warn" : "neutral"}
          />
        </SimpleGrid>

        {activeTab === "dashboard" && (
          <>
            <section id="import">
              <SectionHeader title="ייבוא וסנכרון" subtitle="סנכרון אוטומטי מטפסי הפלוגות. העלה קובץ טפסים לגיבוי בלבד." />
              <div className="upload-grid">
                <UploadCard title="Form Responses" onUpload={handleUpload} disabled={uploadMutation.isPending} />
              </div>
              {!syncData && (
                <div className="empty-state">
                  אין נתונים עדיין. התחבר/י וסנכרן מגוגל או העלה קובץ טפסים ידנית כדי לטעון את הדאטה.
                </div>
              )}
              <div className="actions" style={{ marginTop: 10 }}>
                <Button onClick={handleSync} disabled={syncMutation.isPending} loading={syncMutation.isPending}>
                  {syncMutation.isPending ? "מסנכרן..." : "סנכרון מ-Google Sheets"}
                </Button>
                <Button onClick={refreshAll} disabled={summary.isFetching || coverage.isFetching || tabular.isFetching}>
                  {summary.isFetching || coverage.isFetching || tabular.isFetching ? "מרענן..." : "רענון נתונים"}
                </Button>
              </div>
            </section>

            <section id="platoons">
              <SectionHeader title="ניווט פלוגות" subtitle="בחירת פלוגה ותצוגה מהירה של כיסוי ודיווחים" />
              <div className="platoon-grid">
                {platoonCards.length ? (
                  platoonCards.map((card) => (
                    <PlatoonCard
                      key={card.name}
                      name={card.name}
                      coverage={card.coverage}
                      logo={platoonLogos[card.name] || platoonLogos.romach}
                      anomalyLabel={anomalyLabels[card.coverage?.anomaly]}
                      onSelect={(name) => update((prev) => ({ ...prev, platoon: name, viewMode: "platoon" }))}
                      isActive={platoon === card.name}
                    />
                  ))
                ) : (
                  <EmptyCard title="אין נתוני כיסוי" message="סנכרן מגוגל או העלה טפסים ידנית כדי לראות פלוגות." />
                )}
              </div>
            </section>

            <section id="views">
              <SectionHeader
                title="מצב תצוגה"
                subtitle="תמונת מצב נוכחית מהייבוא האחרון: גדוד שלם או פלוגה ממוקדת."
              >
                <Group gap="sm" wrap="wrap" className="controls">
                  <SegmentedControl
                    value={viewMode}
                    onChange={(value) => update((prev) => ({ ...prev, viewMode: value }))}
                    data={[
                      { label: "גדוד", value: "battalion" },
                      { label: "פלוגה", value: "platoon" },
                    ]}
                  />
                  <TextInput
                    label="שבוע (YYYY-Www)"
                    value={week}
                    onChange={(e) => update((prev) => ({ ...prev, week: e.target.value }))}
                    placeholder="לדוגמה 2026-W01"
                  />
                  <Select
                    label="פלוגה"
                    data={platoonOptions.map((p) => ({ value: p, label: p }))}
                    value={platoon}
                    onChange={(value) => update((prev) => ({ ...prev, platoon: value || "" }))}
                    placeholder="כפיר / סופה / מחץ"
                    searchable
                  />
                  <Badge variant="outline" color="teal">
                    סנכרון אחרון: {syncInfo.last} · {syncInfo.source}
                  </Badge>
                  <Badge variant="outline" color="gray">
                    ETag: {syncInfo.etag}
                  </Badge>
                </Group>
              </SectionHeader>

              <div className="kpi-row">
                <div className="kpi">
                  <div className="kpi-label">שבוע</div>
                  <div className="kpi-value">{summaryData?.week || "latest"}</div>
                </div>
                <div className="kpi">
                  <div className="kpi-label">מספר טנקים</div>
                  <div className="kpi-value">
                    {summaryData?.mode === "platoon" ? platoonSummary?.tank_count ?? "-" : battalionKpi?.tanks ?? "-"}
                  </div>
                </div>
                <div className="kpi">
                  <div className="kpi-label">סנכרון אחרון (טופס)</div>
                  <div className="kpi-value">
                    {syncInfo.last} · {syncInfo.source}
                  </div>
                </div>
                <div className="kpi">
                  <div className="kpi-label">ETag</div>
                  <div className="kpi-value">{syncInfo.etag}</div>
                </div>
              </div>

              {viewMode === "battalion" ? (
                <div className="grid two-col">
                  {platoonRows.length ? (
                    <SummaryTable
                      title="סיכום פלוגות"
                      headers={["פלוגה", "טנקים", "חוסרי זיווד", "חוסרי אמצעים"]}
                      rows={platoonRows}
                    />
                  ) : (
                    <EmptyCard title="אין סיכום פלוגות" message="סנכרן או העלה טפסים כדי לראות נתוני סיכום." />
                  )}
                  {Object.keys(summaryData?.battalion?.ammo || {}).length ? (
                    <SummaryTable
                      title="תחמושת גדודית"
                      headers={["אמצעי", "סה\"כ", "ממוצע לטנק"]}
                      rows={Object.entries(summaryData?.battalion?.ammo || {}).map(([item, vals]) => ({
                        key: item,
                        cells: [item, vals.total ?? 0, vals.avg_per_tank ?? 0],
                      }))}
                    />
                  ) : (
                    <EmptyCard title="אין נתוני תחמושת" message="העלאה/סנכרון נדרשים כדי לראות תחמושת." />
                  )}
                </div>
              ) : (
                <div className="grid two-col">
                  <SummaryTable title="זיווד חוסרים" headers={["פריט", "חוסרים/בלאי"]} rows={zivudRows} />
                  <SummaryTable title="תחמושת" headers={["אמצעי", "סה\"כ", "ממוצע לטנק"]} rows={ammoRows} />
                  {meansRows.length ? (
                    <SummaryTable
                      title="אמצעים"
                      headers={["אמצעי", "חוסרים/בלאי", "ממוצע לטנק"]}
                      rows={meansRows}
                    />
                  ) : (
                    <EmptyCard title="אין נתוני אמצעים" message="סנכרן כדי לראות אמצעים." />
                  )}
                  {issueRows.length ? (
                    <SummaryTable title="פערי צלמים" headers={["פריט", "צ טנק", "מט\"ק", "דגשים"]} rows={issueRows} />
                  ) : (
                    <EmptyCard title="אין פערי צלמים" message="אין דגשים לתצוגה." />
                  )}
                </div>
              )}

              <div className="grid two-col">
                {coverageRows.length ? (
                  <SummaryTable
                    title="כיסוי ודיווחים"
                    headers={["פלוגה", "מספר טפסים", "טנקים מדווחים", "ימים מאז דיווח", "אנומליה"]}
                    rows={coverageRows}
                  />
                ) : (
                  <EmptyCard title="אין כיסוי" message="סנכרון חסר. ודא שהנתונים זמינים." />
                )}
                {anomalyRows.length ? (
                  <SummaryTable
                    title="אנומליות"
                    headers={["פלוגה", "סיבה", "טפסים שבוע נוכחי", "ממוצע אחרון", "ימים ללא דיווח"]}
                    rows={anomalyRows}
                  />
                ) : (
                  <EmptyCard title="אין אנומליות" message="לא זוהו אנומליות פעילות." />
                )}
              </div>
            </section>

            <section id="analytics">
              <SectionHeader title="מדדי זיווד/תחמושת" subtitle={'סה"כ, חוסרים, דלתא וסטיות מהסיכום הגדודי'}>
                <Group gap="sm" wrap="wrap" className="controls">
                  <Select
                    label="תחום"
                    value={section}
                    onChange={(value) => update((prev) => ({ ...prev, section: value || "zivud" }))}
                    data={[
                      { value: "zivud", label: "זיווד" },
                      { value: "ammo", label: "תחמושת" },
                    ]}
                  />
                  <NumberInput
                    label="Top N"
                    value={topN}
                    min={1}
                    max={50}
                    onChange={(value) => update((prev) => ({ ...prev, topN: value || 5 }))}
                  />
                  <TextInput
                    label="פלוגה (אופציונלי)"
                    value={platoon}
                    onChange={(e) => update((prev) => ({ ...prev, platoon: e.target.value }))}
                    placeholder="כפיר / סופה / מחץ"
                  />
                  <TextInput
                    label="שבוע (אופציונלי)"
                    value={week}
                    onChange={(e) => update((prev) => ({ ...prev, week: e.target.value }))}
                    placeholder="2026-W01"
                  />
                  {lastUpdated && <span className="muted">עודכן לאחרונה: {lastUpdated}</span>}
                </Group>
              </SectionHeader>

              <div className="grid two-col">
                <ChartCard title="Totals" data={(tabularData.totals || []).map((t) => ({ item: t.item, value: t.total }))} />
                <ChartCard title="Gaps" data={(tabularData.gaps || []).map((g) => ({ item: g.item, value: g.gaps }))} color="#ef4444" />
              </div>

              <div className="grid two-col">
                <Card className="card">
                  <div className="card-title">Delta vs Previous Import</div>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th>Current</th>
                        <th>Prev</th>
                        <th>Δ</th>
                        <th>Pct</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedDelta.slice(0, 20).map((row) => (
                        <tr key={row.item}>
                          <td>{row.item}</td>
                          <td>{row.current}</td>
                          <td>{row.previous}</td>
                          <td>
                            <span className={`trend-chip ${row.direction}`}>
                              <span className="arrow" />
                              {row.delta?.toFixed(1)}
                            </span>
                          </td>
                          <td>{row.pct_change != null ? `${row.pct_change.toFixed(1)}%` : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
                <Card className="card">
                  <div className="card-title">Variance vs Battalion Summary</div>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th>Current</th>
                        <th>Summary</th>
                        <th>Var</th>
                        <th>Pct</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedVariance.slice(0, 20).map((row) => (
                        <tr key={row.item}>
                          <td>{row.item}</td>
                          <td>{row.current}</td>
                          <td>{row.summary}</td>
                          <td>
                            <span className={`trend-chip ${row.direction}`}>
                              <span className="arrow" />
                              {row.variance?.toFixed(1)}
                            </span>
                          </td>
                          <td>{row.pct_change != null ? `${row.pct_change.toFixed(1)}%` : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </div>

              <div className="card">
                <div className="card-title">מצב טפסים</div>
                <FormStatusTables formsOk={tabularData.forms?.ok} formsGaps={tabularData.forms?.gaps} topN={topN} />
              </div>

              <div className="grid two-col">
                <TrendTable title="Trends (top items, recent weeks)" data={tabularData.trends} />
                <div className="card">
                  <div className="card-title">AI Insight</div>
                  <div className="pill">
                    <span className="dot" />
                    Source: {tabularData.insights?.source || "n/a"} {tabularData.insights?.cached ? "(cached)" : ""}
                  </div>
                  <pre>{tabularData.insights?.content || "No insight yet."}</pre>
                </div>
              </div>
            </section>
          </>
        )}

        {activeTab === "export" && (
          <section id="export">
            <SectionHeader title="הפקת דוחות אקסל" subtitle="בחר שבוע ופלוגה להפקת דוח. לגדוד ניתן לבחור גדוד לריכוז.">
              <Group gap="sm" wrap="wrap" className="controls">
                <Select
                  label="פלוגה"
                  data={platoonOptions.map((p) => ({ value: p, label: p }))}
                  value={platoon}
                  onChange={(value) => update((prev) => ({ ...prev, platoon: value || "" }))}
                />
                <TextInput
                  label="שבוע (YYYY-Www)"
                  value={week}
                  onChange={(e) => update((prev) => ({ ...prev, week: e.target.value }))}
                  placeholder="לדוגמה 2026-W01"
                />
                <Button
                  variant="filled"
                  color="cyan"
                  onClick={() => handleExport("platoon")}
                  disabled={!platoon || exportMutation.isPending}
                  loading={exportMutation.isPending}
                >
                  ייצוא פלוגתי
                </Button>
                <Button variant="light" onClick={() => handleExport("battalion")} loading={exportMutation.isPending}>
                  ייצוא גדודי
                </Button>
              </Group>
            </SectionHeader>
            <div className="card">
              <p className="muted">
                הייצוא מתבצע כעת ישירות מה-API (לפי שבוע ופלוגה). ניתן עדיין להריץ CLI: scripts/seed-and-export.sh עבור זרימה מלאה.
              </p>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
