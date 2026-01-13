const fallbackBase =
  typeof window !== "undefined" ? window.location.origin.replace(/\/$/, "") : "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message || "API error");
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const normalizeBase = (baseUrl) => (baseUrl || fallbackBase).replace(/\/$/, "");

const buildQuery = (params) => {
  if (!params) return "";
  const entries = Object.entries(params).filter(
    ([, value]) => value !== undefined && value !== null && value !== "",
  );
  if (!entries.length) return "";
  const qs = new URLSearchParams();
  entries.forEach(([key, value]) => qs.append(key, String(value)));
  const rendered = qs.toString();
  return rendered ? `?${rendered}` : "";
};

export const createApiClient = ({ baseUrl, token, oauthSession, onUnauthorized } = {}) => {
  const resolvedBase = normalizeBase(baseUrl);
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};
  const sessionHeader = oauthSession || token;

  const request = async (path, { method = "GET", headers, body, responseType = "json", signal } = {}) => {
    const res = await fetch(`${resolvedBase}${path}`, {
      method,
      headers: {
        ...authHeaders,
        ...(sessionHeader ? { "X-OAuth-Session": sessionHeader } : {}),
        ...(headers || {}),
      },
      body,
      signal,
    });

    if (res.status === 401) {
      if (onUnauthorized) onUnauthorized();
      throw new ApiError("unauthorized", 401);
    }

    if (!res.ok) {
      let detail;
      try {
        detail = await res.json();
      } catch {
        try {
          detail = await res.text();
        } catch {
          detail = null;
        }
      }
      throw new ApiError(detail?.detail || detail || res.statusText, res.status, detail);
    }

    if (responseType === "blob") return res.blob();
    if (responseType === "text") return res.text();
    if (responseType === "raw") return res;
    return res.json();
  };

  const getJson = (path, params, options = {}) =>
    request(`${path}${buildQuery(params)}`, {
      ...options,
      method: options.method || "GET",
    });

  const postJson = (path, params, options = {}) =>
    request(`${path}${buildQuery(params)}`, {
      ...options,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      body: options.body ? JSON.stringify(options.body) : options.body,
    });

  const upload = (path, file, params, options = {}) => {
    const form = new FormData();
    form.append("file", file);
    return request(`${path}${buildQuery(params)}`, {
      ...options,
      method: "POST",
      body: form,
    });
  };

  const download = (path, params, options = {}) =>
    request(`${path}${buildQuery(params)}`, {
      ...options,
      method: options.method || "GET",
      responseType: "blob",
    });

  const tabularBundle = async (params, signal) => {
    const { section, topN, platoon, week } = params;
    const scoped = {
      section,
      top_n: topN,
      platoon,
      week,
    };
    const [totals, gaps, delta, variance, forms, insights, trends] = await Promise.all([
      getJson("/queries/tabular/totals", scoped, { signal }),
      getJson("/queries/tabular/gaps", scoped, { signal }),
      getJson("/queries/tabular/delta", { section, top_n: topN }, { signal }),
      getJson("/queries/tabular/variance", { section, top_n: topN }, { signal }),
      getJson("/queries/forms/status", null, { signal }),
      getJson("/insights", { section, top_n: topN, platoon }, { signal }),
      getJson("/queries/trends", { section, top_n: 5, platoon }, { signal }),
    ]);
    return { totals, gaps, delta, variance, forms, insights, trends };
  };

  return {
    baseUrl: resolvedBase,
    getJson,
    postJson,
    upload,
    download,
    health: (signal) => getJson("/health", null, { signal }),
    syncStatus: (signal) => getJson("/sync/status", null, { signal }),
    syncGoogle: (target = "all", signal) => postJson("/sync/google", { target }, { signal }),
    summary: (params, signal) => getJson("/queries/forms/summary", params, { signal }),
    coverage: (params, signal) => getJson("/queries/forms/coverage", params, { signal }),
    tabularBundle,
    exportReport: (mode, params, signal) =>
      download(mode === "platoon" ? "/exports/platoon" : "/exports/battalion", params, { signal }),
    uploadImport: (kind, file, signal) => upload(`/imports/${kind}`, file, null, { signal }),
    uploadForms: (file, signal) => upload("/imports/form-responses", file, null, { signal }),
  };
};
