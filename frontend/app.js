let API_BASE = localStorage.getItem("IRONVIEW_API") || "http://localhost:8000";
document.getElementById("api-base").value = API_BASE;

let chartTotals, chartGaps;

async function pingHealth() {
  const el = document.getElementById("health");
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    el.textContent = `OK v${data.version}`;
    el.style.color = "#10b981";
  } catch (err) {
    el.textContent = "API unreachable";
    el.style.color = "#f87171";
  }
}

function saveApiBase() {
  const val = document.getElementById("api-base").value.trim();
  if (val) {
    API_BASE = val;
    localStorage.setItem("IRONVIEW_API", val);
    pingHealth();
    loadQueries();
  }
}

async function uploadFile(kind, inputId, resultId) {
  const input = document.getElementById(inputId);
  const result = document.getElementById(resultId);
  const file = input.files[0];
  if (!file) {
    result.textContent = "Select a file first";
    return;
  }
  const form = new FormData();
  form.append("file", file);
  result.textContent = "Uploading...";
  try {
    const res = await fetch(`${API_BASE}/imports/${kind}`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    result.textContent = `Inserted: ${data.inserted}`;
    await loadQueries(); // refresh views
  } catch (err) {
    result.textContent = `Error: ${err}`;
  }
}

async function loadQueries() {
  const section = document.getElementById("section").value;
  const topN = document.getElementById("top-n").value || 5;
  try {
    const [totals, gaps, delta, variance, forms] = await Promise.all([
      fetch(`${API_BASE}/queries/tabular/totals?section=${section}&top_n=${topN}`).then(r => r.json()),
      fetch(`${API_BASE}/queries/tabular/gaps?section=${section}&top_n=${topN}`).then(r => r.json()),
      fetch(`${API_BASE}/queries/tabular/delta?section=${section}&top_n=${topN}`).then(r => r.json()),
      fetch(`${API_BASE}/queries/tabular/variance?section=${section}&top_n=${topN}`).then(r => r.json()),
      fetch(`${API_BASE}/queries/forms/status`).then(r => r.json()),
    ]);

    renderChart("chart-totals", totals.map(t => t.item), totals.map(t => t.total), "Totals", (chart) => chartTotals = chart, chartTotals);
    renderChart("chart-gaps", gaps.map(g => g.item), gaps.map(g => g.gaps), "Gaps", (chart) => chartGaps = chart, chartGaps, "#ef4444");
    document.getElementById("totals").textContent = JSON.stringify(totals, null, 2);
    document.getElementById("gaps").textContent = JSON.stringify(gaps, null, 2);
    document.getElementById("delta").textContent = JSON.stringify(delta, null, 2);
    document.getElementById("variance").textContent = JSON.stringify(variance, null, 2);
    document.getElementById("forms-ok").textContent = JSON.stringify(forms.ok.slice(0, topN), null, 2);
    document.getElementById("forms-gaps").textContent = JSON.stringify(forms.gaps.slice(0, topN), null, 2);
  } catch (err) {
    document.getElementById("totals").textContent = `Error: ${err}`;
  }
}

function renderChart(canvasId, labels, data, label, setRef, existingChart, color = "#22c55e") {
  const ctx = document.getElementById(canvasId);
  if (existingChart) existingChart.destroy();
  setRef(new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label,
        data,
        backgroundColor: color + "99",
        borderColor: color,
        borderWidth: 1,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: "#cbd5e1" } }, y: { ticks: { color: "#cbd5e1" } } }
    }
  }));
}

pingHealth();
loadQueries();
