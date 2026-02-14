export const DEFAULT_SECTIONS = ["Logistics", "Armament", "Communications"];

export const SECTION_DISPLAY = {
  Logistics: "לוגיסטיקה",
  Armament: "חימוש",
  Communications: "תקשוב",
};

export function deltaColor(value) {
  if (value > 0) return "red";
  if (value < 0) return "teal";
  return "gray";
}

export function formatDelta(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return "0";
  const rendered = digits > 0 ? number.toFixed(digits) : Math.round(number).toString();
  return number > 0 ? `+${rendered}` : rendered;
}

export function readinessDeltaColor(value) {
  if (value > 0) return "teal";
  if (value < 0) return "red";
  return "gray";
}

export function formatScore(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${Number(value).toFixed(1)}%`;
}

export function readinessVisual(score, { reportedThisWeek = true } = {}) {
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

export function displaySection(section, sectionNames = {}) {
  return sectionNames?.[section] || SECTION_DISPLAY[section] || section;
}

export function displayStatus(status) {
  const map = {
    OK: "תקין",
    Gap: "פערים",
    Critical: "קריטי",
    NoReport: "ללא דיווח",
  };
  return map[status] || status || "-";
}

export function formatTankLabel(value) {
  const raw = `${value || ""}`.trim();
  if (!raw) return "צ׳-";
  const digits = raw.match(/\d{2,4}/)?.[0];
  if (digits) return `צ׳${digits}`;
  if (raw.startsWith("צ׳") || raw.startsWith("צ'")) return raw.replace(/^צ[׳']+/, "צ׳");
  return raw;
}
