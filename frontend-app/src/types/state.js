const fallbackBase =
  typeof window !== "undefined" ? window.location.origin.replace(/\/$/, "") : "http://localhost:8000";

export const STORAGE_KEY = "IRONVIEW_STATE";

export const defaultDashboardState = {
  apiBase: fallbackBase,
  section: "zivud",
  topN: 5,
  platoon: "",
  week: "",
  viewMode: "battalion",
  activeTab: "dashboard",
  token: "",
  oauthSession: "",
  user: null,
};

export const knownPlatoons = ["כפיר", "סופה", "מחץ", "פלסם"];

export const anomalyLabels = {
  no_reports: "אין דיווחים",
  low_volume: "נפח דיווח נמוך",
  stale: "לא דווח זמן רב",
};
