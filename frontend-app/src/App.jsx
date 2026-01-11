import { useEffect, useMemo, useRef, useState } from "react";
import { Badge, Button, Card, Collapse, Group, Paper, Select, SimpleGrid, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import "./index.css";

const storage = typeof window !== "undefined" ? window.localStorage : null;
const oauthUrl = typeof import.meta !== "undefined" && import.meta.env ? (import.meta.env.VITE_GOOGLE_OAUTH_URL || "") : "";
const storageKeys = [
  "IRONVIEW_API",
  "IRONVIEW_SECTION",
  "IRONVIEW_TOPN",
  "IRONVIEW_PLATOON",
  "IRONVIEW_WEEK",
  "IRONVIEW_VIEW",
  "IRONVIEW_TOKEN",
  "IRONVIEW_TAB",
  "IRONVIEW_USER",
];
const clearStoredState = () => {
  if (!storage) return;
  storageKeys.forEach((k) => {
    try {
      storage.removeItem(k);
    } catch {
      /* ignore */
    }
  });
};
const debugLog = (...args) => {
  if (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
};
const safeGet = (key) => {
  if (!storage) return null;
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
};
const fallbackApi = typeof window !== "undefined" ? window.location.origin.replace(/\/$/, "") : "http://localhost:8000";
const defaultApi = safeGet("IRONVIEW_API") || fallbackApi || "http://localhost:8000";
const persisted = (key, fallback) => {
  const raw = safeGet(key);
  if (raw === null) return fallback;
  if (typeof fallback === "number") {
    const parsed = Number(raw);
    return Number.isNaN(parsed) ? fallback : parsed;
  }
  return raw;
};

const friendlyImportName = (kind) => {
  if (kind === "platoon-loadout") return "דוח פלוגתי";
  if (kind === "battalion-summary") return "דוח גדודי";
  if (kind === "form-responses") return "טופס תגובות";
  return kind;
};

const assetBase = typeof window !== "undefined" && window.location.pathname.startsWith("/app") ? "/app" : "";
const logoPath = (file) => `${assetBase}/logos/${file}`;

const platoonLogos = {
  "כפיר": logoPath("Kfir_logo.JPG"),
  "סופה": logoPath("Sufa_logo.JPG"),
  "מחץ": logoPath("Machatz_logo.JPG"),
  "פלסם": logoPath("Palsam_logo.JPG"),
  romach: logoPath("Romach_75_logo.JPG"),
};

const knownPlatoons = ["כפיר", "סופה", "מחץ", "פלסם"];

const anomalyLabels = {
  no_reports: "אין דיווחים",
  low_volume: "נפח דיווח נמוך",
  stale: "לא דווח זמן רב",
};

const handleAuthBanner = (status, setBannerFn) => {
  if (status === 401) {
    setBannerFn({ text: "נדרש טוקן/Basic כדי לבצע פעולה זו", tone: "warning" });
    return true;
  }
  return false;
};

function LoginOverlay({ onLogin, defaultPlatoon }) {
  const [target, setTarget] = useState(defaultPlatoon || "battalion");
  const [email, setEmail] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const logoSrc = target === "battalion" ? platoonLogos.romach : platoonLogos[target] || platoonLogos.romach;

  const handleSubmit = (e) => {
    e.preventDefault();
    const viewMode = target === "battalion" ? "battalion" : "platoon";
    const platoon = target === "battalion" ? "" : target;
    onLogin({ platoon, email, token: tokenInput, viewMode });
  };

  const handleGoogle = () => {
    const viewMode = target === "battalion" ? "battalion" : "platoon";
    const platoon = target === "battalion" ? "" : target;
    if (oauthUrl) {
      const params = new URLSearchParams();
      params.append("platoon", platoon);
      params.append("viewMode", viewMode);
      if (email) params.append("email", email);
      if (tokenInput) params.append("token", tokenInput);
      const sep = oauthUrl.includes("?") ? "&" : "?";
      window.location.href = `${oauthUrl}${sep}${params.toString()}`;
      return;
    }
    notifications.show({ title: "OAuth לא מוגדר", message: "לא הוגדר VITE_GOOGLE_OAUTH_URL. משתמש בפלואו הידני.", color: "yellow" });
    onLogin({ platoon, email: email || "guest@spearhead.local", token: tokenInput, viewMode });
  };

  return (
    <div className="login-overlay">
      <Paper shadow="xl" radius="lg" className="login-card" withBorder>
        <Group justify="center" align="center">
          <Badge color="teal" radius="xl" variant="gradient" gradient={{ from: "green", to: "teal" }}>
            קצה הרומח · Spearhead
          </Badge>
        </Group>
        <div className="login-logo">
          <img src={logoSrc} alt={target === "battalion" ? "רומח" : target} />
        </div>
        <Title order={2} ta="center">כניסה</Title>
        <Text ta="center" c="dimmed" size="sm">בחר מצב (גדוד/פלוגה), הזדהה עם חשבון Google, והמשך לסנכרון אוטומטי.</Text>
        <Stack gap="xs" mt="sm" component="form" onSubmit={handleSubmit}>
          <Select
            label="מצב"
            value={target}
            onChange={(value) => setTarget(value || "battalion")}
            data={[
              { value: "battalion", label: "גדוד (רומח)" },
              { value: "כפיר", label: "כפיר" },
              { value: "סופה", label: "סופה" },
              { value: "מחץ", label: "מחץ" },
            ]}
            required
          />
          <TextInput
            label="מייל Google"
            placeholder="name@domain"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Collapse in={showAdvanced}>
            <TextInput
              label="טוקן (מתקדם/דב)"
              placeholder="Bearer/Basic"
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
            />
          </Collapse>
          <Button type="submit" color="cyan" radius="md" fullWidth>
            המשך וסנכרן
          </Button>
          <Button type="button" variant="light" radius="md" fullWidth onClick={handleGoogle}>
            כניסה עם Google
          </Button>
          <Button type="button" variant="subtle" radius="md" fullWidth onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced ? "הסתר מתקדם" : "שדות מתקדמים (דב)"}
          </Button>
        </Stack>
        <Text size="xs" c="dimmed" ta="center" mt="xs">
          סנכרון ינסה לרוץ אוטומטית לאחר הכניסה. ניתן להעלות קובץ טפסים ידנית במקרה של כשל.
        </Text>
      </Paper>
    </div>
  );
}

function SectionHeader({ title, subtitle, children }) {
  return (
    <div className="section-header">
      <div>
        <h2>{title}</h2>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      <div className="actions">{children}</div>
    </div>
  );
}

function UploadCard({ title, inputId, onUpload, disabled }) {
  return (
    <Card withBorder shadow="md" padding="md" radius="md">
      <Text fw={700} mb="xs">{title}</Text>
      <input type="file" id={inputId} disabled={disabled} />
      <Button
        fullWidth
        mt="sm"
        radius="md"
        onClick={() => onUpload(inputId)}
        disabled={disabled}
        loading={disabled}
      >
        העלה
      </Button>
      <div className="result" id={`result-${inputId}`} />
    </Card>
  );
}

function ChartCard({ title, data, color = "#22c55e" }) {
  const hasData = (data?.length || 0) > 0;
  const [recharts, setRecharts] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      const mod = await import("recharts");
      if (!mounted) return;
      setRecharts({
        ResponsiveContainer: mod.ResponsiveContainer,
        BarChart: mod.BarChart,
        Bar: mod.Bar,
        XAxis: mod.XAxis,
        YAxis: mod.YAxis,
        RTooltip: mod.Tooltip,
        Legend: mod.Legend,
        CartesianGrid: mod.CartesianGrid,
      });
    };
    load();
    return () => { mounted = false; };
  }, []);

  const { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, RTooltip, Legend, CartesianGrid } = recharts || {};
  return (
    <Card withBorder shadow="sm" padding="md" radius="md">
      <div className="card-title">{title}</div>
      {hasData && recharts ? (
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f293b" />
              <XAxis dataKey="item" stroke="#9fb3d0" />
              <YAxis stroke="#9fb3d0" />
              <RTooltip />
              <Legend />
              <Bar dataKey="value" fill={`${color}`} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="empty-hint">אין נתונים להצגה</div>
      )}
    </Card>
  );
}

function SummaryTable({ title, headers, rows }) {
  return (
    <Card withBorder shadow="sm" padding="md" radius="md">
      <div className="card-title">{title}</div>
      <table className="table">
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => (
              <tr key={row.key || row.cells[0]}>
                {row.cells.map((v, idx) => (
                  <td key={idx}>{v}</td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={headers.length}>אין נתונים</td>
            </tr>
          )}
        </tbody>
      </table>
    </Card>
  );
}

function PlatoonCard({ name, coverage, onSelect, isActive }) {
  const logo = platoonLogos[name] || platoonLogos.romach;
  const anomaly = coverage?.anomaly;
  const anomalyText = anomaly ? anomalyLabels[anomaly] || anomaly : null;
  return (
    <button className={`platoon-card ${isActive ? "active" : ""}`} onClick={() => onSelect(name)}>
      <div className="platoon-card__header">
        <div className="platoon-card__title">
          <span className="platoon-name">{name}</span>
          {anomaly && <span className="badge warn">אנומליה</span>}
        </div>
        <img src={logo} alt={name} className="platoon-logo" />
      </div>
      <div className="platoon-card__metrics">
        <div>
          <div className="metric-label">טפסים</div>
          <div className="metric-value">{coverage?.forms ?? 0}</div>
        </div>
        <div>
          <div className="metric-label">טנקים מדווחים</div>
          <div className="metric-value">{coverage?.distinct_tanks ?? 0}</div>
        </div>
        <div>
          <div className="metric-label">ימים ללא דיווח</div>
          <div className="metric-value">{coverage?.days_since_last ?? "-"}</div>
        </div>
      </div>
      <div className="platoon-card__footer">
        {anomaly ? <span className="muted">סיבה: {anomalyText}</span> : <span className="muted">מצב תקין</span>}
      </div>
    </button>
  );
}

function EmptyCard({ title, message }) {
  return (
    <Card withBorder shadow="sm" padding="md" radius="md">
      <div className="card-title">{title}</div>
      <div className="empty-card">{message}</div>
    </Card>
  );
}

function FormStatusTables({ formsOk, formsGaps }) {
  const okRows = (formsOk || []).map((f, idx) => ({ key: idx, cells: [f.platoon || f.item || "?", f.week || "?", f.total || f.count || 0] }));
  const gapRows = (formsGaps || []).map((f, idx) => ({ key: idx, cells: [f.platoon || f.item || "?", f.week || "?", f.total || f.count || 0] }));
  return (
    <div className="grid two-col">
      {okRows.length ? (
        <SummaryTable
          title="טפסים תקינים"
          headers={["פלוגה", "שבוע", "סה\"כ"]}
          rows={okRows}
        />
      ) : (
        <EmptyCard title="אין טפסים תקינים" message="לא נמצאו טפסים תקינים לנתונים שהועלו." />
      )}
      {gapRows.length ? (
        <SummaryTable
          title="פערי טפסים"
          headers={["פלוגה", "שבוע", "סה\"כ"]}
          rows={gapRows}
        />
      ) : (
        <EmptyCard title="אין פערי טפסים" message="לא נמצאו פערים ברשומות הטפסים." />
      )}
    </div>
  );
}

function KpiCard({ label, value, hint, tone = "neutral" }) {
  return (
    <Paper
      className={`kpi-card ${tone}`}
      withBorder
      shadow="sm"
      padding="md"
      radius="md"
    >
      <div className="kpi-card__label">{label}</div>
      <div className="kpi-card__value">{value}</div>
      {hint && <div className="kpi-card__hint">{hint}</div>}
    </Paper>
  );
}

function App() {
  const [apiBase, setApiBase] = useState(defaultApi);
  const [health, setHealth] = useState("Checking...");
  const [section, setSection] = useState(persisted("IRONVIEW_SECTION", "zivud"));
  const [topN, setTopN] = useState(persisted("IRONVIEW_TOPN", 5));
  const [platoon, setPlatoon] = useState(persisted("IRONVIEW_PLATOON", ""));
  const [week, setWeek] = useState(persisted("IRONVIEW_WEEK", ""));
  const [viewMode, setViewMode] = useState(persisted("IRONVIEW_VIEW", "battalion"));
  const [token, setToken] = useState(persisted("IRONVIEW_TOKEN", ""));
  const [activeTab, setActiveTab] = useState(persisted("IRONVIEW_TAB", "dashboard"));
  const [user, setUser] = useState(() => {
    const stored = safeGet("IRONVIEW_USER");
    if (!stored) return null;
    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  });
  const [autoSyncDone, setAutoSyncDone] = useState(false);
  const [summary, setSummary] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  const [platoonOptions, setPlatoonOptions] = useState([]);
  const [banner, setBanner] = useState(null); // {text, tone}
  const [lastUpdated, setLastUpdated] = useState(null);

  const [totals, setTotals] = useState([]);
  const [gaps, setGaps] = useState([]);
  const [delta, setDelta] = useState([]);
  const [variance, setVariance] = useState([]);
  const [forms, setForms] = useState({ ok: [], gaps: [] });
  const [coverage, setCoverage] = useState(null);
  const [insight, setInsight] = useState({ content: "", source: "" });
  const [trends, setTrends] = useState([]);
  const [sortField, setSortField] = useState("delta");
  const [sortDir, setSortDir] = useState("desc");
  const [syncing, setSyncing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [oauthReady] = useState(Boolean(oauthUrl));

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.title = "קצה הרומח · דשבורד מוכנות";
    }
  }, []);

  useEffect(() => { if (storage) storage.setItem("IRONVIEW_API", apiBase); }, [apiBase]);
  useEffect(() => { if (storage) storage.setItem("IRONVIEW_SECTION", section); }, [section]);
  useEffect(() => { if (storage) storage.setItem("IRONVIEW_TOPN", String(topN)); }, [topN]);
  useEffect(() => { if (storage) storage.setItem("IRONVIEW_PLATOON", platoon); }, [platoon]);
  useEffect(() => { if (storage) storage.setItem("IRONVIEW_WEEK", week); }, [week]);
  useEffect(() => { if (storage) storage.setItem("IRONVIEW_VIEW", viewMode); }, [viewMode]);
  useEffect(() => { if (storage) storage.setItem("IRONVIEW_TOKEN", token); }, [token]);
  useEffect(() => { if (storage) storage.setItem("IRONVIEW_TAB", activeTab); }, [activeTab]);
  useEffect(() => {
    if (user) {
      if (storage) storage.setItem("IRONVIEW_USER", JSON.stringify(user));
      if (user.token && !token) {
        setToken(user.token);
      }
      if (user.platoon && !platoon) {
        setPlatoon(user.platoon);
      }
    }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    pingHealth();
    loadStatus();
    loadSummary();
    loadQueries();
    loadCoverage();
    if (!autoSyncDone) {
      triggerSync();
      setAutoSyncDone(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, user]);

  useEffect(() => {
    if (!user) return;
    if (viewMode === "platoon" && !platoon) return;
    loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode, week, platoon]);

  useEffect(() => {
    if (!user) return;
    loadCoverage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [week]);

  useEffect(() => {
    if (!user) return;
    loadQueries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [week, platoon]);

  useEffect(() => {
    if (!week && summary?.week) {
      setWeek(summary.week);
    }
  }, [summary, week]);

  const pingHealth = async () => {
    try {
      const res = await fetch(`${apiBase}/health`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json();
      setHealth(`ON · v${data.version}`);
    } catch (err) {
      setHealth("לא מחובר");
    }
  };

  const loadStatus = async () => {
    try {
      const res = await fetch(`${apiBase}/sync/status`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (handleAuthBanner(res.status, setBanner)) return;
      const data = await res.json();
      setSyncStatus(data);
      if (data?.files?.form_responses?.last_sync) {
        setBanner({
          text: `סנכרון אחרון: ${data.files.form_responses.last_sync} (${data.files.form_responses.source || "n/a"})`,
          tone: data.files.form_responses.status === "ok" ? "success" : "warning",
        });
      }
    } catch (err) {
      setSyncStatus(null);
    }
  };

  const uploadFile = async (kind, inputId) => {
    const input = document.getElementById(inputId);
    const resultEl = document.getElementById(`result-${inputId}`);
    const file = input?.files?.[0];
    if (!file) {
      resultEl.textContent = "בחר/י קובץ";
      return;
    }
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    resultEl.textContent = "מעלה...";
    try {
      const res = await fetch(`${apiBase}/imports/${kind}`, {
        method: "POST",
        body: form,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (handleAuthBanner(res.status, setBanner)) {
        resultEl.textContent = "לא מורשה";
        return;
      }
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      resultEl.textContent = `הוכנסו ${data.inserted}`;
      setBanner({ text: `העלאה הצליחה (${friendlyImportName(kind)}) · נוספו ${data.inserted} רשומות`, tone: "success" });
      notifications.show({ title: "העלאה הושלמה", message: `נוספו ${data.inserted} רשומות (${friendlyImportName(kind)})`, color: "teal" });
      await loadQueries();
      await loadStatus();
      await loadSummary();
    } catch (err) {
      resultEl.textContent = `שגיאה: ${err}`;
      setBanner({ text: `שגיאה בהעלאה (${friendlyImportName(kind)}): ${err}`, tone: "danger" });
      notifications.show({ title: "שגיאה בהעלאה", message: String(err), color: "red" });
    }
    setUploading(false);
  };

  const loadSummary = async () => {
    try {
      if (viewMode === "platoon" && !platoon) {
        setSummary(null);
        return;
      }
      const params = new URLSearchParams();
      params.append("mode", viewMode);
      if (week) params.append("week", week);
      if (viewMode === "platoon" && platoon) params.append("platoon", platoon);
      const res = await fetch(`${apiBase}/queries/forms/summary?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (handleAuthBanner(res.status, setBanner)) return;
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSummary(data);
      const names = data.platoons ? Object.keys(data.platoons) : data.summary ? [data.summary.platoon] : [];
      if (names.length) setPlatoonOptions(names);
    } catch (err) {
      debugLog(err);
      setSummary(null);
    }
  };

  const loadCoverage = async () => {
    try {
      const params = new URLSearchParams();
      if (week) params.append("week", week);
      const res = await fetch(`${apiBase}/queries/forms/coverage?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (handleAuthBanner(res.status, setBanner)) return;
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setCoverage(data);
      if (!week && data.week) {
        setWeek(data.week);
      }
    } catch (err) {
      debugLog(err);
      setCoverage(null);
    }
  };

  const triggerSync = async () => {
    if (syncing) return;
    setBanner({ text: "סנכרון מתבצע...", tone: "warning" });
    setSyncing(true);
    try {
      const res = await fetch(`${apiBase}/sync/google?target=all`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (handleAuthBanner(res.status, setBanner)) return;
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setBanner({ text: `סנכרון הצליח · platoon:${data.platoon_loadout} summary:${data.battalion_summary} forms:${data.form_responses}`, tone: "success" });
      notifications.show({ title: "סנכרון הצליח", message: "הנתונים עודכנו מהמקור", color: "teal" });
      await loadStatus();
      await loadQueries();
      await loadSummary();
    } catch (err) {
      setBanner({ text: `שגיאה בסנכרון: ${err}`, tone: "danger" });
      notifications.show({ title: "שגיאה בסנכרון", message: String(err), color: "red" });
    }
    setSyncing(false);
  };

  const loadQueries = async () => {
    try {
      const platoonParam = platoon ? `&platoon=${encodeURIComponent(platoon)}` : "";
      const weekParam = week ? `&week=${encodeURIComponent(week)}` : "";
      const [t, g, d, v, f, ai, tr] = await Promise.all([
        fetch(`${apiBase}/queries/tabular/totals?section=${section}&top_n=${topN}${platoonParam}${weekParam}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }),
        fetch(`${apiBase}/queries/tabular/gaps?section=${section}&top_n=${topN}${platoonParam}${weekParam}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }),
        fetch(`${apiBase}/queries/tabular/delta?section=${section}&top_n=${topN}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }),
        fetch(`${apiBase}/queries/tabular/variance?section=${section}&top_n=${topN}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }),
        fetch(`${apiBase}/queries/forms/status`, { headers: token ? { Authorization: `Bearer ${token}` } : {} }),
        fetch(`${apiBase}/insights?section=${section}&top_n=${topN}${platoonParam}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }),
        fetch(`${apiBase}/queries/trends?section=${section}&top_n=5${platoonParam}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }),
      ]);
      if ([t, g, d, v, f, ai, tr].some((res) => handleAuthBanner(res.status, setBanner))) {
        return;
      }
      const [tJson, gJson, dJson, vJson, fJson, aiJson, trJson] = await Promise.all([
        t.json(),
        g.json(),
        d.json(),
        v.json(),
        f.json(),
        ai.json(),
        tr.json(),
      ]);
      setTotals(tJson);
      setGaps(gJson);
      setDelta(dJson);
      setVariance(vJson);
      setForms(fJson);
      setInsight(aiJson);
      setTrends(trJson);
      setLastUpdated(new Date().toLocaleString());
    } catch (err) {
      setBanner({ text: "שגיאה בטעינת נתונים. בדוק כתובת API או הרשאות.", tone: "danger" });
    }
  };

  const exportReport = async (mode) => {
    if (exporting) return;
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (week) params.append("week", week);
      if (mode === "platoon") {
        if (!platoon) throw new Error("בחר פלוגה לייצוא פלוגתי");
        params.append("platoon", platoon);
      }
      const endpoint = mode === "platoon" ? "/exports/platoon" : "/exports/battalion";
      const res = await fetch(`${apiBase}${endpoint}?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        let detail = "";
        try {
          const errJson = await res.json();
          detail = errJson.detail || JSON.stringify(errJson);
        } catch {
          detail = await res.text();
        }
        throw new Error(detail || "Export failed");
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const fname = mode === "platoon" ? `platoon_${platoon}_${week || "latest"}.xlsx` : `battalion_${week || "latest"}.xlsx`;
      link.download = fname;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      notifications.show({ title: "הייצוא מוכן", message: `הקובץ ${fname} ירד בהצלחה`, color: "teal" });
    } catch (err) {
      notifications.show({ title: "שגיאה בייצוא", message: String(err), color: "red" });
    }
    setExporting(false);
  };

  const sortedDelta = useMemo(() => {
    const data = [...delta];
    return data.sort((a, b) => {
      const field = sortField || "delta";
      const dir = sortDir === "asc" ? 1 : -1;
      return (a[field] ?? 0) > (b[field] ?? 0) ? dir : -dir;
    });
  }, [delta, sortField, sortDir]);

  const sortedVariance = useMemo(() => {
    const data = [...variance];
    return data.sort((a, b) => {
      const field = sortField === "delta" ? "variance" : sortField;
      const dir = sortDir === "asc" ? 1 : -1;
      return (a[field] ?? 0) > (b[field] ?? 0) ? dir : -dir;
    });
  }, [variance, sortField, sortDir]);

  const deltaText = useMemo(() => JSON.stringify(delta, null, 2), [delta]);
  const varianceText = useMemo(() => JSON.stringify(variance, null, 2), [variance]);
  const formsOk = useMemo(() => JSON.stringify((forms.ok || []).slice(0, topN), null, 2), [forms.ok, topN]);
  const formsGaps = useMemo(() => JSON.stringify((forms.gaps || []).slice(0, topN), null, 2), [forms.gaps, topN]);

  const platoonSummary = useMemo(() => {
    if (!summary) return null;
    if (summary.mode === "platoon") return summary.summary;
    if (summary.mode === "battalion" && platoon && summary.platoons?.[platoon]) {
      return summary.platoons[platoon];
    }
    return null;
  }, [summary, platoon]);

  const platoonRows = useMemo(() => {
    if (!summary?.platoons) return [];
    return Object.values(summary.platoons).map((p) => {
      const zivudTotal = Object.values(p.zivud_gaps || {}).reduce((acc, v) => acc + (v || 0), 0);
      const meansTotal = Object.values(p.means || {}).reduce((acc, v) => acc + (v?.count || 0), 0);
      return {
        key: p.platoon,
        cells: [p.platoon, p.tank_count, zivudTotal, meansTotal],
      };
    });
  }, [summary]);

  const battalionKpi = useMemo(() => {
    if (!summary?.battalion) return null;
    return {
      week: summary.week || summary.latest_week || "latest",
      tanks: summary.battalion.tank_count,
      source: syncStatus?.files?.form_responses?.source || "n/a",
      lastSync: syncStatus?.files?.form_responses?.last_sync || "n/a",
      etag: syncStatus?.files?.form_responses?.etag || "n/a",
    };
  }, [summary, syncStatus]);

  const coverageRows = useMemo(() => {
    if (!coverage?.platoons) return [];
    return Object.entries(coverage.platoons).map(([name, c]) => ({
      key: name,
      cells: [
        name,
        c.forms ?? 0,
        c.distinct_tanks ?? 0,
        c.days_since_last ?? "-",
        c.anomaly ? anomalyLabels[c.anomaly] || c.anomaly : "תקין",
      ],
    }));
  }, [coverage]);

  const anomalyRows = useMemo(() => {
    if (!coverage?.anomalies?.length) return [];
    return coverage.anomalies.map((a, idx) => ({
      key: `${a.platoon}-${idx}`,
      cells: [
        a.platoon,
        anomalyLabels[a.reason] || a.reason,
        a.forms ?? 0,
        a.avg_forms_recent ?? "-",
        a.days_since_last ?? "-",
      ],
    }));
  }, [coverage]);

  const platoonCards = useMemo(() => {
    const entries = Object.entries(coverage?.platoons || {}).filter(([, c]) => (c?.forms || c?.distinct_tanks || 0) > 0);
    if (entries.length) {
      return entries.map(([name, cov]) => ({ name, coverage: cov }));
    }
    return knownPlatoons
      .filter((name) => coverage?.platoons?.[name])
      .map((name) => ({ name, coverage: coverage.platoons[name] }));
  }, [coverage]);

  const syncInfo = useMemo(() => {
    const forms = syncStatus?.files?.form_responses;
    return {
      status: forms?.status || (syncStatus?.enabled ? "enabled" : "disabled"),
      last: forms?.last_sync || "n/a",
      source: forms?.source || "n/a",
      etag: forms?.etag || "n/a",
    };
  }, [syncStatus]);

  const coverageTotals = useMemo(() => {
    const platoons = coverage?.platoons || {};
    const formsTotal = Object.values(platoons).reduce((acc, p) => acc + (p.forms || 0), 0);
    const tanksTotal = Object.values(platoons).reduce((acc, p) => acc + (p.distinct_tanks || 0), 0);
    const anomaliesCount = coverage?.anomalies?.length || 0;
    return { formsTotal, tanksTotal, anomaliesCount };
  }, [coverage]);

  const handleLogin = (payload) => {
    setUser({ platoon: payload.platoon, email: payload.email, token: payload.token || "" });
    setToken(payload.token || "");
    setViewMode(payload.viewMode || (payload.platoon ? "platoon" : "battalion"));
    setActiveTab("dashboard");
  };

  const zivudRows = useMemo(
    () => Object.entries(platoonSummary?.zivud_gaps || {}).map(([item, count]) => ({ key: item, cells: [item, count] })),
    [platoonSummary]
  );
  const ammoRows = useMemo(
    () =>
      Object.entries(platoonSummary?.ammo || {}).map(([item, vals]) => ({
        key: item,
        cells: [item, vals.total ?? 0, vals.avg_per_tank ?? 0],
      })),
    [platoonSummary]
  );
  const meansRows = useMemo(
    () =>
      Object.entries(platoonSummary?.means || {}).map(([item, vals]) => ({
        key: item,
        cells: [item, vals.count ?? 0, vals.avg_per_tank ?? 0],
      })),
    [platoonSummary]
  );
  const issueRows = useMemo(
    () =>
      (platoonSummary?.issues || []).map((issue, idx) => ({
        key: `${issue.item}-${idx}`,
        cells: [issue.item, issue.tank_id, issue.commander || "", issue.detail],
      })),
    [platoonSummary]
  );

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
          {data.map((row) =>
            (row.points || []).map((p) => (
              <tr key={`${row.item}-${p.week}`}>
                <td>{row.item}</td>
                <td>{p.week}</td>
                <td>{p.total}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );

  if (!user) {
    return <LoginOverlay onLogin={handleLogin} defaultPlatoon={platoon || "battalion"} />;
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="hero">
          <div className="hero-text">
            <Badge color="teal" size="lg" radius="md" variant="gradient" gradient={{ from: "green", to: "teal" }}>
              קצה הרומח · רומח 75
            </Badge>
            <Title order={2} mt="xs">דשבורד מוכנות</Title>
            <Text className="muted">סקירה פלוגתית/גדודית, סנכרון מגוגל, כיסוי ואנומליות.</Text>
            <Group gap="xs" mt="sm" wrap="wrap" className="header-actions">
              <Badge variant="light" color="gray">משתמש: {user.email || "לא צוין"}</Badge>
              <Badge variant="light" color="cyan">מצב: {viewMode === "battalion" ? "גדוד" : "פלוגה"} {user.platoon ? `· ${user.platoon}` : ""}</Badge>
              <Badge variant="outline" color="green">{health}</Badge>
              <Badge variant="outline" color={syncStatus?.enabled ? "teal" : "gray"}>
                {syncStatus?.enabled ? "Google Sync פעיל" : "Google Sync כבוי"}
              </Badge>
              <Button
                variant="light"
                size="xs"
                color="red"
                onClick={() => { setUser(null); setToken(""); if (storage) storage.removeItem("IRONVIEW_USER"); }}
              >
                התנתק
              </Button>
            </Group>
          </div>
          <img
            src={viewMode === "battalion" || !user.platoon ? platoonLogos.romach : platoonLogos[user.platoon] || platoonLogos.romach}
            alt={viewMode === "battalion" ? "רומח 75" : user.platoon}
            className="hero-logo"
          />
        </div>
      </header>

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
              <Button variant={activeTab === "dashboard" ? "filled" : "light"} onClick={() => setActiveTab("dashboard")}>
                דשבורד
              </Button>
              <Button variant={activeTab === "export" ? "filled" : "light"} onClick={() => setActiveTab("export")}>
                הפקת דוחות
              </Button>
            </Group>
            <Group gap="xs" className="button-group">
              <Button onClick={triggerSync} loading={syncing} variant="filled" color="cyan">סנכרון מ-Google</Button>
              <Button
                onClick={async () => {
                  if (refreshing) return;
                  setRefreshing(true);
                  await Promise.all([loadQueries(), loadSummary(), loadStatus(), loadCoverage()]);
                  setRefreshing(false);
                }}
                loading={refreshing}
                variant="light"
              >
                רענון נתונים
              </Button>
            </Group>
          </Group>
        </div>

        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md" className="kpi-strip">
          <KpiCard label="שבוע נוכחי" value={summary?.latest_week || summary?.week || coverage?.week || "n/a"} />
          <KpiCard
            label="דיווחים השבוע"
            value={coverageTotals.formsTotal || 0}
            hint="סך טפסים מכל הפלוגות"
          />
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
            <UploadCard title="Form Responses" inputId="file-form" onUpload={(id) => uploadFile("form-responses", id)} disabled={uploading} />
          </div>
          {!syncStatus && (
            <div className="empty-state">
              אין נתונים עדיין. התחבר/י וסנכרן מגוגל או העלה קובץ טפסים ידנית כדי לטעון את הדאטה.
            </div>
            )}
            <div className="actions" style={{ marginTop: 10 }}>
              <button onClick={triggerSync} disabled={syncing}>{syncing ? "מסנכרן..." : "סנכרון מ-Google Sheets"}</button>
              <button
                onClick={async () => {
                  if (refreshing) return;
                  setRefreshing(true);
                  await Promise.all([loadQueries(), loadSummary(), loadStatus(), loadCoverage()]);
                  setRefreshing(false);
                }}
                disabled={refreshing}
              >
                {refreshing ? "מרענן..." : "רענון נתונים"}
              </button>
            </div>
          </section>

            <section id="platoons">
              <SectionHeader title="ניווט פלוגות" subtitle="בחירת פלוגה ותצוגה מהירה של כיסוי ודיווחים" />
              <div className="platoon-grid">
                {platoonCards.length ? platoonCards.map((card) => (
                  <PlatoonCard
                    key={card.name}
                    name={card.name}
                    coverage={card.coverage}
                    onSelect={(name) => {
                      setPlatoon(name);
                      setViewMode("platoon");
                    }}
                    isActive={platoon === card.name}
                  />
                )) : (
                  <EmptyCard title="אין נתוני כיסוי" message="סנכרן מגוגל או העלה טפסים ידנית כדי לראות פלוגות." />
                )}
              </div>
            </section>

            <section id="views">
              <SectionHeader
                title="מצב תצוגה"
                subtitle="תמונת מצב נוכחית מהייבוא האחרון: גדוד שלם או פלוגה ממוקדת."
              >
                <div className="controls">
                  <div className="segmented">
                    <button className={viewMode === "battalion" ? "active" : ""} onClick={() => setViewMode("battalion")}>
                      גדוד
                    </button>
                    <button className={viewMode === "platoon" ? "active" : ""} onClick={() => setViewMode("platoon")}>
                      פלוגה
                    </button>
                  </div>
                  <label>
                    שבוע (YYYY-Www):
                    <input type="text" placeholder="לדוגמה 2026-W01" value={week} onChange={(e) => setWeek(e.target.value)} />
                  </label>
                  <label>
                    פלוגה:
                    <input
                      list="platoon-options"
                      type="text"
                      value={platoon}
                      onChange={(e) => setPlatoon(e.target.value)}
                      placeholder="כפיר / סופה / מחץ"
                    />
                    <datalist id="platoon-options">
                      {platoonOptions.map((p) => (
                        <option key={p} value={p} />
                      ))}
                    </datalist>
                  </label>
                </div>
              </SectionHeader>

              <div className="kpi-row">
                <div className="kpi">
                  <div className="kpi-label">שבוע</div>
                  <div className="kpi-value">{summary?.week || "latest"}</div>
                </div>
                <div className="kpi">
                  <div className="kpi-label">מספר טנקים</div>
                  <div className="kpi-value">{summary?.mode === "platoon" ? platoonSummary?.tank_count ?? "-" : battalionKpi?.tanks ?? "-"}</div>
                </div>
                <div className="kpi">
                  <div className="kpi-label">סנכרון אחרון (טופס)</div>
                  <div className="kpi-value">
                    {syncStatus?.files?.form_responses?.last_sync || "n/a"} · {syncStatus?.files?.form_responses?.source || "unknown"}
                  </div>
                </div>
                <div className="kpi">
                  <div className="kpi-label">ETag</div>
                  <div className="kpi-value">{syncStatus?.files?.form_responses?.etag || "n/a"}</div>
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
                  {Object.keys(summary?.battalion?.ammo || {}).length ? (
                    <SummaryTable
                      title="תחמושת גדודית"
                      headers={["אמצעי", "סה\"כ", "ממוצע לטנק"]}
                      rows={Object.entries(summary?.battalion?.ammo || {}).map(([item, vals]) => ({
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
                  <SummaryTable
                    title="תחמושת"
                    headers={["אמצעי", "סה\"כ", "ממוצע לטנק"]}
                    rows={ammoRows}
                  />
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
                <div className="controls">
                  <label>
                    תחום:
                    <select value={section} onChange={(e) => setSection(e.target.value)}>
                      <option value="zivud">זיווד</option>
                      <option value="ammo">תחמושת</option>
                    </select>
                  </label>
                  <label>
                    Top N:
                    <input type="number" value={topN} min={1} max={50} onChange={(e) => setTopN(Number(e.target.value))} />
                  </label>
                  <label>
                    פלוגה (אופציונלי):
                    <input type="text" value={platoon} onChange={(e) => setPlatoon(e.target.value)} placeholder="כפיר / סופה / מחץ" />
                  </label>
                  <label>
                    שבוע (אופציונלי):
                    <input type="text" value={week} onChange={(e) => setWeek(e.target.value)} placeholder="2026-W01" />
                  </label>
                  <label>
                    מיון:
                    <select value={sortField} onChange={(e) => setSortField(e.target.value)}>
                      <option value="delta">Delta</option>
                      <option value="pct_change">% שינוי</option>
                      <option value="variance">פער מול גדוד</option>
                    </select>
                  </label>
                  <label>
                    כיוון:
                    <select value={sortDir} onChange={(e) => setSortDir(e.target.value)}>
                      <option value="desc">יורד</option>
                      <option value="asc">עולה</option>
                    </select>
                  </label>
                  {lastUpdated && <span className="muted">עודכן לאחרונה: {lastUpdated}</span>}
                </div>
              </SectionHeader>

              <div className="grid two-col">
                <ChartCard title="Totals" data={totals.map((t) => ({ item: t.item, value: t.total }))} />
                <ChartCard title="Gaps" data={gaps.map((g) => ({ item: g.item, value: g.gaps }))} color="#ef4444" />
              </div>

              <div className="grid two-col">
                <div className="card">
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
                </div>
                <div className="card">
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
                </div>
              </div>

              <div className="card">
                <div className="card-title">מצב טפסים</div>
                <FormStatusTables formsOk={forms.ok} formsGaps={forms.gaps} />
              </div>

              <div className="grid two-col">
                <TrendTable title="Trends (top items, recent weeks)" data={trends} />
                <div className="card">
                  <div className="card-title">AI Insight</div>
                  <div className="pill">
                    <span className="dot" />
                    Source: {insight.source || "n/a"} {insight.cached ? "(cached)" : ""}
                  </div>
                  <pre>{insight.content || "No insight yet."}</pre>
                </div>
              </div>
            </section>
          </>
        )}

        {activeTab === "export" && (
          <section id="export">
            <SectionHeader title="הפקת דוחות אקסל" subtitle="בחר שבוע ופלוגה להפקת דוח. לגדוד ניתן לבחור גדוד לריכוז.">
              <div className="controls">
                <label>
                  פלוגה:
                  <select value={platoon} onChange={(e) => setPlatoon(e.target.value)}>
                    <option value="כפיר">כפיר</option>
                    <option value="סופה">סופה</option>
                    <option value="מחץ">מחץ</option>
                  </select>
                </label>
                <label>
                  שבוע (YYYY-Www):
                  <input type="text" value={week} onChange={(e) => setWeek(e.target.value)} placeholder="לדוגמה 2026-W01" />
                </label>
                <Button
                  variant="filled"
                  color="cyan"
                  onClick={() => exportReport("platoon")}
                  disabled={!platoon || exporting}
                  loading={exporting}
                >
                  ייצוא פלוגתי
                </Button>
                <Button
                  variant="light"
                  onClick={() => exportReport("battalion")}
                  loading={exporting}
                >
                  ייצוא גדודי
                </Button>
              </div>
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
