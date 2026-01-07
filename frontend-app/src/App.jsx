import { useEffect, useMemo, useRef, useState } from "react";
import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
} from "chart.js";
import "./index.css";

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip);

const defaultApi = localStorage.getItem("IRONVIEW_API") || "http://localhost:8000";

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
      <button onClick={() => onUpload(inputId)}>Upload</button>
      <div className="result" id={`result-${inputId}`} />
    </div>
  );
}

function ChartCard({ title, data, color = "#22c55e" }) {
  const ref = useRef(null);
  const chartRef = useRef(null);

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
          x: { ticks: { color: "#cbd5e1" } },
          y: { ticks: { color: "#cbd5e1" } },
        },
      },
    });
  }, [data, title, color]);

  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <canvas ref={ref} height="120" />
    </div>
  );
}

function App() {
  const [apiBase, setApiBase] = useState(defaultApi);
  const [health, setHealth] = useState("Checking...");
  const [section, setSection] = useState("zivud");
  const [topN, setTopN] = useState(5);
  const [totals, setTotals] = useState([]);
  const [gaps, setGaps] = useState([]);
  const [delta, setDelta] = useState([]);
  const [variance, setVariance] = useState([]);
  const [forms, setForms] = useState({ ok: [], gaps: [] });

  useEffect(() => {
    localStorage.setItem("IRONVIEW_API", apiBase);
    pingHealth();
    loadQueries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  const pingHealth = async () => {
    try {
      const res = await fetch(`${apiBase}/health`);
      const data = await res.json();
      setHealth(`OK v${data.version}`);
    } catch (err) {
      setHealth("API unreachable");
    }
  };

  const uploadFile = async (kind, inputId) => {
    const input = document.getElementById(inputId);
    const resultEl = document.getElementById(`result-${inputId}`);
    const file = input?.files?.[0];
    if (!file) {
      resultEl.textContent = "Select a file first";
      return;
    }
    const form = new FormData();
    form.append("file", file);
    resultEl.textContent = "Uploading...";
    try {
      const res = await fetch(`${apiBase}/imports/${kind}`, { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      resultEl.textContent = `Inserted: ${data.inserted}`;
      await loadQueries();
    } catch (err) {
      resultEl.textContent = `Error: ${err}`;
    }
  };

  const loadQueries = async () => {
    try {
      const [t, g, d, v, f] = await Promise.all([
        fetch(`${apiBase}/queries/tabular/totals?section=${section}&top_n=${topN}`).then((r) => r.json()),
        fetch(`${apiBase}/queries/tabular/gaps?section=${section}&top_n=${topN}`).then((r) => r.json()),
        fetch(`${apiBase}/queries/tabular/delta?section=${section}&top_n=${topN}`).then((r) => r.json()),
        fetch(`${apiBase}/queries/tabular/variance?section=${section}&top_n=${topN}`).then((r) => r.json()),
        fetch(`${apiBase}/queries/forms/status`).then((r) => r.json()),
      ]);
      setTotals(t);
      setGaps(g);
      setDelta(d);
      setVariance(v);
      setForms(f);
    } catch (err) {
      console.error(err);
    }
  };

  const deltaText = useMemo(() => JSON.stringify(delta, null, 2), [delta]);
  const varianceText = useMemo(() => JSON.stringify(variance, null, 2), [variance]);
  const formsOk = useMemo(() => JSON.stringify((forms.ok || []).slice(0, topN), null, 2), [forms.ok, topN]);
  const formsGaps = useMemo(() => JSON.stringify((forms.gaps || []).slice(0, topN), null, 2), [forms.gaps, topN]);

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>IronView</h1>
          <p className="muted">Local dashboard for imports and deterministic queries</p>
        </div>
        <div className="header-actions">
          <label className="api-label">
            API:
            <input value={apiBase} onChange={(e) => setApiBase(e.target.value)} />
          </label>
          <div className="status">{health}</div>
        </div>
      </header>

      <main>
        <section>
          <SectionHeader title="Import Files" subtitle="Upload the latest weekly spreadsheets to refresh the local DB." />
          <div className="upload-grid">
            <UploadCard title="Platoon Loadout" inputId="file-loadout" onUpload={(id) => uploadFile("platoon-loadout", id)} />
            <UploadCard title="Battalion Summary" inputId="file-summary" onUpload={(id) => uploadFile("battalion-summary", id)} />
            <UploadCard title="Form Responses" inputId="file-form" onUpload={(id) => uploadFile("form-responses", id)} />
          </div>
        </section>

        <section>
          <SectionHeader
            title="Readiness Snapshots"
            subtitle="Totals, gaps, delta, and variance for the selected section"
          >
            <div className="controls">
              <label>
                Section:
                <select value={section} onChange={(e) => setSection(e.target.value)}>
                  <option value="zivud">zivud</option>
                  <option value="ammo">ammo</option>
                </select>
              </label>
              <label>
                Top N:
                <input type="number" value={topN} min={1} max={50} onChange={(e) => setTopN(Number(e.target.value))} />
              </label>
              <button onClick={loadQueries}>Run</button>
            </div>
          </SectionHeader>

          <div className="grid two-col">
            <ChartCard title="Totals" data={totals.map((t) => ({ item: t.item, value: t.total }))} />
            <ChartCard title="Gaps" data={gaps.map((g) => ({ item: g.item, value: g.gaps }))} color="#ef4444" />
          </div>

          <div className="grid two-col">
            <div className="card">
              <div className="card-title">Delta vs Previous Import</div>
              <pre>{deltaText}</pre>
            </div>
            <div className="card">
              <div className="card-title">Variance vs Battalion Summary</div>
              <pre>{varianceText}</pre>
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
        </section>
      </main>
    </div>
  );
}

export default App;
