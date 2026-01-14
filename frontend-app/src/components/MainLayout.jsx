import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Group,
  SimpleGrid,
  SegmentedControl,
  Select,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useDashboard } from "../context/DashboardContext";
import { useOAuthLanding } from "../hooks/useOAuthLanding";
import { useAutoSync } from "../hooks/useAutoSync";

import { EmptyCard } from "./EmptyCard";
import { HeroHeader } from "./HeroHeader";
import { KpiCard } from "./KpiCard";
import { LoginOverlay } from "./LoginOverlay";
import { PlatoonCard } from "./PlatoonCard";
import { SectionHeader } from "./SectionHeader";
import { BattalionView } from "./views/BattalionView";
import { PlatoonView } from "./views/PlatoonView";

// Logos
const assetBase =
  typeof window !== "undefined" && window.location.pathname.startsWith("/app")
    ? "/app"
    : "";
const logoPath = (file) => `${assetBase}/logos/${file}`;
const platoonLogos = {
  כפיר: logoPath("Kfir_logo.JPG"),
  סופה: logoPath("Sufa_logo.JPG"),
  מחץ: logoPath("Machatz_logo.JPG"),
  פלסם: logoPath("Palsam_logo.JPG"),
  romach: logoPath("Romach_75_logo.JPG"),
};

// OAuth Config
const oauthUrl = import.meta.env.VITE_GOOGLE_OAUTH_URL || "";
const oauthReady = Boolean(oauthUrl);

export function MainLayout() {
  const { state, update, actions, data, helpers } = useDashboard();
  const { user, viewMode, platoon, week, activeTab } = state;
  const { health, summary, coverage, syncStatus } = data;
  const { uploadMutation, exportMutation, login, logout } = actions;

  const [banner, setBanner] = useState(null);

  // --- Auto Sync ---
  const { isSyncing } = useAutoSync();

  // --- OAuth Handling ---
  const applyOAuth = useCallback(
    (payload) => {
      update((prev) => ({
        ...prev,
        token: payload.token || prev.token,
        oauthSession: payload.session || payload.token || prev.oauthSession,
        user: {
          email: payload.email || prev.user?.email || "",
          platoon: payload.platoon || prev.user?.platoon || "",
          role: payload.role || "viewer",
          token: payload.token || prev.token,
        },
        platoon: payload.platoon || prev.platoon,
        viewMode:
          payload.viewMode || (payload.platoon ? "platoon" : "battalion"),
        activeTab: "dashboard",
      }));
    },
    [update]
  );
  useOAuthLanding(applyOAuth);

  // --- Title & Metadata ---
  useEffect(() => {
    document.title = "קצה הרומח · דשבורד מוכנות";
  }, []);

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
  const healthLabel = health.data
    ? `ON · v${health.data.version}`
    : health.isError
    ? "לא מחובר"
    : "בודק...";

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
    const list = helpers?.knownPlatoons || [];
    return list
      .map((name) => ({
        name,
        coverage: coverageData?.platoons?.[name],
        logo: platoonLogos[name] || platoonLogos.romach,
      }))
      .filter((c) => c.coverage || activeTab === "dashboard");
  }, [helpers, coverageData, activeTab]);

  const platoonOptions = helpers?.knownPlatoons || [];

  // --- Handlers ---
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

  const handleUpload = async (file) => {
    try {
      const res = await uploadMutation.mutateAsync({
        kind: "form-responses",
        file,
      });
      notifications.show({
        title: "העלאה",
        message: `נקלטו ${res.inserted} רשומות`,
        color: "teal",
      });
      summary.refetch();
      coverage.refetch();
    } catch (e) {
      handleApiError(e, "העלאה נכשלה");
    }
  };

  if (!user) {
    return (
      <LoginOverlay
        onLogin={login}
        defaultPlatoon={platoon || "battalion"}
        oauthReady={oauthReady}
        oauthUrl={oauthUrl}
        logos={platoonLogos}
      />
    );
  }

  // --- Render ---
  return (
    <div className="page">
      <HeroHeader
        user={user}
        viewMode={viewMode}
        platoon={platoon}
        health={healthLabel}
        syncEnabled={syncStatus.data?.enabled}
        onLogout={logout}
        logoSrc={
          viewMode === "battalion"
            ? platoonLogos.romach
            : platoonLogos[platoon] || platoonLogos.romach
        }
      />

      {banner && (
        <div className={`banner ${banner.tone || "info"}`}>
          <span>{banner.text}</span>
          <button className="banner-close" onClick={() => setBanner(null)}>
            ×
          </button>
        </div>
      )}

      <main>
        {/* Actions Bar */}
        <div className="actions-bar">
          <Group justify="space-between">
            <Group>
              <Button
                variant={activeTab === "dashboard" ? "filled" : "light"}
                onClick={() =>
                  update((s) => ({ ...s, activeTab: "dashboard" }))
                }
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
              {isSyncing && (
                <Badge color="cyan" variant="light">
                  מסנכרן נתונים...
                </Badge>
              )}
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
            {/* View Controls */}
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

            {/* Detailed Views (Delegated) */}
            {viewMode === "battalion" ? <BattalionView /> : <PlatoonView />}

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
              <Button onClick={() => handleExport("battalion")}>
                ייצוא גדודי
              </Button>
              <Button
                onClick={() => handleExport("platoon")}
                disabled={!platoon}
              >
                ייצוא פלוגתי
              </Button>
            </Group>
          </div>
        )}
      </main>
    </div>
  );
}
