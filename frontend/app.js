const API_BASE = localStorage.getItem("IRONVIEW_API") || "http://localhost:8000";

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

async function uploadFile(kind, inputId) {
  const input = document.getElementById(inputId);
  const result = document.getElementById(`result-${inputId.split("-")[1]}`);
  const file = input.files[0];
  if (!file) {
    result.textContent = "Select a file first";
    return;
  }
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch(`${API_BASE}/imports/${kind}`, {
      method: "POST",
      body: form,
    });
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
    const [totals, gaps, forms] = await Promise.all([
      fetch(`${API_BASE}/queries/tabular/totals?section=${section}&top_n=${topN}`).then(r => r.json()),
      fetch(`${API_BASE}/queries/tabular/gaps?section=${section}&top_n=${topN}`).then(r => r.json()),
      fetch(`${API_BASE}/queries/forms/status`).then(r => r.json()),
    ]);
    document.getElementById("totals").textContent = JSON.stringify(totals, null, 2);
    document.getElementById("gaps").textContent = JSON.stringify(gaps, null, 2);
    document.getElementById("forms").textContent = JSON.stringify(forms, null, 2);
  } catch (err) {
    document.getElementById("totals").textContent = `Error: ${err}`;
  }
}

pingHealth();
loadQueries();
