const baseApi = () => {
  const stored = typeof localStorage !== "undefined" ? localStorage.getItem("IRONVIEW_API") : null;
  const fallback = typeof window !== "undefined" ? window.location.origin.replace(/\/$/, "") : "http://localhost:8000";
  return stored || fallback || "http://localhost:8000";
};

const authHeaders = (token) => (token ? { Authorization: `Bearer ${token}` } : {});

export const apiFetch = async (path, opts = {}, token) => {
  const res = await fetch(`${baseApi()}${path}`, {
    ...opts,
    headers: {
      ...(opts.headers || {}),
      ...authHeaders(token),
    },
  });
  if (res.status === 401) {
    const err = new Error("unauthorized");
    err.code = 401;
    throw err;
  }
  if (!res.ok) {
    const text = await res.text();
    const err = new Error(text || "request failed");
    err.status = res.status;
    throw err;
  }
  return res;
};

export const fetchJson = async (path, token, opts = {}) => {
  const res = await apiFetch(path, opts, token);
  return res.json();
};

export const uploadFile = async (kind, file, token) => {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch(`/imports/${kind}`, { method: "POST", body: form }, token);
  return res.json();
};

export const triggerSync = async (token) => fetchJson("/sync/google?target=all", token, { method: "POST" });
export const fetchSyncStatus = async (token) => fetchJson("/sync/status", token);
export const fetchSummary = async (mode, week, platoon, token) => {
  const params = new URLSearchParams();
  params.append("mode", mode);
  if (week) params.append("week", week);
  if (mode === "platoon" && platoon) params.append("platoon", platoon);
  return fetchJson(`/queries/forms/summary?${params.toString()}`, token);
};
export const fetchCoverage = async (week, token) => {
  const params = new URLSearchParams();
  if (week) params.append("week", week);
  return fetchJson(`/queries/forms/coverage?${params.toString()}`, token);
};
export const fetchTabular = async (section, topN, platoon, week, token) => {
  const platoonParam = platoon ? `&platoon=${encodeURIComponent(platoon)}` : "";
  const weekParam = week ? `&week=${encodeURIComponent(week)}` : "";
  const [totals, gaps, delta, variance, forms, insights, trends] = await Promise.all([
    fetchJson(`/queries/tabular/totals?section=${section}&top_n=${topN}${platoonParam}${weekParam}`, token),
    fetchJson(`/queries/tabular/gaps?section=${section}&top_n=${topN}${platoonParam}${weekParam}`, token),
    fetchJson(`/queries/tabular/delta?section=${section}&top_n=${topN}`, token),
    fetchJson(`/queries/tabular/variance?section=${section}&top_n=${topN}`, token),
    fetchJson(`/queries/forms/status`, token),
    fetchJson(`/insights?section=${section}&top_n=${topN}${platoonParam}`, token),
    fetchJson(`/queries/trends?section=${section}&top_n=5${platoonParam}`, token),
  ]);
  return { totals, gaps, delta, variance, forms, insights, trends };
};

export const exportReport = async (mode, week, platoon, token) => {
  const params = new URLSearchParams();
  if (week) params.append("week", week);
  if (mode === "platoon" && platoon) params.append("platoon", platoon);
  const endpoint = mode === "platoon" ? "/exports/platoon" : "/exports/battalion";
  const res = await apiFetch(`${endpoint}?${params.toString()}`, {}, token);
  return res.blob();
};
