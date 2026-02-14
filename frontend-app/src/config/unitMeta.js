const baseUrl = (import.meta.env.BASE_URL || "/").replace(/\/?$/, "/");

const logoPath = (fileName) => `${baseUrl}logos/${fileName}`;

const UNIT_CATALOG = {
  battalion: {
    key: "battalion",
    label: "גדוד 75 - רומח",
    shortLabel: "גדוד",
    color: "#0ea5a4",
    logo: logoPath("Romach_75_logo.JPG"),
  },
  "כפיר": {
    key: "כפיר",
    label: "פלוגת כפיר",
    shortLabel: "כפיר",
    color: "#2563eb",
    logo: logoPath("Kfir_logo.JPG"),
  },
  "מחץ": {
    key: "מחץ",
    label: "פלוגת מחץ",
    shortLabel: "מחץ",
    color: "#7c3aed",
    logo: logoPath("Machatz_logo.JPG"),
  },
  "סופה": {
    key: "סופה",
    label: "פלוגת סופה",
    shortLabel: "סופה",
    color: "#ec4899",
    logo: logoPath("Sufa_logo.JPG"),
  },
  "פלס״מ": {
    key: "פלס״מ",
    label: "פלס״מ",
    shortLabel: "פלס״מ",
    color: "#64748b",
    logo: logoPath("Palsam_logo.JPG"),
  },
};

const NORMALIZED_ALIASES = {
  battalion: "battalion",
  גדוד: "battalion",
  גדוד75: "battalion",
  romach: "battalion",
  romach75: "battalion",
  kfir: "כפיר",
  כפיר: "כפיר",
  machatz: "מחץ",
  mahatz: "מחץ",
  מחץ: "מחץ",
  sufa: "סופה",
  סופה: "סופה",
  palsam: "פלס״מ",
  פלסם: "פלס״מ",
  פלסמ: "פלס״מ",
  "פלס״מ": "פלס״מ",
  "פלס\"ם": "פלס״מ",
};

const normalizeKey = (value) => {
  const raw = `${value || ""}`.trim();
  if (!raw) return "battalion";
  const ascii = raw.toLowerCase().replace(/[\s_-]/g, "");
  const hebrew = raw.replace(/[\s_-׳״"']/g, "");
  return NORMALIZED_ALIASES[ascii] || NORMALIZED_ALIASES[hebrew] || raw;
};

export const getUnitMeta = (value) => {
  const normalized = normalizeKey(value);
  if (UNIT_CATALOG[normalized]) return UNIT_CATALOG[normalized];
  return {
    key: `${value || "unit"}`,
    label: `${value || "יחידה"}`,
    shortLabel: `${value || "-"}`,
    color: "#64748b",
    logo: UNIT_CATALOG.battalion.logo,
  };
};

export const COMPANY_KEYS = ["כפיר", "מחץ", "סופה"];

export const LOGIN_UNIT_OPTIONS = [
  { value: "battalion", label: UNIT_CATALOG.battalion.shortLabel },
  ...COMPANY_KEYS.map((key) => ({ value: key, label: key })),
];

export const COMPANY_UNIT_METAS = COMPANY_KEYS.map((key) => UNIT_CATALOG[key]);

export const battalionMeta = UNIT_CATALOG.battalion;
