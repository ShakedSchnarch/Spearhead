import { useEffect, useMemo, useRef, useState } from "react";
import { Chart, BarController, BarElement, CategoryScale, LinearScale, Tooltip } from "chart.js";
import "./index.css";

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip);

const fallbackApi = typeof window !== "undefined" ? window.location.origin.replace(/\/$/, "") : "http://localhost:8000";
const defaultApi = localStorage.getItem("IRONVIEW_API") || fallbackApi || "http://localhost:8000";
const persisted = (key, fallback) => {
  const raw = localStorage.getItem(key);
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
  const [platoon, setPlatoon] = useState(defaultPlatoon || "כפיר");
  const [email, setEmail] = useState("");
  const [tokenInput, setTokenInput] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onLogin({ platoon, email, token: tokenInput });
  };

  return (
    <div className="login-overlay">
      <div className="login-card">
        <div className="pill brand">קצה הרומח · Spearhead</div>
        <h1>כניסה</h1>
        <p className="muted">בחר פלוגה, הזדהה עם חשבון Google, והמשך לסנכרון.</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            פלוגה:
            <select value={platoon} onChange={(e) => setPlatoon(e.target.value)}>
              <option value="כפיר">כפיר</option>
              <option value="סופה">סופה</option>
              <option value="מחץ">מחץ</option>
            </select>
          </label>
          <label>
            מייל Google:
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@domain" required />
          </label>
          <label>
            טוקן (אם נדרש):
            <input type="password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="Bearer/Basic" />
          </label>
          <button type="submit" className="primary">המשך וסנכרן</button>
        </form>
        <div className="login-note muted">סנכרון ינסה לרוץ אוטומטית לאחר הכניסה.</div>
      </div>
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

function UploadCard({ title, inputId, onUpload }) {
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <input type="file" id={inputId} />
      <button onClick={() => onUpload(inputId)}>העלה</button>
      <div className="result" id={`result-${inputId}`} />
    </div>
  );
}

function ChartCard({ title, data, color = "#22c55e" }) {
  const ref = useRef(null);
  const chartRef = useRef(null);
  const hasData = (data?.length || 0) > 0;

  useEffect(() => {
    if (!ref.current) return;
    if (chartRef.current) chartRef.current.destroy();

    const labels = data?.map((d) => d.item) || [];
    const values = data?.map((d) => d.value ?? d.total ?? d.gaps ?? 0) || [];

    chartRef.current = new Chart(ref.current, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: title,
            data: values,
            backgroundColor: `${color}99`,
            borderColor: color,
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#475569" }, grid: { display: false } },
          y: { ticks: { color: "#475569" }, grid: { color: "#e2e8f0" } },
        },
      },
    });
  }, [data, title, color]);

  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <canvas ref={ref} height="120" />
      {!hasData && <div className="empty-hint">אין נתונים להצגה</div>}
    </div>
  );
}

function SummaryTable({ title, headers, rows }) {
  return (
    <div className="card">
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
    </div>
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

function KpiCard({ label, value, hint, tone = "neutral" }) {
  return (
    <div className={`kpi-card ${tone}`}>
      <div className="kpi-card__label">{label}</div>
      <div className="kpi-card__value">{value}</div>
      {hint && <div className="kpi-card__hint">{hint}</div>}
    </div>
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
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem("IRONVIEW_USER");
    return stored ? JSON.parse(stored) : null;
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

  useEffect(() => localStorage.setItem("IRONVIEW_API", apiBase), [apiBase]);
  useEffect(() => localStorage.setItem("IRONVIEW_SECTION", section), [section]);
  useEffect(() => localStorage.setItem("IRONVIEW_TOPN", String(topN)), [topN]);
  useEffect(() => localStorage.setItem("IRONVIEW_PLATOON", platoon), [platoon]);
  useEffect(() => localStorage.setItem("IRONVIEW_WEEK", week), [week]);
  useEffect(() => localStorage.setItem("IRONVIEW_VIEW", viewMode), [viewMode]);
  useEffect(() => localStorage.setItem("IRONVIEW_TOKEN", token), [token]);
  useEffect(() => {
    if (user) {
      localStorage.setItem("IRONVIEW_USER", JSON.stringify(user));
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
      await loadQueries();
      await loadStatus();
      await loadSummary();
    } catch (err) {
      resultEl.textContent = `שגיאה: ${err}`;
      setBanner({ text: `שגיאה בהעלאה (${friendlyImportName(kind)}): ${err}`, tone: "danger" });
    }
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
      console.error(err);
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
      console.error(err);
      setCoverage(null);
    }
  };

  const triggerSync = async () => {
    setBanner({ text: "סנכרון מתבצע...", tone: "warning" });
    try {
      const res = await fetch(`${apiBase}/sync/google?target=all`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (handleAuthBanner(res.status, setBanner)) return;
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setBanner({ text: `סנכרון הצליח · platoon:${data.platoon_loadout} summary:${data.battalion_summary} forms:${data.form_responses}`, tone: "success" });
      await loadStatus();
      await loadQueries();
      await loadSummary();
    } catch (err) {
      setBanner({ text: `שגיאה בסנכרון: ${err}`, tone: "danger" });
    }
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
    setViewMode("battalion");
  };

  if (!user) {
    return <LoginOverlay onLogin={handleLogin} defaultPlatoon={platoon || "כפיר"} />;
  }

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

  return (
    <div className="page">
      <header className="topbar">
        <div className="hero">
          <div className="hero-text">
            <div className="pill brand">קצה הרומח · רומח 75</div>
            <h1>דשבורד מוכנות גדודי</h1>
            <p className="muted">סקירה פלוגתית/גדודית, סנכרון מגוגל, כיסוי ואנומליות.</p>
            <div className="header-actions">
              <div className="pill small">משתמש: {user.email || "לא צוין"}</div>
              <div className="pill small">פלוגה: {user.platoon || "n/a"}</div>
              <div className="status">{health}</div>
              <div className="pill">{syncStatus?.enabled ? "Google Sync פעיל" : "Google Sync כבוי"}</div>
              <div className="pill ghost" onClick={() => { setUser(null); setToken(""); localStorage.removeItem("IRONVIEW_USER"); }}>
                התנתק
              </div>
            </div>
          </div>
          <img src={platoonLogos.romach} alt="רומח 75" className="hero-logo" />
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
          <div className="button-group gap">
            <button onClick={() => document.getElementById("import")?.scrollIntoView({ behavior: "smooth" })}>
              ייבוא/סנכרון
            </button>
            <button onClick={triggerSync}>סנכרון מ-Google</button>
            <button onClick={() => { loadQueries(); loadSummary(); loadStatus(); loadCoverage(); }}>רענון נתונים</button>
          </div>
        </div>

        <div className="kpi-strip">
          <KpiCard label="שבוע נוכחי" value={summary?.latest_week || summary?.week || coverage?.week || "n/a"} />
          <KpiCard
            label="דיווחים השבוע"
            value={coverageTotals.formsTotal || 0}
            hint="סך טפסים מכל הפלוגות"
          />
          <KpiCard label="טנקים מדווחים" value={coverageTotals.tanksTotal || 0} />
          <KpiCard
            label="סנכרון אחרון"
            value={syncInfo.last}
            hint={`מקור: ${syncInfo.source} · ETag: ${syncInfo.etag}`}
            tone={syncInfo.status === "error" ? "danger" : "neutral"}
          />
          <KpiCard
            label="אנומליות פעילות"
            value={coverageTotals.anomaliesCount}
            tone={coverageTotals.anomaliesCount ? "warn" : "neutral"}
          />
        </div>

        <section id="import">
          <SectionHeader title="ייבוא וסנכרון" subtitle="סנכרון אוטומטי מטפסי הפלוגות. העלה קובץ טפסים לגיבוי בלבד." />
          <div className="upload-grid">
            <UploadCard title="Form Responses" inputId="file-form" onUpload={(id) => uploadFile("form-responses", id)} />
          </div>
          <div className="actions" style={{ marginTop: 10 }}>
            <button onClick={triggerSync}>סנכרון מ-Google Sheets</button>
          </div>
        </section>

        <section id="platoons">
          <SectionHeader title="ניווט פלוגות" subtitle="בחירת פלוגה ותצוגה מהירה של כיסוי ודיווחים">
          </SectionHeader>
          <div className="platoon-grid">
            {platoonCards.length ? (
              platoonCards.map((card) => (
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
              ))
            ) : (
              <div className="card empty-card">אין נתוני כיסוי. העלה טפסים כדי לראות פלוגות.</div>
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
              <SummaryTable
                title="סיכום פלוגות"
                headers={["פלוגה", "טנקים", "חוסרי זיווד", "חוסרי אמצעים"]}
                rows={platoonRows}
              />
              <SummaryTable
                title="תחמושת גדודית"
                headers={["אמצעי", "סה\"כ", "ממוצע לטנק"]}
                rows={Object.entries(summary?.battalion?.ammo || {}).map(([item, vals]) => ({
                  key: item,
                  cells: [item, vals.total ?? 0, vals.avg_per_tank ?? 0],
                }))}
              />
            </div>
          ) : (
            <div className="grid two-col">
              <SummaryTable title="זיווד חוסרים" headers={["פריט", "חוסרים/בלאי"]} rows={zivudRows} />
              <SummaryTable
                title="תחמושת"
                headers={["אמצעי", "סה\"כ", "ממוצע לטנק"]}
                rows={ammoRows}
              />
              <SummaryTable
                title="אמצעים"
                headers={["אמצעי", "חוסרים/בלאי", "ממוצע לטנק"]}
                rows={meansRows}
              />
              <SummaryTable title="פערי צלמים" headers={["פריט", "צ טנק", "מט\"ק", "דגשים"]} rows={issueRows} />
            </div>
          )}

          <div className="grid two-col">
            <SummaryTable
              title="כיסוי ודיווחים"
              headers={["פלוגה", "מספר טפסים", "טנקים מדווחים", "ימים מאז דיווח", "אנומליה"]}
              rows={coverageRows}
            />
            <SummaryTable
              title="אנומליות"
              headers={["פלוגה", "סיבה", "טפסים שבוע נוכחי", "ממוצע אחרון", "ימים ללא דיווח"]}
              rows={anomalyRows}
            />
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
              <button onClick={() => { loadQueries(); loadSummary(); loadStatus(); }}>רענון נתונים</button>
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
            <div className="card-title">Form Status</div>
            <div className="grid two-col">
              <div>
                <h4>OK</h4>
                <pre>{formsOk}</pre>
              </div>
              <div>
                <h4>Gaps</h4>
                <pre>{formsGaps}</pre>
              </div>
            </div>
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
      </main>
    </div>
  );
}

export default App;
